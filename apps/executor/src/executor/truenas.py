"""Synchrone JSON-RPC 2.0-client van de executor voor TrueNAS (``wss://<NAS>/api/current``).

Regels (contract 1.3 §3.9 en §8, ADR-0030):

- Uitsluitend ``wss://``. Het certificaat wordt vertrouwd op de **vastgelegde SHA-256-vingerafdruk**, niet op een CA:
  de vingerafdruk wordt na de TLS-handdruk en vóór het versturen van de sleutel exact vergeleken. Wijkt hij af, dan
  gaat er niets geheims over de lijn (``certificaat_gewijzigd``).
- Er is geen vrije doorgeefroute: alleen de leesmethoden hieronder en de methoden die het beleid noemt
  (``policy/acties.yaml`` → ``truenas``) kunnen worden aangeroepen. Elke andere naam is ``methode_niet_toegestaan``.
- Elke fout wordt een :class:`NasFout` met een stabiele code; niets wordt stil overgeslagen.

Alleen tegen de in-repo fake getest: NIET GEVALIDEERD (echte NAS).
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import ipaddress
import itertools
import json
import socket
import ssl
import time
from types import TracebackType
from typing import Any

from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidURI
from websockets.sync.client import ClientConnection, connect

API_PATH = "/api/current"
MAX_MESSAGE_BYTES = 64 * 1024 * 1024
# Lezen (readback) en inloggen. ``app.config`` kan geheimen bevatten: alleen de executor leest het, voor terugzetten.
READ_METHODS: frozenset[str] = frozenset(
    {
        "auth.login_with_api_key",
        "auth.me",
        "core.get_methods",
        "core.get_jobs",
        "app.query",
        "app.image.query",
        "app.config",
        "pool.query",
        "pool.dataset.query",
        "pool.snapshot.query",
        "zfs.snapshot.query",
    }
)
# Rollen waarmee een sleutel als "met schrijfrechten" telt (§3.9). Alleen-lezen (READONLY_ADMIN, *_READ) telt niet.
WRITE_ROLES: frozenset[str] = frozenset({"FULL_ADMIN", "APPS_WRITE", "SNAPSHOT_WRITE"})


class NasFout(Exception):
    """Fout met een stabiele code. ``detail`` is tekst van TrueNAS (nooit een geheim) en gaat alleen het journaal in."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail[:500]


def _context() -> ssl.SSLContext:
    # Hostnaam en CA worden niet gecontroleerd: de vingerafdruk wordt na de handdruk exact vergeleken, vóór er iets
    # geheims wordt verstuurd.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def display_fingerprint(fp: str) -> str:
    return ":".join(fp[i : i + 2] for i in range(0, len(fp), 2)).upper()


def ws_url(host: str, port: int) -> str:
    try:
        if isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address):
            host = f"[{host}]"
    except ValueError:
        pass
    return f"wss://{host}" + ("" if port == 443 else f":{port}") + API_PATH


def fetch_fingerprint(host: str, port: int, *, timeout: float = 5.0) -> str:
    """Alleen de TLS-handdruk: SHA-256 van het certificaat (64 hex-tekens). Er wordt niets verstuurd."""
    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as raw,
            _context().wrap_socket(raw, server_hostname=host) as tls,
        ):
            der = tls.getpeercert(binary_form=True)
    except (OSError, ssl.SSLError, ValueError) as exc:
        raise NasFout("truenas_onbereikbaar", type(exc).__name__) from None
    if not der:
        raise NasFout("truenas_onbereikbaar", "geen certificaat")
    return hashlib.sha256(der).hexdigest()


def has_write_role(roles: list[str]) -> bool:
    return any(r in WRITE_ROLES for r in roles)


