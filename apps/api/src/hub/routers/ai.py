"""Diagnose en voorstellen. De Hub bewaakt rollen, D09 en het beleid voor elk voorstel."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select

from hub import audit
from hub.ai import kennis, runner, tegoed, triage
from hub.deps import DB, Admin, Cursor, Idem, Limit, Operator, SettingsDep, Viewer, decode_cursor, encode_cursor
from hub.errors import HubError, trace_id_of
from hub.models import AuditEvent, IdempotencyRecord
from hub.timeutil import iso, utcnow

router = APIRouter(prefix="/api/v1/ai", tags=["AI-diagnose"])


@router.get("/providers", summary="Gekozen aanbieder en het resterende inbegrepen maandtegoed")
def providers(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    now = utcnow()
    return {"tegoed": tegoed.stand(db, settings, now).model_dump(), "bron": "D09", "observed_at": iso(now)}


@router.get("/audit", summary="Kredietreserveringen, diagnose-uitkomsten en AI-voorstellen")
def ai_audit(db: DB, _: Admin, limit: Limit = 50, cursor: Cursor = None) -> dict[str, Any]:
    q = select(AuditEvent).where(or_(AuditEvent.action.startswith("ai."), AuditEvent.actor_type == "ai"))
    if (before := decode_cursor(cursor)) is not None:
        q = q.where(AuditEvent.id < before)
    rows = list(db.scalars(q.order_by(AuditEvent.id.desc()).limit(limit + 1)))
    return {
        "items": [audit.to_dict(r) for r in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1].id) if len(rows) > limit else None,
    }


@router.get(
    "/kennis/{incident_id}", summary="Lokale bronnen bij een incident (logtekst alleen voor operators en beheerders)"
)
def ai_kennis(incident_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Viewer) -> kennis.Kennis:
    return kennis.lees(db, settings, kennis.incident(db, incident_id, principal), principal)


class DiagnoseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: uuid.UUID


def _frequentie(db: DB, idem: Idem) -> None:
    aantal = db.scalar(
        select(func.count())
        .select_from(IdempotencyRecord)
        .where(IdempotencyRecord.scope == idem.scope, IdempotencyRecord.created_at >= utcnow() - timedelta(minutes=1))
    )
    if aantal is not None and aantal >= 30:
        raise HubError(
            429, "rate_limited", "Wacht een minuut voordat je een nieuw verzoek doet.", headers={"Retry-After": "60"}
        )


@router.post("/diagnose", summary="Verklaar een incident met vaste regels en zo nodig een begrensde analyse")
def diagnose(
    body: DiagnoseIn, request: Request, db: DB, settings: SettingsDep, principal: Operator, idem: Idem
) -> JSONResponse:
    inc = kennis.incident(db, body.incident_id, principal)
    if (replay := idem.replay()) is not None:
        return replay
    _frequentie(db, idem)
    bronnen = kennis.lees(db, settings, inc, principal)
    regel, melding = triage.beoordeel(db, inc, bronnen)
    status, advies = "vaste_regel", None
    if regel == "geen_regel" and inc.classificatie != "sensitive":
        telling = runner.Triage(
            ernst=bronnen.incident.ernst,
            gebeurtenissen=inc.aantal,
            inventaris=bronnen.inventaris.status,
            logregels=len(bronnen.logs),
        )
        status, taak = tegoed.reserveer(db, settings, idem.key, principal.name, telling)
        if taak is not None:
            antwoord = runner.vraag_runner(taak)
            status, advies = antwoord.status, antwoord.analyse
            if status == "tegoed_op":
                tegoed.uitgeput(db, taak)
    elif regel == "geen_regel":
        status = "alleen_lokaal"
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="ai.diagnose",
        target_type="incident",
        target_id=str(inc.id),
        trace_id=trace_id_of(request),
        details={"status": status, "regel": regel},
    )
    return idem.save(
        200,
        {
            "incident_id": str(inc.id),
            "regel": regel,
            "melding": melding,
            "gebeurtenissen": inc.aantal,
            "status": status,
            "advies": advies,
            "zekerheid_regel": bronnen.incident.zekerheid,
            "bron": f"/api/v1/ai/kennis/{inc.id}",
            "observed_at": iso(inc.laatste_op),
        },
    )
