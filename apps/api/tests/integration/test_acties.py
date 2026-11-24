"""Acties aan de Hub-kant zonder executor: weigeringen, blokkades, rollen, idempotentie en ``notification.send``
(contract 1.3 §8; B01-007, B02-005; EX18, EX27). De keten mét executor staat in ``tests/e2e/test_acties.py``."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import (
    HOST,
    Stack,
    app_target,
    audit_acties,
    bouw_stack,
    haal,
    hashes,
    keur_goed,
    schrijfaanroepen,
    stel_voor,
    voer_uit,
)
from conftest import idem, login_as, make_user
from executorhelpers import write_nas
from fakes.fake_gotify import FakeGotify
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import DIGEST, install_params

from hub.models import ActionRequest, IdempotencyRecord
from hub.timeutil import iso, utcnow

pytestmark = pytest.mark.integration
TOKEN = "gotify-app-token-voor-test"


def test_p2_leeslijsten_geven_het_bronmoment_ook_bij_een_lege_selectie(admin: Any) -> None:
    for pad, tijdveld, lijstveld in (
        ("actions?status=wacht_op_goedkeuring", "bijgewerkt_op", "items"),
        ("events?source_app=home-control-hub", "observed_at", "items"),
        ("backups/herstelpunten", "observed_at", "items"),
        ("backups/restore-tests", "observed_at", "items"),
        ("backups/rampenscenario", "observed_at", "laatste_hersteltests"),
        ("backups/self", "observed_at", "items"),
        ("monitoring/monitorplan", "observed_at", "items"),
        ("policy", "observed_at", None),
    ):
        begin = iso(utcnow())
        antwoord = admin.get(f"/api/v1/{pad}")
        assert antwoord.status_code == 200, pad
        data = antwoord.json()
        assert begin <= data[tijdveld] <= iso(utcnow()), pad
        if lijstveld:
            assert data[lijstveld] == [], pad


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    if fake._thread is not None and fake._thread.is_alive():  # een test kan de NAS zelf al hebben gestopt
        fake.stop()


@pytest.fixture
def stack(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Stack:
    """Hub + fake TrueNAS (alleen-lezen), **zonder** executor."""
    return bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        met_executor=False,
    )


def _voorstel(c: Any, action_id: str, target: dict[str, Any], parameters: dict[str, Any] | None = None) -> Any:
    """Voorstel met een eigen sleutel, zodat ook een geweigerd voorstel daarna is op te vragen."""
    key = str(uuid.uuid4())
    body = {"action_id": action_id, "target": target, "parameters": parameters or {}, "reason": "test"}
    return key, c.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})


def _kloon(nas: FakeTrueNAS, naam: str, image: str | None = None) -> None:
    app = copy.deepcopy(nas.app("my-house"))
    app["name"] = app["id"] = naam
    if image is not None:
        app["active_workloads"]["images"] = [image]
        for c in app["active_workloads"]["container_details"]:
            c["image"] = image
    nas.data["app.query"].append(app)


# ---------------------------------------------------------------------- beleid
def test_beleid_is_leesbaar_en_ingebakken(stack: Stack) -> None:
    make_user(stack.admin, "vera", "viewer")
    r = login_as(stack.app, "vera").get("/api/v1/policy")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["policy_hash"].startswith("sha256:") and len(b["policy_hash"]) == 71
    acties = {a["action_id"]: a for a in b["acties"]}
    assert acties["app.restart"]["risk_class"] == "R1" and acties["app.restart"]["risk_class_kritiek"] == "R2"
    assert acties["app.install"]["risk_class"] == "R2" and acties["app.install"]["goedkeuring_nodig"] is True
    assert acties["app.update"]["requires_backup"] is True and acties["notification.send"]["risk_class"] == "R0"
    assert "boiler_verboden" in [v["code"] for v in b["verboden"]]
    assert {"pool_niet_gezond", "backup_gate_rood", "noodstop_actief"} <= {d["code"] for d in b["dynamisch"]}
    assert "adguard-home" in b["kritieke_apps"] and "emby" in [x["app"] for x in b["beschermd"]]
    # Elk voorstel draagt dezelfde policy_hash.
    v = stel_voor(stack.admin, "app.restart", app_target("my-house")).json()
    assert v["policy_hash"] == b["policy_hash"]


def test_beleid_noemt_de_engine_regels_en_r2_voor_het_stoppen_van_een_custom_app(stack: Stack) -> None:
    """S-P2-010, bouwpunt 6a (R-VEILIG-5 van S-P2-005): ``GET /api/v1/policy`` toont niet alleen de yaml-klasse.
    ``app.stop`` is R1 voor een catalogusapp, maar R2 met goedkeuring voor een Custom App (``STOP-EENRICHTING``), en de
    weergave noemt de twee vaste engine-regels. De weergave rekent dat met de engine zelf uit; een echt voorstel voor
    een Custom App (``my-house``) krijgt dezelfde klasse."""
    b = stack.admin.get("/api/v1/policy").json()
    acties = {a["action_id"]: a for a in b["acties"]}
    stop = acties["app.stop"]
    assert (stop["risk_class"], stop["goedkeuring_nodig"]) == ("R1", False)
    assert (stop["risk_class_custom_app"], stop["goedkeuring_nodig_custom_app"]) == ("R2", True)
    assert (
        acties["app.start"]["risk_class_custom_app"] == "R1" and not acties["app.start"]["goedkeuring_nodig_custom_app"]
    )
    herstart = acties["app.restart"]
    assert herstart["risk_class_custom_app"] == "R1" and herstart["goedkeuring_nodig_custom_app"] is True
    assert herstart["goedkeuring_nodig"] is True
    assert acties["notification.send"]["risk_class_custom_app"] is None  # geen app als doel
    regels = {r["id"]: r for r in b["engine_regels"]}
    assert set(regels) == {"STOP-EENRICHTING", "DOEL-ONHERKENBAAR"}
    assert regels["STOP-EENRICHTING"]["acties"] == ["app.stop"]
    assert (regels["STOP-EENRICHTING"]["risk_class"], regels["STOP-EENRICHTING"]["goedkeuring_nodig"]) == ("R2", True)
    assert regels["DOEL-ONHERKENBAAR"]["code"] == "doel_niet_herkenbaar"
    onherkenbaar = regels["DOEL-ONHERKENBAAR"]["acties"]
    assert "app.stop" in onherkenbaar and "app.install" not in onherkenbaar
    assert all(r["reden"] for r in regels.values())
    v = stel_voor(stack.admin, "app.stop", app_target("my-house")).json()
    assert v["risk_class"] == stop["risk_class_custom_app"] and "STOP-EENRICHTING" in v["rule_ids"]


def test_doel_zonder_herkenning_is_na_een_stop_niet_herkenbaar() -> None:
    """S-P2-010, bouwpunt 6c: de standaardherkenning van een :class:`Doel` (doelen zonder app) zegt "na een stop niet
    herkenbaar", dicht bij twijfel; met die herkenning is ``app.stop`` R2."""
    from asm_policy import load_policy
    from asm_policy.engine import classify

    from hub.actions.doel import Doel

    d = Doel("app", "x", "etag", True)
    assert d.herkend_als.na_stop_herkenbaar is False
    c = classify(
        load_policy(),
        action_id="app.stop",
        target=app_target("x"),
        parameters={},
        actor_type="user",
        herkend_als=d.herkend_als,
    )
    assert c.risk_class == "R2" and "STOP-EENRICHTING" in c.rule_ids


