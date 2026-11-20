"""Beheer, kluis en contact van koppelingen tegen lokale testgegevens."""

import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from ipaddress import IPv4Address
from typing import Any
from unittest.mock import Mock

import pytest
from conftest import idem, login_as, make_user
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from hub import migrations, outbound
from hub.adapters import basis, my_house
from hub.catalog.discovery import discover, is_inventory_fresh
from hub.config import Settings
from hub.deps import get_db
from hub.incidents.rules import ADAPTER_HEALTH_FAILED, ADAPTER_HEALTH_RECOVERED
from hub.inventory.collector import CollectResult, KindResult
from hub.inventory.store import save_run
from hub.models import (
    AdapterHouseSnapshot,
    AdapterLink,
    AuditEvent,
    CatalogApp,
    Decision,
    HealthObservation,
    IdempotencyRecord,
    Incident,
    IncidentEvent,
    OutboxEvent,
    VaultSecret,
    WebSession,
)
from hub.monitoring import kuma, timeseries
from hub.monitoring.sources import upsert_observation
from hub.routers import adapterkoppelingen, catalog
from hub.timeutil import iso, utcnow
from hub.truenas import normalize
from hub.truenas.connection import current_target
from hub.vault import Vault, VaultError

ROUTE = "/api/v1/adapterkoppelingen"
APP_ID = "mediaguard"
ANDERE_APP_ID = "media-source-optimizer"
URL = "https://adapter.example"
TWEEDE_BASIS = f"{URL}:8443"
PEER = str(IPv4Address(bytes((192, 0, 2, 1))))


def _bewaar_apps(db: Session, apps: dict[str, tuple[int, ...]]) -> None:
    nas = current_target(db)
    assert nas is not None
    data = normalize.apps(
        [
            {
                "name": app_id,
                "state": "RUNNING",
                "portals": {f"Web {port}": f"{URL}:{port}/" for port in ports},
                "active_workloads": {
                    "used_ports": [
                        {"protocol": "tcp", "host_ports": [{"host_port": port, "host_ip": PEER}]} for port in ports
                    ],
                },
            }
            for app_id, ports in apps.items()
        ]
    )
    meting = KindResult("apps", "ok", None, "", "app.query", data, utcnow())
    save_run(db, CollectResult("ok", None, nas.url, kinds=[meting]), trigger="test")


@pytest.fixture
def doel(
    app: Any, settings: Settings, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> dict[str, Any]:
    app_id = getattr(request, "param", APP_ID)
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({PEER}))
    with app.state.sessionmaker.begin() as db:
        besluit = db.get(Decision, "D03")
        assert besluit is not None
        besluit.status = "Ingevuld"
        besluit.waarde = {"nas_adres": "adapter.example"}
        _bewaar_apps(db, {app_id: (443, 8443)})
        assert discover(db, settings).nieuw == 1
        row = db.scalars(select(CatalogApp)).one()
        assert row.app_id == app_id
        return {"app_id": app_id, "catalog_app_id": str(row.id), "basis_url": URL, "doel_bevestigd": True}


def invoer(waarde: str) -> dict[str, str]:
    return {**idem(), "X-Adapter-Credential": waarde}


def test_beheer_kluis_replay_redactie_en_ontkoppelen(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    waarde = secrets.token_urlsafe()
    headers = invoer(waarde)
    response = admin.post(ROUTE, json=doel, headers=headers)
    assert response.status_code == 201, response.json()
    receipt = response.json()
    path = f"{ROUTE}/{receipt['id']}"
    detail = admin.get(path)
    assert detail.status_code == 200
    data = detail.json()
    assert data["laatste4"] == waarde[-4:]
    assert data["ingevoerd_op"]
    assert waarde not in detail.text
    assert "geheim_ref" not in data
    assert response.headers["ETag"]
    replay = admin.post(ROUTE, json=doel, headers=headers)
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == receipt

    make_user(admin, "lezer", "viewer")
    viewer = login_as(app, "lezer")
    assert viewer.get(path).status_code == 200
    assert viewer.get(ROUTE).json()["items"] == [data]
    assert viewer.post(ROUTE, json=doel, headers=invoer(waarde)).status_code == 403
    assert viewer.patch(path, json={}, headers=idem()).status_code == 403
    assert viewer.post(f"{path}/test", headers=idem()).status_code == 403
    assert viewer.delete(path, headers=idem()).status_code == 403
    invalid = admin.post(ROUTE, json={**doel, "credential": waarde}, headers=idem())
    assert invalid.status_code == 422
    assert waarde not in invalid.text

    probe = Mock(side_effect=AssertionError("MediaGuard heeft een verzoek ontvangen."))
    monkeypatch.setattr(outbound, "request", probe)
    getest = admin.post(f"{path}/test", headers=idem())
    assert getest.status_code == 200
    contact = admin.get(path)
    assert contact.json()["verbinding"]["status"] == "unknown"
    assert contact.json()["verbinding"]["reason_code"] == "geen_alleen_lezen_bron"
    assert contact.json()["gezondheid"]["status"] == "unknown"
    assert waarde not in contact.text

    with app.state.sessionmaker() as db:
        opgeslagen = db.scalar(select(AdapterLink))
        assert opgeslagen is not None
        ref = opgeslagen.geheim_ref
        kluis = db.scalar(select(VaultSecret).where(VaultSecret.ref == ref))
        assert kluis and waarde.encode() not in kluis.ciphertext
        assert waarde not in json.dumps(list(db.scalars(select(AuditEvent.details))))
        rec = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(headers["Idempotency-Key"])))
        assert rec
        canonical = json.dumps(doel, sort_keys=True, separators=(",", ":"))
        assert rec.request_hash == hashlib.sha256(f"{ROUTE}\n{canonical}".encode()).hexdigest()
        assert rec.response_body == receipt
        assert opgeslagen.observed_at is None
        assert opgeslagen.laatste_status is None
        opgeslagen.observed_at = utcnow() - timedelta(seconds=901)
        opgeslagen.laatste_status = "healthy"
        db.commit()
    assert waarde not in caplog.text
    verouderd = admin.get(path).json()["verbinding"]
    assert verouderd["status"] == "unknown"
    assert verouderd["reason_code"] == "geen_alleen_lezen_bron"
    assert verouderd["laatste_status"] == "healthy"
    assert verouderd["observed_at"] is not None

    assert admin.delete(path, headers=idem()).status_code == 200
    assert admin.get(path).status_code == 404
    probe.assert_not_called()
    with app.state.sessionmaker() as db:
        assert db.scalar(select(AdapterLink)) is None
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref == ref)) is None
        for recorded in db.scalars(select(IdempotencyRecord).where(IdempotencyRecord.scope.contains(ROUTE))):
            assert set(recorded.response_body) in ({"id", "version"}, {"verwijderd"})


@pytest.mark.parametrize("adres", ["localhost", str(IPv4Address(bytes((169, 254, 169, 254))))])
def test_verboden_basisadres(admin: Any, doel: dict[str, Any], adres: str) -> None:
    response = admin.post(
        ROUTE, json={**doel, "basis_url": f"https://{adres}"}, headers=invoer(secrets.token_urlsafe())
    )
    assert response.status_code == 422
    assert response.json()["details"]["reason"] == "adres_niet_toegestaan"


