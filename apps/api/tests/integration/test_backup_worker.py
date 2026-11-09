"""Eigen database-export (echte pg_dump + pg_restore --list), worker en migraties."""

from __future__ import annotations

import os
import stat
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
