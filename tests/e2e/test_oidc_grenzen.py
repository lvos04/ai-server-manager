"""KLEIN-107: bestaande OIDC-grenzen met echte Hub-code en uitsluitend lokale fakes."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from conftest import STRONG_PASSWORD, idem
from e2e.test_oidc_sso import (
    MAPPINGS,
    NOOD_PW,
    REDIRECT,
    _breakglass,
    configure,
    enable,
    sso_login,
)
from fakes.fake_oidc import FakeOidc
from fastapi.testclient import TestClient
from sqlalchemy import select
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from hub import breakglass
from hub.models import OidcConfig, VaultSecret, WebSession
from hub.timeutil import utcnow

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
            tuple(getattr(cfg, c.name) for c in OidcConfig.__table__.columns) if cfg else None,
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
def test_geheim_http_geweigerd_zonder_mutatie(admin: Any, app: Any, idp: FakeOidc, wissen: bool, spoof: bool) -> None:
    secret = _breakglass(admin)
    configure(admin, idp)
    before = unchanged(app)
    # Een Secure-cookie reist normaal niet over HTTP; kopieer uitsluitend het testcookie expliciet.
    http = TestClient(app, base_url="http://testserver")
    http.cookies.set("hub_session", admin.cookies.get("hub_session"))
    headers = {**idem(), "X-CSRF-Token": admin.headers["X-CSRF-Token"]}
    if spoof:
        headers.update({"X-Forwarded-Proto": "https", "Forwarded": "proto=https"})
    fields = {"client_secret_wissen": True} if wissen else {"client_secret": idp.client_secret}
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


@pytest.mark.parametrize("reden", ["uit", "andere_versie"])
def test_sessie_toetst_sso_en_actuele_configuratie(admin: Any, app: Any, idp: FakeOidc, reden: str) -> None:
    secret = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    nood = noodlogin(app, secret)
    with app.state.sessionmaker() as db:
        cfg = db.get(OidcConfig, 1)
        if reden == "uit":
            cfg.ingeschakeld = False
        else:
            cfg.config_versie += 1
        db.commit()
    if reden == "uit":
        lokaal = TestClient(app, base_url="https://testserver")
        assert (
            lokaal.post(
                "/api/v1/auth/login",
                json={"username": "beheerder", "password": STRONG_PASSWORD},
            ).status_code
            == 200
        )
    assert sso.get("/api/v1/auth/me").status_code == 401
    assert admin.get("/api/v1/auth/me").status_code == 200
    assert nood.get("/api/v1/auth/me").status_code == 200


def test_upgrade_behoudt_bestaand_totp_en_weigert_oude_oidc_sessie(
    admin: Any, app: Any, idp: FakeOidc, settings: Any
) -> None:
    from hub import migrations

    secret = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    before = unchanged(app)
    migrations.downgrade(settings.database_url, "0012")
    migrations.upgrade(settings.database_url)
    assert unchanged(app) == before
    assert sso.get("/api/v1/auth/me").status_code == 401
    assert admin.get("/api/v1/auth/me").status_code == 200
    noodlogin(app, secret)


@pytest.mark.parametrize(
    "actie",
    [
        "uit",
        "al_uit",
        "vervangen",
        "wissen",
        "automatisch",
        "discover",
        "scopes",
        "duur",
    ],
)
def test_oidc_overgangen_trekken_alleen_oidc_in(admin: Any, app: Any, idp: FakeOidc, actie: str) -> None:
    secret = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    nood = noodlogin(app, secret)
    with app.state.sessionmaker() as db:
        if actie in ("al_uit", "vervangen", "wissen"):
            db.get(OidcConfig, 1).ingeschakeld = False
        if actie == "automatisch":
            db.get(OidcConfig, 1).discovery_op = utcnow() - timedelta(days=2)
        db.commit()
    if actie in ("uit", "al_uit"):
        assert (
            admin.post(
                "/api/v1/auth/oidc/inschakelen",
                json={"ingeschakeld": False},
                headers=idem(),
            ).status_code
            == 200
        )
    elif actie in ("automatisch", "discover"):
        idp.algs = ["RS256", "ES256"]
        if actie == "automatisch":
            assert sso.get("/api/v1/auth/oidc/login", follow_redirects=False).status_code == 303
        else:
            assert admin.post("/api/v1/auth/oidc/discover", headers=idem()).status_code == 200
    else:
        fields = {"client_secret": idp.client_secret} if actie == "vervangen" else {"client_secret_wissen": True}
        if actie == "scopes":
            fields = {"scopes": "openid profile"}
        elif actie == "duur":
            fields = {"sessie_minuten": 60}
        assert admin.put("/api/v1/auth/oidc", json=body(idp, **fields), headers=idem()).status_code == 200
    with app.state.sessionmaker() as db:
        oidc = list(db.scalars(select(WebSession).where(WebSession.auth_bron == "oidc")))
        local = list(db.scalars(select(WebSession).where(WebSession.auth_bron == "lokaal")))
        assert oidc and all(s.revoked_at is not None for s in oidc)
        assert local and all(s.revoked_at is None for s in local)
        assert db.get(OidcConfig, 1).ingeschakeld is False
        db.get(OidcConfig, 1).ingeschakeld = True
        db.commit()
    assert sso.get("/api/v1/auth/me").status_code == 401
    assert admin.get("/api/v1/auth/me").status_code == 200
    assert nood.get("/api/v1/auth/me").status_code == 200


def test_bestaand_totp_na_clientinvoer(admin: Any, app: Any, idp: FakeOidc) -> None:
    secret = _breakglass(admin)
    configure(admin, idp)
    noodlogin(app, secret)


@pytest.mark.parametrize("trusted", [False, True])
def test_geheim_volgt_alleen_vertrouwde_proxy(admin: Any, app: Any, idp: FakeOidc, trusted: bool) -> None:
    proxy = ProxyHeadersMiddleware(app, trusted_hosts=["192.0.2.10"] if trusted else ["127.0.0.1"])
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


@pytest.mark.parametrize("wissen", [False, True])
def test_alleen_lokale_beheerder_of_noodsessie_wijzigt_geheim(
    admin: Any, app: Any, idp: FakeOidc, wissen: bool
) -> None:
    secret = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf") or ""
    fields = {"client_secret_wissen": True} if wissen else {"client_secret": idp.client_secret}
    before = unchanged(app)
    r = sso.put("/api/v1/auth/oidc", json=body(idp, **fields), headers=idem())
    assert r.status_code == 403
    assert r.json()["code"] == "lokale_beheerder_vereist"
    assert unchanged(app) == before
    assert sso.put("/api/v1/auth/oidc", json=body(idp), headers=idem()).status_code == 200
    nood = noodlogin(app, secret)
    assert nood.put("/api/v1/auth/oidc", json=body(idp, **fields), headers=idem()).status_code == 200
    assert admin.get("/api/v1/auth/me").status_code == 200
