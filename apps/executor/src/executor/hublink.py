"""Koppeling van de executor met de Hub (contract 1.3 §3.2–§3.9, §4.5, §4.7).

- Koppelen alleen met een **koppelcode (30 min) + Hub-vingerafdruk** op de eigen statuspagina (§3.9); de Hub geeft voor
  de executor geen enrollment-token uit. Daarna geen koppelformulier meer, tot een ontkoppeling op de executorpagina
  (``/beheer``, met een live geverifieerde TrueNAS-schrijfkey tegen het vastgelegde NAS-adres + certificaat). Die wist
  ook de schrijfsleutel; in ``ontkoppeld`` komt het koppelformulier terug, en de executor voert niets uit tot de sleutel
  opnieuw is ingesteld (BN-1 a, S-P2-020; ADR-0030 besluit 13).
- Opslag in ``/appdata/secrets/hub-link.json`` (0600, atomair, onder ``hub-link.lock``), nooit in een database. Een
  onleesbaar bestand (geen geldige JSON, andere major, ontbrekende velden, verkeerde eigenaar of rechten) is
  **fail-closed** (§3.5): geen vertrouwen, geen formulier, ``koppelstatus_onleesbaar``; een gewone schrijfactie zet
  het nooit stil terug. De executor heeft geen env-token (§3.9): herstel gaat alleen met de live geverifieerde
  schrijfsleutel (:meth:`HubLinkStore.ontkoppel`, aangeroepen door ``/beheer``).
- Hub-sleutels worden gepind uit het enroll-antwoord; een via HTTP opgehaalde JWKS voegt nooit vertrouwen toe.
- Aanroepen naar de Hub: ``http.client`` (geen redirects, geen proxy-omgeving), 5 s connect / 15 s read; de host
  wordt bij elke verbinding opgelost en gecontroleerd (§3.2) en de verbinding gaat naar precies dat adres.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import stat
import threading
import time
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from executor.adres import AdresOngeldig, resolve_allowed
from executor.adres import validate_hub_url as _validate_hub_url
from executor.statuspagina import HERSTEL

SCHEMA_VERSION = "1.3"
STATES = ("nooit_gekoppeld", "gekoppeld", "ontkoppeld", "ingetrokken")
PENDING_MAX_SECONDS = 60 * 60
FILE_NAME = "hub-link.json"
LOCK_NAME = "hub-link.lock"
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
KEYSET_PREFIX = "jl-hub-keyset-v1"
SERVICE_TOKEN_RE = re.compile(r"^svc_[A-Za-z0-9_-]{43}$")
MAX_USED_TOKENS = 20
CLOCK_SKEW = 30

# Herstel bij koppelstatus_onleesbaar: het blok met 'Ontkoppelen van de Hub' staat alleen op de executorpagina als er
# een bruikbare TrueNAS-schrijfsleutel is (statuspagina.py, executor_beheer). Zonder, of als dat niet bekend is,
# verwijst de melding naar het installatiedocument; die verwijzing klopt altijd (R-ONTWERP-4, S-P2-005).
_ONLEESBAAR = "De koppelstatus van de executor is onleesbaar. Hij vertrouwt de Hub niet en voert niets uit."
HERSTEL_MET_SLEUTEL = "Herstel gaat met de TrueNAS-schrijfsleutel op deze pagina (Ontkoppelen van de Hub)."
HERSTEL_ZONDER_SLEUTEL = (
    "Er is geen bruikbare TrueNAS-schrijfsleutel (niet ingesteld of onleesbaar) waarmee je dit op deze pagina kunt "
    f"herstellen. {HERSTEL}"
)

# Vaste meldingen bij last_error (contract 1.3 §3.5, open codelijst); de code is voor machines, de tekst voor mensen.
ERRORS_NL = {
    "hub_onbereikbaar": "De Hub was niet bereikbaar. Controleer het adres en probeer het opnieuw.",
    "hub_weigerde": "De Hub weigerde de koppelcode (onbekend, verlopen of al gebruikt). Maak in de Hub een nieuwe.",
    "hub_incompatibel": "De Hub weigerde het verzoek als ongeldig (versies passen niet bij elkaar); er is niets "
    "opgeslagen.",
    "koppelstatus_onleesbaar": f"{_ONLEESBAAR} {HERSTEL_ZONDER_SLEUTEL}",
    "hub_antwoord_ongeldig": "Het antwoord van de Hub voldeed niet aan het contract; er is niets opgeslagen.",
    "hub_vingerafdruk_onjuist": "De vingerafdruk klopt niet met de sleutels van deze Hub; er is niets opgeslagen.",
    "enroll_endpoint_ontbreekt": "Deze Hub-versie kent aanmelden niet.",
    "rate_limited": "Te veel pogingen; wacht even en probeer het dan opnieuw.",
    "koppelen_onderbroken": "Het koppelen is onderbroken door een herstart. Voer de koppelcode opnieuw in.",
    # Bij de executor niet "via de Hub": ontkoppelen en opnieuw koppelen gaan op deze pagina (§3.9, KLEIN-60).
    "ingetrokken_door_hub": "De Hub heeft deze koppeling ingetrokken; de executor voert niets uit. Opnieuw koppelen "
    "kan alleen na 'Ontkoppelen van de Hub' op deze pagina, met de huidige TrueNAS-schrijfsleutel als bewijs. Dat blok "
    f"staat er alleen als de sleutel is ingesteld. Is er geen sleutel? {HERSTEL}",
    "sleutelrotatie_niet_toegepast": "De Hub meldt een sleutelrotatie die deze versie nog niet kan toepassen; "
    "opnieuw koppelen via de Hub.",
}
PUBLIC_FIELDS = (
    "state",
    "hub_url",
    "service_id",
    "via",
    "linked_at",
    "first_linked_at",
    "service_token_last4",
)


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    if b64url(raw) != text:
        raise ValueError("geen canonieke base64url")
    return raw


# ------------------------------------------------------------------ thumbprint en vingerafdruk (§4.5)
def jwk_thumbprint(jwk: Mapping[str, Any]) -> str:
    x = jwk.get("x")
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519" or not isinstance(x, str) or "d" in jwk:
        raise ValueError("alleen een publieke Ed25519-JWK")
    if len(b64url_decode(x)) != 32:
        raise ValueError("x moet 32 bytes zijn")
    canonical = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": x}, separators=(",", ":"), sort_keys=True)
    return b64url(hashlib.sha256(canonical.encode()).digest())


def keyset_fingerprint(
    jwt_keys: list[Mapping[str, Any]], policy_keys: Mapping[str, Any] | list[Mapping[str, Any]]
) -> str:
    """§4.5 (1.3): over **alle** jwt- en policy-sleutels, beide lijsten gesorteerd op bytewaarde. Met één
    policy-sleutel gelijk aan 1.2 (testvectoren MEGG-…, CYRC-…; nieuw HN69-2PHK-XV2D-X85W met twee policy-sleutels)."""
    policies = [policy_keys] if isinstance(policy_keys, Mapping) else list(policy_keys)
    thumbs = sorted(jwk_thumbprint(k) for k in jwt_keys)
    pthumbs = sorted(jwk_thumbprint(k) for k in policies)
    if not thumbs or not pthumbs:
        raise ValueError("minstens één JWT- en één policy-sleutel nodig")
    text = f"{KEYSET_PREFIX}\njwt:{','.join(thumbs)}\npolicy:{','.join(pthumbs)}"
    bits = "".join(f"{b:08b}" for b in hashlib.sha256(text.encode()).digest()[:10])
    code = "".join(CROCKFORD[int(bits[i : i + 5], 2)] for i in range(0, 80, 5))
    return "-".join(code[i : i + 4] for i in range(0, 16, 4))


def normalize_code(value: str) -> str:
    """Koppelcode en vingerafdruk: hoofdletters, alleen letters/cijfers, ``O→0``, ``I/L→1``."""
    cleaned = "".join(ch for ch in value.upper() if ch.isascii() and ch.isalnum())
    return cleaned.replace("O", "0").replace("I", "1").replace("L", "1")


def valid_pairing_code(value: str) -> bool:
    n = normalize_code(value)
    return len(value) <= 32 and len(n) == 12 and all(ch in CROCKFORD for ch in n)


def valid_fingerprint(value: str) -> bool:
    """Invoer ≤ 64 tekens als geheel (§3.7: nooit eerst afkappen); na normalisatie precies 16 tekens."""
    n = normalize_code(value)
    return len(value) <= 64 and len(n) == 16 and all(ch in CROCKFORD for ch in n)


# ------------------------------------------------------------------ Hub-adres (§3.2)
def validate_hub_url(value: str, *, allow_loopback: bool = False) -> str:
    """``http(s)://<host>[:<poort>]`` volgens de adresregels van §3.2 (zie :mod:`executor.adres`)."""
    return _validate_hub_url(value, allow_loopback=allow_loopback)


