"""Opslag van inventaris-momentopnamen en afleiding van de actuele toestand (met ``observed_at`` en veroudering).

Regels: de laatste poging bepaalt de status. Mislukte poging → ``unknown`` met reason_code; de laatst bekende data wordt
wel getoond maar als ``verouderd``. Een geslaagde meting ouder dan de TTL → ``unknown`` (``stale``). Inventaris van een
ander NAS-adres dan het huidige (D03 gewijzigd) telt niet mee.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.inventory.collector import CollectResult
from hub.models import InventoryRun, InventorySnapshot
from hub.timeutil import iso, utcnow
from hub.truenas.messages import advice, message


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
    return db.scalars(q.order_by(InventorySnapshot.observed_at.desc()).limit(1)).first()


def kind_state(
    db: Session, kind: str, *, target: str | None, ttl_seconds: int, now: datetime | None = None
) -> dict[str, Any]:
    now = now or utcnow()
    base: dict[str, Any] = {
        "kind": kind,
        "status": "unknown",
        "reason_code": "not_configured",
        "melding": message("not_configured"),
        "advies": advice("not_configured"),
        "observed_at": None,
        "laatste_poging": None,
        "verouderd": False,
        "bron": None,
        "data": None,
    }
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
    base.update(status="ok", reason_code=None, melding="", advies="", verouderd=False)
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
