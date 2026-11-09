"""Hub → dienst en koppelbeheer (contract 1.2 §3.8, §4.3, §4.5, H5/H14).

Een kleine nep-dienst (HTTP op 127.0.0.1) controleert dat de Hub zich meldt met een **dienst-JWT** (``token_use:
"hub_service"``, ``sub: "hub"``, ``roles: ["service"]``, eigen ``service_id``, ``jti``) en nooit met het service-token,
met ``Idempotency-Key``. Ontkoppelen trekt pas in na een geslaagd antwoord (of 401 ``not_linked`` bij een herhaling).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import jwt
import pytest
from conftest import enroll_body, idem

pytestmark = pytest.mark.integration


class FakeService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.reply: tuple[int, dict[str, Any]] = (200, {"state": "ontkoppeld"})
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                outer.calls.append({"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)})
                status, body = outer.reply
                raw = json.dumps(body).encode()
                self.send_response(status)
                if status in (301, 302, 307):
                    self.send_header("Location", "http://127.0.0.1:9/elders")
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args: Any) -> None:
                return

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake_service() -> Iterator[FakeService]:
    svc = FakeService()
    yield svc
    svc.close()


def _enrolled(admin: Any, app: Any, app_id: str = "home-control-hub") -> dict[str, Any]:
    from fastapi.testclient import TestClient

    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id}).json()["enrollment_token"]
    anon = TestClient(app, base_url="https://testserver")
    r = anon.post("/api/v1/services/enroll", json=enroll_body(app_id, token=tok))
    assert r.status_code == 200, r.text
    return dict(r.json())


def test_ontkoppelen_met_dienst_jwt_en_daarna_intrekken(
    admin: Any, app: Any, fake_service: FakeService, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.routers import services as services_router

    svc = _enrolled(admin, app)
    monkeypatch.setattr(services_router, "service_base_url", lambda db, settings, s: (fake_service.url, None))
    key = idem()
    r = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=key)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "revoked" and r.json()["ontkoppeld_bij_dienst"] is True
    call = fake_service.calls[-1]
    assert (
        call["path"] == "/connector/v1/hub-link/unlink" and call["headers"]["Idempotency-Key"] == key["Idempotency-Key"]
    )
    bearer = call["headers"]["Authorization"].removeprefix("Bearer ")
    assert bearer != svc["service_token"] and not bearer.startswith("svc_")
    jwks = jwt.PyJWKSet.from_dict(svc["jwks"])
    claims = jwt.decode(bearer, jwks.keys[0].key, algorithms=["EdDSA"], audience="home-control-hub", issuer="hub")
    assert claims["token_use"] == "hub_service" and claims["sub"] == "hub" and claims["roles"] == ["service"]
    assert claims["service_id"] == svc["service_id"] and claims["jti"] and claims["exp"] - claims["iat"] <= 120
    # Registratie is ingetrokken: het service-token werkt niet meer; dezelfde key herhaalt het antwoord
    from fastapi.testclient import TestClient

    anon = TestClient(app, base_url="https://testserver")
    assert (
        anon.get("/api/v1/services/self", headers={"Authorization": f"Bearer {svc['service_token']}"}).status_code
        == 401
    )
    again = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=key)
    assert again.status_code == 200 and again.headers.get("Idempotent-Replay") == "true"
    assert len(fake_service.calls) == 1


def test_herhaalde_unlink_met_not_linked_telt_als_geslaagd(
    admin: Any, app: Any, fake_service: FakeService, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.routers import services as services_router

    svc = _enrolled(admin, app)
    monkeypatch.setattr(services_router, "service_base_url", lambda db, settings, s: (fake_service.url, None))
    fake_service.reply = (401, {"code": "unauthorized", "details": {"reason": "not_linked"}})
    r = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "revoked"


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        ((401, {"code": "unauthorized", "details": {"reason": "token_use_invalid"}}), "unlink_refused"),
        ((403, {"code": "forbidden"}), "unlink_refused"),
        ((500, {"code": "internal_error"}), "unlink_refused"),
        ((302, {}), "service_unreachable"),  # redirect wordt nooit gevolgd
    ],
)
def test_ontkoppelen_mislukt_dan_blijft_de_registratie(
    admin: Any,
    app: Any,
    fake_service: FakeService,
    monkeypatch: pytest.MonkeyPatch,
    reply: tuple[int, dict[str, Any]],
    code: str,
) -> None:
    from hub.routers import services as services_router

    svc = _enrolled(admin, app)
    monkeypatch.setattr(services_router, "service_base_url", lambda db, settings, s: (fake_service.url, None))
    fake_service.reply = reply
    r = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=idem())
    assert r.status_code == 502 and r.json()["code"] == code, r.text
    item = admin.get("/api/v1/services").json()["items"][0]
    assert item["status"] == "active" and any(t["geldig"] for t in item["tokens"])
    assert all(c["path"] != "/elders" for c in fake_service.calls)


def test_ontkoppelen_zonder_gemeten_adres_of_bereikbaarheid(
    admin: Any, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.routers import services as services_router

    svc = _enrolled(admin, app)
    # Geen D03 en geen inventaris: nooit een aangenomen adres (ook niet base_url uit het enroll-verzoek)
    r = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=idem())
    assert r.status_code == 409 and r.json()["details"]["reason"] == "nas_adres_onbekend"
    monkeypatch.setattr(services_router, "service_base_url", lambda db, settings, s: ("http://127.0.0.1:9", None))
    r = admin.post(f"/api/v1/services/{svc['service_id']}/unlink", headers=idem())
    assert r.status_code == 502 and r.json()["code"] == "service_unreachable"
    assert admin.get("/api/v1/services").json()["items"][0]["status"] == "active"
    assert admin.post(f"/api/v1/services/{svc['service_id']}/unlink").status_code == 400  # Idempotency-Key


def test_truenas_appnaam_bevestigen_alleen_als_gemeten(admin: Any, app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from hub.routers import services as services_router

    svc = _enrolled(admin, app, "appstore-en-fork")
    url = f"/api/v1/services/{svc['service_id']}/truenas-app"
    r = admin.put(url, json={"app_name": "mijn-appstore"}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "inventory_not_current"
    apps = [
        {"naam": "mijn-appstore", "images": [{"repository": "ghcr.io/lvos04/appstore-en-fork"}]},
        {"naam": "nep", "images": [{"repository": "docker.io/library/nginx"}]},
    ]
    monkeypatch.setattr(
        services_router, "measured_apps", lambda db, settings: {"status": "ok", "data": apps, "observed_at": None}
    )
    listed = admin.get("/api/v1/services").json()["items"][0]["truenas_app"]
    assert listed["naam"] == "appstore-en-fork" and listed["bevestigd"] is False
    assert listed["gemeten_kandidaten"] == ["mijn-appstore"]
    r = admin.put(url, json={"app_name": "nep"}, headers=idem())
    assert r.status_code == 422 and r.json()["details"]["kandidaten"] == ["mijn-appstore"]
    assert admin.put(url, json={"app_name": "Mijn App"}, headers=idem()).status_code == 422
    r = admin.put(url, json={"app_name": "mijn-appstore"}, headers=idem())
    assert r.status_code == 200, r.text
    assert r.json()["truenas_app"] == {
        "naam": "mijn-appstore",
        "bevestigd": True,
        "bevestigd_door": "beheerder",
        "bevestigd_op": r.json()["truenas_app"]["bevestigd_op"],
    }
    assert r.json()["app_id"] == "appstore-en-fork"  # app_id blijft vast (§2)


def test_registeradres_uit_d03_en_gemeten_hostpoort(app: Any, settings: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.orm import Session

    from hub import registry
    from hub.models import Service

    apps = [
        {
            "naam": "home-control-hub",
            "images": [{"repository": "ghcr.io/lvos04/home-control-hub"}],
            "poorten": [
                {"container_poort": 9999, "host_poort": 31000, "protocol": "tcp"},
                {"container_poort": 30420, "host_poort": 30421, "protocol": "tcp"},
            ],
        }
    ]
    svc = Service(app_id="home-control-hub", enrolled_via="token")
    with Session(app.state.engine) as db:
        assert registry.service_base_url(db, settings, svc) == (None, "nas_adres_onbekend")
        monkeypatch.setattr(registry, "nas_address", lambda db: "192.0.2.20")
        monkeypatch.setattr(registry, "measured_apps", lambda db, s: {"status": "unknown", "data": apps})
        assert registry.service_base_url(db, settings, svc) == (None, "inventaris_niet_actueel")
        monkeypatch.setattr(registry, "measured_apps", lambda db, s: {"status": "ok", "data": apps})
        assert registry.service_base_url(db, settings, svc) == ("http://192.0.2.20:30421", None)
        svc.truenas_app_name = "andere-naam"
        assert registry.service_base_url(db, settings, svc) == (None, "app_niet_gevonden")
        svc.truenas_app_name = None
        apps[0]["images"] = [{"repository": "docker.io/library/nginx"}]
        assert registry.service_base_url(db, settings, svc) == (None, "image_komt_niet_overeen")
        monkeypatch.setattr(registry, "nas_address", lambda db: "fd00::5")
        apps[0]["images"] = [{"repository": "ghcr.io/lvos04/home-control-hub"}]
        assert registry.service_base_url(db, settings, svc) == ("http://[fd00::5]:30421", None)


def test_sleutelrotaties_leeg_en_sleutelset_kopieerbaar(admin: Any, app: Any) -> None:
    from fastapi.testclient import TestClient

    from hub.keys import keyset_fingerprint

    anon = TestClient(app, base_url="https://testserver")
    r = anon.get("/api/v1/auth/key-rotations?after=0")
    assert r.status_code == 200 and r.json() == {"items": []}  # de Hub roteert zijn sleutels nog niet
    assert anon.get("/api/v1/auth/key-rotations?after=-1").status_code == 422
    assert anon.get("/api/v1/auth/keyset").status_code == 401
    ks = admin.get("/api/v1/auth/keyset").json()
    assert ks["keyset_fingerprint"] == keyset_fingerprint(ks["jwks"]["keys"], ks["policy_public_key"])
    assert all("d" not in k for k in [*ks["jwks"]["keys"], ks["policy_public_key"]])  # alleen publieke sleutels
