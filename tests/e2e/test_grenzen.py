"""Toegangscontroles op de lokale Hub met de bestaande simulatorfixtures."""

import uuid

import pytest
from actiehelpers import app_target, schrijfaanroepen, stel_voor
from conftest import login_as, make_user
from e2e.test_acties import stack  # noqa: F401
from e2e.test_catalogus_installeren import _plan, _stel_voor, keten, nas  # noqa: F401
from fakes.fake_truenas import FakeTrueNAS, _app

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def draaiende_apps(omgeving, namen):
    simulator = omgeving.nas
    assert isinstance(simulator, FakeTrueNAS)
    for index, naam in enumerate(namen):
        bestaand = simulator.app(naam)
        if bestaand is None:
            simulator.data["app.query"].append(
                _app(
                    naam,
                    "RUNNING",
                    f"voorbeeld/{naam}:1.0",
                    31240 + index,
                    8096,
                    f"/mnt/testpool/apps/{naam}",
                    "/data",
                    catalog_app=naam,
                )
            )
        elif bestaand["state"] != "RUNNING":
            simulator._set_state(bestaand, "RUNNING")
    assert all(simulator.app(naam)["state"] == "RUNNING" for naam in namen)
    omgeving.vernieuw()


def test_vier_verboden_per_beschermde_app(stack):  # noqa: F811 (pytest-fixture)
    simulator = stack.nas
    regels = stack.admin.get("/api/v1/policy").json()["beschermd"]
    namen = sorted({regel["app"] for regel in regels})
    assert {"emby", "jelly-leon", "jellyfin", "mediaguard", "ai-server-manager", "ai-server-manager-executor"} <= set(
        namen
    )
    draaiende_apps(stack, namen)
    voor = list(schrijfaanroepen(simulator))
    handelingen = {
        "app.stop": {},
        "app.update": {"catalog_version": "1.4.15"},
        "app.rollback": {"catalog_version": "1.4.13"},
        "app.uninstall": {},
    }
    afwijkend = []
    for naam in namen:
        for actie, parameters in handelingen.items():
            antwoord = stel_voor(stack.admin, actie, app_target(naam), parameters)
            if antwoord.status_code != 403 or antwoord.json().get("code") != "actie_geweigerd":
                afwijkend.append((naam, actie, antwoord.status_code, antwoord.json().get("status")))
    aantal = len(namen) * len(handelingen)
    print(f"MATRIX {aantal - len(afwijkend)}/{aantal} HTTP 403; afwijkend={afwijkend}")
    assert schrijfaanroepen(simulator) == voor
    assert not afwijkend, "De beschermingsmatrix moet elke combinatie bij het voorstel weigeren."


def test_geen_herstartvoorstel_voor_de_mediaserver_of_voortgangsdienst(stack):  # noqa: F811 (pytest-fixture)
    namen = ["emby", "jelly-leon", "jellyfin", "mediaguard"]
    draaiende_apps(stack, namen)
    voor = list(schrijfaanroepen(stack.nas))
    uit = {}
    for naam in namen:
        antwoord = stel_voor(stack.admin, "app.restart", app_target(naam))
        uit[naam] = (antwoord.status_code, antwoord.json().get("code"))
    print("HERSTART", uit)
    assert schrijfaanroepen(stack.nas) == voor
    assert all(antwoord == (403, "actie_geweigerd") for antwoord in uit.values())
    assert all(stack.nas.app(naam)["state"] == "RUNNING" for naam in namen)


def test_planrollen_en_onbekende_id(keten):  # noqa: F811 (pytest-fixture)
    beheerder = keten.stack.admin
    app = keten.stack.app
    for naam, rol in [("starter", "operator"), ("collega", "operator"), ("lezer", "viewer"), ("jong", "kind")]:
        make_user(beheerder, naam, rol)
    aangemaakt = _plan(login_as(app, "starter"))
    assert aangemaakt.status_code == 201
    plan = aangemaakt.json()
    pad = "/api/v1/catalog/plans/"
    collega, lezer, jong = (login_as(app, n) for n in ("collega", "lezer", "jong"))
    onbekend = collega.get(pad + str(uuid.uuid4())).status_code
    ongeldig = collega.get(pad + "geen-plan").status_code
    gezien = lezer.get(pad + plan["plan_id"])
    kind = jong.get(pad + plan["plan_id"]).status_code
    gelezen = collega.get(pad + plan["plan_id"]).status_code
    kijkervoorstel = _stel_voor(lezer, plan).status_code
    voorstel = _stel_voor(collega, plan)
    assert voorstel.json().get("actor", {}).get("id") == "collega"
    print(
        f"PLAN onbekend={onbekend} ongeldig={ongeldig} kind={kind} kijker={gezien.status_code}/{kijkervoorstel} "
        f"andere-operator={gelezen}/{voorstel.status_code} status={voorstel.json().get('status')}"
    )
    assert (onbekend, ongeldig, kind, gezien.status_code, kijkervoorstel) == (404, 422, 403, 200, 403)
    assert gelezen == 200 and voorstel.status_code == 201
    assert voorstel.json()["status"] == "wacht_op_goedkeuring"
    assert schrijfaanroepen(keten.stack.nas) == []