def test_strijdige_catalogusbestemming(
    admin: Any, app: Any, settings: Settings, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.sessionmaker.begin() as db:
        _bewaar_apps(db, {APP_ID: (443, 8443), ANDERE_APP_ID: (9443,)})
        assert discover(db, settings).nieuw == 1
    transport = Mock()
    monkeypatch.setattr(outbound, "request", transport)
    for bestemming in (f"{URL}:9443", f"{URL}/andere-app", "https://andere-instantie.example"):
        response = admin.post(ROUTE, json={**doel, "basis_url": bestemming}, headers=invoer(secrets.token_urlsafe()))
        assert response.status_code == 409
        assert response.json()["details"]["reason"] == "doelbinding"
    transport.assert_not_called()
    with app.state.sessionmaker() as db:
        assert db.scalar(select(AdapterLink)) is None
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None


def test_binding_volgt_de_laatst_vastgelegde_poorteigenaar(
    admin: Any, app: Any, settings: Settings, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = Mock(side_effect=AssertionError("Deze proef gebruikt geen netwerktransport"))
    monkeypatch.setattr(outbound, "request", transport)
    waarde = secrets.token_urlsafe()
    aangemaakt = admin.post(ROUTE, json=doel, headers=invoer(waarde))
    assert aangemaakt.status_code == 201
    pad = f"{ROUTE}/{aangemaakt.json()['id']}"
    assert admin.post(f"{pad}/test", headers=idem()).status_code == 200
    versie = admin.get(pad).json()["version"]

    with app.state.sessionmaker.begin() as db:
        _bewaar_apps(db, {ANDERE_APP_ID: (443,)})
    with app.state.sessionmaker() as db:
        inventaris = is_inventory_fresh(db, settings)
        assert inventaris["status"] == "ok"
        (eigenaar,) = inventaris["data"]
        assert eigenaar["runtime_id"] == ANDERE_APP_ID
        assert eigenaar["poorten"][0]["host_poort"] == 443
        assert db.scalars(select(CatalogApp)).one().aanwezig

    # De inventaris is vastgelegd. De catalogus bevat nog de vorige poorteigenaar.
    geweigerd = [
        admin.post(f"{pad}/test", headers=idem()),
        admin.patch(pad, json={"doel_bevestigd": True}, headers=invoer(secrets.token_urlsafe())),
        admin.patch(pad, json={}, headers=invoer(secrets.token_urlsafe())),
    ]
    for antwoord in geweigerd:
        assert antwoord.status_code == 409
        assert antwoord.json()["details"]["reason"] == "doelbinding"
    with app.state.sessionmaker() as db:
        link = db.scalars(select(AdapterLink)).one()
        assert link.version == versie
        assert app.state.vault().get(db, link.geheim_ref) == waarde

    assert admin.delete(pad, headers=idem()).status_code == 200
    achterhaalde_koppeling = admin.post(ROUTE, json=doel, headers=invoer(secrets.token_urlsafe()))
    assert achterhaalde_koppeling.status_code == 409
    assert achterhaalde_koppeling.json()["details"]["reason"] == "doelbinding"
    with app.state.sessionmaker.begin() as db:
        assert db.scalar(select(AdapterLink)) is None
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None
        resultaat = discover(db, settings)
        assert resultaat.nieuw == 1 and resultaat.verdwenen == 1
        opvolger = db.scalars(select(CatalogApp).where(CatalogApp.app_id == ANDERE_APP_ID)).one()
        nieuw_doel = {**doel, "app_id": ANDERE_APP_ID, "catalog_app_id": str(opvolger.id)}
    assert admin.post(ROUTE, json=doel, headers=invoer(secrets.token_urlsafe())).status_code == 409
    assert admin.post(ROUTE, json=nieuw_doel, headers=idem()).status_code == 201
    transport.assert_not_called()


def test_herbevestiging_en_wijziging_van_de_catalogusinstantie(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = invoer(secrets.token_urlsafe())
    assert admin.post(ROUTE, json={**doel, "app_id": "my_house"}, headers=headers).status_code == 409
    created = admin.post(ROUTE, json=doel, headers=headers)
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    probe = Mock(side_effect=AssertionError("MediaGuard heeft een verzoek ontvangen."))
    monkeypatch.setattr(outbound, "request", probe)
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    detail = admin.get(path).json()
    assert detail["verbinding"]["status"] == "unknown"
    assert detail["verbinding"]["reason_code"] == "geen_alleen_lezen_bron"
    ander = {"basis_url": TWEEDE_BASIS, "doel_bevestigd": True}
    assert admin.patch(path, json=ander, headers=idem()).status_code == 422
    afwijkend = {**ander, "basis_url": f"{URL}:9443"}
    geweigerd = admin.patch(path, json=afwijkend, headers=invoer(secrets.token_urlsafe()))
    assert geweigerd.status_code == 409
    assert geweigerd.json()["details"]["reason"] == "doelbinding"
    assert admin.get(path).json() == detail
    with app.state.sessionmaker() as db:
        link = db.scalar(select(AdapterLink))
        assert link is not None
        assert app.state.vault().get(db, link.geheim_ref) == headers["X-Adapter-Credential"]
    updated = admin.patch(path, json=ander, headers=invoer(secrets.token_urlsafe()))
    assert updated.status_code == 200
    assert admin.get(path).json()["basis_url"] == ander["basis_url"]
    with app.state.sessionmaker() as db:
        instance = db.scalar(select(CatalogApp))
        assert instance
        instance.app_id = "my_house"
        db.commit()
    assert admin.post(f"{path}/test", headers=idem()).status_code == 409
    probe.assert_not_called()


@pytest.mark.parametrize(
    "wijziging",
    [
        {"aanwezig": False},
        {"poorten": []},
        {"poorten": [{"protocol": "tcp", "host_poort": 443, "host_ip": str(IPv4Address(bytes((192, 0, 2, 2))))}]},
    ],
    ids=["afwezig", "poort-verdwenen", "ander-netwerkadres"],
)
def test_weggevallen_binding_blokkeert_contact_en_toont_laatst_bekende_meting(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch, wijziging: dict[str, Any]
) -> None:
    created = admin.post(ROUTE, json=doel, headers=invoer(secrets.token_urlsafe()))
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    probe = Mock(side_effect=AssertionError("MediaGuard heeft een verzoek ontvangen."))
    monkeypatch.setattr(outbound, "request", probe)

    with app.state.sessionmaker.begin() as db:
        link = db.scalars(select(AdapterLink)).one()
        link.observed_at = utcnow()
        link.laatste_status = "healthy"
    meting = admin.get(path).json()["verbinding"]
    assert meting["status"] == "unknown"
    assert meting["laatste_status"] == "healthy"

    with app.state.sessionmaker.begin() as db:
        instance = db.get(CatalogApp, uuid.UUID(doel["catalog_app_id"]))
        assert instance is not None
        for veld, waarde in wijziging.items():
            setattr(instance, veld, waarde)

    status = {
        "status": "unknown",
        "reason_code": "doelbinding",
        "observed_at": meting["observed_at"],
        "laatste_status": "healthy",
    }
    assert admin.get(path).json()["verbinding"] == status
    assert admin.get(ROUTE).json()["items"][0]["verbinding"] == status
    geweigerd = admin.post(f"{path}/test", headers=idem())
    assert geweigerd.status_code == 409
    assert geweigerd.json()["details"]["reason"] == "doelbinding"
    assert admin.patch(path, json={}, headers=invoer(secrets.token_urlsafe())).status_code == 409
    probe.assert_not_called()


def test_mediaguard_toont_alle_metingen_als_onbekend_zonder_bronverkeer(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = Mock(side_effect=AssertionError("MediaGuard heeft een verzoek ontvangen."))
    monkeypatch.setattr(outbound, "request", transport)
    gemaakt = admin.post(ROUTE, json=doel, headers=invoer(secrets.token_urlsafe()))
    assert gemaakt.status_code == 201
    pad = f"{ROUTE}/{gemaakt.json()['id']}"
    headers = idem()
    getest = admin.post(f"{pad}/test", headers=headers)
    assert getest.status_code == 200
    assert set(getest.json()) == {"id", "version"}
    assert admin.post(f"{pad}/test", headers=headers).json() == getest.json()

    detail = admin.get(pad).json()
    assert admin.get(ROUTE).json()["items"] == [detail]
    assert detail["verbinding"]["observed_at"] is None
    assert detail["gezondheid"]["status"] == "unknown"
    onbekend = {
        "status": "unknown",
        "observed_at": None,
        "reason_code": "geen_alleen_lezen_bron",
        "reason": "geen alleen-lezen bron",
    }
    assert detail["mediaguard"] == dict.fromkeys(
        ("wanted", "status", "downloads", "av1", "incidenten", "mediaservers", "noodstop", "opslagprognose", "backups"),
        onbekend,
    )
    assert admin.delete(pad, headers=idem()).status_code == 200
    assert admin.get(pad).status_code == 404
    transport.assert_not_called()
    with app.state.sessionmaker() as db:
        assert db.scalar(select(AdapterLink)) is None
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_koppelcode_wordt_zonder_server_id_geweigerd(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = Mock(side_effect=AssertionError("Geen transport zonder bevestigde server-ID."))
    monkeypatch.setattr(outbound, "request", transport)
    waarde = secrets.token_urlsafe()
    response = admin.post(ROUTE, json=doel, headers=invoer(waarde))
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert waarde not in response.text
    transport.assert_not_called()
    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None


def test_downgrade_wist_alleen_adapteropslag(admin: Any, app: Any, doel: dict[str, Any], settings: Any) -> None:
    from sqlalchemy import inspect

    from hub.vault import make_ref

    created = admin.post(ROUTE, json=doel, headers=invoer(secrets.token_urlsafe()))
    assert created.status_code == 201
    other_ref = make_ref("monitoring", "testbron")
    other_value = secrets.token_urlsafe()
    vault = app.state.vault()
    with app.state.sessionmaker() as db:
        link = db.scalar(select(AdapterLink))
        assert link
        link_ref = link.geheim_ref
        vault.put(db, other_ref, other_value, actor="test")
        db.commit()

    try:
        migrations.downgrade(settings.database_url, "0016")
        assert "adapter_link" not in inspect(app.state.engine).get_table_names()
        with app.state.sessionmaker() as db:
            assert db.get(CatalogApp, uuid.UUID(doel["catalog_app_id"]))
            assert vault.get(db, other_ref) == other_value
            assert vault.get(db, link_ref) is None
    finally:
        migrations.upgrade(settings.database_url)
    assert "adapter_link" in inspect(app.state.engine).get_table_names()


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_mso_openbare_probes(admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    buiten_witte_lijst = secrets.token_urlsafe()
    responses = {
        "/healthz": {"status": "ok", "version": "1.6.0", "extra": buiten_witte_lijst},
        "/api/v1/setup/status": {
            "setup_required": False,
            "completed": True,
            "version": "1.6.0",
            "admin_exists": True,
            "connectors": {"voorbeeld": {"configured": True, "status": "auth_failed", "url": buiten_witte_lijst}},
        },
    }

    def fake_mso(base: str, method: str, path: str, **options: Any) -> outbound.Response:
        assert base == URL
        assert method == "GET"
        assert set(options) == {"policy", "max_bytes"}
        assert options["policy"].allowed_peer_addresses == frozenset({PEER})
        assert not options["policy"].allow_loopback
        assert options["max_bytes"] == basis.MAX_RESPONSE_BYTES
        return outbound.Response(200, json.dumps(responses[path]).encode())

    transport = Mock(side_effect=fake_mso)
    monkeypatch.setattr(outbound, "request", transport)
    created = admin.post(ROUTE, json=doel, headers=idem())
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    headers = idem()
    tested = admin.post(f"{path}/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["probes"] == {
        "healthz": {"status": "ok", "version": "1.6.0"},
        "setup": {"setup_required": False, "completed": True, "version": "1.6.0"},
    }
    replay = admin.post(f"{path}/test", headers=headers)
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == tested.json()
    assert [call.args[2] for call in transport.call_args_list] == list(responses)
    detail = admin.get(path).json()
    assert detail["verbinding"]["status"] == "healthy"
    assert detail["gezondheid"]["status"] == "unknown"
    assert detail["gezondheid"]["reason_code"] == "capability_unavailable"
    assert "mediaguard" not in detail
    assert detail["laatste4"] == ""
    assert detail["ingevoerd_op"] is None

    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None
        assert buiten_witte_lijst not in json.dumps(list(db.scalars(select(IdempotencyRecord.response_body))))
        _bewaar_apps(db, {APP_ID: (443,)})
        db.commit()
    assert admin.post(f"{path}/test", headers=idem()).status_code == 409
    assert transport.call_count == 2


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_timeout_na_succes_toont_laatst_bekende_contactmeting(
    admin: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = Mock(
        side_effect=[
            outbound.Response(200, b'{"status":"ok","version":"1.6.0"}'),
            outbound.Response(200, b'{"setup_required":false,"completed":true,"version":"1.6.0"}'),
            outbound.OutboundError("tijdslimiet"),
            outbound.OutboundError("tijdslimiet"),
        ]
    )
    monkeypatch.setattr(outbound, "request", transport)
    gemaakt = admin.post(ROUTE, json=doel, headers=idem())
    assert gemaakt.status_code == 201
    pad = f"{ROUTE}/{gemaakt.json()['id']}"
    assert admin.post(f"{pad}/test", headers=idem()).status_code == 200
    bekend = admin.get(pad).json()["verbinding"]
    assert bekend["status"] == "healthy"
    assert bekend["observed_at"] is not None

    assert admin.post(f"{pad}/test", headers=idem()).status_code == 200
    detail = admin.get(pad).json()
    assert detail["verbinding"] == {
        "status": "unknown",
        "reason_code": "tijdslimiet",
        "observed_at": bekend["observed_at"],
        "laatste_status": "healthy",
    }
    assert admin.get(ROUTE).json()["items"] == [detail]


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_poorteigenaar_per_probe(admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    created = admin.post(ROUTE, json=doel, headers=idem())
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"

    def wissel_poorteigenaar(_base: str, method: str, probe_path: str, **_options: Any) -> outbound.Response:
        assert method == "GET"
        if probe_path == "/healthz":
            with app.state.sessionmaker.begin() as db:
                _bewaar_apps(db, {APP_ID: (443,)})
            return outbound.Response(200, b'{"status":"ok","version":"1.6.0"}')
        raise outbound.OutboundError("doelbinding")

    transport = Mock(side_effect=wissel_poorteigenaar)
    monkeypatch.setattr(outbound, "request", transport)
    tested = admin.post(f"{path}/test", headers=idem())
    assert [call.args[2] for call in transport.call_args_list] == ["/healthz"]
    assert tested.status_code == 409
    assert tested.json()["details"]["reason"] == "doelbinding"
    detail = admin.get(path).json()
    assert detail["verbinding"]["status"] == "unknown"
    assert detail["verbinding"]["reason_code"] == "doelbinding"


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_herstelsignaal_vereist_eerdere_storing(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    created = admin.post(ROUTE, json=doel, headers=idem())
    assert created.status_code == 201
    link_id = created.json()["id"]
    path = f"{ROUTE}/{link_id}"
    healthz = outbound.Response(200, b'{"status":"ok","version":"1.6.0"}')
    setup = outbound.Response(200, b'{"setup_required":false,"completed":true,"version":"1.6.0"}')
    geweigerd = outbound.Response(403, b'{"code":"forbidden"}')
    antwoorden = [healthz, setup] * 2 + [healthz, geweigerd] + [healthz, setup] * 2
    monkeypatch.setattr(outbound, "request", Mock(side_effect=antwoorden))

    for status in ("healthy", "healthy", "unknown", "healthy", "healthy"):
        assert admin.post(f"{path}/test", headers=idem()).status_code == 200
        assert admin.get(path).json()["verbinding"]["status"] == status

    with app.state.sessionmaker() as db:
        events = db.scalars(
            select(OutboxEvent.event_type)
            .where(OutboxEvent.entity_id == link_id, OutboxEvent.event_type.startswith("monitoring.mso_probe."))
            .order_by(OutboxEvent.seq)
        ).all()
    assert events == ["monitoring.mso_probe.failed", "monitoring.mso_probe.recovered"]


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_bevestigingsmelding_voor_mso(admin: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    transport = Mock(side_effect=AssertionError("Een wijziging hoort geen MSO-verzoek te sturen"))
    monkeypatch.setattr(outbound, "request", transport)
    created = admin.post(ROUTE, json=doel, headers=idem())
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    wijziging = {"basis_url": TWEEDE_BASIS}
    zonder = admin.patch(path, json=wijziging, headers=idem())
    assert zonder.status_code == 422
    assert zonder.json()["message"] == "Bevestig de nieuwe bestemming."
    bevestigd = {**wijziging, "doel_bevestigd": True}
    geweigerd = admin.patch(path, json=bevestigd, headers=invoer(secrets.token_urlsafe()))
    assert geweigerd.status_code == 422
    assert admin.patch(path, json=bevestigd, headers=idem()).status_code == 200
    transport.assert_not_called()


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_mso_weigert_credentials(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    transport = Mock(side_effect=AssertionError("Een koppelverzoek hoort geen MSO-verzoek te sturen"))
    monkeypatch.setattr(outbound, "request", transport)
    waarde = secrets.token_urlsafe()
    headers = idem()
    for response in (
        admin.post(ROUTE, json={**doel, "username": "voorbeeld", "password": waarde}, headers=headers),
        admin.post(ROUTE, json={**doel, "scopes": ["read"]}, headers=headers),
        admin.post(ROUTE, json=doel, headers={**headers, "X-Adapter-Credential": waarde}),
    ):
        assert response.status_code == 422
        assert waarde not in response.text
    created = admin.post(ROUTE, json=doel, headers=headers)
    assert created.status_code == 201
    assert admin.post(ROUTE, json=doel, headers={**headers, "X-Adapter-Credential": waarde}).status_code == 422
    path = f"{ROUTE}/{created.json()['id']}"
    keuze = {"doel_bevestigd": True}
    patch_headers = idem()
    assert admin.patch(path, json=keuze, headers=patch_headers).status_code == 200
    geweigerd = admin.patch(path, json=keuze, headers={**patch_headers, "X-Adapter-Credential": waarde})
    assert geweigerd.status_code == 422
    assert waarde not in geweigerd.text
    transport.assert_not_called()
    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None
        assert waarde not in json.dumps(list(db.scalars(select(AuditEvent.details))))
    assert waarde not in caplog.text


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_mso_probeweigering_maakt_geschoond_incident(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch, periodic_run: Any, caplog: Any
) -> None:
    brontekst = secrets.token_urlsafe()
    correlation_id = uuid.uuid4().hex[:12]
    responses = [
        outbound.Response(200, b'{"status":"ok","version":"1.6.0"}'),
        outbound.Response(
            403, json.dumps({"detail": brontekst, "code": "forbidden", "correlation_id": correlation_id}).encode()
        ),
    ]
    monkeypatch.setattr(outbound, "request", Mock(side_effect=responses))
    created = admin.post(ROUTE, json=doel, headers=idem())
    path = f"{ROUTE}/{created.json()['id']}"
    tested = admin.post(f"{path}/test", headers=idem())
    assert tested.status_code == 200
    assert tested.json()["probes"]["setup"] is None
    detail = admin.get(path).json()
    assert detail["verbinding"]["status"] == "unknown"
    assert detail["verbinding"]["reason_code"] == "bron_credential_geweigerd"
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        incident = db.scalars(select(Incident).where(Incident.onderwerp_id == created.json()["id"])).one()
        assert incident.correlatie_ids == [correlation_id]
        assert brontekst not in json.dumps(list(db.scalars(select(OutboxEvent.payload))))
    assert brontekst not in tested.text
    assert brontekst not in caplog.text


@pytest.mark.parametrize("doel", [ANDERE_APP_ID], indirect=True)
def test_mso_oude_kluiswaarde_is_overbodig(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    created = admin.post(ROUTE, json=doel, headers=idem())
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    with app.state.sessionmaker.begin() as db:
        link = db.scalars(select(AdapterLink)).one()
        ref = link.geheim_ref
        meta = app.state.vault().put(db, ref, secrets.token_urlsafe(), actor="system:test")
        link.laatste4, link.ingevoerd_op = meta.last4, meta.updated_at

    read_secret = Mock(side_effect=AssertionError("Een openbare probe leest de kluis niet"))
    monkeypatch.setattr("hub.vault.Vault.get", read_secret)
    transport = Mock(
        side_effect=[
            outbound.Response(200, b'{"status":"ok","version":"1.6.0"}'),
            outbound.Response(200, b'{"setup_required":false,"completed":true,"version":"1.6.0"}'),
        ]
    )
    monkeypatch.setattr(outbound, "request", transport)
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    assert admin.get(path).json()["verbinding"]["status"] == "healthy"
    assert admin.get(path).json()["laatste4"] == ""
    read_secret.assert_not_called()
    assert admin.patch(path, json={"doel_bevestigd": True}, headers=idem()).status_code == 200
    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref == ref)) is None


@pytest.fixture
def huis_simulatie(
    doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> tuple[str, dict[str, Any], list[tuple[str, str]]]:
    from hmac import digest

    doel["server_id"], client_id, home_id = (str(uuid.uuid4()) for _ in range(3))
    zone_id, integration_id = (str(uuid.uuid4()) for _ in range(2))
    tekens = [secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8)]
    code = "".join(tekens[:4]) + "-" + "".join(tekens[4:])
    toestand: dict[str, Any] = {
        "token": "shc_" + secrets.token_urlsafe(32),
        "rol": "viewer",
        "purpose": "hub",
        "status": 200,
        "server_id": doel["server_id"],
        "renew_status": 200,
        "worker": {"key": "worker", "state": "ok", "age_s": 0},
        "extra_check": [],
    }
    calls: list[tuple[str, str]] = []

    def transport(base: str, method: str, path: str, **options: Any) -> outbound.Response:
        assert base == URL
        assert options["policy"].allowed_peer_addresses == frozenset({PEER})
        calls.append((method, path))
        headers = options.get("headers") or {}
        status = 200
        if path == "/api/v1/pairing/identity":
            assert "Authorization" not in headers
            body: Any = {"server_id": toestand["server_id"]}
            query = options.get("query")
            if query:
                assert query["client_id"] == client_id
                message = f"shc-identity-v1\n{toestand['server_id']}\n{query['nonce']}"
                key = hashlib.sha256(toestand["token"].encode()).hexdigest()
                body.update(proof_alg="hmac-sha256-v1", proof=digest(key.encode(), message.encode(), "sha256").hex())
        elif path == "/api/v1/pairing/redeem":
            assert method == "POST" and not headers
            assert options["json_body"] == {"code": toestand.get("code", code), "device_name": "Hub"}
            body = {
                "token": toestand["token"],
                "client": {
                    "id": client_id,
                    "role": toestand["rol"],
                    "purpose": toestand["purpose"],
                    "expires_at": (utcnow() + timedelta(days=179)).isoformat(),
                    "revoked": False,
                    "expired": False,
                },
                "server": {"server_id": doel["server_id"], "lan_url": code},
                "user": {"name": code},
            }
        elif path == "/api/v1/health":
            assert method == "GET" and not headers
            body = {"status": "ok", "version": "1.0.0", "detail": code}
        else:
            assert headers == {"Authorization": f"Bearer {toestand['token']}"}
            if path == "/api/v1/clients/self/refresh":
                assert method == "POST"
                status = toestand["renew_status"]
                if status == 200:
                    toestand["token"] = "shc_" + secrets.token_urlsafe(32)
                body = {"token": toestand["token"], "expires_at": (utcnow() + timedelta(days=180)).isoformat()}
            else:
                assert method == "GET"
                status = toestand["status"]
                body = {
                    "/api/v1/system/status": {
                        "version": "1.0.0",
                        "checks": [
                            {"key": "database", "state": "ok", "detail": code},
                            toestand["worker"],
                            *(
                                [{"key": f"integration:{integration_id}", **toestand["extra_check"]}]
                                if toestand["extra_check"]
                                else []
                            ),
                            *toestand.get("extra_checks", []),
                        ],
                    },
                    "/api/v1/homes": [
                        {"id": home_id, "name": "Proefwoning", "timezone": "Europe/Amsterdam", "active": True}
                    ],
                    f"/api/v1/homes/{home_id}/zones": [
                        {
                            "id": zone_id,
                            "name": code,
                            "unit_status": "not_linked",
                            "online": False,
                            "mode": "off",
                            "policy": {"stale_after_s": 420},
                            "target_c": 21,
                            "target_at": utcnow().isoformat(),
                            "temperature": {
                                "value": 18.5,
                                "unit": "°C",
                                "at": (utcnow() - timedelta(hours=1)).isoformat(),
                                "quality": "measured",
                                "stale": False,
                                "detail": toestand["token"],
                            },
                            "humidity": {
                                "value": 42.5,
                                "unit": "%",
                                "at": utcnow().isoformat(),
                                "quality": "measured",
                                "stale": False,
                            },
                        }
                    ],
                    f"/api/v1/homes/{home_id}/lights": {"groups": [], "scenes": [], "lights": []},
                    f"/api/v1/homes/{home_id}/alerts": [],
                    f"/api/v1/homes/{home_id}/devices": [],
                    "/api/v1/system/settings": {
                        "lan_url": "javascript:open()",
                        "remote_url": toestand.get("app_link"),
                        "safe_mode": False,
                        "maintenance": False,
                    },
                }[path]
        if status != 200:
            body = {"detail": {"code": "token_expired" if status == 401 else "unavailable", "message": code}}
        return outbound.Response(status, json.dumps(body).encode())

    monkeypatch.setattr(outbound, "request", transport)
    return code, toestand, calls


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize(("rol", "purpose"), [("admin", "hub"), ("control", "phone"), ("viewer", "phone")])
def test_my_house_weigert_onjuist_recht(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, rol: str, purpose: str
) -> None:
    code, toestand, calls = huis_simulatie
    toestand.update(rol=rol, purpose=purpose)
    denied = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert denied.status_code == 422
    assert denied.json()["details"]["reason"] == "bron_recht_ongeldig"
    with app.state.sessionmaker() as db:
        assert db.scalar(select(AdapterLink)) is None
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None
    assert calls == [("GET", "/api/v1/pairing/identity"), ("POST", "/api/v1/pairing/redeem")]


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_weigert_gewisselde_server(admin: Any, doel: dict[str, Any], huis_simulatie: Any) -> None:
    code, toestand, calls = huis_simulatie
    toestand["server_id"] = str(uuid.uuid4())
    denied = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert denied.status_code == 422
    assert calls == [("GET", "/api/v1/pairing/identity")]


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_projectie_en_verlopen_token(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, periodic_run: Any, caplog: Any
) -> None:
    code, toestand, _ = huis_simulatie
    headers = invoer(code)
    created = admin.post(ROUTE, json=doel, headers=headers)
    assert created.status_code == 201
    assert admin.post(ROUTE, json=doel, headers=headers).headers["Idempotent-Replay"] == "true"
    link_id = created.json()["id"]
    path = f"{ROUTE}/{link_id}"
    tested = admin.post(f"{path}/test", headers=idem())
    assert tested.status_code == 200
    data = tested.json()["my_house"]
    assert data["systeem"]["checks"] == [{"key": "database", "state": "ok"}, {"key": "worker", "state": "ok"}]
    instellingen = data["instellingen"]
    assert instellingen["observed_at"] is not None
    assert instellingen == {
        "link": None,
        "safe_mode": False,
        "maintenance": False,
        "observed_at": instellingen["observed_at"],
    }
    assert len(data["woningen"]) == 1
    assert data["woningen"][0]["meldingen"]["open"] == 0
    zone = data["woningen"][0]["zones"][0]
    assert zone["name"] is None
    assert zone["temperature"]["value"] is None and zone["temperature"]["stale"] is True
    assert zone["humidity"]["value"] == 42.5
    assert admin.get(path).json()["gezondheid"]["status"] == "healthy"

    toestand["extra_check"] = {"state": "error", "details": {"checked_at": utcnow().isoformat(), "text": code}}
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    assert admin.get(path).json()["gezondheid"]["status"] == "down"
    toestand["extra_check"]["details"]["checked_at"] = (utcnow() - timedelta(hours=1)).isoformat()
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    assert admin.get(path).json()["gezondheid"]["status"] == "unknown"

    toestand["status"] = 401
    failed = admin.post(f"{path}/test", headers=idem())
    assert failed.status_code == 200
    assert failed.json()["my_house"] is None
    health = admin.get(path).json()["gezondheid"]
    assert health["status"] == "unknown" and health["reason_code"] == "bron_token_verlopen"
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        incident = db.scalars(select(Incident).where(Incident.onderwerp_id == link_id)).one()
        event = db.scalars(select(IncidentEvent).where(IncidentEvent.incident_id == incident.id)).one()
        assert event.details["reason_code"] == "bron_token_verlopen"
        row = db.scalars(select(AdapterLink)).one()
        kluis = db.scalars(select(VaultSecret).where(VaultSecret.ref == row.geheim_ref)).one()
        assert toestand["token"].encode() not in kluis.ciphertext
        payloads = [
            *db.scalars(select(AuditEvent.details)),
            *db.scalars(select(OutboxEvent.payload)),
            *db.scalars(select(IdempotencyRecord.response_body)),
            *db.scalars(select(AdapterHouseSnapshot.measurement)),
        ]
    for geheim in (code, toestand["token"]):
        assert geheim not in tested.text and geheim not in failed.text
        assert geheim not in caplog.text and geheim not in json.dumps(payloads)


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_catalogus_leest_adaptergezondheid_en_incident_volgt_op_derde_meting(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, periodic_run: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, toestand, _ = huis_simulatie
    app_id = doel["catalog_app_id"]
    path = f"/api/v1/apps/{app_id}"

    health = admin.get(path).json()["gezondheid"]
    assert health["status"] == "unknown" and health["reason_code"] == "adapter_niet_gekoppeld"
    assert "Instellingen → Diensten" in health["melding"]

    response = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert response.status_code == 201
    link = f"{ROUTE}/{response.json()['id']}"
    assert admin.post(f"{link}/test", headers=idem()).status_code == 200

    with monkeypatch.context() as isolated:
        call = Mock(side_effect=AssertionError("De appcatalogus mag de adapterbron niet aanroepen."))
        isolated.setattr(outbound, "request", call)
        view = admin.get(path).json()["gezondheid"]
        assert view["status"] == "healthy"
        assert admin.get("/api/v1/apps").json()["items"][0]["gezondheid"]["status"] == "healthy"
        assert view["observed_at"] == admin.get(link).json()["gezondheid"]["observed_at"]
        call.assert_not_called()

    toestand["extra_check"] = {"state": "error", "details": {"checked_at": (utcnow() - timedelta(hours=1)).isoformat()}}
    first = idem()
    assert admin.post(f"{link}/test", headers=first).status_code == 200
    assert admin.post(f"{link}/test", headers=first).headers["Idempotent-Replay"] == "true"
    health = admin.get(path).json()["gezondheid"]
    assert (health["status"], health["reason_code"]) == ("unknown", "meting_verouderd")
    assert health["observed_at"] == admin.get(link).json()["gezondheid"]["observed_at"]

    def incidents() -> list[Incident]:
        periodic_run("incidenten_bijwerken")
        with app.state.sessionmaker() as db:
            return list(db.scalars(select(Incident).where(Incident.soort == "monitoring.adapter_health")))

    assert incidents() == []
    toestand["extra_check"]["details"]["checked_at"] = utcnow().isoformat()
    assert admin.post(f"{link}/test", headers=idem()).status_code == 200
    assert admin.get(path).json()["gezondheid"]["status"] == "down"
    assert incidents() == []
    assert admin.post(f"{link}/test", headers=idem()).status_code == 200
    [incident] = incidents()
    assert (incident.status, incident.onderwerp_id) == ("open", app_id)
    assert admin.post(f"{link}/test", headers=idem()).status_code == 200
    [incident] = incidents()
    assert incident.aantal == 1

    toestand["extra_check"] = None
    assert admin.post(f"{link}/test", headers=idem()).status_code == 200
    [incident] = incidents()
    assert incident.status == "opgelost"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_vernieuwing_door_worker(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, periodic_run: Any
) -> None:
    code, toestand, calls = huis_simulatie
    created = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    with app.state.sessionmaker.begin() as db:
        db.scalars(select(AdapterLink)).one().my_house_expires_at = utcnow() + timedelta(days=12)
    toestand["renew_status"] = 503
    periodic_run("my_house_vernieuwen")
    assert admin.get(path).json()["gezondheid"]["reason_code"] == "bron_vernieuwing_mislukt"
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        assert db.scalars(select(Incident).where(Incident.onderwerp_id == created.json()["id"])).one().status == "open"
    toestand["renew_status"] = 200
    oud = toestand["token"]
    periodic_run("my_house_vernieuwen")
    assert toestand["token"] != oud
    assert calls.count(("POST", "/api/v1/clients/self/refresh")) == 2
    assert admin.post(f"{path}/test", headers=idem()).json()["my_house"]["systeem"]["version"] == "1.0.0"
    assert admin.get(path).json()["laatste4"] == toestand["token"][-4:]
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        incident = db.scalars(select(Incident).where(Incident.onderwerp_id == created.json()["id"])).one()
        assert incident.status == "opgelost"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_downgrade_verwijdert_eigen_kluiswaarde(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, settings: Settings
) -> None:
    from hub.vault import make_ref

    code, _, _ = huis_simulatie
    response = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert response.status_code == 201
    ref = make_ref("adapters", f"my_house.{response.json()['id']}")
    vault = app.state.vault()
    other_ref = make_ref("monitoring", "andere-proef")
    other_value = secrets.token_urlsafe()
    with app.state.sessionmaker.begin() as db:
        vault.put(db, other_ref, other_value, actor="test")
        assert vault.get(db, ref) is not None
    try:
        migrations.downgrade(settings.database_url, "0018")
        with app.state.sessionmaker() as db:
            assert vault.get(db, ref) is None
            assert vault.get(db, other_ref) == other_value
            assert db.get(CatalogApp, uuid.UUID(doel["catalog_app_id"])) is not None
    finally:
        migrations.upgrade(settings.database_url)
    assert admin.get(f"{ROUTE}/{response.json()['id']}").status_code == 404


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize("terugrol", [None, "0019", "0018"])
def test_my_house_wist_metingen_en_behoudt_bevestigingen(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, settings: Settings, terugrol: str | None
) -> None:
    code, _, calls = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}"
    eerdere_sleutel, laatste_sleutel = idem(), idem()
    eerste = admin.post(f"{path}/test", headers=eerdere_sleutel)
    tweede = admin.post(f"{path}/test", headers=laatste_sleutel)
    assert eerste.json()["my_house"]["woningen"] and tweede.json()["my_house"]["woningen"]
    calls_voor = list(calls)
    replay = admin.post(f"{path}/test", headers=eerdere_sleutel)
    assert replay.json() == eerste.json()
    assert replay.headers["Idempotent-Replay"] == "true" and replay.headers["ETag"] == eerste.headers["ETag"]
    with app.state.sessionmaker.begin() as db:
        snapshots = db.scalars(select(AdapterHouseSnapshot).where(AdapterHouseSnapshot.link_id == uuid.UUID(link_id)))
        assert len(snapshots.all()) == 2
        record = db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(eerdere_sleutel["Idempotency-Key"]))
        )
        assert record.response_body == {**eerste.json(), "my_house": None}
        # Een bevestiging zoals die vóór het herstel werd opgeslagen.
        record.response_body = eerste.json()
    if terugrol is None:
        assert admin.delete(path, headers=idem()).status_code == 200
    else:
        migrations.downgrade(settings.database_url, terugrol)
    try:
        with app.state.sessionmaker() as db:
            records = db.scalars(select(IdempotencyRecord).where(IdempotencyRecord.scope.endswith("/test"))).all()
            assert len(records) == 2 and all(record.response_body.get("my_house") is None for record in records)
    finally:
        if terugrol is not None:
            migrations.upgrade(settings.database_url)
    with app.state.sessionmaker() as db:
        assert db.scalar(select(AdapterHouseSnapshot).where(AdapterHouseSnapshot.link_id == uuid.UUID(link_id))) is None
    for sleutel, antwoord in ((eerdere_sleutel, eerste), (laatste_sleutel, tweede)):
        replay = admin.post(f"{path}/test", headers=sleutel)
        assert replay.json() == {**antwoord.json(), "my_house": None}
        assert replay.headers["ETag"] == antwoord.headers["ETag"]
        assert replay.headers["Idempotent-Replay"] == "true"
    assert calls == calls_voor


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_upgrade_wist_oude_herhalingen_en_status_zonder_meettijd(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, settings: Settings
) -> None:
    code, _, calls = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}"
    headers = idem()
    antwoord = admin.post(f"{path}/test", headers=headers).json()
    assert antwoord["my_house"]["woningen"]
    assert admin.delete(path, headers=idem()).status_code == 200
    actieve_link = uuid.UUID(admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"])
    migrations.downgrade(settings.database_url, "0019")
    try:
        with app.state.sessionmaker.begin() as db:
            record = db.scalar(
                select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(headers["Idempotency-Key"]))
            )
            record.response_body = antwoord
            db.execute(text("UPDATE adapter_link SET my_house_status = 'healthy' WHERE id = :id"), {"id": actieve_link})
    finally:
        migrations.upgrade(settings.database_url)
    calls_voor = list(calls)
    with app.state.sessionmaker() as db:
        record = db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(headers["Idempotency-Key"]))
        )
        assert record.response_body == {**antwoord, "my_house": None}
        assert db.get(AdapterLink, actieve_link).my_house_status is None
    assert admin.get(f"{ROUTE}/{actieve_link}").json()["gezondheid"]["status"] == "unknown"
    assert admin.post(f"{path}/test", headers=headers).json() == {**antwoord, "my_house": None}
    assert calls == calls_voor


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_bronmeettijd_bepaalt_gezondheid_en_herhaling(
    admin: Any, doel: dict[str, Any], huis_simulatie: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, toestand, calls = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}"
    klok = [utcnow().replace(microsecond=0)]
    monkeypatch.setattr(my_house, "utcnow", lambda: klok[0])
    monkeypatch.setattr(adapterkoppelingen, "utcnow", lambda: klok[0])
    gemeten = klok[0] - timedelta(seconds=895)
    toestand["extra_check"] = {"state": "ok", "details": {"checked_at": gemeten.isoformat()}}
    headers = idem()
    eerste = admin.post(f"{path}/test", headers=headers).json()
    assert admin.get(path).json()["gezondheid"]["status"] == "healthy"
    klok[0] += timedelta(seconds=5)
    assert admin.get(path).json()["gezondheid"]["status"] == "healthy"
    klok[0] += timedelta(seconds=5)
    calls_voor = list(calls)
    replay = admin.post(f"{path}/test", headers=headers).json()
    assert replay["my_house"]["observed_at"] == eerste["my_house"]["observed_at"]
    assert replay["my_house"]["systeem"]["checks"][-1]["state"] == "unknown"
    assert calls == calls_voor
    for _ in range(2):
        detail = admin.get(path).json()
        assert detail["verbinding"]["status"] == "healthy"
        health = detail["gezondheid"]
        assert (health["status"], health["reason_code"]) == ("unknown", "meting_verouderd")
        assert health["observed_at"] == gemeten.isoformat().replace("+00:00", "Z")
        assert admin.get(ROUTE).json()["items"][0]["gezondheid"] == health
        admin.post(f"{path}/test", headers=idem()).raise_for_status()
    toestand["extra_checks"] = [
        {"key": f"integration:{uuid.uuid4()}", "state": "error", "details": {"checked_at": klok[0].isoformat()}}
    ]
    admin.post(f"{path}/test", headers=idem()).raise_for_status()
    assert admin.get(path).json()["gezondheid"]["status"] == "down"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
# Vaste regressiegevallen uit de werkerversheidsproef van R-VEILIG-2.
@pytest.mark.parametrize(
    ("bronleeftijd", "transport_ms", "na_ontvangst_ms"),
    [(118, 0, 2500), (None, 0, 121_000), (118, 1750, 750)],
    ids=["direct", "zonder_leeftijd", "vertraagd"],
)
def test_my_house_workerhartslag_vervalt_bij_detail_lijst_en_herhaling(
    admin: Any,
    doel: dict[str, Any],
    huis_simulatie: Any,
    monkeypatch: pytest.MonkeyPatch,
    bronleeftijd: int | None,
    transport_ms: int,
    na_ontvangst_ms: int,
) -> None:
    code, toestand, calls = huis_simulatie
    koppeling = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert koppeling.status_code == 201
    path = f"{ROUTE}/{koppeling.json()['id']}"
    klok = utcnow().replace(microsecond=0)
    monkeypatch.setattr(my_house, "utcnow", lambda: klok)
    monkeypatch.setattr(adapterkoppelingen, "utcnow", lambda: klok)
    if bronleeftijd is None:
        del toestand["worker"]["age_s"]
    else:
        toestand["worker"]["age_s"] = bronleeftijd
    transport = outbound.request

    def vertraagd_antwoord(base: str, method: str, route: str, **options: Any) -> outbound.Response:
        nonlocal klok
        antwoord = transport(base, method, route, **options)
        if route == my_house.Route.SYSTEM:
            klok += timedelta(milliseconds=transport_ms)
        return antwoord

    monkeypatch.setattr(outbound, "request", vertraagd_antwoord)
    headers = idem()
    eerste = admin.post(f"{path}/test", headers=headers)
    assert eerste.status_code == 200
    if bronleeftijd is not None and transport_ms == 0:
        assert eerste.json()["my_house"]["systeem"]["checks"][1]["state"] == "ok"
        detail = admin.get(path).json()["gezondheid"]
        assert detail["status"] == "healthy"
        assert admin.get(ROUTE).json()["items"][0]["gezondheid"] == detail

    aantal = len(calls)
    klok += timedelta(milliseconds=na_ontvangst_ms)
    detail = admin.get(path).json()
    lijst = admin.get(ROUTE).json()["items"][0]
    herhaling = admin.post(f"{path}/test", headers=headers)
    assert herhaling.status_code == 200 and herhaling.headers["Idempotent-Replay"] == "true"
    assert herhaling.json()["my_house"]["systeem"]["checks"][1] == {"key": "worker", "state": "unknown"}
    assert len(calls) == aantal
    assert detail["verbinding"]["status"] == "healthy"
    assert detail["gezondheid"] == lijst["gezondheid"]
    reden = "meting_verouderd" if bronleeftijd is not None else "meettijd_onbekend"
    assert (detail["gezondheid"]["status"], detail["gezondheid"]["reason_code"]) == ("unknown", reden)


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_workeruitval_heeft_eigen_vervalgrens(
    admin: Any, doel: dict[str, Any], huis_simulatie: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, toestand, calls = huis_simulatie
    koppeling = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert koppeling.status_code == 201
    path = f"{ROUTE}/{koppeling.json()['id']}"
    klok = utcnow().replace(microsecond=0)
    monkeypatch.setattr(my_house, "utcnow", lambda: klok)
    monkeypatch.setattr(adapterkoppelingen, "utcnow", lambda: klok)

    def gezondheid(status: str, reden: str | None = None) -> dict[str, Any]:
        detail = admin.get(path).json()["gezondheid"]
        assert (detail["status"], detail["reason_code"]) == (status, reden)
        assert admin.get(ROUTE).json()["items"][0]["gezondheid"] == detail
        return detail

    def workerstatus(antwoord: Any) -> str:
        antwoord.raise_for_status()
        checks = antwoord.json()["my_house"]["systeem"]["checks"]
        return next(check["state"] for check in checks if check["key"] == "worker")

    # De bronproef in R-VEILIG-3 mat dezelfde hartslag op 118 en 120,5 seconden.
    worker = toestand["worker"]
    worker.update(state="ok", age_s=118)
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "ok"
    gezondheid("healthy")
    klok += timedelta(milliseconds=2500)
    gezondheid("unknown", "meting_verouderd")

    worker.update(state="error", age_s=120)
    headers = idem()
    assert workerstatus(admin.post(f"{path}/test", headers=headers)) == "error"
    fout = gezondheid("down")
    assert fout["observed_at"] == klok.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    klok += timedelta(seconds=120)
    worker["age_s"] += 120
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "error"
    assert gezondheid("down") == fout
    aantal = len(calls)
    replay = admin.post(f"{path}/test", headers=headers)
    assert replay.headers["Idempotent-Replay"] == "true" and workerstatus(replay) == "error"
    assert len(calls) == aantal

    klok += timedelta(microseconds=1)
    verlopen = gezondheid("unknown", "meting_verouderd")
    assert verlopen["observed_at"] == fout["observed_at"] and verlopen["laatste_status"] == "down"
    replay = admin.post(f"{path}/test", headers=headers)
    assert replay.headers["Idempotent-Replay"] == "true" and workerstatus(replay) == "unknown"
    assert len(calls) == aantal
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "unknown"
    assert gezondheid("unknown", "meting_verouderd") == verlopen

    del worker["age_s"]
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "unknown"
    gezondheid("unknown", "meettijd_onbekend")
    worker["age_s"] = 240
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "unknown"
    assert gezondheid("unknown", "meting_verouderd") == verlopen

    worker.update(state="ok", age_s=0)
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "ok"
    gezondheid("healthy")
    klok += timedelta(seconds=120)
    worker.update(state="error", age_s=120)
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "error"
    assert gezondheid("down")["observed_at"] != fout["observed_at"]
    assert workerstatus(admin.post(f"{path}/test", headers=headers)) == "unknown"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize(
    ("bronleeftijd", "tweede_uitval"),
    [(421, False), (120, True)],
    ids=["doorlopend", "tweede_uitval"],
)
def test_my_house_herkent_volgende_uitval_aan_de_hartslag(
    admin: Any,
    doel: dict[str, Any],
    huis_simulatie: Any,
    monkeypatch: pytest.MonkeyPatch,
    bronleeftijd: int,
    tweede_uitval: bool,
) -> None:
    code, toestand, oproepen = huis_simulatie
    koppeling = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert koppeling.status_code == 201
    path = f"{ROUTE}/{koppeling.json()['id']}"
    begin = utcnow().replace(microsecond=0)
    klok = begin - timedelta(milliseconds=2500)
    monkeypatch.setattr(my_house, "utcnow", lambda: klok)
    monkeypatch.setattr(adapterkoppelingen, "utcnow", lambda: klok)

    def workerstatus(antwoord: Any) -> str:
        assert antwoord.status_code == 200
        checks = antwoord.json()["my_house"]["systeem"]["checks"]
        return next(check["state"] for check in checks if check["key"] == "worker")

    worker = toestand["worker"]
    worker.update(state="ok", age_s=118)
    assert workerstatus(admin.post(f"{path}/test", headers=idem())) == "ok"
    assert admin.get(path).json()["gezondheid"]["status"] == "healthy"

    klok = begin
    worker.update(state="error", age_s=120)
    eerste_sleutel = idem()
    assert workerstatus(admin.post(f"{path}/test", headers=eerste_sleutel)) == "error"
    eerste = admin.get(path).json()["gezondheid"]
    assert eerste["status"] == "down"

    # De Hub pollt tussendoor niet. Bij de tweede uitval meldt de bron de
    # leeftijd van een hartslag die 180 s na de eerste uitval is gemeten.
    klok += timedelta(milliseconds=300500)
    worker["age_s"] = bronleeftijd
    laatste_sleutel = idem()
    laatste = admin.post(f"{path}/test", headers=laatste_sleutel)
    assert laatste.headers.get("Idempotent-Replay") != "true"
    nieuw = workerstatus(laatste)
    assert oproepen.count(("GET", my_house.Route.SYSTEM)) == 3
    aantal = len(oproepen)
    detail = admin.get(path).json()["gezondheid"]
    assert admin.get(ROUTE).json()["items"][0]["gezondheid"] == detail

    oude_herhaling = admin.post(f"{path}/test", headers=eerste_sleutel)
    assert oude_herhaling.headers["Idempotent-Replay"] == "true"
    assert workerstatus(oude_herhaling) == "unknown"
    herhaling = admin.post(f"{path}/test", headers=laatste_sleutel)
    assert herhaling.headers["Idempotent-Replay"] == "true"
    herhaald = workerstatus(herhaling)
    assert len(oproepen) == aantal
    if tweede_uitval:
        assert (nieuw, detail["status"], detail["reason_code"], herhaald) == ("error", "down", None, "error")
        assert detail["observed_at"] == klok.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    else:
        assert (nieuw, detail["status"], detail["reason_code"], herhaald) == (
            "unknown",
            "unknown",
            "meting_verouderd",
            "unknown",
        )
        assert detail["observed_at"] == eerste["observed_at"]
        assert detail["laatste_status"] == "down"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_my_house_nieuwe_code_herstelt_na_verloren_vernieuwingsantwoord(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any, periodic_run: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, toestand, calls = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}"
    assert admin.post(f"{path}/test", headers=idem()).json()["my_house"] is not None
    with app.state.sessionmaker.begin() as db:
        db.get(AdapterLink, uuid.UUID(link_id)).my_house_expires_at = utcnow() + timedelta(days=12)
    transport = outbound.request

    def verloren_antwoord(base: str, method: str, route: str, **options: Any) -> outbound.Response:
        response = transport(base, method, route, **options)
        if route == my_house.Route.REFRESH:
            raise outbound.OutboundError("tijdslimiet")
        return response

    with monkeypatch.context() as context:
        context.setattr(outbound, "request", verloren_antwoord)
        periodic_run("my_house_vernieuwen")
    periodic_run("my_house_vernieuwen")
    periodic_run("incidenten_bijwerken")
    assert calls.count(("POST", my_house.Route.REFRESH)) == 1
    assert admin.get(path).json()["gezondheid"]["reason_code"] == "bron_vernieuwing_mislukt"
    with app.state.sessionmaker() as db:
        assert db.scalars(select(Incident.status).where(Incident.onderwerp_id == link_id)).one() == "open"

    toestand["code"] = ("B" if code[0] == "A" else "A") + code[1:]
    toestand["token"] = "shc_" + secrets.token_urlsafe(32)
    assert admin.patch(path, json={}, headers=invoer(toestand["code"])).status_code == 200
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        assert db.scalars(select(Incident.status).where(Incident.onderwerp_id == link_id)).one() == "open"
    assert admin.post(f"{path}/test", headers=idem()).json()["my_house"] is not None
    periodic_run("incidenten_bijwerken")
    with app.state.sessionmaker() as db:
        assert db.scalars(select(Incident.status).where(Incident.onderwerp_id == link_id)).one() == "opgelost"
        hersteld = select(OutboxEvent).where(
            OutboxEvent.entity_id == link_id, OutboxEvent.event_type == "monitoring.my_house.recovered"
        )
        assert len(db.scalars(hersteld).all()) == 1


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_huis_overzicht_leest_als_kijker_zonder_bronmutaties(
    admin: Any, app: Any, doel: dict[str, Any], huis_simulatie: Any
) -> None:
    code, toestand, calls = huis_simulatie
    toestand["app_link"] = URL
    toestand["extra_checks"] = [{"key": "backup", "state": "ok", "age_h": 2.5, "detail": code}]
    created = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert created.status_code == 201
    link_id = created.json()["id"]
    path = f"{ROUTE}/{link_id}/huis"
    make_user(admin, "huiskijker", "viewer")
    make_user(admin, "huiskind", "kind")
    viewer = login_as(app, "huiskijker")
    child = login_as(app, "huiskind")
    calls.clear()
    assert child.get(f"{ROUTE}/my-house").status_code == 403
    assert child.get(path).status_code == 403
    assert viewer.get(f"{ROUTE}/my-house").json() == {"items": [link_id], "next_cursor": None}
    assert viewer.get(f"{ROUTE}/my-house", params={"cursor": link_id}).json() == {"items": [], "next_cursor": None}
    assert viewer.get(f"{ROUTE}/my-house", params={"cursor": "ongeldig"}).status_code == 400
    assert viewer.post(path, headers=idem()).status_code == 405
    assert calls == []

    # De bestaande achtergrondtaak beheert vernieuwing. De schermroute leest ook nabij de vernieuwingsgrens alleen.
    with app.state.sessionmaker.begin() as db:
        row = db.get(AdapterLink, uuid.UUID(link_id))
        row.my_house_expires_at = utcnow() + timedelta(days=1)
    response = viewer.get(path)
    assert response.status_code == 200
    assert response.json()["laatste_backup"]["age_h"] == 2.5
    assert response.json()["instellingen"]["link"] == URL
    assert response.headers["Cache-Control"] == "no-store"
    zone = response.json()["woningen"][0]["zones"][0]
    assert zone["temperature"]["value"] is None
    assert zone["temperature"]["max_age_s"] == 420
    assert zone["target_c"] == 21
    assert "policy" not in zone
    assert code not in response.text and toestand["token"] not in response.text
    assert calls and {method for method, _ in calls} == {"GET"}

    calls.clear()
    with app.state.sessionmaker.begin() as db:
        db.get(AdapterLink, uuid.UUID(link_id)).my_house_expires_at = utcnow() - timedelta(seconds=1)
    response = viewer.get(path)
    assert response.status_code == 409
    assert response.json()["code"] == "bron_token_verlopen"
    assert calls == []


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_huis_deeluitval_en_weigering(
    admin: Any, doel: dict[str, Any], huis_simulatie: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, _, _ = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}/huis"
    transport = outbound.request

    def opvragen(onderdeel: str, status: int) -> Response:
        def met_storing(base: str, method: str, route: str, **kwargs: Any) -> outbound.Response:
            assert method == "GET"
            if route.rsplit("/", 1)[-1] == onderdeel:
                return outbound.Response(status, b"")
            return transport(base, method, route, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(outbound, "request", met_storing)
            return admin.get(path)

    for onderdeel, veld in (
        ("health", "databaseprobe"),
        ("status", "systeem"),
        ("homes", "woningen"),
        ("settings", "instellingen"),
        ("zones", "zones"),
        ("lights", "licht"),
        ("alerts", "meldingen"),
        ("devices", "apparaten"),
    ):
        response = opvragen(onderdeel, 503)
        assert response.status_code == 200
        body = response.json()
        deel = body["woningen"][0] if onderdeel in {"zones", "lights", "alerts", "devices"} else body
        assert deel[veld] is None
        if onderdeel != "settings":
            assert body["instellingen"]["safe_mode"] is False
        if onderdeel != "status":
            assert body["systeem"]["checks"]
        for status in (401, 403):
            response = opvragen(onderdeel, status)
            assert response.status_code == 409
            assert "woningen" not in response.json() and "instellingen" not in response.json()


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize(("status", "body", "verwacht"), [(503, b"", 503), (200, b"{}", 409)])
def test_huis_zonder_bronverbinding_of_identiteitsbewijs(
    admin: Any,
    doel: dict[str, Any],
    huis_simulatie: Any,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    body: bytes,
    verwacht: int,
) -> None:
    code, _, _ = huis_simulatie
    link_id = admin.post(ROUTE, json=doel, headers=invoer(code)).json()["id"]
    path = f"{ROUTE}/{link_id}/huis"
    transport = outbound.request
    gezien: list[str] = []

    def ontbrekende_bron(base: str, method: str, route: str, **kwargs: Any) -> outbound.Response:
        assert method == "GET" and not (kwargs.get("headers") or {}).get("Authorization")
        gezien.append(route)
        if route == my_house.Route.HEALTH:
            return transport(base, method, route, **kwargs)
        assert route == my_house.Route.IDENTITY
        return outbound.Response(status, body)

    monkeypatch.setattr(outbound, "request", ontbrekende_bron)
    antwoord = admin.get(path)
    assert antwoord.status_code == verwacht
    assert "woningen" not in antwoord.json() and "instellingen" not in antwoord.json()
    assert gezien == [my_house.Route.HEALTH, my_house.Route.IDENTITY]


def inventariseer(app: Any, settings: Settings, staat: str, *, werk_catalogus_bij: bool) -> str | None:
    with app.state.sessionmaker.begin() as db:
        eerdere = is_inventory_fresh(db, settings)
        assert eerdere["status"] == "ok" and len(eerdere["data"]) == 1
        data = [{**eerdere["data"][0], "staat": staat}]
        nu = utcnow()
        snapshot = KindResult("apps", "ok", None, "", "app.query", data, nu)
        save_run(db, CollectResult("ok", None, current_target(db).url, kinds=[snapshot]), trigger="test")
        if werk_catalogus_bij:
            assert discover(db, settings).status == "ok"
        assert is_inventory_fresh(db, settings)["data"][0]["staat"] == staat
        return iso(nu)


def toestanden(client: TestClient, doel: dict[str, Any], *, alleen_aanwezig: bool = True) -> tuple[str, str]:
    detail = client.get("/api/v1/apps/" + doel["catalog_app_id"])
    lijst = client.get("/api/v1/apps", params={"alleen_aanwezig": alleen_aanwezig})
    assert detail.status_code == lijst.status_code == 200
    (item,) = lijst.json()["items"]
    assert lijst.json()["per_status"][item["gezondheid"]["status"]] == 1
    assert item["runtime_staat"] == detail.json()["runtime_staat"]
    return detail.json()["gezondheid"]["status"], item["gezondheid"]["status"]


def maak_koppeling(admin: TestClient, doel: dict[str, Any], code: str) -> str:
    antwoord = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert antwoord.status_code == 201
    return f"{ROUTE}/{antwoord.json()['id']}"


def meet(admin: TestClient, koppeling: str) -> None:
    assert admin.post(f"{koppeling}/test", headers=idem()).status_code == 200


@pytest.mark.parametrize("doel", ["emby", "my_house", "mediaguard"], indirect=True)
def test_crash_gaat_meteen_voor_op_eerdere_meting(
    admin: TestClient, app: Any, settings: Settings, doel: dict[str, Any], huis_simulatie: Any
) -> None:
    code, _, _ = huis_simulatie
    naam = doel["app_id"]
    inventariseer(app, settings, "RUNNING", werk_catalogus_bij=True)
    if naam == "my_house":
        meet(admin, maak_koppeling(admin, doel, code))
    nu = utcnow()
    with app.state.sessionmaker.begin() as db:
        row = db.scalars(select(CatalogApp)).one()
        upsert_observation(
            db,
            bron_type="uptime_kuma",
            bron_id="proef",
            naam="Buitenkant",
            status="healthy",
            observed_at=nu,
            ttl_seconds=300,
            details={},
            reason_code=None,
            subject_app_id=row.id,
            now=nu,
        )
    verwacht = "unknown" if naam == "mediaguard" else "healthy"
    assert toestanden(admin, doel) == (verwacht, verwacht)
    meettijd = inventariseer(app, settings, "CRASHED", werk_catalogus_bij=False)
    tijdens = toestanden(admin, doel)
    detail = admin.get("/api/v1/apps/" + doel["catalog_app_id"]).json()
    assert detail["runtime_staat"] == "CRASHED"
    assert detail["gezondheid"]["observed_at"] == meettijd
    assert all(c["status"] != "healthy" for c in detail["gezondheid"]["componenten"])
    with app.state.sessionmaker.begin() as db:
        assert discover(db, settings).status == "ok"
    na = toestanden(admin, doel)
    assert na == ("down", "down")
    assert tijdens == ("down", "down")


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize("al_verwerkt", [True, False], ids=["open", "nog_in_outbox"])
def test_eerste_gezonde_meting_na_herkoppeling_sluit_incident(
    admin: TestClient,
    app: Any,
    settings: Settings,
    doel: dict[str, Any],
    huis_simulatie: Any,
    periodic_run: Any,
    al_verwerkt: bool,
) -> None:
    code, simulator, _ = huis_simulatie
    inventariseer(app, settings, "RUNNING", werk_catalogus_bij=True)
    koppeling = maak_koppeling(admin, doel, code)
    simulator["worker"] = {"key": "worker", "state": "error", "age_s": my_house.WORKER_OK_S + 5}
    for _ in range(3):
        meet(admin, koppeling)
    assert toestanden(admin, doel) == ("down", "down")

    def incidentstatus() -> tuple[str, str]:
        periodic_run("incidenten_bijwerken")
        with app.state.sessionmaker() as db:
            incident = db.scalars(select(Incident).where(Incident.soort == "monitoring.adapter_health")).one()
            return incident.onderwerp_id, incident.status

    if al_verwerkt:
        assert incidentstatus() == (doel["catalog_app_id"], "open")
    assert admin.delete(koppeling, headers=idem()).status_code == 200
    assert toestanden(admin, doel) == ("unknown", "unknown")
    # Nieuwe synthetische koppelcode via dezelfde simulator, voor dezelfde catalogusinstantie.
    simulator["code"] = code[5:] + "-" + code[:4]
    opnieuw = maak_koppeling(admin, doel, simulator["code"])
    assert opnieuw != koppeling
    if not al_verwerkt:
        for _ in range(3):
            meet(admin, opnieuw)
    simulator["worker"] = {"key": "worker", "state": "ok", "age_s": 0}
    meet(admin, opnieuw)
    assert toestanden(admin, doel) == ("healthy", "healthy")
    meet(admin, opnieuw)
    onderwerp, status = incidentstatus()
    with app.state.sessionmaker() as db:
        events = list(
            db.scalars(
                select(OutboxEvent.event_type)
                .where(
                    OutboxEvent.entity_id == doel["catalog_app_id"],
                    OutboxEvent.event_type.in_((ADAPTER_HEALTH_FAILED, ADAPTER_HEALTH_RECOVERED)),
                )
                .order_by(OutboxEvent.seq)
            )
        )
        assert events == [ADAPTER_HEALTH_FAILED, ADAPTER_HEALTH_RECOVERED]
    assert onderwerp == doel["catalog_app_id"] and status == "opgelost"


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
def test_verlopen_storing_behoudt_bronmeettijd_zonder_bronverkeer(
    admin: TestClient,
    app: Any,
    settings: Settings,
    doel: dict[str, Any],
    huis_simulatie: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    code, simulator, aanvragen = huis_simulatie
    inventariseer(app, settings, "RUNNING", werk_catalogus_bij=True)
    koppeling = maak_koppeling(admin, doel, code)
    simulator["worker"] = {"key": "worker", "state": "error", "age_s": my_house.WORKER_OK_S + 5}
    meet(admin, koppeling)
    aantal = len(aanvragen)

    def kluis_gesloten(*args, **kwargs):
        pytest.fail("De catalogus probeert de kluis te openen.")

    monkeypatch.setattr(Vault, "get", kluis_gesloten)
    pad = "/api/v1/apps/" + doel["catalog_app_id"]
    assert toestanden(admin, doel) == ("down", "down")
    meettijd = admin.get(pad).json()["gezondheid"]["observed_at"]
    assert meettijd
    later = utcnow() + timedelta(seconds=my_house.WORKER_OK_S + 1)
    monkeypatch.setattr(catalog, "utcnow", lambda: later)
    assert toestanden(admin, doel) == ("unknown", "unknown")
    uitkomst = admin.get(pad).json()["gezondheid"]
    (adapter,) = [c for c in uitkomst["componenten"] if c["bron"] == "adapter_p3"]
    assert adapter["observed_at"] == uitkomst["observed_at"] == meettijd
    assert adapter["laatste_status"] == "down" and adapter["reason_code"] == "meting_verouderd"
    for antwoord in (admin.get(pad), admin.get("/api/v1/apps")):
        assert code not in antwoord.text and simulator["token"] not in antwoord.text
    assert len(aanvragen) == aantal


def test_rechten_en_onbeschikbare_database(
    admin: TestClient, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    pad = "/api/v1/apps/" + doel["catalog_app_id"]
    paden = ["/api/v1/apps", pad]
    uitgaand = []
    monkeypatch.setattr(outbound, "request", lambda *args, **kwargs: uitgaand.append(True))
    with TestClient(app, base_url="https://testserver") as anoniem:
        assert [anoniem.get(p).status_code for p in paden] == [401, 401]
    for rol, verwacht in [("kind", 403), ("viewer", 200)]:
        make_user(admin, "proef-" + rol, rol)
        with login_as(app, "proef-" + rol) as gebruiker:
            assert [gebruiker.get(p).status_code for p in paden] == [verwacht, verwacht]
            assert gebruiker.post("/api/v1/apps/discover", headers=idem()).status_code == 403

    def database_weg():
        raise ConnectionError("Lokale testdatabase niet beschikbaar")

    assert [admin.get(p).status_code for p in paden] == [200, 200]
    with monkeypatch.context() as lokaal:
        lokaal.setitem(app.dependency_overrides, get_db, database_weg)
        with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as los:
            los.cookies.update(admin.cookies)
            fouten = [los.get(p) for p in paden]
            assert all(r.status_code >= 500 and "gezondheid" not in r.text for r in fouten)
    with app.state.sessionmaker.begin() as db:
        db.execute(update(WebSession).values(expires_at=utcnow() - timedelta(seconds=1)))
    assert [admin.get(p).status_code for p in paden] == [401, 401]
    assert not uitgaand


@pytest.mark.parametrize("doel", ["emby"], indirect=True)
@pytest.mark.parametrize(
    "geval",
    [
        "vers",
        "verversing_mislukt",
        "verlopen",
        "verdwenen",
        "dubbel",
        "ander_profiel",
        "andere_instantie",
        "ander_doel",
        "nieuwe_poort",
    ],
)
def test_catalogus_toestandstabel(
    admin: TestClient, app: Any, settings: Settings, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch, geval: str
) -> None:
    with app.state.sessionmaker.begin() as db:
        inv = is_inventory_fresh(db, settings)
        (origineel,) = inv["data"]
        row = db.scalars(select(CatalogApp)).one()
        nu = utcnow()
        upsert_observation(
            db,
            bron_type="uptime_kuma",
            bron_id="proef",
            naam="Buitenkant",
            status="healthy",
            observed_at=nu,
            ttl_seconds=300,
            details={},
            reason_code=None,
            subject_app_id=row.id,
            now=nu,
        )
        data = [origineel]
        if geval == "dubbel":
            data = [origineel, origineel]
        if geval == "verdwenen":
            data = []
        if geval == "ander_profiel":
            data = [{**origineel, "herkend_als": "my_house"}]
        if geval == "ander_doel":
            row.bron = {**row.bron, "nas": "https://vorige.example"}
        if geval == "nieuwe_poort":
            data = [{**origineel, "poorten": []}]
        if geval == "andere_instantie":
            data = [{**origineel, "runtime_id": "andere-instantie"}]
        mislukt = geval == "verversing_mislukt"
        status = "unknown" if mislukt else "ok"
        reden = "unreachable" if mislukt else None
        snapshot = KindResult("apps", status, reden, "", "app.query", None if mislukt else data, nu)
        save_run(db, CollectResult(status, reden, current_target(db).url, kinds=[snapshot]), trigger="test")
    if geval == "verlopen":
        monkeypatch.setattr(catalog, "utcnow", lambda: nu + timedelta(seconds=settings.inventory_max_age_seconds + 1))
    verwacht = "healthy" if geval == "vers" else "unknown"
    assert toestanden(admin, doel) == (verwacht, verwacht)
    detail = admin.get("/api/v1/apps/" + doel["catalog_app_id"]).json()
    (runtime,) = [c for c in detail["gezondheid"]["componenten"] if c["soort"] == "truenas"]
    if geval in ("vers", "verlopen", "verversing_mislukt", "nieuwe_poort"):
        assert runtime["observed_at"] == (inv["observed_at"] if mislukt else iso(nu))
    else:
        assert runtime["observed_at"] is None
    if geval != "vers":
        assert all(c["status"] != "healthy" for c in detail["gezondheid"]["componenten"])
    if geval in ("ander_doel", "nieuwe_poort"):
        with app.state.sessionmaker.begin() as db:
            assert discover(db, settings).status == "ok"
        assert toestanden(admin, doel) == ("unknown", "unknown")
        with app.state.sessionmaker.begin() as db:
            obs = db.scalars(select(HealthObservation)).one()
            obs.observed_at = utcnow()
        assert toestanden(admin, doel) == ("healthy", "healthy")


def bewaar_inventaris(db: Session, data: list[dict[str, Any]]) -> None:
    meting = KindResult("apps", "ok", None, "", "app.query", data, utcnow())
    save_run(db, CollectResult("ok", None, current_target(db).url, kinds=[meting]), trigger="test")


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize("tussenupdate", [True, False], ids=["bijgewerkt", "overgeslagen"])
@pytest.mark.parametrize("onderbreking", ["afwezig", "bestemming"])
def test_terugkeer_andere_instantie(admin, app, settings, doel, huis_simulatie, tussenupdate, onderbreking):
    code, simulator, aanvragen = huis_simulatie
    pad = maak_koppeling(admin, doel, code)
    meet(admin, pad)
    assert toestanden(admin, doel) == ("healthy", "healthy")
    with app.state.sessionmaker.begin() as db:
        origineel = is_inventory_fresh(db, settings)["data"]
        if onderbreking == "afwezig":
            bewaar_inventaris(db, [])
        else:
            _bewaar_apps(db, {"my_house": (9443,)})
        if tussenupdate:
            assert discover(db, settings).status == "ok"
    assert toestanden(admin, doel, alleen_aanwezig=False) == ("unknown", "unknown")
    with app.state.sessionmaker.begin() as db:
        bewaar_inventaris(db, origineel)
        assert discover(db, settings).status == "ok"
    aantal = len(aanvragen)
    assert toestanden(admin, doel) == ("unknown", "unknown")
    # De buitenkant kan op het teruggekeerde adres al een andere server bereiken.
    with app.state.sessionmaker.begin() as db:
        row = db.scalars(select(CatalogApp)).one()
        nu = utcnow()
        upsert_observation(
            db,
            bron_type="uptime_kuma",
            bron_id="proef",
            naam="Buitenkant",
            status="healthy",
            observed_at=nu,
            ttl_seconds=300,
            details={},
            reason_code=None,
            subject_app_id=row.id,
            now=nu,
        )
    inventariseer(app, settings, "CRASHED", werk_catalogus_bij=False)
    assert toestanden(admin, doel) == ("unknown", "unknown")
    inventariseer(app, settings, "RUNNING", werk_catalogus_bij=False)
    assert len(aanvragen) == aantal
    server_id = simulator["server_id"]
    simulator["server_id"] = str(uuid.uuid4())
    meet(admin, pad)
    gezondheid = admin.get("/api/v1/apps/" + doel["catalog_app_id"]).json()["gezondheid"]
    assert (gezondheid["status"], gezondheid["reason_code"]) == ("unknown", "bron_identiteit_gewijzigd")
    simulator["server_id"] = server_id
    meet(admin, pad)
    assert toestanden(admin, doel) == ("healthy", "healthy")


@pytest.mark.parametrize("doel", ["emby"], indirect=True)
@pytest.mark.parametrize("staat", ["RUNNING", "CRASHED"])
def test_gewijzigde_bestemming_voor_catalogusupdate(admin, app, settings, doel, staat):
    with app.state.sessionmaker.begin() as db:
        row = db.scalars(select(CatalogApp)).one()
        nu = utcnow()
        upsert_observation(
            db,
            bron_type="uptime_kuma",
            bron_id="proef",
            naam="Buitenkant",
            status="healthy",
            observed_at=nu,
            ttl_seconds=300,
            details={},
            reason_code=None,
            subject_app_id=row.id,
            now=nu,
        )
    assert toestanden(admin, doel) == ("healthy", "healthy")
    with app.state.sessionmaker.begin() as db:
        _bewaar_apps(db, {"emby": (9443,)})
        (andere,) = is_inventory_fresh(db, settings)["data"]
        assert andere["poorten"] and andere["portals"]
        bewaar_inventaris(db, [{**andere, "staat": staat}])
    assert toestanden(admin, doel) == ("unknown", "unknown")


@pytest.fixture
def catalogusmonitor(admin, doel, settings, monkeypatch):
    aangemaakt = admin.post(
        "/api/v1/monitoring/sources",
        json={
            "soort": "uptime_kuma",
            "naam": "Testmonitor",
            "basis_url": "https://monitor.example",
            "api_key": uuid.uuid4().hex,
        },
        headers=idem(),
    )
    assert aangemaakt.status_code == 201
    pad = "/api/v1/monitoring/sources/" + aangemaakt.json()["id"] + "/test"

    def peil(*args, now, **kwargs):
        monitor = kuma.KumaMonitor("id:1", "Buitenkant", url=doel["basis_url"], status="healthy", observed_at=now)
        return kuma.KumaResult(ok=True, monitors={monitor.sleutel: monitor})

    monkeypatch.setattr(kuma, "fetch", peil)
    monkeypatch.setattr(settings, "monitor_ttl_seconds", 30)
    assert admin.post(pad, headers=idem()).json()["resultaat"]["gekoppeld"] == 1
    assert toestanden(admin, doel) == ("healthy", "healthy")
    return pad


def kluis_gesloten(*args):
    raise VaultError("De testkluis is onbeschikbaar.")


@pytest.mark.parametrize("doel", ["emby"], indirect=True)
def test_vertraagde_inventaris_herstelt_geen_oude_bevestiging(admin, app, settings, doel, catalogusmonitor):
    with app.state.sessionmaker.begin() as db:
        origineel = is_inventory_fresh(db, settings)["data"]
        bewaar_inventaris(db, [])
        eerder = utcnow() - timedelta(seconds=5)
        vertraagd = KindResult("apps", "ok", None, "", "app.query", origineel, eerder)
        save_run(
            db, CollectResult("ok", None, current_target(db).url, kinds=[vertraagd]), trigger="test", started_at=eerder
        )
        bewaar_inventaris(db, origineel)
    assert toestanden(admin, doel) == ("unknown", "unknown")
    assert admin.post(catalogusmonitor, headers=idem()).json()["resultaat"]["status"] == "ok"
    assert toestanden(admin, doel) == ("healthy", "healthy")


@pytest.mark.parametrize("doel", ["emby"], indirect=True)
@pytest.mark.parametrize("poging_ok", [False, True], ids=["kluisfout", "poging-ok"])
@pytest.mark.parametrize("vers", [False, True], ids=["verlopen", "vers"])
@pytest.mark.parametrize("bevestigd", [False, True], ids=["onderbroken", "bevestigd"])
def test_groen_vereist_drie_bewijzen(
    admin, app, settings, doel, monkeypatch, catalogusmonitor, poging_ok, vers, bevestigd
):
    pad = catalogusmonitor
    if not poging_ok:
        with monkeypatch.context() as fout:
            fout.setattr(Vault, "get", kluis_gesloten)
            assert admin.post(pad, headers=idem()).json()["resultaat"]["status"] == "fout"
    if not bevestigd:
        with app.state.sessionmaker.begin() as db:
            origineel = is_inventory_fresh(db, settings)["data"]
            bewaar_inventaris(db, [])
            bewaar_inventaris(db, origineel)
    with monkeypatch.context() as klok:
        if not vers:
            later = utcnow() + timedelta(seconds=31)
            klok.setattr(catalog, "utcnow", lambda: later)
        verwacht = "healthy" if poging_ok and vers and bevestigd else "unknown"
        assert toestanden(admin, doel) == (verwacht, verwacht)
    assert admin.post(pad, headers=idem()).json()["resultaat"]["status"] == "ok"
    assert toestanden(admin, doel) == ("healthy", "healthy")


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize("bron", ["inventaris", "adapter"])
def test_kluisfout_na_gezonde_adapter_of_inventaris(admin, app, doel, huis_simulatie, monkeypatch, worker_once, bron):
    code, _, _ = huis_simulatie
    pad = maak_koppeling(admin, doel, code)
    meet(admin, pad)
    assert toestanden(admin, doel) == ("healthy", "healthy")

    with monkeypatch.context() as fout:
        fout.setattr(Vault, "get", kluis_gesloten)
        if bron == "inventaris":
            assert admin.post("/api/v1/inventory/refresh", headers=idem()).status_code == 202
            assert len(worker_once()) == 1
        else:
            meet(admin, pad)
    assert toestanden(admin, doel) == ("unknown", "unknown")
    if bron == "inventaris":
        with app.state.sessionmaker.begin() as db:
            _bewaar_apps(db, {"my_house": (443, 8443)})
    else:
        meet(admin, pad)
    assert toestanden(admin, doel) == ("healthy", "healthy")


@pytest.mark.parametrize("doel", ["emby"], indirect=True)
@pytest.mark.parametrize("fout", ["onbereikbaar", "kluis", "na_opslag"])
def test_mislukte_laatste_monitorpoging(admin, app, doel, catalogusmonitor, monkeypatch, fout):
    with app.state.sessionmaker.begin() as db:
        tijd = db.scalars(select(HealthObservation)).one().observed_at
    with monkeypatch.context() as storing:
        if fout == "kluis":
            storing.setattr(Vault, "get", kluis_gesloten)
        elif fout == "onbereikbaar":
            storing.setattr(kuma, "fetch", lambda *a, **kw: kuma.KumaResult(ok=False, reden="niet_bereikbaar"))
        else:
            storing.setattr(timeseries, "record", Mock(side_effect=RuntimeError("Tijdreeksopslag onbeschikbaar")))
        resultaat = admin.post(catalogusmonitor, headers=idem()).json()
        assert resultaat["resultaat"]["status"] == "fout"
        bronstatus = resultaat["bron"]["status"]
        assert bronstatus["laatste_poging"] and bronstatus["status"] == "fout"
    assert toestanden(admin, doel) == ("unknown", "unknown")
    with app.state.sessionmaker.begin() as db:
        obs = db.scalars(select(HealthObservation)).one()
        assert obs.observed_at == tijd and obs.details["bron_fout"]
    assert admin.post(catalogusmonitor, headers=idem()).json()["resultaat"]["status"] == "ok"
    assert toestanden(admin, doel) == ("healthy", "healthy")
