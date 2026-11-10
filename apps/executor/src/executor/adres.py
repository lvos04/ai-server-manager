"""Adresregels van contract 1.3 §3.2 en de ``Host``-beperking van §3.7 (DNS-rebinding).

- Een IPv4-adres alleen als ``a.b.c.d`` (vier decimale delen 0–255, zonder voorloopnul). Een host van alleen cijfers,
  punten en hex-delen die daar niet aan voldoet (``127.1``, ``2130706433``, ``0x7f000001``, ``010.0.0.1``, ``0``) is
  ongeldig: zulke vormen lost een resolver anders stil op naar een (verboden) adres.
- IPv6 alleen tussen ``[]``; geen zone-ID.
- Eén punt aan het eind van een naam telt niet mee (``localhost.`` = ``localhost``).
- Verboden: loopback (alleen met een expliciete ontwikkelvlag), link-local (``169.254.0.0/16``, ``fe80::/10``) en
  ``0.0.0.0``/``::``. Bij een hostnaam gelden die ook voor het opgeloste adres, **bij elke verbinding** (zie
  :func:`resolve_allowed`); de verbinding gaat daarna naar precies het gecontroleerde adres.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

_CANON_V4 = re.compile(r"^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$")
# Alleen cijfers, punten en hex-delen (0x…): zo'n host is een (mogelijk niet-canonieke) IPv4-vorm, nooit een naam.
_NUMERIEK = re.compile(r"^(\d+|0[xX][0-9a-fA-F]*)(\.(\d+|0[xX][0-9a-fA-F]*))*\.?$")
_LABEL = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
# Namen waarop een formulier-POST mag (§3.7 punt 4): een naam zonder punt of onder een van deze lokale domeinen.
LOKALE_DOMEINEN = (".local", ".lan", ".internal", ".home.arpa")


class AdresOngeldig(ValueError):
    """Het adres voldoet niet aan §3.2; de tekst is een vaste Nederlandse melding (nooit de invoer zelf)."""


def parse_host(host: str) -> tuple[str, IPAddress | None]:
    """Normaliseer een host (zonder poort) volgens §3.2 → ``(naam_of_adres, ip_of_None)``.

    ``host`` is wat ``urlsplit(...).hostname`` geeft of de host uit een ``Host``-header; IPv6 komt hier zonder ``[]``
    binnen (de aanroeper controleert de haken). Gooit :class:`AdresOngeldig`.
    """
    if not host or "%" in host:
        raise AdresOngeldig("ongeldig adres")
    if ":" in host:
        try:
            v6 = ipaddress.IPv6Address(host)
        except ValueError:
            raise AdresOngeldig("ongeldig IPv6-adres") from None
        return str(v6), v6
    if _NUMERIEK.match(host):
        bare = host[:-1] if host.endswith(".") else host
        if not _CANON_V4.match(bare):
            raise AdresOngeldig("IPv4 alleen als a.b.c.d (vier delen 0–255, zonder voorloopnul)")
        return bare, ipaddress.IPv4Address(bare)
    name = (host[:-1] if host.endswith(".") else host).lower()
    if not name or len(name) > 253 or not all(_LABEL.match(label) for label in name.split(".")):
        raise AdresOngeldig("ongeldige hostnaam")
    return name, None


def _unwrap(addr: IPAddress) -> IPAddress:
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def check_address(addr: IPAddress, *, allow_loopback: bool = False) -> None:
    """Verboden bereiken van §3.2 (ook na DNS-resolutie)."""
    a = _unwrap(addr)
    if a.is_unspecified or a.is_link_local:
        raise AdresOngeldig("dit adres is niet toegestaan")
    if a.is_loopback and not allow_loopback:
        raise AdresOngeldig("loopback is niet toegestaan")


def validate_hub_url(value: str, *, allow_loopback: bool = False, max_len: int = 512) -> str:
    """``http(s)://<host>[:<poort>]`` zonder pad, query, fragment of inloggegevens (§3.2). Geeft de genormaliseerde
    vorm terug. De invoer wordt als geheel gecontroleerd en nooit eerst afgekapt (§3.7)."""
    if len(value) > max_len:
        raise AdresOngeldig(f"het adres is langer dan {max_len} tekens")
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise AdresOngeldig("adres moet beginnen met http:// of https://")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise AdresOngeldig("alleen http(s)://host[:poort], zonder pad, query of inloggegevens")
    try:
        port = parts.port
    except ValueError:
        raise AdresOngeldig("ongeldige poort") from None
    if port == 0:
        raise AdresOngeldig("ongeldige poort")
    hostport = parts.netloc.rsplit("@", 1)[-1]
    raw = parts.hostname or ""
    bracketed = hostport.startswith("[")
    if (":" in raw) != bracketed:
        raise AdresOngeldig("IPv6 alleen tussen [ ]")
    name, ip = parse_host(raw)
    if ip is not None:
        check_address(ip, allow_loopback=allow_loopback)
    elif name == "localhost" and not allow_loopback:
        raise AdresOngeldig("loopback is niet toegestaan")
    netloc = f"[{name}]" if isinstance(ip, ipaddress.IPv6Address) else name
    return f"{parts.scheme}://{netloc}" + (f":{port}" if port else "")


def resolve_allowed(host: str, port: int, *, allow_loopback: bool = False) -> str:
    """Los ``host`` op en controleer **elk** opgelost adres (§3.2: bij elke verbinding). Geeft het adres terug waarmee
    verbonden moet worden, zodat een tweede (andere) DNS-uitkomst tussen controle en verbinding geen rol speelt."""
    name, ip = parse_host(host)
    if ip is not None:
        check_address(ip, allow_loopback=allow_loopback)
        return str(ip)
    if name == "localhost" and not allow_loopback:
        raise AdresOngeldig("loopback is niet toegestaan")
    try:
        infos = socket.getaddrinfo(name, port, type=socket.SOCK_STREAM)
    except OSError:
        raise AdresOngeldig("naam niet op te lossen") from None
    addrs = [ipaddress.ip_address(str(info[4][0]).split("%", 1)[0]) for info in infos]
    if not addrs:
        raise AdresOngeldig("naam niet op te lossen")
    for a in addrs:
        check_address(a, allow_loopback=allow_loopback)
    return str(_unwrap(addrs[0]))


def split_host_header(header: str) -> tuple[str, bool]:
    """``Host``-header → ``(host zonder poort, tussen haken)``; IPv6 zonder de haken."""
    header = header.strip()
    if header.startswith("["):
        end = header.find("]")
        if end < 0 or (header[end + 1 :] and not re.fullmatch(r":\d{1,5}", header[end + 1 :])):
            return "", True
        return header[1:end], True
    host, _sep, port = header.partition(":")
    if _sep and not re.fullmatch(r"\d{1,5}", port):
        return "", False
    return host, False


def host_allowed_for_post(header: str) -> bool:
    """§3.7 punt 4 (DNS-rebinding): een formulier-POST alleen als de ``Host`` (zonder poort) een IP-adres in de vorm
    van §3.2 is (IPv6 tussen ``[]``), een naam zonder punt, of een naam onder ``.local``, ``.lan``, ``.internal`` of
    ``.home.arpa``. Een publieke domeinnaam (waarmee rebinding werkt) → nee."""
    host, bracketed = split_host_header(header)
    if not host or (":" in host) != bracketed:
        return False
    try:
        name, ip = parse_host(host)
    except AdresOngeldig:
        return False
    if ip is not None:
        return True
    return "." not in name or name.endswith(LOKALE_DOMEINEN)
