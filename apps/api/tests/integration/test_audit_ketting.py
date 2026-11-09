"""Auditspoor append-only met hash-ketting (ADR-0022): verzegelen bij commit, trigger, verificatie, anker,
gelijktijdige schrijvers, rollback en het verzegelen van bestaande rijen door migratie 0006."""

from __future__ import annotations

import os
import threading
from typing import Any

import psycopg
import pytest
from conftest import idem

from hub import audit

pytestmark = pytest.mark.integration


def _pg(settings: Any) -> str:
    return str(settings.database_url).replace("postgresql+psycopg://", "postgresql://", 1)


def test_ketting_doorlopend_en_intact_na_beheerhandelingen(admin: Any, settings: Any) -> None:
    for i in range(3):
        r = admin.post(
            "/api/v1/users",
            json={"username": f"gebruiker{i}", "password": "Lang-Genoeg-Wachtwoord-1", "role": "viewer"},
            headers=idem(),
        )
        assert r.status_code == 201, r.text
    items = admin.get("/api/v1/audit?limit=200").json()["items"]
    nrs = sorted(i["ketting_nr"] for i in items)
    assert nrs == list(range(1, len(items) + 1)), "ketting_nr moet doorlopend en gatloos zijn"
    by_nr = {i["ketting_nr"]: i for i in items}
    for nr in nrs[1:]:
        assert by_nr[nr]["prev_hash"] == by_nr[nr - 1]["hash"]
    assert by_nr[1]["prev_hash"] == audit.GENESIS
    res = admin.get("/api/v1/audit/verify").json()
    assert res["status"] == "intact" and res["gecontroleerd"] == len(items)
    assert res["kop"] == {"nr": nrs[-1], "hash": by_nr[nrs[-1]]["hash"]}
    # Geheimen staan nooit in de details (contract §3.10).
    created = [i for i in items if i["actie"] == "user.created"]
    assert created and all("Lang-Genoeg" not in str(i) for i in items)


def test_trigger_weigert_wijzigen_en_verwijderen(admin: Any, settings: Any) -> None:
    with psycopg.connect(_pg(settings), autocommit=True) as conn:
        rid = conn.execute("SELECT id FROM audit_event ORDER BY id LIMIT 1").fetchone()[0]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE audit_event SET action = 'iets.anders' WHERE id = %s", (rid,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("UPDATE audit_event SET hash = repeat('0', 64) WHERE id = %s", (rid,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM audit_event WHERE id = %s", (rid,))
    assert admin.get("/api/v1/audit/verify").json()["status"] == "intact"


def _tamper(settings: Any, sql: str, params: tuple[Any, ...] = ()) -> None:
    """Alleen tests: de trigger omzeilen zoals een database-eigenaar zou kunnen; de ketting moet het dan verraden."""
    with psycopg.connect(_pg(settings), autocommit=True) as conn:
        conn.execute("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only")
        try:
            conn.execute(sql, params)
        finally:
            conn.execute("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only")


def test_manipulatie_wordt_gevonden(admin: Any, settings: Any) -> None:
    for i in range(4):
        admin.post(
            "/api/v1/users",
            json={"username": f"m{i}-gebruiker", "password": "Lang-Genoeg-Wachtwoord-1", "role": "viewer"},
            headers=idem(),
        ).raise_for_status()
    _tamper(settings, 'UPDATE audit_event SET details = \'{"role": "admin"}\'::jsonb WHERE ketting_nr = 3')
    res = admin.get("/api/v1/audit/verify").json()
    assert res["status"] == "verbroken"
    assert res["fouten"][0]["soort"] == "inhoud_gewijzigd" and res["fouten"][0]["nr"] == 3
    assert "admin" not in str(res["fouten"]), "de uitkomst noemt geen inhoud"


def test_verwijderde_rij_geeft_gat(admin: Any, settings: Any) -> None:
    for i in range(3):
        admin.post(
            "/api/v1/users",
            json={"username": f"g{i}-gebruiker", "password": "Lang-Genoeg-Wachtwoord-1", "role": "viewer"},
            headers=idem(),
        ).raise_for_status()
    _tamper(settings, "DELETE FROM audit_event WHERE ketting_nr = 2")
    res = admin.get("/api/v1/audit/verify").json()
    assert res["status"] == "verbroken" and res["fouten"][0]["soort"] == "gat_in_nummering"


