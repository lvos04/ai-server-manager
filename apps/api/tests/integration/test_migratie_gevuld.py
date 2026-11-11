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
import os
import uuid
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
import sqlalchemy as sa
from alembic.script import ScriptDirectory
from conftest import ADMIN_URL
from sqlalchemy.dialects import postgresql as pg

from hub import migrations

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
