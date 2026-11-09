"""Enrollment (eenmalige tokens, koppelcodes), service-tokens (alleen hashes), rotatie en intrekken."""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from conftest import idem

pytestmark = pytest.mark.integration


def _token(admin: Any, app_id: str = "jelly-leon-platform") -> str:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    return str(r.json()["enrollment_token"])


def _enroll(client: Any, **body: Any) -> Any:
    client.headers.pop("X-CSRF-Token", None)
    return client.post("/api/v1/services/enroll", json=body)


def test_enrollment_eenmalig_en_geeft_jwks(admin: Any, app: Any, clean_db: str) -> None:
    from fastapi.testclient import TestClient

    tok = _token(admin)
    anon = TestClient(app, base_url="https://testserver")
    r = _enroll(
        anon, app_id="jelly-leon-platform", enrollment_token=tok, version="0.1.0", base_url="http://192.0.2.10:30440"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert (
        body["service_token"].startswith("svc_")
        and body["jwks"]["keys"]
        and body["policy_public_key"]["crv"] == "Ed25519"
    )
    assert r.headers["Cache-Control"] == "no-store"
    again = _enroll(anon, app_id="jelly-leon-platform", enrollment_token=tok)
    assert again.status_code == 401 and again.json()["code"] == "invalid_enrollment"
    # alleen hashes in de database
    with psycopg.connect(clean_db) as conn:
        rows = conn.execute("SELECT token_hash FROM service_token").fetchall()
        assert rows and all(len(r[0]) == 64 for r in rows)
        dump = str(conn.execute("SELECT * FROM service_token").fetchall()) + str(
            conn.execute("SELECT * FROM enrollment_grant").fetchall()
        )
        assert body["service_token"] not in dump and tok not in dump
    services = admin.get("/api/v1/services").json()["items"]
    assert services[0]["tokens"][0]["laatste4"] == body["service_token"][-4:]
    assert body["service_token"] not in str(services)


def test_verkeerde_app_en_verlopen_token(admin: Any, app: Any, clean_db: str) -> None:
    from fastapi.testclient import TestClient

    anon = TestClient(app, base_url="https://testserver")
    tok = _token(admin, "home-control-hub")
    assert _enroll(anon, app_id="andere-app", enrollment_token=tok).status_code == 401
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE enrollment_grant SET expires_at = now() - interval '1 minute'")
    assert _enroll(anon, app_id="home-control-hub", enrollment_token=tok).status_code == 401
    assert _enroll(anon, app_id="home-control-hub").status_code == 422  # token of koppelcode verplicht


def test_koppelcode_handmatige_app(admin: Any, app: Any) -> None:
    from fastapi.testclient import TestClient

    r = admin.post("/api/v1/services/pairing-codes", json={"app_id": "appstore-en-fork"})
    code = r.json()["koppelcode"]
    anon = TestClient(app, base_url="https://testserver")
    r = _enroll(anon, app_id="appstore-en-fork", pairing_code=code.lower().replace("-", " "))
    assert r.status_code == 200, r.text
    assert _enroll(anon, app_id="appstore-en-fork", pairing_code=code).status_code == 401


def test_rotatie_en_intrekken(admin: Any, app: Any, settings: Any) -> None:
    from fastapi.testclient import TestClient

    anon = TestClient(app, base_url="https://testserver")
    svc = _enroll(
        anon, app_id="zoeken-en-persoonlijke-ai", enrollment_token=_token(admin, "zoeken-en-persoonlijke-ai")
    ).json()
    old = svc["service_token"]
    hdr = {"Authorization": f"Bearer {old}"}
    assert anon.get("/connector/v1/discover", headers=hdr).status_code == 200
    rot = anon.post("/api/v1/services/self/rotate", headers=hdr)
    assert rot.status_code == 200, rot.text
    new = rot.json()["service_token"]
    assert new != old
    assert anon.get("/connector/v1/discover", headers=hdr).status_code == 200  # overgangstijd
    assert anon.get("/connector/v1/discover", headers={"Authorization": f"Bearer {new}"}).status_code == 200
    r = admin.post(f"/api/v1/services/{svc['service_id']}/revoke", headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    for t in (old, new):
        r = anon.get("/connector/v1/discover", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 401 and r.json()["code"] == "unauthorized"


def test_herinschrijving_trekt_oude_tokens_in(admin: Any, app: Any) -> None:
    from fastapi.testclient import TestClient

    anon = TestClient(app, base_url="https://testserver")
    first = _enroll(anon, app_id="jelly-leon", enrollment_token=_token(admin, "jelly-leon")).json()["service_token"]
    second = _enroll(anon, app_id="jelly-leon", enrollment_token=_token(admin, "jelly-leon")).json()["service_token"]
    assert anon.get("/connector/v1/discover", headers={"Authorization": f"Bearer {first}"}).status_code == 401
    assert anon.get("/connector/v1/discover", headers={"Authorization": f"Bearer {second}"}).status_code == 200


def test_publieke_sleutel_validatie(admin: Any, app: Any) -> None:
    from fastapi.testclient import TestClient

    anon = TestClient(app, base_url="https://testserver")
    bad = {"kty": "OKP", "crv": "Ed25519", "x": "AAAA", "d": "geheim"}
    r = _enroll(anon, app_id="jelly-leon", enrollment_token=_token(admin, "jelly-leon"), public_key_jwk=bad)
    assert r.status_code == 422
