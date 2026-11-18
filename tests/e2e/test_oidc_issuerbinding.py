"""Een gewijzigd provideradres of client-ID erft geen bestaand clientgeheim."""

from typing import Any

import pytest
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import body
from e2e.test_oidc_sso import enable, sso_login
from fakes.fake_oidc import FakeOidc
from fastapi.testclient import TestClient
from hub.models import OidcConfig
from hub.oidc.service import SECRET_REF

from conftest import idem

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.mark.parametrize("veld", ["issuer", "client_id"])
def test_wissel_zonder_nieuw_geheim_ontkoppelt_kluis(
    admin: Any, app: Any, idp: FakeOidc, veld: str
) -> None:
    enable(admin, idp)
    sso, page = sso_login(app, idp)
    assert page.status_code == 200
    tweede = FakeOidc(client_id="tweede-client").start()
    try:
        http = TestClient(app, base_url="http://testserver")
        http.cookies.set("hub_session", admin.cookies.get("hub_session"))
        http.headers["X-CSRF-Token"] = admin.headers["X-CSRF-Token"]
        r = http.put(
            "/api/v1/auth/oidc",
            json=body(idp, **{veld: getattr(tweede, veld)}),
            headers=idem(),
        )
        assert r.status_code == 200
        assert r.json()["ingeschakeld"] is False
        assert sso.get("/api/v1/auth/me").status_code == 401
        testlogin = http.post("/api/v1/auth/oidc/test")
        assert (testlogin.status_code, testlogin.json().get("code")) == (
            409,
            "oidc_clientgeheim_ontbreekt",
        )
        assert not [
            r
            for r in tweede.requests
            if r.method == "POST" and r.path.endswith("/token/")
        ]
        with app.state.sessionmaker() as db:
            assert db.get(OidcConfig, 1).client_secret_ref is None
            assert app.state.vault().get(db, SECRET_REF) is None
    finally:
        tweede.stop()
