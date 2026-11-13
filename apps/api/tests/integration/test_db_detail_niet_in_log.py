"""KLEIN-33: een onverwachte databasefout zet de DETAIL-regel van PostgreSQL niet in de app-log.

PostgreSQL noemt bij een constraint-schending de sleutelwaarde ("Key (kolom)=(waarde) already exists.") of de hele rij
("Failing row contains (...)"). ``hide_parameters=True`` (V-094) haalt die regel niet weg. De algemene foutafhandeling
van API (hub.errors) en worker (hub.worker.run_once) logt bij een DBAPIError daarom alleen soort, sqlstate, constraint
en tabel; een logfilter (hub.logfilter.DbDetailFilter) haalt DETAIL ook elders weg (vangnet).
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Any

import pytest
from conftest import _psycopg_url
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from hub.db import make_engine
from hub.errors import install_error_handlers

pytestmark = pytest.mark.integration

# Herkenbare testwaarden (geen echt geheim).
UNIEK = "asm-k33-uniek-0123456789"
RIJ = "asm-k33-rij-geheim-9876543210"
VERBODEN = (UNIEK, RIJ, "DETAIL", "Failing row", "Key (")


def _schending(engine: Engine, soort: str) -> DBAPIError:
    """Een echte unique- of check-schending op een tijdelijke tabel met benoemde constraints."""
    with engine.connect() as conn, pytest.raises(DBAPIError) as info:
        conn.execute(
            text(
                "CREATE TEMP TABLE k33_proef (sleutel varchar(64), geheim varchar(64), getal int,"
                " CONSTRAINT k33_sleutel_uniek UNIQUE (sleutel), CONSTRAINT k33_getal_positief CHECK (getal > 0))"
            )
        )
        conn.execute(text("INSERT INTO k33_proef VALUES (:s, :g, 1)"), {"s": UNIEK, "g": RIJ})
        if soort == "unique":
            conn.execute(text("INSERT INTO k33_proef VALUES (:s, :g, 2)"), {"s": UNIEK, "g": RIJ})
        else:
            conn.execute(text("INSERT INTO k33_proef VALUES (:s, :g, -1)"), {"s": "ander", "g": RIJ})
    # Zonder de maatregel staat de waarde in de fouttekst; anders kan deze test niet falen.
    assert "DETAIL" in str(info.value)
    return info.value


VERWACHT = {
    "unique": ("23505", "k33_sleutel_uniek"),
    "check": ("23514", "k33_getal_positief"),
}


@pytest.fixture
def engine(clean_db: str) -> Any:
    e = make_engine(_psycopg_url(clean_db))
    yield e
    e.dispose()


def _controleer_log(tekst: str, soort: str) -> None:
    for verboden in VERBODEN:
        assert verboden not in tekst, f"{verboden!r} staat in de log:\n{tekst}"
    sqlstate, constraint = VERWACHT[soort]
    assert f"sqlstate {sqlstate}" in tekst
    assert f"constraint {constraint}" in tekst
    assert "tabel k33_proef" in tekst


@pytest.mark.parametrize("soort", ["unique", "check"])
def test_api_algemene_foutafhandeling_zonder_detail(
    engine: Engine, soort: str, caplog: pytest.LogCaptureFixture
) -> None:
    app = FastAPI()
    install_error_handlers(app)
    trace = str(uuid.uuid4())

    @app.middleware("http")
    async def _trace(request: Request, call_next: Any) -> Any:  # zoals hub.app: trace_id op request.state
        request.state.trace_id = trace
        return await call_next(request)

    @app.get("/k33")
    def _route() -> None:
        raise _schending(engine, soort)

    caplog.clear()
    with caplog.at_level(logging.INFO), TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/k33")
    # Het HTTP-antwoord blijft zoals het was.
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal_error"
    assert body["message"] == "Interne fout; de details staan in de app-log onder deze trace_id."
    assert body["details"] == {}
    assert body["trace_id"] == trace
    fouten = [rec for rec in caplog.records if rec.name == "hub.errors"]
    assert fouten, "de fout is niet gelogd"
    assert body["trace_id"] in caplog.text
    _controleer_log(caplog.text, soort)


@pytest.mark.parametrize("soort", ["unique", "check"])
def test_worker_job_zonder_detail(
    engine: Engine,
    worker_once: Any,
    app: Any,
    soort: str,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from hub import worker
    from hub.models import Job

    fout = _schending(engine, soort)

    def kapot(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise fout

    monkeypatch.setattr(worker, "_run_job", kapot)
    with app.state.sessionmaker() as db:
        db.add(Job(kind="self_backup", status="queued", requested_by="k33", params={}))
        db.commit()
    caplog.clear()
    with caplog.at_level(logging.INFO):
        done = worker_once()
    assert len(done) == 1
    # Het jobresultaat blijft zoals het was.
    assert done[0]["status"] == "failed"
    assert done[0]["reason_code"] == "exception"
    assert done[0]["fout"] == type(fout).__name__
    assert any(rec.name == "hub.worker" and "mislukt" in rec.getMessage() for rec in caplog.records)
    _controleer_log(caplog.text, soort)


def _stroom(handler_filter: bool = True) -> tuple[logging.Logger, io.StringIO]:
    from hub.logfilter import install_log_filter

    stroom = io.StringIO()
    logger = logging.getLogger(f"k33.proef.{uuid.uuid4().hex}")
    logger.propagate = False
    handler = logging.StreamHandler(stroom)
    logger.addHandler(handler)
    if handler_filter:
        install_log_filter(logger)
        install_log_filter(logger)  # tweemaal aanhaken mag
        assert len(handler.filters) == 1
    return logger, stroom


@pytest.mark.parametrize("soort", ["unique", "check"])
def test_filter_haalt_detail_uit_bericht_en_traceback(engine: Engine, soort: str) -> None:
    from hub.logfilter import DETAIL_WEGGELATEN

    fout = _schending(engine, soort)
    logger, stroom = _stroom()
    try:
        raise fout
    except DBAPIError:
        logger.exception("elders gelogd: %s", fout)
    tekst = stroom.getvalue()
    # De aantekening zelf bevat het woord DETAIL; verboden is de regel van PostgreSQL ("DETAIL:  Key (...").
    for verboden in (UNIEK, RIJ, "DETAIL:", "Failing row", "Key ("):
        assert verboden not in tekst, f"{verboden!r} staat in de log:\n{tekst}"
    assert DETAIL_WEGGELATEN in tekst
    assert "elders gelogd" in tekst


def test_filter_laat_gewone_regels_en_args_staan() -> None:
    from hub.logfilter import DbDetailFilter

    record = logging.LogRecord("x", logging.INFO, __file__, 1, "%s - %s", ("a", "b"), None)
    assert DbDetailFilter().filter(record) is True
    assert record.args == ("a", "b")
    assert record.getMessage() == "a - b"


def test_uvicorn_logconfig_heeft_het_filter_op_elke_handler() -> None:
    from hub.logfilter import uvicorn_log_config

    config = uvicorn_log_config()
    assert config["filters"]["db_detail"] == {"()": "hub.logfilter.DbDetailFilter"}
    assert config["handlers"]
    for handler in config["handlers"].values():
        assert "db_detail" in handler["filters"]
