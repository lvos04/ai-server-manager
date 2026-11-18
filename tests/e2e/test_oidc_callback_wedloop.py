"""Een oude OIDC-callback schrijft geen account of sessie na een configuratiewijziging."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import pytest
from conftest import idem
from e2e import test_oidc_sso
from e2e.test_oidc_sso import callback, enable, fout
from fastapi.testclient import TestClient
from sqlalchemy import select

from hub.models import User, WebSession
from hub.oidc import client

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_callback_schrijft_niets_na_uitzetten(admin: Any, app: Any, idp: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    enable(admin, idp)
    browser = TestClient(app, base_url="https://testserver")
    start = browser.get("/api/v1/auth/oidc/login", follow_redirects=False)
    assert start.status_code == 302
    uitgewisseld, verder = Event(), Event()
    echt = client.exchange_code

    def wissel_code(meta: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        antwoord = echt(meta, **kwargs)
        uitgewisseld.set()
        assert verder.wait(20)
        return antwoord

    monkeypatch.setattr(client, "exchange_code", wissel_code)
    with ThreadPoolExecutor(max_workers=1) as executor:
        resultaat = executor.submit(callback, browser, idp, start.headers["location"])
        try:
            assert uitgewisseld.wait(20)
            r = admin.post(
                "/api/v1/auth/oidc/inschakelen",
                json={"ingeschakeld": False},
                headers=idem(),
            )
            assert r.status_code == 200
        finally:
            verder.set()
        antwoord = resultaat.result(timeout=20)

    with app.state.sessionmaker() as db:
        assert not db.scalars(select(User.id).where(User.auth_bron == "oidc")).all()
        assert not db.scalars(select(WebSession.id).where(WebSession.auth_bron == "oidc")).all()
    assert fout(antwoord) == "config_gewijzigd"
    assert "hub_session" not in browser.cookies
