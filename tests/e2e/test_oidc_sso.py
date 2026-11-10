"""Dienst-E2E: SSO-login van de Hub via OIDC (B01-006, Hub-kant van B13) tegen een in-repo OIDC-fake (Sim-getest).

Acceptatie B01-006: een kijker kan nooit update/stop of geheimen ophalen; uitloggen en sessie-intrekking werken direct.
B13-002 (Hub-kant): verkeerde issuer/aud/nonce, verkeerd algoritme en replay worden geweigerd. Contract 1.2 §4.1: de
noodlogin blijft werken als OIDC faalt, "OIDC verplicht" kan niet zonder werkend noodaccount.
NIET GEVALIDEERD tegen een echte Authentik (account/instantie ontbreekt).
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import psycopg
import pytest
from conftest import STRONG_PASSWORD, enroll_body, idem, login_as, make_user
from eventhelpers import event, post, service
from fakes.fake_oidc import FakeHchSso, FakeOidc
from fastapi.testclient import TestClient

from hub import breakglass
from hub.timeutil import utcnow

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
REDIRECT = "https://testserver/api/v1/auth/oidc/callback"
MAPPINGS = [
    {"groep": "hub-admins", "rol": "admin"},
    {"groep": "hub-beheer", "rol": "operator"},
    {"groep": "hub-kijkers", "rol": "viewer"},
    {"groep": "kinderen", "rol": "kind"},
]
NOOD_PW = "Paraplu-Vuurtoren-Lang-Genoeg-2026!"


@pytest.fixture
def idp() -> Any:
    f = FakeOidc().start()
    yield f
    f.stop()


def configure(admin: Any, idp: FakeOidc, **kw: Any) -> dict[str, Any]:
    body = {
        "issuer": idp.issuer,
        "client_id": idp.client_id,
        "client_secret": idp.client_secret,
        "redirect_uri": REDIRECT,
        "rolkoppelingen": MAPPINGS,
        **kw,
    }
    r = admin.put("/api/v1/auth/oidc", json=body, headers=idem())
    assert r.status_code == 200, r.text
    r = admin.post("/api/v1/auth/oidc/discover", headers=idem())
    assert r.status_code == 200 and r.json()["resultaat"] == "ok", r.text
    return dict(r.json()["oidc"])


def callback(c: TestClient, idp: FakeOidc, auth_url: str) -> Any:
    cb = urlsplit(idp.authorize(auth_url))
    return c.get(f"{cb.path}?{cb.query}", follow_redirects=False)


def do_testlogin(admin: Any, idp: FakeOidc) -> None:
    r = admin.post("/api/v1/auth/oidc/test")
    assert r.status_code == 200, r.text
    page = callback(admin, idp, r.json()["autorisatie_url"])
    assert page.status_code == 200 and "Testlogin klaar" in page.text, page.text


def d17_getest(admin: Any) -> None:
    w = {"domeinnaam": "auth.thuis.lan", "https": True, "recovery_account": True, "rollen": ["admin", "viewer"]}
    admin.put("/api/v1/decisions/D17/waarde", json={"waarde": w}, headers=idem()).raise_for_status()
    ev = {
        "soort": "handmatige_test",
        "omschrijving": "Testlogin via Authentik geslaagd",
        "resultaat": "geslaagd",
        "uitgevoerd_op": "2026-11-09",
    }
    admin.post("/api/v1/decisions/D17/bewijs", json=ev, headers=idem()).raise_for_status()


def enable(admin: Any, idp: FakeOidc, *, verplicht: bool = False) -> None:
    configure(admin, idp)
    do_testlogin(admin, idp)
    d17_getest(admin)
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True, "verplicht": verplicht}, headers=idem())
    assert r.status_code == 200, r.text


def sso_login(app: Any, idp: FakeOidc, terug: str = "/apps") -> tuple[TestClient, Any]:
    c = TestClient(app, base_url="https://testserver")
    r = c.get("/api/v1/auth/oidc/login", params={"terug": terug}, follow_redirects=False)
    if r.status_code != 302:
        return c, r
    loc = r.headers["location"]
    if not loc.startswith(idp.url):
        return c, r
    cookie = r.headers["set-cookie"]
    assert "hub_oidc=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie.replace("Lax", "lax")
    q = {k: v[0] for k, v in parse_qs(urlsplit(loc).query).items()}
    assert q["code_challenge_method"] == "S256" and len(q["code_challenge"]) == 43 and q["nonce"] and q["state"]
    return c, callback(c, idp, loc)


def fout(resp: Any) -> str:
    assert resp.status_code == 303, (resp.status_code, resp.text[:300])
    return str(parse_qs(urlsplit(resp.headers["location"]).query)["sso_fout"][0])


def test_volledige_flow_pkce_groepen_naar_rol_en_replay(admin: Any, app: Any, idp: FakeOidc) -> None:
    enable(admin, idp)
    c, page = sso_login(app, idp)
    assert page.status_code == 200 and 'http-equiv="refresh"' in page.text and "url=/apps" in page.text
    assert page.headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert "hub_session=" in page.headers.get("set-cookie", "")
    c.headers["X-CSRF-Token"] = c.cookies.get("hub_csrf") or ""
    me = c.get("/api/v1/auth/me").json()["user"]
    assert me["auth_bron"] == "oidc" and me["role"] == "admin" and me["username"] == "leon"
    # Een tweede aanmelding gebruikt hetzelfde account (koppeling op issuer + sub, niet op naam).
    c2, _ = sso_login(app, idp)
    assert c2.get("/api/v1/auth/me").json()["user"]["id"] == me["id"]
    users = [u for u in admin.get("/api/v1/users").json()["items"] if u["auth_bron"] == "oidc"]
    assert len(users) == 1
    # Replay van een callback (zelfde state): geweigerd, geen sessie.
    c3 = TestClient(app, base_url="https://testserver")
    r = c3.get("/api/v1/auth/oidc/login", follow_redirects=False)
    cb = urlsplit(idp.authorize(r.headers["location"]))
    assert c3.get(f"{cb.path}?{cb.query}", follow_redirects=False).status_code == 200
    replay = c3.get(f"{cb.path}?{cb.query}", follow_redirects=False)
    assert fout(replay) == "state_al_gebruikt"
    # Callback in een andere browser (zonder transactiecookie): geweigerd.
    c4 = TestClient(app, base_url="https://testserver")
    r = c4.get("/api/v1/auth/oidc/login", follow_redirects=False)
    other = TestClient(app, base_url="https://testserver")
    cb = urlsplit(idp.authorize(r.headers["location"]))
    assert fout(other.get(f"{cb.path}?{cb.query}", follow_redirects=False)) == "browser_onjuist"
    acties = [a["actie"] for a in admin.get("/api/v1/audit", params={"limit": 200}).json()["items"]]
    assert "auth.oidc.login" in acties and "auth.oidc.tested" in acties
    assert idp.client_secret not in str(admin.get("/api/v1/audit", params={"limit": 200}).json())


@pytest.mark.parametrize(
    ("aanval", "reden"),
    [
        ({"claims_override": {"iss": "https://kwaadwillig.lan/application/o/hub/"}}, "issuer_onjuist"),
        ({"claims_override": {"aud": "andere-client"}}, "audience_onjuist"),
        ({"claims_override": {"aud": ["hub-client", "x"], "azp": "x"}}, "azp_onjuist"),
        ({"claims_override": {"nonce": "verkeerde-nonce"}}, "nonce_onjuist"),
        ({"claims_override": {"exp": int(time.time()) - 3600, "iat": int(time.time()) - 4000}}, "id_token_verlopen"),
        ({"sign_with": "HS256"}, "alg_niet_toegestaan"),
        ({"sign_with": "none"}, "alg_niet_toegestaan"),
        ({"sign_with": "andere_sleutel"}, "handtekening_ongeldig"),
        ({"token_status": 500}, "token_geweigerd"),
    ],
)
def test_foute_tokens_en_storingen_geweigerd(
    admin: Any, app: Any, idp: FakeOidc, aanval: dict[str, Any], reden: str
) -> None:
    enable(admin, idp)
    for k, v in aanval.items():
        setattr(idp, k, v)
    c, resp = sso_login(app, idp)
    assert fout(resp) == reden
    assert "hub_session=" not in resp.headers.get("set-cookie", "")
    assert c.get("/api/v1/auth/me").status_code == 401


def test_rollen_viewer_kind_en_geen_rol(admin: Any, app: Any, idp: FakeOidc) -> None:
    enable(admin, idp)
    idp.user.groups = ["hub-kijkers"]
    viewer, _ = sso_login(app, idp)
    viewer.headers["X-CSRF-Token"] = viewer.cookies.get("hub_csrf") or ""
    assert viewer.get("/api/v1/auth/me").json()["user"]["role"] == "viewer"
    # Een kijker kan nooit iets updaten/stoppen of geheimen ophalen of wijzigen.
    assert viewer.post("/api/v1/inventory/refresh", headers=idem()).status_code == 403
    assert viewer.put("/api/v1/truenas/api-key", json={"api_key": "x" * 20}, headers=idem()).status_code == 403
    assert viewer.get("/api/v1/auth/oidc").status_code == 403
    assert viewer.get("/api/v1/notifications/channels").status_code == 403
    assert (
        viewer.post("/api/v1/auth/password", json={"huidig_wachtwoord": "x", "nieuw_wachtwoord": "y"}).status_code
        == 409
    )
    # Rol 'kind' wint altijd van andere rollen (contract §4.2).
    idp.user.sub, idp.user.preferred_username, idp.user.groups = "sub-kind", "kind1", ["hub-admins", "kinderen"]
    kid, _ = sso_login(app, idp)
    assert kid.get("/api/v1/auth/me").json()["user"]["role"] == "kind"
    # Geen gekoppelde groep → geen toegang én de lopende SSO-sessies van die gebruiker vervallen.
    idp.user.sub, idp.user.preferred_username, idp.user.groups = "authentik-sub-0001", "leon", ["hub-kijkers"]
    before, _ = sso_login(app, idp)
    assert before.get("/api/v1/auth/me").status_code == 200
    idp.user.groups = ["iets-anders"]
    _, resp = sso_login(app, idp)
    assert fout(resp) == "geen_rol"
    assert before.get("/api/v1/auth/me").status_code == 401
    # Groepen alleen via userinfo (niet in het ID-token) werken ook.
    idp.groups_in_id_token, idp.user.groups = False, ["hub-beheer"]
    op, _ = sso_login(app, idp)
    assert op.get("/api/v1/auth/me").json()["user"]["role"] == "operator"


def test_uitloggen_en_intrekken_werken_direct(admin: Any, app: Any, idp: FakeOidc, periodic_run: Any) -> None:
    enable(admin, idp)
    c, _ = sso_login(app, idp)
    c.headers["X-CSRF-Token"] = c.cookies.get("hub_csrf") or ""
    uid = c.get("/api/v1/auth/me").json()["user"]["id"]
    sessions = admin.get("/api/v1/sessions").json()["items"]
    assert any(s["auth_bron"] == "oidc" and s["gebruiker"] == "leon" for s in sessions)
    r = admin.post(f"/api/v1/users/{uid}/sessions/revoke", json={"reden": "test"}, headers=idem())
    assert r.status_code == 200 and r.json()["ingetrokken"] == 1
    assert c.get("/api/v1/auth/me").status_code == 401
    # Uitloggen trekt de sessie in.
    c2, _ = sso_login(app, idp)
    c2.headers["X-CSRF-Token"] = c2.cookies.get("hub_csrf") or ""
    assert c2.post("/api/v1/auth/logout").status_code == 204
    assert c2.get("/api/v1/auth/me").status_code == 401
    # sso.access.revoked van home-control-hub trekt de SSO-sessies van die Authentik-gebruiker in.
    c3, _ = sso_login(app, idp)
    assert c3.get("/api/v1/auth/me").status_code == 200
    hch = service(admin, "home-control-hub")
    post(
        admin,
        hch,
        event(
            "home-control-hub",
            "sso.access.revoked",
            ("authentik_user", "leon"),
            {"change": "deactivated", "roles_lost": ["admin"]},
            classification="sensitive",
        ),
    )
    periodic_run("incidenten_bijwerken")
    assert c3.get("/api/v1/auth/me").status_code == 401
    acties = [a["actie"] for a in admin.get("/api/v1/audit", params={"limit": 200}).json()["items"]]
    assert "auth.oidc.sessions_revoked" in acties and "auth.sessions_revoked_by_admin" in acties
    # Een andere dienst kan dit niet: alleen home-control-hub, en nooit rechten geven.
    c4, _ = sso_login(app, idp)
    other = service(admin, "appstore-en-fork")
    post(admin, other, event("appstore-en-fork", "sso.access.revoked", ("authentik_user", "leon")))
    periodic_run("incidenten_bijwerken")
    assert c4.get("/api/v1/auth/me").status_code == 200
    # Rolwijziging bij een volgende login trekt de oudere SSO-sessies in.
    idp.user.groups = ["hub-kijkers"]
    c5, _ = sso_login(app, idp)
    assert c5.get("/api/v1/auth/me").json()["user"]["role"] == "viewer"
    assert c4.get("/api/v1/auth/me").status_code == 401


def test_sso_access_koppelt_op_issuer_en_sub(admin: Any, app: Any, idp: FakeOidc, periodic_run: Any) -> None:
    """C1.3-ASM-10: sso.access.revoked/changed koppelen op (issuer, sub); alleen zonder sub op de gebruikersnaam.
    Een event trekt alleen sessies in en geeft nooit rechten."""
    enable(admin, idp)
    hch = service(admin, "home-control-hub")
    base = {"issuer": idp.issuer, "preferred_username": "leon"}
    # Zelfde gebruikersnaam maar een andere sub (een ander account bij dezelfde issuer): niets ingetrokken.
    c1, _ = sso_login(app, idp)
    post(admin, hch, event("home-control-hub", "sso.access.revoked", ("authentik_user", "leon"),
                           {**base, "sub": "ander-account-0002"}))  # fmt: skip
    periodic_run("incidenten_bijwerken")
    assert c1.get("/api/v1/auth/me").status_code == 200
    # Andere issuer met dezelfde sub: ook niets.
    post(admin, hch, event("home-control-hub", "sso.access.revoked", ("authentik_user", "leon"),
                           {**base, "issuer": "https://andere-idp.invalid/", "sub": idp.user.sub}))  # fmt: skip
    periodic_run("incidenten_bijwerken")
    assert c1.get("/api/v1/auth/me").status_code == 200
    # sso.access.changed met de juiste (issuer, sub): sessies ingetrokken, maar de rol verandert niet.
    role_before = c1.get("/api/v1/auth/me").json()["user"]["role"]
    post(admin, hch, event("home-control-hub", "sso.access.changed", ("authentik_user", "iemand-anders"),
                           {**base, "sub": idp.user.sub, "groepen": ["hub-beheerders"]}))  # fmt: skip
    periodic_run("incidenten_bijwerken")
    assert c1.get("/api/v1/auth/me").status_code == 401
    c2, _ = sso_login(app, idp)
    assert c2.get("/api/v1/auth/me").json()["user"]["role"] == role_before  # nooit rechten via een event
    # sso.access.revoked met de juiste (issuer, sub) trekt in, ook als de gebruikersnaam intussen anders is.
    nieuw = {"issuer": idp.issuer, "sub": idp.user.sub, "preferred_username": "nieuwe-naam"}
    post(admin, hch, event("home-control-hub", "sso.access.revoked", ("authentik_user", "nieuwe-naam"), nieuw))
    periodic_run("incidenten_bijwerken")
    assert c2.get("/api/v1/auth/me").status_code == 401
    details = [
        a["details"]
        for a in admin.get("/api/v1/audit", params={"limit": 200, "actie": "auth.oidc.sessions_revoked"}).json()[
            "items"
        ]
    ]
    assert {d["koppeling"] for d in details} == {"issuer_sub"} and {d["reden"] for d in details} == {
        "sso.access.revoked",
        "sso.access.changed",
    }


def _breakglass(admin: Any) -> str:
    left = 30 - time.time() % 30
    if left < 6:
        time.sleep(left + 0.2)
    r = admin.post(
        "/api/v1/auth/break-glass/setup",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "username": "nood", "password": NOOD_PW},
    )
    secret = str(r.json()["totp"]["geheim"])
    code = breakglass.totp_at(secret, breakglass.time_step(utcnow()))
    admin.post("/api/v1/auth/break-glass/confirm", json={"totp": code}).raise_for_status()
    return secret


def test_noodlogin_blijft_werken_en_oidc_verplicht(admin: Any, app: Any, idp: FakeOidc) -> None:
    make_user(admin, "lokaal1", "operator")
    enable(admin, idp)
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True, "verplicht": True}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "break_glass_required"
    secret = _breakglass(admin)
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True, "verplicht": True}, headers=idem())
    assert r.status_code == 200 and r.json()["verplicht_effectief"] is True
    assert admin.get("/api/v1/auth/oidc/beschikbaar").json() == {
        "ingeschakeld": True,
        "verplicht": True,
        "login_url": "/api/v1/auth/oidc/login",
        "noodlogin": "Bij nood (SSO werkt niet): de noodlogin van de Hub, alleen vanaf het thuisnetwerk.",
    }
    lokaal = TestClient(app, base_url="https://testserver")
    r = lokaal.post("/api/v1/auth/login", json={"username": "lokaal1", "password": STRONG_PASSWORD})
    assert r.status_code == 403 and r.json()["code"] == "oidc_verplicht"
    # De identity provider valt uit: SSO faalt eerlijk, de noodlogin werkt zonder enige netwerkaanroep.
    idp.stop()
    _, resp = sso_login(app, idp)
    assert fout(resp) == "token_onbereikbaar"
    nood = TestClient(app, base_url="https://testserver", client=("192.168.1.20", 40000))
    code = breakglass.totp_at(secret, breakglass.time_step(utcnow()) + 1)
    r = nood.post("/api/v1/auth/break-glass/login", json={"username": "nood", "password": NOOD_PW, "totp": code})
    assert r.status_code == 200 and r.json()["noodlogin"] is True
    # Werkt het noodaccount niet meer (geroteerd, nog niet bevestigd), dan geldt 'verplicht' niet: geen lock-out.
    admin.post(
        "/api/v1/auth/break-glass/rotate",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": NOOD_PW + "-2"},
    ).raise_for_status()
    assert admin.get("/api/v1/auth/oidc").json()["verplicht_effectief"] is False
    r = lokaal.post("/api/v1/auth/login", json={"username": "lokaal1", "password": STRONG_PASSWORD})
    assert r.status_code == 200


def test_inschakelen_vereist_testlogin_en_d17_en_wijzigen_zet_uit(admin: Any, app: Any, idp: FakeOidc) -> None:
    configure(admin, idp)
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "testlogin_vereist"
    do_testlogin(admin, idp)
    r = admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "gate_authentik_dicht"
    d17_getest(admin)
    assert admin.post("/api/v1/auth/oidc/inschakelen", json={"ingeschakeld": True}, headers=idem()).status_code == 200
    c, _ = sso_login(app, idp)
    assert c.get("/api/v1/auth/me").status_code == 200
    # Een andere groep→rol-koppeling vraagt een nieuwe testlogin en zet SSO uit (sessies ingetrokken).
    cfg = admin.put(
        "/api/v1/auth/oidc",
        json={
            "issuer": idp.issuer,
            "client_id": idp.client_id,
            "redirect_uri": REDIRECT,
            "rolkoppelingen": MAPPINGS[:1],
        },
        headers=idem(),
    ).json()
    assert cfg["ingeschakeld"] is False and cfg["laatste_test"]["actueel"] is False
    assert cfg["client_secret"]["ingesteld"] is True and cfg["client_secret"]["laatste4"] == idp.client_secret[-4:]
    assert idp.client_secret not in str(cfg)
    assert c.get("/api/v1/auth/me").status_code == 401
    _, resp = sso_login(app, idp)
    assert fout(resp) == "sso_uit"
    # Een kijker of operator kan SSO niet instellen.
    make_user(admin, "op-sso", "operator")
    assert login_as(app, "op-sso").put("/api/v1/auth/oidc", json={}, headers=idem()).status_code == 403


def test_discovery_regels(admin: Any, idp: FakeOidc) -> None:
    base = {"client_id": "hub-client", "redirect_uri": REDIRECT}
    r = admin.put(
        "/api/v1/auth/oidc", json={**base, "issuer": "http://auth.thuis.lan/application/o/hub/"}, headers=idem()
    )
    assert r.status_code == 422 and r.json()["code"] == "issuer_niet_https"
    bad = admin.put(
        "/api/v1/auth/oidc", json={**base, "issuer": idp.issuer, "redirect_uri": "https://x.lan/elders"}, headers=idem()
    )
    assert bad.status_code == 422
    admin.put("/api/v1/auth/oidc", json={**base, "issuer": idp.issuer.rstrip("/")}, headers=idem()).raise_for_status()
    r = admin.post("/api/v1/auth/oidc/discover", headers=idem()).json()
    assert r["resultaat"] == "mislukt" and r["reden"] == "issuer_komt_niet_overeen"
    admin.put("/api/v1/auth/oidc", json={**base, "issuer": idp.issuer}, headers=idem()).raise_for_status()
    idp.pkce_methods = ["plain"]
    assert admin.post("/api/v1/auth/oidc/discover", headers=idem()).json()["reden"] == "pkce_niet_ondersteund"
    idp.pkce_methods, idp.algs = ["S256"], ["HS256"]
    assert admin.post("/api/v1/auth/oidc/discover", headers=idem()).json()["reden"] == "alleen_symmetrisch"
    idp.algs = ["RS256"]
    assert admin.post("/api/v1/auth/oidc/discover", headers=idem()).json()["resultaat"] == "ok"
    idp.redirect_to = "https://elders.lan/"
    r = admin.post("/api/v1/auth/oidc/discover", headers=idem()).json()
    assert r["resultaat"] == "mislukt" and r["reden"] == "issuer_onbereikbaar"  # redirects worden nooit gevolgd


def test_jwks_rotatie_wordt_opgehaald_hooguit_eens_per_minuut(
    admin: Any, app: Any, idp: FakeOidc, clean_db: str
) -> None:
    enable(admin, idp)
    idp.rotate_key()
    _, resp = sso_login(app, idp)
    assert fout(resp) == "onbekende_sleutel"  # JWKS net opgehaald: niet meteen opnieuw (geen versterker)
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE oidc_config SET jwks_op = jwks_op - interval '2 minutes'")
    c, page = sso_login(app, idp)
    assert page.status_code == 200 and c.get("/api/v1/auth/me").status_code == 200


def test_sso_advies_van_home_control_hub_nooit_groen(admin: Any, app: Any, fake_nas: Any, worker_once: Any) -> None:
    from fakes.fake_truenas import _app
    from nashelpers import connect, refresh

    assert admin.get("/api/v1/sso/status").json()["reden"] == "home_control_hub_niet_gekoppeld"
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "home-control-hub"})
    enrolled = admin.post(
        "/api/v1/services/enroll", json=enroll_body("home-control-hub", token=r.json()["enrollment_token"])
    ).json()
    hch = FakeHchSso(app.state.keyring().jwt_signing.public_key(), enrolled["service_id"]).start()
    try:
        fake_nas.data["app.query"].append(
            _app(
                "home-control-hub",
                "RUNNING",
                "ghcr.io/lvos04/home-control-hub:0.1.0",
                hch.port,
                30420,
                "/mnt/x",
                "/appdata",
            )
        )
        connect(admin, fake_nas)
        refresh(admin, worker_once)
        st = admin.get("/api/v1/sso/status").json()
        assert st["status"] == "ok" and hch.rejected == []
        assert st["least_privilege"] == {
            "waarde": "deels_gecontroleerd",
            "weergave": "waarschuwing",
            "melding": "Rolrechten niet volledig te controleren.",
        }
        assert st["rechten"]["status"] == "verouderd" and st["rechten"]["weergave"] == "verouderd"
        assert "leon" not in str(st)  # de rechtenkaart zelf wordt niet doorgegeven
        hch.least_privilege, hch.rights_status = "ok", "ok"  # 'ok' bestaat in HCH niet voor least privilege
        st = admin.get("/api/v1/sso/status").json()
        assert st["least_privilege"]["weergave"] == "onbekend" and st["rechten"]["weergave"] == "ok"
        hch.stop()
        st = admin.get("/api/v1/sso/status").json()
        assert st["status"] == "onbekend" and st["least_privilege"]["weergave"] == "onbekend"
    finally:
        hch.stop()
