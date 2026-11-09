"""Worker: hartslag, geplande inventaris en eigen back-up, jobs uitvoeren, opruimen.

Jobs worden geclaimd met ``FOR UPDATE SKIP LOCKED`` (meerdere workers mogelijk, geen dubbele uitvoering).
"""

from __future__ import annotations

import asyncio
import logging
import signal
import threading
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from hub.backup.selfbackup import run_self_backup
from hub.config import Settings
from hub.events.envelope import emit
from hub.inventory.store import latest_run, prune_runs, save_run
from hub.keys import KeyRing
from hub.models import EnrollmentGrant, IdempotencyRecord, Job, LoginAttempt, SelfBackup, WebSession, WorkerHeartbeat
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target, run_collect
from hub.vault import Vault

log = logging.getLogger("hub.worker")


def heartbeat(db: Session, details: dict[str, Any]) -> None:
    hb = db.get(WorkerHeartbeat, "worker")
    if hb is None:
        db.add(WorkerHeartbeat(name="worker", beat_at=utcnow(), details=details))
    else:
        hb.beat_at, hb.details = utcnow(), details
    db.commit()


def _enqueue_if_due(db: Session, settings: Settings) -> list[str]:
    queued: list[str] = []
    now = utcnow()
    active = {j.kind for j in db.scalars(select(Job).where(Job.status.in_(("queued", "running"))))}
    target = current_target(db)
    if target is not None and "inventory_refresh" not in active:
        run = latest_run(db, target.url)
        if run is None or now - run.started_at > timedelta(seconds=settings.inventory_interval_seconds):
            db.add(
                Job(
                    kind="inventory_refresh",
                    status="queued",
                    requested_by="system:schema",
                    params={"trigger": "schema"},
                )
            )
            queued.append("inventory_refresh")
    if "self_backup" not in active:
        last = db.scalars(select(SelfBackup).order_by(SelfBackup.started_at.desc()).limit(1)).first()
        if last is None or now - last.started_at > timedelta(seconds=settings.self_backup_interval_seconds):
            db.add(
                Job(kind="self_backup", status="queued", requested_by="system:schema", params={"trigger": "schedule"})
            )
            queued.append("self_backup")
    db.commit()
    return queued


def _claim(db: Session) -> Job | None:
    job = db.scalars(
        select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1).with_for_update(skip_locked=True)
    ).first()
    if job is None:
        db.rollback()
        return None
    job.status, job.started_at = "running", utcnow()
    db.commit()
    return job


def _run_job(db: Session, settings: Settings, vault: Vault, job: Job) -> dict[str, Any]:
    if job.kind == "inventory_refresh":
        started = utcnow()
        res = asyncio.run(run_collect(db, vault, settings))
        if res.reason_code == "not_configured":
            return {"status": "unknown", "reason_code": "not_configured"}
        run = save_run(db, res, trigger=str(job.params.get("trigger") or "manual"), started_at=started)
        emit(
            db,
            "inventory.run.completed",
            "inventory_run",
            str(run.id),
            {"status": res.status, "reason_code": res.reason_code},
        )
        db.commit()
        return {
            "status": res.status,
            "reason_code": res.reason_code,
            "run_id": str(run.id),
            "soorten": {k.kind: k.status for k in res.kinds},
        }
    if job.kind == "self_backup":
        row = run_self_backup(db, settings, trigger=str(job.params.get("trigger") or "manual"))
        emit(
            db,
            "backup.run.succeeded" if row.status == "geslaagd" else "backup.run.failed",
            "self_backup",
            str(row.id),
            {"status": row.status, "reason_code": row.reason_code, "sha256": row.sha256},
        )
        db.commit()
        return {"status": row.status, "reason_code": row.reason_code, "backup_id": str(row.id)}
    return {"status": "failed", "reason_code": "unknown_job_kind"}


def cleanup(db: Session) -> None:
    now = utcnow()
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < now - timedelta(days=1)))
    db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.created_at < now - timedelta(days=1)))
    db.execute(delete(WebSession).where(WebSession.expires_at < now - timedelta(days=7)))
    db.execute(delete(EnrollmentGrant).where(EnrollmentGrant.expires_at < now - timedelta(days=30)))
    prune_runs(db, keep=50)
    db.commit()


def run_once(
    factory: sessionmaker[Session], settings: Settings, vault: Vault, *, schedule: bool = True
) -> list[dict[str, Any]]:
    """Eén ronde: hartslag, plannen, alle wachtende jobs uitvoeren. Geeft de uitgevoerde jobs terug (voor tests)."""
    done: list[dict[str, Any]] = []
    with factory() as db:
        heartbeat(db, {"laatste_ronde": iso(utcnow())})
        if schedule:
            _enqueue_if_due(db, settings)
        while (job := _claim(db)) is not None:
            try:
                result = _run_job(db, settings, vault, job)
                job.status = "done" if result.get("status") not in ("failed",) else "failed"
            except Exception as exc:
                db.rollback()
                log.exception("job %s mislukt", job.id)
                result = {"status": "failed", "reason_code": "exception", "fout": type(exc).__name__}
                job = db.get(Job, job.id) or job
                job.status = "failed"
            job.result, job.finished_at = result, utcnow()
            db.commit()
            done.append({"id": str(job.id), "kind": job.kind, **result})
        cleanup(db)
    return done


def main(settings: Settings) -> int:
    from hub.db import make_engine, make_sessionmaker

    engine = make_engine(settings.database_url)
    factory = make_sessionmaker(engine)
    KeyRing.load(settings.secrets_dir)  # faalt vroeg als geheimen ontbreken
    vault = Vault.from_file(settings.secrets_dir / "vault.key")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    log.info("worker gestart (interval %.0f s)", settings.worker_poll_seconds)
    while not stop.is_set():
        try:
            for j in run_once(factory, settings, vault):
                log.info("job %s (%s): %s %s", j["id"], j["kind"], j.get("status"), j.get("reason_code") or "")
        except Exception:
            log.exception("worker-ronde mislukt; volgende ronde over %.0f s", settings.worker_poll_seconds)
        stop.wait(settings.worker_poll_seconds)
    engine.dispose()
    log.info("worker gestopt")
    return 0
