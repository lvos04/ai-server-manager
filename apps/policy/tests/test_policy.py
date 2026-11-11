"""Risicobeleid: laden, policy_hash, classificatie (EX18, EX27), parameters (EX47) en ExecutionRequest."""

from __future__ import annotations

import copy
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from policyhelpers import DIGEST, DIGEST_B, HOST, POLICY_DIR, approval_for, execution_request, install_params, proposal

from asm_policy import PolicyError, execreq, load_policy, policy_hash
from asm_policy.canonical import CanonicalError, canonical_json, canonical_sha256
from asm_policy.engine import classify, recognize
from asm_policy.etag import ABSENT, app_etag
from asm_policy.loader import is_read_only
from asm_policy.params import expected_image, validate_parameters, validate_target, vault_refs
from asm_policy.verify import check_decision, check_envelope

POLICY = load_policy(POLICY_DIR)
APP = {"host_id": HOST, "app_id": "demo-app"}


def kopie(tmp_path: Path) -> Path:
    doel = tmp_path / "policy"
    shutil.copytree(POLICY_DIR, doel)
    return doel


# ------------------------------------------------------------------ laden en policy_hash
def test_beleid_laadt_en_allowlist_is_die_van_het_contract() -> None:
    assert POLICY.hash == policy_hash(POLICY_DIR)
    assert POLICY.hash.startswith("sha256:") and len(POLICY.hash) == 71
    assert POLICY.executor_allowlist() == [
        "app.install",
        "app.restart",
        "app.rollback",
        "app.start",
        "app.stop",
        "app.uninstall",
        "app.update",
        "zfs.snapshot.clone_to_sandbox",
        "zfs.snapshot.create",
    ]
    assert POLICY.acties["notification.send"].uitvoerder == "hub:gotify"
    assert POLICY.acties["sso.sessions.revoke"].eigenaar == "home-control-hub"
    assert not POLICY.acties["sso.oidc.hub.register"].ai_mag_voorstellen


def test_policy_hash_verandert_bij_elke_byte_en_negeert_de_readme(tmp_path: Path) -> None:
    doel = kopie(tmp_path)
    assert policy_hash(doel) == POLICY.hash
    (doel / "README.md").write_text("iets anders", encoding="utf-8")
    assert policy_hash(doel) == POLICY.hash
    with (doel / "apps.yaml").open("ab") as fh:
        fh.write(b"\n")
    assert policy_hash(doel) != POLICY.hash
    doel2 = kopie(tmp_path / "b")
    (doel2 / "extra.yaml").write_text("schema: asm-policy/1\n", encoding="utf-8")
    assert policy_hash(doel2) != POLICY.hash


