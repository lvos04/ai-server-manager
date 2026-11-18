"""Een gevulde installatie houdt na een upgrade toegang via bestaande lokale gegevens."""

from typing import Any

import pytest
from conftest import STRONG_PASSWORD, idem
from e2e import test_oidc_sso
from e2e.test_oidc_grenzen import noodlogin
from e2e.test_oidc_sso import NOOD_PW, REDIRECT, _breakglass, enable, fout
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from hub import breakglass, migrations
from hub.app import create_app
from hub.models import AuditEvent, OidcConfig, VaultSecret
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


@pytest.mark.parametrize("verwijderen", [True, False], ids=["ontbreekt", "onleesbaar"])
def test_ontbrekende_nood_totp_laat_lokale_aanmelding_toe(
    admin: Any,
    app: Any,
    settings: Any,
    idp: Any,
    caplog: pytest.LogCaptureFixture,
    verwijderen: bool,
) -> None:
    basis = "/api/v1/auth/break-glass"
    reden = "nood_totp_kluisrij_ontbreekt"
    actie = "auth.break_glass.totp_kluisrij_ontbreekt"
    totp = _breakglass(admin)
    enable(admin, idp, verplicht=True)
    assert admin.get(basis).json()["werkend"] is True
    assert admin.get("/api/v1/auth/oidc/beschikbaar").json()["verplicht"] is True

    with app.state.sessionmaker.begin() as db:
        user = breakglass.account(db)
        row = db.scalar(select(VaultSecret).where(VaultSecret.ref == user.totp_secret_ref))
        if verwijderen:
            db.delete(row)
        else:
            row.ciphertext = b"onleesbare rij"

    status = admin.get(basis).json()
    assert status["werkend"] is False and status["oidc_verplicht_mogelijk"] is False
    assert status["reden"] == reden and "ontbreekt of is onleesbaar" in status["uitleg"]
    assert "Instellingen → Noodaccount" in status["uitleg"]
    zelftest = admin.post(f"{basis}/selftest").json()
    assert zelftest["resultaat"] == "niet_ok"
    assert next(c for c in zelftest["controles"] if c["naam"] == "totp")["status"] == "fout"

    def auditregels() -> list[Any]:
        with app.state.sessionmaker() as db:
            return list(db.scalars(select(AuditEvent).where(AuditEvent.action == actie)))

    assert auditregels() == []
    nieuwe_app = create_app(settings)
    with TestClient(nieuwe_app, base_url="https://testserver", client=("192.168.1.20", 40000)) as lokaal:
        beschikbaar = lokaal.get("/api/v1/auth/oidc/beschikbaar").json()
        assert beschikbaar["ingeschakeld"] and beschikbaar["login_url"] and not beschikbaar["verplicht"]
        assert beschikbaar["reden"] == reden
        assert "ontbreekt of is onleesbaar" in beschikbaar["noodlogin"]
        assert "Instellingen → Noodaccount" in beschikbaar["noodlogin"]
        r = lokaal.post(
            "/api/v1/auth/login",
            json={"username": "beheerder", "password": STRONG_PASSWORD},
        )
        assert r.status_code == 200
        lokaal.headers["X-CSRF-Token"] = r.json()["csrf_token"]
        cfg = lokaal.get("/api/v1/auth/oidc").json()
        assert cfg["ingeschakeld"] and cfg["verplicht"] and cfg["client_secret"]["ingesteld"]
        assert not cfg["verplicht_effectief"] and not cfg["noodaccount_werkend"] and cfg["reden"] == reden
        r = lokaal.post(
            "/api/v1/auth/oidc/inschakelen",
            json={"ingeschakeld": True, "verplicht": True},
            headers=idem(),
        )
        assert r.status_code == 409 and r.json()["code"] == "break_glass_required"
        code = breakglass.totp_at(totp, breakglass.time_step(utcnow()))
        r = lokaal.post(
            f"{basis}/login",
            json={"username": "nood", "password": NOOD_PW, "totp": code},
        )
        assert r.status_code == 401
        assert lokaal.get(basis).json()["werkend"] is False
        regels = auditregels()
        assert len(regels) == 1 and regels[0].details == {"reden": reden}
        with TestClient(create_app(settings)):
            assert len(auditregels()) == 1

        rotatie = lokaal.post(
            f"{basis}/rotate",
            json={
                "huidig_wachtwoord": STRONG_PASSWORD,
                "nieuw_wachtwoord": NOOD_PW + "-2",
            },
        )
        assert rotatie.status_code == 200
        nieuw_totp = rotatie.json()["totp"]["geheim"]
        code = breakglass.totp_at(nieuw_totp, breakglass.time_step(utcnow()))
        bevestiging = lokaal.post(f"{basis}/confirm", json={"totp": code})
        assert bevestiging.status_code == 200 and bevestiging.json()["werkend"] is True
        assert lokaal.get("/api/v1/auth/oidc/beschikbaar").json()["verplicht"] is True

    with TestClient(create_app(settings)):
        assert len(auditregels()) == 1
    assert not any(geheim in caplog.text for geheim in (totp, nieuw_totp))
