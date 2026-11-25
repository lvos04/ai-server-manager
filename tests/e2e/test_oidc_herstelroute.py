"""Een beheerwijziging laat een werkende lokale herstelroute over."""

from datetime import timedelta
from typing import Any

import pytest
from conftest import idem
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import body, noodlogin
from e2e.test_oidc_sso import NOOD_PW, _breakglass, enable, fout, sso_login
from fakes.adressen import LAN_CLIENT
from fastapi.testclient import TestClient
from sqlalchemy import select

from hub import breakglass
from hub.models import AuditEvent, OidcConfig, User
from hub.timeutil import utcnow

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.mark.parametrize("noodaccount", [False, True])
@pytest.mark.parametrize("actie", ["uitzetten", "wissen", "issuer", "client", "scopes", "duur", "discovery"])
def test_configuratie_intrekken_vraagt_herstelroute(
    admin: Any, app: Any, idp: Any, noodaccount: bool, actie: str
) -> None:
    totp = _breakglass(admin) if noodaccount else None
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf")
    with app.state.sessionmaker() as db:
        # Ook bestaande installaties kunnen al zonder lokale beheerder zijn.
        db.scalar(select(User).where(User.username == "beheerder")).disabled = True
        db.commit()

    cfg = sso.get("/api/v1/auth/oidc").json()
    if actie == "uitzetten":
        antwoord = sso.post(
            "/api/v1/auth/oidc/inschakelen",
            json={"ingeschakeld": False},
            headers=idem(),
        )
    elif actie == "discovery":
        idp.algs = ["RS256", "ES256"]
        antwoord = sso.post("/api/v1/auth/oidc/discover", headers=idem())
    else:
        beheerder = noodlogin(app, totp) if actie == "wissen" and totp else sso
        if actie == "wissen" and not totp:
            # Een al bekende noodsessie kan hier ontbreken. Laat alleen voor deze proef de lokale sessie
            # een beheerder zonder bruikbaar wachtwoord voorstellen.
            with app.state.sessionmaker() as db:
                lokaal = db.scalar(select(User).where(User.username == "beheerder"))
                lokaal.disabled, lokaal.password_hash = False, "!test-zonder-wachtwoord"
                db.commit()
            beheerder = admin
        updates = {
            "wissen": {"client_secret_wissen": True},
            "issuer": {"issuer": idp.issuer + "verplaatst/"},
            "client": {"client_id": "andere-client"},
            "scopes": {"scopes": "openid profile"},
            "duur": {"sessie_minuten": 60},
        }
        antwoord = beheerder.put("/api/v1/auth/oidc", json=body(idp, **updates[actie]), headers=idem())
    if totp:
        assert antwoord.status_code == 200
        assert sso.get("/api/v1/auth/me").status_code == 401
    else:
        assert (antwoord.status_code, antwoord.json().get("code")) == (
            409,
            "lokale_herstelroute_vereist",
        )
        assert sso.get("/api/v1/auth/me").status_code == 200
    assert cfg.get("lokale_herstelroute") is noodaccount


@pytest.mark.parametrize("wijziging", [{"disabled": True}, {"role": "viewer"}])
def test_laatste_lokale_beheerder_telt_oidc_niet_mee(admin: Any, app: Any, idp: Any, wijziging: dict[str, Any]) -> None:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    assert sso.get("/api/v1/auth/me").json()["user"]["role"] == "admin"
    gebruiker = admin.get("/api/v1/auth/me").json()["user"]
    r = admin.patch(f"/api/v1/users/{gebruiker['id']}", json=wijziging, headers=idem())
    assert (r.status_code, r.json().get("code")) == (409, "lokale_herstelroute_vereist")
    assert admin.get("/api/v1/auth/me").status_code == 200


def test_automatische_discovery_trekt_ook_zonder_herstelroute_in(admin: Any, app: Any, idp: Any) -> None:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    with app.state.sessionmaker() as db:
        db.scalar(select(User).where(User.username == "beheerder")).disabled = True
        db.get(OidcConfig, 1).discovery_op = utcnow() - timedelta(days=2)
        db.commit()
    idp.algs = ["RS256", "ES256"]
    nieuw = TestClient(app, base_url="https://testserver")
    assert fout(nieuw.get("/api/v1/auth/oidc/login", follow_redirects=False)) == "sso_gewijzigd"
    assert sso.get("/api/v1/auth/me").status_code == 401


def _alleen_sso_en_noodaccount(admin: Any, app: Any, idp: Any, totp: str) -> tuple[TestClient, TestClient]:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf")
    lokaal_id = admin.get("/api/v1/auth/me").json()["user"]["id"]
    assert sso.patch(f"/api/v1/users/{lokaal_id}", json={"disabled": True}, headers=idem()).status_code == 200
    assert sso.get("/api/v1/auth/oidc").json()["lokale_herstelroute"] is True
    return sso, noodlogin(app, totp)


