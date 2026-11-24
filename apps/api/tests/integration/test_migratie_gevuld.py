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
from asm_policy.canonical import canonical_sha256
from conftest import ADMIN_URL
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Session

from hub import migrations
from hub.backup import selfbackup
from hub.config import Settings
from hub.models import ActionRequest, Approval, IdempotencyRecord

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


BEWAARD = ("catalog_plan_bewaard", "app_geheim_bewaard", "kluis_afgifte_bewaard", "herstelpunt_bewaard")


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
        if isinstance(t.item_type, sa.DateTime):
            return [dt.datetime(2026, 1, 1, tzinfo=dt.UTC) + dt.timedelta(minutes=i)]
        return [f"{col.name}-{i}"]
    if isinstance(t, pg.INET):
        return f"127.0.0.{i + 1}"
    if isinstance(t, sa.String | sa.Text):
        return f"{col.name[:6]}{i}-{tabel[:10]}"[: getattr(t, "length", None) or 200]
    raise AssertionError(f"onbekend kolomtype {tabel}.{col.name}: {t!r}; breid _waarde uit")


def _vul(engine: sa.Engine) -> dict[str, list[str]]:
    """Vul alle tabellen met drie rijen en de verplichte singleton met haar ene rij (ouders eerst)."""
    md = sa.MetaData()
    md.reflect(engine)
    tabellen = [t for t in md.sorted_tables if t.name != "alembic_version"]
    rijen: dict[str, list[dict[str, Any]]] = {}
    with engine.begin() as c:
        for tab in tabellen:
            rows = []
            for i in range(1 if tab.name == "catalog_snapshot" else RIJEN):
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
    te_weinig = sorted(t for t, (n, _md5) in voor.items() if n != (1 if t == "catalog_snapshot" else RIJEN))
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


def test_planregistratie_overleeft_terugmigratie_onder_0022(lege_db: str) -> None:
    """R-HARDE-EIS-1: een bevestigde installatie onder 0022 behoudt bij 0022 -> 0021 -> 0022 haar registratie."""
    from hub.models import CatalogPlan
    from hub.timeutil import utcnow

    migrations.upgrade(lege_db, "0022")
    pid = uuid.uuid4()
    registratie = {"app_name": "demo-app", "digests": ["sha256:" + "a" * 64]}
    engine = sa.create_engine(lege_db)
    try:
        with Session(engine) as db:
            db.add(CatalogPlan(id=pid, soort="install", app_id="demo-app", app_name="demo-app",
                               instance_id=uuid.uuid4(), planner_service_id=uuid.uuid4(), binding={"plan_id": str(pid)},
                               step_id="installeren", stap_sha256="sha256:" + "b" * 64, plan_etag='"plan-v1"',
                               controles_na_installatie=[], expires_at=utcnow(), status="geinstalleerd_controles_open",
                               request_id=uuid.uuid4(), created_by="test", created_at=utcnow(), updated_at=utcnow(),
                               melding={"status": "gemeld"}, registratie=registratie))  # fmt: skip
            db.commit()
        migrations.downgrade(lege_db, "0021")
        migrations.upgrade(lege_db, "0022")
        with Session(engine) as db:
            na = db.get(CatalogPlan, pid)
            assert na is not None and na.registratie == registratie and na.status == "geinstalleerd_controles_open"
        # Een lege tabel mag gewoon weg: terug en heen blijft dan schoon.
        with Session(engine) as db:
            db.execute(sa.delete(CatalogPlan))
            db.commit()
        migrations.downgrade(lege_db, "0021")
        assert "catalog_plan_bewaard" not in sa.inspect(engine).get_table_names()
        migrations.upgrade(lege_db, "0022")
    finally:
        engine.dispose()


