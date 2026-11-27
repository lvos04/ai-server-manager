"""Diagnose en voorstellen. De Hub bewaakt rollen, D09 en het beleid voor elk voorstel."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import or_, select

from hub import audit
from hub.ai import kennis, tegoed
from hub.deps import DB, Admin, Cursor, Limit, SettingsDep, Viewer, decode_cursor, encode_cursor
from hub.models import AuditEvent
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
