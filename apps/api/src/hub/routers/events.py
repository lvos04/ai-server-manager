"""Events-inbox (contract §7) met dedupe, auditlijst en het connectorcontract (§6) voor de Hub zelf.

Contract 1.3: ``discover`` noemt ``limits.max_age_s`` (§6.2); ``health`` gebruikt de vaste checknamen ``database``,
``worker`` en ``jobs`` (plus ``eigen_backup``) en het totaal is de slechtste check (§6); ``items`` volgt de vaste scopes
van §4.4 (``decision`` alleen met ``besluiten.lezen``, ``backup.self`` alleen voor gebruikers); ``events`` en
``evidence`` zijn alleen voor gebruikers (``viewer``+): daar zit beheerinformatie in waarvoor geen dienstscope bestaat.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from hub import APP_ID, __version__, audit
from hub.backup.selfbackup import latest_verified
from hub.backup.selfbackup import to_dict as backup_dict
from hub.config import DEFAULT_MAX_AGE_SECONDS
from hub.deps import (
    DB,
    Admin,
    Cursor,
    Limit,
    Principal,
    ServiceP,
    SettingsDep,
    Viewer,
    ViewerOrService,
    decode_cursor,
    encode_cursor,
    require_viewer_or_scope,
)
from hub.errors import HubError
from hub.events.envelope import EventEnvelope, accept, inbox_to_dict, outbox_to_envelope
from hub.models import (
    AuditEvent,
    Decision,
    InboxEvent,
    InventoryRun,
    Job,
    OutboxEvent,
    SelfBackup,
    WorkerHeartbeat,
)
from hub.monitoring.sources import worst
from hub.onboarding import service as decisions
from hub.scopes import BESLUITEN_LEZEN
from hub.security import Role
from hub.timeutil import iso, utcnow

router = APIRouter(tags=["events en connector"])
UsersOnly = Annotated[Principal, Depends(require_viewer_or_scope(None))]
DecisionReader = Annotated[Principal, Depends(require_viewer_or_scope(BESLUITEN_LEZEN))]
# Een wachtrij die niet afneemt (oudste wachtende job ouder dan dit) → jobs degraded (§6 regel 3).
JOBS_STIL_NA_S = 15 * 60


@router.post("/api/v1/events/inbox", summary="Event ontvangen (service-token); dedupe op event_id en bron-id")
def inbox(env: EventEnvelope, db: DB, principal: ServiceP) -> JSONResponse:
    if env.source_app != principal.service_app_id:
        raise HubError(403, "source_mismatch", "source_app moet gelijk zijn aan de app van het service-token.")
    status, row = accept(db, env, service_id=uuid.UUID(principal.id))
    code = 202 if status == "accepted" else 200
    return JSONResponse({"status": status, "event_id": str(row.event_id), "seq": row.seq}, status_code=code)


@router.get("/api/v1/events", summary="Ontvangen events (nieuwste eerst, cursor)")
def list_events(
    db: DB,
    principal: Viewer,
    limit: Limit = 50,
    cursor: Cursor = None,
    source_app: str | None = Query(default=None, max_length=64),
    event_type: str | None = Query(default=None, max_length=128),
) -> dict[str, Any]:
    before = decode_cursor(cursor)
    q = select(InboxEvent)
    if before is not None:
        q = q.where(InboxEvent.seq < before)
    if source_app:
        q = q.where(InboxEvent.source_app == source_app)
    if event_type:
        q = q.where(InboxEvent.event_type == event_type)
    rows = list(db.scalars(q.order_by(InboxEvent.seq.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    show = principal.role == Role.admin
    return {
        "items": [inbox_to_dict(r, show_sensitive=show) for r in rows],
        "next_cursor": encode_cursor(rows[-1].seq) if more and rows else None,
    }


@router.get("/api/v1/audit", summary="Globaal auditspoor (admin), nieuwste eerst, met hash-ketting")
def list_audit(
    db: DB,
    _: Admin,
    limit: Limit = 50,
    cursor: Cursor = None,
    actie: str | None = Query(default=None, max_length=96, description="Exacte actie, bv. auth.login"),
    actor: str | None = Query(default=None, max_length=64, description="Exacte actor-id"),
) -> dict[str, Any]:
    before = decode_cursor(cursor)
    q = select(AuditEvent)
    if before is not None:
        q = q.where(AuditEvent.id < before)
    if actie:
        q = q.where(AuditEvent.action == actie)
    if actor:
        q = q.where(AuditEvent.actor_id == actor)
    rows = list(db.scalars(q.order_by(AuditEvent.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [audit.to_dict(r) for r in rows],
        "next_cursor": encode_cursor(rows[-1].id) if more and rows else None,
    }


@router.get(
    "/api/v1/audit/verify",
    summary="Hash-ketting van het auditspoor controleren (admin): nummering, koppeling, inhoud en anker",
)
def verify_audit(db: DB, settings: SettingsDep, _: Admin) -> dict[str, Any]:
    return audit.verify(db, settings.data_dir)


# ------------------------------------------------------------------ connectorcontract §6 (de Hub als bron)
@router.get("/connector/v1/discover", summary="Connector: capabilities van de Hub (met limits.max_age_s, §6.2)")
def discover(_: ViewerOrService) -> dict[str, Any]:
    return {
        "app_id": APP_ID,
        "source_version": __version__,
        "schema_version": "1.0",
        "capabilities": ["read"],
        "permissions": ["decision:read", "gate:read", "backup:read", "events:read"],
        "limits": {
            "max_page_size": 200,
            "event_payload_max_bytes": 16384,
            # §6.2: per capability of itemtype; zonder eigen waarde geldt de standaard van 900 s.
            "max_age_s": {"health": DEFAULT_MAX_AGE_SECONDS, "decision": DEFAULT_MAX_AGE_SECONDS},
        },
        "timestamp_utc": iso(utcnow()),
    }


def _jobs_check(db: Any, now: Any) -> dict[str, Any]:
    """§6 regel 3: ``jobs`` met ``detail.wachtrij``, ``detail.bezig`` en ``detail.laatste_job_klaar``; een wachtrij die
    niet afneemt (oudste wachtende job ouder dan 15 min) → degraded."""
    try:
        queued = int(db.scalar(select(func.count()).select_from(Job).where(Job.status == "queued")) or 0)
        running = int(db.scalar(select(func.count()).select_from(Job).where(Job.status == "running")) or 0)
        oldest = db.scalar(select(func.min(Job.created_at)).where(Job.status == "queued"))
        last_done = db.scalar(select(func.max(Job.finished_at)).where(Job.status.in_(("done", "failed"))))
    except Exception:
        return {"name": "jobs", "status": "unknown", "observed_at": iso(now), "detail": "niet te lezen"}
    stuck = oldest is not None and now - oldest > timedelta(seconds=JOBS_STIL_NA_S)
    return {
        "name": "jobs",
        "status": "degraded" if stuck else "healthy",
        "observed_at": iso(now),
        "detail": {
            "wachtrij": queued,
            "bezig": running,
            "laatste_job_klaar": iso(last_done),
            **({"reden": "wachtrij_neemt_niet_af"} if stuck else {}),
        },
    }


@router.get("/connector/v1/health", summary="Connector: gezondheid van de Hub (totaal = slechtste check, §6)")
def health(db: DB, settings: SettingsDep, _: ViewerOrService) -> dict[str, Any]:
    now = utcnow()
    checks: list[dict[str, Any]] = []
    try:
        db.execute(text("SELECT 1"))
        checks.append({"name": "database", "status": "healthy", "observed_at": iso(now), "detail": ""})
    except Exception:
        checks.append({"name": "database", "status": "down", "observed_at": iso(now), "detail": "niet bereikbaar"})
    hb = db.get(WorkerHeartbeat, "worker") if checks[0]["status"] == "healthy" else None
    if hb is None:
        checks.append({"name": "worker", "status": "unknown", "observed_at": None, "detail": "nog geen hartslag"})
    else:
        fresh = (now - hb.beat_at).total_seconds() < max(60, settings.worker_poll_seconds * 6)
        checks.append(
            {
                "name": "worker",
                "status": "healthy" if fresh else "down",
                "observed_at": iso(hb.beat_at),
                "detail": "" if fresh else "hartslag verouderd",
            }
        )
    if checks[0]["status"] == "healthy":
        checks.append(_jobs_check(db, now))
    else:
        checks.append({"name": "jobs", "status": "unknown", "observed_at": None, "detail": "database niet bereikbaar"})
    b = latest_verified(db) if checks[0]["status"] == "healthy" else None
    if b is None or b.finished_at is None:
        checks.append(
            {
                "name": "eigen_backup",
                "status": "degraded",
                "observed_at": None,
                "detail": "nog geen geverifieerde back-up",
            }
        )
    else:
        fresh = (now - b.finished_at).total_seconds() < settings.self_backup_interval_seconds + 7200
        checks.append(
            {
                "name": "eigen_backup",
                "status": "healthy" if fresh else "degraded",
                "observed_at": iso(b.finished_at),
                "detail": "" if fresh else "verouderd",
            }
        )
    overall = worst([c["status"] for c in checks])
    bad = next((c for c in checks if c["status"] == overall), None) if overall != "healthy" else None
    reason = None if bad is None else f"{bad['name']}_{overall}"
    return {"status": overall, "observed_at": iso(now), "reason_code": reason, "checks": checks}


@router.get(
    "/connector/v1/items",
    summary="Connector: eigen data (gepagineerd); decision met scope besluiten.lezen, backup.self alleen gebruikers",
    responses={403: {"description": "scope_ontbreekt: dienst zonder de vaste scope voor dit itemtype (§4.4)"}},
)
def items(
    db: DB,
    principal: ViewerOrService,
    type: str = Query(pattern=r"^(decision|backup\.self)$"),
    limit: Limit = 50,
    cursor: Cursor = None,
) -> dict[str, Any]:
    # §4.4: zonder scope 403 scope_ontbreekt; backup.self is alleen voor gebruikers (K6).
    require_viewer_or_scope(BESLUITEN_LEZEN if type == "decision" else None)(principal)
    offset = decode_cursor(cursor) or 0
    now = utcnow()
    if type == "decision":
        decisions.seed(db)
        rows = list(db.scalars(select(Decision).order_by(Decision.id).offset(offset).limit(limit + 1)))
        data = [decisions.to_dict(r) for r in rows[:limit]]
    else:
        brows = list(
            db.scalars(select(SelfBackup).order_by(SelfBackup.started_at.desc()).offset(offset).limit(limit + 1))
        )
        rows = brows  # type: ignore[assignment]
        data = [backup_dict(r) for r in brows[:limit]]
    return {
        "type": type,
        "items": data,
        "observed_at": iso(now),  # §6.2: elke meting met observed_at (gelezen uit de eigen database)
        "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
    }


def _unavailable(what: str) -> JSONResponse:
    return JSONResponse(
        {
            "code": "capability_unavailable",
            "message": f"De Hub biedt '{what}' als connector niet aan (alleen lezen).",
            "details": {},
            "trace_id": str(uuid.uuid4()),
        },
        status_code=501,
    )


@router.post("/connector/v1/propose", summary="Connector: niet beschikbaar (501)")
def propose(_: ViewerOrService) -> JSONResponse:
    return _unavailable("propose")


@router.post("/connector/v1/apply", summary="Connector: niet beschikbaar (501)")
def apply(_: ViewerOrService) -> JSONResponse:
    return _unavailable("apply")


@router.post("/connector/v1/rollback", summary="Connector: niet beschikbaar (501)")
def rollback(_: ViewerOrService) -> JSONResponse:
    return _unavailable("rollback")


@router.get("/connector/v1/evidence/{evidence_id}", summary="Connector: geredigeerd bewijs (alleen gebruikers)")
def evidence(evidence_id: str, db: DB, _: UsersOnly) -> dict[str, Any]:
    kind, _sep, ident = evidence_id.partition(":")
    try:
        if kind == "backup":
            b = db.get(SelfBackup, uuid.UUID(ident))
            if b is not None:
                return {"id": evidence_id, "soort": "eigen_backup", "bewijs": backup_dict(b)}
        elif kind == "inventory_run":
            r = db.get(InventoryRun, uuid.UUID(ident))
            if r is not None:
                return {
                    "id": evidence_id,
                    "soort": "inventaris",
                    "bewijs": {
                        "status": r.status,
                        "reason_code": r.reason_code,
                        "nas_versie": r.nas_version,
                        "capability_bron": r.capability_source,
                        "key_scope": r.key_scope,
                        "gestart": iso(r.started_at),
                        "klaar": iso(r.finished_at),
                        "aanleiding": r.trigger,
                    },
                }
        elif kind == "audit":
            a = db.get(AuditEvent, int(ident))
            if a is not None:
                return {
                    "id": evidence_id,
                    "soort": "audit",
                    "bewijs": {
                        "op": iso(a.at),
                        "actor": f"{a.actor_type}:{a.actor_id}",
                        "actie": a.action,
                        "doel": f"{a.target_type}:{a.target_id}",
                        "details": a.details,
                    },
                }
    except ValueError:
        pass
    raise HubError(404, "not_found", "Bewijs niet gevonden (formaat: backup:<id>, inventory_run:<id>, audit:<id>).")


@router.get("/connector/v1/events", summary="Connector: outbox van de Hub (cursor; alleen gebruikers, viewer+)")
def outbox(db: DB, _: UsersOnly, cursor: Cursor = None, limit: Limit = 100) -> dict[str, Any]:
    after = decode_cursor(cursor) or 0
    rows = list(db.scalars(select(OutboxEvent).where(OutboxEvent.seq > after).order_by(OutboxEvent.seq).limit(limit)))
    return {
        "items": [outbox_to_envelope(r, APP_ID) for r in rows],
        "next_cursor": encode_cursor(rows[-1].seq) if rows else (cursor or None),
    }
