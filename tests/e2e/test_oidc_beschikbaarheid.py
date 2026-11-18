"""Een gevulde installatie houdt na een upgrade toegang via bestaande lokale gegevens."""

from typing import Any

import pytest
from conftest import STRONG_PASSWORD
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import noodlogin
from e2e.test_oidc_sso import REDIRECT, _breakglass, fout
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from hub import migrations
from hub.app import create_app
from hub.models import AuditEvent, OidcConfig
from hub.oidc import service
from hub.timeutil import utcnow

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_upgrade_publieke_client_laat_lokale_en_noodlogin_toe(admin: Any, app: Any, settings: Any, idp: Any) -> None:
    totp = _breakglass(admin)
    migrations.downgrade(settings.database_url, "0012")
    try:
        with app.state.sessionmaker() as db:
            cfg = service.config(db)
            cfg.issuer, cfg.client_id, cfg.redirect_uri = (
                idp.issuer,
                idp.client_id,
                REDIRECT,
            )
            cfg.discovery = idp.metadata()
            cfg.discovery_op = utcnow()
            cfg.ingeschakeld = cfg.verplicht = True
            db.commit()
    finally:
        migrations.upgrade(settings.database_url)

    nieuwe_app = create_app(settings)
    with TestClient(nieuwe_app, base_url="https://testserver") as lokaal:
        beschikbaar = lokaal.get("/api/v1/auth/oidc/beschikbaar").json()
        assert fout(lokaal.get("/api/v1/auth/oidc/login", follow_redirects=False)) == "oidc_clientgeheim_ontbreekt"
        r = lokaal.post(
            "/api/v1/auth/login",
            json={"username": "beheerder", "password": STRONG_PASSWORD},
        )
        assert r.status_code == 200
        assert (
            beschikbaar["ingeschakeld"],
            beschikbaar["verplicht"],
            beschikbaar["login_url"],
        ) == (False, False, None)
        assert beschikbaar["reden"] == "oidc_clientgeheim_ontbreekt"
        beheer = lokaal.get("/api/v1/auth/oidc").json()
        assert beheer["ingeschakeld"] and beheer["verplicht"] and not beheer["verplicht_effectief"]
        assert beheer["reden"] == "oidc_clientgeheim_ontbreekt"
        assert noodlogin(nieuwe_app, totp).get("/api/v1/auth/me").status_code == 200

    with TestClient(create_app(settings)), app.state.sessionmaker() as db:
        cfg = db.get(OidcConfig, 1)
        assert cfg.ingeschakeld and cfg.verplicht
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.action == "auth.oidc.clientgeheim_ontbreekt")
            )
            == 1
        )
    assert not [r for r in idp.requests if r.method == "POST" and r.path.endswith("/token/")]