@pytest.mark.parametrize(
    ("bestand", "oud", "nieuw"),
    [
        ("acties.yaml", "    klasse: R1\n    klasse_kritiek: R2\n", "    klasse: R3\n    klasse_kritiek: R2\n"),
        ("acties.yaml", "    doel: app\n", "    doel: iets\n"),
        ("acties.yaml", "  app.restart:\n", "  pool.dataset.delete:\n"),
        ("acties.yaml", "schema: asm-policy/1", "schema: asm-policy/2"),
        ("acties.yaml", "    max_per_uur: 3\n", "    max_per_uur: 3\n    shell: true\n"),
        ("blokkades.yaml", "\ndynamisch:\n", "\ndynamisch_weg:\n"),
        ("apps.yaml", "  dataset_naam: asm-sandbox", "  dataset_naam: ../x"),
    ],
)
def test_ongeldig_beleid_wordt_geweigerd(tmp_path: Path, bestand: str, oud: str, nieuw: str) -> None:
    doel = kopie(tmp_path)
    tekst = (doel / bestand).read_text(encoding="utf-8")
    assert oud in tekst
    (doel / bestand).write_text(tekst.replace(oud, nieuw, 1), encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy(doel)


def test_ontbrekend_of_onleesbaar_beleid_is_fail_closed(tmp_path: Path) -> None:
    doel = kopie(tmp_path)
    (doel / "blokkades.yaml").unlink()
    with pytest.raises(PolicyError):
        load_policy(doel)
    doel2 = kopie(tmp_path / "b")
    (doel2 / "apps.yaml").write_text("schema: [", encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy(doel2)
    with pytest.raises(PolicyError):
        policy_hash(tmp_path / "leeg")


def test_is_read_only(tmp_path: Path) -> None:
    doel = kopie(tmp_path)
    assert not is_read_only(doel)
    for p in doel.iterdir():
        p.chmod(0o444)
    doel.chmod(0o555)
    try:
        assert is_read_only(doel)
    finally:
        doel.chmod(0o755)


# ------------------------------------------------------------------ classificatie
def test_ex18_risk_claim_telt_niet_en_destructief_is_altijd_r3_en_geweigerd() -> None:
    # classify krijgt de risk_claim niet eens; een voorstel "R0" voor pool.dataset.delete wordt R3 en geweigerd.
    c = classify(POLICY, action_id="pool.dataset.delete", target={"host_id": HOST}, parameters={}, actor_type="ai")
    assert c.risk_class == "R3" and c.geweigerd and c.requires_approval
    assert [b.code for b in c.blokkades] == ["actie_verboden_destructief"]
    assert "BLK-DESTRUCTIEF" in c.rule_ids


@pytest.mark.parametrize(
    ("action_id", "code"),
    [
        ("shell.exec", "actie_verboden_shell"),
        ("system.sudo", "actie_verboden_shell"),
        ("zfs.snapshot.delete", "actie_verboden_destructief"),
        ("app.uninstall_data", "actie_verboden_destructief"),
    ],
)
def test_verboden_patronen(action_id: str, code: str) -> None:
    c = classify(POLICY, action_id=action_id, target={}, parameters={}, actor_type="user")
    assert c.geweigerd and c.risk_class == "R3"
    assert code in [b.code for b in c.blokkades]


@pytest.mark.parametrize(
    ("action_id", "target", "parameters"),
    [
        ("smart_home.boiler.on", {}, {}),
        ("app.restart", {"host_id": HOST, "app_id": "boiler-control"}, {}),
        (
            "app.install",
            {"host_id": HOST, "app_id": "x"},
            {"app_create": {"values": {"envs": [{"name": "WARM_WATER"}]}}},
        ),
        ("app.restart", {"host_id": HOST, "app_id": "x"}, {"apparaat": "Water Heater"}),
    ],
)
def test_ex27_boiler_wordt_altijd_geweigerd(action_id: str, target: dict[str, Any], parameters: dict[str, Any]) -> None:
    for actor in ("user", "ai", "flow"):
        c = classify(POLICY, action_id=action_id, target=target, parameters=parameters, actor_type=actor)
        assert c.geweigerd and c.risk_class == "R3"
        assert "boiler_verboden" in [b.code for b in c.blokkades]


def test_melding_over_de_boiler_schakelt_niets_en_mag() -> None:
    c = classify(
        POLICY,
        action_id="notification.send",
        target={"host_id": HOST},
        parameters={"titel": "Boiler", "tekst": "De boilersensor is offline.", "prioriteit": 5},
        actor_type="ai",
    )
    assert not c.geweigerd and c.risk_class == "R0" and not c.requires_approval


def test_onbekend_gereserveerd_en_klassen() -> None:
    onbekend = classify(POLICY, action_id="app.frobnicate", target={}, parameters={}, actor_type="user")
    assert not onbekend.known and onbekend.risk_class == "R3"
    mg = classify(POLICY, action_id="mediaguard.media.replace", target={}, parameters={}, actor_type="user")
    assert mg.gereserveerd is not None and mg.gereserveerd.code == "handmatig_in_mediaguard"
    huis = classify(POLICY, action_id="my_house.lamp.on", target={}, parameters={}, actor_type="user")
    assert huis.gereserveerd is not None and huis.gereserveerd.code == "capability_unavailable"
    r1 = classify(POLICY, action_id="app.restart", target=APP, parameters={}, actor_type="ai")
    assert (r1.risk_class, r1.requires_approval, r1.geweigerd) == ("R1", False, False)
    r2 = classify(POLICY, action_id="app.update", target=APP, parameters={}, actor_type="user")
    assert (r2.risk_class, r2.requires_approval, r2.requires_backup, r2.opslagmutatie) == ("R2", True, True, True)
    kritiek = classify(
        POLICY, action_id="app.restart", target=APP, parameters={}, actor_type="ai", herkend_als="authentik"
    )
    assert kritiek.risk_class == "R2" and kritiek.requires_approval and "KRITIEK:authentik" in kritiek.rule_ids
    claim = classify(
        POLICY, action_id="app.restart", target=APP, parameters={}, actor_type="ai", requires_backup_claim=True
    )
    assert claim.requires_backup
    geen_claim = classify(
        POLICY, action_id="app.update", target=APP, parameters={}, actor_type="ai", requires_backup_claim=False
    )
    assert geen_claim.requires_backup  # een voorstel kan de eis nooit verlagen


def test_beschermde_apps_en_alleen_beheerder() -> None:
    for aid in ("app.stop", "app.restart", "app.update", "app.uninstall"):
        c = classify(POLICY, action_id=aid, target=APP, parameters={}, actor_type="user", herkend_als="emby")
        assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades]
    zelf = classify(
        POLICY,
        action_id="app.uninstall",
        target=APP,
        parameters={},
        actor_type="user",
        herkend_als="ai-server-manager-executor",
    )
    assert "executor_niet_zelf" in [b.code for b in zelf.blokkades]
    mg = classify(
        POLICY, action_id="app.update", target=APP, parameters={}, actor_type="user", herkend_als="mediaguard"
    )
    assert "mediaguard_upgradebewijs_ontbreekt" in [b.code for b in mg.blokkades]
    mg_ok = classify(
        POLICY, action_id="app.restart", target=APP, parameters={}, actor_type="user", herkend_als="mediaguard"
    )
    assert not mg_ok.geweigerd
    sso = {"host_id": HOST, "app_id": "home-control-hub", "resource": "hub"}
    ai = classify(POLICY, action_id="sso.sessions.revoke", target=sso, parameters={}, actor_type="ai")
    assert "alleen_beheerder" in [b.code for b in ai.blokkades]
    mens = classify(POLICY, action_id="sso.sessions.revoke", target=sso, parameters={}, actor_type="user")
    assert not mens.geweigerd and mens.requires_approval
    vreemd = classify(POLICY, action_id="app.restart", target=APP, parameters={}, actor_type="robot")
    assert "actor_onbekend" in [b.code for b in vreemd.blokkades]


def test_herkenning_is_alleen_strenger() -> None:
    assert recognize(POLICY, "emby") == "emby"
    assert recognize(POLICY, "mijn-server", ["docker.io/emby/embyserver:4.9.1.80"]) == "emby"
    assert recognize(POLICY, "authentik-server") == "authentik"
    assert recognize(POLICY, "jelly-leon-platform") == "jelly-leon-platform"
    assert recognize(POLICY, "ai-server-manager-executor") == "ai-server-manager-executor"
    assert recognize(POLICY, "iets-anders", ["ghcr.io/x/y:1"]) is None
    assert recognize(POLICY, None) is None


# ------------------------------------------------------------------ doel en parameters
def test_doelschema() -> None:
    restart = POLICY.acties["app.restart"]
    assert validate_target(restart, APP) == []
    for fout in ({"host_id": "ander", "app_id": "x"}, {"host_id": HOST}, {"host_id": HOST, "app_id": "X y"}, [], None,
                 {"host_id": HOST, "app_id": "x", "extra": 1}):  # fmt: skip
        assert validate_target(restart, fout), fout
    snap = POLICY.acties["zfs.snapshot.create"]
    assert validate_target(snap, {"host_id": HOST, "dataset": "testpool/apps/demo"}) == []
    assert validate_target(snap, {"host_id": HOST, "dataset": "../etc"})
    kloon = POLICY.acties["zfs.snapshot.clone_to_sandbox"]
    assert validate_target(kloon, {"host_id": HOST, "snapshot": "testpool/apps/demo@asm-1"}) == []
    assert validate_target(kloon, {"host_id": HOST, "snapshot": "testpool/apps/demo"})


def test_parameters_eenvoudige_acties() -> None:
    restart = POLICY.acties["app.restart"]
    assert validate_parameters(POLICY, restart, APP, {}) == []
    assert validate_parameters(POLICY, restart, APP, {"force": True})
    snap = POLICY.acties["zfs.snapshot.create"]
    doel = {"host_id": HOST, "dataset": "testpool/apps/demo"}
    assert validate_parameters(POLICY, snap, doel, {"naam": "asm-voor-update", "recursief": False}) == []
    assert validate_parameters(POLICY, snap, doel, {"naam": "a b"})
    kloon = POLICY.acties["zfs.snapshot.clone_to_sandbox"]
    bron = {"host_id": HOST, "snapshot": "testpool/apps/demo@asm-1"}
    assert validate_parameters(POLICY, kloon, bron, {"doel_dataset": "testpool/asm-sandbox/proef"}) == []
    for fout in (
        "testpool/apps/proef",
        "anderepool/asm-sandbox/proef",
        "testpool/asm-sandbox",
        "testpool/asm-sandbox/a/b",
    ):
        assert validate_parameters(POLICY, kloon, bron, {"doel_dataset": fout}), fout
    meld = POLICY.acties["notification.send"]
    assert validate_parameters(POLICY, meld, {"host_id": HOST}, {"titel": "T", "tekst": "x", "prioriteit": 5}) == []
    assert validate_parameters(POLICY, meld, {"host_id": HOST}, {"titel": "T", "tekst": "x" * 5000, "prioriteit": 5})
    upd = POLICY.acties["app.update"]
    goed = {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.4@{DIGEST_B}"}}
    assert validate_parameters(POLICY, upd, APP, goed) == []
    assert validate_parameters(
        POLICY, upd, APP, {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": "latest"}}
    )
    assert validate_parameters(
        POLICY, upd, APP, {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": "1.2.4"}}
    )
    assert validate_parameters(POLICY, upd, APP, {})
    rb = POLICY.acties["app.rollback"]
    assert validate_parameters(POLICY, rb, APP, {"herstel_van": "0b0e8a9c-1111-4222-8333-444455556666"}) == []
    assert validate_parameters(POLICY, rb, APP, {"herstel_van": "nee"})


def test_install_goed_en_verwachte_image() -> None:
    inst = POLICY.acties["app.install"]
    params = install_params()
    assert validate_parameters(POLICY, inst, APP, params) == []
    assert expected_image(params) == {
        "repository": "ghcr.io/voorbeeld/demo-app",
        "tag": f"1.2.3@{DIGEST}",
        "versie": "1.2.3",
        "digest": DIGEST,
    }
    met_geheim = install_params(envs=[{"name": "DB_PASSWORD", "value": "vault://app/demo-app/db_password"}])
    assert validate_parameters(POLICY, inst, APP, met_geheim) == []
    assert vault_refs(met_geheim) == ["vault://app/demo-app/db_password"]


def _met(params: dict[str, Any], pad: str, waarde: Any) -> dict[str, Any]:
    out = copy.deepcopy(params)
    cur: Any = out
    delen = pad.split(".")
    for d in delen[:-1]:
        cur = cur[d]
    cur[delen[-1]] = waarde
    return out


@pytest.mark.parametrize(
    ("pad", "waarde", "code"),
    [
        ("app_create.values.privileged", True, "privileged_verboden"),
        ("app_create.custom_app", True, "compose_verboden"),
        ("app_create.custom_compose_config", {"services": {}}, "compose_verboden"),
        ("app_create.values.custom_compose_config_string", "services: {}", "compose_verboden"),
        (
            "app_create.values.image",
            {"repository": "ghcr.io/voorbeeld/demo-app", "tag": "latest"},
            "latest_of_ongeldig",
        ),
        ("app_create.version", "latest", "versie_exact"),
        ("app_create.values.capabilities", {"add": ["SYS_ADMIN"]}, "capabilities_verboden"),
        (
            "app_create.values.devices",
            [{"host_device": "/dev/sda", "container_device": "/dev/sda"}],
            "devices_verboden",
        ),
        ("app_create.values.networks", [{"name": "gedeeld"}], "netwerk_verboden"),
        ("app_create.values.host_network", True, "host_network_zonder_reden"),
        ("app_create.values.run_as_custom_user", True, "root_verboden"),
        ("app_create.values.envs", [{"name": "HUB_SERVICE_TOKEN", "value": "x"}], "reserved_env"),
        ("app_create.values.restart_policy", None, "waarde"),
        ("app_create.values.resources", None, "verplicht"),
        ("app_create.app_name", "andere-app", "doel_verschilt"),
        ("app_create.values.onbekend_veld", 1, "onbekend_veld"),
    ],
)
def test_ex47_installatie_wordt_voor_uitvoering_geweigerd(pad: str, waarde: Any, code: str) -> None:
    inst = POLICY.acties["app.install"]
    fouten = validate_parameters(POLICY, inst, APP, _met(install_params(), pad, waarde))
    assert code in [f.code for f in fouten], [f.as_dict() for f in fouten]


HOSTPADEN_FOUT = [
    "/",
    "/etc",
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/root",
    "/mnt",
    "/mnt/testpool",
    "/mnt/.ix-apps/x",
    "/mnt/testpool/../etc",
    "relatief/pad",
    "/mnt/testpool/apps/",
]


@pytest.mark.parametrize("pad", HOSTPADEN_FOUT)
def test_ex47_hostmount_buiten_een_dataset(pad: str) -> None:
    inst = POLICY.acties["app.install"]
    opslag = [{"type": "host_path", "mount_path": "/data", "host_path_config": {"path": pad}}]
    fouten = validate_parameters(POLICY, inst, APP, install_params(storage=opslag))
    codes = [f.code for f in fouten]
    assert "hostpad_verboden" in codes or "docker_socket_verboden" in codes, codes


def test_ex47_docker_socket_ergens_in_de_waarden() -> None:
    inst = POLICY.acties["app.install"]
    params = install_params(envs=[{"name": "DOCKER_HOST", "value": "unix:///var/run/docker.sock"}])
    assert "docker_socket_verboden" in [f.code for f in validate_parameters(POLICY, inst, APP, params)]
    mount = install_params(storage=[{"type": "ix_volume", "mount_path": "/var/run/docker.sock"}])
    assert validate_parameters(POLICY, inst, APP, mount)


# ------------------------------------------------------------------ canonieke JSON, ETag, handtekening
def test_canonieke_json() -> None:
    assert canonical_json({"b": 1, "a": ["é", None, True]}) == '{"a":["é",null,true],"b":1}'.encode()
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})
    for fout in ({"a": 1.5}, {1: "a"}, {"a": {1, 2}}, {"a": b"x"}):
        with pytest.raises(CanonicalError):
            canonical_json(fout)


def test_app_etag_volgt_image_digest_en_staat() -> None:
    app = {
        "name": "demo-app",
        "state": "RUNNING",
        "version": "1.4.8",
        "custom_app": False,
        "metadata": {"name": "ix-app", "train": "stable"},
        "active_workloads": {"images": ["ghcr.io/voorbeeld/demo-app:1.2.3"]},
    }
    images = [
        {"repo_tags": ["ghcr.io/voorbeeld/demo-app:1.2.3"], "repo_digests": [f"ghcr.io/voorbeeld/demo-app@{DIGEST}"]}
    ]
    basis = app_etag(app, images)
    assert basis.startswith("sha256:") and basis == app_etag(copy.deepcopy(app), copy.deepcopy(images))
    assert app_etag(None) == ABSENT
    assert app_etag({**app, "state": "STOPPED"}, images) != basis
    assert app_etag({**app, "active_workloads": {"images": ["ghcr.io/voorbeeld/demo-app:1.2.4"]}}, images) != basis
    andere = [
        {"repo_tags": ["ghcr.io/voorbeeld/demo-app:1.2.3"], "repo_digests": [f"ghcr.io/voorbeeld/demo-app@{DIGEST_B}"]}
    ]
    assert app_etag(app, andere) != basis


def test_handtekening_en_vorm() -> None:
    key, andere = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    prop = proposal("app.restart", APP, expected_version="sha256:" + "d" * 64)
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1")
    assert execreq.structure_errors(req) == []
    assert execreq.verify_signature(req, [andere.public_key(), key.public_key()])
    assert not execreq.verify_signature(req, [andere.public_key()])
    assert not execreq.verify_signature(req, [])
    for veld, waarde in (("nonce", "0b0e8a9c-1111-4222-8333-444455556666"), ("expires_at", "2099-01-01T00:00:00Z")):
        assert not execreq.verify_signature({**req, veld: waarde}, [key.public_key()])
    gewijzigd = copy.deepcopy(req)
    gewijzigd["proposal"]["target"]["app_id"] = "andere-app"
    assert not execreq.verify_signature(gewijzigd, [key.public_key()])
    assert not execreq.verify_signature({**req, "signature": "@@@"}, [key.public_key()])
    assert execreq.structure_errors({**req, "extra": 1})
    assert execreq.structure_errors({k: v for k, v in req.items() if k != "nonce"})
    assert execreq.structure_errors("geen object")


# ------------------------------------------------------------------ verify: envelop en besluit
NU = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
ETAG = "sha256:" + "d" * 64


def _envelope(req: dict[str, Any], key: Ed25519PrivateKey, now: datetime = NU) -> str | None:
    w = check_envelope(POLICY, req, [key.public_key()], now=now)
    return w.code if w else None


def test_envelop_tijden_handtekening_en_policy_hash() -> None:
    key = Ed25519PrivateKey.generate()
    prop = proposal("app.restart", APP, expected_version=ETAG)
    goed = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU)
    assert _envelope(goed, key) is None
    assert _envelope(goed, Ed25519PrivateKey.generate()) == "handtekening_ongeldig"
    assert _envelope(goed, key, NU + timedelta(seconds=301)) == "verzoek_verlopen"
    assert _envelope(goed, key, NU - timedelta(seconds=120)) == "verzoek_nog_niet_geldig"
    lang = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU, ttl=901)
    assert _envelope(lang, key) == "verzoek_geldigheid_ongeldig"
    andere_hash = execution_request(key, prop, policy_hash="sha256:" + "0" * 64, risk_class="R1", now=NU)
    assert _envelope(andere_hash, key) == "policy_hash_verschilt"
    assert _envelope({**goed, "extra": 1}, key) == "execution_request_ongeldig"


