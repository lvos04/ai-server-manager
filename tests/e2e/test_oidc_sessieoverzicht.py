"""Sessieoverzichten tonen geldige OIDC-sessies en beheerinformatie volgt de aanmeldbron."""

import uuid
from typing import Any

import pytest
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import noodlogin
from e2e.test_oidc_sso import _breakglass, enable, sso_login

from hub.models import WebSession

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_sessieoverzichten_filteren_oude_oidc_generatie(admin: Any, app: Any, idp: Any) -> None:
    enable(admin, idp)
    oud, page = sso_login(app, idp)
    assert page.status_code == 200
    huidig, page = sso_login(app, idp)
    assert page.status_code == 200
    oud_id = oud.get("/api/v1/auth/me").json()["sessie_id"]
    huidig_id = huidig.get("/api/v1/auth/me").json()["sessie_id"]
    lokaal_id = admin.get("/api/v1/auth/me").json()["sessie_id"]
    with app.state.sessionmaker() as db:
        db.get(WebSession, uuid.UUID(oud_id)).oidc_config_versie = None
        db.commit()

    def ids(browser: Any, pad: str) -> set[str]:
        return {s["id"] for s in browser.get(pad).json()["items"]}

    assert ids(huidig, "/api/v1/auth/sessions") == {huidig_id}
    assert ids(admin, "/api/v1/sessions") == {huidig_id, lokaal_id}
    assert oud.get("/api/v1/auth/me").status_code == 401


def test_laatste_vier_zijn_alleen_voor_lokale_beheerder_of_noodsessie(admin: Any, app: Any, idp: Any) -> None:
    totp = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    pad = "/api/v1/auth/oidc"
    metadata = sso.get(pad).json()["client_secret"]
    assert metadata == {"ingesteld": True, "laatste4": None}
    for beheerder in (admin, noodlogin(app, totp)):
        assert beheerder.get(pad).json()["client_secret"]["laatste4"] == idp.client_secret[-4:]
