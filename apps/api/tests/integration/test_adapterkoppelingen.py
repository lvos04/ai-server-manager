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
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import outbound
from hub.adapters import basis
from hub.catalog.discovery import discover, is_inventory_fresh
from hub.config import Settings
from hub.inventory.collector import CollectResult, KindResult
from hub.inventory.store import save_run
from hub.models import (
    AdapterLink,
    AuditEvent,
    CatalogApp,
    Decision,
    IdempotencyRecord,
    Incident,
    OutboxEvent,
    VaultSecret,
)
from hub.timeutil import utcnow
from hub.truenas import normalize
from hub.truenas.connection import current_target

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

    probe = Mock(return_value=outbound.Response(200, json.dumps({"status": "ok", "extra": waarde}).encode()))
    monkeypatch.setattr(outbound, "request", probe)
    getest = admin.post(f"{path}/test", headers=idem())
    assert getest.status_code == 200
    contact = admin.get(path)
    assert contact.json()["verbinding"]["status"] == "healthy"
    assert contact.json()["gezondheid"]["status"] == "unknown"
    assert waarde not in contact.text
    assert probe.call_args.args == (URL, "GET", "/api/v1/health")
    assert "headers" not in probe.call_args.kwargs

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
        opgeslagen.observed_at = utcnow() - timedelta(seconds=901)
        db.commit()
    assert waarde not in caplog.text
    assert admin.get(path).json()["verbinding"]["reason_code"] == "meting_verouderd"

    assert admin.delete(path, headers=idem()).status_code == 200
    assert admin.get(path).status_code == 404
    assert probe.call_count == 1
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
    contact = Mock(return_value=basis.Measurement(status="unknown", reason_code="tijdslimiet"))
    monkeypatch.setattr(outbound, "request", transport)
    monkeypatch.setattr(basis, "probe", contact)
    waarde = secrets.token_urlsafe()
    aangemaakt = admin.post(ROUTE, json=doel, headers=invoer(waarde))
    assert aangemaakt.status_code == 201
    pad = f"{ROUTE}/{aangemaakt.json()['id']}"
    assert admin.post(f"{pad}/test", headers=idem()).status_code == 200
    contact.assert_called_once()
    contact.reset_mock()
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
    contact.assert_not_called()
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
    contact.assert_not_called()


def test_doelbinding_en_onbereikbaarheid(
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = invoer(secrets.token_urlsafe())
    assert admin.post(ROUTE, json={**doel, "app_id": "my_house"}, headers=headers).status_code == 409
    created = admin.post(ROUTE, json=doel, headers=headers)
    assert created.status_code == 201
    path = f"{ROUTE}/{created.json()['id']}"
    probe = Mock(side_effect=outbound.OutboundError("tijdslimiet"))
    monkeypatch.setattr(outbound, "request", probe)
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    detail = admin.get(path).json()
    assert detail["verbinding"]["status"] == "unknown"
    assert detail["verbinding"]["reason_code"] == "tijdslimiet"
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
    assert probe.call_count == 1


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
    probe = Mock(return_value=outbound.Response(200, b'{"status":"ok"}'))
    monkeypatch.setattr(outbound, "request", probe)
    assert admin.post(f"{path}/test", headers=idem()).status_code == 200
    meting = admin.get(path).json()["verbinding"]
    assert meting["status"] == "healthy"

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
    probe.assert_called_once()


def test_my_house_koppelcode_wordt_zonder_inwisseling_geweigerd(admin: Any, app: Any, doel: dict[str, Any]) -> None:
    with app.state.sessionmaker() as db:
        instance = db.get(CatalogApp, uuid.UUID(doel["catalog_app_id"]))
        assert instance
        instance.app_id = "my_house"
        db.commit()
    waarde = secrets.token_urlsafe()
    response = admin.post(ROUTE, json={**doel, "app_id": "my_house"}, headers=invoer(waarde))
    assert response.status_code == 501
    assert response.json()["code"] == "capability_unavailable"
    assert waarde not in response.text
    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref.startswith("vault://adapters/"))) is None


def test_downgrade_wist_alleen_adapteropslag(admin: Any, app: Any, doel: dict[str, Any], settings: Any) -> None:
    from sqlalchemy import inspect

    from hub import migrations
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
