"""Eigen database-export (echte pg_dump + pg_restore --list), worker en migraties."""

from __future__ import annotations

import os
import stat
import time
import uuid
from pathlib import Path
from typing import Any

import psycopg
import pytest
from conftest import idem

pytestmark = pytest.mark.integration


def test_echte_backup_geverifieerd(admin: Any, settings: Any, worker_once: Any) -> None:
    r = admin.post("/api/v1/backups/self", headers=idem())
    assert r.status_code == 202
    done = worker_once()
    assert done[-1]["kind"] == "self_backup" and done[-1]["status"] == "geslaagd", done
    lst = admin.get("/api/v1/backups/self").json()
    b = lst["laatste_geverifieerd"]
    assert b["status"] == "geslaagd" and b["inhoudsopgave_items"] > 10 and len(b["sha256"]) == 64
    folder = settings.backups_dir
    assert (folder / b["bestand"]).read_bytes()[:5] == b"PGDMP"
    assert (folder / (b["bestand"] + ".sha256")).read_text().startswith(b["sha256"])
    assert '"verificatie"' in (folder / (b["bestand"] + ".json")).read_text()
    assert not list(folder.glob("*.partial"))
    v = admin.post(f"/api/v1/backups/self/{b['id']}/verify", headers=idem()).json()
    assert v["ok"] is True
    with (folder / b["bestand"]).open("r+b") as fh:  # sabotage: checksum moet afwijken
        fh.seek(-1, os.SEEK_END)
        last = fh.read(1)
        fh.seek(-1, os.SEEK_END)
        fh.write(bytes([last[0] ^ 0xFF]))
    v = admin.post(f"/api/v1/backups/self/{b['id']}/verify", headers=idem()).json()
    assert v["ok"] is False and v["reason_code"] in ("checksum_mismatch", "restore_list_failed")
    cov = {a["app"]: a for a in admin.get("/api/v1/backups/coverage").json()["apps"]}
    assert cov["ai-server-manager"]["db_export"]["status"] == "geverifieerd"
    assert any(
        c["name"] == "eigen_backup" and c["status"] == "healthy"
        for c in admin.get("/connector/v1/health").json()["checks"]
    )


def _stub(tmp_path: Path, name: str, script: str) -> str:
    p = tmp_path / name
    p.write_text("#!/bin/sh\n" + script)
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p)


def test_nooit_geslaagd_op_alleen_exitcode(settings: Any, app: Any, tmp_path: Path) -> None:
    from hub.backup.selfbackup import run_self_backup

    # pg_dump die "slaagt" (exit 0) maar rommel schrijft → mislukt (bad_magic)
    settings.pg_dump_bin = _stub(
        tmp_path,
        "pg_dump",
        'for a in "$@"; do case "$a" in --file=*) echo rommel > "${a#--file=}";; esac; done\nexit 0\n',
    )
    with app.state.sessionmaker() as db:
        row = run_self_backup(db, settings, trigger="manual")
        assert row.status == "mislukt" and row.reason_code == "bad_magic"
    # pg_dump die een geldig-lijkende header schrijft maar pg_restore kan hem niet lezen
    settings.pg_dump_bin = _stub(
        tmp_path,
        "pg_dump2",
        'for a in "$@"; do case "$a" in --file=*) printf PGDMPxx > "${a#--file=}";; esac; done\nexit 0\n',
    )
    with app.state.sessionmaker() as db:
        row = run_self_backup(db, settings, trigger="manual")
        assert row.status == "mislukt" and row.reason_code == "restore_list_failed"
    # ontbrekende binary
    settings.pg_dump_bin = str(tmp_path / "bestaat-niet")
    with app.state.sessionmaker() as db:
        row = run_self_backup(db, settings, trigger="manual")
        assert row.status == "mislukt" and row.reason_code == "pg_dump_failed"
    assert not list(settings.backups_dir.glob("*.dump"))


def test_retentie(settings: Any, app: Any) -> None:
    from hub.backup.selfbackup import run_self_backup

    settings.self_backup_keep = 2
    with app.state.sessionmaker() as db:
        rows = [run_self_backup(db, settings, trigger="manual") for _ in range(3)]
        assert all(r.status == "geslaagd" for r in rows)
        assert rows[0].deleted_at is not None and rows[2].deleted_at is None
    assert len(list(settings.backups_dir.glob("*.dump"))) == 2


def test_retentie_laat_pre_upgrade_export_staan_bij_samenloop(settings: Any, app: Any, tmp_path: Path) -> None:
    """Een oudere export die later afrondt, mag het net gecontroleerde pre-upgrade-archief niet verwijderen."""
    import shutil
    import threading

    from hub.backup.selfbackup import run_self_backup

    settings.self_backup_keep = 1
    poort = tmp_path / "poort"
    echt = shutil.which("pg_dump")
    traag = _stub(
        tmp_path,
        "pg_dump",
        f'case "$1" in --version) exec {echt} "$@";; esac\n'
        f'while [ ! -e {poort} ]; do sleep 0.05; done\nexec {echt} "$@"\n',
    )
    echte_bin, uitkomst = settings.pg_dump_bin, {}

    def eerdere_export() -> None:
        eigen = settings.model_copy(update={"pg_dump_bin": traag})
        with app.state.sessionmaker() as db:
            uitkomst["rij"] = run_self_backup(db, eigen, trigger="manual")

    thread = threading.Thread(target=eerdere_export)
    thread.start()
    time.sleep(0.5)  # de oudere export is begonnen en wacht op zijn dump
    settings.pg_dump_bin = echte_bin
    with app.state.sessionmaker() as db:
        upgrade = run_self_backup(db, settings, trigger="pre-upgrade")
        assert upgrade.status == "geslaagd"
        poort.touch()
        thread.join(30)
        assert uitkomst["rij"].status == "geslaagd"
        db.refresh(upgrade)
        assert upgrade.deleted_at is None and (settings.backups_dir / upgrade.file_name).is_file()
        from hub.backup.selfbackup import verify_pre_upgrade

        assert verify_pre_upgrade(db, settings, upgrade.id).ok


