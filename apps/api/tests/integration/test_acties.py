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

from hub.models import ActionRequest

pytestmark = pytest.mark.integration
TOKEN = "gotify-app-token-voor-test"


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
    for aid in ("app.start", "app.restart"):
        assert (acties[aid]["risk_class_custom_app"], acties[aid]["goedkeuring_nodig_custom_app"]) == ("R1", False)
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
        # Bekende actie van een andere eigenaar: de klasse uit het beleid blijft staan, uitvoeren kan hier niet.
        ("sso.oidc.hub.register", 501, "capability_unavailable", "R2"),
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


def test_een_tweede_emby_installeren_onder_een_andere_naam_wordt_geweigerd(stack: Stack) -> None:
    """HARDE EIS (S-P2-010, bouwpunt 6g): ``app.install`` met ``catalog_app: "emby"`` onder een andere naam valt onder
    APP-EMBY, ook voor een beheerder. Tegenproef: een andere catalogusapp onder een eigen naam wordt gewoon voorgesteld
    (R2, met goedkeuring)."""
    key, r = _voorstel(stack.admin, "app.install", app_target("mediaspeler"), _catalogus_install("mediaspeler", "emby"))
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [b["code"] for b in r.json()["details"]["blokkades"]], r.text
    assert haal(stack.admin, key)["status"] == "geweigerd"
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


def test_catalogusapp_met_extra_rechten_wordt_geweigerd(stack: Stack) -> None:
    """S-P2-010, R-VEILIG-3 (ADR-0030 besluit 6): ook de eigen waarden van een catalogusapp krijgen geen extra
    capabilities, apparaten, host-PID/-IPC, gedeeld netwerk of GPU zonder ``gpu: intel_render``, ook genest. De Hub
    geeft 422 met de code per sleutel en bewaart niets. Tegenproef: dezelfde app zonder die waarden wordt
    voorgesteld."""
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
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text


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
    assert r.status_code == 201 and r.json()["risk_class"] == "R2", r.text
    assert schrijfaanroepen(stack.nas) == []


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
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
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
