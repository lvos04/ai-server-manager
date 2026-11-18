"""Een beheerwijziging laat een werkende lokale herstelroute over."""

from datetime import timedelta
from typing import Any

import pytest
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import body, noodlogin
from e2e.test_oidc_sso import _breakglass, enable, fout, sso_login
from fastapi.testclient import TestClient
from hub.models import OidcConfig, User
from hub.timeutil import utcnow
from sqlalchemy import select

from conftest import idem

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.mark.parametrize("noodaccount", [False, True])
@pytest.mark.parametrize(
    "actie", ["uitzetten", "wissen", "issuer", "client", "scopes", "duur", "discovery"]
)
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
        antwoord = beheerder.put(
            "/api/v1/auth/oidc", json=body(idp, **updates[actie]), headers=idem()
        )
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
def test_laatste_lokale_beheerder_telt_oidc_niet_mee(
    admin: Any, app: Any, idp: Any, wijziging: dict[str, Any]
) -> None:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    assert sso.get("/api/v1/auth/me").json()["user"]["role"] == "admin"
    gebruiker = admin.get("/api/v1/auth/me").json()["user"]
    r = admin.patch(f"/api/v1/users/{gebruiker['id']}", json=wijziging, headers=idem())
    assert (r.status_code, r.json().get("code")) == (409, "lokale_herstelroute_vereist")
    assert admin.get("/api/v1/auth/me").status_code == 200


def test_automatische_discovery_trekt_ook_zonder_herstelroute_in(
    admin: Any, app: Any, idp: Any
) -> None:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    with app.state.sessionmaker() as db:
        db.scalar(select(User).where(User.username == "beheerder")).disabled = True
        db.get(OidcConfig, 1).discovery_op = utcnow() - timedelta(days=2)
        db.commit()
    idp.algs = ["RS256", "ES256"]
    nieuw = TestClient(app, base_url="https://testserver")
    assert (
        fout(nieuw.get("/api/v1/auth/oidc/login", follow_redirects=False))
        == "sso_gewijzigd"
    )
    assert sso.get("/api/v1/auth/me").status_code == 401