# ---------------------------------------------------------------------- weigeringen (statisch beleid)
@pytest.mark.parametrize(
    ("action_id", "target", "parameters"),
    [
        ("boiler.set", {"host_id": HOST}, {}),
        ("app.restart", {"host_id": HOST, "app_id": "boiler-regelaar"}, {}),
        ("app.restart", {"host_id": HOST, "app_id": "warm-water"}, {}),
        (
            "app.install",
            {"host_id": HOST, "app_id": "demo-app"},
            {"app_create": {"values": {"envs": [{"name": "KETEL"}]}}},
        ),
        ("zfs.snapshot.create", {"host_id": HOST, "dataset": "testpool/apps/water_heater"}, {"naam": "x"}),
    ],
)
def test_boiler_wordt_altijd_geweigerd(
    stack: Stack, action_id: str, target: dict[str, Any], parameters: dict[str, Any]
) -> None:
    """EX27: boiler in actie, doel of parameters → geweigerd, ook voor een beheerder en ook met goedkeuring."""
    admin = stack.admin
    key, r = _voorstel(admin, action_id, target, parameters)
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "boiler_verboden" in [b["code"] for b in r.json()["details"]["blokkades"]]
    v = haal(admin, key)
    assert v["status"] == "geweigerd" and v["risk_class"] == "R3" and v["preview"] is None
    assert "boiler_verboden" in [b["code"] for b in v["blokkades"]]
    # De parameterwaarden van een geweigerd voorstel worden niet bewaard (alleen hun hash).
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(key))
        assert rij is not None and rij.parameters == {} and rij.gestart_op is None
    # Een geweigerd voorstel is niet goed te keuren en niet uit te voeren.
    hashes = {"preview_hash": "sha256:" + "0" * 64, "resource_etag": "x", "policy_hash": v["policy_hash"]}
    r = admin.post(f"/api/v1/actions/{key}/approve", json=hashes, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    r = voer_uit(admin, key)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    assert "action.proposal.refused" in audit_acties(stack.app) and schrijfaanroepen(stack.nas) == []


def test_een_melding_over_de_boiler_mag_maar_schakelt_niets(stack: Stack) -> None:
    """Bewaking is geen bediening: vrije meldingstekst is geen doel."""
    r = stel_voor(
        stack.admin, "notification.send", {"host_id": HOST}, {"titel": "Boiler", "tekst": "De boiler is warm."}
    )
    assert r.status_code == 201 and r.json()["risk_class"] == "R0", r.text


@pytest.mark.parametrize(
    ("action_id", "status", "code", "klasse"),
    [
        ("shell.exec", 403, "actie_geweigerd", "R3"),
        ("docker.exec", 403, "actie_geweigerd", "R3"),
        ("pool.dataset.delete", 403, "actie_geweigerd", "R3"),
        ("app.onbekend", 403, "actie_niet_toegestaan", "R3"),
        ("mediaguard.repair.start", 501, "capability_unavailable", "R3"),
        ("my_house.device.set", 501, "capability_unavailable", "R3"),
        # MediaGuard-acties blijven gereserveerd tot BG-05 en P3-02 (§8, tweede tabel; S-P2-080).
        ("mediaguard.wanted.search", 501, "capability_unavailable", "R3"),
        ("mediaguard.quarantine.restore", 501, "capability_unavailable", "R3"),
    ],
)
def test_verboden_onbekende_en_gereserveerde_acties(
    stack: Stack, action_id: str, status: int, code: str, klasse: str
) -> None:
    key, r = _voorstel(stack.admin, action_id, {"host_id": HOST}, {})
    assert r.status_code == status and r.json()["code"] == code, r.text
    # Ook met risk_claim R0 (EX18) verandert er niets: de claim wordt alleen bewaard.
    r2 = stel_voor(stack.admin, action_id, {"host_id": HOST}, {}, risk_claim="R0")
    assert r2.status_code == status and r2.json()["code"] == code, r2.text
    v = haal(stack.admin, key)
    assert v["status"] == "geweigerd" and v["risk_class"] == klasse and v["risk_claim"] is None
    assert voer_uit(stack.admin, key).json()["code"] == "status_past_niet"
    assert schrijfaanroepen(stack.nas) == []


@pytest.mark.parametrize(
    ("naam", "image"),
    [("emby", None), ("mijn-media", "docker.io/emby/embyserver:4.9.1.80"), ("emby", "docker.io/jellyfin/jellyfin:10")],
)
@pytest.mark.parametrize("action_id", ["app.stop", "app.restart", "app.uninstall"])
def test_emby_wordt_nooit_door_het_platform_aangeraakt(
    stack: Stack, naam: str, image: str | None, action_id: str
) -> None:
    """Besluit van de gebruiker: Emby blijft tot hij het zelf verwijdert. Herkend op naam én op image."""
    _kloon(stack.nas, naam, image)
    key, r = _voorstel(stack.admin, action_id, app_target(naam))
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [b["code"] for b in r.json()["details"]["blokkades"]]
    assert haal(stack.admin, key)["status"] == "geweigerd"


def _catalogus_install(naam: str, catalogus: str) -> dict[str, Any]:
    params = install_params(naam)
    params["app_create"].update(catalog_app=catalogus, version="1.0.0", values={})
    params["manifest"] = {"app_id": naam, "install_reason": "proef met een catalogusapp"}
    return params


def test_een_tweede_emby_installeren_onder_een_andere_naam_wordt_geweigerd(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HARDE EIS (S-P2-010, bouwpunt 6g): ``app.install`` met ``catalog_app: "emby"`` onder een andere naam valt onder
    APP-EMBY, ook voor een beheerder. Tegenproef: een andere catalogusapp onder een eigen naam wordt gewoon voorgesteld
    (R2, met goedkeuring)."""
    key, r = _voorstel(stack.admin, "app.install", app_target("mediaspeler"), _catalogus_install("mediaspeler", "emby"))
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [b["code"] for b in r.json()["details"]["blokkades"]], r.text
    assert haal(stack.admin, key)["status"] == "geweigerd"
    from asm_policy import params

    monkeypatch.setattr(params, "catalogusinstallatie", lambda *_a: [])
    r = stel_voor(stack.admin, "app.install", app_target("fotos"), _catalogus_install("fotos", "immich"))
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text
    assert r.json()["status"] == "wacht_op_goedkeuring" and r.json()["preview"]["herkend_als"] == "immich"
    # Alleen de dynamische blokkade van deze opstelling zonder executor; geen statische weigering.
    assert [b["code"] for b in r.json()["blokkades"]] == ["executor_niet_gekoppeld"], r.text
    assert schrijfaanroepen(stack.nas) == []


def _nest(diepte: int, blad: Any) -> Any:
    v = blad
    for i in range(diepte):
        v = {f"k{i}": v}
    return v


def _lijst(stack: Stack) -> list[dict[str, Any]]:
    return list(stack.admin.get("/api/v1/actions").json()["items"])


def test_diep_geneste_waarden_worden_geweigerd_en_niet_bewaard(stack: Stack) -> None:
    """S-P2-010, R-VEILIG-1 (dicht bij twijfel): een catalogusapp met privileged, compose, docker.sock en hostpad "/"
    diep in de waarden geeft 422: tot de dieptegrens met de eigen code, dieper ``te_diep_genest``. Er wordt niets
    voorgesteld of bewaard. De boiler diep genest geeft 403 (EX27) en het geweigerde voorstel bewaart geen
    parameterwaarden. Vroeger werd beide voorgesteld (R2), goedgekeurd en via ``app.create`` uitgevoerd."""
    from asm_policy.params import MAX_PARAMETER_DIEPTE

    admin = stack.admin
    blad = {
        "privileged": True,
        "host_path_config": {"path": "/"},
        "custom_compose_config": {"services": {}},
        "sock": "/var/run/docker.sock",
    }
    for diepte, codes in (
        (MAX_PARAMETER_DIEPTE - 6, {"privileged_verboden", "hostpad_verboden", "compose_verboden"}),
        (MAX_PARAMETER_DIEPTE, {"te_diep_genest"}),
    ):
        r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", _nest(diepte, blad)))
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
        assert codes <= {f["code"] for f in r.json()["details"]["fouten"]}, (diepte, r.text)
    assert _lijst(stack) == []
    boiler = _catalogus_waarden("huis", _nest(MAX_PARAMETER_DIEPTE, {"x": "boiler aan"}))
    key, r = _voorstel(admin, "app.install", app_target("huis"), boiler)
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "boiler_verboden" in [b["code"] for b in r.json()["details"]["blokkades"]], r.text
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(key))
        assert rij is not None and rij.status == "geweigerd" and rij.parameters == {}
    assert schrijfaanroepen(stack.nas) == []


def _catalogus_waarden(naam: str, values: Any) -> dict[str, Any]:
    params = _catalogus_install(naam, "home-assistant")
    params["app_create"].update(train="community", values=values)
    return params


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({}, "catalogusversie_niet_toegelaten"),
        ({"app": {"onbekend": None}}, "catalogusversie_niet_toegelaten"),
        ({"app": {"init": {"token": "proefgeheim"}}}, "account_gegevens_verboden"),
        ({"app": {"api_token": "prod"}}, "secret_in_form"),
        ({"envs": [{"name": "JUPYTER_TOKEN", "value": "vault://app/huis/voorbeeld"}]}, "account_gegevens_verboden"),
        ({"storage": [{"type": "nfs", "nfs_config": {"path": "export"}}]}, "opslag_verboden"),
        ({"storage": [{"type": "cifs", "cifs_config": {}}]}, "opslag_verboden"),
    ],
)
def test_deel_c_weigert_een_catalogusvoorstel_zonder_nas_schrijfactie(stack: Stack, values: Any, code: str) -> None:
    rid, r = _voorstel(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig"
    assert code in {f["code"] for f in r.json()["details"]["fouten"]}
    assert "proefgeheim" not in r.text
    assert stack.admin.get(f"/api/v1/actions/{rid}").status_code == 404
    assert _lijst(stack) == [] and schrijfaanroepen(stack.nas) == []


@pytest.mark.parametrize("veld", ["host_network", "privileged"])
def test_deel_c_ex47_weigert_ook_met_voorsteltoelichting(stack: Stack, veld: str) -> None:
    params = install_params("demo", **{veld: True})
    params["manifest"]["host_network_reason"] = "Synthetische toelichting voor deze proef."
    rid, r = _voorstel(stack.admin, "app.install", app_target("demo"), params)
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig"
    assert f"{veld}_verboden" in {f["code"] for f in r.json()["details"]["fouten"]}
    assert stack.admin.get(f"/api/v1/actions/{rid}").status_code == 404
    assert schrijfaanroepen(stack.nas) == []


def test_deel_c_weigert_letterlijke_omgevingswaarde_in_geheimveld(stack: Stack) -> None:
    params = install_params("demo")
    env = params["app_create"]["values"]["envs"][0]
    env["name"] = "API_TOKEN"
    logins_voor = stack.nas.logins
    rid, r = _voorstel(stack.admin, "app.install", app_target("demo"), params)
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig"
    assert [f["code"] for f in r.json()["details"]["fouten"]] == ["secret_in_form"]
    assert stack.admin.get(f"/api/v1/actions/{rid}").status_code == 404
    assert stack.nas.logins == logins_voor and schrijfaanroepen(stack.nas) == []


def test_deel_c_oude_preview_maskeren_bij_lezen_en_herhalen(stack: Stack) -> None:
    body = {
        "action_id": "app.install",
        "target": app_target("demo"),
        "parameters": install_params("demo"),
        "reason": "test",
    }
    headers = idem()
    pad = "/api/v1/actions"
    r = stack.admin.post(pad, json=body, headers=headers)
    assert r.status_code == 201
    rid = uuid.UUID(r.json()["request_id"])
    preview_hash = r.json()["preview_hash"]
    preview_oud = r.json()["preview"]
    sleutel = "a1b2c3d4-1234-4567-a123-987654321abc"
    preview_oud["wijziging"]["waarden"]["api_token"] = {sleutel: "/padvormig/geheim"}
    preview_oud["wijziging"]["waarden"]["url"] = "https://app.invalid/?refresh_token=voorbeeld&mod=debug"
    with stack.app.state.sessionmaker() as db:
        req = db.get(ActionRequest, rid)
        rec = db.query(IdempotencyRecord).filter_by(key=rid).one()
        assert req is not None
        req.preview = copy.deepcopy(preview_oud)
        rec.response_body = {**rec.response_body, "preview": preview_oud}
        db.commit()
    assert sleutel not in stack.admin.get(pad).text
    detail = stack.admin.get(f"{pad}/{rid}").json()
    assert detail["preview"]["wijziging"]["waarden"]["api_token"] == {"***": "***"}
    herhaling = stack.admin.post(pad, json=body, headers=headers)
    assert herhaling.status_code == 201 and herhaling.headers["Idempotent-Replay"] == "true"
    assert sleutel not in herhaling.text and "/padvormig/geheim" not in herhaling.text
    r = stack.admin.post(f"{pad}/{rid}/reject", json={"reden": "test"}, headers=idem())
    assert r.status_code == 200 and sleutel not in r.text
    with stack.app.state.sessionmaker() as db:
        rec = db.query(IdempotencyRecord).filter_by(key=rid).one()
        assert sleutel not in str(rec.response_body)
        req = db.get(ActionRequest, rid)
        assert req is not None and req.preview_hash == preview_hash
        assert req.preview == rec.response_body["preview"] == detail["preview"]
        assert req.preview["wijziging"]["waarden"]["url"] == "https://app.invalid/?refresh_token=***&mod=debug"
    assert schrijfaanroepen(stack.nas) == []


@pytest.fixture
def oude_cataloguspreview(monkeypatch: pytest.MonkeyPatch) -> None:
    """Laat de bestaande presentatietests met hun synthetische invoer een oude cataloguspreview maken."""
    from asm_policy import params

    c12 = params.c12_installatie
    monkeypatch.setattr(params, "catalogusinstallatie", lambda *_a: [])
    monkeypatch.setattr(params, "c12_installatie", lambda values, *, ix_app: c12(values, ix_app=True) if ix_app else [])


def test_catalogusapp_met_extra_rechten_wordt_geweigerd(stack: Stack) -> None:
    """S-P2-010, R-VEILIG-3 (ADR-0030 besluit 6): ook de eigen waarden van een catalogusapp krijgen geen extra
    capabilities, apparaten, host-PID/-IPC, gedeeld netwerk of GPU zonder ``gpu: intel_render``, ook genest. De Hub
    geeft 422 met de code per sleutel en bewaart niets. Zonder extra rechten resteert de witte-lijstweigering."""
    values = {
        "app": {
            "capabilities": {"add": ["SYS_ADMIN"]},
            "devices": [{"host_device": "/dev/sda"}],
            "host_pid": True,
            "host_ipc": True,
            "networks": ["gedeeld"],
        },
        "resources": {"gpus": {"use_all_gpus": True}},
    }
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    codes = {f["code"] for f in r.json()["details"]["fouten"]}
    verwacht = {
        "capabilities_verboden",
        "devices_verboden",
        "host_pid_verboden",
        "host_ipc_verboden",
        "netwerk_verboden",
        "gpu_zonder_d08",
    }
    assert verwacht <= codes, codes
    assert _lijst(stack) == [] and schrijfaanroepen(stack.nas) == []
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", {"app": {"tz": "x"}}))
    assert r.status_code == 422
    assert [f["code"] for f in r.json()["details"]["fouten"]] == ["catalogusversie_niet_toegelaten"]


def test_losse_teksten_in_lijsten_worden_geweigerd_en_niet_bewaard(stack: Stack) -> None:
    """S-P2-010, herstelronde 2 (dicht bij twijfel): een losse tekst in een lijst werd niet bekeken. Een catalogusapp
    met ``{"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}``, ``{"binds": ["/:/host"]}``, ``"--privileged"``
    of een ongeldige kluisverwijzing in een lijst (ook genest) geeft nu 422 met de eigen code; er wordt niets
    voorgesteld of bewaard. Een geldige kluisverwijzing in een lijst geeft 501 (``vault_verwijzingen``), net als in een
    object. Tegenproef: gewone teksten in lijsten (dataset als bron, benoemd volume) worden voorgesteld (R2)."""
    admin = stack.admin
    values = {
        "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
        "app": {"binds": ["/mnt/testpool/media:/media", "/:/host"], "args": [["--privileged", "--pid=host"]]},
        "geheim": ["vault://ander/x"],
    }
    r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    fouten = {(f["veld"], f["code"]) for f in r.json()["details"]["fouten"]}
    w = "parameters.app_create.values"
    assert {
        (f"{w}.volumes[0]", "docker_socket_verboden"),
        (f"{w}.app.binds[1]", "hostpad_verboden"),
        (f"{w}.app.args[0][0]", "privileged_verboden"),
        (f"{w}.app.args[0][1]", "host_pid_verboden"),
        (f"{w}.geheim[0]", "vault_ref_ongeldig"),
    } <= fouten, fouten
    assert not [f for f in fouten if f[0] == f"{w}.app.binds[0]"], fouten  # een dataset als bron mag
    # De standaard Custom App: een geldige kluisverwijzing in command wordt nu gevonden (501), niets voorgesteld.
    r = stel_voor(admin, "app.install", app_target("demo"), install_params("demo", command=["vault://app/demo/token"]))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"] == {"reden": "vault_verwijzingen"}, r.text
    assert _lijst(stack) == [] and schrijfaanroepen(stack.nas) == []
    # De boiler als losse tekst in een lijst: 403, en het geweigerde voorstel bewaart geen parameterwaarden.
    key, r = _voorstel(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", {"a": [["boiler aan"]]}))
    assert r.status_code == 403 and "boiler_verboden" in [b["code"] for b in r.json()["details"]["blokkades"]]
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(key))
        assert rij is not None and rij.status == "geweigerd" and rij.parameters == {}
    goed = {"volumes": ["/mnt/testpool/media:/media:ro", "data:/data"], "args": ["--config", "/config/app.yml"]}
    r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", goed))
    assert r.status_code == 422
    assert [f["code"] for f in r.json()["details"]["fouten"]] == ["catalogusversie_niet_toegelaten"]
    assert schrijfaanroepen(stack.nas) == []


def test_objectvormen_in_catalogusapp_waarden_worden_geweigerd_en_niet_bewaard(stack: Stack) -> None:
    """S-P2-010, herstelronde 3 (R-VEILIG-7, -8, -9; R-TECH-6, -7): in een object van de waarden van een catalogusapp
    kwamen ``privileged`` met de waarde 1 of "true", andere schrijfwijzen (``Privileged``, ``hostNetwork``),
    Docker-/compose-namen (``network_mode``, ``device``, ``security_opt``, ``Custom-Compose-Config``) en een tekst in
    vlag- of bindvorm (``{"extra_args": "--privileged"}``, ``{"volume": "/:/host"}``) zonder fout door: voorgesteld
    (R2), goedgekeurd met een preview die "privileged: false" toonde, en uitgevoerd via ``app.create``. Nu 422 met
    de code per veld, samen en elk apart, ook in een onderdeel van de standaard Custom App; er wordt niets
    voorgesteld of bewaard. Tegenproef: uit-standen en vrije tekst worden voorgesteld (R2), en een gewone opdracht
    van de standaard Custom App ook."""
    admin = stack.admin
    w = "parameters.app_create.values"
    vormen: dict[str, tuple[Any, str, str]] = {
        "a": ({"privileged": 1}, f"{w}.a.privileged", "privileged_verboden"),
        "b": ({"privileged": "true"}, f"{w}.b.privileged", "privileged_verboden"),
        "c": ({"network_mode": "host"}, f"{w}.c.network_mode", "catalogus_waarde_verboden"),
        "d": ({"device": "/dev/sda"}, f"{w}.d.device", "devices_verboden"),
        "e": ({"Privileged": True}, f"{w}.e.Privileged", "privileged_verboden"),
        "f": ({"hostNetwork": True}, f"{w}.f.hostNetwork", "host_network_zonder_reden"),
        "g": ({"Custom-Compose-Config": {"services": {}}}, f"{w}.g.Custom-Compose-Config", "compose_verboden"),
        "h": ({"security_opt": ["seccomp=unconfined"]}, f"{w}.h.security_opt", "catalogus_waarde_verboden"),
        "extra_args": ("--privileged", f"{w}.extra_args", "privileged_verboden"),
        "volume": ("/:/host", f"{w}.volume", "hostpad_verboden"),
        "mount": ({"type": "bind", "source": "/etc", "target": "/e"}, f"{w}.mount.source", "hostpad_verboden"),
    }
    samen = {sleutel: waarde for sleutel, (waarde, _veld, _code) in vormen.items()}
    r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", samen))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    fouten = {(f["veld"], f["code"]) for f in r.json()["details"]["fouten"]}
    assert {(veld, code) for _waarde, veld, code in vormen.values()} <= fouten, fouten
    for sleutel, (waarde, veld, code) in vormen.items():
        r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", {sleutel: waarde}))
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", (sleutel, r.text)
        assert (veld, code) in {(f["veld"], f["code"]) for f in r.json()["details"]["fouten"]}, (sleutel, r.text)
    # Ook in een onderdeel van de standaard Custom App (de witte lijst geldt alleen bovenaan).
    ix = install_params("demo", resources={"limits": {"cpus": 2, "memory": 1024}, "privileged": "true"})
    r = stel_voor(admin, "app.install", app_target("demo"), ix)
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert (f"{w}.resources.privileged", "privileged_verboden") in {
        (f["veld"], f["code"]) for f in r.json()["details"]["fouten"]
    }, r.text
    assert _lijst(stack) == [] and schrijfaanroepen(stack.nas) == []
    goed = {
        "privileged": False,
        "network": {"host_network": False, "web_port": {"port_number": 30200}},
        "additional_envs": [{"name": "PATH", "value": "/usr/bin:/bin"}, {"name": "EXTRA", "value": "--privileged"}],
        "notes": "privileged: nee. Zie /etc:/x",
        "opslag": {"source": "/mnt/testpool/media"},
    }
    r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", goed))
    assert r.status_code == 422
    assert [f["code"] for f in r.json()["details"]["fouten"]] == ["catalogusversie_niet_toegelaten"]
    # Een eigen opdracht van de standaard Custom App doorstaat het beleid, maar de Hub weigert hem tot een
    # installatiescherm hem veilig kan tonen (S-P2-040, R-VEILIG-1, besluit regisseur optie C; ADR-0030 besluit 32).
    opdracht = install_params("demo", command=["java", "-cp", "/app/lib/*:/app/classes", "nl.Main"])
    r = stel_voor(admin, "app.install", app_target("demo"), opdracht)
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"] == {"reden": "eigen_opdracht", "velden": ["command"]}, r.text
    assert schrijfaanroepen(stack.nas) == []
    # Precies de lege lijst zet geen opdracht (de vertaling van de appstore zet haar altijd; S-P2-050g): voorgesteld
    # en zichtbaar als lege lijst. Een lege tekst in de lijst is wel een opdracht.
    for veld in ("command", "entrypoint"):
        r = stel_voor(admin, "app.install", app_target("demo"), install_params("demo", **{veld: [""]}))
        assert r.status_code == 501 and r.json()["details"]["velden"] == [veld], r.text
    r = stel_voor(admin, "app.install", app_target("demo"), install_params("demo", command=[], entrypoint=[]))
    assert r.status_code == 201, r.text
    waarden = r.json()["preview"]["wijziging"]["waarden"]
    assert waarden["command"] == [] and waarden["entrypoint"] == [], waarden


def test_bijwerken_of_terugzetten_naar_een_emby_image_wordt_geweigerd(stack: Stack) -> None:
    """S-P2-010, R-VEILIG-2 en R-TECH-1 (HARDE EIS): ``app.update`` van een bestaande Custom App naar een Emby-image
    maakt er een tweede Emby van. De Hub herkent het doel ook op de image ná de actie: 403 met de Emby-regel, ook
    voor een beheerder; TrueNAS krijgt niets. Tegenproef: bijwerken binnen dezelfde repository blijft R2. Bij
    terugzetten (``herstel_van``) telt de image van vóór die wijziging, zoals de Hub hem toen zag."""
    admin = stack.admin
    emby = {"image": {"repository": "emby/embyserver", "tag": f"4.8.10.0@{DIGEST}"}}
    key, r = _voorstel(admin, "app.update", app_target("my-house"), emby)
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [b["code"] for b in r.json()["details"]["blokkades"]], r.text
    assert haal(admin, key)["status"] == "geweigerd"
    zelfde = {"image": {"repository": "ghcr.io/lvos04/my_house", "tag": f"0.2.0@{DIGEST}"}}
    r = stel_voor(admin, "app.update", app_target("my-house"), zelfde)
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text
    assert "emby_nooit_door_platform" not in str(r.json()["blokkades"]), r.text
    update_id = r.json()["request_id"]
    # Terugzetten naar de toestand van vóór die update: daar draaide (volgens de preview van toen) een Emby-image.
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(update_id))
        assert rij is not None
        preview = copy.deepcopy(rij.preview)
        preview["huidig"]["images"] = ["docker.io/emby/embyserver:4.8.10.0"]
        rij.preview = preview
        db.commit()
    key, r = _voorstel(admin, "app.rollback", app_target("my-house"), {"herstel_van": update_id})
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [b["code"] for b in r.json()["details"]["blokkades"]], r.text
    # Tegenproef: terugzetten naar een gewone vorige image wordt voorgesteld (R2).
    r = stel_voor(admin, "app.update", app_target("my-house"), zelfde)
    assert r.status_code == 201, r.text
    r = stel_voor(admin, "app.rollback", app_target("my-house"), {"herstel_van": r.json()["request_id"]})
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text
    assert schrijfaanroepen(stack.nas) == []


def test_losse_surrogaat_in_de_parameters_geeft_422(stack: Stack) -> None:
    """S-P2-010, R-VEILIG-6: een losse surrogaat (``"\\ud800"`` in JSON) is geen UTF-8. Vroeger gaf dat een
    onverwachte fout (500); nu 422 ``parameters_ongeldig`` met ``niet_canoniek``, en er wordt niets bewaard."""
    for parameters in ('{"app_create":{"x":"\\ud800"}}', '{"image":{"\\udc80":"x"}}'):
        actie = "app.install" if "app_create" in parameters else "app.update"
        body = (
            f'{{"action_id":"{actie}","target":{{"host_id":"{HOST}","app_id":"my-house"}},'
            f'"parameters":{parameters},"reason":"test"}}'
        )
        r = stack.admin.post(
            "/api/v1/actions", content=body.encode(), headers={**idem(), "Content-Type": "application/json"}
        )
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
        assert [f["code"] for f in r.json()["details"]["fouten"]] == ["niet_canoniek"], r.text
    assert _lijst(stack) == [] and schrijfaanroepen(stack.nas) == []


@pytest.mark.parametrize(
    ("naam", "action_id", "code"),
    [
        ("ai-server-manager", "app.stop", "platform_niet_stoppen"),
        ("ai-server-manager", "app.uninstall", "platform_niet_stoppen"),
        ("ai-server-manager-executor", "app.stop", "executor_niet_zelf"),
        ("mediaguard", "app.uninstall", "mediaguard_upgradebewijs_ontbreekt"),
        ("jellyfin", "app.uninstall", "mediaserver_migratie_vraagt_rapport"),
    ],
)
def test_beschermde_apps(stack: Stack, naam: str, action_id: str, code: str) -> None:
    if naam not in ("mediaguard", "jellyfin"):
        _kloon(stack.nas, naam)
    _key, r = _voorstel(stack.admin, action_id, app_target(naam))
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert code in [b["code"] for b in r.json()["details"]["blokkades"]], r.text


def test_schema_en_doel_worden_gecontroleerd(stack: Stack) -> None:
    admin = stack.admin
    for target in ({"host_id": "andere-nas", "app_id": "my-house"}, {"host_id": HOST}, {"app_id": "../etc"}):
        r = stel_voor(admin, "app.restart", target)
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    r = stel_voor(admin, "app.restart", app_target("my-house"), {"force": True})
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    r = stel_voor(admin, "app.restart", app_target("bestaat-niet"))
    assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_niet", r.text
    r = stel_voor(admin, "app.install", app_target("my-house"), install_params("my-house"))
    assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_al", r.text
    # Onbekende velden in het voorstel zelf bestaan niet (ook geen eigen backup_checkpoint_id of risicoklasse).
    for extra in ({"backup_checkpoint_id": "x"}, {"risk_class": "R0"}, {"approval": {"approved_by": "ai"}}):
        r = stel_voor(admin, "app.restart", app_target("my-house"), **extra)
        assert r.status_code == 422, r.text
    assert admin.get("/api/v1/actions").json()["items"] == [] and schrijfaanroepen(stack.nas) == []


def test_nas_onbereikbaar_dan_geen_voorstel(stack: Stack) -> None:
    """Zonder eigen readback geen preview en geen ETag: onbekend is geen grond voor een voorstel."""
    stack.nas.stop()
    r = stel_voor(stack.admin, "app.restart", app_target("my-house"))
    assert r.status_code == 409 and r.json()["code"] == "doel_onbekend", r.text
    assert stack.admin.get("/api/v1/actions").json()["items"] == []


# ---------------------------------------------------------------------- rollen en idempotentie
def test_rollen(stack: Stack) -> None:
    admin = stack.admin
    for naam, rol in (("vera", "viewer"), ("oscar", "operator"), ("kim", "kind")):
        make_user(admin, naam, rol)
    vera, oscar, kim = (login_as(stack.app, n) for n in ("vera", "oscar", "kim"))
    v = stel_voor(oscar, "app.uninstall", app_target("my-house")).json()
    assert v["status"] == "wacht_op_goedkeuring" and v["actor"] == {"type": "user", "id": "oscar"}
    assert stel_voor(vera, "app.restart", app_target("my-house")).status_code == 403
    assert stel_voor(kim, "app.restart", app_target("my-house")).status_code == 403
    assert kim.get("/api/v1/actions").status_code == 403 and kim.get("/api/v1/policy").status_code == 403
    assert vera.get("/api/v1/actions").status_code == 200
    for c in (vera, oscar, kim):
        assert keur_goed(c, v).status_code == 403
        r = c.post(f"/api/v1/actions/{v['request_id']}/reject", json={"reden": "nee"}, headers=idem())
        assert r.status_code == 403
        assert c.put("/api/v1/actions/noodstop", json={"actief": False}, headers=idem()).status_code == 403
    assert haal(admin, v)["status"] == "wacht_op_goedkeuring" and haal(admin, v)["goedkeuring"] is None


def test_idempotentie_en_lijst(stack: Stack) -> None:
    admin = stack.admin
    key = str(uuid.uuid4())
    body = {"action_id": "app.restart", "target": app_target("my-house"), "parameters": {}, "reason": "test"}
    r1 = admin.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})
    r2 = admin.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})
    assert r1.status_code == 201 and r2.status_code == 201 and r1.json() == r2.json()
    assert r1.json()["request_id"] == key  # request_id = Idempotency-Key (contract §8: idempotency_key)
    # Dezelfde sleutel met een ander voorstel is geen nieuw voorstel.
    r3 = admin.post("/api/v1/actions", json={**body, "action_id": "app.stop"}, headers={"Idempotency-Key": key})
    assert r3.status_code in (409, 422), r3.text
    r = admin.post("/api/v1/actions", json={**body, "idempotency_key": str(uuid.uuid4())}, headers=idem())
    assert r.status_code == 422 and r.json()["code"] == "idempotency_key_past_niet", r.text
    key2 = str(uuid.uuid4())
    stop = {**body, "action_id": "app.stop", "idempotency_key": key2}
    r = admin.post("/api/v1/actions", json=stop, headers={"Idempotency-Key": key2})
    assert r.status_code == 201 and r.json()["request_id"] == key2, r.text
    stel_voor(admin, "app.uninstall", app_target("mediaguard"))  # geweigerd (beschermd)
    stel_voor(admin, "app.uninstall", app_target("my-house"))
    lijst = admin.get("/api/v1/actions").json()
    assert len(lijst["items"]) == 4 and lijst["noodstop"]["actief"] is False
    assert [i["action_id"] for i in admin.get("/api/v1/actions", params={"status": "open"}).json()["items"]] == [
        "app.uninstall",
        "app.stop",
        "app.restart",
    ]
    assert len(admin.get("/api/v1/actions", params={"status": "geweigerd"}).json()["items"]) == 1
    assert len(admin.get("/api/v1/actions", params={"action_id": "app.restart"}).json()["items"]) == 1
    pagina = admin.get("/api/v1/actions", params={"limit": 2}).json()
    assert len(pagina["items"]) == 2 and pagina["next_cursor"]
    rest = admin.get("/api/v1/actions", params={"limit": 2, "cursor": pagina["next_cursor"]}).json()
    assert len(rest["items"]) == 2 and rest["next_cursor"] is None
    assert {i["request_id"] for i in pagina["items"]}.isdisjoint(i["request_id"] for i in rest["items"])
    assert admin.get(f"/api/v1/actions/{uuid.uuid4()}").status_code == 404


def test_muterende_actieroutes_vragen_een_idempotency_key(stack: Stack) -> None:
    """Zonder ``Idempotency-Key`` gebeurt er niets: geen voorstel, goedkeuring, afwijzing, uitvoering of noodstop."""
    admin = stack.admin
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    rid = v["request_id"]
    body = {"action_id": "app.restart", "target": app_target("my-house"), "parameters": {}, "reason": "test"}
    for pad, inhoud in (
        ("/api/v1/actions", body),
        (f"/api/v1/actions/{rid}/approve", hashes(v)),
        (f"/api/v1/actions/{rid}/reject", {"reden": "nee"}),
        (f"/api/v1/actions/{rid}/execute", None),
        (f"/api/v1/actions/{rid}/reconcile", None),
    ):
        r = admin.post(pad, json=inhoud)
        assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required", (pad, r.text)
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "proef"})
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required", r.text
    assert [i["request_id"] for i in admin.get("/api/v1/actions").json()["items"]] == [rid]
    assert haal(admin, v)["status"] == "wacht_op_goedkeuring" and haal(admin, v)["goedkeuring"] is None
    assert admin.get("/api/v1/actions/noodstop").json()["actief"] is False and schrijfaanroepen(stack.nas) == []


# ---------------------------------------------------------------------- zonder executor
def test_zonder_gekoppelde_executor_wordt_er_niets_gewijzigd(stack: Stack) -> None:
    admin = stack.admin
    v = stel_voor(admin, "app.start", app_target("my-house")).json()
    assert v["status"] == "klaar"
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "executor_niet_gekoppeld", r.text
    assert haal(admin, v)["status"] == "klaar"  # niets gestart, niets verbruikt
    w = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert "executor_niet_gekoppeld" in [b["code"] for b in w["blokkades"]]
    r = keur_goed(admin, w)
    assert r.status_code == 409 and r.json()["code"] == "actie_geblokkeerd", r.text
    assert schrijfaanroepen(stack.nas) == []


# ---------------------------------------------------------------------- notification.send (R0, in de Hub)
def test_melding_versturen_r0(stack: Stack, periodic_run: Any) -> None:
    admin = stack.admin
    params = {"titel": "Proefmelding", "tekst": "Dit is een test.", "prioriteit": 5}
    v = stel_voor(admin, "notification.send", {"host_id": HOST}, params).json()
    assert v["risk_class"] == "R0" and v["status"] == "klaar" and v["uitvoerder"] == "hub:gotify"
    # Zonder kanaal: eerlijk mislukt, geen gesimuleerd succes.
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "geen_kanaal", r.text
    assert haal(admin, v)["status"] == "mislukt"
    gotify = FakeGotify(tokens={TOKEN}).start()
    try:
        r = admin.post(
            "/api/v1/notifications/channels",
            json={"naam": "Telefoon", "basis_url": gotify.url, "token": TOKEN},
            headers=idem(),
        )
        assert r.status_code == 201, r.text
        make_user(admin, "oscar", "operator")
        oscar = login_as(stack.app, "oscar")
        v = stel_voor(oscar, "notification.send", {"host_id": HOST}, params).json()
        r = voer_uit(oscar, v)
        assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
        assert r.json()["resultaat"]["status"] == "wachtrij" and len(r.json()["resultaat"]["meldingen"]) == 1
        periodic_run("meldingen_versturen")
        assert [m["title"] for m in gotify.messages] == ["Proefmelding"]
    finally:
        gotify.stop()
    for fout in (
        {"titel": "x"},
        {"titel": "x", "tekst": "y", "prioriteit": 11},
        {"titel": "x", "tekst": "y", "url": "z"},
    ):
        r = stel_voor(admin, "notification.send", {"host_id": HOST}, fout)
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text


# ---------------------------------------------------------------------- goedkeuring: bepaald, niet toevallig
def test_open_goedkeuring_gaat_altijd_voor_ook_in_dezelfde_seconde(stack: Stack) -> None:
    """Twee goedkeuringen met hetzelfde tijdstip (vervallen en meteen opnieuw goedgekeurd) mogen niet door toeval
    worden verwisseld: anders zou een geldige goedkeuring soms als vervallen gelden."""
    from hub.actions.service import huidige_goedkeuring
    from hub.models import Approval
    from hub.timeutil import utcnow

    v = stel_voor(stack.admin, "app.uninstall", app_target("my-house")).json()
    nu = utcnow().replace(microsecond=0)

    def goedkeuring(**meer: Any) -> Approval:
        return Approval(
            id=uuid.uuid4(),
            request_id=uuid.UUID(v["request_id"]),
            preview_hash=v["preview_hash"],
            resource_etag=v["resource_etag"],
            policy_hash=v["policy_hash"],
            risk_class="R2",
            approved_by="beheerder",
            approved_at=nu,
            expires_at=nu + timedelta(minutes=15),
            one_time_nonce=uuid.uuid4(),
            action_scope={},
            **meer,
        )

    with stack.app.state.sessionmaker() as db:
        req = db.get(ActionRequest, uuid.UUID(v["request_id"]))
        assert huidige_goedkeuring(db, req) is None
        vervallen = [goedkeuring(vervallen_op=nu, vervallen_reden="gewijzigd:resource_etag") for _ in range(12)]
        db.add_all(vervallen)
        db.flush()
        gebruikt = goedkeuring(used_at=nu)
        db.add(gebruikt)
        db.flush()
        assert huidige_goedkeuring(db, req).id == gebruikt.id  # gebruikt gaat voor vervallen
        open_ = goedkeuring()
        db.add(open_)
        db.flush()
        for _ in range(3):
            assert huidige_goedkeuring(db, req).id == open_.id
        db.rollback()


# ---------------------------------------------------------------------- S-P2-040 herstel: preview en noodstop
# Per veld van het formulier van de standaard Custom App (``IX_VALUES_KEYS``) een waarde die het beleid toelaat, anders
# dan de standaardwaarde van ``install_params`` (R-VEILIG-1). Een nieuw veld zonder proefwaarde maakt de test rood.
IX_PROEFWAARDEN: dict[str, Any] = {
    "notes": "notitie bij de app",
    "image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.3@{DIGEST}", "pull_policy": "always"},
    "hostname": "proef-hostnaam",
    "entrypoint": ["/bin/start"],
    "command": ["--modus", "proef"],
    "TZ": "Europe/Amsterdam",
    "envs": [{"name": "PROEF_MODUS", "value": "waarde-blijft-verborgen-731"}],
    "restart_policy": "on-failure",
    "max_retry_count": 3,
    "disable_builtin_healthcheck": True,
    "tty": True,
    "stdin": True,
    "devices": [],
    "privileged": False,
    "capabilities": {"add": []},
    "run_as_custom_user": True,
    "run_as": {"user": 568, "group": 568},
    "host_network": False,
    "ports": [{"bind_mode": "published", "port_number": 30556, "container_port": 9090, "protocol": "udp"}],
    "networks": [],
    "dns_config": {"nameservers": ["127.0.0.1"], "searches": ["proef.invalid"], "options": []},
    "portals": [{"name": "Web", "scheme": "http", "port": 30556, "path": "/start"}],
    "storage": [{"type": "tmpfs", "mount_path": "/cache", "tmpfs_config": {"size": 256}}],
    "labels": [{"key": "proef.label", "value": "proefwaarde-label", "containers": ["demo-app"]}],
    "resources": {"limits": {"cpus": 1, "memory": 512}},
}


def test_elk_veld_van_de_standaard_custom_app_heeft_een_previewregel() -> None:
    """Bewaking (S-P2-040, R-VEILIG-1): elk veld dat het beleid in de waarden van de standaard Custom App toelaat, heeft
    een vaste regel voor de preview. Komt er in ``IX_VALUES_KEYS`` een veld bij zonder regel (of zonder proefwaarde
    hieronder), dan is deze test rood: een veld dat naar TrueNAS gaat maar niet in de preview staat, keurt een beheerder
    ongezien goed."""
    from asm_policy.params import IX_VALUES_KEYS

    from hub.actions.preview import IX_PREVIEWREGELS

    assert set(IX_PREVIEWREGELS) == set(IX_VALUES_KEYS)
    assert set(IX_PROEFWAARDEN) == set(IX_VALUES_KEYS)
    assert set(IX_PREVIEWREGELS.values()) <= {"waarde", "namen", "geweigerd"}
    # Besluit regisseur (optie C): alleen command en entrypoint worden geweigerd; alleen bij envs blijft de waarde weg.
    assert {k for k, regel in IX_PREVIEWREGELS.items() if regel == "geweigerd"} == {"command", "entrypoint"}
    assert {k for k, regel in IX_PREVIEWREGELS.items() if regel == "namen"} == {"envs"}


def test_preview_van_een_installatie_toont_elk_gezet_veld(stack: Stack) -> None:
    """S-P2-040, R-VEILIG-1 (blokkerend): per toegelaten veld van de standaard Custom App een voorstel; het veld staat
    met zijn waarde in ``preview.wijziging.waarden`` (bij ``envs`` alleen de namen; ADR-0030 besluit 28). ``command``
    en ``entrypoint`` weigert de Hub met ``501 capability_unavailable`` (besluit regisseur, optie C): niets
    voorgesteld."""
    from asm_policy.params import IX_VALUES_KEYS

    admin = stack.admin
    for sleutel in sorted(IX_VALUES_KEYS):
        waarde = IX_PROEFWAARDEN[sleutel]
        extra = {sleutel: waarde}
        if sleutel == "run_as_custom_user":
            extra["run_as"] = IX_PROEFWAARDEN["run_as"]  # het beleid eist dan een gewone uid/gid
        key, r = _voorstel(admin, "app.install", app_target("demo-app"), install_params("demo-app", **extra))
        if sleutel in ("command", "entrypoint"):
            assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", (sleutel, r.text)
            assert r.json()["details"] == {"reden": "eigen_opdracht", "velden": [sleutel]}, (sleutel, r.text)
            assert admin.get(f"/api/v1/actions/{key}").status_code == 404  # niets voorgesteld of bewaard
            continue
        assert r.status_code == 201, (sleutel, r.text)
        waarden = r.json()["preview"]["wijziging"]["waarden"]
        if sleutel == "envs":
            assert waarden["envs"] == ["PROEF_MODUS"], waarden
            assert "waarde-blijft-verborgen-731" not in r.text
        else:
            assert waarden[sleutel] == waarde, (sleutel, waarden)
        assert waarden == haal(admin, key)["preview"]["wijziging"]["waarden"]
    assert schrijfaanroepen(stack.nas) == []


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_preview_van_een_catalogusapp_toont_de_eigen_waarden(stack: Stack) -> None:
    """S-P2-040, R-VEILIG-1: ook de eigen waarden van een catalogusapp staan in de preview, met hun waarde. Alleen een
    geheim (een waarde onder een geheim-achtige sleutel) staat er als ``***``, zoals overal in de API-uitvoer van de Hub
    (``hub.redact``). Van een paar name/value staat alleen de naam erin (herstelronde 2, R-VEILIG-6; besluit 28)."""
    values = {
        "app": {"tz": "Europe/Amsterdam", "web_port": 30200, "beheerwachtwoord": "proefgeheim-catalogus-812"},
        "additional_envs": [
            {"name": "GEHEIME_SLEUTEL", "value": "proefgeheim-env-813"},
            {"name": "MODUS", "value": "zichtbaar"},
        ],
        "notes": "notitie bij de catalogusapp",
    }
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text
    waarden = r.json()["preview"]["wijziging"]["waarden"]
    assert waarden == {
        "app": {"tz": "Europe/Amsterdam", "web_port": 30200, "beheerwachtwoord": "***"},
        "additional_envs": [{"name": "GEHEIME_SLEUTEL", "value": "***"}, {"name": "MODUS", "value": "***"}],
        "notes": "notitie bij de catalogusapp",
    }, waarden
    assert "proefgeheim" not in r.text and "proefgeheim" not in stack.admin.get("/api/v1/actions").text


def _kijkers_tekst(stack: Stack, kijker: Any, rid: str) -> str:
    """Wat een kijker (rol viewer) en een beheerder van een voorstel kunnen lezen: het voorstel en de lijst."""
    return "\n".join(
        c.get(pad).text for c in (kijker, stack.admin) for pad in (f"/api/v1/actions/{rid}", "/api/v1/actions")
    )


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_geheime_sleutel_direct_onder_de_waarden_van_een_catalogusapp_staat_er_als_sterretjes(stack: Stack) -> None:
    """S-P2-040, herstelronde 2 (R-VEILIG-5; ADR-0030 besluit 32): een waarde onder een geheim-achtige sleutel staat er
    als ``***``, ook als die sleutel direct onder ``values`` van een catalogusapp staat; in het antwoord op het
    voorstel, voor een kijker en ook nadat het voorstel is afgewezen."""
    make_user(stack.admin, "kijker5", "viewer")
    kijker = login_as(stack.app, "kijker5")
    values = {
        "admin_password": "proefgeheim-top-901",
        "api_token": "proefgeheim-top-902",
        "app": {"tz": "Europe/Amsterdam", "admin_password": "proefgeheim-genest-903"},
    }
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"] == {
        "admin_password": "***",
        "api_token": "***",
        "app": {"tz": "Europe/Amsterdam", "admin_password": "***"},
    }, r.text
    rid = r.json()["request_id"]
    assert "proefgeheim" not in r.text and "proefgeheim" not in _kijkers_tekst(stack, kijker, rid)
    assert stack.admin.post(f"/api/v1/actions/{rid}/reject", json={"reden": "nee"}, headers=idem()).status_code == 200
    assert "proefgeheim" not in _kijkers_tekst(stack, kijker, rid)
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(rid))
        assert rij is not None and "proefgeheim" not in str(rij.preview)


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_omgevingsvariabelen_van_een_catalogusapp_alleen_met_naam_in_de_preview(stack: Stack) -> None:
    """S-P2-040, herstelronde 2 (R-VEILIG-6; ADR-0030 besluit 28): van een paar name/value in de waarden van een
    catalogusapp staat alleen de naam in de preview; de waarde is verborgen (``***``), ook bij een naam die niet op een
    geheim lijkt. In het antwoord, voor een kijker en na afwijzen; ook niet in de bewaarde preview."""
    make_user(stack.admin, "kijker6", "viewer")
    kijker = login_as(stack.app, "kijker6")
    values = {
        "home_assistant": {
            "additional_envs": [
                {"name": "ENCRYPTION_KEY", "value": "proefgeheim-env-911"},
                {"name": "DB_PWD", "value": "proefgeheim-env-912"},
                {"name": "POSTGRES_PASSWORD", "value": "proefgeheim-env-913"},
            ]
        }
    }
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"] == {
        "home_assistant": {
            "additional_envs": [
                {"name": "ENCRYPTION_KEY", "value": "***"},
                {"name": "DB_PWD", "value": "***"},
                {"name": "POSTGRES_PASSWORD", "value": "***"},
            ]
        }
    }, r.text
    rid = r.json()["request_id"]
    assert "proefgeheim" not in r.text and "proefgeheim" not in _kijkers_tekst(stack, kijker, rid)
    assert "ENCRYPTION_KEY" in _kijkers_tekst(stack, kijker, rid)
    assert stack.admin.post(f"/api/v1/actions/{rid}/reject", json={"reden": "nee"}, headers=idem()).status_code == 200
    assert "proefgeheim" not in _kijkers_tekst(stack, kijker, rid)
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(rid))
        assert rij is not None and "proefgeheim" not in str(rij.preview)


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_geheim_in_een_label_of_een_niet_tekstwaarde_staat_er_als_sterretjes(stack: Stack) -> None:
    """S-P2-040, herstelronde 3 (R-VEILIG-8; ADR-0030 besluit 32): (a) de ``value`` van een label met een geheim-achtige
    ``key`` staat er als ``***``, bij de standaard Custom App en bij een catalogusapp; (b) de ``value`` van een paar
    name/value is ook ``***`` als het een getal, een lijst of een object is; (c) een geheim-achtige sleutel direct
    onder ``values`` met een getal of een object ook; (d) leeg en ja/nee blijven zichtbaar, en een gewoon label ook."""
    admin = stack.admin
    ix = install_params(
        "demo-lab",
        labels=[
            {"key": "x.token", "value": "proefgeheim-lab-921", "containers": []},
            {"key": "proef.wachtwoord", "value": "proefgeheim-lab-922", "containers": []},
            {"key": "x.info", "value": "zichtbaar-lab-923", "containers": []},
        ],
    )
    r = stel_voor(admin, "app.install", app_target("demo-lab"), ix)
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"]["labels"] == [
        {"key": "x.token", "value": "***", "containers": []},
        {"key": "proef.wachtwoord", "value": "***", "containers": []},
        {"key": "x.info", "value": "zichtbaar-lab-923", "containers": []},
    ], r.text
    assert "proefgeheim" not in r.text
    values = {
        "app": {
            "labels": [{"key": "x.token", "value": "proefgeheim-lab-924"}, {"key": "x.info", "value": "zichtbaar"}],
            "additional_envs": [
                {"name": "A", "value": 1234},
                {"name": "B", "value": ["proefgeheim-lijst-925"]},
                {"name": "C", "value": {"x": "proefgeheim-object-926"}},
                {"name": "D", "value": ""},
                {"name": "E", "value": True},
            ],
        },
        "api_token": 123456,
        "client_secret": {"a": "proefgeheim-object-927"},
        "admin_token": True,
        "password": "",
    }
    r = stel_voor(admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"] == {
        "app": {
            "labels": [{"key": "x.token", "value": "***"}, {"key": "x.info", "value": "zichtbaar"}],
            "additional_envs": [
                {"name": "A", "value": "***"},
                {"name": "B", "value": "***"},
                {"name": "C", "value": "***"},
                {"name": "D", "value": ""},
                {"name": "E", "value": True},
            ],
        },
        "api_token": "***",
        "client_secret": {"a": "***"},  # de vorm blijft staan (herstelronde 6, R-VEILIG-20; besluit regisseur)
        "admin_token": True,
        "password": "",
    }, r.text
    assert "proefgeheim" not in r.text
    assert "proefgeheim" not in admin.get("/api/v1/actions").text


@pytest.mark.parametrize(
    ("values", "verwacht"),
    [
        pytest.param(
            {"app": {"environment": {"DB_HOST": "proefgeheim-env-931", "LEEG": "", "AAN": True}}},
            {"app": {"environment": {"DB_HOST": "***", "LEEG": "", "AAN": True}}},
            id="object",
        ),
        pytest.param(
            {"app": {"Env": {"MODUS": 7, "LIJST": ["proefgeheim-env-932"]}}},
            {"app": {"Env": {"MODUS": "***", "LIJST": "***"}}},
            id="object_hoofdletter_sleutel",
        ),
        pytest.param(
            {"app": {"environment": ["DB_HOST=proefgeheim-env-933", "MODUS=proefgeheim-env-934", "ALLEEN"]}},
            {"app": {"environment": ["DB_HOST", "MODUS", "ALLEEN"]}},
            id="tekstlijst",
        ),
        pytest.param(
            {"app": {"envs": ["X=proefgeheim-env-935", {"name": "Y", "value": "proefgeheim-env-936"}, 42]}},
            {"app": {"envs": ["X", {"name": "Y", "value": "***"}, "***"]}},
            id="gemengde_lijst",
        ),
        pytest.param(
            {"name": "X", "value": "proefgeheim-env-937"},
            {"name": "X", "value": "***"},
            id="paar_direct_onder_values",
        ),
        pytest.param(
            {"app": {"extra": [{"Name": "ENCRYPTION_KEY", "Value": "proefgeheim-env-938"}, {"NAME": "B", "VALUE": 5}]}},
            {"app": {"extra": [{"Name": "ENCRYPTION_KEY", "Value": "***"}, {"NAME": "B", "VALUE": "***"}]}},
            id="paar_met_hoofdletters",
        ),
    ],
)
@pytest.mark.usefixtures("oude_cataloguspreview")
def test_omgevingsvariabelen_in_andere_vormen_alleen_met_naam(stack: Stack, values: Any, verwacht: Any) -> None:
    """S-P2-040, herstelronde 3 (besluit regisseur; ADR-0030 besluit 28 en 32): van een omgevingsvariabele van een
    catalogusapp staat alleen de naam in de preview, ook als hij geen paar ``name`` + ``value`` in kleine letters is:
    waarden onder een sleutel ``environment``, ``env`` of ``envs`` (object of lijst; ``NAAM=waarde`` als alleen
    ``NAAM``), een paar direct onder ``values`` en een paar met hoofdletters (``Name``/``Value``). Leeg en ja/nee
    blijven zichtbaar, zoals bij een paar."""
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"] == verwacht, r.text
    assert "proefgeheim" not in r.text and "proefgeheim" not in stack.admin.get("/api/v1/actions").text


@pytest.mark.parametrize(
    ("values", "verwacht"),
    [
        # G1 (R-VEILIG-9): een object met een variabele NAME is geen paar; onder een omgevingssleutel alleen namen.
        pytest.param(
            {"app": {"environment": {"NAME": "mijnapp", "DB_HOST": "proefgeheim-g1a"}}},
            {"app": {"environment": {"NAME": "***", "DB_HOST": "***"}}},
            id="g1_object_met_NAME",
        ),
        pytest.param(
            {"app": {"env": [{"Name": "mijnapp", "DB_HOST": "proefgeheim-g1b"}]}},
            {"app": {"env": [{"Name": "***", "DB_HOST": "***"}]}},
            id="g1_lijst_object_met_Name",
        ),
        pytest.param(
            {"app": {"environment": [{"name": "DB_HOST", "value": "proefgeheim-g1c", "uitleg": "proefgeheim-g1d"}]}},
            {"app": {"environment": [{"name": "DB_HOST", "value": "***", "uitleg": "***"}]}},
            id="g1_paar_met_extra_veld",
        ),
        # G2 (R-VEILIG-10): tekst onder een omgevingssleutel, per regel alleen een naam.
        pytest.param(
            {"app": {"environment": ["postgres://beheer:proefgeheim-g2a@db/app"]}},
            {"app": {"environment": ["postgres"]}},
            id="g2_url_met_wachtwoord",
        ),
        pytest.param(
            {"app": {"env": "Bearer proefgeheim-g2b-abcdefgh"}},
            {"app": {"env": "***"}},
            id="g2_bearer_als_losse_tekst",
        ),
        pytest.param(
            {"app": {"environment": ["https://beheer:proefgeheim-g2c@host/x?sslmode=require"]}},
            {"app": {"environment": ["https"]}},
            id="g2_url_met_query",
        ),
        pytest.param(
            {"app": {"environment": ["DB_HOST: proefgeheim-g2d", "export DB=proefgeheim-g2e"]}},
            {"app": {"environment": ["DB_HOST", "***"]}},
            id="g2_dubbele_punt_en_geen_naam",
        ),
        pytest.param(
            {"app": {"environment": "DB_HOST=x\nLD_PRELOAD=/opt/proefgeheim-g2f.so"}},
            {"app": {"environment": "DB_HOST\nLD_PRELOAD"}},
            id="g2_meerdere_regels",
        ),
        # G3 (R-VEILIG-11): Key/Value in elke schrijfwijze.
        pytest.param(
            {
                "app": {
                    "labels": [{"Key": "x.token", "Value": "proefgeheim-g3a"}, {"KEY": "x.info", "VALUE": "zichtbaar"}]
                }
            },
            {"app": {"labels": [{"Key": "x.token", "Value": "***"}, {"KEY": "x.info", "VALUE": "zichtbaar"}]}},
            id="g3_Key_Value",
        ),
        pytest.param(
            {"app": {"labels": [{"KEY": "proef.password", "VALUE": "proefgeheim-g3b"}]}},
            {"app": {"labels": [{"KEY": "proef.password", "VALUE": "***"}]}},
            id="g3_KEY_VALUE",
        ),
        # G4 (R-VEILIG-12): elke sleutel met een omgevingsbetekenis (genormaliseerd: bevat "env").
        pytest.param(
            {
                "app": {
                    "additional_envs": ["DB_HOST=proefgeheim-g4a"],
                    "Additional-Envs": {"DB_HOST": "proefgeheim-g4b"},
                }
            },
            {"app": {"additional_envs": ["DB_HOST"], "Additional-Envs": {"DB_HOST": "***"}}},
            id="g4_additional_envs",
        ),
        pytest.param(
            {"app": {"env_vars": {"DB_HOST": "proefgeheim-g4c"}, "environment_variables": ["DB_HOST=proefgeheim-g4d"]}},
            {"app": {"env_vars": {"DB_HOST": "***"}, "environment_variables": ["DB_HOST"]}},
            id="g4_env_vars_en_environment_variables",
        ),
        pytest.param(
            {"app": {"additional_envs": ["DB_WACHTWOORD=proefgeheim-g4e"]}},
            {"app": {"additional_envs": ["DB_WACHTWOORD"]}},
            id="g4_geheime_naam_in_een_tekst",
        ),
    ],
)
@pytest.mark.usefixtures("oude_cataloguspreview")
def test_omgevingscontext_en_paren_volgens_een_regel(stack: Stack, values: Any, verwacht: Any) -> None:
    """S-P2-040, herstelronde 4 (R-VEILIG-9 t/m 12; besluit regisseur; ADR-0030 besluit 32): onder een sleutel met een
    omgevingsbetekenis (``env``, ``environment``, ``additional_envs``, ``env_vars``, … in elke schrijfwijze) staan
    alleen namen: een object met zijn sleutels en ``***``, een tekst per regel als naam (anders ``***``), een paar met
    alleen de naam. ``key``/``name``/``value`` tellen in elke schrijfwijze; een paar alleen met naam én waarde."""
    make_user(stack.admin, "kijker7", "viewer")
    kijker = login_as(stack.app, "kijker7")
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    assert r.json()["preview"]["wijziging"]["waarden"] == verwacht, r.text
    assert "proefgeheim" not in r.text and "proefgeheim" not in _kijkers_tekst(stack, kijker, r.json()["request_id"])


H1_NAMEN = ["api.key", "Api.Key", "x.api.key", "access-key", "access.key", "encryption_key", "license.key", "db_pwd",
            "auth"]  # fmt: skip


@pytest.mark.parametrize(
    ("values", "verwacht", "geheimen"),
    [
        # H1 (R-VEILIG-14): geheim-achtige sleutelnamen met punt of streep, op key, pwd en auth.
        pytest.param(
            {
                "app": {
                    **{n: f"proefgeheim-h1-{i}" for i, n in enumerate(H1_NAMEN)},
                    "labels": [{"key": "api.key", "value": "proefgeheim-h1-lab"}],
                }
            },
            {"app": {**dict.fromkeys(H1_NAMEN, "***"), "labels": [{"key": "api.key", "value": "***"}]}},
            ["proefgeheim"],
            id="h1_sleutelnamen",
        ),
        # H2 (R-VEILIG-17): een losse waarde onder een omgevingssleutel alleen als hij kort en niet willekeurig is.
        pytest.param(
            {
                "app": {
                    "environment": ["GeheimH4woord2x", "Z2VoZWltLWg0LWI2NC14eXo=", "production"],
                    "env": "Xk9fQ2mZ7pL4wR8tH4",
                    "envs": "Z2VoZWltLWg0LWI2NC14eQ==",
                    "env_vars": "DB_PASSWORD\nGeheimH4regel2",
                    "Environment": {"DB_HOST=proefgeheim-h2k": ""},
                }
            },
            {
                "app": {
                    "environment": ["***", "***", "production"],
                    "env": "***",
                    "envs": "***",
                    "env_vars": "DB_PASSWORD\n***",
                    "Environment": {"DB_HOST": ""},
                }
            },
            ["GeheimH4woord2x", "Z2VoZWltLWg0LWI2NC14", "Xk9fQ2mZ7pL4wR8tH4", "GeheimH4regel2", "proefgeheim"],
            id="h2_restvorm_onder_een_omgevingssleutel",
        ),
        # H3 (R-VEILIG-15): een URL met alleen een wachtwoord.
        pytest.param(
            {
                "app": {
                    "redis_url": "redis://:proefgeheim-h3a@redis:6379/0",
                    "labels": [{"key": "x.info", "value": "redis://:proefgeheim-h3b@redis:6379"}],
                }
            },
            {
                "app": {
                    "redis_url": "redis://:***@redis:6379/0",
                    "labels": [{"key": "x.info", "value": "redis://:***@redis:6379"}],
                }
            },
            ["proefgeheim"],
            id="h3_url_met_alleen_een_wachtwoord",
        ),
        # H4 (R-VEILIG-16): env als deel van een ander woord is geen omgevingscontext; alles blijft zichtbaar.
        pytest.param(
            {
                "openvpn": {"port": 1194, "server": "vpn.voorbeeld.invalid"},
                "envoy": {"listen_port": 8443},
                "venv": {"host_path": "/mnt/testpool/apps/venv"},
            },
            {
                "openvpn": {"port": 1194, "server": "vpn.voorbeeld.invalid"},
                "envoy": {"listen_port": 8443},
                "venv": {"host_path": "/mnt/testpool/apps/venv"},
            },
            ["***"],
            id="h4_env_in_een_ander_woord",
        ),
    ],
)
@pytest.mark.usefixtures("oude_cataloguspreview")
def test_vormen_van_herreview_4_volgens_het_principe(
    stack: Stack, values: Any, verwacht: Any, geheimen: list[str]
) -> None:
    """S-P2-040, herstelronde 5 (R-VEILIG-14 t/m 17; besluit regisseur; ADR-0030 besluit 32): de vormen H1-H4 van
    herreview 4 via de API. Geheim-achtige namen ook genormaliseerd en op ``key``/``pwd``/``auth``; een URL met alleen
    een wachtwoord; onder een omgevingssleutel (alleen als heel deel van de naam) een losse waarde alleen als hij kort
    en niet willekeurig is. Bij H4 staat er nergens ``***``: de beheerder ziet poort, server en hostpad."""
    make_user(stack.admin, "kijker8", "viewer")
    kijker = login_as(stack.app, "kijker8")
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    waarden = r.json()["preview"]["wijziging"]["waarden"]
    assert waarden == verwacht, r.text
    tekst = _kijkers_tekst(stack, kijker, r.json()["request_id"])
    for geheim in geheimen:
        if geheim == "***":
            assert geheim not in str(waarden), waarden
        else:
            assert geheim not in r.text and geheim not in tekst, geheim


J2_NAMEN = ["encryption_keys", "ssh_keys", "license_keys", "oauth", "jwt", "otp", "mnemonic", "salt", "seed"]


@pytest.mark.parametrize(
    ("values", "verwacht", "geheimen"),
    [
        # J1 (R-VEILIG-18): een deel dat op een omgevingswoord eindigt, en environ en dotenv: alleen namen.
        pytest.param(
            {
                "app": {
                    "additionalenvs": {"DB_HOST": "proefgeheim-j1a"},
                    "extraenv": {"DB_HOST": "proefgeheim-j1b"},
                    "appenv": {"DB_HOST": "proefgeheim-j1c"},
                    "environ": ["DB_HOST=proefgeheim-j1d"],
                    "dotenv": "DB_HOST=proefgeheim-j1e",
                    "additional_envs": {"DB_HOST": "proefgeheim-j1f"},
                }
            },
            {
                "app": {
                    "additionalenvs": {"DB_HOST": "***"},
                    "extraenv": {"DB_HOST": "***"},
                    "appenv": {"DB_HOST": "***"},
                    "environ": ["DB_HOST"],
                    "dotenv": "DB_HOST",
                    "additional_envs": {"DB_HOST": "***"},
                }
            },
            ["proefgeheim"],
            id="j1_omgevingswoord_aan_het_eind",
        ),
        # J2 (R-VEILIG-19): meervoud op keys en de andere geheim-achtige namen; de kale keys en pin niet.
        pytest.param(
            {"app": {**{n: f"proefgeheim-j2-{i}" for i, n in enumerate(J2_NAMEN)}, "keys": "zichtbaar", "pin": "z"}},
            {"app": {**dict.fromkeys(J2_NAMEN, "***"), "keys": "zichtbaar", "pin": "z"}},
            ["proefgeheim"],
            id="j2_meervoud_en_andere_namen",
        ),
        # J3 (R-VEILIG-20): onder een geheim-achtige naam blijft de vorm staan; een pad en public_key zichtbaar.
        pytest.param(
            {
                "app": {
                    "basic_auth": {"enabled": False},
                    "auth": {"enabled": True, "port": 8443},
                    "tls.key": "/mnt/testpool/certs/app.key",
                    "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 beheer",
                    "env_file": "/mnt/testpool/apps/app.env",
                    "client_secret": {"waarde": "proefgeheim-j3", "aan": True},
                }
            },
            {
                "app": {
                    "basic_auth": {"enabled": False},
                    "auth": {"enabled": True, "port": "***"},
                    "tls.key": "/mnt/testpool/certs/app.key",
                    "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 beheer",
                    "env_file": "/mnt/testpool/apps/app.env",
                    "client_secret": {"waarde": "***", "aan": True},
                }
            },
            ["proefgeheim"],
            id="j3_vorm_onder_een_geheime_naam",
        ),
    ],
)
@pytest.mark.usefixtures("oude_cataloguspreview")
def test_vormen_van_herreview_5_volgens_het_besluit(
    stack: Stack, values: Any, verwacht: Any, geheimen: list[str]
) -> None:
    """S-P2-040, herstelronde 6 (R-VEILIG-18 t/m 20; besluit regisseur; ADR-0030 besluit 32): de vormen J1-J3 van
    herreview 5 via de API, ook in wat een kijker ziet. Een deel van de sleutel dat op ``env``/``envs``/
    ``environment(s)`` eindigt, en ``environ`` en ``dotenv``, is een omgevingscontext; namen op ``keys`` en ``oauth``,
    ``jwt``, ``otp``, ``mnemonic``, ``salt`` en ``seed`` zijn geheim-achtig; onder een geheim-achtige naam blijft de
    vorm staan (sleutels, ja/nee, leeg), een absoluut pad blijft zichtbaar en ``public_key`` telt niet als geheim."""
    make_user(stack.admin, "kijker9", "viewer")
    kijker = login_as(stack.app, "kijker9")
    r = stel_voor(stack.admin, "app.install", app_target("huis"), _catalogus_waarden("huis", values))
    assert r.status_code == 201, r.text
    waarden = r.json()["preview"]["wijziging"]["waarden"]
    assert waarden == verwacht, r.text
    tekst = _kijkers_tekst(stack, kijker, r.json()["request_id"])
    for geheim in geheimen:
        assert geheim not in r.text and geheim not in tekst, geheim


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_geen_rauw_veld_in_de_wijziging_van_een_installatie(stack: Stack) -> None:
    """S-P2-040, herstelronde 4 (R-VEILIG-13; besluit regisseur punt 1): ook ``resources`` en de andere velden van een
    installatie (herstartbeleid, poorten, opslag, namen van omgevingsvariabelen, redenen en controles uit het manifest)
    gaan door de toonfunctie. Een geheim staat er nergens in, ook niet in de bewaarde preview."""
    values = {
        "resources": {"limits": {"cpus": 1}, "api_token": "proefgeheim-g6"},
        "restart_policy": "postgres://beheer:proefgeheim-r1@db/app",
        "ports": [{"port_number": 30200, "protocol": "Bearer proefgeheim-r2-abcdefgh"}],
        "storage": [{"type": "Bearer proefgeheim-r3-abcdefgh", "mount_path": "/data"}],
        "envs": [{"name": "Bearer proefgeheim-r4-abcdefgh", "value": "x"}],
    }
    params = _catalogus_waarden("huis", values)
    params["manifest"].update(
        version="postgres://beheer:proefgeheim-r5@db/app",
        install_reason="proef; sleutel Bearer proefgeheim-r6-abcdefgh",
        post_install_checks=[{"id": "web", "soort": "handmatig", "beschrijving_nl": "Bearer proefgeheim-r7-abcdefgh"}],
    )
    r = stel_voor(stack.admin, "app.install", app_target("huis"), params)
    assert r.status_code == 201, r.text
    w = r.json()["preview"]["wijziging"]
    assert w["resources"] == {"limits": {"cpus": 1}, "api_token": "***"} == w["waarden"]["resources"], w
    assert w["restart_policy"] == "postgres://beheer:***@db/app", w
    assert w["poorten"][0]["protocol"] == "Bearer ***" and w["opslag"][0]["type"] == "Bearer ***", w
    assert w["omgevingsvariabelen"] == ["***"], w
    assert w["manifest"]["version"] == "postgres://beheer:***@db/app", w
    assert w["reden_catalogusapp"] == "proef; sleutel Bearer ***", w
    assert w["controles_na_installatie"] == [{"id": "web", "soort": "handmatig", "beschrijving_nl": "Bearer ***"}], w
    assert "proefgeheim" not in r.text and "proefgeheim" not in stack.admin.get("/api/v1/actions").text
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(r.json()["request_id"]))
        assert rij is not None and "proefgeheim" not in str(rij.preview)


@pytest.mark.usefixtures("oude_cataloguspreview")
def test_de_toonfunctie_verbergt_niets_wat_de_beheerder_moet_zien(stack: Stack) -> None:
    """S-P2-040, herstelronde 4 (besluit regisseur punt 5; proef G5 van R-VEILIG): poorten, opslag, labels zonder
    geheim, run_as, dns_config, portalen, leeg en ja/nee blijven zichtbaar, bij de standaard Custom App en bij een
    catalogusapp; een losse naam onder ``env`` ook."""
    p = install_params(
        "demo-g5",
        portals=[{"name": "Web UI", "scheme": "http", "host": "0.0.0.0", "port": 30555, "path": "/zichtbaar-portal"}],
        labels=[{"key": "x.info", "value": "zichtbaar-label", "containers": []}],
        run_as_custom_user=True,
        run_as={"user": 568, "group": 568},
        dns_config={"nameservers": ["1.1.1.1"], "searches": [], "options": [{"key": "ndots", "value": "2"}]},
    )
    r = stel_voor(stack.admin, "app.install", app_target("demo-g5"), p)
    assert r.status_code == 201, r.text
    wz = r.json()["preview"]["wijziging"]
    verwacht = {k: v for k, v in p["app_create"]["values"].items() if k != "envs"}
    assert {k: v for k, v in wz["waarden"].items() if k != "envs"} == verwacht, wz
    assert wz["waarden"]["envs"] == ["APP_MODE"] and wz["omgevingsvariabelen"] == ["APP_MODE"], wz
    assert wz["poorten"] == [
        {"host_poort": 30555, "container_poort": 8080, "protocol": "tcp", "bind_mode": "published"}
    ]
    assert wz["opslag"] == [
        {"type": "host_path", "mount_path": "/data", "host_path": "/mnt/testpool/apps/demo-app", "alleen_lezen": False}
    ], wz
    assert wz["resources"] == {"limits": {"cpus": 2, "memory": 1024}} and wz["restart_policy"] == "unless-stopped"
    cat = {
        "network": {"web_port": {"bind_mode": "published", "port_number": 30080}},
        "storage": {"config": {"type": "ix_volume", "ix_volume_config": {"dataset_name": "config"}}},
        "run_as": {"user": 568, "group": 568},
        "resources": {"limits": {"cpus": 2, "memory": 4096}},
        "labels": [{"key": "x.info", "value": "zichtbaar-cat", "containers": ["app"]}],
        "app": {"env": "production", "debug": False, "leeg": "", "additional_envs": [{"name": "TZ", "value": "x"}]},
    }
    r = stel_voor(stack.admin, "app.install", app_target("cat-g5"), _catalogus_waarden("cat-g5", cat))
    assert r.status_code == 201, r.text
    verwacht_cat = copy.deepcopy(cat)
    verwacht_cat["app"]["additional_envs"] = [{"name": "TZ", "value": "***"}]
    assert r.json()["preview"]["wijziging"]["waarden"] == verwacht_cat, r.text


def test_open_voorstel_met_eigen_opdracht_van_voor_het_herstel_wordt_geweigerd(stack: Stack) -> None:
    """S-P2-040, R-VEILIG-1 (optie C): een voorstel dat vóór dit herstel met ``command`` is gemaakt, toonde die opdracht
    niet in de preview. Goedkeuren kan dan niet meer: ``501 capability_unavailable``, status ``geweigerd``, en de vrije
    tekst staat daarna niet meer in de database van de Hub (ADR-0030 besluit 28)."""
    admin = stack.admin
    r = stel_voor(admin, "app.install", app_target("demo"), install_params("demo"))
    assert r.status_code == 201 and r.json()["status"] == "wacht_op_goedkeuring", r.text
    v = r.json()
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(v["request_id"]))
        params = copy.deepcopy(rij.parameters)
        params["app_create"]["values"]["command"] = ["--wachtwoord", "oud-geheim-cmd-904"]
        rij.parameters = params
        db.commit()
    r = keur_goed(admin, v)
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"]["reden"] == "eigen_opdracht" and r.json()["details"]["velden"] == ["command"], r.text
    nu = haal(admin, v)
    assert nu["status"] == "geweigerd" and nu["goedkeuring"] is None, nu
    with stack.app.state.sessionmaker() as db:
        values = db.get(ActionRequest, uuid.UUID(v["request_id"])).parameters["app_create"]["values"]
    assert "command" not in values and values["vrije_tekst_gewist"] == ["command"], values
    assert schrijfaanroepen(stack.nas) == []


def test_herhaalde_noodstop_met_dezelfde_sleutel_zet_de_stand_echt(stack: Stack) -> None:
    """S-P2-040, R-VEILIG-4: aan, uit, en dan hetzelfde aan-verzoek nog eens (zelfde Idempotency-Key): de noodstop
    staat daarna echt aan, en het antwoord zegt dat ook. Dezelfde sleutel voor een ander verzoek blijft 422."""
    admin = stack.admin
    aan = idem()
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "onderhoud"}, headers=aan)
    assert r.status_code == 200 and r.json()["actief"] is True, r.text
    r = admin.put("/api/v1/actions/noodstop", json={"actief": False}, headers=idem())
    assert r.status_code == 200 and r.json()["actief"] is False, r.text
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "onderhoud"}, headers=aan)
    assert r.status_code == 200 and r.json()["actief"] is True, r.text
    assert admin.get("/api/v1/actions/noodstop").json()["actief"] is True
    r = admin.put("/api/v1/actions/noodstop", json={"actief": False}, headers=aan)
    assert r.status_code == 422 and r.json()["code"] == "idempotency_key_reused", r.text
    assert admin.get("/api/v1/actions/noodstop").json()["actief"] is True
    assert audit_acties(stack.app).count("action.emergency_stop.enabled") == 2


def test_herhaald_oud_uit_verzoek_heft_een_later_gezette_noodstop_niet_op(stack: Stack) -> None:
    """S-P2-040, herstelronde 2 (R-VEILIG-7): beheerder A zet de noodstop uit (sleutel K1), daarna zet beheerder B hem
    aan. Komt A's uit-verzoek met K1 nog eens binnen (herhaling van de client), dan wijzigt dat niets: de noodstop
    blijft aan en het antwoord geeft de werkelijke stand. Er komt geen nieuwe audit van uitzetten bij."""
    admin = stack.admin
    make_user(admin, "beheerder2", "admin")
    b = login_as(stack.app, "beheerder2")
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "eerste"}, headers=idem())
    assert r.status_code == 200, r.text
    k1 = idem()
    r = admin.put("/api/v1/actions/noodstop", json={"actief": False}, headers=k1)
    assert r.status_code == 200 and r.json()["actief"] is False, r.text
    r = b.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "nieuw incident"}, headers=idem())
    assert r.status_code == 200 and r.json()["actief"] is True, r.text
    uit_voor = audit_acties(stack.app).count("action.emergency_stop.disabled")
    r = admin.put("/api/v1/actions/noodstop", json={"actief": False}, headers=k1)
    assert r.status_code == 200, r.text
    assert r.json()["actief"] is True and r.json()["reden"] == "nieuw incident" and r.json()["door"] == "beheerder2"
    assert admin.get("/api/v1/actions/noodstop").json() == r.json()
    assert audit_acties(stack.app).count("action.emergency_stop.disabled") == uit_voor
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "x"}, headers=k1)
    assert r.status_code == 422 and r.json()["code"] == "idempotency_key_reused", r.text