def test_anker_vindt_afgeknipte_staart(admin: Any, app: Any, settings: Any, periodic_run: Any) -> None:
    admin.post(
        "/api/v1/users",
        json={"username": "staart-test", "password": "Lang-Genoeg-Wachtwoord-1", "role": "viewer"},
        headers=idem(),
    ).raise_for_status()
    out = periodic_run("audit_verankeren")["audit_verankeren"]
    assert out["status"] == "geschreven" and out["nr"] >= 2
    path = audit.anchor_path(settings.data_dir)
    assert path.exists() and oct(path.stat().st_mode & 0o777) == "0o600"
    assert admin.get("/api/v1/audit/verify").json()["anker"]["status"] == "ok"
    top = out["nr"]
    _tamper(settings, "DELETE FROM audit_event WHERE ketting_nr = %s", (top,))
    res = admin.get("/api/v1/audit/verify").json()
    assert res["status"] == "verbroken"
    assert res["fouten"][0]["soort"] == "staart_ontbreekt" and res["anker"]["status"] == "afgeknipt"
    # De dagelijkse controle maakt er één event van (en niet bij elke volgende ronde opnieuw).
    first = periodic_run("audit_controleren")["audit_controleren"]
    assert first["status"] == "verbroken"
    periodic_run("audit_controleren")
    with app.state.sessionmaker() as db:
        from sqlalchemy import func, select

        from hub.models import OutboxEvent

        n = db.scalar(
            select(func.count()).select_from(OutboxEvent).where(OutboxEvent.event_type == "audit.chain.broken")
        )
    assert n == 1


def test_gelijktijdige_schrijvers_en_rollback(app: Any, settings: Any) -> None:
    factory = app.state.sessionmaker
    with factory() as db:
        audit.record(db, actor_type="system", actor_id="test", action="test.rollback")
        db.rollback()
    errors: list[BaseException] = []

    def writer(n: int) -> None:
        try:
            for i in range(10):
                with factory() as db:
                    audit.record(
                        db,
                        actor_type="system",
                        actor_id=f"draad-{n}",
                        action="test.gelijktijdig",
                        details={"i": i, "token": "geheim-dat-weg-moet"},
                    )
                    audit.record(db, actor_type="system", actor_id=f"draad-{n}", action="test.tweede")
                    db.commit()
        except BaseException as exc:  # pragma: no cover - alleen bij een fout
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    with factory() as db:
        res = audit.verify(db, settings.data_dir)
        assert res["status"] == "intact", res
        assert res["gecontroleerd"] == 6 * 10 * 2
        from sqlalchemy import select

        from hub.models import AuditEvent

        details = [r.details for r in db.scalars(select(AuditEvent).where(AuditEvent.action == "test.gelijktijdig"))]
    assert details and all(d["token"] == "***" for d in details)


def test_migratie_verzegelt_bestaande_rijen(pg_url: str) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from hub import migrations

    base, _, _ = pg_url.rpartition("/")
    name = "asm_test_audit_" + os.urandom(3).hex()
    admin_url = base + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    url = f"{base}/{name}"
    sa_url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    try:
        migrations.upgrade(sa_url, "0005")
        with psycopg.connect(url, autocommit=True) as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO audit_event (at, actor_type, actor_id, action, target_type, target_id, details, "
                    "trace_id) VALUES (now(), 'user', %s, 'oud.record', '', '', %s::jsonb, '')",
                    (f"u{i}", '{"a": 1.5, "b": [1, 2], "ç": "ü"}'),
                )
        migrations.upgrade(sa_url)
        engine = create_engine(sa_url)
        with Session(engine) as db:
            res = audit.verify(db)
            assert res["status"] == "intact" and res["gecontroleerd"] == 5
            audit.record(db, actor_type="system", actor_id="na-migratie", action="nieuw.record")
            db.commit()
            res = audit.verify(db)
            assert res["status"] == "intact" and res["gecontroleerd"] == 6
        engine.dispose()
        migrations.downgrade(sa_url, "0005")
        migrations.upgrade(sa_url)
    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
