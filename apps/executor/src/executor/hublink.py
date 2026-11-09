"""Koppeling van de executor met de Hub (contract 1.2 §3.2–§3.9, §4.5, §4.7).

- Koppelen alleen met een **koppelcode (30 min) + Hub-vingerafdruk** op de eigen statuspagina (§3.9); de Hub geeft voor
  de executor geen enrollment-token uit. Daarna geen koppelformulier meer: ontkoppelen/opnieuw koppelen vraagt een live
  geverifieerde TrueNAS-schrijfkey tegen het vastgelegde NAS-adres + certificaat, en die bestaat pas in P2.
- Opslag in ``/appdata/secrets/hub-link.json`` (0600, atomair, onder ``hub-link.lock``), nooit in een database.
- Hub-sleutels worden gepind uit het enroll-antwoord; een via HTTP opgehaalde JWKS voegt nooit vertrouwen toe.
- Aanroepen naar de Hub: ``http.client`` (geen redirects, geen proxy-omgeving), 5 s connect / 15 s read.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import http.client
import ipaddress
import json
import os
import re
import uuid
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA_VERSION = "1.2"
FILE_NAME = "hub-link.json"
LOCK_NAME = "hub-link.lock"
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
KEYSET_PREFIX = "jl-hub-keyset-v1"
SERVICE_TOKEN_RE = re.compile(r"^svc_[A-Za-z0-9_-]{43}$")
MAX_USED_TOKENS = 20
CLOCK_SKEW = 30

# Vaste meldingen bij last_error (contract 1.2 §3.5); de code is voor machines, de tekst voor mensen.
ERRORS_NL = {
    "hub_onbereikbaar": "De Hub was niet bereikbaar. Controleer het adres en probeer het opnieuw.",
    "hub_weigerde": "De Hub weigerde de koppelcode (onbekend, verlopen of al gebruikt). Maak in de Hub een nieuwe.",
    "hub_antwoord_ongeldig": "Het antwoord van de Hub voldeed niet aan het contract; er is niets opgeslagen.",
    "hub_vingerafdruk_onjuist": "De vingerafdruk klopt niet met de sleutels van deze Hub; er is niets opgeslagen.",
    "enroll_endpoint_ontbreekt": "Deze Hub-versie kent aanmelden niet.",
    "rate_limited": "Te veel pogingen; wacht even en probeer het dan opnieuw.",
    "koppelen_onderbroken": "Het koppelen is onderbroken door een herstart. Voer de koppelcode opnieuw in.",
    "ingetrokken_door_hub": "De Hub heeft deze koppeling ingetrokken; opnieuw koppelen gaat via de Hub.",
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


def keyset_fingerprint(jwt_keys: list[Mapping[str, Any]], policy_key: Mapping[str, Any]) -> str:
    thumbs = sorted(jwk_thumbprint(k) for k in jwt_keys)
    if not thumbs:
        raise ValueError("minstens één JWT-sleutel nodig")
    text = f"{KEYSET_PREFIX}\njwt:{','.join(thumbs)}\npolicy:{jwk_thumbprint(policy_key)}"
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
    n = normalize_code(value)
    return len(value) <= 32 and len(n) == 16 and all(ch in CROCKFORD for ch in n)


# ------------------------------------------------------------------ Hub-adres (§3.2)
def validate_hub_url(value: str, *, allow_loopback: bool = False) -> str:
    """``http(s)://<host>[:<poort>]`` zonder pad, query, fragment of inloggegevens; geen loopback/link-local/0.0.0.0."""
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("adres moet beginnen met http:// of https://")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("alleen http(s)://host[:poort], zonder pad, query of inloggegevens")
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("ongeldige poort") from exc
    host = parts.hostname
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        addr = None
        if host.lower() == "localhost" and not allow_loopback:
            raise ValueError("loopback is niet toegestaan") from None
    if addr is not None:
        if addr.is_unspecified or addr.is_link_local:
            raise ValueError("dit adres is niet toegestaan")
        if addr.is_loopback and not allow_loopback:
            raise ValueError("loopback is niet toegestaan")
    netloc = f"[{host}]" if addr is not None and addr.version == 6 else host
    return f"{parts.scheme}://{netloc}" + (f":{port}" if port else "")


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


class HubLinkStore:
    def __init__(self, secrets_dir: Path) -> None:
        self.dir = secrets_dir
        self.path = secrets_dir / FILE_NAME
        self.lock_path = secrets_dir / LOCK_NAME

    def read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return empty_link()
        if not isinstance(data, dict):
            raise ValueError("hub-link.json is geen object")
        return {**empty_link(), **data}

    @contextlib.contextmanager
    def update(self) -> Iterator[dict[str, Any]]:
        """Lezen-wijzigen-schrijven onder een exclusieve vergrendeling; atomair vervangen (O_EXCL → fsync → rename)."""
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = self.read()
            yield data
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


