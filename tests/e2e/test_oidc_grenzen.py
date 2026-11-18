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
    callback,
    configure,
    enable,
    sso_login,
)
from fakes.fake_oidc import FakeOidc
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
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


@pytest.mark.parametrize("ontbreekt", ["ref", "rij", "onleesbaar"])
def test_zonder_actief_geheim_geen_test_callback_of_inschakelen(
    admin: Any, app: Any, idp: FakeOidc, ontbreekt: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.oidc import client as oidc_client

    secret = _breakglass(admin)
    enable(admin, idp)
    started = admin.post("/api/v1/auth/oidc/test")
    assert started.status_code == 200
    with app.state.sessionmaker() as db:
        if ontbreekt == "ref":
            db.get(OidcConfig, 1).client_secret_ref = None
        elif ontbreekt == "rij":
            db.execute(delete(VaultSecret).where(VaultSecret.ref == db.get(OidcConfig, 1).client_secret_ref))
        else:
            row = db.scalar(select(VaultSecret).where(VaultSecret.ref == db.get(OidcConfig, 1).client_secret_ref))
            row.ciphertext = b"onleesbare-testciphertext"
        db.commit()
    tokens_before = len([r for r in idp.requests if r.path.endswith("/token/")])
    exchange = oidc_client.exchange_code
    exchanges = []

    def spy(*args: Any, **kwargs: Any) -> Any:
        exchanges.append(True)
        return exchange(*args, **kwargs)

    monkeypatch.setattr(oidc_client, "exchange_code", spy)
    r = admin.post("/api/v1/auth/oidc/test")
    assert r.status_code == 409
    assert r.json()["code"] == "oidc_clientgeheim_ontbreekt"
    page = callback(admin, idp, started.json()["autorisatie_url"])
    assert page.status_code == 400 and "oidc_clientgeheim_ontbreekt" in page.text
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True}, headers=idem())
    assert r.status_code == 409
    assert r.json()["code"] == "oidc_clientgeheim_ontbreekt"
    assert len([r for r in idp.requests if r.path.endswith("/token/")]) == tokens_before
    assert not exchanges
    noodlogin(app, secret)


def test_wissen_verwijdert_oude_ciphertext_en_zet_sso_uit(admin: Any, app: Any, idp: FakeOidc) -> None:
    from hub.oidc.service import SECRET_REF

    secret = _breakglass(admin)
    enable(admin, idp)
    r = admin.put("/api/v1/auth/oidc", json=body(idp, client_secret_wissen=True), headers=idem())
    assert r.status_code == 200 and r.json()["ingeschakeld"] is False
    with app.state.sessionmaker() as db:
        assert db.scalar(select(VaultSecret).where(VaultSecret.ref == SECRET_REF)) is None
        assert app.state.vault().get(db, SECRET_REF) is None
    r = admin.post("/api/v1/auth/oidc/test")
    assert r.status_code == 409 and r.json()["code"] == "oidc_clientgeheim_ontbreekt"
    noodlogin(app, secret)


@pytest.mark.parametrize("route", ["put", "discover", "enable"])
def test_oidc_idempotentie_bewaart_geen_geheime_metadata(admin: Any, app: Any, idp: FakeOidc, route: str) -> None:
    from hub.models import IdempotencyRecord

    secret = _breakglass(admin)
    enable(admin, idp)
    key = idem()
    if route == "put":
        r = admin.put("/api/v1/auth/oidc", json=body(idp, client_secret=idp.client_secret), headers=key)
    elif route == "discover":
        r = admin.post("/api/v1/auth/oidc/discover", headers=key)
    else:
        r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True}, headers=key)
    assert r.status_code == 200
    with app.state.sessionmaker() as db:
        records = list(db.scalars(select(IdempotencyRecord)))
        assert len(records) >= 4
        for record in records:
            if ":/api/v1/auth/oidc" in record.scope:
                assert "laatste4" not in str(record.response_body)
    assert admin.get("/api/v1/auth/oidc").json()["client_secret"]["laatste4"] == idp.client_secret[-4:]
    noodlogin(app, secret)


def test_oude_oidc_antwoorden_worden_bij_replay_en_migratie_geschoond(
    admin: Any, app: Any, idp: FakeOidc, settings: Any
) -> None:
    import uuid

    from hub import migrations
    from hub.models import IdempotencyRecord

    configure(admin, idp)
    key = idem()
    payload = body(idp)
    assert admin.put("/api/v1/auth/oidc", json=payload, headers=key).status_code == 200
    with app.state.sessionmaker() as db:
        rec = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(key["Idempotency-Key"])))
        rec.response_body = {**rec.response_body, "client_secret": {"ingesteld": True, "laatste4": "oude-metadata"}}
        db.commit()
    replay = admin.put("/api/v1/auth/oidc", json=payload, headers=key)
    assert replay.status_code == 200 and replay.headers["Idempotent-Replay"] == "true"
    assert "laatste4" not in str(replay.json())
    migrations.downgrade(settings.database_url, "0013")
    with app.state.sessionmaker() as db:
        rows = list(db.scalars(select(IdempotencyRecord)))
        for row in rows:
            row.response_body = {**row.response_body, "oidc": {"client_secret": {"laatste4": "oude-metadata"}}}
        db.commit()
    migrations.upgrade(settings.database_url)
    with app.state.sessionmaker() as db:
        rows = list(db.scalars(select(IdempotencyRecord)))
        assert rows
        for row in rows:
            assert "laatste4" not in str(row.response_body)