def test_plannen_uit_de_oorspronkelijke_0022_blijven_leesbaar(lege_db: str) -> None:
    """R-HARDE-EIS-1: de oorspronkelijke 0022 had geen ``stap_sha256``. 0023 maakt zo'n database weer leesbaar, laat de
    registratie staan en zet een open plan zonder stapbewijs op opnieuw voorvertonen; ook na terug en weer heen."""
    from hub.catalog import plannen
    from hub.timeutil import utcnow

    migrations.upgrade(lege_db, "0022")
    engine = sa.create_engine(lege_db)
    try:
        with engine.begin() as c:
            c.execute(
                sa.text("ALTER TABLE catalog_plan DROP COLUMN stap_sha256")
            )  # de vorm van de oorspronkelijke 0022
        tabel = sa.Table("catalog_plan", sa.MetaData(), autoload_with=engine)
        registratie = {"app_name": "demo-app", "digests": ["sha256:" + "a" * 64]}
        controle = {"id": "http_bereikbaar", "soort": "http", "beschrijving_nl": "Antwoordt.", "oude_notitie": "x"}
        ongeldig = {"id": "oud", "soort": "http", "beschrijving_nl": {"oude_notitie": "x"}}  # buiten het schema
        openbaar = [{k: controle[k] for k in plannen.CONTROLE_KEYS}]
        ids = {"bevestigd": uuid.uuid4(), "open": uuid.uuid4()}
        cache = sa.Table("idempotency_record", sa.MetaData(), autoload_with=engine)
        with engine.begin() as c:
            c.execute(cache.insert().values(
                scope="user:test:POST:/api/v1/catalog/plans/install", key=uuid.uuid4(), request_hash="c" * 64,
                status_code=201, created_at=utcnow(),
                response_body={"plan_id": str(ids["open"]), "controles_na_installatie": [controle, ongeldig]},
            ))  # fmt: skip
        with engine.begin() as c:
            for soort, pid in ids.items():
                c.execute(tabel.insert().values(
                    id=pid, soort="install", app_id="demo-app", app_name=f"demo-{soort}", instance_id=uuid.uuid4(),
                    planner_service_id=uuid.uuid4(), binding={"plan_id": str(pid)}, plan_etag='"plan-v1"',
                    step_id="installeren", controles_na_installatie=[controle, ongeldig], expires_at=utcnow(),
                    status="geinstalleerd_controles_open" if soort == "bevestigd" else "klaar_voor_voorstel",
                    request_id=uuid.uuid4() if soort == "bevestigd" else None,
                    registratie=registratie if soort == "bevestigd" else None,
                    created_by="test", created_at=utcnow(), updated_at=utcnow(),
                ))  # fmt: skip
        assert migrations.pending_migrations(lege_db)
        for ronde in ("update", "terug_en_heen"):
            if ronde == "terug_en_heen":
                migrations.downgrade(lege_db, "0021")
            migrations.upgrade(lege_db)
            assert not migrations.pending_migrations(lege_db)
            with Session(engine) as db:
                bevestigd = plannen.haal_plan(db, ids["bevestigd"])
                assert bevestigd.registratie == registratie and bevestigd.status == "geinstalleerd_controles_open"
                assert bevestigd.stap_sha256 is None
                assert bevestigd.controles_na_installatie == openbaar
                open_plan = plannen.haal_plan(db, ids["open"])
                assert (open_plan.status, open_plan.reden) == ("geblokkeerd", "opnieuw_voorvertonen")
                # R-VEILIG-1: ook het bewaarde planantwoord is opgeschoond, vóór enige herhaling.
                assert db.execute(sa.select(cache.c.response_body)).scalar_one()["controles_na_installatie"] == openbaar
    finally:
        engine.dispose()