def public_status(link: Mapping[str, Any]) -> dict[str, Any]:
    """Witte lijst (§3.5): nooit service_token of pending.secret_sha256."""
    out = {k: link.get(k) for k in PUBLIC_FIELDS}
    pins = link.get("pins") or {}
    out["koppelen_bezig"] = link.get("pending") is not None
    out["keyset_fingerprint"] = pins.get("keyset_fingerprint") if link.get("state") == "gekoppeld" else None
    err = link.get("last_error")
    out["last_error"] = None if not err else {"code": err.get("code"), "melding": ERRORS_NL.get(str(err.get("code")))}
    return out


def resume_after_restart(store: HubLinkStore) -> None:
    """§3.6 stap 5: een koppelcode is na een herstart weg → ``koppelen_onderbroken``."""
    if not store.path.exists() or store.read().get("pending") is None:
        return
    with store.update() as link:
        if link.get("pending") is not None:
            link["pending"] = None
            link["last_error"] = {"code": "koppelen_onderbroken", "at": now_iso()}


# ------------------------------------------------------------------ HTTP naar de Hub
@dataclass
class HubResponse:
    status: int
    body: Any
    retry_after: str | None = None


class HubUnreachable(Exception):
    pass


def hub_request(
    hub_url: str,
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    bearer: str | None = None,
    connect_timeout: float = 5.0,
    read_timeout: float = 15.0,
) -> HubResponse:
    parts = urlsplit(hub_url)
    conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(parts.hostname or "", parts.port, timeout=connect_timeout)
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
    computed = keyset_fingerprint(keys, body["policy_public_key"])
    if computed != body["keyset_fingerprint"]:
        raise EnrollFailed("hub_antwoord_ongeldig")
    if normalize_code(computed) != normalize_code(expected_fingerprint):
        raise EnrollFailed("hub_vingerafdruk_onjuist")
    return {"jwt": jwt_pins, "policy": [policy_pin], "keyset_fingerprint": computed, "rotation_sequence": 0}


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
    """Koppelen via de statuspagina (eenmalig, vóór de eerste koppeling). Geeft de publieke status terug."""
    secret_hash = hashlib.sha256(normalize_code(pairing_code).encode()).hexdigest()
    with store.update() as link:
        if link.get("first_linked_at"):
            raise EnrollFailed("al_gekoppeld")
        link["pending"] = {
            "kind": "koppelcode",
            "secret_sha256": secret_hash,
            "hub_url": hub_url,
            "started_at": now_iso(),
            "attempts": 1,
        }
    code = None
    pins: dict[str, Any] | None = None
    body: Any = None
    try:
        res = hub_request(
            hub_url, "POST", "/api/v1/services/enroll", body=enroll_request(app_id, pairing_code, version, identity_jwk)
        )
        if res.status == 200:
            pins = check_enroll_response(res.body, app_id, fingerprint)
            body = res.body
        elif res.status == 404:
            code = "enroll_endpoint_ontbreekt"
        elif res.status == 429:
            code = "rate_limited"
        elif res.status >= 500:
            code = "hub_onbereikbaar"
        else:  # 401/413/422: definitief voor deze code
            code = "hub_weigerde"
    except HubUnreachable:
        code = "hub_onbereikbaar"
    except EnrollFailed as exc:
        code = exc.code
    with store.update() as link:
        link["pending"] = None  # het adres van een mislukte poging wordt nergens bewaard
        if pins is None or body is None:
            link["last_error"] = {"code": code or "hub_antwoord_ongeldig", "at": now_iso()}
            return public_status(link)
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
    confirm(store)
    return public_status(store.read())


def confirm(store: HubLinkStore) -> bool:
    """§3.6 stap 3: bevestigen met ``GET /api/v1/services/self``; 401 → ingetrokken (alleen bij 401, nooit bij 5xx)."""
    link = store.read()
    if link.get("state") != "gekoppeld" or not link.get("service_token") or link.get("confirmed_at"):
        return bool(link.get("confirmed_at"))
    try:
        res = hub_request(str(link["hub_url"]), "GET", "/api/v1/services/self", bearer=str(link["service_token"]))
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


def verify_hub_jwt(token: str, link: Mapping[str, Any], *, audience: str, now: int | None = None) -> dict[str, Any]:
    """Controlevolgorde van §4.7: state → tokensoort → handtekening/kid → claims → token_use → jti."""
    state = link.get("state")
    if state == "ingetrokken":
        raise AuthFailed("revoked")
    if state != "gekoppeld" or not link.get("pins"):
        raise AuthFailed("not_linked")
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
    pin = next((p for p in link["pins"].get("jwt", []) if p.get("kid") == header.get("kid")), None)
    if pin is None:
        raise AuthFailed("unknown_key")
    try:
        key = Ed25519PublicKey.from_public_bytes(b64url_decode(pin["jwk"]["x"]))
        key.verify(signature, f"{header_b64}.{payload_b64}".encode())
    except (InvalidSignature, ValueError):
        raise AuthFailed("invalid_token") from None
    t = int(datetime.now(UTC).timestamp()) if now is None else now
    numbers = ("iat", "nbf", "exp")
    if any(not isinstance(claims.get(k), int) for k in numbers) or claims.get("iss") != "hub":
        raise AuthFailed("invalid_token")
    if claims.get("aud") != audience or claims["exp"] - claims["iat"] > 120 or claims["nbf"] > t + CLOCK_SKEW:
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