def _besluit(req: dict[str, Any], herkend: str | None = None, uitvoerder: str = "executor") -> str | None:
    _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=herkend, uitvoerder=uitvoerder)
    return w.code if w else None


def test_besluit_r1_zonder_goedkeuring_en_risicoklasse_nooit_lager() -> None:
    key = Ed25519PrivateKey.generate()
    prop = proposal("app.restart", APP, expected_version=ETAG)
    assert _besluit(execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU)) is None
    assert (
        _besluit(execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R0", now=NU))
        == "risicoklasse_te_laag"
    )
    # Kritieke app: de executor herkent het doel zelf en eist dan R2 + goedkeuring, wat de Hub ook beweert.
    r1 = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU)
    assert _besluit(r1, herkend="authentik") == "risicoklasse_te_laag"
    r2 = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R2", now=NU)
    assert _besluit(r2, herkend="authentik") == "goedkeuring_ontbreekt"
    assert _besluit(r1, herkend="emby") == "actie_geweigerd"


def test_besluit_weigert_onbekend_verboden_andere_uitvoerder_en_slechte_parameters() -> None:
    key = Ed25519PrivateKey.generate()

    def req(
        aid: str, target: dict[str, Any], params: dict[str, Any] | None = None, klasse: str = "R3"
    ) -> dict[str, Any]:
        return execution_request(
            key,
            proposal(aid, target, params, expected_version=ETAG),
            policy_hash=POLICY.hash,
            risk_class=klasse,
            now=NU,
        )

    assert _besluit(req("app.frobnicate", APP)) == "actie_niet_toegestaan"
    assert _besluit(req("pool.dataset.delete", APP)) == "actie_geweigerd"
    assert _besluit(req("mediaguard.media.replace", APP)) == "capability_unavailable"
    assert _besluit(req("notification.send", {"host_id": HOST}, {"titel": "T", "tekst": "x", "prioriteit": 5})) == (
        "actie_niet_toegestaan"
    )
    assert _besluit(req("app.restart", APP, {"force": True})) == "parameters_ongeldig"
    assert _besluit(req("app.restart", {"host_id": "ander", "app_id": "x"})) == "parameters_ongeldig"
    assert _besluit(req("app.restart", {"host_id": HOST, "app_id": "boiler"})) == "actie_geweigerd"


