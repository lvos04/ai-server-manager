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

from hub import outbound
from hub.models import AdapterLink, AuditEvent, CatalogApp, Decision, IdempotencyRecord, VaultSecret
from hub.timeutil import utcnow

ROUTE = "/api/v1/adapterkoppelingen"
APP_ID = "mediaguard"
URL = "https://adapter.example"
TWEEDE_BASIS = f"{URL}:8443"
PEER = str(IPv4Address(bytes((192, 0, 2, 1))))


@pytest.fixture
def doel(app: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({PEER}))
    with app.state.sessionmaker() as db:
        besluit = db.get(Decision, "D03")
        assert besluit is not None
        besluit.status = "Ingevuld"
        besluit.waarde = {"nas_adres": "adapter.example"}
        row = CatalogApp(
            runtime_id="test-instantie",
            naam="Testinstantie",
            app_id=APP_ID,
            adaptertype="bestaand_mediaguard",
            soort="bestaand",
            installatiewijze="custom_app",
            portals=[{"schema": "https", "poort": poort, "pad": "/"} for poort in (443, 8443)],
            poorten=[{"protocol": "tcp", "host_poort": poort} for poort in (443, 8443)],
        )
        db.add(row)
        db.flush()
        body = {"app_id": APP_ID, "catalog_app_id": str(row.id), "basis_url": URL, "doel_bevestigd": True}
        db.commit()
    return body


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
    admin: Any, app: Any, doel: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.state.sessionmaker.begin() as db:
        db.add(
            CatalogApp(
                runtime_id="andere-testinstantie",
                naam="Andere testinstantie",
                app_id="media-source-optimizer",
                adaptertype="bestaand_mso",
                soort="bestaand",
                installatiewijze="custom_app",
                portals=[{"schema": "https", "poort": 9443, "pad": "/"}],
                poorten=[{"protocol": "tcp", "host_poort": 9443}],
            )
        )
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
