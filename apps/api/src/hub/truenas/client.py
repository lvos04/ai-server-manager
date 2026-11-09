"""Alleen-lezen JSON-RPC 2.0-client voor de TrueNAS-WebSocket-API (``wss://<NAS>/api/current``).

Veiligheidsregels (contract §8, ADR-0003):
- Uitsluitend ``wss://``. TrueNAS trekt API-keys die over onversleuteld HTTP worden gebruikt zelf in; bovendien zou de
  key dan leesbaar over het LAN gaan.
- TLS wordt standaard geverifieerd (systeem-CA's, optioneel een extra CA-bestand). Een zelfondertekend certificaat werkt
  alleen na **expliciete bevestiging van de SHA-256-vingerafdruk** door een beheerder; de vingerafdruk wordt na de
  TLS-handdruk en vóór het versturen van de API-key gecontroleerd.
- Alleen methoden uit ``READ_ONLY_METHODS`` kunnen worden aangeroepen; elke andere methode is een programmeerfout.
- Elke fout wordt een ``TrueNASError`` met ``reason_code``; niets wordt stil overgeslagen.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import ipaddress
import itertools
import json
import socket
import ssl
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Literal
from urllib.parse import urlsplit

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus, InvalidURI

from hub.truenas.messages import message

READ_ONLY_METHODS: frozenset[str] = frozenset(
    {
        "auth.login_with_api_key",
        "auth.me",
        "core.get_methods",
        "system.version",
        "system.info",
        "pool.query",
        "pool.dataset.query",
        "app.query",
        "app.image.query",
        "app.gpu_choices",
        "device.get_info",
        "disk.query",
        "smart.test.results",
        "pool.snapshottask.query",
        "pool.snapshot.query",
        "zfs.snapshot.query",
        "cloudsync.query",
        "replication.query",
        "alert.list",
        "network.general.summary",
        "interface.query",
        # Abonneren op een alleen-lezen event source (reporting.realtime); verandert niets op de NAS.
        "core.subscribe",
        "core.unsubscribe",
    }
)
# Event sources die de Hub mag volgen (alleen lezen; rol REPORTING_READ).
READ_ONLY_EVENTS: frozenset[str] = frozenset({"reporting.realtime"})

API_PATH = "/api/current"
MAX_MESSAGE_BYTES = 64 * 1024 * 1024  # app.query/pool.dataset.query kunnen groot zijn


class TrueNASError(Exception):
    def __init__(self, reason_code: str, detail: str = "", details: dict[str, Any] | None = None) -> None:
        super().__init__(f"{reason_code}: {detail or message(reason_code)}")
        self.reason_code = reason_code
        self.detail = detail
        self.details = details or {}


def normalize_fingerprint(value: str) -> str:
    """``AB:CD:…`` of ``abcd…`` → 64 kleine hex-tekens; ongeldig → ValueError."""
    cleaned = "".join(ch for ch in value.strip().lower() if ch not in ": -")
    if len(cleaned) != 64 or any(ch not in "0123456789abcdef" for ch in cleaned):
        raise ValueError("vingerafdruk moet een SHA-256-waarde zijn (64 hex-tekens)")
    return cleaned


def display_fingerprint(fp: str) -> str:
    return ":".join(fp[i : i + 2] for i in range(0, len(fp), 2)).upper()


def validate_host(host: str) -> str:
    """NAS-adres: IP-adres of hostnaam, zonder schema/pad/poort."""
    host = host.strip()
    if not host or len(host) > 253:
        raise ValueError("NAS-adres is leeg of te lang")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.rstrip(".").split(".")
    for label in labels:
        if not label or len(label) > 63 or not all(ch.isalnum() or ch == "-" for ch in label) or label[0] == "-":
            raise ValueError("NAS-adres moet een IP-adres of geldige hostnaam zijn (zonder http:// of poort)")
    return host


def build_ws_url(host: str, https_port: int | None) -> str:
    host = validate_host(host)
    try:
        if isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address):
            host = f"[{host}]"
    except ValueError:
        pass
    port = "" if https_port in (None, 443) else f":{https_port}"
    return f"wss://{host}{port}{API_PATH}"


@dataclass(frozen=True)
class TLSSettings:
    pinned_fingerprint: str | None = None  # alleen na expliciete bevestiging
    extra_ca_file: Path | None = None


def _verify_context(extra_ca: Path | None) -> ssl.SSLContext:
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    if extra_ca is not None:
        ctx.load_verify_locations(cafile=str(extra_ca))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def _pinned_context() -> ssl.SSLContext:
    # Hostnaam/CA worden hier niet gecontroleerd; de vingerafdruk wordt na de handdruk exact vergeleken
    # voordat er iets geheims wordt verstuurd.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


async def fetch_server_fingerprint(url: str, timeout: float) -> str | None:
    """Haal alleen het servercertificaat op (geen HTTP, geen geheimen) om de vingerafdruk te tonen."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or 443
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=_pinned_context(), server_hostname=host or None), timeout
        )
    except (OSError, TimeoutError, ssl.SSLError):
        return None
    try:
        sslobj = writer.get_extra_info("ssl_object")
        der = sslobj.getpeercert(binary_form=True) if sslobj is not None else None
        return hashlib.sha256(der).hexdigest() if der else None
    finally:
        writer.close()
        with contextlib.suppress(OSError, ssl.SSLError):
            await writer.wait_closed()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rpc_error(method: str, err: Any) -> TrueNASError:
    if not isinstance(err, dict):
        return TrueNASError("protocol_error", f"{method}: onleesbare foutmelding")
    code = err.get("code")
    data = _dict(err.get("data"))
    errname = str(data.get("errname") or "")
    reason = str(data.get("reason") or err.get("message") or "")
    low = reason.lower()
    details = {"method": method, "rpc_code": code, "errname": errname or None}
    if code == -32601 or "method not found" in low or errname == "ENOMETHOD":
        return TrueNASError("method_unavailable", f"{method} bestaat niet op deze NAS", details)
    if errname in {"ENOTAUTHENTICATED"} or "not authenticated" in low:
        return TrueNASError("auth_failed", f"{method}: niet aangemeld", details)
    if errname in {"EACCES", "EPERM"} or data.get("error") in (1, 13) or "not authorized" in low or "permission" in low:
        return TrueNASError("permission_denied", f"geen leesrecht voor {method}", details)
    return TrueNASError("protocol_error", f"{method}: {reason[:200]}", details)


