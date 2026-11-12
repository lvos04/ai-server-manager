"""Synchrone JSON-RPC 2.0-client van de executor voor TrueNAS (``wss://<NAS>/api/current``).

Regels (contract 1.3 §3.9 en §8, ADR-0030):

- Uitsluitend ``wss://``. Het certificaat wordt vertrouwd op de **vastgelegde SHA-256-vingerafdruk**, niet op een CA:
  de vingerafdruk wordt na de TLS-handdruk en vóór het versturen van de sleutel exact vergeleken. Wijkt hij af, dan
  gaat er niets geheims over de lijn (``certificaat_gewijzigd``).
- Er is geen vrije doorgeefroute: alleen de leesmethoden hieronder en de methoden die het beleid noemt
  (``policy/acties.yaml`` → ``truenas``) kunnen worden aangeroepen. Elke andere naam is ``methode_niet_toegestaan``.
- Elke fout wordt een :class:`NasFout` met een stabiele code; niets wordt stil overgeslagen.
- De verbinding draait op een **eigen event loop in één eigen thread**: alleen die thread raakt het TLS-object aan.
  De synchrone websockets-client leest en schrijft vanuit twee threads tegelijk op hetzelfde TLS-object; onder
  belasting liep de handdruk daardoor af en toe vast (gemeten tegen de fake: enkele op de 1600 verbindingen, met de
  asyncio-client nul). Voor de aanroeper blijft de client synchroon. Nooit via een proxy uit de omgeving.
- De verbinding logt via een **eigen logger die vast op INFO staat** (:data:`WS_LOGGER`). websockets logt op DEBUG elk
  frame, ook ``auth.login_with_api_key`` met (het einde van) de sleutel en waarden van ``app.create``; zo komt dat
  nooit in een log, ook niet als de root-logger op DEBUG staat (R-VEILIG-4, S-P2-020).
- Een sleutel telt alleen als schrijfsleutel als zijn rollen de app- **én** snapshotacties van de allowlist dekken:
  ``FULL_ADMIN``, of ``APPS_WRITE`` samen met ``SNAPSHOT_WRITE`` (R-TECH-1, S-P2-020). De rolnamen komen uit de publieke
  API-beschrijving: NIET GEVALIDEERD (echte NAS).

Alleen tegen de in-repo fake getest: NIET GEVALIDEERD (echte NAS).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import ipaddress
import itertools
import json
import logging
import socket
import ssl
import threading
import time
from collections.abc import Coroutine
from types import TracebackType
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, WebSocketException

API_PATH = "/api/current"
MAX_MESSAGE_BYTES = 64 * 1024 * 1024
# Vangnet bovenop de eigen tijdslimiet van een aanroep: zo lang wacht de aanroeper hooguit extra op de eigen thread.
RUN_GRACE_SECONDS = 5.0
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
# Rollen met schrijfrechten (§3.9). Alleen-lezen (READONLY_ADMIN, *_READ) telt niet. Voor de executor moet een sleutel
# de hele allowlist dekken (app.* én snapshots): FULL_ADMIN, of APPS_WRITE samen met SNAPSHOT_WRITE. Rolnamen:
# NIET GEVALIDEERD (echte NAS).
WRITE_ROLES: frozenset[str] = frozenset({"FULL_ADMIN", "APPS_WRITE", "SNAPSHOT_WRITE"})
ALLOWLIST_ROLES: frozenset[str] = frozenset({"APPS_WRITE", "SNAPSHOT_WRITE"})
# Eigen logger voor de websocket-verbinding, vast op INFO: geen DEBUG-frames (met de sleutel) in een log.
WS_LOGGER = logging.getLogger("executor.truenas.websockets")
WS_LOGGER.setLevel(logging.INFO)


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


def covers_allowlist(roles: list[str]) -> bool:
    """Of de rollen de app- én snapshotacties van de allowlist dekken (R-TECH-1)."""
    return "FULL_ADMIN" in roles or set(roles) >= ALLOWLIST_ROLES


class NasClient:
    """Eén verbinding; gebruik als context manager. ``allowed`` = de schrijfmethoden uit het beleid.

    Synchroon voor de aanroeper, niet bedoeld voor gebruik vanuit meerdere threads tegelijk. De verbinding zelf leeft
    op een eigen event loop in een eigen thread (zie de kop van dit bestand).
    """

    def __init__(
        self, host: str, port: int, fingerprint: str, *, allowed: frozenset[str] = frozenset(), timeout: float = 15.0
    ) -> None:
        self.host, self.port, self.fingerprint = host, port, fingerprint
        self.allowed = READ_METHODS | allowed
        self.timeout = timeout
        self._ids = itertools.count(1)
        self._ws: ClientConnection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> NasClient:
        self.open()
        return self

    def __exit__(self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None) -> None:
        self.close()

    # ------------------------------------------------------------ eigen event loop
    def _run[T](self, coro: Coroutine[Any, Any, T], limit: float) -> T:
        """Voer ``coro`` uit op de eigen loop en wacht hooguit ``limit`` seconden op het resultaat."""
        loop = self._loop
        if loop is None:
            coro.close()
            raise NasFout("truenas_onbereikbaar", "geen verbinding")
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return fut.result(limit)
        except TimeoutError:
            fut.cancel()
            raise

    def _stop_loop(self) -> None:
        loop, thread = self._loop, self._thread
        self._loop = self._thread = None
        if loop is None:
            return

        async def opruimen() -> None:
            taken = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for t in taken:
                t.cancel()
            await asyncio.gather(*taken, return_exceptions=True)

        with contextlib.suppress(Exception):
            asyncio.run_coroutine_threadsafe(opruimen(), loop).result(RUN_GRACE_SECONDS)
        loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(RUN_GRACE_SECONDS)
        if not loop.is_running():
            loop.close()

    async def _open(self) -> ClientConnection:
        ws = await connect(
            ws_url(self.host, self.port),
            ssl=_context(),
            open_timeout=self.timeout,
            close_timeout=2,
            max_size=MAX_MESSAGE_BYTES,
            proxy=None,  # LAN-verbinding; nooit via een proxy uit de omgeving
            user_agent_header="ai-server-manager-executor",
            ping_interval=None,
            logger=WS_LOGGER,  # vast op INFO: nooit DEBUG-frames met de sleutel (R-VEILIG-4)
        )
        # De vingerafdruk wordt hier, op de thread van de loop, gelezen en vergeleken: vóór er iets geheims gaat.
        sslobj = ws.transport.get_extra_info("ssl_object")
        der = sslobj.getpeercert(binary_form=True) if sslobj is not None else None
        found = hashlib.sha256(der).hexdigest() if der else ""
        if not found or not hmac.compare_digest(found, self.fingerprint):
            with contextlib.suppress(Exception):
                await ws.close()
            raise NasFout("certificaat_gewijzigd")
        return ws

    @staticmethod
    async def _exchange(ws: ClientConnection, payload: str, mid: int, limit: float) -> dict[str, Any]:
        async with asyncio.timeout(limit):
            await ws.send(payload)
            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == mid:
                    return msg
                # meldingen en events van TrueNAS horen niet bij deze aanroep

    # ------------------------------------------------------------ verbinding
    def open(self) -> None:
        self.close()
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, name="nas-client", daemon=True)
        thread.start()
        self._loop, self._thread = loop, thread
        try:
            self._ws = self._run(self._open(), self.timeout + RUN_GRACE_SECONDS)
        except NasFout:
            self._stop_loop()
            raise
        except (OSError, ssl.SSLError, TimeoutError, WebSocketException, ValueError, EOFError) as exc:
            self._stop_loop()
            raise NasFout("truenas_onbereikbaar", type(exc).__name__) from None
        except BaseException:
            self._stop_loop()
            raise

    def close(self) -> None:
        ws, self._ws = self._ws, None
        if ws is not None and self._loop is not None:
            with contextlib.suppress(Exception):
                self._run(ws.close(), RUN_GRACE_SECONDS)
        self._stop_loop()

    def call(self, method: str, *params: Any, timeout: float | None = None) -> Any:
        if method not in self.allowed:
            raise NasFout("methode_niet_toegestaan", method)
        ws = self._ws
        if ws is None or self._loop is None:
            raise NasFout("truenas_onbereikbaar", "geen verbinding")
        mid = next(self._ids)
        limit = timeout or self.timeout
        payload = json.dumps({"jsonrpc": "2.0", "id": mid, "method": method, "params": list(params)})
        try:
            msg = self._run(self._exchange(ws, payload, mid, limit), limit + RUN_GRACE_SECONDS)
        except TimeoutError:
            raise NasFout("truenas_timeout", method) from None
        except (ConnectionClosed, OSError) as exc:
            self.close()
            raise NasFout("truenas_onbereikbaar", type(exc).__name__) from None
        err = msg.get("error")
        if err is not None:
            data = err.get("data") if isinstance(err, dict) else None
            data = data if isinstance(data, dict) else {}
            naam = str(data.get("errname") or "")
            reden = str(data.get("reason") or (err.get("message") if isinstance(err, dict) else "") or "")
            code = "truenas_geen_toegang" if naam in ("EACCES", "EPERM", "ENOTAUTHENTICATED") else "truenas_fout"
            raise NasFout(code, f"{method}: [{naam}] {reden}" if naam else f"{method}: {reden}")
        return msg.get("result")

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
    ``core.get_methods``. Geeft (rollen, methoden); ``schrijfrechten_ontbreken`` bij een alleen-lezen-sleutel en
    ``schrijfrechten_onvolledig`` als de rollen niet de app- én snapshotacties dekken (R-TECH-1).

    ``core.get_methods`` is hier alleen een controle dat de sleutel die methode mag aanroepen (faalt de aanroep, dan
    wordt de sleutel geweigerd); de aanroepers gebruiken de lijst niet. Bij elke uitvoering vraagt de executor de
    methoden opnieuw op (R-TECH-7, ADR-0030 besluit 13 en 15)."""
    with NasClient(host, port, fingerprint, timeout=timeout) as nas:
        nas.login(api_key)
        roles = nas.roles()
        if not has_write_role(roles):
            raise NasFout("schrijfrechten_ontbreken")
        if not covers_allowlist(roles):
            raise NasFout("schrijfrechten_onvolledig")
        return roles, nas.methods()
