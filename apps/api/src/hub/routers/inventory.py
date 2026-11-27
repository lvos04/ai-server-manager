"""Inventaris (alleen-lezen), dienstenregister en jobs.

Endpoints tonen altijd ``status``, ``observed_at`` en ``verouderd``; verouderde of mislukte metingen zijn ``unknown``.
Er wordt hier nooit iets geïnstalleerd of gewijzigd op de NAS.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import audit
from hub.adapters.binding import confirmed_binding
from hub.config import Settings
from hub.deps import (
    DB,
    SESSION_COOKIE,
    Cursor,
    Idem,
    Limit,
    Operator,
    Principal,
    SettingsDep,
    Viewer,
    decode_cursor,
    encode_cursor,
    require_viewer_or_scope,
)
from hub.errors import HubError, trace_id_of
from hub.inventory.poolstatus import Poolmeting, projecteer
from hub.inventory.store import kind_state, latest_run
from hub.jobs import job_dict
from hub.models import AdapterLink, Decision, Job, Service
from hub.scopes import POOLSTATUS_LEZEN
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target

router = APIRouter(prefix="/api/v1", tags=["inventaris"])
PoolReader = Annotated[Principal, Depends(require_viewer_or_scope(POOLSTATUS_LEZEN))]

PUBLIC_KINDS = {
    "apps": "apps",
    "images": "images",
    "pools": "pools",
    "datasets": "datasets",
    "gpus": "gpus",
    "disks": "disks",
    "smart": "smart",
    "snapshot-taken": "snapshot_tasks",
    "cloud-sync": "cloudsync",
    "replicatie": "replication",
    "alerts": "alerts",
    "netwerk": "network",
    "systeem": "system",
}


def _target(db: Session) -> str | None:
    t = current_target(db)
    return t.url if t else None


def _state(db: Session, settings: Settings, kind: str) -> dict[str, Any]:
    return kind_state(db, kind, target=_target(db), ttl_seconds=settings.inventory_max_age_seconds)


def app_status(app: dict[str, Any], stale: bool) -> str:
    if stale:
        return "onbekend"
    return {"RUNNING": "draait", "STOPPED": "gestopt", "CRASHED": "gecrasht", "DEPLOYING": "bezig"}.get(
        str(app.get("staat") or ""), "onbekend"
    )


@router.get("/inventory", summary="Overzicht per soort: status, observed_at, veroudering")
def inventory_summary(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    target = _target(db)
    run = latest_run(db, target) if target else None
    kinds = []
    for public, kind in PUBLIC_KINDS.items():
        st = _state(db, settings, kind)
        data = st.pop("data")
        st["aantal"] = len(data) if isinstance(data, list) else None
        st["pad"] = f"/api/v1/inventory/{public}"
        kinds.append(st)
    return {
        "nas_url": target,
        "laatste_run": None
        if run is None
        else {
            "id": str(run.id),
            "gestart": iso(run.started_at),
            "klaar": iso(run.finished_at),
            "status": run.status,
            "reason_code": run.reason_code,
            "nas_versie": run.nas_version,
            "capability_bron": run.capability_source,
            "key_scope": run.key_scope,
            "aanleiding": run.trigger,
        },
        "soorten": kinds,
        "ttl_seconden": settings.inventory_max_age_seconds,
        "alleen_lezen": True,
    }


@router.get(
    "/inventory/pools",
    summary="Poolinventaris voor een kijker of de gekoppelde MediaGuard-dienstidentiteit",
    response_model=None,
    dependencies=[
        Depends(
            HTTPBearer(scheme_name="MediaGuardPooltoken", description="Token voor poolstatus.lezen", auto_error=False)
        ),
        Depends(APIKeyCookie(name=SESSION_COOKIE, scheme_name="HubSessie", auto_error=False)),
    ],
    responses={
        200: {
            "model": Poolmeting | dict[str, Any],
            "description": "MediaGuard ontvangt Poolmeting. Een kijker ontvangt de bestaande gepagineerde inventaris.",
        },
        400: {"description": "MediaGuard vraagt de meting zonder queryparameters op"},
        401: {"description": "Geen geldige sessie of ongeldig, vervangen of ingetrokken poolleestoken"},
        403: {"description": "Onvoldoende gebruikersrol, ontbrekende scope of onbevestigde adapterbinding"},
    },
)
def inventory_pools(
    request: Request,
    response: Response,
    db: DB,
    settings: SettingsDep,
    principal: PoolReader,
    limit: Limit = 200,
    cursor: Cursor = None,
) -> Poolmeting | dict[str, Any]:
    """MediaGuard stuurt `Authorization: Bearer <pool_token>` met scope `poolstatus.lezen`.
    De dienst krijgt alle toestanden uit één meting, zonder queryparameters of paginering."""
    response.headers["Cache-Control"] = "no-store"
    if principal.kind == "user":
        return _inventory_page(_state(db, settings, "pools"), limit, cursor)
    link = db.get_one(AdapterLink, uuid.UUID(principal.id))
    nas = current_target(db)
    if nas is None or not confirmed_binding(db, settings, link, nas):
        raise HubError(
            403, "forbidden", "De MediaGuard-koppeling kan niet worden bevestigd.", {"reason": "doelbinding"}
        )
    if request.query_params:
        raise HubError(400, "bad_request", "De volledige poolmeting wordt zonder queryparameters opgevraagd.")
    nu = utcnow()
    staat = kind_state(db, "pools", target=nas.url, ttl_seconds=settings.inventory_max_age_seconds, now=nu)
    meting = projecteer(staat, nu)
    audit.record(
        db,
        actor_type="service",
        actor_id=link.app_id,
        action="inventory.pools.read",
        target_type="adapter_link",
        target_id=principal.id,
        details={"scope": POOLSTATUS_LEZEN},
        trace_id=trace_id_of(request),
    )
    db.commit()
    return meting


@router.get("/inventory/{soort}", summary="Eén soort uit de inventaris (alleen-lezen)")
def inventory_kind(
    soort: str, db: DB, settings: SettingsDep, _: Viewer, limit: Limit = 200, cursor: Cursor = None
) -> dict[str, Any]:
    kind = PUBLIC_KINDS.get(soort)
    if kind is None:
        raise HubError(404, "not_found", f"Onbekende soort; kies uit: {', '.join(PUBLIC_KINDS)}.")
    return _inventory_page(_state(db, settings, kind), limit, cursor)


def _inventory_page(st: dict[str, Any], limit: int, cursor: str | None) -> dict[str, Any]:
    data = st.get("data")
    if isinstance(data, list):
        offset = decode_cursor(cursor) or 0
        page = data[offset : offset + limit]
        if st["kind"] == "apps":
            stale = st["status"] != "ok"
            page = [
                {
                    **a,
                    "status": app_status(a, stale),
                    "gezondheid": "unknown"
                    if stale
                    else ("down" if a.get("staat") in ("STOPPED", "CRASHED") else "unknown"),
                    "gezondheid_toelichting": "Gezondheid volgt uit de connector van de app (P3); de TrueNAS-staat "
                    "alleen is geen bewijs van gezond.",
                }
                for a in page
            ]
        st["items"] = page
        st["next_cursor"] = encode_cursor(offset + limit) if offset + limit < len(data) else None
        st["totaal"] = len(data)
        del st["data"]
    return st


@router.post("/inventory/refresh", status_code=202, summary="Inventaris vernieuwen (job; alleen-lezen op de NAS)")
def refresh(db: DB, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    job = db.scalars(select(Job).where(Job.kind == "inventory_refresh", Job.status.in_(("queued", "running")))).first()
    if job is None:
        job = Job(kind="inventory_refresh", status="queued", requested_by=principal.actor, params={"trigger": "manual"})
        db.add(job)
        db.flush()
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="inventory.refresh_requested",
            target_type="job",
            target_id=str(job.id),
        )
    return idem.save(202, job_dict(job))


@router.get("/jobs/{job_id}", summary="Status van een job")
def get_job(job_id: uuid.UUID, db: DB, _: Viewer) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if job is None:
        raise HubError(404, "not_found", "Job niet gevonden.")
    return job_dict(job)


@router.get("/jobs", summary="Recente jobs")
def list_jobs(db: DB, _: Viewer, limit: Limit = 50) -> dict[str, Any]:
    rows = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit))
    return {"items": [job_dict(j) for j in rows]}


# ------------------------------------------------------------------ dienstenregister
@router.get(
    "/registry/services", summary="Dienstenregister: app → basis-URL (NAS-adres uit D03 + hostpoort uit app.query)"
)
def registry(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    d03 = db.get(Decision, "D03")
    adres = None
    if d03 is not None and d03.status in ("Ingevuld", "Getest") and isinstance(d03.waarde, dict):
        adres = str(d03.waarde.get("nas_adres") or "") or None
    st = _state(db, settings, "apps")
    services = list(db.scalars(select(Service)))
    enrolled = {s.app_id: s for s in services}
    by_app_name = {s.truenas_app_name: s for s in services if s.truenas_app_name}
    items = []
    for a in st.get("data") or []:
        ports = [p for p in a.get("poorten") or [] if p.get("host_poort") and p.get("protocol") == "tcp"]
        host = f"[{adres}]" if adres and ":" in adres else adres
        urls = [f"http://{host}:{p['host_poort']}" for p in ports] if adres else []
        key = a.get("herkend_als") or a["naam"]
        svc = by_app_name.get(str(a["naam"])) or enrolled.get(str(key)) or enrolled.get(str(a["naam"]))
        items.append(
            {
                "app": a["naam"],
                "herkend_als": a.get("herkend_als"),
                "basis_url": urls[0] if urls else None,
                "alle_urls": urls,
                "reden_geen_url": None if urls else ("nas_adres_onbekend (D03)" if not adres else "geen_tcp_hostpoort"),
                "hostpoorten": [p["host_poort"] for p in ports],
                "bron": {
                    "poorten": "app.query",
                    "nas_adres": "D03" if adres else None,
                    "observed_at": st.get("observed_at"),
                },
                "verouderd": st.get("status") != "ok",
                "ingeschreven_dienst": None
                if svc is None
                else {"id": str(svc.id), "status": svc.status, "versie": svc.version},
                "geinstalleerd_door_hub": False,
            }
        )
    return {
        "items": items,
        "status": st["status"],
        "reason_code": st.get("reason_code"),
        "observed_at": st.get("observed_at"),
        "toelichting": "Alleen registratie; er wordt niets geïnstalleerd.",
    }
