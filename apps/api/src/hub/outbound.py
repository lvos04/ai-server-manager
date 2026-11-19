"""Uitgaande HTTP(S)-aanroepen naar monitoringbronnen, meldingskanalen en eigen diensten (contract §5).

- Alleen ``http``/``https`` naar een door een beheerder ingesteld adres; nooit inloggegevens, query of fragment in het
  basisadres; nooit een redirect volgen (3xx = storing); nooit proxy-omgevingsvariabelen (``http.client`` gebruikt die
  niet).
- HTTPS met systeem-CA's (optioneel een extra CA-bestand); nooit stil zonder verificatie.
- Tijdslimieten (standaard 5 s verbinden / 15 s lezen) en een harde grens op de antwoordgrootte.
- Adresregels van contract 1.3 §3.2: een IPv4-adres alleen als ``a.b.c.d`` (een host van alleen cijfers, punten en
  hex-delen die daar niet aan voldoet, zoals ``127.1`` of ``2130706433``, is ongeldig), IPv6 alleen tussen ``[]``,
  één punt aan het eind van een naam telt niet mee.
- Loopback, link-local (``169.254.0.0/16``, ``fe80::/10``) en ``0.0.0.0``/``::`` worden geweigerd, behalve met de
  expliciete ontwikkelvlag ``HUB_OUTBOUND_ALLOW_LOOPBACK`` (alleen voor tests): zo kan een ingesteld adres nooit de
  eigen interne API of een metadata-adres van de container raken.
- Geheimen (API-keys, tokens, wachtwoorden) gaan alleen in headers mee en komen nooit in foutmeldingen of logs.
"""

from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import re
import socket
import ssl
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

DEFAULT_MAX_BYTES = 2 * 1024 * 1024
_CANON_V4 = re.compile(r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$")
_NUMERIEK = re.compile(r"^(\d+|0[xX][0-9a-fA-F]*)(\.(\d+|0[xX][0-9a-fA-F]*))*\.?$")


class OutboundError(Exception):
    """Vaste reden (Engels, voor machines): ``adres_ongeldig``, ``adres_niet_toegestaan``, ``niet_bereikbaar``,
    ``tijdslimiet``, ``tls_fout``, ``redirect_niet_gevolgd``, ``antwoord_te_groot``."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        try:
            return json.loads(self.body) if self.body else None
        except ValueError:
            return None

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class OutboundPolicy:
    connect_timeout: float = 5.0
    read_timeout: float = 15.0
    allow_loopback: bool = False
    extra_ca_file: Path | None = None
    allowed_peer_addresses: frozenset[str] | None = None


def validate_base_url(url: str, *, allow_loopback: bool = False) -> str:
    """Basisadres ``http(s)://host[:poort][/pad]``; geeft het genormaliseerde adres (zonder slash aan het eind)."""
    url = (url or "").strip()
    if len(url) > 512:
        raise OutboundError("adres_ongeldig", "adres is te lang")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise OutboundError("adres_ongeldig", "alleen http:// of https:// met een hostnaam of IP-adres")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise OutboundError("adres_ongeldig", "geen inloggegevens, query of fragment in het adres")
    try:
        _ = parts.port
    except ValueError as exc:
        raise OutboundError("adres_ongeldig", "ongeldige poort") from exc
    hostport = parts.netloc.rsplit("@", 1)[-1]
    if (":" in parts.hostname) != hostport.startswith("["):
        raise OutboundError("adres_ongeldig", "IPv6 alleen tussen [ ]")
    _check_host(parts.hostname, allow_loopback=allow_loopback)
    return url.rstrip("/")


def _forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, allow_loopback: bool) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.is_unspecified or ip.is_link_local or ip.is_multicast:
        return True
    return bool(ip.is_loopback and not allow_loopback)


def _check_host(host: str, *, allow_loopback: bool) -> None:
    if "%" in host:
        raise OutboundError("adres_ongeldig", "geen zone-ID in een IPv6-adres")
    if ":" not in host and _NUMERIEK.match(host) and not _CANON_V4.match(host.removesuffix(".")):
        raise OutboundError("adres_ongeldig", "IPv4 alleen als a.b.c.d (vier delen 0–255, zonder voorloopnul)")
    host = host.removesuffix(".")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host.lower() in ("localhost", "localhost.localdomain") and not allow_loopback:
            raise OutboundError("adres_niet_toegestaan", "loopback is niet toegestaan") from None
        return
    if _forbidden_ip(ip, allow_loopback):
        raise OutboundError("adres_niet_toegestaan", "loopback-, link-local- of onbepaald adres is niet toegestaan")