def test_ex19_goedkeuring_is_gebonden_aan_elk_veld() -> None:
    key = Ed25519PrivateKey.generate()
    params = {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.4@{DIGEST_B}"}}
    prop = proposal("app.update", APP, params, expected_version=ETAG)

    def code(approval: dict[str, Any] | None, p: dict[str, Any] = prop, now: datetime = NU) -> str | None:
        r = execution_request(key, p, policy_hash=POLICY.hash, risk_class="R2", approval=approval, now=NU)
        _a, _c, w = check_decision(POLICY, r, now=now, herkend_als=None, uitvoerder="executor")
        return w.code if w else None

    goed = approval_for(prop, policy_hash=POLICY.hash, risk_class="R2", now=NU, backup_checkpoint_id="cp-1")
    assert code(goed) is None
    assert code(None) == "goedkeuring_ontbreekt"
    assert code({**goed, "backup_checkpoint_id": None}) == "backup_checkpoint_ontbreekt"
    assert code({**goed, "resource_etag": "sha256:" + "e" * 64}) == "goedkeuring_past_niet"
    assert code({**goed, "policy_hash": "sha256:" + "0" * 64}) == "goedkeuring_past_niet"
    assert code({**goed, "risk_class": "R1"}) == "goedkeuring_past_niet"
    # Andere parameters, ander doel of andere actie dan waarvoor is goedgekeurd.
    andere_tag = {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.5@{DIGEST}"}}
    assert code(goed, proposal("app.update", APP, andere_tag, expected_version=ETAG)) == "goedkeuring_past_niet"
    ander_doel = {"host_id": HOST, "app_id": "andere-app"}
    assert code(goed, proposal("app.update", ander_doel, params, expected_version=ETAG)) == "goedkeuring_past_niet"
    assert (
        code(goed, proposal("app.update", APP, params, expected_version="sha256:" + "f" * 64))
        == "goedkeuring_past_niet"
    )
    # Geldigheid: hooguit 15 minuten.
    assert code(goed, now=NU + timedelta(seconds=601)) == "goedkeuring_verlopen"
    lang = approval_for(prop, policy_hash=POLICY.hash, risk_class="R2", now=NU, ttl=901, backup_checkpoint_id="cp-1")
    assert code(lang) == "goedkeuring_ongeldig"
    toekomst = approval_for(
        prop, policy_hash=POLICY.hash, risk_class="R2", now=NU + timedelta(minutes=5), backup_checkpoint_id="cp-1"
    )
    assert code(toekomst) == "goedkeuring_ongeldig"