def test_historische_actiepreviews_migreren_met_behoud_van_goedkeuring(lege_db: str, tmp_path: Path) -> None:
    migrations.upgrade(lege_db, "0017")
    settings = Settings(database_url=lege_db, data_dir=tmp_path)
    oud = {
        "schema": "asm-preview/1",
        "huidig": {"envs": {"MODUS": "proeftekst", "MODUS=voorbeeld": False}},
        "wijziging": {"url": "https://app.invalid/?refresh_token=proeftekst&mod=debug&code_verifier=proeftekst"},
        "parameters_sha256": canonical_sha256({"modus": "debug"}),
    }
    gemaskeerd = {
        **oud,
        "huidig": {"envs": {"MODUS": "***", "MODUS (2)": False}},
        "wijziging": {"url": "https://app.invalid/?refresh_token=***&mod=debug&code_verifier=***"},
    }
    hash_oud = canonical_sha256(oud)
    antwoord = {"preview": oud, "preview_hash": hash_oud, "status": "afgewezen"}
    scopes = [
        "user:beheer:POST:/api/v1/actions",
        "user:beheer:POST:/api/v1/actions/{request_id}/reject",
        "user:beheer:POST:/api/v1/auth/setup",
    ]
    engine = sa.create_engine(lege_db)
    try:
        kolommen = _vul(engine)
        with Session(engine) as db:
            acties = db.scalars(sa.select(ActionRequest).order_by(ActionRequest.id)).all()
            for actie, status in zip(acties, ("afgewezen", "uitgevoerd", "goedgekeurd"), strict=True):
                actie.status, actie.preview, actie.preview_hash = status, oud, hash_oud
            for goedkeuring in db.scalars(sa.select(Approval)):
                goedkeuring.preview_hash = hash_oud
            herhalingen = db.scalars(sa.select(IdempotencyRecord).order_by(IdempotencyRecord.id)).all()
            for rec, scope in zip(herhalingen, scopes, strict=True):
                rec.scope, rec.response_body = scope, antwoord
            db.commit()
        voor = _meet(engine, kolommen)
        overige_kolommen = {
            t: [
                k
                for k in cols
                if (t, k) not in {("action_request", "preview"), ("idempotency_record", "response_body")}
            ]
            for t, cols in kolommen.items()
        }
        ongewijzigd = _meet(engine, overige_kolommen)
        dump = tmp_path / "voor-previews.dump"
        subprocess.run(
            [settings.pg_dump_bin, "--format=custom", "--no-owner", "-f", dump, settings.libpq_url],
            check=True,
            capture_output=True,
        )

        def meet_maskering() -> dict[str, tuple[int, str]]:
            with Session(engine) as db:
                assert db.scalars(sa.select(ActionRequest.preview)).all() == [gemaskeerd] * RIJEN
                assert db.scalars(sa.select(IdempotencyRecord.response_body).order_by(IdempotencyRecord.id)).all() == [
                    {**antwoord, "preview": gemaskeerd},
                    {**antwoord, "preview": gemaskeerd},
                    antwoord,
                ]
            assert _meet(engine, overige_kolommen) == ongewijzigd
            return _meet(engine, kolommen)

        migrations.upgrade(lege_db, "0018")
        na = meet_maskering()
        migrations.downgrade(lege_db, "0017")
        assert _meet(engine, kolommen) == na
        migrations.upgrade(lege_db, "0018")
        assert meet_maskering() == na

        migrations.downgrade(lege_db, "base")
        with engine.begin() as conn:
            # De bewarende terugweg van 0022, 0024 en 0025 laat gevulde tabellen staan; voor een leeg schema hier weg.
            for tabel in BEWAARD:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tabel}")
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
        assert migrations.pending_migrations(lege_db)
        assert _meet(engine, kolommen) == voor
        migrations.upgrade(lege_db, "0018")
        assert meet_maskering() == na
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
        assert len(list(settings.backups_dir.glob("*.dump"))) == bewaren + 1
        assert hashlib.sha256(dump.read_bytes()).hexdigest() == backup.sha256
        assert Path(str(dump) + ".sha256").read_text().split() == [backup.sha256, dump.name]
        # Herstel op een leeg schema zodat de gebruikerswijziging alleen uit deze export kan komen.
        migrations.downgrade(lege_db, "base")
        with engine.begin() as conn:
            # De bewarende terugweg van 0022, 0024 en 0025 laat gevulde tabellen staan; voor een leeg schema hier weg.
            for tabel in BEWAARD:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {tabel}")
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
        "klokcorrectie",
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
        if storing == "klokcorrectie":
            with sa.orm.Session(engine) as db, monkeypatch.context() as klok:
                toekomst = selfbackup.utcnow() + dt.timedelta(minutes=5)
                klok.setattr(selfbackup, "utcnow", lambda: toekomst)
                eerder = selfbackup.run_self_backup(db, instellingen, trigger="pre-upgrade")
                assert eerder.status == "geslaagd"
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
        moet_stoppen = storing not in (None, "klokcorrectie")
        with pytest.raises(SystemExit if moet_stoppen else MigratieAfgerond):
            supervisor.main()
        with engine.connect() as conn:
            revision = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
            backup = conn.execute(
                sa.text("SELECT status, sha256, reason_code FROM self_backup WHERE trigger = 'pre-upgrade'")
            ).first()
        if moet_stoppen:
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
            assert len(list((tmp_path / "backups").glob("*.dump"))) == (2 if storing == "klokcorrectie" else 1)
        assert _meet(engine, {t: c for t, c in kolommen.items() if t != "self_backup"}) == {
            t: meting for t, meting in voor.items() if t != "self_backup"
        }
    finally:
        engine.dispose()


