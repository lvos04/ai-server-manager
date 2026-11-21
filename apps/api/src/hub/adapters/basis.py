"""Gedeelde doelbinding, leesinterface en versheid voor bestaande apps."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, Field

from hub import outbound
from hub.models import AdapterLink
from hub.timeutil import UtcDateTime, age_seconds

type AppId = Literal["mediaguard", "media-source-optimizer", "my_house"]
type Status = Literal["healthy", "unknown", "degraded", "down"]

MAX_AGE_S = 900
MAX_RESPONSE_BYTES = 64 * 1024
MSO_APP_ID = "media-source-optimizer"
PUBLIC_PROBES = {
    # MediaGuard heeft hier geen toelating. Ook de openbare health-route voert een schemacontrole uit.
    MSO_APP_ID: "/healthz",
    "my_house": "/api/v1/health",
}
MSO_SETUP_PATH = "/api/v1/setup/status"


class Measurement(BaseModel):
    status: Status
    observed_at: UtcDateTime | None = None
    reason_code: str | None = None
    laatste_status: Status | None = None
    # Interne vervalgrens voor de catalogus, afgeleid van de TTL van de bron.
    geldig_tot: datetime | None = Field(default=None, exclude=True)


class ReadAdapter(Protocol):
    """Appmodules projecteren hun toegelaten leesroutes op het connectorcontract (§6)."""

    def discover(self) -> dict[str, object]: ...

    def health(self) -> Measurement: ...

    def items(self, item_type: str, *, cursor: str | None, limit: int) -> dict[str, object]: ...


def fresh_measurement(
    measurement: Measurement, *, now: datetime | None = None, max_age_s: int = MAX_AGE_S
) -> Measurement:
    age = age_seconds(measurement.observed_at, now)
    if measurement.observed_at is None or age is None or age < 0:
        return Measurement(status="unknown", reason_code=measurement.reason_code or "meettijd_onbekend")
    ttl = min(max_age_s, MAX_AGE_S)
    if age > ttl:
        return Measurement(
            status="unknown",
            observed_at=measurement.observed_at,
            reason_code="meting_verouderd",
            laatste_status=measurement.laatste_status or measurement.status,
        )
    return measurement.model_copy(update={"geldig_tot": measurement.observed_at + timedelta(seconds=ttl)})


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


def read_request(
    link: AdapterLink, path: str, *, policy: outbound.OutboundPolicy, correlation_id: UUID | None = None
) -> outbound.Response:
    """Verzend de toegelaten openbare probe naar de bevestigde bestemming."""
    public_probe = PUBLIC_PROBES.get(link.app_id)
    if public_probe is None or (path != public_probe and not (link.app_id == MSO_APP_ID and path == MSO_SETUP_PATH)):
        raise outbound.OutboundError("capability_unavailable")
    base = validate_base_url(link.basis_url)
    bound = bound_policy(link, policy)
    if correlation_id is None:
        return outbound.request(base, "GET", path, policy=bound, max_bytes=MAX_RESPONSE_BYTES)
    return outbound.request(
        base, "GET", path, policy=bound, headers={"X-Correlation-Id": str(correlation_id)}, max_bytes=MAX_RESPONSE_BYTES
    )


def bound_policy(link: AdapterLink, policy: outbound.OutboundPolicy) -> outbound.OutboundPolicy:
    if not link.peer_addresses:
        raise outbound.OutboundError("doelbinding_ontbreekt")
    return replace(policy, allow_loopback=False, allowed_peer_addresses=frozenset(link.peer_addresses))
