"""M3 tegen de echte Hub en de lokale TrueNAS-WebSocket-simulator."""

from __future__ import annotations

import asyncio
import secrets
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from multiprocessing import get_context
from pathlib import Path
from threading import Event, Thread, current_thread
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import enroll_body
from nashelpers import READONLY_KEY, connect

PATH = "/api/v1/catalog/availability"
PIN = {"train": "stable", "app": "ix-app", "version": "1.4.8"}
NOW = datetime(2026, 11, 18, 15, tzinfo=UTC)

pytestmark = pytest.mark.integration


def _headers(admin: Any, app_id: str = "jelly-leon-platform") -> dict[str, str]:
    grant = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert grant.status_code == 201
    enrolled = admin.post("/api/v1/services/enroll", json=enroll_body(app_id, token=grant.json()["enrollment_token"]))
    assert enrolled.status_code == 200
    return {"Authorization": f"Bearer {enrolled.json()['service_token']}"}


@pytest.mark.parametrize(
    "query",
    [
        {"train": "Stable"},
        {"app": "ix/app"},
        {"app": "a" * 64},
        {"app": "ix-app\n"},
        {"version": "latest"},
        {"version": ">=1.4.8"},
        {"version": "1.4.8\n"},
        {"version": "1.4.8-" + "a" * 59},
        {"q": "ix-app"},
    ],
)
def test_weigert_ongeldige_catalogusquery(admin: Any, query: dict[str, str]) -> None:
    r = admin.get(PATH, params={**PIN, **query}, headers=_headers(admin))
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error" and r.json()["details"]["fouten"]


def test_weigert_dubbele_ontbrekende_en_body(admin: Any) -> None:
    headers = _headers(admin)
    for r in (
        admin.get(PATH, params=[*PIN.items(), ("version", PIN["version"])], headers=headers),
        admin.get(PATH, params={"train": "stable", "app": "ix-app"}, headers=headers),
        admin.request("GET", PATH, params=PIN, headers=headers, content=b"{}"),
    ):
        assert r.status_code == 422
        assert r.json()["code"] == "validation_error" and r.json()["details"]["fouten"]


@pytest.mark.parametrize(
    ("toestand", "reden"),
    [
        ("sessie", "invalid_token"),
        ("ongeldig", "invalid_token"),
        ("verlopen", "token_expired"),
        ("ingetrokken", "revoked"),
    ],
)
def test_401_bevat_contractreden(admin: Any, app: Any, toestand: str, reden: str) -> None:
    from sqlalchemy import select

    from hub.models import ServiceToken
    from hub.timeutil import utcnow

    headers = _headers(admin) if toestand in {"verlopen", "ingetrokken"} else {}
    if toestand == "ongeldig":
        headers = {"Authorization": "Bearer geen-diensttoken"}
    if toestand in {"verlopen", "ingetrokken"}:
        with app.state.sessionmaker.begin() as db:
            token = db.scalars(select(ServiceToken)).one()
            if toestand == "verlopen":
                token.expires_at = utcnow() - timedelta(minutes=1)
            else:
                token.revoked_at = utcnow()
    r = admin.get(PATH, params=PIN, headers=headers)
    assert r.status_code == 401
    assert set(r.json()) == {"code", "message", "details", "trace_id"}
    assert r.json()["code"] == "unauthorized" and r.json()["details"] == {"reason": reden}


def test_onvolledige_trein_bewijst_geen_afwezigheid(admin: Any, fake_nas: Any, worker_once: Any) -> None:
    connect(admin, fake_nas)
    headers = _headers(admin)
    fake_nas.data["catalog.apps"]["stable"] = {
        "andere-app": {"name": "andere-app", "healthy": False},
    }
    assert PIN["version"] in fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]
    worker_once(schedule=True)
    assert admin.get(PATH, params=PIN, headers=headers).json() == {**PIN, "beschikbaar": "onbekend", "gemeten_op": None}


