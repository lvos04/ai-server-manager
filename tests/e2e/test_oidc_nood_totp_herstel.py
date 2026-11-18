"""Een ontbrekende nood-TOTP mag de enige lokale beheerroute niet wegnemen."""

from typing import Any

import pytest
from conftest import STRONG_PASSWORD, idem
from e2e import test_oidc_sso
from e2e.test_oidc_sso import NOOD_PW, _breakglass, enable, sso_login
from fastapi.testclient import TestClient
from sqlalchemy import select

from hub import __main__ as hub_cli
from hub import breakglass
from hub.models import AuditEvent, User, VaultSecret
from hub.timeutil import utcnow

idp = test_oidc_sso.idp
pytestmark = [pytest.mark.e2e, pytest.mark.integration]
OIDC = "/api/v1/auth/oidc"
NOOD = "/api/v1/auth/break-glass"
VERPLICHT = {"ingeschakeld": True, "verplicht": True}


def _sso_beheerder(app: Any, idp: Any) -> TestClient:
    sso, pagina = sso_login(app, idp)
    assert pagina.status_code == 200
    sso.headers["X-CSRF-Token"] = sso.cookies.get("hub_csrf")
    return sso


def _verwijder_wachtwoorddigest(app: Any) -> None:
    with app.state.sessionmaker.begin() as db:
        beheerder = db.scalar(select(User).where(User.username == "beheerder"))
        assert beheerder is not None
        beheerder.password_hash = beheerder.password_hash.rsplit("$", 1)[0] + "$"


def test_oidc_verplicht_weigert_noodaccount_als_enige_lokale_beheerroute(admin: Any, app: Any, idp: Any) -> None:
    _breakglass(admin)
    enable(admin, idp)
    sso = _sso_beheerder(app, idp)
    lokaal_id = admin.get("/api/v1/auth/me").json()["user"]["id"]
    sso.patch(f"/api/v1/users/{lokaal_id}", json={"disabled": True}, headers=idem()).raise_for_status()

    antwoord = sso.post(f"{OIDC}/inschakelen", json=VERPLICHT, headers=idem())
    assert (antwoord.status_code, antwoord.json().get("code")) == (
        409,
        "lokale_beheerder_ontbreekt",
    )
    assert sso.get(OIDC).json()["verplicht"] is False


def test_oidc_verplicht_weigert_lokale_beheerder_zonder_wachtwoorddigest(admin: Any, app: Any, idp: Any) -> None:
    _breakglass(admin)
    enable(admin, idp)
    sso = _sso_beheerder(app, idp)
    _verwijder_wachtwoorddigest(app)
    antwoord = sso.post(f"{OIDC}/inschakelen", json=VERPLICHT, headers=idem())

    assert (antwoord.status_code, antwoord.json().get("code")) == (409, "lokale_beheerder_ontbreekt")
    status = sso.get(OIDC).json()
    assert status["noodaccount_werkend"] and not status["lokale_beheerder_aanwezig"] and not status["verplicht"]