# ------------------------------------------------------------------ opslag (§3.5)
def empty_link() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "nooit_gekoppeld",
        "app_id": None,
        "hub_url": None,
        "service_id": None,
        "via": None,
        "first_linked_at": None,
        "linked_at": None,
        "confirmed_at": None,
        "service_token": None,
        "service_token_last4": None,
        "pins": None,
        "previous_pins": None,
        "pending": None,
        "used_enrollment_token_sha256": [],
        "last_error": None,
    }


class KoppelstatusOnleesbaar(Exception):
    """``hub-link.json`` is onleesbaar (§3.5): fail-closed; een gewone schrijfactie mag het niet terugzetten."""


def _required_ok(data: Mapping[str, Any]) -> bool:
    """Verplichte velden van §3.5; extra velden mogen (oudere lezers negeren ze)."""
    version = data.get("schema_version")
    if not isinstance(version, str) or version.split(".")[0] != "1":
        return False
    state = data.get("state")
    if state not in STATES:
        return False
    if not isinstance(data.get("used_enrollment_token_sha256", []), list):
        return False
    if state != "nooit_gekoppeld" and not (isinstance(data.get("first_linked_at"), str) and data["first_linked_at"]):
        return False  # zonder first_linked_at zou het formulier terugkomen (§3.7): nooit stil "nooit gekoppeld"
    if state == "gekoppeld":
        pins = data.get("pins")
        if not isinstance(pins, dict) or not isinstance(pins.get("jwt"), list):
            return False
        for key in ("service_token", "service_id", "hub_url"):
            if not isinstance(data.get(key), str) or not data[key]:
                return False
    return True