def test_appgeheimen_en_afgiften_overleven_terugmigratie_onder_0024(lege_db: str) -> None:
    """HARDE EIS (S-P2-050e): een versleuteld appgeheim en een afgifte blijven bij 0024 -> 0023 -> 0024 bewaard."""
    from hub.models import AppGeheim, KluisAfgifte
    from hub.timeutil import utcnow

    migrations.upgrade(lege_db, "0024")
    gid, rid = uuid.uuid4(), uuid.uuid4()
    engine = sa.create_engine(lege_db)
    try:
        with Session(engine) as db:
            db.add(
                AppGeheim(
                    id=gid,
                    instance_id=uuid.uuid4(),
                    ref="vault://app/demo-app/app_secret_key",
                    revision=uuid.uuid4(),
                    nonce=b"n" * 12,
                    ciphertext=b"c" * 48,
                    created_at=utcnow(),
                )
            )
            db.add(KluisAfgifte(request_id=rid, request_sha256="sha256:" + "a" * 64, expires_at=utcnow(),
                                created_at=utcnow()))  # fmt: skip
            db.commit()
        migrations.downgrade(lege_db, "0023")
        assert {"app_geheim_bewaard", "kluis_afgifte_bewaard"} <= set(sa.inspect(engine).get_table_names())
        migrations.upgrade(lege_db, "0024")
        with Session(engine) as db:
            geheim = db.get(AppGeheim, gid)
            assert geheim is not None and geheim.ciphertext == b"c" * 48 and db.get(KluisAfgifte, rid) is not None
            db.execute(sa.delete(AppGeheim))
            db.execute(sa.delete(KluisAfgifte))
            db.commit()
        migrations.downgrade(lege_db, "0023")
        assert not {"app_geheim", "app_geheim_bewaard"} & set(sa.inspect(engine).get_table_names())
        migrations.upgrade(lege_db, "0024")
    finally:
        engine.dispose()


