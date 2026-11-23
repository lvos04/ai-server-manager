"""Back-up en herstel (B12-001/002/003): dekking, snapshotbeleid-voorstel, eigen pg_dump-export en hersteltests."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import audit
from hub.backup import bronmetingen, hersteltest, rampenscenario
from hub.backup import coverage as cov
from hub.backup.selfbackup import latest_verified, reverify, to_dict
from hub.config import Settings
from hub.deps import DB, Admin, Idem, Operator, SettingsDep, Viewer, get_vault
from hub.errors import HubError
from hub.inventory.store import kind_state
from hub.jobs import job_dict
from hub.models import Decision, Herstelpunt, Job, RestoreTest, SelfBackup, Service
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target
from hub.vault import Vault

router = APIRouter(prefix="/api/v1/backups", tags=["back-up en herstel"])


class RestoreTestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")
    dataset: str | None = Field(default=None, max_length=512)
    soort: Literal["foto", "database", "dataset", "config"]
    resultaat: Literal["geslaagd", "mislukt"]
    omgeving: str = Field(min_length=3, max_length=256, description="Geïsoleerde omgeving (nooit productie).")
    omschrijving: str = Field(min_length=10, max_length=2000)
    referentie: str = Field(default="", max_length=512)
    duur_minuten: int | None = Field(default=None, ge=0, le=60 * 24 * 14)
    uitgevoerd_op: datetime

    @model_validator(mode="after")
    def _target(self) -> RestoreTestIn:
        if not self.app_id and not self.dataset:
            raise ValueError("geef app_id of dataset")
        if self.uitgevoerd_op.tzinfo is None:
            raise ValueError("uitgevoerd_op moet een tijdzone hebben")
        return self


def restore_dict(r: RestoreTest) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "app_id": r.app_id,
        "dataset": r.dataset,
        "soort": r.soort,
        "resultaat": r.resultaat,
        "omgeving": r.omgeving,
        "omschrijving": r.omschrijving,
        "referentie": r.referentie,
        "duur_minuten": r.duur_minuten,
        "uitgevoerd_op": iso(r.uitgevoerd_op),
        "vastgelegd_door": r.vastgelegd_door,
        "vastgelegd_op": iso(r.vastgelegd_op),
    }


def coverage_inputs(db: Session, settings: Settings) -> cov.CoverageInputs:
    target = current_target(db)
    url = target.url if target else None

    def st(kind: str) -> dict[str, Any]:
        return kind_state(db, kind, target=url, ttl_seconds=settings.inventory_max_age_seconds)

    extra: list[str] = []
    d02 = db.get(Decision, "D02")
    if d02 is not None and d02.status in ("Ingevuld", "Getest") and isinstance(d02.waarde, dict):
        extra = [*d02.waarde.get("appdata_datasets", []), *d02.waarde.get("media_datasets", [])]
    b = latest_verified(db)
    return cov.CoverageInputs(
        apps=st("apps"),
        datasets=st("datasets"),
        pools=st("pools"),
        snapshot_tasks=st("snapshot_tasks"),
        latest_snapshots=st("latest_snapshots"),
        cloudsync=st("cloudsync"),
        replication=st("replication"),
        rpo_rto=bronmetingen.rpo_doelen(db),
        self_backup={"finished_at": b.finished_at, "sha256": b.sha256, "id": str(b.id)}
        if b and b.finished_at
        else None,
        self_backup_max_age_seconds=settings.self_backup_interval_seconds + 2 * 3600,
        restore_tests=[restore_dict(r) for r in db.scalars(select(RestoreTest))],
        enrolled_apps={s.app_id for s in db.scalars(select(Service).where(Service.status == "active"))},
        extra_datasets=extra,
        app_bronnen=bronmetingen.lees(db, settings),
    )


class AppBackupView(BaseModel):
    naam: str
    status: Literal["gedekt", "degraded", "unknown"]
    reden: str | None
    observed_at: str | None
    geldig_tot: str | None
    gemaakt_op: str | None
    leeftijd_uren: float | None
    aanwezig: bool | None
    plaats: str | None
    vereist: bool


class CoverageView(BaseModel):
    apps: list[dict[str, Any]]
    datasets: list[dict[str, Any]]
    bronnen: dict[str, Any]
    app_backups: dict[str, AppBackupView]
    opmerking: str
    afgeleid_op: str


@router.get(
    "/coverage",
    response_model=CoverageView,
    summary="Dekking per app en dataset (lokaal, extern, DB-export, hersteltest, RPO/RTO)",
)
def get_coverage(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    return cov.compute(coverage_inputs(db, settings))


@router.get("/snapshot-policy/proposal", summary="Snapshotbeleid als voorstel (wordt niet toegepast)")
def get_policy_proposal(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    inp = coverage_inputs(db, settings)
    return cov.snapshot_policy_proposal(inp, cov.compute(inp))


@router.get("/extern", summary="Verificatie van de externe back-up (OneDrive-uploadtaken uit D04, B12-004)")
def get_extern(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    from hub.routers.onboarding import gate_inputs

    uit = gate_inputs(db, settings).extern_backup
    db.commit()
    return {**(uit or {}), "opmerking": cov.SYNC_IS_GEEN_GARANTIE}


@router.get("/herstelpunten", summary="Herstelpunten per app (B12-006): snapshot, database-export en status")
def list_herstelpunten(db: DB, _: Viewer, app: str | None = None) -> dict[str, Any]:
    q = select(Herstelpunt).order_by(Herstelpunt.gemaakt_op.desc()).limit(100)
    if app:
        q = q.where(Herstelpunt.app == app)
    return {
        "items": [
            {
                "id": str(h.id),
                "app": h.app,
                "checkpoint_id": h.checkpoint_id,
                "gemaakt_op": iso(h.gemaakt_op),
                "snapshot": h.snapshot,
                "db_export": h.db_export,
                "status": h.status,
                "reden": h.reden,
                "vastgelegd_op": iso(h.vastgelegd_op),
            }
            for h in db.scalars(q)
        ],
        "regel": "Alleen een geverifieerd herstelpunt jonger dan de RPO uit D16 telt; voor Emby, de mediaserver en "
        "MediaGuard alleen met de database erin.",
    }


class HersteltestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    klonen: list[uuid.UUID] = Field(
        min_length=1,
        max_length=32,
        description="De uitgevoerde zfs.snapshot.clone_to_sandbox-voorstellen (één per dataset van het herstelpunt).",
    )


@router.post(
    "/herstelpunten/{herstelpunt_id}/hersteltest",
    summary="Hersteltest-robot (B12-005): kloon in de zandbak, export in een proefdatabase, productie onveranderd",
)
def run_hersteltest(
    herstelpunt_id: uuid.UUID,
    body: HersteltestIn,
    db: DB,
    settings: SettingsDep,
    vault: Annotated[Vault, Depends(get_vault)],
    principal: Admin,
    idem: Idem,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    hp = db.get(Herstelpunt, herstelpunt_id)
    if hp is None:
        raise HubError(404, "not_found", "Herstelpunt niet gevonden.")
    uit = hersteltest.voer_uit(db, settings, vault, hp, body.klonen, door=principal.name)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="backup.hersteltest",
        target_type="herstelpunt",
        target_id=str(hp.id),
        details={"resultaat": uit["resultaat"], "reden": uit["reden"], "restore_test": uit["restore_test"]},
    )
    return idem.save(200, uit)


@router.get("/rampenscenario", summary="Rampenscenario (B12-007): herstelstappen via de Hub en de TrueNAS-web-UI")
def get_rampenscenario(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    inp = coverage_inputs(db, settings)
    return {
        "scenarios": rampenscenario.SCENARIOS,
        "rpo_rto": inp.rpo_rto,
        "laatste_hersteltests": [
            {k: t[k] for k in ("app_id", "resultaat", "duur_minuten", "uitgevoerd_op")}
            for t in sorted(inp.restore_tests, key=lambda t: str(t["uitgevoerd_op"]), reverse=True)[:20]
        ],
        "regel": rampenscenario.REGEL,
    }


@router.get("/self", summary="Eigen database-exports (pg_dump) met verificatie")
def list_self(db: DB, _: Viewer) -> dict[str, Any]:
    rows = db.scalars(select(SelfBackup).order_by(SelfBackup.started_at.desc()).limit(50))
    b = latest_verified(db)
    return {"items": [to_dict(r) for r in rows], "laatste_geverifieerd": to_dict(b) if b else None}


@router.post("/self", status_code=202, summary="Nu een eigen database-export maken (job)")
def run_self(db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    job = db.scalars(select(Job).where(Job.kind == "self_backup", Job.status.in_(("queued", "running")))).first()
    if job is None:
        job = Job(kind="self_backup", status="queued", requested_by=principal.actor, params={"trigger": "manual"})
        db.add(job)
        db.flush()
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="backup.self_requested",
            target_type="job",
            target_id=str(job.id),
        )
    return idem.save(202, job_dict(job))


@router.post("/self/{backup_id}/verify", summary="Bestaande export opnieuw verifiëren (checksum + inhoudsopgave)")
def verify_self(backup_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = db.get(SelfBackup, backup_id)
    if row is None:
        raise HubError(404, "not_found", "Back-up niet gevonden.")
    ver = reverify(db, settings, row)
    row.verification = {
        **(row.verification or {}),
        "herverificatie": {"ok": ver.ok, "reason_code": ver.reason_code, "op": iso(utcnow())},
    }
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="backup.self_reverified",
        target_type="backup",
        target_id=str(row.id),
        details={"ok": ver.ok, "reason_code": ver.reason_code},
    )
    return idem.save(
        200, {"backup": to_dict(row), "ok": ver.ok, "reason_code": ver.reason_code, "melding": ver.message}
    )


@router.get("/restore-tests", summary="Vastgelegde hersteltests (bewijsrecords)")
def list_restore_tests(db: DB, _: Viewer) -> dict[str, Any]:
    rows = db.scalars(select(RestoreTest).order_by(RestoreTest.uitgevoerd_op.desc()))
    return {"items": [restore_dict(r) for r in rows]}


@router.post(
    "/restore-tests", status_code=201, summary="Hersteltest vastleggen (expliciet bewijs; de Hub herstelt zelf niets)"
)
def add_restore_test(body: RestoreTestIn, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = RestoreTest(**body.model_dump(), vastgelegd_door=principal.name, vastgelegd_op=utcnow())
    db.add(row)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="backup.restore_test_recorded",
        target_type="restore_test",
        target_id=str(row.id),
        details={"soort": body.soort, "resultaat": body.resultaat},
    )
    return idem.save(201, restore_dict(row))
