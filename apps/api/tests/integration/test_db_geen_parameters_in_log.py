"""V-094: een databasefout zet de parameterwaarden niet in de foutmelding of in de app-log.

De productie-engines van de Hub staan op hide_parameters=True: ``hub.db.make_engine`` (API en worker),
``hub.migrations.pending_migrations`` en de engine in ``apps/api/alembic/env.py`` (migraties). Zonder die stand schrijft
SQLAlchemy bij elke databasefout "[parameters: {...}]" met de letterlijke waarden in str(fout); de algemene
foutafhandeling (hub.errors, log.exception) zet die tekst dan in de app-log. Een parameter kan een geheim of token zijn.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
import sqlalchemy
from conftest import _psycopg_url
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from hub import migrations
from hub.db import make_engine

pytestmark = pytest.mark.integration

# Herkenbare testwaarde (geen echt geheim); te lang voor varchar(8), dus PostgreSQL weigert hem.
TESTWAARDE = "asm-v094-testgeheim-0123456789"


def _controleer_engine(engine: Engine, caplog: pytest.LogCaptureFixture) -> None:
    with engine.connect() as conn, pytest.raises(DBAPIError) as info:
        conn.execute(text("CREATE TEMP TABLE v094_proef (waarde varchar(8))"))
        conn.execute(text("INSERT INTO v094_proef (waarde) VALUES (:waarde)"), {"waarde": TESTWAARDE})
    fout = info.value
    # De fout zelf blijft bruikbaar: de SQL-tekst en de oorzaak staan er nog in.
    assert "INSERT INTO v094_proef" in str(fout)
    assert "parameters hidden" in str(fout)
    assert TESTWAARDE not in str(fout)
    assert TESTWAARDE not in repr(fout)
    # Zoals de algemene foutafhandeling het logt (hub.errors: log.exception).
    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="hub.errors"):
        try:
            raise fout
        except DBAPIError:
            logging.getLogger("hub.errors").exception("onverwachte fout (trace_id=%s)", "v094")
    assert caplog.records, "de fout is niet gelogd"
    assert "INSERT INTO v094_proef" in caplog.text
    assert TESTWAARDE not in caplog.text


def test_make_engine_zonder_parameterwaarden_in_fout_en_log(clean_db: str, caplog: pytest.LogCaptureFixture) -> None:
    engine = make_engine(_psycopg_url(clean_db))
    try:
        _controleer_engine(engine, caplog)
    finally:
        engine.dispose()


def test_migratie_engines_zonder_parameterwaarden_in_fout_en_log(
    pg_url: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """De engines van pending_migrations en van alembic/env.py (via migrations.upgrade) onderscheppen en beproeven."""
    echte_create_engine = sqlalchemy.create_engine
    gemaakt: list[Engine] = []

    def spion(*args: Any, **kwargs: Any) -> Engine:
        engine = echte_create_engine(*args, **kwargs)
        gemaakt.append(engine)
        return engine

    # Beide plekken doen "from sqlalchemy import create_engine" bij het aanroepen of laden; dat leest dit attribuut.
    monkeypatch.setattr(sqlalchemy, "create_engine", spion)
    url = _psycopg_url(pg_url)
    assert migrations.pending_migrations(url) is False
    assert len(gemaakt) == 1, "pending_migrations maakte geen eigen engine"
    migrations.upgrade(url)  # al op head: draait alembic/env.py online, zonder wijziging
    assert len(gemaakt) == 2, "alembic/env.py maakte geen eigen engine"
    monkeypatch.undo()
    for engine in gemaakt:
        try:
            _controleer_engine(engine, caplog)
        finally:
            engine.dispose()
