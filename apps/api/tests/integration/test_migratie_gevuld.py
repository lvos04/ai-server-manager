"""Migratie op een GEVULDE database van de vorige revisie: niets verloren, ook niet terug en weer heen (P-HARDE-EIS
punt 3; HARDE EIS, ADR-0020).

De test vult elke tabel van de vorige revisie (de ``down_revision`` van head) met een vast aantal rijen, meet per tabel
het aantal rijen en een md5 over de inhoud van de kolommen die er toen waren, en migreert dan naar head, terug en weer
naar head. Elke meting moet gelijk zijn aan die van vóór de migratie. Een lege tabel of een lege meting is een fout
(V-005), en een eigen tegenproef laat zien dat de vergelijking een verdwenen rij ziet (V-003).

Kolommen die een nieuwe migratie toevoegt, tellen niet mee; een kolom die verdwijnt of een type dat het vullen niet
kent, maakt de test rood. Dan moet de migratie (of deze test) uitdrukkelijk zeggen wat er met die gegevens gebeurt.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib
import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import psycopg
import pytest
import sqlalchemy as sa
from alembic.script import ScriptDirectory
from conftest import ADMIN_URL
from sqlalchemy.dialects import postgresql as pg

from hub import migrations
from hub.backup import selfbackup
from hub.config import Settings

pytestmark = pytest.mark.integration
RIJEN = 3


@pytest.fixture
def lege_db() -> Iterator[str]:
    """Een eigen, lege database (``asm_test_mig_<id>``); na afloop weg."""
    name = f"asm_test_mig_{uuid.uuid4().hex[:8]}"
    try:
        with psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=5) as conn:
            conn.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as exc:
        if os.environ.get("CI") or os.environ.get("HUB_TEST_REQUIRE_PG"):
            pytest.fail(f"PostgreSQL vereist (CI) maar niet bereikbaar: {exc}")
        pytest.skip(f"geen PostgreSQL voor integratietests: {exc}")
    url = f"{ADMIN_URL.rsplit('/', 1)[0]}/{name}".replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        yield url
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def _vorige_en_head() -> tuple[str, str]:
    script = ScriptDirectory.from_config(migrations.alembic_config())
    head = script.get_current_head()
    assert isinstance(head, str), "precies één head verwacht"
    vorige = script.get_revision(head).down_revision
    assert isinstance(vorige, str), f"head {head} heeft geen enkele vorige revisie"
    return vorige, head


def _waarde(col: sa.Column[Any], i: int, tabel: str) -> Any:
    """Een geldige, per rij unieke testwaarde voor de kolom (alleen testgegevens)."""
    t = col.type
    if isinstance(t, sa.Uuid | pg.UUID):
        return uuid.uuid5(uuid.NAMESPACE_URL, f"{tabel}.{col.name}.{i}")
    if isinstance(t, sa.Boolean):
        return i % 2 == 0
    if isinstance(t, sa.BigInteger | sa.Integer | sa.SmallInteger):
        return i + 1
    if isinstance(t, sa.Float | sa.Numeric):
        return 1.5 + i
    if isinstance(t, sa.DateTime):
        return dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC) + dt.timedelta(minutes=i)
    if isinstance(t, sa.Date):
        return dt.date(2026, 1, 1) + dt.timedelta(days=i)
    if isinstance(t, pg.JSONB | pg.JSON | sa.JSON):
        return {"rij": i, "tabel": tabel, "kolom": col.name, "lijst": [1, 2, i]}
    if isinstance(t, sa.LargeBinary | pg.BYTEA):
        return f"{tabel}-{col.name}-{i}".encode()
    if isinstance(t, pg.ARRAY):
        return [f"{col.name}-{i}"]
    if isinstance(t, pg.INET):
        return f"127.0.0.{i + 1}"
    if isinstance(t, sa.String | sa.Text):
        return f"{col.name[:6]}{i}-{tabel[:10]}"[: getattr(t, "length", None) or 200]
    raise AssertionError(f"onbekend kolomtype {tabel}.{col.name}: {t!r}; breid _waarde uit")


def _vul(engine: sa.Engine) -> dict[str, list[str]]:
    """Vul elke tabel met ``RIJEN`` rijen (ouders eerst). Geeft de kolommen per tabel op deze revisie."""
    md = sa.MetaData()
    md.reflect(engine)
    tabellen = [t for t in md.sorted_tables if t.name != "alembic_version"]
    rijen: dict[str, list[dict[str, Any]]] = {}
    with engine.begin() as c:
        for tab in tabellen:
            rows = []
            for i in range(RIJEN):
                row: dict[str, Any] = {}
                for col in tab.columns:
                    fks = list(col.foreign_keys)
                    if fks:
                        ref = fks[0].column
                        bron = rijen.get(ref.table.name) or []
                        row[col.name] = bron[i % len(bron)][ref.name] if bron and ref.table.name != tab.name else None
                        continue
                    row[col.name] = _waarde(col, i, tab.name)
                rows.append(row)
            c.execute(tab.insert(), rows)
            rijen[tab.name] = rows
    return {t.name: [col.name for col in t.columns] for t in tabellen}


def _meet(engine: sa.Engine, kolommen: dict[str, list[str]]) -> dict[str, tuple[int, str]]:
    """Per tabel: aantal rijen en md5 over de inhoud van de gegeven kolommen (in vaste volgorde)."""
    out: dict[str, tuple[int, str]] = {}
    with engine.connect() as c:
        for tabel, cols in kolommen.items():
            rij = ", ".join(f'x."{k}"' for k in cols)
            n, md5 = c.execute(
                sa.text(
                    f"SELECT count(*), md5(coalesce(string_agg(r::text, '|' ORDER BY r::text), '')) "  # noqa: S608 - namen uit de catalogus
                    f'FROM (SELECT ROW({rij}) AS r FROM "{tabel}" x) s'
                )
            ).one()
            out[tabel] = (int(n), str(md5))
    return out


def _gevuld(engine: sa.Engine, url: str) -> tuple[dict[str, list[str]], dict[str, tuple[int, str]]]:
    vorige, _head = _vorige_en_head()
    migrations.upgrade(url, vorige)
    kolommen = _vul(engine)
    voor = _meet(engine, kolommen)
    te_weinig = sorted(t for t, (n, _md5) in voor.items() if n < RIJEN)
    assert voor and te_weinig == [], f"lege meting of te weinig rijen: {te_weinig}"
    return kolommen, voor


def test_migratie_naar_head_op_een_gevulde_database_verliest_niets(lege_db: str) -> None:
    vorige, head = _vorige_en_head()
    engine = sa.create_engine(lege_db)
    try:
        kolommen, voor = _gevuld(engine, lege_db)
        migrations.upgrade(lege_db, head)
        assert _meet(engine, kolommen) == voor, f"{vorige} -> {head}: gegevens veranderd"
        migrations.downgrade(lege_db, vorige)
        assert _meet(engine, kolommen) == voor, f"{head} -> {vorige}: gegevens veranderd"
        migrations.upgrade(lege_db, head)
        assert _meet(engine, kolommen) == voor, f"opnieuw {vorige} -> {head}: gegevens veranderd"
        with engine.connect() as c:
            assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == head
    finally:
        engine.dispose()


def test_de_vergelijking_ziet_een_verdwenen_rij(lege_db: str) -> None:
    """Tegenproef (V-003): verdwijnt er na het vullen één rij uit een gewone tabel, dan is de meting anders."""
    engine = sa.create_engine(lege_db)
    try:
        kolommen, voor = _gevuld(engine, lege_db)
        with engine.begin() as c:
            tabel = c.execute(
                sa.text(
                    "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'alembic_version' "
                    "AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.contype = 'f' AND k.confrelid = c.oid) "
                    "AND NOT EXISTS (SELECT 1 FROM pg_trigger g WHERE g.tgrelid = c.oid AND NOT g.tgisinternal) "
                    "ORDER BY 1 LIMIT 1"
                )
            ).scalar()
            assert isinstance(tabel, str), "geen tabel zonder verwijzingen en triggers gevonden"
            c.execute(sa.text(f'DELETE FROM "{tabel}" WHERE ctid IN (SELECT ctid FROM "{tabel}" LIMIT 1)'))  # noqa: S608
        na = _meet(engine, kolommen)
        assert na != voor and na[tabel][0] == RIJEN - 1, (tabel, na[tabel], voor[tabel])
        assert {t: m for t, m in na.items() if t != tabel} == {t: m for t, m in voor.items() if t != tabel}
    finally:
        engine.dispose()


@pytest.mark.parametrize("bewaren", [1, 7])
def test_terugval_na_klokcorrectie(lege_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bewaren: int) -> None:
    vorige, _ = _vorige_en_head()
    settings = Settings(database_url=lege_db, data_dir=tmp_path, self_backup_keep=bewaren)
    engine = sa.create_engine(lege_db)
    try:
        migrations.upgrade(lege_db, vorige)
        _vul(engine)
        with monkeypatch.context() as klok, sa.orm.Session(engine) as db:
            toekomst = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=2)
            klok.setattr(selfbackup, "utcnow", lambda: toekomst)
            for _ in range(bewaren):
                assert selfbackup.run_self_backup(db, settings, trigger="manual").status == "geslaagd"
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE app_user SET username='laatste-wijziging' "
                "WHERE id=(SELECT id FROM app_user ORDER BY id LIMIT 1)"
            )
        env = {
            **os.environ,
            "HUB_DATABASE_URL": lege_db,
            "HUB_DATA_DIR": str(tmp_path),
            "HUB_SELF_BACKUP_KEEP": str(bewaren),
        }
        subprocess.run(
            [sys.executable, "-m", "hub", "backup-now", "--trigger", "pre-upgrade"],
            env=env,
            check=True,
            capture_output=True,
        )
        with engine.connect() as conn:
            backup = conn.exec_driver_sql(
                "SELECT status, deleted_at, file_name, sha256 FROM self_backup WHERE trigger='pre-upgrade'"
            ).one()
        assert backup.status == "geslaagd" and backup.deleted_at is None
        dump = settings.backups_dir / backup.file_name
        assert len(list(settings.backups_dir.glob("*.dump"))) == bewaren
        assert hashlib.sha256(dump.read_bytes()).hexdigest() == backup.sha256
        assert Path(str(dump) + ".sha256").read_text().split() == [backup.sha256, dump.name]
        # Herstel op een leeg schema zodat de gebruikerswijziging alleen uit deze export kan komen.
        migrations.downgrade(lege_db, "base")
        subprocess.run(
            [
                settings.pg_restore_bin,
                "--clean",
                "--if-exists",
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "-d",
                settings.libpq_url,
                dump,
            ],
            check=True,
            capture_output=True,
        )
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == vorige
            assert (
                conn.exec_driver_sql("SELECT count(*) FROM app_user WHERE username='laatste-wijziging'").scalar_one()
                == 1
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "storing",
    [
        "ruimtegebrek",
        "exportfout",
        "verificatiefout",
        "verdwenen",
        "verwisseld",
        "zonder_controlesom",
        "weg_voor_migratie",
        None,
    ],
)
def test_opstartmigratie_wacht_op_geverifieerde_backup(
    lege_db: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, storing: str | None
) -> None:
    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "deploy/common"))
    supervisor = importlib.import_module("deploy.allinone.supervisor")
    postgres = Mock()
    for name in ("prepare_dirs", "demote", "init_database", "wait_for_db"):
        monkeypatch.setattr(supervisor, name, Mock())
    monkeypatch.setattr(supervisor, "postgres_child", lambda: postgres)
    monkeypatch.setattr(supervisor, "has_schema", lambda: True)
    monkeypatch.setattr(supervisor, "DATA", tmp_path)
    monkeypatch.setattr(supervisor, "os", SimpleNamespace(getuid=lambda: supervisor.UID))
    monkeypatch.setattr(supervisor, "fail", Mock(side_effect=SystemExit(78)))
    env = {**os.environ, "HUB_DATABASE_URL": lege_db, "HUB_DATA_DIR": str(tmp_path)}
    if storing == "ruimtegebrek":
        monkeypatch.setattr(supervisor.shutil, "disk_usage", Mock(return_value=Mock(free=0)))
    elif storing in {"exportfout", "verificatiefout"}:
        tool = "DUMP" if storing == "exportfout" else "RESTORE"
        env[f"HUB_PG_{tool}_BIN"] = str(tmp_path / "ontbrekend-testprogramma")
    instellingen = Settings(database_url=lege_db, data_dir=tmp_path)
    na_retentie = {
        "verdwenen": "dump_missing",
        "verwisseld": "checksum_mismatch",
        "zonder_controlesom": "backup_unavailable",
    }
    uitgevoerd = []

    class MigratieAfgerond(Exception):
        pass

    def voer_uit(naam: str, cmd: list[str]) -> int:
        uitgevoerd.append(naam)
        if naam == "first-start-init":
            return 0
        if naam == "back-up vóór upgrade" and storing in na_retentie:
            from hub import __main__ as cli

            monkeypatch.setattr(cli, "get_settings", lambda: instellingen)
            return cli.main(cmd[3:])
        if naam == "controle archief vóór upgrade" and storing == "weg_voor_migratie":
            for dump in tmp_path.glob("backups/*.dump"):  # samenloop na backup-now, vóór de migratie
                dump.unlink()
        result = subprocess.run(cmd, env=env, capture_output=True, check=False)
        if naam == "migraties":
            assert result.returncode == 0
            raise MigratieAfgerond
        return result.returncode

    monkeypatch.setattr(supervisor, "run_once", voer_uit)
    engine = sa.create_engine(lege_db)
    try:
        vorige, head = _vorige_en_head()
        kolommen, voor = _gevuld(engine, lege_db)
        if storing in na_retentie:
            with sa.orm.Session(engine) as db:
                eerder = selfbackup.run_self_backup(db, instellingen, trigger="manual")
                assert eerder.status == "geslaagd" and eerder.file_name
                oud = instellingen.backups_dir / eerder.file_name
            retentie = selfbackup.apply_retention

            def verstoor(*args: Any, **kwargs: Any) -> list[str]:
                verwijderd = retentie(*args, **kwargs)
                (nieuw,) = set(instellingen.backups_dir.glob("*.dump")) - {oud}
                if storing == "verdwenen":
                    nieuw.unlink()
                elif storing == "verwisseld":
                    shutil.copyfile(oud, nieuw)  # Leesbaar pg_dump-archief, maar van een andere export.
                else:
                    Path(str(nieuw) + ".sha256").unlink()
                return verwijderd

            monkeypatch.setattr(selfbackup, "apply_retention", verstoor)
        with pytest.raises(SystemExit if storing else MigratieAfgerond):
            supervisor.main()
        with engine.connect() as conn:
            revision = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
            backup = conn.execute(
                sa.text("SELECT status, sha256, reason_code FROM self_backup WHERE trigger = 'pre-upgrade'")
            ).first()
        if storing:
            assert revision == vorige and "migraties" not in uitgevoerd
            postgres.stop.assert_called_once()
            if storing == "weg_voor_migratie":
                assert backup and backup.status == "geslaagd"
            elif storing in na_retentie:
                assert backup and (backup.status, backup.reason_code) == ("mislukt", na_retentie[storing])
            else:
                assert backup is None if storing == "ruimtegebrek" else backup[:2] == ("mislukt", None)
        else:
            assert revision == head and uitgevoerd[-3:] == [
                "back-up vóór upgrade",
                "controle archief vóór upgrade",
                "migraties",
            ]
            assert backup and backup.status == "geslaagd" and len(backup.sha256) == 64
            assert len(list((tmp_path / "backups").glob("*.dump"))) == 1
        assert _meet(engine, {t: c for t, c in kolommen.items() if t != "self_backup"}) == {
            t: meting for t, meting in voor.items() if t != "self_backup"
        }
    finally:
        engine.dispose()
