"""Vrije providerdiagnostiek blijft buiten de antwoorden en de database."""

from typing import Any

import pytest
from conftest import idem
from e2e import test_oidc_sso
from e2e.test_oidc_sso import callback, configure
from fakes.fake_http import Reply, Seen
from sqlalchemy import select

from hub.models import AuditEvent, IdempotencyRecord, OidcConfig

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.mark.parametrize("bron", ["token", "callback"])
def test_providerfout_bewaart_alleen_vaste_reden(
    admin: Any, app: Any, idp: Any, monkeypatch: pytest.MonkeyPatch, bron: str
) -> None:
    configure(admin, idp)
    canary = "ContextmarkeringUitTestprovider"
    echt = idp.handle

    def verzoek(gezien: Seen) -> Reply:
        if gezien.path.endswith("/token/"):
            return Reply(400, {"error": canary})
        return echt(gezien)

    monkeypatch.setattr(idp, "handle", verzoek)
    start = admin.post("/api/v1/auth/oidc/test")
    assert start.status_code == 200
    if bron == "token":
        resultaat = callback(admin, idp, start.json()["autorisatie_url"])
        reden = "token_geweigerd"
    else:
        from urllib.parse import parse_qs, urlsplit

        state = parse_qs(urlsplit(start.json()["autorisatie_url"]).query)["state"][0]
        resultaat = admin.get("/api/v1/auth/oidc/callback", params={"state": state, "error": canary})
        reden = "idp_weigerde"
    assert resultaat.status_code == 400

    headers = idem()
    mutatie = admin.post("/api/v1/auth/oidc/discover", headers=headers)
    herhaling = admin.post("/api/v1/auth/oidc/discover", headers=headers)
    assert mutatie.status_code == herhaling.status_code == 200
    assert mutatie.json() == herhaling.json()
    beheer = admin.get("/api/v1/auth/oidc")
    with app.state.sessionmaker() as db:
        cfg = db.get(OidcConfig, 1)
        audit = db.scalars(select(AuditEvent.details).where(AuditEvent.action == "auth.oidc.tested")).all()
        idempotentie = db.scalars(select(IdempotencyRecord.response_body)).all()
        assert cfg.laatste_test["reden"] == reden
        assert all(canary not in str(deel) for deel in (cfg.laatste_test, audit, idempotentie))
    assert all(canary not in r.text for r in (resultaat, mutatie, herhaling, beheer))
