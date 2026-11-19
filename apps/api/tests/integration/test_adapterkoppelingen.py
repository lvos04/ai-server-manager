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
from hub.models import AuditEvent, CatalogApp, IdempotencyRecord, VaultSecret
from hub.timeutil import utcnow

ROUTE = "/api/v1/adapterkoppelingen"
APP_ID = "mediaguard"
URL = "https://adapter.example"
PEER = str(IPv4Address(bytes((192, 0, 2, 1))))


@pytest.fixture
def doel(app: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr(outbound, "resolve_peer_addresses", lambda *_args: frozenset({PEER}))
    with app.state.sessionmaker() as db:
        row = CatalogApp(
            runtime_id="test-instantie",
            naam="Testinstantie",
            app_id=APP_ID,
            adaptertype="bestaand_mediaguard",
            soort="bestaand",
            installatiewijze="custom_app",
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
    from hub.models import AdapterLink

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
    contact = admin.get(path).json()["verbinding"]
    assert contact["status"] == "unknown"
    assert contact["reason_code"] == "tijdslimiet"
    ander = {"basis_url": "https://ander.example", "doel_bevestigd": True}
    assert admin.patch(path, json=ander, headers=idem()).status_code == 422
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
    from hub.models import AdapterLink
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
