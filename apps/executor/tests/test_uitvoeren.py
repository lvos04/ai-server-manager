"""Executor voert ondertekende acties uit tegen de fake TrueNAS (contract 1.3 §8, ADR-0030; Sim-getest).

Positief én negatief: handtekening, vervaltijd, policy-hash, nonce, gebonden goedkeuring (EX19, EX20), allowlist
(EX17), pool niet gezond (EX11), nooit custom compose (EX47), container-only verwijderen, terugzetten met de bewaarde
vorige waarden, before/after-hash en readback; afwijking → de executor stopt.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from asm_policy import execreq
from asm_policy.etag import ABSENT, app_etag, dataset_etag, snapshot_etag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from executorhelpers import (
    NAS_HOST,
    POLICY,
    READ_KEY,
    WRITE_KEY,
    Hub,
    approved,
    auth,
    execute,
    nas_hub,
    set_write_key,
    signed,
    write_nas,
)
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS, _app
from fastapi.testclient import TestClient
from policyhelpers import DIGEST, DIGEST_B, HOST, approval_for, execution_request, install_params, proposal

from executor.journal import Journal
from executor.naslink import NasLinkStore
from executor.uitvoeren import Uitvoerder, pools_gezond

REPO = "ghcr.io/voorbeeld/demo-app"
Stack = tuple[Hub, TestClient, FakeTrueNAS]


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(tmp_path: Path, nas: FakeTrueNAS) -> Stack:
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    return hub, hub_client(hub), nas


def app_target(name: str) -> dict[str, Any]:
    return {"host_id": HOST, "app_id": name}


def etag(nas: FakeTrueNAS, name: str) -> str:
    return app_etag(nas.app(name), nas.data["app.image.query"])


def app_prop(nas: FakeTrueNAS, action: str, name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return proposal(action, app_target(name), parameters, expected_version=etag(nas, name))


def install_prop(name: str = "demo-app", **values: Any) -> dict[str, Any]:
    return proposal("app.install", app_target(name), install_params(name, **values), expected_version=ABSENT)


def writes(nas: FakeTrueNAS) -> list[str]:
    """Schrijfaanroepen die TrueNAS heeft gekregen (zonder het lezen van de app-configuratie)."""
    return [m for m in nas.mutations if m != "app.config"]


def journaal(c: TestClient, hub: Hub, request_id: str) -> dict[str, Any]:
    r = c.get(f"/api/v1/executions/{request_id}", headers=auth(hub.jwt()))
    assert r.status_code == 200, r.text
    return dict(r.json())


# ------------------------------------------------------------------ R1 zonder goedkeuring: starten, stoppen, herstart
def test_herstart_uitgevoerd_met_hashes_readback_en_journaal(stack: Stack) -> None:
    hub, c, nas = stack
    st = c.get("/api/v1/status").json()
    assert st["uitvoeren"] == {"mogelijk": True, "reden": None}
    assert st["schrijfsleutel"]["ingesteld"] is True and st["schrijfsleutel"]["laatste4"] == WRITE_KEY[-4:]
    assert st["truenas"]["adres"] == NAS_HOST and st["truenas"]["poort"] == nas.port
    assert WRITE_KEY not in str(st)

    prop = app_prop(nas, "app.restart", "my-house")
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 200, r.text
    uit = r.json()
    assert uit["status"] == "uitgevoerd" and uit["methode"] == "app.redeploy" and uit["action_id"] == "app.restart"
    assert uit["before_hash"] == prop["expected_version"] and uit["after_hash"] == uit["resource_etag"]
    assert uit["readback"]["staat"] == "RUNNING" and uit["policy_hash"] == POLICY.hash
    assert uit["request_id"] == prop["idempotency_key"] and uit["waarschuwingen"] == []
    assert writes(nas) == ["app.redeploy"] and ("app.redeploy", ["my-house"]) in nas.calls

    j = journaal(c, hub, prop["idempotency_key"])
    assert j["gestopt"] is False and len(j["uitvoeringen"]) == 1
    rij = j["uitvoeringen"][0]
    assert rij["status"] == "uitgevoerd" and rij["methode"] == "app.redeploy" and "nonce" not in rij
    assert rij["target"] == app_target("my-house") and rij["before_hash"] == uit["before_hash"]
    assert rij["after_hash"] == uit["after_hash"] and rij["finished_at"] is not None


def test_stoppen_en_starten_geven_een_nieuwe_etag(stack: Stack) -> None:
    hub, c, nas = stack
    voor = etag(nas, "my-house")
    r = execute(c, hub, signed(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R1"))
    assert r.status_code == 200, r.text
    assert r.json()["readback"]["staat"] == "STOPPED" and r.json()["resource_etag"] != voor
    assert r.json()["resource_etag"] == etag(nas, "my-house")
    r = execute(c, hub, signed(hub, app_prop(nas, "app.start", "my-house"), risk_class="R1"))
    assert r.status_code == 200 and r.json()["resource_etag"] == voor, r.text
    assert writes(nas) == ["app.stop", "app.start"]


def test_exacte_herhaling_met_hetzelfde_token_geeft_hetzelfde_antwoord(stack: Stack) -> None:
    hub, c, nas = stack
    req = signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")
    headers = auth(hub.jwt(), str(uuid.uuid4()))
    eerste = c.post("/api/v1/execute", json=req, headers=headers)
    tweede = c.post("/api/v1/execute", json=req, headers=headers)
    assert eerste.status_code == tweede.status_code == 200
    assert tweede.headers["Idempotent-Replay"] == "true" and tweede.json() == eerste.json()
    assert writes(nas) == ["app.redeploy"]  # één keer uitgevoerd


# ------------------------------------------------------------------ envelop: handtekening, tijden, policy-hash, nonce
def test_handtekening_tijden_en_policy_hash(stack: Stack) -> None:
    hub, c, nas = stack
    prop = app_prop(nas, "app.restart", "my-house")
    nu = datetime.now(UTC)

    vreemd = execution_request(Ed25519PrivateKey.generate(), prop, policy_hash=POLICY.hash, risk_class="R1")
    r = execute(c, hub, vreemd)
    assert r.status_code == 403 and r.json()["code"] == "handtekening_ongeldig", r.text

    # De JWT-sleutel van de Hub is niet de policy-sleutel: daarmee ondertekenen telt niet.
    r = execute(c, hub, execution_request(hub.key, prop, policy_hash=POLICY.hash, risk_class="R1"))
    assert r.status_code == 403 and r.json()["code"] == "handtekening_ongeldig", r.text

    geknoeid = signed(hub, prop, risk_class="R1")
    geknoeid["proposal"]["target"]["app_id"] = "mediaguard"
    r = execute(c, hub, geknoeid)
    assert r.status_code == 403 and r.json()["code"] == "handtekening_ongeldig", r.text

    r = execute(c, hub, signed(hub, prop, risk_class="R1", now=nu - timedelta(seconds=900), ttl=300))
    assert r.status_code == 403 and r.json()["code"] == "verzoek_verlopen", r.text
    r = execute(c, hub, signed(hub, prop, risk_class="R1", now=nu + timedelta(seconds=300)))
    assert r.status_code == 403 and r.json()["code"] == "verzoek_nog_niet_geldig", r.text
    r = execute(c, hub, signed(hub, prop, risk_class="R1", ttl=execreq.MAX_REQUEST_SECONDS + 60))
    assert r.status_code == 403 and r.json()["code"] == "verzoek_geldigheid_ongeldig", r.text

    ander = execution_request(hub.policy_key, prop, policy_hash="sha256:" + "0" * 64, risk_class="R1")
    r = execute(c, hub, ander)
    assert r.status_code == 409 and r.json()["code"] == "policy_hash_verschilt", r.text
    assert r.json()["details"]["eigen_policy_hash"] == POLICY.hash

    zonder = signed(hub, prop, risk_class="R1")
    del zonder["signature"]
    r = execute(c, hub, zonder)
    assert r.status_code == 422 and r.json()["code"] == "execution_request_ongeldig", r.text

    assert writes(nas) == [] and nas.logins == 0  # niets bereikte TrueNAS


def test_nonce_van_het_verzoek_is_eenmalig(stack: Stack) -> None:
    hub, c, nas = stack
    req = signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")
    assert execute(c, hub, req).status_code == 200
    # Hetzelfde ondertekende verzoek met een nieuw token en een nieuwe Idempotency-Key: de executor kent de nonce.
    r = execute(c, hub, req)
    assert r.status_code == 409 and r.json()["code"] == "nonce_al_gebruikt", r.text
    assert writes(nas) == ["app.redeploy"]


def test_nonce_overleeft_een_herstart_van_de_executor(stack: Stack) -> None:
    hub, c, nas = stack
    req = signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")
    assert execute(c, hub, req).status_code == 200
    r = execute(hub_client(hub), hub, req)  # nieuwe app-instantie, zelfde datamap
    assert r.status_code == 409 and r.json()["code"] == "nonce_al_gebruikt", r.text


# ------------------------------------------------------------------ risicoklasse en goedkeuring (EX18, EX19, EX20)
def test_kritieke_app_vraagt_r2_en_een_goedkeuring(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("authentik", "RUNNING", "ghcr.io/goauthentik/server:2025.2.4", 30140, 9000, "/mnt/testpool/a", "/data")
    )
    prop = app_prop(nas, "app.restart", "authentik")
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 403 and r.json()["code"] == "risicoklasse_te_laag", r.text
    assert r.json()["details"]["eigen_risk_class"] == "R2"
    r = execute(c, hub, signed(hub, prop, risk_class="R2"))
    assert r.status_code == 403 and r.json()["code"] == "goedkeuring_ontbreekt", r.text
    assert writes(nas) == []
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 200 and writes(nas) == ["app.redeploy"], r.text


def test_kritieke_app_onder_een_andere_naam_wordt_herkend_op_de_image(stack: Stack) -> None:
    """De executor herkent op de image uit zijn eigen readback, niet op de naam die de Hub noemt."""
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("dns", "RUNNING", "adguard/adguardhome:v0.107.52", 30053, 3000, "/mnt/testpool/a", "/data")
    )
    prop = app_prop(nas, "app.restart", "dns")
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 403 and r.json()["code"] == "risicoklasse_te_laag", r.text
    assert r.json()["details"]["eigen_risk_class"] == "R2" and writes(nas) == []
    assert execute(c, hub, approved(hub, prop)).status_code == 200


def test_goedkeuring_vervalt_bij_elk_gewijzigd_gebonden_veld(stack: Stack) -> None:
    """EX19: actie, doel, parameters, ETag, beleid en geldigheid zijn gebonden; één wijziging en de goedkeuring past
    niet meer."""
    hub, c, nas = stack
    prop = app_prop(nas, "app.uninstall", "my-house")
    ander_doel = app_prop(nas, "app.uninstall", "media-source-optimizer")
    nu = datetime.now(UTC)

    def met(**change: Any) -> dict[str, Any]:
        velden: dict[str, Any] = {"policy_hash": POLICY.hash, "risk_class": "R2", **change}
        return signed(hub, prop, risk_class="R2", approval=approval_for(prop, **velden))

    gevallen: list[tuple[dict[str, Any], int, str, list[str] | None]] = [
        (met(resource_etag="sha256:" + "1" * 64), 409, "goedkeuring_past_niet", ["resource_etag"]),
        (met(policy_hash="sha256:" + "2" * 64), 409, "goedkeuring_past_niet", ["policy_hash"]),
        (
            met(action_scope=execreq.action_scope("app.uninstall", ander_doel["target"], {})),
            409,
            "goedkeuring_past_niet",
            ["action_scope"],
        ),
        (
            met(action_scope=execreq.action_scope("app.stop", prop["target"], {})),
            409,
            "goedkeuring_past_niet",
            ["action_scope"],
        ),
        (met(risk_class="R1"), 409, "goedkeuring_past_niet", ["risk_class"]),
        (met(now=nu - timedelta(seconds=1200), ttl=600), 403, "goedkeuring_verlopen", None),
        (met(ttl=execreq.MAX_APPROVAL_SECONDS + 60), 403, "goedkeuring_ongeldig", None),
        (met(now=nu + timedelta(seconds=600)), 403, "goedkeuring_ongeldig", None),
    ]
    for req, status, code, gewijzigd in gevallen:
        r = execute(c, hub, req)
        assert (r.status_code, r.json()["code"]) == (status, code), r.text
        if gewijzigd is not None:
            assert r.json()["details"]["gewijzigd"] == gewijzigd
    assert writes(nas) == [] and nas.app("my-house") is not None


def test_doel_gewijzigd_sinds_de_goedkeuring_wordt_niet_uitgevoerd(stack: Stack) -> None:
    """EX19: de beheerder keurde een verwijdering goed; daarna veranderde de app. De executor leest zelf terug en
    weigert."""
    hub, c, nas = stack
    prop = app_prop(nas, "app.uninstall", "my-house")
    app = nas.app("my-house")
    assert app is not None
    nas._set_state(app, "STOPPED")  # wijziging buiten het platform om
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "doel_gewijzigd", r.text
    assert r.json()["details"] == {"verwacht": prop["expected_version"], "gevonden": etag(nas, "my-house")}
    assert writes(nas) == [] and nas.deleted == []
    # Een andere image telt net zo.
    prop = app_prop(nas, "app.uninstall", "my-house")
    nas._set_image(app, {"repository": "ghcr.io/voorbeeld/anders", "tag": "9.9.9"})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "doel_gewijzigd", r.text
    assert nas.deleted == []


def test_goedkeuring_is_eenmalig(stack: Stack) -> None:
    """EX20: dezelfde goedkeuring in een tweede (nieuw ondertekend) verzoek wordt geweigerd."""
    hub, c, nas = stack
    prop = app_prop(nas, "app.stop", "my-house")
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R2")
    r = execute(c, hub, signed(hub, prop, risk_class="R2", approval=approval))
    assert r.status_code == 200, r.text
    assert r.json()["request_id"] == approval["request_id"]
    r = execute(c, hub, signed(hub, prop, risk_class="R2", approval=copy.deepcopy(approval)))
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_al_gebruikt", r.text
    assert writes(nas) == ["app.stop"]


def test_herstelpunt_verplicht_bij_update_en_terugzetten(stack: Stack) -> None:
    hub, c, nas = stack
    prop = app_prop(nas, "app.update", "my-house", {"image": {"repository": REPO, "tag": f"2.0.0@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop, backup_checkpoint_id=None))
    assert r.status_code == 409 and r.json()["code"] == "backup_checkpoint_ontbreekt", r.text
    assert writes(nas) == []


# ------------------------------------------------------------------ beschermde apps en verboden acties
def test_emby_wordt_nooit_geraakt(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(_app("emby", "RUNNING", "emby/embyserver:4.8.10.0", 8096, 8096, "/mnt/t/e", "/c"))
    for action in ("app.stop", "app.restart", "app.uninstall", "app.update"):
        params = (
            {"image": {"repository": "emby/embyserver", "tag": f"4.9.0@{DIGEST}"}} if action == "app.update" else {}
        )
        r = execute(c, hub, approved(hub, app_prop(nas, action, "emby", params), risk_class="R3"))
        assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
        assert r.json()["details"]["blokkades"][0]["code"] == "emby_nooit_door_platform"
    assert writes(nas) == [] and nas.logins == 0


def test_emby_onder_een_andere_naam_wordt_herkend_op_de_image(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(_app("films", "RUNNING", "emby/embyserver:4.8.10.0", 8096, 8096, "/mnt/t/e", "/c"))
    for action in ("app.stop", "app.restart", "app.uninstall"):
        r = execute(c, hub, approved(hub, app_prop(nas, action, "films"), risk_class="R3"))
        assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
        assert r.json()["details"]["blokkades"][0]["code"] == "emby_nooit_door_platform"
    app = nas.app("films")
    assert writes(nas) == [] and app is not None and app["state"] == "RUNNING"


def test_de_executor_wijzigt_zichzelf_niet(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("ai-server-manager-executor", "RUNNING", "ghcr.io/lvos04/asm-executor:0.1.0", 30410, 30410, "/m", "/a")
    )
    r = execute(c, hub, approved(hub, app_prop(nas, "app.stop", "ai-server-manager-executor"), risk_class="R3"))
    assert r.status_code == 403 and r.json()["details"]["blokkades"][0]["code"] == "executor_niet_zelf", r.text
    assert writes(nas) == []


# ------------------------------------------------------------------ installeren (B01-003, EX47)
def test_installeren_als_standaard_custom_app_nooit_compose(stack: Stack) -> None:
    hub, c, nas = stack
    prop = install_prop()
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 200, r.text
    uit = r.json()
    assert uit["methode"] == "app.create" and uit["readback"]["catalogus_app"] == "ix-app"
    assert uit["readback"]["custom_app"] is False and uit["readback"]["images"] == [f"{REPO}:1.2.3@{DIGEST}"]
    assert uit["readback"]["digests"] == [f"{REPO}@{DIGEST}"] and uit["waarschuwingen"] == []
    assert uit["before_hash"] != uit["after_hash"] and uit["resource_etag"] == etag(nas, "demo-app")
    # Precies de velden van een standaard Custom App; nooit een compose-veld (EX47).
    assert len(nas.created) == 1
    body = nas.created[0]
    assert set(body) == {"app_name", "custom_app", "catalog_app", "train", "version", "values"}
    assert body["custom_app"] is False and body["catalog_app"] == "ix-app" and body["app_name"] == "demo-app"
    assert body["values"] == prop["parameters"]["app_create"]["values"]
    assert "app.create(custom_compose)" not in nas.mutations and "compose" not in str(body)


@pytest.mark.parametrize(
    "wijziging",
    [
        {"custom_compose_config": {"services": {"x": {"image": "busybox"}}}},
        {"custom_compose_config_string": "services: {}"},
        {"custom_app": True},
    ],
    ids=["compose_config", "compose_string", "custom_app_true"],
)
def test_compose_installatie_wordt_geweigerd(stack: Stack, wijziging: dict[str, Any]) -> None:
    hub, c, nas = stack
    prop = install_prop()
    prop["parameters"]["app_create"].update(wijziging)
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert nas.created == [] and writes(nas) == [] and nas.logins == 0


def test_latest_tag_en_gevaarlijke_waarden_worden_geweigerd(stack: Stack) -> None:
    hub, c, nas = stack
    slecht: list[dict[str, Any]] = [
        {"image": {"repository": REPO, "tag": "latest"}},
        {"image": {"repository": REPO, "tag": "1.2.3"}, "privileged": True},
        {
            "storage": [
                {
                    "type": "host_path",
                    "mount_path": "/var/run/docker.sock",
                    "host_path_config": {"path": "/var/run/docker.sock"},
                }
            ]
        },
        {"storage": [{"type": "host_path", "mount_path": "/data", "host_path_config": {"path": "/etc"}}]},
    ]
    for values in slecht:
        r = execute(c, hub, approved(hub, install_prop(**values)))
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert nas.created == [] and nas.logins == 0


def test_installeren_over_een_bestaande_app_wordt_geweigerd(stack: Stack) -> None:
    hub, c, nas = stack
    r = execute(c, hub, approved(hub, install_prop("my-house")))
    assert r.status_code == 409 and r.json()["code"] == "doel_gewijzigd", r.text
    assert nas.created == []


def test_kluisverwijzingen_bij_installeren_nog_niet_beschikbaar(stack: Stack) -> None:
    hub, c, nas = stack
    prop = install_prop(envs=[{"name": "API_TOKEN", "value": "vault://app/demo-app/api_token"}])
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"] == {"reden": "vault_verwijzingen"} and nas.created == []


def test_andere_digest_dan_goedgekeurd_is_een_afwijking_en_stopt_de_executor(stack: Stack) -> None:
    hub, c, nas = stack
    nas.digest_override[REPO] = DIGEST_B  # de registry levert iets anders dan de gepinde digest
    prop = install_prop()
    req = approved(hub, prop)
    r = execute(c, hub, req)
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    d = r.json()["details"]
    assert d["reden"] == "digest_verschilt" and d["gestopt"] is True and d["methode"] == "app.create"
    assert d["afwijkingen"] == [
        {"code": "digest_verschilt", "verwacht": f"{REPO}@{DIGEST}", "gevonden": [f"{REPO}@{DIGEST_B}"]}
    ]
    assert d["before_hash"] != d["after_hash"] and d["request_id"] == req["approval"]["request_id"]

    st = c.get("/api/v1/status").json()
    assert st["gestopt"]["reden"] == "digest_verschilt" and st["gestopt"]["request_id"] == d["request_id"]
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "executor_gestopt"}
    pagina = c.get("/").text
    assert "Gestopt" in pagina and "executor_gestopt" in pagina
    j = journaal(c, hub, d["request_id"])
    assert j["gestopt"] is True and j["uitvoeringen"][0]["status"] == "afwijking"

    # Gestopt: ook een onschuldige herstart wordt niet meer uitgevoerd, ook niet na een herstart van de executor.
    voor = list(nas.mutations)
    for client in (c, hub_client(hub)):
        r = execute(client, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
        assert r.status_code == 409 and r.json()["code"] == "executor_gestopt", r.text
        assert r.json()["details"]["reden"] == "digest_verschilt"
    assert nas.mutations == voor


# ------------------------------------------------------------------ verwijderen: alleen containers
def test_verwijderen_is_container_only_data_blijft(stack: Stack) -> None:
    hub, c, nas = stack
    datasets = sorted(nas.datasets())
    snapshots = copy.deepcopy(nas.data["snapshots"])
    r = execute(c, hub, approved(hub, app_prop(nas, "app.uninstall", "my-house")))
    assert r.status_code == 200, r.text
    assert r.json()["methode"] == "app.delete" and r.json()["resource_etag"] == ABSENT
    assert r.json()["readback"] == {"naam": "my-house", "afwezig": True}
    assert nas.deleted == [("my-house", {"remove_images": False, "remove_ix_volumes": False})]
    assert sorted(nas.datasets()) == datasets and nas.data["snapshots"] == snapshots
    assert writes(nas) == ["app.delete"]


def test_verwijderen_vraagt_altijd_een_goedkeuring(stack: Stack) -> None:
    hub, c, nas = stack
    prop = app_prop(nas, "app.uninstall", "my-house")
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 403 and r.json()["code"] == "risicoklasse_te_laag", r.text
    r = execute(c, hub, signed(hub, prop, risk_class="R2"))
    assert r.status_code == 403 and r.json()["code"] == "goedkeuring_ontbreekt", r.text
    assert nas.deleted == []


def test_verwijderen_van_een_app_die_er_niet_is(stack: Stack) -> None:
    hub, c, nas = stack
    prop = proposal("app.uninstall", app_target("bestaat-niet"), expected_version="sha256:" + "0" * 64)
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_niet", r.text
    assert writes(nas) == []


# ------------------------------------------------------------------ bijwerken en terugzetten
def test_bijwerken_en_terugzetten_met_de_bewaarde_vorige_waarden(stack: Stack) -> None:
    hub, c, nas = stack
    envs = [
        {"name": "APP_MODE", "value": "prod"},
        {"name": "PROEF_INSTELLING", "value": "waarde-alleen-in-de-kluis-417"},
    ]
    assert execute(c, hub, approved(hub, install_prop(envs=envs))).status_code == 200
    vorige = copy.deepcopy(nas.created[0]["values"])
    assert vorige["envs"] == envs

    prop = app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    req = approved(hub, prop)
    r = execute(c, hub, req)
    assert r.status_code == 200, r.text
    assert r.json()["methode"] == "app.update" and r.json()["readback"]["images"] == [f"{REPO}:1.2.4@{DIGEST_B}"]
    assert r.json()["readback"]["digests"] == [f"{REPO}@{DIGEST_B}"]
    naam, opties = nas.updated[-1]
    assert naam == "demo-app" and set(opties) == {"values"} and set(opties["values"]) == {"image"}
    assert opties["values"]["image"] == {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}", "pull_policy": "missing"}
    update_id = req["approval"]["request_id"]

    # Terugzetten = app.update met de waarden die de executor vóór de wijziging zelf uit app.config las.
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": update_id})
    r = execute(c, hub, approved(hub, terug))
    assert r.status_code == 200, r.text
    assert r.json()["methode"] == "app.update" and r.json()["readback"]["images"] == [f"{REPO}:1.2.3@{DIGEST}"]
    naam, opties = nas.updated[-1]
    assert naam == "demo-app" and opties == {"values": vorige}
    assert writes(nas) == ["app.create", "app.update", "app.update"]
    assert "app.update(custom_compose)" not in nas.mutations

    # De vorige waarden staan alleen versleuteld in het journaal van de executor (ook niet in het WAL-bestand).
    ruw = b"".join(p.read_bytes() for p in hub.settings.replay_db.parent.glob(hub.settings.replay_db.name + "*"))
    assert b"SQLite format 3" in ruw
    assert b"PROEF_INSTELLING" not in ruw and b"waarde-alleen-in-de-kluis-417" not in ruw


def test_terugzetten_zonder_bekend_herstelpunt(stack: Stack) -> None:
    hub, c, nas = stack
    prop = app_prop(nas, "app.rollback", "my-house", {"herstel_van": str(uuid.uuid4())})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "herstelpunt_onbekend", r.text
    assert writes(nas) == []


def test_herstelpunt_van_een_andere_app_telt_niet(stack: Stack) -> None:
    hub, c, nas = stack
    assert execute(c, hub, approved(hub, install_prop())).status_code == 200
    req = approved(
        hub, app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    )
    assert execute(c, hub, req).status_code == 200
    prop = app_prop(nas, "app.rollback", "my-house", {"herstel_van": req["approval"]["request_id"]})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "herstelpunt_onbekend", r.text
    assert len(nas.updated) == 1


def test_catalogusapp_naar_een_vaste_versie_en_terug(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("immich", "RUNNING", "ghcr.io/immich-app/server:1.0.0", 2283, 2283, "/m", "/d", catalog_app="immich")
    )
    r = execute(c, hub, approved(hub, app_prop(nas, "app.update", "immich", {"catalog_version": "1.0.1"})))
    assert r.status_code == 200 and r.json()["methode"] == "app.upgrade", r.text
    assert r.json()["readback"]["versie"] == "1.0.1"
    r = execute(c, hub, approved(hub, app_prop(nas, "app.rollback", "immich", {"catalog_version": "1.0.0"})))
    assert r.status_code == 200 and r.json()["methode"] == "app.rollback", r.text
    assert r.json()["readback"]["versie"] == "1.0.0"
    assert ("app.rollback", ["immich", {"app_version": "1.0.0", "rollback_snapshot": False}]) in nas.calls
    # Een image wijzigen kan alleen bij een standaard Custom App.
    prop = app_prop(nas, "app.update", "immich", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "doel_past_niet", r.text
    # En een catalogusversie kiezen niet bij een Custom App.
    r = execute(c, hub, approved(hub, app_prop(nas, "app.update", "my-house", {"catalog_version": "1.0.1"})))
    assert r.status_code == 409 and r.json()["code"] == "doel_past_niet", r.text


def test_compose_app_wordt_nooit_gewijzigd(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("yaml-app", "RUNNING", "ghcr.io/voorbeeld/yaml:1.0.0", 30999, 80, "/m", "/d", custom_app=True)
    )
    prop = app_prop(nas, "app.update", "yaml-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "doel_past_niet", r.text
    assert nas.updated == [] and writes(nas) == []


# ------------------------------------------------------------------ pool niet gezond (EX11)
@pytest.mark.parametrize("toestand", ["DEGRADED", "FAULTED", "onbekend", "geen_pools", "niet_healthy"])
def test_pool_niet_gezond_of_onbekend_blokkeert_opslagmutaties(stack: Stack, toestand: str) -> None:
    hub, c, nas = stack
    pool = nas.data["pool.query"][0]
    if toestand == "geen_pools":
        nas.data["pool.query"] = []
    elif toestand == "onbekend":
        pool["status"] = None
    elif toestand == "niet_healthy":
        pool["healthy"] = False
    else:
        pool["status"] = toestand
    snap = proposal(
        "zfs.snapshot.create",
        {"host_id": HOST, "dataset": "testpool/apps/mediaguard"},
        {"naam": "asm-proef"},
        expected_version=dataset_etag("testpool/apps/mediaguard"),
    )
    upd = app_prop(nas, "app.update", "my-house", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    for req in (approved(hub, install_prop()), signed(hub, snap, risk_class="R1"), approved(hub, upd)):
        r = execute(c, hub, req)
        assert r.status_code == 409 and r.json()["code"] == "pool_niet_gezond", r.text
        assert isinstance(r.json()["details"]["pools"], list)
    assert writes(nas) == [] and nas.created == []
    # Geen opslagmutatie: een app herstarten mag nog wel.
    r = execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
    assert r.status_code == 200 and writes(nas) == ["app.redeploy"], r.text


def test_pools_gezond_telt_onbekend_nooit_als_gezond() -> None:
    assert pools_gezond([{"name": "p", "status": "ONLINE", "healthy": True}])[0] is True
    for beeld in (None, [], "ONLINE", [{"name": "p", "status": "ONLINE"}], [{"name": "p", "healthy": True}]):
        assert pools_gezond(beeld)[0] is False
    twee = [{"name": "a", "status": "ONLINE", "healthy": True}, {"name": "b", "status": "DEGRADED", "healthy": False}]
    assert pools_gezond(twee) == (
        False,
        [{"pool": "a", "status": "ONLINE", "healthy": True}, {"pool": "b", "status": "DEGRADED", "healthy": False}],
    )


# ------------------------------------------------------------------ snapshots en sandbox-kloon
@pytest.mark.parametrize(("versie", "prefix"), [("25.04.2", "pool"), ("24.10.2", "zfs")])
def test_snapshot_maken_en_klonen_naar_de_sandbox(tmp_path: Path, versie: str, prefix: str) -> None:
    nas = write_nas(version=versie).start()
    try:
        hub = nas_hub(tmp_path / "appdata", nas)
        set_write_key(hub, nas)
        c = hub_client(hub)
        ds = "testpool/apps/mediaguard"
        prop = proposal(
            "zfs.snapshot.create",
            {"host_id": HOST, "dataset": ds},
            {"naam": "asm-proef"},
            expected_version=dataset_etag(ds),
        )
        r = execute(c, hub, signed(hub, prop, risk_class="R1"))
        assert r.status_code == 200, r.text
        assert r.json()["methode"] == f"{prefix}.snapshot.create"
        assert r.json()["readback"] == {"snapshot": f"{ds}@asm-proef", "aanwezig": True}
        assert r.json()["before_hash"] != r.json()["after_hash"]
        # Dezelfde naam nogmaals: geweigerd vóór de aanroep.
        prop2 = proposal(prop["action_id"], prop["target"], prop["parameters"], expected_version=dataset_etag(ds))
        r = execute(c, hub, signed(hub, prop2, risk_class="R1"))
        assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_al", r.text

        snap = f"{ds}@asm-proef"
        kloon = proposal(
            "zfs.snapshot.clone_to_sandbox",
            {"host_id": HOST, "snapshot": snap},
            {"doel_dataset": "testpool/asm-sandbox/proef"},
            expected_version=snapshot_etag(snap),
        )
        # De ouderdataset van de sandbox maakt de beheerder; ontbreekt die, dan faalt TrueNAS en is er niets veranderd.
        r = execute(c, hub, signed(hub, kloon, risk_class="R1"))
        assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
        nas.add_dataset("testpool/asm-sandbox")
        kloon2 = proposal(
            kloon["action_id"], kloon["target"], kloon["parameters"], expected_version=snapshot_etag(snap)
        )
        r = execute(c, hub, signed(hub, kloon2, risk_class="R1"))
        assert r.status_code == 200 and r.json()["methode"] == f"{prefix}.snapshot.clone", r.text
        assert r.json()["readback"] == {"dataset": "testpool/asm-sandbox/proef", "aanwezig": True}
        assert "testpool/asm-sandbox/proef" in nas.datasets()
        assert writes(nas) == [f"{prefix}.snapshot.create", f"{prefix}.snapshot.clone", f"{prefix}.snapshot.clone"]
    finally:
        nas.stop()


def test_snapshot_buiten_de_sandbox_of_op_een_onbekende_dataset(stack: Stack) -> None:
    hub, c, nas = stack
    snap = "testpool/apps@auto-latest"
    for doel in (
        "testpool/media/kloon",
        "testpool/asm-sandbox",
        "anderepool/asm-sandbox/x",
        "testpool/asm-sandbox/a/b",
    ):
        prop = proposal(
            "zfs.snapshot.clone_to_sandbox",
            {"host_id": HOST, "snapshot": snap},
            {"doel_dataset": doel},
            expected_version=snapshot_etag(snap),
        )
        r = execute(c, hub, signed(hub, prop, risk_class="R1"))
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    prop = proposal(
        "zfs.snapshot.create",
        {"host_id": HOST, "dataset": "testpool/bestaat-niet"},
        {"naam": "x"},
        expected_version=dataset_etag("testpool/bestaat-niet"),
    )
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_niet", r.text
    assert writes(nas) == []


# ------------------------------------------------------------------ TrueNAS werkt niet mee
def test_methode_ontbreekt_in_deze_versie_capability_unavailable(stack: Stack) -> None:
    hub, c, nas = stack
    nas.hidden.add("app.redeploy")
    r = execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"] == {"methoden": ["app.redeploy"]} and writes(nas) == []


def test_mislukte_job_zonder_wijziging_is_geen_afwijking(stack: Stack) -> None:
    hub, c, nas = stack
    nas.fail["app.redeploy"] = "image pull mislukt"
    prop = app_prop(nas, "app.restart", "my-house")
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
    d = r.json()["details"]
    assert d["reden"] == "job_mislukt" and d["before_hash"] == d["after_hash"]
    assert c.get("/api/v1/status").json()["gestopt"] is None
    rij = journaal(c, hub, prop["idempotency_key"])["uitvoeringen"][0]
    assert rij["status"] == "mislukt" and "image pull mislukt" in rij["detail"]
    # Niet gestopt: de volgende actie loopt gewoon.
    del nas.fail["app.redeploy"]
    assert execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")).status_code == 200


def test_job_die_slaagt_zonder_iets_te_doen_is_een_afwijking(stack: Stack) -> None:
    hub, c, nas = stack
    nas.silent_noop.add("app.stop")
    r = execute(c, hub, signed(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R1"))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    d = r.json()["details"]
    assert d["reden"] == "staat_verschilt" and d["gestopt"] is True
    assert d["afwijkingen"] == [{"code": "staat_verschilt", "verwacht": "STOPPED", "gevonden": "RUNNING"}]
    assert c.get("/api/v1/status").json()["gestopt"]["reden"] == "staat_verschilt"


def test_verwijderen_dat_niets_verwijdert_is_een_afwijking(stack: Stack) -> None:
    hub, c, nas = stack
    nas.silent_noop.add("app.delete")
    r = execute(c, hub, approved(hub, app_prop(nas, "app.uninstall", "my-house")))
    assert r.status_code == 409 and r.json()["details"]["reden"] == "nog_aanwezig", r.text


def test_mislukte_job_met_gewijzigde_toestand_is_een_afwijking(stack: Stack) -> None:
    """TrueNAS meldt een fout, maar de app is wel veranderd: de uitkomst is onbekend → stop."""
    hub, c, nas = stack
    echte = nas._write

    def half(method: str, params: list[Any]) -> Any:
        job_id = echte(method, params)
        if method == "app.stop":
            nas.jobs[job_id].update(state="FAILED", error="halverwege gestopt")
        return job_id

    nas._write = half  # type: ignore[method-assign]
    r = execute(c, hub, signed(hub, app_prop(nas, "app.stop", "my-house"), risk_class="R1"))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert r.json()["details"]["reden"] == "uitkomst_onbekend" and r.json()["details"]["gestopt"] is True


def test_alleen_lezen_sleutel_kan_niets_uitvoeren(tmp_path: Path, nas: FakeTrueNAS) -> None:
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas, READ_KEY, ["READONLY_ADMIN"])
    c = hub_client(hub)
    r = execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
    assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
    assert r.json()["details"]["reden"] == "truenas_geen_toegang"
    app = nas.app("my-house")
    assert app is not None and app["state"] == "RUNNING"


def test_ander_certificaat_dan_vastgelegd_de_sleutel_wordt_niet_verstuurd(tmp_path: Path, nas: FakeTrueNAS) -> None:
    hub = nas_hub(tmp_path / "appdata", nas)
    NasLinkStore(hub.settings.secrets_dir).save_key(NAS_HOST, nas.port, "0" * 64, WRITE_KEY, ["FULL_ADMIN"])
    c = hub_client(hub)
    r = execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
    assert r.status_code == 503 and r.json()["code"] == "certificaat_gewijzigd", r.text
    assert nas.logins == 0 and nas.calls == []


def test_truenas_onbereikbaar_of_sleutel_ingetrokken(stack: Stack) -> None:
    hub, c, nas = stack
    del nas.keys[WRITE_KEY]
    r = execute(c, hub, signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"))
    assert r.status_code == 503 and r.json()["code"] == "sleutel_geweigerd", r.text
    prop = app_prop(nas, "app.restart", "my-house")
    nas.offline()
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 503 and r.json()["code"] == "truenas_onbereikbaar", r.text
    assert writes(nas) == []


def test_onleesbare_sleutelopslag_voert_niets_uit(stack: Stack) -> None:
    hub, c, nas = stack
    prop = app_prop(nas, "app.restart", "my-house")
    (hub.settings.secrets_dir / "naslink.json").write_text("{kapot", encoding="utf-8")
    st = c.get("/api/v1/status").json()
    assert st["schrijfsleutel"] == {"ingesteld": False, "onleesbaar": True, "laatste4": None, "ingesteld_op": None}
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "sleutelopslag_onleesbaar"}
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert writes(nas) == [] and nas.logins == 0
    pagina = c.get("/").text
    assert "sleutelopslag_onleesbaar" in pagina and 'name="truenas_sleutel"' not in pagina


# ------------------------------------------------------------------ één tegelijk, journaal
def test_een_uitvoering_tegelijk_en_de_nonce_blijft_bruikbaar(tmp_path: Path, nas: FakeTrueNAS) -> None:
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    uitvoerder = Uitvoerder(
        policy=POLICY,
        journal=Journal(hub.settings.replay_db, hub.settings.secrets_dir),
        naslink=NasLinkStore(hub.settings.secrets_dir),
        settle_seconds=0.5,
        poll_seconds=0.05,
        timeout=5,
    )
    keys = [hub.policy_key.public_key()]
    req = signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1")
    assert uitvoerder._bezig.acquire(blocking=False)
    try:
        uit = uitvoerder.run(req, keys)
        assert uit.status == 409 and uit.body["code"] == "executor_bezet"
    finally:
        uitvoerder._bezig.release()
    assert writes(nas) == []
    uit = uitvoerder.run(req, keys)  # dezelfde nonce: was nog niet verbruikt
    assert uit.status == 200 and uit.body["status"] == "uitgevoerd"


def test_onbruikbaar_journaal_voert_niets_uit(tmp_path: Path, nas: FakeTrueNAS) -> None:
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    kapot = tmp_path / "geen-map" / "executor.sqlite3"
    uitvoerder = Uitvoerder(
        policy=POLICY,
        journal=Journal(kapot, hub.settings.secrets_dir),
        naslink=NasLinkStore(hub.settings.secrets_dir),
    )
    uit = uitvoerder.run(
        signed(hub, app_prop(nas, "app.restart", "my-house"), risk_class="R1"), [hub.policy_key.public_key()]
    )
    assert uit.status == 503 and uit.body["code"] == "journaal_niet_beschikbaar"
    assert writes(nas) == [] and nas.logins == 0


def test_journaal_alleen_voor_de_hub(stack: Stack) -> None:
    hub, c, _nas = stack
    rid = str(uuid.uuid4())
    assert c.get(f"/api/v1/executions/{rid}").status_code == 401
    r = c.get(f"/api/v1/executions/{rid}", headers=auth(hub.user_jwt(["admin"])))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    r = c.get("/api/v1/executions/geen-uuid", headers=auth(hub.jwt()))
    assert r.status_code == 422 and r.json()["code"] == "validation_error"
    assert journaal(c, hub, rid) == {"request_id": rid, "uitvoeringen": [], "gestopt": False}


def test_geen_enkele_route_voert_een_vrije_methode_uit(stack: Stack) -> None:
    """De client van de executor kent alleen leesmethoden en de methoden uit het beleid: er is geen doorgeefroute."""
    from executor.truenas import READ_METHODS, NasClient, NasFout

    toegestaan = {m for a in POLICY.acties.values() if a.uitvoerder == "executor" for m in a.truenas}
    assert toegestaan == {
        "app.redeploy",
        "app.stop",
        "app.start",
        "app.create",
        "app.update",
        "app.upgrade",
        "app.rollback",
        "app.delete",
        "pool.snapshot.create",
        "zfs.snapshot.create",
        "pool.snapshot.clone",
        "zfs.snapshot.clone",
    }
    assert not {m for m in READ_METHODS | toegestaan if "dataset.delete" in m or "snapshot.delete" in m}
    nas_client = NasClient(NAS_HOST, 1, "0" * 64, allowed=frozenset(toegestaan))
    for methode in ("pool.dataset.delete", "filesystem.put", "core.bulk", "system.shutdown", "user.create"):
        with pytest.raises(NasFout) as exc:
            nas_client.call(methode)
        assert exc.value.code == "methode_niet_toegestaan"
