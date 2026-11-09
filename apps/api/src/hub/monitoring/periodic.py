"""Periodieke taken van de worker (B09): gezondheid vastleggen, tijdreeksonderhoud, alerts en meldingen.

Elke taak heeft een rij in ``periodic_task`` (laatst gestart/klaar, status, duur) die met ``FOR UPDATE SKIP LOCKED``
wordt geclaimd: meerdere workers voeren een taak nooit dubbel uit. Een fout in één taak stopt de andere niet en wordt
vastgelegd (nooit stil).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from hub.catalog.discovery import is_inventory_fresh
from hub.config import Settings
from hub.inventory.store import kind_state
from hub.keys import KeyRing
from hub.models import CatalogApp, PeriodicTask
from hub.monitoring import alerts, timeseries
from hub.monitoring.appstatus import app_health
from hub.monitoring.health import status_value
from hub.monitoring.timeseries import Sample
from hub.notify.dispatch import dispatch
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target
from hub.vault import Vault

log = logging.getLogger("hub.worker.periodiek")


@dataclass
class Context:
    settings: Settings
    vault: Vault
    keyring: KeyRing | None
    now: datetime


@dataclass(frozen=True)
class Task:
    naam: str
    interval: Callable[[Settings], float]
    run: Callable[[Session, Context], dict[str, Any]]


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def inventory_samples(db: Session, settings: Settings, now: datetime | None = None) -> list[Sample]:
    """Pool-gebruik, vrije ruimte en gezondheid uit een verse ``pool.query``-meting (geen meting → geen samples)."""
    target = current_target(db)
    st = kind_state(
        db, "pools", target=target.url if target else None, ttl_seconds=settings.inventory_ttl_seconds, now=now
    )
    observed = _parse(st.get("observed_at"))
    if st["status"] != "ok" or observed is None:
        return []
    out: list[Sample] = []
    for p in st.get("data") or []:
        name = str(p.get("naam") or "")
        if not name:
            continue
        if isinstance(p.get("gebruik_pct"), int | float):
            out.append(
                Sample("pool", name, "pool.gebruik", "%", "truenas.pool.query", observed, float(p["gebruik_pct"]))
            )
        if isinstance(p.get("vrij_bytes"), int | float):
            out.append(Sample("pool", name, "pool.vrij", "B", "truenas.pool.query", observed, float(p["vrij_bytes"])))
        if isinstance(p.get("gezond"), bool):
            out.append(
                Sample(
                    "pool",
                    name,
                    "pool.gezond",
                    "status",
                    "truenas.pool.query",
                    observed,
                    1.0 if p["gezond"] else 0.0,
                    {"status": p.get("status")},
                )
            )
    return out


def record_inventory_metrics(db: Session, settings: Settings, now: datetime | None = None) -> dict[str, Any]:
    return timeseries.record(db, settings, inventory_samples(db, settings, now), now=now).as_dict()


def _task_health(db: Session, ctx: Context) -> dict[str, Any]:
    """Gezondheid per aanwezige app als reeks ``app.status`` (1/0.5/0; ``unknown`` → geen meting, een gat)."""
    inv = is_inventory_fresh(db, ctx.settings, ctx.now)
    samples = []
    unknown = 0
    for row in db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True))):
        h = app_health(db, ctx.settings, row, inv, ctx.now)
        v = status_value(h["status"])
        if v is None:
            unknown += 1
            continue
        samples.append(
            Sample("app", str(row.id), "app.status", "status", "hub.gezondheid", ctx.now, v, {"naam": row.naam})
        )
    res = timeseries.record(db, ctx.settings, samples, now=ctx.now).as_dict()
    return {**res, "onbekend": unknown}


def _task_maintenance(db: Session, ctx: Context) -> dict[str, Any]:
    row = db.get(PeriodicTask, "tijdreeksen_onderhoud")
    previous = row.laatst_klaar if row is not None else None
    since = (
        (previous - timedelta(minutes=10))
        if previous
        else ctx.now - timedelta(seconds=ctx.settings.metrics_raw_retention_seconds)
    )
    return {"aggregatie": timeseries.rollup(db, since=since), "retentie": timeseries.prune(db, now=ctx.now)}


def _task_sources(db: Session, ctx: Context) -> dict[str, Any]:
    from hub.monitoring.sources import poll_all

    return poll_all(db, ctx.settings, ctx.vault, ctx.keyring, now=ctx.now)


def _task_alerts(db: Session, ctx: Context) -> dict[str, Any]:
    added = alerts.seed_default_rules(db)
    return {"standaardregels_toegevoegd": added, **alerts.evaluate(db, ctx.settings, now=ctx.now)}


def _task_notify(db: Session, ctx: Context) -> dict[str, Any]:
    return dispatch(db, ctx.settings, ctx.vault, now=ctx.now)


TASKS: list[Task] = [
    Task("bronnen_pollen", lambda s: s.monitoring_interval_seconds, _task_sources),
    Task("gezondheid_vastleggen", lambda s: s.health_record_interval_seconds, _task_health),
    Task("alerts_evalueren", lambda s: s.alert_interval_seconds, _task_alerts),
    Task("meldingen_versturen", lambda s: 0, _task_notify),
    Task("tijdreeksen_onderhoud", lambda s: s.metrics_maintenance_interval_seconds, _task_maintenance),
]


def _claim(db: Session, task: Task, now: datetime, force: bool, settings: Settings) -> PeriodicTask | None:
    row = db.scalars(
        select(PeriodicTask).where(PeriodicTask.naam == task.naam).with_for_update(skip_locked=True)
    ).first()
    if row is None:
        db.add(PeriodicTask(naam=task.naam, details={}))
        try:
            db.flush()
        except IntegrityError:  # een andere worker maakte de rij tegelijk aan
            db.rollback()
            return None
        row = db.scalars(
            select(PeriodicTask).where(PeriodicTask.naam == task.naam).with_for_update(skip_locked=True)
        ).first()
        if row is None:
            return None
    recent = row.laatst_gestart is not None and (now - row.laatst_gestart).total_seconds() < task.interval(settings)
    if recent and not force:
        db.rollback()
        return None
    row.laatst_gestart = now
    db.commit()
    return row


def run_due(
    factory: sessionmaker[Session],
    settings: Settings,
    vault: Vault,
    keyring: KeyRing | None,
    *,
    now: datetime | None = None,
    force: bool = False,
    only: set[str] | None = None,
    tasks: list[Task] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for task in tasks or TASKS:
        if only is not None and task.naam not in only:
            continue
        ctx = Context(settings, vault, keyring, now or utcnow())
        with factory() as db:
            if _claim(db, task, ctx.now, force, settings) is None:
                continue
            started = time.monotonic()
            try:
                details = task.run(db, ctx)
                db.commit()
                status, reason = "ok", None
            except Exception as exc:
                db.rollback()
                log.exception("periodieke taak %s mislukt", task.naam)
                details, status, reason = {"fout": type(exc).__name__}, "failed", "exception"
            row = db.get(PeriodicTask, task.naam)
            if row is not None:
                row.laatst_klaar = ctx.now if now is not None else utcnow()
                row.laatste_status, row.laatste_reden = status, reason
                row.duur_ms = int((time.monotonic() - started) * 1000)
                row.details = details
                db.commit()
            out.append({"taak": task.naam, "status": status, **details})
    return out


def task_dict(row: PeriodicTask, interval: float) -> dict[str, Any]:
    return {
        "naam": row.naam,
        "interval_s": interval,
        "laatst_gestart": iso(row.laatst_gestart),
        "laatst_klaar": iso(row.laatst_klaar),
        "status": row.laatste_status or "unknown",
        "reden": row.laatste_reden,
        "duur_ms": row.duur_ms,
        "details": row.details,
    }
