"""Openbare leesprobes voor Media Source Optimizer (S-P3-040, ADR-0034)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, ValidationError

from hub import outbound
from hub.adapters import basis
from hub.models import AdapterLink
from hub.timeutil import iso, utcnow

APP_ID = basis.MSO_APP_ID
HEALTH_PATH = basis.PUBLIC_PROBES[APP_ID]
Version = Annotated[str, Field(max_length=48, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?$")]
ERROR_CODES = {401: "unauthorized", 403: "forbidden", 429: "rate_limited", 503: "error", 500: "internal"}


class Liveness(BaseModel):
    status: Literal["ok"]
    version: Version


class SetupStatus(BaseModel):
    setup_required: bool
    completed: bool
    version: Version


class PublicProbes(BaseModel):
    healthz: Liveness | None
    setup: SetupStatus | None


@dataclass(frozen=True)
class ProbeFailure:
    reason_code: str
    correlation_id: str | None = None


@dataclass(frozen=True)
class ProbeResult:
    probes: PublicProbes
    connection: basis.Measurement
    failures: tuple[ProbeFailure, ...]


def discover() -> dict[str, object]:
    return {
        "app_id": APP_ID,
        "source_version": None,
        "schema_version": "1.0",
        "capabilities": [],
        "permissions": [],
        "limits": {"max_age_s": {}},
        "timestamp_utc": iso(utcnow()),
    }


def health() -> basis.Measurement:
    return basis.Measurement(status="unknown", reason_code="capability_unavailable")


def items(item_type: str, *, cursor: str | None, limit: int) -> dict[str, object]:
    return {"status": "unknown", "reason_code": "capability_unavailable", "observed_at": None, "items": []}


def _read[T: BaseModel](
    link: AdapterLink, path: str, model: type[T], policy: outbound.OutboundPolicy, check_binding: Callable[[], None]
) -> T | ProbeFailure:
    check_binding()
    try:
        response = basis.read_request(link, path, policy=policy)
    except outbound.OutboundError as exc:
        return ProbeFailure(exc.reason)

    try:
        body: Any = response.json()
    except RecursionError:
        body = None
    if response.status != 200:
        reason = "bron_credential_geweigerd" if response.status in (401, 403) else "onverwachte_statuscode"
        code = ERROR_CODES.get(response.status)
        if code and isinstance(body, dict) and body.get("code") == code:
            cid = body.get("correlation_id")
            if isinstance(cid, str) and re.fullmatch(r"[0-9a-f]{12}", cid):
                return ProbeFailure(reason, cid)
        return ProbeFailure(reason)
    try:
        return model.model_validate(body, strict=True)
    except ValidationError:
        return ProbeFailure("antwoord_ongeldig")


def public_probes(
    link: AdapterLink, policy: outbound.OutboundPolicy, *, check_binding: Callable[[], None]
) -> ProbeResult:
    liveness = _read(link, HEALTH_PATH, Liveness, policy, check_binding)
    setup = _read(link, basis.MSO_SETUP_PATH, SetupStatus, policy, check_binding)
    if isinstance(setup, SetupStatus) and setup.setup_required == setup.completed:
        setup = ProbeFailure("antwoord_ongeldig")

    failures = tuple(probe for probe in (liveness, setup) if isinstance(probe, ProbeFailure))
    connection = (
        basis.Measurement(status="unknown", reason_code=failures[0].reason_code)
        if failures
        else basis.Measurement(status="healthy", observed_at=utcnow())
    )
    return ProbeResult(
        PublicProbes(
            healthz=liveness if isinstance(liveness, Liveness) else None,
            setup=setup if isinstance(setup, SetupStatus) else None,
        ),
        connection,
        failures,
    )
