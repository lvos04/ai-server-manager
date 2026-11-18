"""KLEIN-107: bestaande OIDC-grenzen met echte Hub-code en uitsluitend lokale fakes."""

from __future__ import annotations

from typing import Any

import pytest
from e2e.test_oidc_sso import MAPPINGS, NOOD_PW, REDIRECT, _breakglass, configure
from fakes.fake_oidc import FakeOidc
from fastapi.testclient import TestClient
from hub import breakglass
from hub.models import OidcConfig, VaultSecret
from hub.timeutil import utcnow
from sqlalchemy import select
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from conftest import idem

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.fixture
def idp() -> Any:
    fake = FakeOidc().start()
    yield fake
    fake.stop()


def body(idp: FakeOidc, **changes: Any) -> dict[str, Any]:
    return {
        "issuer": idp.issuer,
        "client_id": idp.client_id,
        "redirect_uri": REDIRECT,
        "rolkoppelingen": MAPPINGS,
        **changes,
    }


def unchanged(app: Any) -> tuple[Any, ...]:
    """Vergelijk configuratie en alle kluisrijen zonder ze in testuitvoer af te drukken."""
    with app.state.sessionmaker() as db:
        cfg = db.get(OidcConfig, 1)
        return (
            tuple(getattr(cfg, c.name) for c in OidcConfig.__table__.columns)
            if cfg
            else None,
            tuple(
                (r.ref, r.nonce, r.ciphertext, r.updated_at)
                for r in db.scalars(select(VaultSecret).order_by(VaultSecret.ref))
            ),
        )


def noodlogin(app: Any, secret: str, offset: int = 1) -> TestClient:
    c = TestClient(app, base_url="https://testserver", client=("192.168.1.20", 40000))
    code = breakglass.totp_at(secret, breakglass.time_step(utcnow()) + offset)
    r = c.post(
        "/api/v1/auth/break-glass/login",
        json={"username": "nood", "password": NOOD_PW, "totp": code},
    )
    assert r.status_code == 200
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


@pytest.mark.parametrize("wissen", [False, True])
@pytest.mark.parametrize("spoof", [False, True])
def test_geheim_http_geweigerd_zonder_mutatie(
    admin: Any, app: Any, idp: FakeOidc, wissen: bool, spoof: bool
) -> None:
    secret = _breakglass(admin)
    configure(admin, idp)
    before = unchanged(app)
    # Een Secure-cookie reist normaal niet over HTTP; kopieer uitsluitend het testcookie expliciet.
    http = TestClient(app, base_url="http://testserver")
    http.cookies.set("hub_session", admin.cookies.get("hub_session"))
    headers = {**idem(), "X-CSRF-Token": admin.headers["X-CSRF-Token"]}
    if spoof:
        headers.update({"X-Forwarded-Proto": "https", "Forwarded": "proto=https"})
    fields = (
        {"client_secret_wissen": True}
        if wissen
        else {"client_secret": idp.client_secret}
    )
    r = http.put("/api/v1/auth/oidc", json=body(idp, **fields), headers=headers)
    assert r.status_code == 403
    assert r.json()["code"] == "oidc_geheim_https_vereist"
    assert unchanged(app) == before
    # Niet-geheime instellingen blijven via HTTP werken.
    assert (
        http.put(
            "/api/v1/auth/oidc",
            json=body(idp, sessie_minuten=60),
            headers={**headers, **idem()},
        ).status_code
        == 200
    )
    assert admin.get("/api/v1/auth/me").status_code == 200
    noodlogin(app, secret)


@pytest.mark.parametrize("trusted", [False, True])
def test_geheim_volgt_alleen_vertrouwde_proxy(
    admin: Any, app: Any, idp: FakeOidc, trusted: bool
) -> None:
    proxy = ProxyHeadersMiddleware(
        app, trusted_hosts=["192.0.2.10"] if trusted else ["127.0.0.1"]
    )
    c = TestClient(proxy, base_url="http://testserver", client=("192.0.2.10", 40000))
    c.cookies.set("hub_session", admin.cookies.get("hub_session"))
    r = c.put(
        "/api/v1/auth/oidc",
        json=body(idp, client_secret=idp.client_secret),
        headers={
            **idem(),
            "X-CSRF-Token": admin.headers["X-CSRF-Token"],
            "X-Forwarded-Proto": "https",
        },
    )
    assert r.status_code == (200 if trusted else 403)
