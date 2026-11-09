"""Heartbeat van eigen diensten naar de Hub (B09-002) — Hub-uitbreiding, geen route uit contract 1.2 (ADR-0016).

``POST /api/v1/monitoring/heartbeat`` met het service-token (dienst → Hub, contract §4.4). De dienst meldt haar eigen
status, losse controles en de toestand van haar worker. Beoordeling (grace-drempels):
- worker meldt zich niet meer binnen ``max(180 s, 3 × interval)`` → ``degraded`` (``worker_staat_stil``);
- er staan taken klaar maar de laatste afgeronde taak is ouder dan ``jobs_stil_na_s`` → ``degraded``
  (``jobs_staan_stil``) — de app geeft dan wél 200, maar doet haar werk niet (acceptatie B09-002);
- een controle ``down`` maakt een 'healthy' melding ``degraded``; ``down`` van de dienst zelf blijft ``down``.
Een heartbeat die uitblijft, maakt de dienst na ``3 × verwacht_interval_s`` ``unknown`` (nooit 'nog gezond').
Geen ``Idempotency-Key``: een herhaling met dezelfde ``observed_at`` is een duplicaat (zoals de events-inbox op
``event_id`` dedupliceert).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal["healthy", "degraded", "down"]
CheckStatus = Literal["healthy", "degraded", "down", "unknown"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Check(Strict):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    status: CheckStatus
    detail: str = Field(default="", max_length=200)


class Worker(Strict):
    laatste_hartslag: datetime | None = None
    wachtrij: int | None = Field(default=None, ge=0, le=10_000_000)
    bezig: int | None = Field(default=None, ge=0, le=100_000)
    laatste_job_klaar: datetime | None = None
    jobs_stil_na_s: int = Field(default=900, ge=60, le=86400)

    @field_validator("laatste_hartslag", "laatste_job_klaar")
    @classmethod
    def _tz(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("tijd moet een tijdzone hebben (UTC, eindigend op Z)")
        return v


class HeartbeatIn(Strict):
    status: Status
    observed_at: datetime
    verwacht_interval_s: int = Field(default=60, ge=10, le=3600)
    checks: list[Check] = Field(default_factory=list, max_length=20)
    worker: Worker | None = None

    @field_validator("observed_at")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("observed_at moet een tijdzone hebben (UTC, eindigend op Z)")
        return v


def judge(hb: HeartbeatIn, now: datetime) -> tuple[str, str | None]:
    if hb.status == "down":
        return "down", "dienst_meldt_down"
    w = hb.worker
    if w is not None:
        grace = timedelta(seconds=max(180, 3 * hb.verwacht_interval_s))
        if w.laatste_hartslag is not None and now - w.laatste_hartslag > grace:
            return "degraded", "worker_staat_stil"
        if (
            (w.wachtrij or 0) > 0
            and w.laatste_job_klaar is not None
            and now - w.laatste_job_klaar > timedelta(seconds=w.jobs_stil_na_s)
        ):
            return "degraded", "jobs_staan_stil"
    if hb.status == "degraded":
        return "degraded", "dienst_meldt_degraded"
    failing = [c.name for c in hb.checks if c.status in ("down", "degraded")]
    if failing:
        return "degraded", "controle_faalt"
    return "healthy", None


def details(hb: HeartbeatIn) -> dict[str, Any]:
    return {
        "checks": [c.model_dump() for c in hb.checks],
        "worker": hb.worker.model_dump(mode="json") if hb.worker else None,
        "gemeld": hb.status,
        "verwacht_interval_s": hb.verwacht_interval_s,
    }