class TrueNASClient:
    """Gebruik als ``async with TrueNASClient(...) as c: await c.call("pool.query")``."""

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        tls: TLSSettings | None = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
    ) -> None:
        if not url.startswith("wss://"):
            raise TrueNASError("not_configured", "alleen wss:// is toegestaan (geen onversleutelde verbinding)")
        self.url = url
        self._api_key = api_key
        self.tls = tls or TLSSettings()
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._ws: ClientConnection | None = None
        self._ids = itertools.count(1)
        self.tls_mode: Literal["verified", "pinned"] = "pinned" if self.tls.pinned_fingerprint else "verified"
        self.server_fingerprint: str | None = None

    async def __aenter__(self) -> TrueNASClient:
        await self.open()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.close()

    async def open(self) -> None:
        ctx = _pinned_context() if self.tls.pinned_fingerprint else _verify_context(self.tls.extra_ca_file)
        try:
            self._ws = await connect(
                self.url,
                ssl=ctx,
                open_timeout=self.connect_timeout,
                close_timeout=2,
                max_size=MAX_MESSAGE_BYTES,
                proxy=None,  # LAN-verbinding; nooit via een proxy
                user_agent_header="ai-server-manager-hub",
                ping_interval=None,
            )
        except ssl.SSLCertVerificationError as exc:
            fp = await fetch_server_fingerprint(self.url, self.connect_timeout)
            raise TrueNASError(
                "tls_untrusted",
                f"certificaat niet vertrouwd: {exc.verify_message or exc.reason}",
                {"fingerprint_sha256": fp, "fingerprint_weergave": display_fingerprint(fp) if fp else None},
            ) from exc
        except ssl.SSLError as exc:
            raise TrueNASError("tls_untrusted", f"TLS-fout: {exc.reason}") from exc
        except InvalidStatus as exc:
            status = exc.response.status_code
            if status == 404:
                raise TrueNASError(
                    "method_unavailable", f"{API_PATH} bestaat niet (HTTP 404); TrueNAS te oud?", {"http": status}
                ) from exc
            raise TrueNASError("unreachable", f"WebSocket geweigerd (HTTP {status})", {"http": status}) from exc
        except InvalidURI as exc:
            raise TrueNASError("not_configured", "ongeldig NAS-adres") from exc
        except TimeoutError as exc:
            raise TrueNASError("timeout", f"geen verbinding binnen {self.connect_timeout:.0f} s") from exc
        except socket.gaierror as exc:
            raise TrueNASError("unreachable", "hostnaam niet gevonden") from exc
        except (OSError, InvalidHandshake) as exc:
            raise TrueNASError("unreachable", f"verbinding mislukt: {type(exc).__name__}") from exc

        sslobj = self._ws.transport.get_extra_info("ssl_object")
        der = sslobj.getpeercert(binary_form=True) if sslobj is not None else None
        self.server_fingerprint = hashlib.sha256(der).hexdigest() if der else None
        if self.tls.pinned_fingerprint and self.server_fingerprint != self.tls.pinned_fingerprint:
            await self.close()
            fp = self.server_fingerprint
            raise TrueNASError(
                "tls_untrusted",
                "de vingerafdruk van het certificaat is gewijzigd sinds de bevestiging",
                {
                    "fingerprint_sha256": fp,
                    "fingerprint_weergave": display_fingerprint(fp) if fp else None,
                    "bevestigd": display_fingerprint(self.tls.pinned_fingerprint),
                },
            )
        ok = await self.call("auth.login_with_api_key", [self._api_key])
        if ok is not True:
            await self.close()
            raise TrueNASError("auth_failed", "API-key geweigerd")

    async def close(self) -> None:
        if self._ws is not None:
            ws, self._ws = self._ws, None
            with contextlib.suppress(OSError, ConnectionClosed):
                await ws.close()

    async def first_event(self, event: str, timeout: float) -> dict[str, Any]:
        """Abonneer op een alleen-lezen event source, wacht op de eerste ``collection_update`` met ``fields`` en zeg
        het abonnement weer op. Bron: ``core.subscribe``/``core.unsubscribe`` en ``send_event`` in de middleware
        (TS-25.10.8); NIET GEVALIDEERD op een echte NAS."""
        if event not in READ_ONLY_EVENTS:
            raise PermissionError(f"event {event} is niet toegestaan")
        if self._ws is None:
            raise TrueNASError("unreachable", "geen open verbinding")
        ident = await self.call("core.subscribe", [event])
        try:
            async with asyncio.timeout(timeout):
                while True:
                    raw = await self._ws.recv()
                    try:
                        msg = json.loads(raw)
                    except (TypeError, ValueError) as exc:
                        raise TrueNASError("protocol_error", f"{event}: geen geldige JSON") from exc
                    if not isinstance(msg, dict):
                        continue
                    params = _dict(msg.get("params"))
                    if msg.get("method") == "notify_unsubscribed" and params.get("collection") == event:
                        err = _dict(params.get("error"))
                        reason = "permission_denied" if err.get("errname") in ("EACCES", "EPERM") else "protocol_error"
                        raise TrueNASError(reason, f"{event}: abonnement beëindigd door TrueNAS")
                    if (
                        msg.get("method") == "collection_update"
                        and params.get("collection") == event
                        and params.get("msg") in ("added", "changed")
                        and isinstance(params.get("fields"), dict)
                    ):
                        return dict(params["fields"])
        except TimeoutError as exc:
            raise TrueNASError("timeout", f"{event}: geen gegevens binnen {timeout:.0f} s") from exc
        except ConnectionClosed as exc:
            raise TrueNASError("unreachable", f"{event}: verbinding verbroken") from exc
        finally:
            if self._ws is not None and isinstance(ident, str):
                with contextlib.suppress(TrueNASError):
                    await self.call("core.unsubscribe", [ident])

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        if method not in READ_ONLY_METHODS:
            raise PermissionError(f"methode {method} is niet alleen-lezen; de Hub roept die nooit aan")
        if self._ws is None:
            raise TrueNASError("unreachable", "geen open verbinding")
        req_id = next(self._ids)
        payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or []})
        try:
            await self._ws.send(payload)
            async with asyncio.timeout(self.read_timeout):
                while True:
                    raw = await self._ws.recv()
                    try:
                        msg = json.loads(raw)
                    except (TypeError, ValueError) as exc:
                        raise TrueNASError("protocol_error", f"{method}: geen geldige JSON") from exc
                    if not isinstance(msg, dict) or msg.get("id") != req_id:
                        continue  # notificaties (bv. collection_update) of oude antwoorden negeren
                    if "error" in msg and msg["error"] is not None:
                        raise _rpc_error(method, msg["error"])
                    return msg.get("result")
        except TimeoutError as exc:
            raise TrueNASError("timeout", f"{method}: geen antwoord binnen {self.read_timeout:.0f} s") from exc
        except ConnectionClosed as exc:
            raise TrueNASError("unreachable", f"{method}: verbinding verbroken") from exc
