"""Log-index (B09-004): eigen diensten sturen geschoonde logregels (service-token); operators zoeken op incident,
bron, tijd, niveau, tekst of trace_id. Alles wat in de index staat is vóór opslag geschoond en begrensd."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select

from hub.deps import DB, Cursor, Limit, Operator, ServiceP, SettingsDep, decode_cursor, encode_cursor, get_vault
from hub.errors import HubError
from hub.logsink import Regel, recent_count, store, to_dict
from hub.models import Incident, LogEntry
from hub.timeutil import iso, utcnow
from hub.vault import Vault

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])
VaultDep = Annotated[Vault, Depends(get_vault)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegelIn(Strict):
    """Contract 1.3 §6.1 (RV11): ``op`` een tijd met tijdzone, ``trace_id`` een UUID; invoer ``bericht`` 1–8000 tekens
    (langer → 422, nooit eerst afkappen); opslag daarna hooguit 2000 tekens, gemarkeerd als ingekort."""

    op: datetime
    niveau: Literal["debug", "info", "warning", "error", "critical"]
    bericht: str = Field(min_length=1, max_length=8000)
    logger: str = Field(default="", max_length=96)
    trace_id: uuid.UUID | None = None
    velden: dict[str, Any] = Field(default_factory=dict)

    @field_validator("op")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("op moet een tijdzone hebben (UTC, eindigend op Z)")
        return v


class LogsIn(Strict):
    regels: list[RegelIn] = Field(min_length=1, max_length=200)


@router.post(
    "",
    status_code=202,
    summary="Logregels van een eigen dienst opnemen (service-token; geschoond en begrensd vóór opslag)",
    responses={429: {"description": "rate_limited (per dienst per minuut)"}},
)
def logs_ingest(body: LogsIn, db: DB, settings: SettingsDep, principal: ServiceP, vault: VaultDep) -> JSONResponse:
    now = utcnow()
    bron = principal.service_app_id or "onbekend"
    used = recent_count(db, bron, now)
    room = max(0, settings.log_ingest_max_per_minute - used)
    if room == 0:
        raise HubError(
            429, "rate_limited", "Te veel logregels; probeer het later opnieuw.", headers={"Retry-After": "60"}
        )
    accepted = body.regels[:room]
    n = store(
        db,
        [
            Regel(
                op=r.op,
                bron=bron,
                niveau=r.niveau,
                bericht=r.bericht,
                logger=r.logger,
                trace_id=str(r.trace_id) if r.trace_id else None,
                velden=r.velden,
            )
            for r in accepted
        ],
        vault,
    )
    db.commit()
    return JSONResponse({"opgeslagen": n, "geweigerd": len(body.regels) - n, "bron": bron}, status_code=202)


@router.get("", summary="Logregels zoeken (operator): op incident, bron, niveau, tekst, trace_id en tijd")
def search_logs(
    db: DB,
    _: Operator,
    limit: Limit = 100,
    cursor: Cursor = None,
    q: str | None = Query(default=None, max_length=100, description="Tekst (geschoonde berichten)"),
    bron: str | None = Query(default=None, max_length=64),
    niveau: Literal["debug", "info", "warning", "error", "critical"] | None = None,
    trace_id: uuid.UUID | None = None,
    incident_id: uuid.UUID | None = None,
    van: datetime | None = None,
    tot: datetime | None = None,
) -> dict[str, Any]:
    before = decode_cursor(cursor)
    stmt = select(LogEntry)
    if before is not None:
        stmt = stmt.where(LogEntry.id < before)
    if q:
        stmt = stmt.where(LogEntry.bericht.ilike(f"%{q.replace('%', '').replace('_', '')}%"))
    if bron:
        stmt = stmt.where(LogEntry.bron == bron)
    if niveau:
        stmt = stmt.where(LogEntry.niveau == niveau)
    if trace_id:
        stmt = stmt.where(LogEntry.trace_id == str(trace_id))
    if van:
        stmt = stmt.where(LogEntry.op >= van)
    if tot:
        stmt = stmt.where(LogEntry.op <= tot)
    if incident_id:
        inc = db.get(Incident, incident_id)
        if inc is None:
            raise HubError(404, "not_found", "Incident niet gevonden.")
        traces = [t for t in inc.trace_ids or [] if t]
        stmt = stmt.where(
            or_(
                LogEntry.trace_id.in_(traces) if traces else LogEntry.id < 0,
                (LogEntry.op >= inc.eerste_op) & (LogEntry.op <= (inc.opgelost_op or utcnow())),
            )
        )
    rows = list(db.scalars(stmt.order_by(LogEntry.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [to_dict(r) for r in rows],
        "next_cursor": encode_cursor(rows[-1].id) if more and rows else None,
        "geschoond": True,
    }


@router.get("/bronnen", summary="Welke logbronnen de Hub heeft (en welke niet: eerlijk onbekend)")
def sources(settings: SettingsDep, _: Operator) -> dict[str, Any]:
    return {
        "bronnen": [
            {"bron": "hub-api", "status": "actief", "vanaf_niveau": settings.log_hub_level, "via": "eigen proces"},
            {"bron": "hub-worker", "status": "actief", "vanaf_niveau": settings.log_hub_level, "via": "eigen proces"},
            {
                "bron": "eigen diensten",
                "status": "actief",
                "via": "POST /api/v1/logs (service-token)",
                "toelichting": "Alleen diensten die zelf logregels sturen; per dienst hooguit "
                f"{settings.log_ingest_max_per_minute} regels per minuut.",
            },
            {
                "bron": "TrueNAS-containerlogs",
                "status": "capability_unavailable",
                "toelichting": "Nog niet gebouwd: welke TrueNAS-methode containerlogs aan de alleen-lezen-sleutel "
                "geeft is NIET GEVALIDEERD (echte NAS). Bekijk ze in TrueNAS → Apps → app → Logs.",
            },
            {
                "bron": "bestaande apps (MediaGuard, MSO, my_house, Jellyfin)",
                "status": "unknown",
                "toelichting": "Hun eigen logs blijven in hun eigen UI; koppeling volgt met de adapters (P3).",
            },
        ],
        "retentie_s": settings.log_retention_seconds,
        "max_regels": settings.log_max_rows,
        "schoning": "geheimen, tokens, JWT, PEM, lange hex/base64, e-mail en IP-adressen gemaskeerd vóór opslag",
        "bijgewerkt_op": iso(utcnow()),
    }
