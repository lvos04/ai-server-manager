"""Gedeelde doelbinding, leesinterface en versheid voor bestaande apps."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from hub import outbound
from hub.models import AdapterLink
from hub.timeutil import UtcDateTime, age_seconds, utcnow

type AppId = Literal["mediaguard", "media-source-optimizer", "my_house"]
type Status = Literal["healthy", "unknown", "degraded", "down"]

MAX_AGE_S = 900
MAX_RESPONSE_BYTES = 64 * 1024
PUBLIC_PROBES = {
    "mediaguard": "/api/v1/health",
    "media-source-optimizer": "/healthz",
    "my_house": "/api/v1/health",
}


class Measurement(BaseModel):
    status: Status
    observed_at: UtcDateTime | None = None
    reason_code: str | None = None
    laatste_status: Status | None = None


class ReadAdapter(Protocol):
    """Appmodules projecteren hun toegelaten leesroutes op het connectorcontract (§6)."""

    def discover(self) -> dict[str, object]: ...

    def health(self) -> Measurement: ...

    def items(self, item_type: str, *, cursor: str | None, limit: int) -> dict[str, object]: ...


def fresh_measurement(
    measurement: Measurement, *, now: datetime | None = None, max_age_s: int = MAX_AGE_S
) -> Measurement:
    age = age_seconds(measurement.observed_at, now)
    if age is None or age < 0:
        return Measurement(status="unknown", reason_code=measurement.reason_code or "meettijd_onbekend")
    if age > min(max_age_s, MAX_AGE_S):
        return Measurement(
            status="unknown",
            observed_at=measurement.observed_at,
            reason_code="meting_verouderd",
            laatste_status=measurement.laatste_status or measurement.status,
        )
    return measurement


def validate_base_url(url: str) -> str:
    if any(ord(char) < 33 or ord(char) == 127 for char in url):
        raise outbound.OutboundError("adres_ongeldig")
    try:
        base = outbound.validate_base_url(url)
        parts = urlsplit(base)
    except ValueError:
        raise outbound.OutboundError("adres_ongeldig") from None
    if parts.scheme != "https":
        raise outbound.OutboundError("https_verplicht")
    if (
        "@" in parts.netloc
        or parts.port == 0
        or "?" in base
        or "#" in base
        or not re.fullmatch(r"(?:/[a-zA-Z0-9._~-]+)*", parts.path)
        or {".", ".."}.intersection(parts.path.split("/"))
    ):
        raise outbound.OutboundError("adres_ongeldig")
    return base


def resolve_binding(base: str) -> list[str]:
    parts = urlsplit(validate_base_url(base))
    return sorted(outbound.resolve_peer_addresses(parts.hostname or "", parts.port or 443, False))


def read_request(link: AdapterLink, path: str, *, policy: outbound.OutboundPolicy) -> outbound.Response:
    """Verzend de toegelaten openbare probe naar de bevestigde bestemming."""
    if path != PUBLIC_PROBES.get(link.app_id):
        raise outbound.OutboundError("capability_unavailable")
    if not link.peer_addresses:
        raise outbound.OutboundError("doelbinding_ontbreekt")
    base = validate_base_url(link.basis_url)
    bound = replace(policy, allow_loopback=False, allowed_peer_addresses=frozenset(link.peer_addresses))
    return outbound.request(base, "GET", path, policy=bound, max_bytes=MAX_RESPONSE_BYTES)


def probe(link: AdapterLink, policy: outbound.OutboundPolicy) -> Measurement:
    """Een verse openbare respons bewijst contact. De appgezondheid vereist een afzonderlijke adapter."""
    try:
        response = read_request(link, PUBLIC_PROBES.get(link.app_id, ""), policy=policy)
    except outbound.OutboundError as exc:
        return Measurement(status="unknown", reason_code=exc.reason)
    if response.status in (401, 403):
        return Measurement(status="unknown", reason_code="bron_credential_geweigerd")
    body = response.json()
    if response.status != 200 or not isinstance(body, dict) or body.get("status") != "ok":
        return Measurement(status="unknown", reason_code="antwoord_ongeldig")
    return Measurement(status="healthy", observed_at=utcnow())