def test_pre_upgrade_controle_faalt_zonder_archief(settings: Any, app: Any) -> None:
    from hub.backup.selfbackup import run_self_backup, verify_pre_upgrade

    with app.state.sessionmaker() as db:
        assert verify_pre_upgrade(db, settings, uuid.uuid4()).reason_code == "not_available"
        rij = run_self_backup(db, settings, trigger="pre-upgrade")
        assert verify_pre_upgrade(db, settings, rij.id).ok
        andere = run_self_backup(db, settings, trigger="pre-upgrade")
        gewoon = run_self_backup(db, settings, trigger="manual")
        assert verify_pre_upgrade(db, settings, gewoon.id).reason_code == "not_available"
        (settings.backups_dir / rij.file_name).unlink()
        assert verify_pre_upgrade(db, settings, andere.id).ok
        assert verify_pre_upgrade(db, settings, rij.id).reason_code == "dump_missing"


def test_worker_plant_backup_maar_geen_inventaris_zonder_d03(admin: Any, worker_once: Any) -> None:
    done = worker_once(schedule=True)
    kinds = [d["kind"] for d in done]
    assert kinds == ["self_backup"], "zonder NAS-adres (D03) wordt er niets bij TrueNAS opgevraagd"
    assert admin.get("/connector/v1/health").json()["checks"][1]["status"] == "healthy"
    assert worker_once(schedule=True) == []  # niets opnieuw binnen het interval


def test_migraties_op_en_neer(pg_url: str) -> None:
    from hub import migrations

    base, _, _ = pg_url.rpartition("/")
    name = "asm_test_mig_" + os.urandom(3).hex()
    admin_url = base + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    url = f"{base}/{name}".replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        migrations.upgrade(url)
        assert not migrations.pending_migrations(url)
        migrations.downgrade(url, "base")
        assert migrations.pending_migrations(url)
        migrations.upgrade(url)
        from alembic.autogenerate import compare_metadata
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine

        from hub.models import Base

        engine = create_engine(url)
        with engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        engine.dispose()
        assert diff == [], f"modellen en migraties lopen uiteen: {diff}"
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def test_openapi_actueel() -> None:
    from hub.openapi_export import export

    out = Path(__file__).resolve().parents[4] / "docs" / "openapi" / "hub-api.openapi.json"
    assert export(out, check=True) == 0, "draai `make openapi`"


def test_worker_plant_inventaris_niet_elke_ronde(admin: Any, worker_once: Any) -> None:
    admin.put(
        "/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "127.0.0.1", "https_poort": 1}}, headers=idem()
    ).raise_for_status()
    first = [d for d in worker_once(schedule=True) if d["kind"] == "inventory_refresh"]
    assert first and first[0]["reason_code"] == "not_configured"  # nog geen API-key
    assert [d for d in worker_once(schedule=True) if d["kind"] == "inventory_refresh"] == []
    admin.put("/api/v1/truenas/api-key", json={"api_key": "readonly-test-key-0123456789"}, headers=idem())
    assert [d for d in worker_once(schedule=True) if d["kind"] == "inventory_refresh"] == []  # binnen interval
    r = admin.post("/api/v1/inventory/refresh", headers=idem())  # handmatig kan altijd
    assert r.status_code == 202
    done = [d for d in worker_once() if d["kind"] == "inventory_refresh"]
    assert done and done[0]["reason_code"] == "unreachable"


@pytest.mark.parametrize("bewaren", [1, 7])
def test_mislukte_opvolger_behoudt_vorig_herstelpunt(
    settings: Any, app: Any, monkeypatch: pytest.MonkeyPatch, bewaren: int
) -> None:
    from hub.backup import selfbackup

    settings.self_backup_keep = bewaren
    with app.state.sessionmaker() as db:
        vorig = selfbackup.run_self_backup(db, settings, trigger="pre-upgrade")
        assert vorig.status == "geslaagd"
        archief = settings.backups_dir / vorig.file_name
        bestanden = [archief, Path(str(archief) + ".sha256"), Path(str(archief) + ".json")]
        digests = [selfbackup.sha256_file(pad) for pad in bestanden]
        for _ in range(bewaren):
            assert selfbackup.run_self_backup(db, settings, trigger="manual").status == "geslaagd"
        controle = selfbackup.reverify

        def verlies_nieuwe_dump(sessie: Any, config: Any, rij: Any) -> Any:
            assert rij.id != vorig.id
            (config.backups_dir / rij.file_name).unlink()
            return controle(sessie, config, rij)

        with monkeypatch.context() as fout:
            fout.setattr(selfbackup, "reverify", verlies_nieuwe_dump)
            nieuw = selfbackup.run_self_backup(db, settings, trigger="pre-upgrade")
        assert (nieuw.status, nieuw.reason_code) == ("mislukt", "dump_missing")
        assert selfbackup.run_self_backup(db, settings, trigger="schedule").status == "geslaagd"
        db.refresh(vorig)
        assert vorig.deleted_at is None and controle(db, settings, vorig).ok
        assert [selfbackup.sha256_file(pad) for pad in bestanden] == digests
        assert len(list(settings.backups_dir.glob("*.dump"))) == bewaren + 1