def test_herstelpunten_overleven_terugmigratie_onder_0025(lege_db: str) -> None:
    """HARDE EIS (S-P2-090): een vastgelegd herstelpunt blijft bij 0025 -> 0024 -> 0025 bewaard; een lege tabel gaat
    gewoon weg."""
    from hub.models import Herstelpunt
    from hub.timeutil import utcnow

    migrations.upgrade(lege_db, "0025")
    hid = uuid.uuid4()
    engine = sa.create_engine(lege_db)
    try:
        with Session(engine) as db:
            db.add(Herstelpunt(id=hid, app="demo-app", checkpoint_id=str(uuid.uuid4()), gemaakt_op=utcnow(),
                               snapshot={"datasets": ["p/apps"]}, status="geverifieerd"))  # fmt: skip
            db.commit()
        migrations.downgrade(lege_db, "0024")
        assert "herstelpunt_bewaard" in set(sa.inspect(engine).get_table_names())
        migrations.upgrade(lege_db, "0025")
        with Session(engine) as db:
            hp = db.get(Herstelpunt, hid)
            assert hp is not None and hp.snapshot == {"datasets": ["p/apps"]}
            db.execute(sa.delete(Herstelpunt))
            db.commit()
        migrations.downgrade(lege_db, "0024")
        assert not {"herstelpunt", "herstelpunt_bewaard"} & set(sa.inspect(engine).get_table_names())
        migrations.upgrade(lege_db, "0025")
    finally:
        engine.dispose()


def test_terugweg_0025_bewaart_een_tijdens_het_wachten_bevestigd_herstelpunt(lege_db: str) -> None:
    """R-HARDE-EIS-1: een schrijver die commit terwijl de terugweg op het tabelslot wacht, verliest niets; de rij komt
    na 0024 -> 0025 met alle velden terug."""
    import time
    from concurrent.futures import ThreadPoolExecutor

    from hub.models import Herstelpunt
    from hub.timeutil import utcnow

    migrations.upgrade(lege_db, "0025")
    engine = sa.create_engine(lege_db)
    hid = uuid.uuid4()
    wacht = sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype='relation' AND relation='herstelpunt'::regclass "
        "AND mode='AccessExclusiveLock' AND NOT granted)"
    )
    alles = sa.select(*Herstelpunt.__table__.columns)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool, Session(engine) as schrijver:
            schrijver.add(Herstelpunt(id=hid, app="mediaguard", checkpoint_id=str(uuid.uuid4()), gemaakt_op=utcnow(),
                                      snapshot={"datasets": ["p/mg"]}, db_export={"sha256": "ab" * 32},
                                      status="niet_geverifieerd", reden="database_export_ontbreekt"))  # fmt: skip
            schrijver.flush()
            voor = schrijver.execute(alles).all()
            terug = pool.submit(migrations.downgrade, lege_db, "0024")
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as kijker:
                eind = time.monotonic() + 10
                while not kijker.scalar(wacht):
                    assert not terug.done() and time.monotonic() < eind, "terugweg bereikte het tabelslot niet"
                    time.sleep(0.02)
            schrijver.commit()
            terug.result(timeout=10)
        assert "herstelpunt_bewaard" in set(sa.inspect(engine).get_table_names())
        migrations.upgrade(lege_db, "0025")
        with engine.connect() as c:
            na = c.execute(alles).all()
        assert len(voor) == 1 and na == voor
    finally:
        engine.dispose()


def test_oude_open_herstart_komt_in_de_wachtlijst(lege_db: str) -> None:
    migrations.upgrade(lege_db, "0025")
    engine = sa.create_engine(lege_db)
    try:
        _vul(engine)
        with Session(engine) as db:
            rijen = db.scalars(sa.select(ActionRequest).order_by(ActionRequest.id)).all()
            for rij, (actie, status) in zip(
                rijen, [("app.restart", "klaar"), ("app.restart", "uitgevoerd"), ("app.start", "klaar")], strict=True
            ):
                rij.action_id, rij.status = actie, status
            db.commit()
        migrations.upgrade(lege_db, "0026")
        with Session(engine) as db:
            assert db.scalars(sa.select(ActionRequest.status).order_by(ActionRequest.id)).all() == [
                "wacht_op_goedkeuring",
                "uitgevoerd",
                "klaar",
            ]
    finally:
        engine.dispose()
