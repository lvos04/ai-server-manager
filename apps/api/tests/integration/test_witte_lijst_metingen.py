"""R-VEILIG-2 en -3 (S-P2-060): alleen aantoonbaar geldige, verse metingen openen een gate. Echte database, echte
pg_dump-export en echte herverificatie; alleen tijdstippen en het exportbestand worden in de proef gewijzigd
(Sim-getest)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from conftest import idem
from sqlalchemy import select

pytestmark = pytest.mark.integration


def _export(admin: Any, worker_once: Any, app: Any) -> Any:
    from hub.models import SelfBackup

    assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
    assert worker_once()[-1]["status"] == "geslaagd"
    with app.state.sessionmaker() as db:
        return db.scalars(select(SelfBackup).order_by(SelfBackup.finished_at.desc()).limit(1)).one()


def _afkeuren(admin: Any, settings: Any, export: Any) -> None:
    (settings.backups_dir / export.file_name).rename(settings.backups_dir / (export.file_name + ".weg"))
    r = admin.post(f"/api/v1/backups/self/{export.id}/verify", headers=idem())
    assert r.status_code == 200 and r.json()["reason_code"] == "dump_missing", r.text


def _eigen_backup(app: Any, settings: Any) -> Any:
    from hub.routers.onboarding import gate_inputs

    with app.state.sessionmaker() as db:
        return gate_inputs(db, settings).eigen_backup


def test_afgekeurde_export_is_nooit_herstelbewijs(admin: Any, app: Any, settings: Any, worker_once: Any) -> None:
    """R-VEILIG-2: na een mislukte herverificatie telt de export niet meer; een oudere, nog geldige export of een
    nieuwe verse export mag de plaats innemen, verder niets."""
    from hub.backup.selfbackup import latest_verified

    oud = _export(admin, worker_once, app)
    nieuw = _export(admin, worker_once, app)
    _afkeuren(admin, settings, nieuw)
    assert _eigen_backup(app, settings)["id"] == str(oud.id)  # de andere, geverifieerde export
    _afkeuren(admin, settings, oud)
    assert _eigen_backup(app, settings) is None
    with app.state.sessionmaker() as db:
        assert latest_verified(db) is None
    gate = admin.get("/api/v1/gates/backup_gate").json()
    assert any(r["id"] == "eigen_backup" for r in gate["redenen"]), gate
    derde = _export(admin, worker_once, app)
    assert _eigen_backup(app, settings)["id"] == str(derde.id)


def test_poolmeting_in_de_toekomst_is_niet_vers(app: Any) -> None:
    """R-VEILIG-3: ``kind_state`` gebruikt beide grenzen; binnen de klokmarge vers, daarbuiten onbekend."""
    from hub.inventory.store import kind_state
    from hub.models import InventoryRun, InventorySnapshot
    from hub.timeutil import KLOKMARGE_SECONDEN, utcnow

    nu = utcnow()
    uitkomst = {}
    for naam, verschuiving in (("marge", KLOKMARGE_SECONDEN - 5), ("toekomst", 86400), ("oud", -61), ("vers", -59)):
        doel = f"sim-{naam}"
        meting = nu + timedelta(seconds=verschuiving)
        with app.state.sessionmaker() as db:
            run = InventoryRun(status="ok", target_url=doel, started_at=meting, finished_at=meting)
            db.add(run)
            db.flush()
            data = [{"naam": "p", "status": "ONLINE", "gezond": True}]
            db.add(InventorySnapshot(run_id=run.id, kind="pools", status="ok", data=data, observed_at=meting))
            db.flush()
            st = kind_state(db, "pools", target=doel, ttl_seconds=60, now=nu)
            uitkomst[naam] = (st["status"], st["reason_code"])
            db.rollback()
    assert uitkomst == {
        "marge": ("ok", None),
        "toekomst": ("unknown", "meting_verouderd"),
        "oud": ("unknown", "meting_verouderd"),
        "vers": ("ok", None),
    }


def test_export_in_de_toekomst_geeft_het_backupincident(
    admin: Any, app: Any, settings: Any, worker_once: Any, periodic_run: Any
) -> None:
    """R-VEILIG-3: het back-upincident gebruikt dezelfde tijdcontrole als de gate."""
    from hub.models import SelfBackup

    export = _export(admin, worker_once, app)
    assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"] is False
    with app.state.sessionmaker() as db:
        rij = db.get(SelfBackup, export.id)
        rij.finished_at += timedelta(days=1)
        db.commit()
    assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"] is True
    gate = admin.get("/api/v1/gates/backup_gate").json()
    assert any(r["id"] == "eigen_backup" for r in gate["redenen"]), gate
