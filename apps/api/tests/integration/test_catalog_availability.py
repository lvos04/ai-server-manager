"""M3 tegen de echte Hub en de lokale TrueNAS-WebSocket-simulator."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
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


def test_meting_versheid_en_geen_bronaanroepen_per_leesverzoek(
    admin: Any, fake_nas: Any, worker_once: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.catalog import availability

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
    assert read(train="community")["beschikbaar"] == "nee"
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
