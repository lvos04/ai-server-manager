"""De aanmeldbron bepaalt wie lokaal beheer en het noodaccount mag wijzigen."""

from typing import Any

import pytest
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import noodlogin
from e2e.test_oidc_sso import NOOD_PW, _breakglass, enable, sso_login

from conftest import STRONG_PASSWORD, idem

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_alleen_lokale_beheerder_of_noodsessie_verleent_beheer(
    admin: Any, app: Any, idp: Any
) -> None:
    totp = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf")
    gebruikers = "/api/v1/users"
    account = {"username": "test-kijker", "password": STRONG_PASSWORD, "role": "viewer"}
    r = sso.post(gebruikers, json=account, headers=idem())
    assert r.status_code == 201
    pad = f"{gebruikers}/{r.json()['id']}"
    assert sso.patch(pad, json={"role": "operator"}, headers=idem()).status_code == 200
    gemaakt = sso.post(
        gebruikers,
        json={**account, "username": "test-beheerder", "role": "admin"},
        headers=idem(),
    )
    bevorderd = sso.patch(pad, json={"role": "admin"}, headers=idem())
    assert [(r.status_code, r.json().get("code")) for r in (gemaakt, bevorderd)] == [
        (403, "lokale_beheerder_vereist"),
        (403, "lokale_beheerder_vereist"),
    ]
    for i, beheerder in enumerate((admin, noodlogin(app, totp))):
        r = beheerder.post(
            gebruikers,
            json={**account, "username": f"test-lokaal-{i}", "role": "admin"},
            headers=idem(),
        )
        assert r.status_code == 201
        r = beheerder.post(
            gebruikers, json={**account, "username": f"test-kijker-{i}"}, headers=idem()
        )
        r.raise_for_status()
        assert (
            beheerder.patch(
                f"{gebruikers}/{r.json()['id']}", json={"role": "admin"}, headers=idem()
            ).status_code
            == 200
        )


def test_sso_beheerder_mag_noodaccount_niet_wijzigen(
    admin: Any, app: Any, idp: Any
) -> None:
    totp = _breakglass(admin)
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf")
    basis = "/api/v1/auth/break-glass"
    nood_id = sso.get(basis).json()["noodaccount"]["id"]
    pad = f"/api/v1/users/{nood_id}"
    acties = [
        sso.patch(pad, json={"disabled": True}, headers=idem()),
        sso.patch(pad, json={"display_name": "Gewijzigd"}, headers=idem()),
        sso.post(
            f"{basis}/setup",
            json={
                "username": "noodtest",
                "password": NOOD_PW,
                "huidig_wachtwoord": NOOD_PW,
            },
        ),
        sso.post(
            f"{basis}/rotate",
            json={"nieuw_wachtwoord": NOOD_PW, "huidig_wachtwoord": NOOD_PW},
        ),
        sso.post(f"{basis}/confirm", json={"totp": "000000"}),
    ]
    assert [(r.status_code, r.json().get("code")) for r in acties] == [
        (403, "lokale_beheerder_vereist")
    ] * len(acties)
    assert noodlogin(app, totp).get("/api/v1/auth/me").status_code == 200