def test_verlopen_broncache_ververst_geen_meettijd(
    admin: Any, app: Any, fake_nas: Any, worker_once: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.catalog import availability
    from hub.models import CatalogSnapshot

    now = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    connect(admin, fake_nas)
    headers = _headers(admin)
    index = fake_nas.data["catalog.apps"]
    details = fake_nas.data["catalog.get_app_details"]
    for suffix in "abc":
        naam = "app-" + suffix
        entry = {"name": naam, "healthy": True, "latest_version": "1.0.0"}
        index["community"][naam] = entry
        details["community"][naam] = {**entry, "versions": {"1.0.0": {"version": "1.0.0"}}}
    pin = {"train": "community", "app": "app-c", "version": "1.0.0"}
    worker_once(schedule=True)
    assert admin.get(PATH, params=pin, headers=headers).json()["beschikbaar"] == "ja"
    details["community"]["app-c"]["versions"] = {"1.0.1": {"version": "1.0.1"}}
    now += timedelta(seconds=901)
    onbekend = {**pin, "beschikbaar": "onbekend", "gemeten_op": None}
    assert admin.get(PATH, params=pin, headers=headers).json() == onbekend
    start = len(fake_nas.calls)
    worker_once(schedule=True)
    assert ("catalog.get_app_details", ["app-c", {"train": "community"}]) not in fake_nas.calls[start:]
    assert admin.get(PATH, params=pin, headers=headers).json() == onbekend
    with app.state.sessionmaker.begin() as db:
        snapshot = db.get(CatalogSnapshot, 1)
        assert snapshot is not None
        snapshot.catalog = {"community": {"app-c": {"latest": "1.0.0", "versions": {"1.0.0": True}}}}
    assert admin.get(PATH, params=pin, headers=headers).json() == onbekend


def test_deadline_omvat_kluistijd(
    admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import select

    from hub.catalog import availability
    from hub.models import CatalogAttempt

    connect(admin, fake_nas)
    headers = _headers(admin)
    factory, vault = app.state.sessionmaker, app.state.vault()
    started = 0.0
    monkeypatch.setattr(availability, "time", SimpleNamespace(monotonic=lambda: started))
    real_get = vault.get

    def trage_kluis(db: Any, ref: str) -> str | None:
        nonlocal started
        with factory() as lezer:
            poging = lezer.scalars(select(CatalogAttempt)).one()
            assert poging.completed_at is None
        assert admin.get(PATH, params=PIN, headers=headers).json()["gemeten_op"] is None
        started += availability.MEASUREMENT_TIMEOUT + 0.2
        return real_get(db, ref)

    monkeypatch.setattr(vault, "get", trage_kluis)
    calls = list(fake_nas.calls)
    availability.refresh_if_due(factory, settings, vault)
    assert fake_nas.calls == calls
    assert admin.get(PATH, params=PIN, headers=headers).json() == {**PIN, "beschikbaar": "onbekend", "gemeten_op": None}


@pytest.mark.parametrize("fase", ["schrijven", "commit"])
def test_deadline_omvat_publicatie(
    admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch, fase: str
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    connect(admin, fake_nas)
    headers = _headers(admin)
    factory = app.state.sessionmaker
    nu = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: nu)
    availability.refresh_if_due(factory, settings, app.state.vault())
    pins = (PIN, {**PIN, "version": "1.4.7"})
    assert [admin.get(PATH, params=pin, headers=headers).json()["beschikbaar"] for pin in pins] == ["ja", "nee"]
    nu += availability.MEASUREMENT_INTERVAL
    start_bron = len(fake_nas.calls)
    grens = 2.0
    monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", grens)
    fake_nas.delays["catalog.apps"] = 0.8
    with factory.begin() as db:
        db.execute(
            text("""
            CREATE FUNCTION trage_publicatie() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN PERFORM pg_sleep(3); RETURN NULL; END $$
        """)
        )
        db.execute(
            text("""
            CREATE CONSTRAINT TRIGGER trage_publicatie AFTER UPDATE ON catalog_snapshot
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.observed_at IS NOT NULL)
            EXECUTE FUNCTION trage_publicatie()
        """)
        )
        if fase == "commit":
            db.execute(
                text("""CREATE FUNCTION uitstel_publicatie() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN SET CONSTRAINTS trage_publicatie DEFERRED; RETURN NEW; END $$""")
            )
            db.execute(
                text("""CREATE TRIGGER uitstel_publicatie BEFORE UPDATE ON catalog_snapshot
                FOR EACH ROW EXECUTE FUNCTION uitstel_publicatie()""")
            )
    try:
        start = time.monotonic()
        availability.refresh_if_due(factory, settings, app.state.vault())
        duur = time.monotonic() - start
        for pin in pins:
            antwoord = admin.get(PATH, params=pin, headers=headers)
            assert antwoord.status_code == 200
            assert antwoord.json() == {**pin, "beschikbaar": "onbekend", "gemeten_op": None}
        assert any(method == "catalog.get_app_details" for method, _ in fake_nas.calls[start_bron:])
        assert not fake_nas.mutations
        assert duur < grens + 0.5
        with factory.begin() as db:
            assert db.scalar(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": availability.MEASUREMENT_LOCK})
    finally:
        with factory.begin() as db:
            if fase == "commit":
                db.execute(text("DROP TRIGGER uitstel_publicatie ON catalog_snapshot"))
                db.execute(text("DROP FUNCTION uitstel_publicatie()"))
            db.execute(text("DROP TRIGGER trage_publicatie ON catalog_snapshot"))
            db.execute(text("DROP FUNCTION trage_publicatie()"))


def test_deadline_omvat_vertraagde_reservering(
    admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    connect(admin, fake_nas)
    headers = _headers(admin)
    factory = app.state.sessionmaker
    nu = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: nu)
    availability.refresh_if_due(factory, settings, app.state.vault())
    pins = (PIN, {**PIN, "version": "1.4.7"})
    assert [admin.get(PATH, params=pin, headers=headers).json()["beschikbaar"] for pin in pins] == ["ja", "nee"]
    nu += availability.MEASUREMENT_INTERVAL
    grens = 1.5
    monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", grens)
    calls = list(fake_nas.calls)
    with ThreadPoolExecutor(max_workers=1) as worker, factory.begin() as houder:
        houder.execute(text("SELECT id FROM catalog_snapshot WHERE id = 1 FOR UPDATE"))

        def meet() -> float:
            begin = time.monotonic()
            availability.refresh_if_due(factory, settings, app.state.vault())
            return time.monotonic() - begin

        taak = worker.submit(meet)
        time.sleep(grens + 0.4)  # de rij blijft tot na de grens bezet
        for pin in pins:
            assert admin.get(PATH, params=pin, headers=headers).json() == {
                **pin,
                "beschikbaar": "onbekend",
                "gemeten_op": None,
            }
        with factory.begin() as lezer:
            meetlock_vrij = lezer.scalar(
                text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": availability.MEASUREMENT_LOCK}
            )
        worker_vrij = taak.done()
    duur = taak.result(timeout=5)
    assert worker_vrij and meetlock_vrij
    assert duur <= grens
    with factory.begin() as lezer:
        assert lezer.scalar(text("SELECT failed FROM catalog_attempt WHERE started_at = :nu"), {"nu": nu})
    for pin in pins:
        assert admin.get(PATH, params=pin, headers=headers).json() == {
            **pin,
            "beschikbaar": "onbekend",
            "gemeten_op": None,
        }
    assert fake_nas.calls == calls and not fake_nas.mutations


def test_onleesbare_kluis_laat_periodieke_taken_door(
    admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub import worker
    from hub.catalog import availability
    from hub.vault import Vault

    connect(admin, fake_nas)
    headers = _headers(admin)
    factory = app.state.sessionmaker
    now = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    worker.run_once(factory, settings, app.state.vault())
    assert admin.get(PATH, params=PIN, headers=headers).json()["beschikbaar"] == "ja"
    calls = len(fake_nas.calls)
    periodiek = []

    def run_due(*args: Any) -> list[Any]:
        periodiek.append(True)
        return []

    monkeypatch.setattr(worker.periodic, "run_due", run_due)
    now += timedelta(seconds=300)
    worker.run_once(factory, settings, Vault(secrets.token_bytes(32)))
    assert periodiek == [True]
    assert all(not method.startswith("catalog.") for method, _ in fake_nas.calls[calls:])
    assert admin.get(PATH, params=PIN, headers=headers).json() == {**PIN, "beschikbaar": "onbekend", "gemeten_op": None}


def test_meting_versheid_en_geen_bronaanroepen_per_leesverzoek(
    admin: Any, app: Any, fake_nas: Any, worker_once: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.catalog import availability
    from hub.models import CatalogSnapshot

    now = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    connect(admin, fake_nas)
    headers = _headers(admin)

    def read(**vervang: str) -> dict[str, Any]:
        query = {**PIN, **vervang}
        response = admin.get(PATH, params=query, headers=headers)
        assert response.status_code == 200
        result = response.json()
        assert result == {**query, "beschikbaar": result["beschikbaar"], "gemeten_op": result["gemeten_op"]}
        return result

    assert read() == {**PIN, "beschikbaar": "onbekend", "gemeten_op": None}
    fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]["1.4.6"] = {"version": "1.4.6"}
    worker_once(schedule=True)
    calls = list(fake_nas.calls)
    meting = read()
    assert meting == {**PIN, "beschikbaar": "ja", "gemeten_op": "2026-11-18T15:00:00Z"}
    assert read(version="1.4.7")["beschikbaar"] == "nee"
    assert read(version="1.4.6")["beschikbaar"] == "ja"
    assert read(train="community") == {
        **PIN,
        "train": "community",
        "beschikbaar": "onbekend",
        "gemeten_op": None,
    }
    assert read(train="community", app="authentik", version="1.3.64")["beschikbaar"] == "ja"
    assert read(train="enterprise")["beschikbaar"] == "onbekend"
    assert read(version="v1.4.8")["beschikbaar"] == "nee"
    assert [params for method, params in calls if method == "catalog.apps"] == [
        [{"cache": True, "cache_only": True, "retrieve_all_trains": True}]
    ]
    assert fake_nas.calls == calls
    assert not fake_nas.mutations

    now = NOW - timedelta(seconds=121)
    assert read()["gemeten_op"] is None
    now = NOW - timedelta(seconds=120)
    assert read() == meting
    now = NOW + timedelta(seconds=900)
    assert read() == {**PIN, "beschikbaar": "onbekend", "gemeten_op": None}
    assert fake_nas.calls == calls
    # Isoleer de twee grenzen: een nieuwe bevestiging kan de ouderdom van de
    # onderliggende brongegevens niet verkorten. Toets de bron exact op 900 en 901 s.
    worker_once(schedule=True)
    with app.state.sessionmaker.begin() as db:
        db.get(CatalogSnapshot, 1).observed_at = NOW
    assert read() == meting
    now += timedelta(seconds=1)
    assert read(version="1.4.7")["beschikbaar"] == "onbekend"
    assert read()["gemeten_op"] is None


@pytest.mark.parametrize(
    "storing",
    ["geen_methode", "bronfout", "onvolledig", "overschrijding", "cumulatieve_bytes", "te_veel_combinaties", "timeout"],
)
def test_mislukte_meting_trekt_een_oude_nee_in(
    admin: Any, fake_nas: Any, worker_once: Any, monkeypatch: pytest.MonkeyPatch, storing: str
) -> None:
    from hub.catalog import availability

    now = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    connect(admin, fake_nas)
    headers = _headers(admin)
    query = {**PIN, "version": "1.4.7"}
    worker_once(schedule=True)
    assert admin.get(PATH, params=query, headers=headers).json()["beschikbaar"] == "nee"
    if storing == "geen_methode":
        fake_nas.hidden.add("catalog.get_app_details")
    elif storing == "bronfout":
        fake_nas.keys[READONLY_KEY].deny.add("catalog.apps")
    elif storing == "onvolledig":
        fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"] = {}
    elif storing == "overschrijding":
        fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["extra"] = "x" * (8 * 1024 * 1024)
    elif storing == "cumulatieve_bytes":
        monkeypatch.setattr(availability, "MAX_SOURCE_BYTES", 8192)
        fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["extra"] = "x" * 4600
        fake_nas.data["catalog.get_app_details"]["community"]["authentik"]["extra"] = "x" * 4600
    elif storing == "te_veel_combinaties":
        monkeypatch.setattr(availability, "MAX_COMBINATIONS", 2)
        fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]["1.4.6"] = {"version": "1.4.6"}
    else:
        monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", 0.1)
        fake_nas.delays["catalog.apps"] = 0.3
    now += timedelta(seconds=299)
    worker_once(schedule=True)
    assert admin.get(PATH, params=query, headers=headers).json()["beschikbaar"] == "nee"
    now += timedelta(seconds=1)
    worker_once(schedule=True)
    r = admin.get(PATH, params=query, headers=headers)
    assert r.status_code == 200
    assert r.json() == {**query, "beschikbaar": "onbekend", "gemeten_op": None}


def test_limiet_is_voortschrijdend_per_dienst_ook_bij_rotatie(admin: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from hub.catalog import availability

    now = NOW
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    headers = _headers(admin)
    ander = _headers(admin, "home-control-hub")

    def read(version: str) -> int:
        return int(admin.get(PATH, params={**PIN, "version": version}, headers=headers).status_code)

    assert read("1.4.8") == 200
    now += timedelta(seconds=50)
    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(read, (f"1.2.{i}" for i in range(61))))
    assert codes.count(200) == 59 and codes.count(429) == 2
    r = admin.post("/api/v1/services/self/rotate", headers=headers)
    assert r.status_code == 200
    nieuw = {"Authorization": f"Bearer {r.json()['service_token']}"}
    r = admin.get(PATH, params=PIN, headers=nieuw)
    assert r.status_code == 429 and r.headers["Retry-After"] == "10"
    assert r.json()["code"] == "rate_limited"
    assert admin.get(PATH, params=PIN, headers=ander).status_code == 200
    now += timedelta(seconds=10)
    assert admin.get(PATH, params=PIN, headers=nieuw).status_code == 200
    assert admin.get(PATH, params=PIN, headers=headers).status_code == 429


def test_onleesbare_meetvoorraad_geeft_503(admin: Any, app: Any, fake_nas: Any) -> None:
    from sqlalchemy import text

    connect(admin, fake_nas)
    headers = _headers(admin)
    with app.state.sessionmaker.begin() as db:
        # Eigen testdatabase. Een omkeerbare wijziging maakt alleen de meetvoorraad onleesbaar.
        db.execute(text("ALTER TABLE catalog_snapshot RENAME TO catalog_snapshot_test"))
    try:
        r = admin.get(PATH, params=PIN, headers=headers)
        assert r.status_code == 503 and r.headers["Retry-After"] == "5"
        assert set(r.json()) == {"code", "message", "details", "trace_id"}
        assert r.json()["code"] == "dependency_unavailable"
        assert r.json()["details"] == {}
    finally:
        with app.state.sessionmaker.begin() as db:
            db.execute(text("ALTER TABLE catalog_snapshot_test RENAME TO catalog_snapshot"))


def test_tweede_worker_start_geen_meting_tijdens_een_lopende_meting(
    admin: Any, app: Any, fake_nas: Any, worker_once: Any
) -> None:
    from sqlalchemy import text

    from hub.catalog.availability import MEASUREMENT_LOCK

    connect(admin, fake_nas)
    with app.state.sessionmaker.begin() as db:
        assert db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": MEASUREMENT_LOCK})
        worker_once(schedule=True)
        assert all(method != "catalog.apps" for method, _ in fake_nas.calls)
    worker_once(schedule=True)
    assert sum(method == "catalog.apps" for method, _ in fake_nas.calls) == 1


@pytest.fixture
def vorige_meting(admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    from hub.catalog import availability

    connect(admin, fake_nas)
    headers = _headers(admin)
    with monkeypatch.context() as klok:
        klok.setattr(availability, "utcnow", lambda: datetime.now(UTC) - timedelta(seconds=301))
        availability.refresh_if_due(app.state.sessionmaker, settings, app.state.vault())

    def pins() -> list[tuple[str, str | None]]:
        return _lees_pins(admin, headers)

    assert [staat for staat, _ in pins()] == ["ja", "nee"]
    return pins


def _lees_pins(client: Any, headers: dict[str, str]) -> list[tuple[str, str | None]]:
    pins = []
    for versie in (PIN["version"], "1.4.7"):
        response = client.get(PATH, params={**PIN, "version": versie}, headers=headers)
        assert response.status_code == 200
        pins.append((response.json()["beschikbaar"], response.json()["gemeten_op"]))
    return pins


def _lees_in_hub(settings: Any, headers: dict[str, str]) -> list[tuple[str, str | None]]:
    from fastapi.testclient import TestClient

    from hub.app import create_app

    with TestClient(create_app(settings), base_url="https://testserver") as client:
        return _lees_pins(client, headers)


def _pins_na_herstart(settings: Any, headers: dict[str, str]) -> list[tuple[str, str | None]]:
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as proces:
        return proces.submit(_lees_in_hub, settings, headers).result(timeout=15)


@pytest.mark.parametrize("leesfout", [PermissionError, BlockingIOError])
def test_leesroute_weigert_onleesbaar_oud_en_onvolledig_meetbewijs(
    vorige_meting: Any,
    admin: Any,
    settings: Any,
    fake_nas: Any,
    monkeypatch: pytest.MonkeyPatch,
    leesfout: type[OSError],
) -> None:
    from hub.catalog import availability

    headers = _headers(admin, "home-control-hub")
    bewijs = settings.data_dir / availability.MEASUREMENT_RECEIPT
    velden = bewijs.read_bytes().split()
    bron = list(fake_nas.calls)

    def geweigerd(pad: Any, modus: str, **opties: Any) -> Any:
        if pad == bewijs and modus == "rb":
            raise leesfout("Het meetbewijs is niet leesbaar.")
        return open(pad, modus, **opties)

    with monkeypatch.context() as opslag:
        opslag.setattr(availability, "open", geweigerd, raising=False)
        antwoord = admin.get(PATH, params=PIN, headers=headers)
    assert antwoord.status_code == 503 and antwoord.json()["code"] == "dependency_unavailable"
    assert int(antwoord.headers["Retry-After"]) > 0
    for inhoud in (velden[0], b" ".join(velden[:3]), b"onvolledig"):
        bewijs.write_bytes(inhoud)
        assert vorige_meting() == [("onbekend", None)] * 2
    assert fake_nas.calls == bron and not fake_nas.mutations


def test_alleen_leesbaar_bewijs_en_bezette_voorraad(
    vorige_meting: Any, admin: Any, app: Any, settings: Any, fake_nas: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    headers = _headers(admin, "home-control-hub")
    bewijs = settings.data_dir / availability.MEASUREMENT_RECEIPT
    versies = fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]
    assert "1.4.7" not in versies
    versies["1.4.7"] = {"version": "1.4.7"}
    bron = list(fake_nas.calls)
    onbekend = [("onbekend", None)] * 2

    def alleen_lezen(pad: Any, modus: str, **opties: Any) -> Any:
        if pad == bewijs and modus == "a+b":
            raise PermissionError("Het meetbewijs is alleen leesbaar.")
        return open(pad, modus, **opties)

    with monkeypatch.context() as opslag, app.state.sessionmaker.begin() as houder:
        opslag.setattr(availability, "open", alleen_lezen, raising=False)
        opslag.setattr(availability, "MEASUREMENT_TIMEOUT", 0.75)
        houder.execute(text("SELECT id FROM catalog_snapshot WHERE id=1 FOR UPDATE")).scalar_one()
        houder.execute(text("LOCK TABLE catalog_attempt IN SHARE MODE"))
        begin = time.monotonic()
        availability.refresh_if_due(app.state.sessionmaker, settings, app.state.vault())
        time.sleep(max(0.0, begin + 0.85 - time.monotonic()))
        tijdens = vorige_meting()
    assert tijdens == _pins_na_herstart(settings, headers) == onbekend
    assert fake_nas.calls == bron
    monkeypatch.setattr(availability, "utcnow", lambda: datetime.now(UTC) + timedelta(seconds=301))
    availability.refresh_if_due(app.state.sessionmaker, settings, app.state.vault())
    assert all(staat == "ja" and tijd is not None for staat, tijd in vorige_meting())
    assert not fake_nas.mutations


@pytest.mark.parametrize("storing", ["map_en_onderhoud", "trage_weigering"])
def test_onzekere_intrekking_vervalt_ook_na_herstart(
    vorige_meting: Any,
    admin: Any,
    app: Any,
    settings: Any,
    fake_nas: Any,
    monkeypatch: pytest.MonkeyPatch,
    storing: str,
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    voor = vorige_meting()
    headers = _headers(admin, "home-control-hub")
    bevestiging = (settings.data_dir / availability.MEASUREMENT_RECEIPT).with_suffix(".bevestigd")
    versies = fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]
    versies["1.4.7"] = {"version": "1.4.7"}
    bron = list(fake_nas.calls)
    geweigerd, vrij = Event(), Event()
    schrijvers: list[Thread] = []
    verwijderen = Path.unlink

    def weiger(pad: Path, missing_ok: bool = False) -> None:
        if pad != bevestiging:
            return verwijderen(pad, missing_ok=missing_ok)
        schrijvers.append(current_thread())
        geweigerd.set()
        if storing == "trage_weigering":
            assert vrij.wait(5)
        raise PermissionError("De testmap is alleen leesbaar.")

    factory, vault = app.state.sessionmaker, app.state.vault()
    with monkeypatch.context() as opslag, factory.begin() as onderhoud, ThreadPoolExecutor(max_workers=1) as pool:
        opslag.setattr(availability, "MEASUREMENT_TIMEOUT", 1.0)
        opslag.setattr(Path, "unlink", weiger)
        if storing == "map_en_onderhoud":
            onderhoud.execute(text("LOCK TABLE catalog_attempt IN SHARE MODE"))
        werk = pool.submit(availability.refresh_if_due, factory, settings, vault)
        try:
            assert geweigerd.wait(3)
            werk.result(timeout=2)
        finally:
            vrij.set()
    for schrijver in schrijvers:
        schrijver.join(timeout=3)
        assert not schrijver.is_alive()
    # Dezelfde bestanden zijn weer toegankelijk. Zelfs binnen de normale bronversheid
    # en na het terugzetten van de klok mag de oude uitslag niet opnieuw verschijnen.
    onbekend = [("onbekend", None)] * 2
    assert bevestiging.exists()
    assert _pins_na_herstart(settings, headers) == onbekend
    with monkeypatch.context() as klok:
        klok.setattr(availability, "utcnow", lambda: datetime.fromisoformat(voor[0][1]))
        assert vorige_meting() == onbekend
    assert fake_nas.calls == bron
    with monkeypatch.context() as klok:
        klok.setattr(availability, "utcnow", lambda: datetime.now(UTC) + timedelta(seconds=301))
        availability.refresh_if_due(factory, settings, vault)
        assert all(staat == "ja" and tijd is not None for staat, tijd in vorige_meting())
    assert not fake_nas.mutations


@pytest.mark.parametrize("klok", ["bronklok", "verstreken_tijd"])
def test_bevestiging_verloopt_zonder_enige_schrijfhandeling(
    vorige_meting: Any, app: Any, monkeypatch: pytest.MonkeyPatch, klok: str
) -> None:
    from sqlalchemy import select

    from hub.catalog import availability
    from hub.models import CatalogAttempt

    voor = vorige_meting()
    with app.state.sessionmaker() as db:
        start = db.scalars(select(CatalogAttempt.started_at)).one()
    horizon = availability.MEASUREMENT_INTERVAL + timedelta(seconds=availability.MEASUREMENT_TIMEOUT)
    if klok == "bronklok":
        grens = start + horizon
        monkeypatch.setattr(availability, "utcnow", lambda: grens)
        assert vorige_meting() == voor
        grens += timedelta(microseconds=1)
    else:
        monkeypatch.setattr(availability, "utcnow", lambda: start)
        assert vorige_meting() == voor
        verlopen = time.monotonic_ns() + round(horizon.total_seconds() * 1_000_000_000)
        monkeypatch.setattr(availability, "monotonic_ns", lambda: verlopen, raising=False)
    assert vorige_meting() == [("onbekend", None)] * 2


@pytest.mark.parametrize("vertraging", ["voor_schrijven", "na_schrijven", "voor_koppelen", "na_koppelen"])
def test_late_bestandsbevestiging_mag_geen_pins_vrijgeven(
    admin: Any, app: Any, settings: Any, fake_nas: Any, monkeypatch: pytest.MonkeyPatch, vertraging: str
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    connect(admin, fake_nas)
    headers = _headers(admin)
    bewijs = settings.data_dir / availability.MEASUREMENT_RECEIPT
    schrijft, vrij, gesloten = Event(), Event(), Event()
    grens = 1.0
    onbekend = [("onbekend", None)] * 2

    def wacht() -> None:
        schrijft.set()
        assert vrij.wait(8)

    class TrageSchrijver:
        def __init__(self, bestand: Any):
            self.bestand = bestand

        def __getattr__(self, naam: str) -> Any:
            return getattr(self.bestand, naam)

        def write(self, data: bytes) -> int:
            if vertraging == "voor_schrijven":
                wacht()
            aantal = self.bestand.write(data)
            if vertraging == "na_schrijven":
                wacht()
            return aantal

    @contextmanager
    def open_testbestand(pad: Any, modus: str, **opties: Any) -> Iterator[Any]:
        with open(pad, modus, **opties) as bestand:
            if pad == bewijs and modus == "a+b":
                try:
                    yield TrageSchrijver(bestand)
                finally:
                    gesloten.set()
            else:
                yield bestand

    monkeypatch.setattr(availability, "open", open_testbestand, raising=False)
    monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", grens)
    bij_publicatie = []
    if vertraging in {"voor_koppelen", "na_koppelen"}:
        koppel = availability.os.link

        def koppel_te_laat(bron: Any, doel: Any, **opties: Any) -> None:
            if bron != bewijs:
                return koppel(bron, doel, **opties)
            if vertraging == "voor_koppelen":
                wacht()
            koppel(bron, doel, **opties)
            if vertraging == "na_koppelen":
                wacht()
            # De koppeling bestaat al. De schrijver kan haar nog niet opruimen.
            bij_publicatie.extend(_lees_pins(admin, headers))

        monkeypatch.setattr(availability.os, "link", koppel_te_laat)
    with ThreadPoolExecutor(max_workers=1) as worker:
        begin = time.monotonic()
        taak = worker.submit(availability.refresh_if_due, app.state.sessionmaker, settings, app.state.vault())
        try:
            assert schrijft.wait(5)
            with app.state.sessionmaker() as db:
                assert (
                    0
                    <= db.scalar(text("SELECT extract(epoch FROM completed_at - started_at) FROM catalog_attempt"))
                    <= grens
                )
            time.sleep(max(0.0, begin + grens + 0.2 - time.monotonic()))
            tijdig_terug = taak.done()
            tijdens = _lees_pins(admin, headers)
        finally:
            vrij.set()
        taak.result(timeout=5)
        assert gesloten.wait(5)
    if vertraging == "voor_koppelen":
        # Ook na een processtop vóór het opruimen moet de lezer de late publicatie zelf weigeren.
        bevestiging = bewijs.with_suffix(".bevestigd")
        if not bevestiging.exists():
            koppel(bewijs, bevestiging)
    na = _lees_pins(admin, headers)
    nieuw = _pins_na_herstart(settings, headers)
    assert tijdens == na == nieuw == onbekend
    if vertraging in {"voor_koppelen", "na_koppelen"}:
        assert bij_publicatie == onbekend
    assert tijdig_terug and not fake_nas.mutations


def test_geblokkeerde_voorraadlezing_houdt_worker_niet_vast(
    vorige_meting: Any, app: Any, settings: Any, fake_nas: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    factory = app.state.sessionmaker
    monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", 1.0)
    bron = list(fake_nas.calls)
    with ThreadPoolExecutor(max_workers=1) as worker, factory.begin() as houder:
        houder.execute(text("LOCK TABLE catalog_snapshot IN ACCESS EXCLUSIVE MODE"))
        taak = worker.submit(availability.refresh_if_due, factory, settings, app.state.vault())
        tijdig = taak.result(timeout=1.4)
    assert tijdig is None and fake_nas.calls == bron
    assert vorige_meting() == [("onbekend", None)] * 2


def test_onbeschrijfbare_meetstart_weigert_vorige_pins(
    vorige_meting: Any, app: Any, settings: Any, fake_nas: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    factory, vault = app.state.sessionmaker, app.state.vault()
    versies = fake_nas.data["catalog.get_app_details"]["stable"]["ix-app"]["versions"]
    versies["1.4.7"] = {"version": "1.4.7"}
    bron = list(fake_nas.calls)
    with monkeypatch.context() as grens, factory.begin() as onderhoud:
        grens.setattr(availability, "MEASUREMENT_TIMEOUT", 1.0)
        onderhoud.execute(text("LOCK TABLE catalog_attempt IN SHARE MODE"))
        availability.refresh_if_due(factory, settings, vault)
        tijdens = vorige_meting()
    factory.kw["bind"].dispose()
    assert tijdens == vorige_meting() == [("onbekend", None)] * 2
    assert fake_nas.calls == bron
    with monkeypatch.context() as klok:
        klok.setattr(availability, "utcnow", lambda: datetime.now(UTC) + timedelta(seconds=301))
        availability.refresh_if_due(factory, settings, vault)
        assert all(staat == "ja" and tijd is not None for staat, tijd in vorige_meting())
    assert not fake_nas.mutations


def test_onbereikbaar_startbewijs_trekt_de_momentopname_in(
    vorige_meting: Any, app: Any, settings: Any, fake_nas: Any
) -> None:
    from hub.catalog import availability

    bewijs = settings.data_dir / availability.MEASUREMENT_RECEIPT
    bewaard = bewijs.rename(bewijs.with_suffix(".bewaard"))
    bron = list(fake_nas.calls)
    assert vorige_meting() == [("onbekend", None)] * 2
    try:
        bewijs.mkdir()
        availability.refresh_if_due(app.state.sessionmaker, settings, app.state.vault())
    finally:
        bewijs.rmdir()
        bewaard.rename(bewijs)
    assert vorige_meting() == [("onbekend", None)] * 2
    assert fake_nas.calls == bron and not fake_nas.mutations


def test_klokcorrectie_laat_geen_tweede_worker_meten(
    admin: Any, app: Any, fake_nas: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.catalog import availability

    connect(admin, fake_nas)
    gelezen, hervat = Event(), Event()
    call = availability.TrueNASClient.call

    async def wacht_na_index(client: Any, method: str, params: Any = None) -> Any:
        result = await call(client, method, params)
        if method == "catalog.apps":
            gelezen.set()
            assert await asyncio.to_thread(hervat.wait, 12)
        return result

    monkeypatch.setattr(availability.TrueNASClient, "call", wacht_na_index)
    tweede_worker = """
import sys
from datetime import UTC, datetime, timedelta
from hub.app import create_app
from hub.catalog import availability
from hub.config import Settings

settings = Settings.model_validate_json(sys.stdin.read())
app = create_app(settings)
availability.utcnow = lambda: datetime.now(UTC) + timedelta(seconds=301)
availability.refresh_if_due(app.state.sessionmaker, settings, app.state.vault())
"""
    with ThreadPoolExecutor(max_workers=1) as worker:
        eerste = worker.submit(availability.refresh_if_due, app.state.sessionmaker, settings, app.state.vault())
        try:
            assert gelezen.wait(5)
            subprocess.run(
                [sys.executable, "-c", tweede_worker],
                input=settings.model_dump_json(),
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
            )
        finally:
            hervat.set()
        eerste.result(timeout=5)
    assert sum(method == "catalog.apps" for method, _ in fake_nas.calls) == 1
    assert not fake_nas.mutations


def test_geweigerde_publicatie_herstelt_geen_vorige_nee(
    vorige_meting: Any, app: Any, settings: Any, fake_nas: Any
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability

    factory = app.state.sessionmaker
    with factory.begin() as db:
        db.execute(
            text("""CREATE FUNCTION weiger_voorraad() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'meetvoorraad niet beschikbaar' USING ERRCODE = '57014'; END $$""")
        )
        db.execute(
            text("""CREATE TRIGGER weiger_voorraad BEFORE UPDATE ON catalog_snapshot
            FOR EACH ROW EXECUTE FUNCTION weiger_voorraad()""")
        )
    try:
        availability.refresh_if_due(factory, settings, app.state.vault())
        factory.kw["bind"].dispose()
        assert vorige_meting() == [("onbekend", None)] * 2
        assert not fake_nas.mutations
    finally:
        with factory.begin() as db:
            db.execute(text("DROP TRIGGER weiger_voorraad ON catalog_snapshot"))
            db.execute(text("DROP FUNCTION weiger_voorraad()"))


def test_afgeronde_meting_laat_geen_sessieslot_achter(admin: Any, app: Any, settings: Any, fake_nas: Any) -> None:
    from contextlib import ExitStack

    from sqlalchemy import text

    from hub.catalog import availability
    from hub.db import make_engine, make_sessionmaker

    connect(admin, fake_nas)
    headers = _headers(admin)
    engine = make_engine(settings.database_url)
    try:
        with ExitStack() as stack:
            for _ in range(3):
                stack.enter_context(engine.connect())
        availability.refresh_if_due(make_sessionmaker(engine), settings, app.state.vault())
        with engine.connect() as lezer:
            assert (
                lezer.scalar(
                    text("""SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND granted
                AND database=(SELECT oid FROM pg_database WHERE datname=current_database())""")
                )
                == 0
            )
        for versie, verwacht in ((PIN["version"], "ja"), ("1.4.7", "nee")):
            r = admin.get(PATH, params={**PIN, "version": versie}, headers=headers)
            assert r.json()["beschikbaar"] == verwacht and r.json()["gemeten_op"]
    finally:
        engine.dispose()


def test_geblokkeerde_rij_laat_geen_wachtende_verbinding_achter(
    vorige_meting: Any, app: Any, settings: Any, fake_nas: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import text

    from hub.catalog import availability
    from hub.db import make_engine, make_sessionmaker

    engine = make_engine(settings.database_url)
    monkeypatch.setattr(availability, "MEASUREMENT_TIMEOUT", 1.0)
    try:
        with app.state.sessionmaker.begin() as houder:
            houder.execute(text("SELECT id FROM catalog_snapshot WHERE id=1 FOR UPDATE"))
            availability.refresh_if_due(make_sessionmaker(engine), settings, app.state.vault())
            assert engine.pool.checkedout() == 0
            assert not houder.scalar(
                text("""SELECT EXISTS (SELECT FROM pg_stat_activity
                WHERE datname = current_database() AND pg_backend_pid() = ANY(pg_blocking_pids(pid)))""")
            )
            assert vorige_meting() == [("onbekend", None)] * 2
        assert not fake_nas.mutations
    finally:
        engine.dispose()


def test_lezer_toetst_commit_en_verlopen_poging_na_herstart(
    vorige_meting: Any, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sqlalchemy import select

    from hub.catalog import availability
    from hub.models import CatalogAttempt

    factory = app.state.sessionmaker
    geldig = vorige_meting()
    onbekend = [("onbekend", None)] * 2
    with factory.begin() as db:
        afgerond = db.scalars(select(CatalogAttempt)).one()
        assert afgerond.completed_at is not None
        # De inhoud blijft leesbaar en vers. Alleen het opgeslagen commitbewijs is te laat.
        afgerond.completed_at = afgerond.started_at + timedelta(seconds=15, microseconds=1)
        begin = afgerond.started_at
    factory.kw["bind"].dispose()
    assert vorige_meting() == onbekend
    with factory.begin() as db:
        db.get(CatalogAttempt, afgerond.id).completed_at = begin + timedelta(seconds=15)
        nieuwe_start = begin + timedelta(seconds=300)
        db.add(CatalogAttempt(started_at=nieuwe_start))
    nu = nieuwe_start + timedelta(seconds=15)
    monkeypatch.setattr(availability, "utcnow", lambda: nu)
    assert vorige_meting() == geldig
    nu += timedelta(microseconds=1)
    assert vorige_meting() == onbekend


def test_oude_sessiemarkering_heeft_geen_invloed_op_pins(vorige_meting: Any, pg_url: str) -> None:
    import psycopg
    from sqlalchemy.engine import make_url

    geldig = vorige_meting()
    # De oude markering in een tweede database op hetzelfde lokale testcluster.
    andere_db = make_url(pg_url).set(database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(andere_db) as andere:
        andere.execute("SELECT pg_advisory_xact_lock(%s)", (0x41534D4D34,))
        assert vorige_meting() == geldig
