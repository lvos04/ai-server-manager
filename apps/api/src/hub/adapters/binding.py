"""Controle van adapterdoelbinding op basis van de opgeslagen app-inventaris."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from hub.adapters import basis
from hub.models import AdapterLink, CatalogApp
from hub.outbound import OutboundError
from hub.truenas.connection import NasTarget


def target_matches(target: CatalogApp | None, app_id: str) -> bool:
    return target is not None and target.aanwezig and target.app_id == app_id and target.soort == "bestaand"


def published_ports(inventory: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    owners: dict[int, list[dict[str, Any]]] = {}
    if inventory["status"] != "ok" or not isinstance(inventory["data"], list):
        return owners
    for app in inventory["data"]:
        if not isinstance(app, dict) or not isinstance(app.get("poorten"), list):
            continue
        for port in {
            binding["host_poort"]
            for binding in app["poorten"]
            if isinstance(binding, dict) and binding.get("protocol") == "tcp" and type(binding.get("host_poort")) is int
        }:
            owners.setdefault(port, []).append(app)
    return owners


def registered_port(
    base: str, target: CatalogApp, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> int | None:
    # De inventaris kan al zijn vastgelegd terwijl de worker de catalogus nog bijwerkt.
    parts = urlsplit(base)
    port = parts.port or 443
    if nas is None or parts.hostname != nas.host.strip("[]").lower() or target.bron.get("nas", nas.url) != nas.url:
        return None
    port_owners = owners.get(port, [])
    if len(port_owners) != 1:
        return None
    owner = port_owners[0]
    if (
        owner.get("runtime_id") != target.runtime_id
        or owner.get("herkend_als") != target.app_id
        or owner.get("poorten") != target.poorten
        or owner.get("portals") != target.portals
    ):
        return None
    if any(
        isinstance(portal, dict)
        and portal.get("schema") == "https"
        and portal.get("poort") == port
        and str(portal.get("pad") or "/").rstrip("/") == parts.path
        for portal in target.portals
    ):
        return port
    return None


def registered_peers(target: CatalogApp, port: int, peers: list[str]) -> bool:
    interfaces = [
        binding.get("host_ip")
        for binding in target.poorten
        if isinstance(binding, dict) and binding.get("protocol") == "tcp" and binding.get("host_poort") == port
    ]
    if not peers:
        return False
    if None in interfaces or "" in interfaces:
        return True
    try:
        addresses = {ip_address(str(interface)) for interface in interfaces}
        return all(
            peer in addresses or any(addr.is_unspecified and addr.version == peer.version for addr in addresses)
            for peer in map(ip_address, peers)
        )
    except ValueError:
        return False


def binding_is_current(
    row: AdapterLink, target: CatalogApp | None, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> bool:
    if target is None or not target_matches(target, row.app_id):
        return False
    try:
        base = basis.validate_base_url(row.basis_url)
    except OutboundError:
        return False
    port = registered_port(base, target, nas, owners)
    return port is not None and registered_peers(target, port, row.peer_addresses)