def resolve_peer_addresses(host: str, port: int, allow_loopback: bool) -> frozenset[str]:
    """Controleer ook de opgeloste adressen van een hostnaam (geen omweg via DNS naar loopback/link-local)."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise OutboundError("niet_bereikbaar", "hostnaam niet gevonden") from exc
    addresses: set[str] = set()
    for info in infos:
        try:
            ip = ipaddress.ip_address(str(info[4][0]).split("%", 1)[0])
        except ValueError:
            continue
        if _forbidden_ip(ip, allow_loopback):
            raise OutboundError("adres_niet_toegestaan", "de hostnaam verwijst naar een niet-toegestaan adres")
        addresses.add(str(ip))
    if not addresses:
        raise OutboundError("niet_bereikbaar", "hostnaam heeft geen bruikbaar adres")
    return frozenset(addresses)


class _BoundHTTPSConnection(http.client.HTTPSConnection):
    """Verbind met een gecontroleerd numeriek adres en verifieer TLS tegen de ingestelde hostnaam."""

    def __init__(self, host: str, port: int, *, timeout: float, context: ssl.SSLContext, peer: str) -> None:
        super().__init__(host, port, timeout=timeout, context=context)
        self._tls_context = context
        self._peer = peer

    def connect(self) -> None:
        raw = socket.create_connection((self._peer, self.port), self.timeout)
        try:
            actual = str(ipaddress.ip_address(raw.getpeername()[0]))
            if actual != self._peer:
                raise OutboundError("doelbinding_gewijzigd")
            self.sock = self._tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def basic_auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def request(
    base_url: str,
    method: str,
    path: str,
    *,
    policy: OutboundPolicy,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    form_body: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Response:
    base = validate_base_url(base_url, allow_loopback=policy.allow_loopback)
    parts = urlsplit(base)
    if not path.startswith("/"):
        raise OutboundError("adres_ongeldig", "pad moet met / beginnen")
    full_path = (parts.path.rstrip("/") + path) or "/"
    if query:
        full_path += "?" + "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in query.items())
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    addresses = resolve_peer_addresses(host, port, policy.allow_loopback)
    allowed = policy.allowed_peer_addresses
    if allowed is not None:
        if parts.scheme != "https":
            raise OutboundError("https_verplicht")
        if not addresses or not addresses <= allowed:
            raise OutboundError("doelbinding_gewijzigd")
    hdrs = {"Accept": "application/json", "User-Agent": "ai-server-manager"}
    hdrs.update(headers or {})
    data = None
    if json_body is not None:
        data = json.dumps(json_body, separators=(",", ":")).encode()
        hdrs["Content-Type"] = "application/json"
    elif form_body is not None:
        data = urlencode(form_body).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    conn: http.client.HTTPConnection
    if parts.scheme == "https":
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if policy.extra_ca_file is not None:
            ctx.load_verify_locations(cafile=str(policy.extra_ca_file))
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        if allowed is not None:
            conn = _BoundHTTPSConnection(host, port, timeout=policy.connect_timeout, context=ctx, peer=min(addresses))
        else:
            conn = http.client.HTTPSConnection(host, port, timeout=policy.connect_timeout, context=ctx)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=policy.connect_timeout)
    try:
        try:
            conn.connect()
            if conn.sock is not None:
                conn.sock.settimeout(policy.read_timeout)
            conn.request(method, full_path, body=data, headers=hdrs)
            resp = conn.getresponse()
            raw = resp.read(max_bytes + 1)
        except ssl.SSLError as exc:
            raise OutboundError("tls_fout", type(exc).__name__) from None
        except TimeoutError:
            raise OutboundError("tijdslimiet") from None
        except (OSError, http.client.HTTPException) as exc:
            raise OutboundError("niet_bereikbaar", type(exc).__name__) from None
    finally:
        conn.close()
    if len(raw) > max_bytes:
        raise OutboundError("antwoord_te_groot", f"meer dan {max_bytes} bytes")
    if 300 <= resp.status < 400:
        raise OutboundError("redirect_niet_gevolgd", f"HTTP {resp.status}")
    return Response(resp.status, raw, {k.lower(): v for k, v in resp.getheaders()})


def split_url(url: str, *, allow_loopback: bool = False) -> tuple[str, str]:
    """Volledige URL → (basisadres, pad + query) voor ``request``; zelfde adresregels als ``validate_base_url``."""
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.fragment:
        raise OutboundError("adres_ongeldig", "alleen http:// of https:// zonder fragment")
    base = f"{parts.scheme}://{parts.netloc}"
    validate_base_url(base, allow_loopback=allow_loopback)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return base, path
