"""Synthetische IPv4-adressen voor de lokale tests en simulators."""

from ipaddress import IPv4Address


def ipv4(*octetten: int) -> str:
    return str(IPv4Address(bytes(octetten)))


def documentatieadres(host: int) -> str:
    """Een adres in TEST-NET-1 (RFC 5737)."""
    return ipv4(192, 0, 2, host)


LAN_CLIENT = ipv4(192, 168, 1, 20)
LINKLOCAL_METADATA = ipv4(169, 254, 169, 254)
ONGESPECIFICEERD = str(IPv4Address(0))
# Opzettelijk ongeldige schrijfwijze met een voorloopnul.
ADRES_MET_VOORLOOPNUL = ".".join(("010", "0", "0", "1"))