class NasClient:
    """Eén verbinding; gebruik als context manager. ``allowed`` = de schrijfmethoden uit het beleid."""

    def __init__(
        self, host: str, port: int, fingerprint: str, *, allowed: frozenset[str] = frozenset(), timeout: float = 15.0
    ) -> None:
        self.host, self.port, self.fingerprint = host, port, fingerprint
        self.allowed = READ_METHODS | allowed
        self.timeout = timeout
        self._ids = itertools.count(1)
        self._ws: ClientConnection | None = None

    def __enter__(self) -> NasClient:
        self.open()
        return self

    def __exit__(self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None) -> None:
        self.close()

    def open(self) -> None:
        try:
            ws = connect(
                ws_url(self.host, self.port),
                ssl=_context(),
                open_timeout=self.timeout,
                close_timeout=2,
                max_size=MAX_MESSAGE_BYTES,
                legacy=True,  # de verbinding leeft langer dan één blok: open() … close()
            )
        except (OSError, ssl.SSLError, TimeoutError, InvalidHandshake, InvalidURI, ValueError) as exc:
            raise NasFout("truenas_onbereikbaar", type(exc).__name__) from None
        der: bytes | None = None
        with contextlib.suppress(AttributeError, ValueError, OSError):
            der = ws.socket.getpeercert(binary_form=True)  # type: ignore[attr-defined]
        found = hashlib.sha256(der).hexdigest() if der else ""
        if not found or not hmac.compare_digest(found, self.fingerprint):
            with contextlib.suppress(Exception):
                ws.close()
            raise NasFout("certificaat_gewijzigd")
        self._ws = ws

    def close(self) -> None:
        if self._ws is not None:
            with contextlib.suppress(Exception):
                self._ws.close()
            self._ws = None

    def call(self, method: str, *params: Any, timeout: float | None = None) -> Any:
        if method not in self.allowed:
            raise NasFout("methode_niet_toegestaan", method)
        if self._ws is None:
            raise NasFout("truenas_onbereikbaar", "geen verbinding")
        mid = next(self._ids)
        deadline = time.monotonic() + (timeout or self.timeout)
        try:
            self._ws.send(json.dumps({"jsonrpc": "2.0", "id": mid, "method": method, "params": list(params)}))
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise NasFout("truenas_timeout", method)
                try:
                    raw = self._ws.recv(timeout=left)
                except TimeoutError:
                    raise NasFout("truenas_timeout", method) from None
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(msg, dict) or msg.get("id") != mid:
                    continue  # meldingen en events van TrueNAS horen niet bij deze aanroep
                err = msg.get("error")
                if err is not None:
                    data = err.get("data") if isinstance(err, dict) else None
                    data = data if isinstance(data, dict) else {}
                    naam = str(data.get("errname") or "")
                    reden = str(data.get("reason") or (err.get("message") if isinstance(err, dict) else "") or "")
                    code = (
                        "truenas_geen_toegang" if naam in ("EACCES", "EPERM", "ENOTAUTHENTICATED") else "truenas_fout"
                    )
                    raise NasFout(code, f"{method}: [{naam}] {reden}" if naam else f"{method}: {reden}")
                return msg.get("result")
        except (ConnectionClosed, OSError) as exc:
            self.close()
            raise NasFout("truenas_onbereikbaar", type(exc).__name__) from None

    def login(self, api_key: str) -> None:
        if self.call("auth.login_with_api_key", api_key) is not True:
            raise NasFout("sleutel_geweigerd")

    def roles(self) -> list[str]:
        me = self.call("auth.me")
        priv = me.get("privilege") if isinstance(me, dict) else None
        roles: Any = priv.get("roles") if isinstance(priv, dict) else None
        if isinstance(roles, dict):  # TrueNAS geeft een verzameling als {"$set": [...]}
            roles = roles.get("$set")
        return sorted(str(r) for r in roles) if isinstance(roles, list) else []

    def methods(self) -> frozenset[str]:
        got = self.call("core.get_methods")
        return frozenset(str(m) for m in got) if isinstance(got, dict | list) else frozenset()

    def job(self, method: str, *params: Any, timeout: float, poll: float = 1.0) -> Any:
        """Job-methode starten en wachten op het einde (``core.get_jobs``). ``job_mislukt`` bij FAILED/ABORTED,
        ``job_timeout`` als de job na ``timeout`` seconden nog loopt (de uitkomst is dan onbekend)."""
        job_id = self.call(method, *params)
        if not isinstance(job_id, int) or isinstance(job_id, bool):
            return job_id  # geen job: het resultaat zelf
        deadline = time.monotonic() + timeout
        while True:
            rows = self.call("core.get_jobs", [["id", "=", job_id]])
            job = next((j for j in rows or [] if isinstance(j, dict) and j.get("id") == job_id), None)
            state = str(job.get("state") or "") if job else ""
            if state == "SUCCESS" and job is not None:
                return job.get("result")
            if state in ("FAILED", "ABORTED"):
                raise NasFout("job_mislukt", f"{method}: {(job or {}).get('error') or state}")
            if time.monotonic() >= deadline:
                raise NasFout("job_timeout", method)
            time.sleep(poll)


def verify_key(
    host: str, port: int, fingerprint: str, api_key: str, *, timeout: float = 15.0
) -> tuple[list[str], frozenset[str]]:
    """Live verifiëren (§3.9): verbinding met de vastgelegde vingerafdruk → ``auth.login_with_api_key`` → rolcontrole →
    ``core.get_methods``. Geeft (rollen, methoden); ``schrijfrechten_ontbreken`` bij een alleen-lezen-sleutel."""
    with NasClient(host, port, fingerprint, timeout=timeout) as nas:
        nas.login(api_key)
        roles = nas.roles()
        if not has_write_role(roles):
            raise NasFout("schrijfrechten_ontbreken")
        return roles, nas.methods()