class HubLinkStore:
    def __init__(self, secrets_dir: Path, *, allow_loopback: bool = False) -> None:
        self.dir = secrets_dir
        self.path = secrets_dir / FILE_NAME
        self.lock_path = secrets_dir / LOCK_NAME
        self.allow_loopback = allow_loopback

    def _load(self) -> dict[str, Any] | None:
        """Inhoud, of ``None`` als het bestand onleesbaar is (§3.5). Een ontbrekend bestand = ``nooit_gekoppeld``."""
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return empty_link()
        except OSError:
            return None  # o.a. een symlink of geen leesrecht
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
                return None  # verkeerde eigenaar of rechten (moet 0600 van de eigen gebruiker zijn)
            raw = os.read(fd, 1024 * 1024 + 1)
        finally:
            os.close(fd)
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        if not isinstance(data, dict) or len(raw) > 1024 * 1024 or not _required_ok(data):
            return None
        return {**empty_link(), **data}

    def read(self) -> dict[str, Any]:
        """De koppelstatus; bij een onleesbaar bestand een fail-closed toestand met ``_onleesbaar`` (nooit
        geschreven) en ``last_error`` ``koppelstatus_onleesbaar`` — geen pins, geen token."""
        data = self._load()
        if data is None:
            return {
                **empty_link(),
                "state": None,
                "_onleesbaar": True,
                "last_error": {"code": "koppelstatus_onleesbaar", "at": now_iso()},
            }
        return data

    def unreadable(self) -> bool:
        return bool(self.read().get("_onleesbaar"))

    @contextlib.contextmanager
    def update(self) -> Iterator[dict[str, Any]]:
        """Lezen-wijzigen-schrijven onder een exclusieve vergrendeling; atomair vervangen (O_EXCL → fsync → rename).
        Een onleesbaar bestand → :class:`KoppelstatusOnleesbaar` (nooit stil terugzetten, §3.5)."""
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = self._load()
            if data is None:
                raise KoppelstatusOnleesbaar
            yield data
            data["schema_version"] = SCHEMA_VERSION  # een dienst schrijft de versie van het contract dat hij volgt
            self._write(data)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def ontkoppel(self) -> None:
        """Ontkoppelen op de executorpagina, na een live geverifieerde TrueNAS-schrijfsleutel (contract 1.3 §3.9; de
        aanroeper wist eerst de schrijfsleutel, BN-1 a, S-P2-020). Net als bij een ontkoppeling door de Hub (§3.8):
        ``state`` wordt ``ontkoppeld``, service-token weg, pins naar ``previous_pins`` (alleen audit, geen vertrouwen),
        een lopende poging weg. ``first_linked_at`` blijft **altijd** staan (§3.5).

        Is het bestand onleesbaar, dan blijft het origineel bewaard als ``hub-link.json.onleesbaar-<UTC-tijd>`` (0600,
        §3.5) en komt er een nieuw bestand met ``unreadable_replaced_at``. De echte ``first_linked_at`` is dan niet te
        lezen; omdat er een schrijfsleutel lag, is de executor eerder gekoppeld geweest, en ``first_linked_at`` wordt
        het moment van vervangen (nooit leeg: een leeg veld zou "nooit gekoppeld" betekenen)."""
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            at = now_iso()
            data = self._load()
            if data is None:
                bewaard = self.dir / f"{FILE_NAME}.onleesbaar-{at.replace('-', '').replace(':', '')}"
                # Hernoemen volgt nooit een symlink (die wordt zelf hernoemd); een gewoon bestand krijgt 0600.
                os.rename(self.path, bewaard)
                with contextlib.suppress(OSError):
                    kopie = os.open(bewaard, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        if stat.S_ISREG(os.fstat(kopie).st_mode):
                            os.fchmod(kopie, 0o600)
                    finally:
                        os.close(kopie)
                data = {**empty_link(), "unreadable_replaced_at": at}
            if data.get("pins"):
                data["previous_pins"] = data["pins"]
            data.update(
                schema_version=SCHEMA_VERSION,
                state="ontkoppeld",
                first_linked_at=data.get("first_linked_at") or at,
                confirmed_at=None,
                service_token=None,
                service_token_last4=None,
                pins=None,
                pending=None,
                last_error=None,
            )
            self._write(data)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.dir / f".{FILE_NAME}.{uuid.uuid4().hex}"
        out = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(out, (json.dumps(data, indent=1, sort_keys=True) + "\n").encode())
            os.fsync(out)
        finally:
            os.close(out)
        os.replace(tmp, self.path)
        dfd = os.open(self.dir, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


def melding_nl(code: str, *, sleutel_ingesteld: bool = False) -> str | None:
    """De vaste melding bij ``code``. Bij ``koppelstatus_onleesbaar`` alleen met een bruikbare schrijfsleutel het
    herstel op deze pagina; anders de verwijzing naar het installatiedocument."""
    if code == "koppelstatus_onleesbaar" and sleutel_ingesteld:
        return f"{_ONLEESBAAR} {HERSTEL_MET_SLEUTEL}"
    return ERRORS_NL.get(code)


def public_status(link: Mapping[str, Any], *, sleutel_ingesteld: bool = False) -> dict[str, Any]:
    """Witte lijst (§3.5, een maximum): nooit service_token of pending.secret_sha256. ``sleutel_ingesteld``: of er een
    bruikbare TrueNAS-schrijfsleutel is (kiest de herstelweg in de melding, zie :func:`melding_nl`)."""
    out = {k: link.get(k) for k in PUBLIC_FIELDS}
    pins = link.get("pins") or {}
    out["koppelen_bezig"] = link.get("pending") is not None
    out["keyset_fingerprint"] = pins.get("keyset_fingerprint") if link.get("state") == "gekoppeld" else None
    err = link.get("last_error")
    out["last_error"] = (
        None
        if not err
        else {
            "code": err.get("code"),
            "melding": melding_nl(str(err.get("code")), sleutel_ingesteld=sleutel_ingesteld),
        }
    )
    return out


def resume_after_restart(store: HubLinkStore) -> None:
    """§3.6 stap 5: een koppelcode is na een herstart weg → ``koppelen_onderbroken``. Onleesbaar: niets schrijven."""
    link = store.read()
    if link.get("_onleesbaar") or link.get("pending") is None:
        return
    with store.update() as cur:
        if cur.get("pending") is not None:
            cur["pending"] = None
            cur["last_error"] = {"code": "koppelen_onderbroken", "at": now_iso()}


# ------------------------------------------------------------------ HTTP naar de Hub
@dataclass
class HubResponse:
    status: int
    body: Any
    retry_after: str | None = None


class HubUnreachable(Exception):
    pass


class _PinnedHTTP(http.client.HTTPConnection):
    """Verbindt met precies het gecontroleerde adres (§3.2: verboden bereiken ook na DNS-resolutie, per verbinding);
    de ``Host``-header blijft de naam uit het Hub-adres."""

    def __init__(self, host: str, port: int | None, *, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int | None, *, ip: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)  # type: ignore[attr-defined]


def hub_request(
    hub_url: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    bearer: str | None = None,
    connect_timeout: float = 5.0,
    read_timeout: float = 15.0,
    allow_loopback: bool = False,
) -> HubResponse:
    parts = urlsplit(hub_url)
    https = parts.scheme == "https"
    port = parts.port or (443 if https else 80)
    try:
        ip = resolve_allowed(parts.hostname or "", port, allow_loopback=allow_loopback)
    except AdresOngeldig:
        raise HubUnreachable("adres_niet_toegestaan") from None
    conn_cls = _PinnedHTTPS if https else _PinnedHTTP
    conn = conn_cls(parts.hostname or "", port, ip=ip, timeout=connect_timeout)
    headers = {"Accept": "application/json", "User-Agent": "ai-server-manager-executor"}
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode()
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    try:
        conn.connect()
        if conn.sock is not None:
            conn.sock.settimeout(read_timeout)
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read(1024 * 1024 + 1)
    except (OSError, http.client.HTTPException) as exc:
        raise HubUnreachable(type(exc).__name__) from None
    finally:
        conn.close()
    if 300 <= resp.status < 400 or len(raw) > 1024 * 1024:
        raise HubUnreachable("redirect_of_te_groot")  # nooit een redirect volgen (§3.2)
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    return HubResponse(resp.status, parsed, resp.getheader("Retry-After"))


# ------------------------------------------------------------------ enrollment (§3.3, §3.6)
class EnrollFailed(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def enroll_request(app_id: str, pairing_code: str, version: str, identity_jwk: Mapping[str, str]) -> dict[str, Any]:
    """Precies de velden van §3.3: ``public_key_jwk`` alleen ``{kty, crv, x, kid=thumbprint}``."""
    jwk = {"kty": "OKP", "crv": "Ed25519", "x": identity_jwk["x"]}
    jwk["kid"] = jwk_thumbprint(jwk)
    return {"app_id": app_id, "pairing_code": pairing_code, "version": version, "base_url": None, "public_key_jwk": jwk}


def _pin(jwk: Any) -> dict[str, Any]:
    if not isinstance(jwk, dict) or "d" in jwk or jwk.get("use") != "sig" or jwk.get("alg") != "EdDSA":
        raise EnrollFailed("hub_antwoord_ongeldig")
    if not isinstance(jwk.get("kid"), str) or not jwk["kid"]:
        raise EnrollFailed("hub_antwoord_ongeldig")
    try:
        thumb = jwk_thumbprint(jwk)
    except ValueError:
        raise EnrollFailed("hub_antwoord_ongeldig") from None
    return {
        "kid": jwk["kid"],
        "jwk": {"kty": "OKP", "crv": "Ed25519", "x": jwk["x"]},
        "thumbprint": thumb,
        "pinned_at": now_iso(),
        "source": "enroll",
    }


def check_enroll_response(body: Any, app_id: str, expected_fingerprint: str) -> dict[str, Any]:
    """Alle controles van §3.3 vóór opslaan; onbekende extra velden worden genegeerd."""
    if not isinstance(body, dict):
        raise EnrollFailed("hub_antwoord_ongeldig")
    strings = ("schema_version", "service_id", "app_id", "service_token", "token_type", "hub_issuer",
               "keyset_fingerprint", "jwks_url", "events_inbox_url", "key_rotation_url")  # fmt: skip
    if any(not isinstance(body.get(k), str) for k in strings) or not isinstance(body.get("enrollment_replayed"), bool):
        raise EnrollFailed("hub_antwoord_ongeldig")
    if body["schema_version"].split(".")[0] != "1" or body["app_id"] != app_id:
        raise EnrollFailed("hub_antwoord_ongeldig")
    if (
        body["token_type"] != "Bearer"  # noqa: S105 — tokensoort, geen geheim
        or body["hub_issuer"] != "hub"
        or not SERVICE_TOKEN_RE.match(body["service_token"])
    ):
        raise EnrollFailed("hub_antwoord_ongeldig")
    try:
        uuid.UUID(body["service_id"])
    except ValueError:
        raise EnrollFailed("hub_antwoord_ongeldig") from None
    jwks = body.get("jwks")
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(keys, list) or not keys:
        raise EnrollFailed("hub_antwoord_ongeldig")
    jwt_pins = [_pin(k) for k in keys]
    if len({p["kid"] for p in jwt_pins}) != len(jwt_pins):
        raise EnrollFailed("hub_antwoord_ongeldig")
    policy_pin = _pin(body.get("policy_public_key"))
    # rotation_sequence (nieuw in 1.3): integer ≥ 0; een Hub 1.2 stuurt het niet → 0 (§3.3).
    sequence = body.get("rotation_sequence", 0)
    if type(sequence) is not int or sequence < 0:  # bool telt niet als getal
        raise EnrollFailed("hub_antwoord_ongeldig")
    computed = keyset_fingerprint(keys, [body["policy_public_key"]])
    if computed != body["keyset_fingerprint"]:
        raise EnrollFailed("hub_antwoord_ongeldig")
    if normalize_code(computed) != normalize_code(expected_fingerprint):
        raise EnrollFailed("hub_vingerafdruk_onjuist")
    return {"jwt": jwt_pins, "policy": [policy_pin], "keyset_fingerprint": computed, "rotation_sequence": sequence}


def hub_status_code(status: int) -> str | None:
    """HTTP-uitkomst van ``POST /enroll`` → vaste ``last_error``-code (§3.3, §3.5); ``None`` bij 200."""
    if status == 200:
        return None
    if status == 401:
        return "hub_weigerde"
    if status == 404:
        return "enroll_endpoint_ontbreekt"
    if status in (413, 422):
        return "hub_incompatibel"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "hub_onbereikbaar"
    return "hub_antwoord_ongeldig"


def pending_expired(link: Mapping[str, Any], now: datetime | None = None) -> bool:
    """§3.6 stap 4: 60 min na ``pending.started_at`` zonder succes is de poging definitief mislukt."""
    pending = link.get("pending")
    if not isinstance(pending, dict):
        return False
    try:
        started = datetime.fromisoformat(str(pending.get("started_at")).replace("Z", "+00:00"))
    except ValueError:
        return True
    return ((now or datetime.now(UTC)) - started).total_seconds() > PENDING_MAX_SECONDS


def koppelen_toegestaan(link: Mapping[str, Any]) -> bool:
    """Of het koppelformulier mag (§3.7, §3.9): nooit gekoppeld (``first_linked_at`` leeg), of ontkoppeld op de
    executorpagina. Dat laatste kan alleen na een live geverifieerde schrijfsleutel, en die is dan gewist: tot hij
    opnieuw is ingesteld voert de executor niets uit (BN-1 a, S-P2-020). Nooit bij een onleesbaar bestand."""
    if link.get("_onleesbaar"):
        return False
    return not link.get("first_linked_at") or link.get("state") == "ontkoppeld"


def enroll_with_pairing_code(
    store: HubLinkStore,
    *,
    app_id: str,
    version: str,
    identity_jwk: Mapping[str, str],
    hub_url: str,
    pairing_code: str,
    fingerprint: str,
) -> dict[str, Any]:
    """Koppelen via de statuspagina (eenmalig, vóór de eerste koppeling). Geeft de publieke status terug.

    ``EnrollFailed`` met ``koppelstatus_onleesbaar``, ``al_gekoppeld`` of ``koppelen_bezig`` als er niets naar de Hub
    gaat (§3.7); anders staat de uitkomst in ``last_error`` van de teruggegeven status."""
    secret_hash = hashlib.sha256(normalize_code(pairing_code).encode()).hexdigest()
    try:
        with store.update() as link:
            if not koppelen_toegestaan(link):
                raise EnrollFailed("al_gekoppeld")
            if link.get("pending") is not None and not pending_expired(link):
                raise EnrollFailed("koppelen_bezig")
            link["pending"] = {
                "kind": "koppelcode",
                "secret_sha256": secret_hash,
                "hub_url": hub_url,
                "started_at": now_iso(),
                "attempts": 1,
            }
    except KoppelstatusOnleesbaar:
        raise EnrollFailed("koppelstatus_onleesbaar") from None
    code: str | None = "hub_antwoord_ongeldig"
    pins: dict[str, Any] | None = None
    body: Any = None
    try:
        res = hub_request(
            hub_url,
            "POST",
            "/api/v1/services/enroll",
            body=enroll_request(app_id, pairing_code, version, identity_jwk),
            allow_loopback=store.allow_loopback,
        )
        code = hub_status_code(res.status)
        if code is None:
            pins = check_enroll_response(res.body, app_id, fingerprint)
            body = res.body
    except HubUnreachable:
        code = "hub_onbereikbaar"
    except EnrollFailed as exc:
        code = exc.code
    finally:
        # Altijd afsluiten, ook bij een onverwachte fout: een achtergebleven ``pending`` zou elk volgend verzoek
        # ``koppelen_bezig`` geven.
        with store.update() as link:
            link["pending"] = None  # het adres van een mislukte poging wordt nergens bewaard
            if pins is None or body is None:
                link["last_error"] = {"code": code or "hub_antwoord_ongeldig", "at": now_iso()}
            else:
                at = now_iso()
                if link.get("pins"):
                    link["previous_pins"] = link["pins"]
                link.update(
                    state="gekoppeld",
                    app_id=app_id,
                    hub_url=hub_url,
                    service_id=body["service_id"],
                    via="koppelcode",
                    first_linked_at=link.get("first_linked_at") or at,
                    linked_at=at,
                    confirmed_at=None,
                    service_token=body["service_token"],
                    service_token_last4=body["service_token"][-4:],
                    pins=pins,
                    last_error=None,
                )
    if pins is not None:
        confirm(store)
    return public_status(store.read())


class KeyRotationPoller:
    """§4.5: sleutelrotaties ophalen (≤ elke 15 min; bij een onbekende ``kid`` extra, max. 1× per 30 s).

    De Hub roteert nog niet en geeft ``{"items": []}``. Statements toepassen (handtekening met een gepinde sleutel van
    hetzelfde doel, ``sequence`` zonder gaten) is nog niet gebouwd: een niet-lege lijst stopt daarom het toepassen en
    wordt zichtbaar als ``last_error`` — de pins blijven ongewijzigd (nooit stil vertrouwen toevoegen).
    """

    def __init__(self, store: HubLinkStore, *, min_interval: float = 30.0) -> None:
        self.store, self.min_interval = store, min_interval
        self.last_poll = 0.0
        self.last_result: str | None = None
        self._lock = threading.Lock()

    def poll(self, *, force: bool = False) -> str | None:
        with self._lock:
            now = time.monotonic()
            if not force and now - self.last_poll < self.min_interval:
                return self.last_result
            self.last_poll = now
        link = self.store.read()
        if link.get("state") != "gekoppeld" or not link.get("hub_url"):
            return None
        seq = int((link.get("pins") or {}).get("rotation_sequence") or 0)
        try:
            res = hub_request(
                str(link["hub_url"]),
                "GET",
                f"/api/v1/auth/key-rotations?after={seq}",
                allow_loopback=self.store.allow_loopback,
            )
        except HubUnreachable:
            self.last_result = "hub_onbereikbaar"
            return self.last_result
        items = res.body.get("items") if res.status == 200 and isinstance(res.body, dict) else None
        if not isinstance(items, list):
            self.last_result = "antwoord_ongeldig"
        elif not items:
            self.last_result = "geen_rotaties"
        else:
            self.last_result = "sleutelrotatie_niet_toegepast"
            with self.store.update() as cur:
                cur["last_error"] = {"code": "sleutelrotatie_niet_toegepast", "at": now_iso()}
        return self.last_result

    def trigger_background(self) -> None:
        """Na een onbekende ``kid``: poll op de achtergrond; het verzoek wacht daar niet op."""
        if time.monotonic() - self.last_poll >= self.min_interval:
            threading.Thread(target=self.poll, daemon=True).start()


def confirm(store: HubLinkStore) -> bool:
    """§3.6 stap 3: bevestigen met ``GET /api/v1/services/self``; 401 → ingetrokken (alleen bij 401, nooit bij 5xx)."""
    link = store.read()
    if link.get("state") != "gekoppeld" or not link.get("service_token") or link.get("confirmed_at"):
        return bool(link.get("confirmed_at"))
    try:
        res = hub_request(
            str(link["hub_url"]),
            "GET",
            "/api/v1/services/self",
            bearer=str(link["service_token"]),
            allow_loopback=store.allow_loopback,
        )
    except HubUnreachable:
        return False
    with store.update() as cur:
        if cur.get("service_token") != link.get("service_token"):
            return False
        if res.status == 200 and isinstance(res.body, dict) and res.body.get("service_id") == cur.get("service_id"):
            cur["confirmed_at"] = now_iso()
            return True
        if res.status == 401:
            cur.update(
                state="ingetrokken", service_token=None, last_error={"code": "ingetrokken_door_hub", "at": now_iso()}
            )
    return False


# ------------------------------------------------------------------ inkomende Hub-JWT (§4.3, §4.5, §4.7)
class AuthFailed(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def bearer_token(authorization: str | None) -> str:
    """``Authorization``-header → token; geen header, een ander schema dan ``Bearer`` of een lege waarde →
    ``invalid_token`` (§4.7)."""
    scheme, _sep, value = (authorization or "").strip().partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        raise AuthFailed("invalid_token")
    return value.strip()


def verify_hub_authorization(
    authorization: str | None, link: Mapping[str, Any], *, audience: str, now: int | None = None
) -> dict[str, Any]:
    """§4.7 vanaf de header: eerst ``state`` (ook zonder header: ``not_linked``/``revoked``), dan de tokensoort."""
    _check_state(link)
    return verify_hub_jwt(bearer_token(authorization), link, audience=audience, now=now)


def _check_state(link: Mapping[str, Any]) -> None:
    state = link.get("state")
    if state == "ingetrokken":
        raise AuthFailed("revoked")
    if state != "gekoppeld" or not link.get("pins") or link.get("_onleesbaar"):
        raise AuthFailed("not_linked")  # ook een onleesbaar koppelbestand (§3.5, fail-closed)


def verify_hub_jwt(token: str, link: Mapping[str, Any], *, audience: str, now: int | None = None) -> dict[str, Any]:
    """Controlevolgorde van §4.7: state → tokensoort → handtekening/kid → claims → token_use → jti.

    ``aud`` moet precies één string zijn (§4.2): een lijst — ook met de eigen ``app_id`` erin — is ``invalid_token``.
    Een JWS-header zonder ``kid`` is ``unknown_key``."""
    _check_state(link)
    if not token:
        raise AuthFailed("invalid_token")
    if token.startswith("svc_"):
        raise AuthFailed("service_token_not_accepted")
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(b64url_decode(header_b64))
        claims = json.loads(b64url_decode(payload_b64))
        signature = b64url_decode(sig_b64)
    except ValueError:
        raise AuthFailed("invalid_token") from None
    if not isinstance(header, dict) or not isinstance(claims, dict) or header.get("alg") != "EdDSA":
        raise AuthFailed("invalid_token")
    kid = header.get("kid")
    pin = next((p for p in link["pins"].get("jwt", []) if isinstance(kid, str) and p.get("kid") == kid), None)
    if pin is None:
        raise AuthFailed("unknown_key")
    try:
        key = Ed25519PublicKey.from_public_bytes(b64url_decode(pin["jwk"]["x"]))
        key.verify(signature, f"{header_b64}.{payload_b64}".encode())
    except (InvalidSignature, ValueError):
        raise AuthFailed("invalid_token") from None
    t = int(datetime.now(UTC).timestamp()) if now is None else now
    numbers = ("iat", "nbf", "exp")
    if any(type(claims.get(k)) is not int for k in numbers) or claims.get("iss") != "hub":  # bool telt niet als getal
        raise AuthFailed("invalid_token")
    aud = claims.get("aud")
    if not isinstance(aud, str) or aud != audience:  # ook een lijst met de eigen app_id erin (§4.2)
        raise AuthFailed("invalid_token")
    if claims["exp"] - claims["iat"] > 120 or claims["exp"] < claims["iat"]:
        raise AuthFailed("invalid_token")
    if claims["nbf"] > t + CLOCK_SKEW or claims["iat"] > t + CLOCK_SKEW:  # nog niet geldig of uit de toekomst
        raise AuthFailed("invalid_token")
    if claims["exp"] + CLOCK_SKEW < t:
        raise AuthFailed("token_expired")
    use, roles = claims.get("token_use"), claims.get("roles")
    if use == "hub_service":
        if claims.get("sub") != "hub" or roles != ["service"] or claims.get("service_id") != link.get("service_id"):
            raise AuthFailed("token_use_invalid")
    elif use == "user":
        if not isinstance(roles, list) or "service" in roles:
            raise AuthFailed("token_use_invalid")
    else:
        raise AuthFailed("token_use_invalid")
    if not isinstance(claims.get("jti"), str) or not claims["jti"]:
        raise AuthFailed("jti_missing")
    return claims
