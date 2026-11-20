"""Opslag van inventaris-momentopnamen en afleiding van de actuele toestand (met ``observed_at`` en veroudering).

Regels: de laatste poging bepaalt de status. Mislukte poging → ``unknown`` met reason_code; de laatst bekende data wordt
wel getoond maar als ``verouderd``. Een geslaagde meting ouder dan de TTL → ``unknown`` (``stale``). Inventaris van een
ander NAS-adres dan het huidige (D03 gewijzigd) telt niet mee.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from hub.catalog.identity import continuity
from hub.inventory.collector import CollectResult
from hub.models import CatalogApp, InventoryRun, InventorySnapshot
from hub.timeutil import iso, utcnow
from hub.truenas.messages import advice, message

# Interne momentopname naast app.query. De cataloguscontrole vergrendelt geen catalogusrij:
# een lopende adapterproef moet een nieuw opgeslagen poorteigenaar direct kunnen lezen.
_IDENTITY_KIND = "catalogus_identiteit"


def _last_identity(db: Session) -> InventorySnapshot | None:
    return db.scalar(
        select(InventorySnapshot)
        .where(InventorySnapshot.kind == _IDENTITY_KIND)
        .order_by(InventorySnapshot.observed_at.desc(), InventorySnapshot.id.desc())
        .limit(1)
    )


def _save_identity(db: Session, run: InventoryRun, data: Any) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('hub.catalogus_identiteit'))"))
    # Ook een vertraagde inventaris ziet een reeds vastgelegde onderbreking.
    # De grenstijd daarvan mag nooit terugschuiven naar een oudere bronmeting.
    recorded = utcnow()
    previous = _last_identity(db)
    earlier = None
    boundaries = {}
    if previous is not None:
        previous_run = db.get(InventoryRun, previous.run_id)
        if previous_run is not None and previous_run.target_url == run.target_url:
            earlier = db.scalar(
                select(InventorySnapshot.data).where(
                    InventorySnapshot.run_id == previous.run_id, InventorySnapshot.kind == "apps"
                )
            )
            boundaries = previous.data
    known = set(db.scalars(select(CatalogApp.runtime_id)))
    db.add(
        InventorySnapshot(
            run_id=run.id,
            kind=_IDENTITY_KIND,
            status="ok",
            method="app.query",
            message="",
            data=continuity(earlier, boundaries, data, known, recorded),
            observed_at=recorded,
        )
    )


def save_run(db: Session, result: CollectResult, *, trigger: str, started_at: datetime | None = None) -> InventoryRun:
    run = InventoryRun(
        started_at=started_at or utcnow(),
        finished_at=utcnow(),
        status=result.status,
        reason_code=result.reason_code,
        nas_version=result.nas_version,
        capability_source=result.capabilities.source if result.capabilities else None,
        capabilities=result.capabilities.as_dict() if result.capabilities else {},
        key_scope=result.key_scope,
        target_url=result.target_url,
        trigger=trigger,
    )
    db.add(run)
    db.flush()
    for k in result.kinds:
        if k.kind == "apps" and k.status == "ok":
            _save_identity(db, run, k.data)
        db.add(
            InventorySnapshot(
                run_id=run.id,
                kind=k.kind,
                status=k.status,
                reason_code=k.reason_code,
                message=k.message,
                method=k.method,
                data=k.data,
                observed_at=k.observed_at,
            )
        )
    db.flush()
    return run


def _latest(db: Session, kind: str, target: str, only_ok: bool) -> InventorySnapshot | None:
    q = (
        select(InventorySnapshot)
        .join(InventoryRun, InventoryRun.id == InventorySnapshot.run_id)
        .where(InventorySnapshot.kind == kind, InventoryRun.target_url == target)
    )
    if only_ok:
        q = q.where(InventorySnapshot.status == "ok")
    # Een traag antwoord op een oudere poging mag een nieuwere mislukking niet uitwissen.
    return db.scalars(
        q.order_by(
            InventoryRun.started_at.desc(), InventorySnapshot.observed_at.desc(), InventorySnapshot.id.desc()
        ).limit(1)
    ).first()


def kind_state(
    db: Session,
    kind: str,
    *,
    target: str | None,
    ttl_seconds: int,
    now: datetime | None = None,
    include_identity: bool = False,
) -> dict[str, Any]:
    now = now or utcnow()
    base: dict[str, Any] = {
        "kind": kind,
        "status": "unknown",
        "reason_code": "not_configured",
        "melding": message("not_configured"),
        "advies": advice("not_configured"),
        "observed_at": None,
        "geldig_tot": None,
        "laatste_poging": None,
        "verouderd": False,
        "bron": None,
        "data": None,
    }
    if include_identity:
        base["identiteit_sinds"] = {}
    if target is None:
        return base
    attempt = _latest(db, kind, target, only_ok=False)
    if attempt is None:
        base.update(reason_code="stale", melding="Nog niet gemeten.", advies="Vernieuw de inventaris.")
        return base
    last_ok = attempt if attempt.status == "ok" else _latest(db, kind, target, only_ok=True)
    base["laatste_poging"] = iso(attempt.observed_at)
    if last_ok is not None:
        base["observed_at"] = iso(last_ok.observed_at)
        base["data"] = last_ok.data
        base["bron"] = {"methode": last_ok.method, "nas": target}
        if include_identity:
            identity = _last_identity(db)
            if identity is not None and identity.run_id == last_ok.run_id:
                base["identiteit_sinds"] = identity.data
    if attempt.status != "ok":
        base.update(
            reason_code=attempt.reason_code,
            melding=attempt.message or message(attempt.reason_code),
            advies=advice(attempt.reason_code),
            verouderd=last_ok is not None,
        )
        return base
    if now - attempt.observed_at > timedelta(seconds=ttl_seconds):
        # Contract 1.3 §6.2: verouderd = unknown met meting_verouderd (laatst bekende data blijft zichtbaar).
        base.update(
            reason_code="meting_verouderd",
            melding=message("meting_verouderd"),
            advies=advice("meting_verouderd"),
            verouderd=True,
        )
        return base
    base.update(
        status="ok",
        reason_code=None,
        melding="",
        advies="",
        verouderd=False,
        geldig_tot=iso(attempt.observed_at + timedelta(seconds=ttl_seconds)),
    )
    return base


def latest_run(db: Session, target: str | None = None) -> InventoryRun | None:
    q = select(InventoryRun)
    if target is not None:
        q = q.where(InventoryRun.target_url == target)
    return db.scalars(q.order_by(InventoryRun.started_at.desc()).limit(1)).first()


def prune_runs(db: Session, keep: int = 50) -> int:
    ids = list(db.scalars(select(InventoryRun.id).order_by(InventoryRun.started_at.desc()).offset(keep)))
    for run_id in ids:
        run = db.get(InventoryRun, run_id)
        if run is not None:
            db.delete(run)
    return len(ids)