def _roteer_noodaccount(nood: TestClient) -> str:
    antwoord = nood.post(
        "/api/v1/auth/break-glass/rotate",
        json={"huidig_wachtwoord": NOOD_PW, "nieuw_wachtwoord": NOOD_PW + "-rotatie"},
    )
    assert antwoord.status_code == 200
    return str(antwoord.json()["totp"]["geheim"])


def _bevestig_rotatie_via_noodlogin(app: Any, sso: TestClient, nieuw_totp: str) -> None:
    nieuw = TestClient(app, base_url="https://testserver", client=(LAN_CLIENT, 40001))
    gegevens = {
        "username": "nood",
        "password": NOOD_PW + "-rotatie",
        "totp": breakglass.totp_at(nieuw_totp, breakglass.time_step(utcnow())),
    }
    status = sso.get("/api/v1/auth/break-glass").json()
    assert status["noodaccount"]["totp_wacht_op_bevestiging"] is True
    assert nieuw.post("/api/v1/auth/break-glass/login", json={**gegevens, "password": NOOD_PW}).status_code == 401
    assert sso.get("/api/v1/auth/break-glass").json()["noodaccount"]["totp_wacht_op_bevestiging"] is True
    assert nieuw.post("/api/v1/auth/break-glass/login", json=gegevens).status_code == 200
    status = sso.get("/api/v1/auth/break-glass").json()
    assert status["noodaccount"]["totp_wacht_op_bevestiging"] is False
    assert status["noodaccount"]["rotatie_vereist"] is True
    assert sso.get("/api/v1/auth/oidc").json()["lokale_herstelroute"] is True
    assert nieuw.post("/api/v1/auth/break-glass/login", json=gegevens).status_code == 401
    with app.state.sessionmaker() as db:
        bevestigingen = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.break_glass.confirmed")).all()
        assert len(bevestigingen) == 2


def test_c1_rotatie_zonder_bevestiging_laat_noodlogin_toe(admin: Any, app: Any, idp: Any) -> None:
    sso, nood = _alleen_sso_en_noodaccount(admin, app, idp, _breakglass(admin))
    nieuw_totp = _roteer_noodaccount(nood)
    assert nood.post("/api/v1/auth/logout").status_code == 204
    _bevestig_rotatie_via_noodlogin(app, sso, nieuw_totp)


@pytest.mark.parametrize("alle_sessies", [False, True])
def test_c4_sso_beheerder_kan_noodsessies_niet_intrekken(admin: Any, app: Any, idp: Any, alle_sessies: bool) -> None:
    sso, nood = _alleen_sso_en_noodaccount(admin, app, idp, _breakglass(admin))
    nieuw_totp = _roteer_noodaccount(nood)
    nood_id = nood.get("/api/v1/auth/me").json()["user"]["id"]
    sessie_id = next(s["id"] for s in nood.get("/api/v1/auth/sessions").json()["items"] if s["huidige"])
    if alle_sessies:
        antwoord = sso.post(
            f"/api/v1/users/{nood_id}/sessions/revoke",
            json={"reden": "test"},
            headers=idem(),
        )
    else:
        antwoord = sso.post(f"/api/v1/auth/sessions/{sessie_id}/revoke", headers=idem())
    assert (antwoord.status_code, antwoord.json().get("code")) == (
        403,
        "lokale_beheerder_vereist",
    )
    assert nood.get("/api/v1/auth/me").status_code == 200
    _bevestig_rotatie_via_noodlogin(app, sso, nieuw_totp)


def test_herbevestiging_blokkeert_geen_noodlogin_en_laatste_noodaccount_blijft_aan(
    admin: Any, app: Any, idp: Any, settings: Any
) -> None:
    totp = _breakglass(admin)
    with app.state.sessionmaker() as db:
        account = breakglass.account(db)
        account.break_glass_reconfirmed_at = utcnow() - timedelta(days=settings.break_glass_reconfirm_days + 1)
        db.commit()
    assert admin.get("/api/v1/auth/break-glass").json()["noodaccount"]["herbevestiging_nodig"] is True
    sso, nood = _alleen_sso_en_noodaccount(admin, app, idp, totp)
    nood_id = nood.get("/api/v1/auth/me").json()["user"]["id"]
    antwoord = nood.patch(f"/api/v1/users/{nood_id}", json={"disabled": True}, headers=idem())
    assert (antwoord.status_code, antwoord.json().get("code")) == (409, "lokale_herstelroute_vereist")
    assert nood.get("/api/v1/auth/me").status_code == 200
    assert sso.get("/api/v1/auth/oidc").json()["lokale_herstelroute"] is True