def test_consoleherstelt_bij_ontbrekende_nood_totp_en_wachtwoorddigest(
    admin: Any, app: Any, idp: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _breakglass(admin)
    enable(admin, idp, verplicht=True)
    sso = _sso_beheerder(app, idp)
    _verwijder_wachtwoorddigest(app)
    with app.state.sessionmaker.begin() as db:
        nood = breakglass.account(db)
        rij = db.scalar(select(VaultSecret).where(VaultSecret.ref == nood.totp_secret_ref))
        db.delete(rij)

    status = sso.get(OIDC).json()
    assert status["verplicht"] and not status["verplicht_effectief"]
    with TestClient(app, base_url="https://testserver") as lokaal:
        oud = lokaal.post("/api/v1/auth/login", json={"username": "beheerder", "password": STRONG_PASSWORD})
        assert oud.status_code == 401

        monkeypatch.setattr(hub_cli, "get_settings", lambda: settings)
        monkeypatch.setattr("getpass.getpass", lambda _prompt: STRONG_PASSWORD)
        assert hub_cli.main(["herstel-lokale-beheerder", "herstelbeheer"]) == 0
        assert hub_cli.main(["herstel-lokale-beheerder", "tweede-herstelbeheer"]) != 0

        nieuw = lokaal.post("/api/v1/auth/login", json={"username": "herstelbeheer", "password": STRONG_PASSWORD})
        assert nieuw.status_code == 200
    assert not status["lokale_herstelroute"]
    assert sso.get(OIDC).json()["lokale_herstelroute"]
    with app.state.sessionmaker() as db:
        regels = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.lokale_beheerder_hersteld")).all()
        assert len(regels) == 1 and regels[0].details == {"reden": breakglass.TOTP_UNAVAILABLE}


@pytest.mark.parametrize("wijziging", [{"disabled": True}, {"role": "viewer"}])
def test_oidc_verplicht_beschermt_laatste_gewone_lokale_beheerder(
    admin: Any, app: Any, idp: Any, wijziging: dict[str, Any]
) -> None:
    _breakglass(admin)
    enable(admin, idp, verplicht=True)
    sso = _sso_beheerder(app, idp)
    lokaal_id = admin.get("/api/v1/auth/me").json()["user"]["id"]

    antwoord = sso.patch(f"/api/v1/users/{lokaal_id}", json=wijziging, headers=idem())
    assert (antwoord.status_code, antwoord.json().get("code")) == (
        409,
        "lokale_beheerder_ontbreekt",
    )
    assert admin.get("/api/v1/auth/me").json()["user"]["role"] == "admin"
    assert sso.get(OIDC).json()["verplicht_effectief"] is True


@pytest.mark.parametrize("verwijderen", [True, False], ids=["ontbreekt", "onleesbaar"])
def test_bestaande_installatie_zonder_lokale_beheerder_herstelt_via_console(
    admin: Any,
    app: Any,
    idp: Any,
    settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verwijderen: bool,
) -> None:
    oude_totp = _breakglass(admin)
    enable(admin, idp, verplicht=True)
    sso = _sso_beheerder(app, idp)
    lokaal_id = admin.get("/api/v1/auth/me").json()["user"]["id"]
    with app.state.sessionmaker.begin() as db:
        # Boots een installatie na die vóór deze wijziging de lokale beheerder kwijtraakte.
        db.scalar(select(User).where(User.username == "beheerder")).disabled = True

    monkeypatch.setattr(hub_cli, "get_settings", lambda: settings)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: STRONG_PASSWORD)
    herstel = ["herstel-lokale-beheerder", "herstelbeheer"]
    assert hub_cli.main(herstel) != 0

    with app.state.sessionmaker.begin() as db:
        nood = breakglass.account(db)
        rij = db.scalar(select(VaultSecret).where(VaultSecret.ref == nood.totp_secret_ref))
        if verwijderen:
            db.delete(rij)
        else:
            rij.ciphertext = b"onleesbare rij"

    status = sso.get(OIDC).json()
    assert status["verplicht"] and not status["verplicht_effectief"]
    assert not status["noodaccount_werkend"] and not status["lokale_herstelroute"]
    publiek = sso.get(f"{OIDC}/beschikbaar").json()
    assert publiek["ingeschakeld"] and not publiek["verplicht"]
    assert "herstel-lokale-beheerder" in publiek["noodlogin"]
    assert "Instellingen → Noodaccount" not in publiek["noodlogin"]
    noodclient = TestClient(app, base_url="https://testserver", client=(breakglass.SELFTEST_INSIDE, 40000))
    oude_code = breakglass.totp_at(oude_totp, breakglass.time_step(utcnow()))
    antwoord = noodclient.post(f"{NOOD}/login", json={"username": "nood", "password": NOOD_PW, "totp": oude_code})
    assert antwoord.status_code == 401
    heractiveren = sso.patch(f"/api/v1/users/{lokaal_id}", json={"disabled": False}, headers=idem())
    roteren = sso.post(
        f"{NOOD}/rotate",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": NOOD_PW},
    )
    assert [(r.status_code, r.json().get("code")) for r in (heractiveren, roteren)] == [
        (403, "lokale_beheerder_vereist"),
    ] * 2

    assert hub_cli.main(["herstel-lokale-beheerder", "beheerder"]) != 0
    assert hub_cli.main(herstel) == 0
    assert hub_cli.main(["herstel-lokale-beheerder", "tweede-herstelbeheer"]) != 0
    uitvoer = capsys.readouterr()
    assert STRONG_PASSWORD not in uitvoer.out + uitvoer.err
    assert sso.get(OIDC).json()["lokale_herstelroute"] is True
    lokaal = TestClient(app, base_url="https://testserver")
    gegevens = {"username": "herstelbeheer", "password": STRONG_PASSWORD}
    login = lokaal.post("/api/v1/auth/login", json=gegevens)
    assert login.status_code == 200
    lokaal.headers["X-CSRF-Token"] = login.json()["csrf_token"]

    rotatie = lokaal.post(
        f"{NOOD}/rotate",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": NOOD_PW},
    )
    assert rotatie.status_code == 200
    nieuwe_totp = rotatie.json()["totp"]["geheim"]
    code = breakglass.totp_at(nieuwe_totp, breakglass.time_step(utcnow()))
    assert lokaal.post(f"{NOOD}/confirm", json={"totp": code}).status_code == 200
    login = lokaal.post("/api/v1/auth/login", json=gegevens)
    assert (login.status_code, login.json().get("code")) == (403, "oidc_verplicht")
    assert sso.get(OIDC).json()["verplicht_effectief"] is True
    nieuwe_code = breakglass.totp_at(nieuwe_totp, breakglass.time_step(utcnow()) + 1)
    antwoord = noodclient.post(f"{NOOD}/login", json={"username": "nood", "password": NOOD_PW, "totp": nieuwe_code})
    assert antwoord.status_code == 200

    with app.state.sessionmaker() as db:
        regels = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.lokale_beheerder_hersteld")).all()
        assert len(regels) == 1 and regels[0].details == {"reden": breakglass.TOTP_UNAVAILABLE}
