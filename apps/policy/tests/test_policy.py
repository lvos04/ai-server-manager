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
from asm_policy.engine import classify, herken_app, recognize, recognize_all
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


# Per verboden patroon uit policy/blokkades.yaml minstens één action_id, met de eigen id en code (S-P2-010, bouwpunt 3).
# De code is de bewering: een onbekend action_id geeft óók R3, dus "R3" of "geweigerd" alleen bewijst niets (V-003).
VERBODEN_PER_BLOKKADE = [
    ("shell.exec", "BLK-SHELL", "actie_verboden_shell"),
    ("app.shell.exec", "BLK-SHELL", "actie_verboden_shell"),
    ("pool.dataset.delete", "BLK-DESTRUCTIEF", "actie_verboden_destructief"),
    ("policy.update", "BLK-BEVEILIGING", "actie_verboden_beveiligingsbeleid"),
    ("roles.grant", "BLK-BEVEILIGING", "actie_verboden_beveiligingsbeleid"),
    ("breakglass.reset", "BLK-BEVEILIGING", "actie_verboden_beveiligingsbeleid"),
    ("vault.secret.read", "BLK-BEVEILIGING", "actie_verboden_beveiligingsbeleid"),
    ("ai.credits.purchase", "BLK-BETAALD", "actie_verboden_betaald"),
    ("abonnement.opwaarderen", "BLK-BETAALD", "actie_verboden_betaald"),
    ("billing.topup", "BLK-BETAALD", "actie_verboden_betaald"),
    ("emby.db.write", "BLK-DB-DIRECT", "actie_verboden_database"),
    ("mediaguard_core.sqlite.update", "BLK-DB-DIRECT", "actie_verboden_database"),
    ("app.postgres.query_write", "BLK-DB-DIRECT", "actie_verboden_database"),
    ("network.interface.update", "BLK-NETWERK", "actie_verboden_netwerk"),
    ("firewall.rule.add", "BLK-NETWERK", "actie_verboden_netwerk"),
    ("tailscale.up", "BLK-NETWERK", "actie_verboden_netwerk"),
    ("dns.record.set", "BLK-NETWERK", "actie_verboden_netwerk"),
]


@pytest.mark.parametrize(("action_id", "blokkade_id", "code"), VERBODEN_PER_BLOKKADE)
def test_elke_verboden_blokkade_weigert_met_haar_eigen_code(action_id: str, blokkade_id: str, code: str) -> None:
    """Elk verboden patroon weigert met zijn eigen id en code, ook voor de AI, een flow en met goedkeuring (R3); en
    het is géén onbekende actie (``known`` blijft waar), zodat de test rood wordt als de blokkade uit het beleid
    verdwijnt."""
    for actor in ("user", "ai", "flow"):
        c = classify(POLICY, action_id=action_id, target={"host_id": HOST}, parameters={}, actor_type=actor)
        assert c.known and c.geweigerd and c.risk_class == "R3", (action_id, actor)
        assert blokkade_id in c.rule_ids and code in [b.code for b in c.blokkades], (action_id, c.rule_ids)
        assert "ONBEKEND" not in c.rule_ids


def test_elke_verboden_blokkade_uit_het_beleid_heeft_een_test() -> None:
    """Een nieuw verboden patroon in ``policy/blokkades.yaml`` zonder regel in ``VERBODEN_PER_BLOKKADE`` maakt deze
    test rood, en een id in de lijst die niet (meer) in het beleid staat ook."""
    assert {b for _a, b, _c in VERBODEN_PER_BLOKKADE} == {v.id for v in POLICY.verboden}
    codes = {v.id: v.code for v in POLICY.verboden}
    assert all(codes[b] == c for _a, b, c in VERBODEN_PER_BLOKKADE)


@pytest.mark.parametrize("action_id", ["app.network.set", "app.policy.update", "app.auth.reset", "app.vpn.up"])
def test_onbekend_id_met_een_verboden_woord_verderop_wordt_als_onbekend_geweigerd(action_id: str) -> None:
    """BLK-BEVEILIGING en BLK-NETWERK toetsen alleen het eerste segment (besluit van de regisseur, 2026-11-12: patronen
    blijven zoals ze zijn). Zo'n action_id staat nooit op de allowlist en wordt dus als onbekend geweigerd: in de
    engine (``known`` onwaar, R3) en in het besluit van Hub én executor (``actie_niet_toegestaan``)."""
    c = classify(POLICY, action_id=action_id, target={"host_id": HOST}, parameters={}, actor_type="ai")
    assert not c.known and c.risk_class == "R3" and c.rule_ids == ("ONBEKEND",)
    assert POLICY.actie(action_id) is None
    prop = proposal(action_id, APP, expected_version=ETAG)
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R3", now=NU)
    key = Ed25519PrivateKey.generate()
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R3", approval=approval, now=NU)
    for uitvoerder in ("executor", "hub:gotify"):
        _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=None, uitvoerder=uitvoerder)
        assert w is not None and (w.status, w.code) == (403, "actie_niet_toegestaan"), uitvoerder


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


def test_naam_en_image_wijzen_naar_verschillende_apps_dan_gelden_beide() -> None:
    """Een herkenning is er alleen om strenger te zijn: wijst de naam naar de ene app en de image naar de andere,
    dan gelden de regels van allebei (anders zou een andere image de bescherming van de naam opheffen)."""
    # Kritieke naam, image van een niet-kritieke bekende app → nog steeds kritiek (R2).
    herkend = recognize_all(POLICY, "adguard-home", ["ghcr.io/voorbeeld/my-house:1.0"])
    assert (
        herkend == ("adguard-home", "my_house")
        and recognize(POLICY, "adguard-home", ["x/my-house:1"]) == "adguard-home"
    )
    c = classify(
        POLICY,
        action_id="app.restart",
        target={"app_id": "adguard-home"},
        parameters={},
        actor_type="user",
        herkend_als=herkend,
    )
    assert c.risk_class == "R2" and c.kritiek and c.requires_approval and "KRITIEK:adguard-home" in c.rule_ids
    # Naam emby met een andere bekende image, en andersom: de Emby-regel geldt in beide gevallen.
    for naam, image in (("emby", "docker.io/jellyfin/jellyfin:10"), ("jellyfin", "docker.io/emby/embyserver:4.9")):
        herkend = recognize_all(POLICY, naam, [image])
        assert set(herkend) == {"emby", "jellyfin"}
        c = classify(
            POLICY, action_id="app.stop", target={"app_id": naam}, parameters={}, actor_type="user", herkend_als=herkend
        )
        assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades]
    # Eén herkenning als tekst blijft werken; geen herkenning opent niets en verhoogt niets.
    assert classify(
        POLICY, action_id="app.stop", target={"app_id": "emby"}, parameters={}, actor_type="user", herkend_als="emby"
    ).geweigerd
    assert recognize_all(POLICY, "iets-anders", ["ghcr.io/x/y:1"]) == ()
    assert recognize_all(POLICY, "authentik-server", ["docker.io/emby/embyserver:4"]) == ("authentik", "emby")


def _readback(naam: str, staat: str, images: list[str], catalogus: str = "ix-app", custom: bool = False) -> Any:
    """Een app zoals ``app.query`` hem geeft; gestopt = lege ``active_workloads`` (zoals TrueNAS)."""
    details = [{"service_name": naam, "image": i, "state": staat.lower()} for i in images]
    return {
        "name": naam,
        "state": staat,
        "custom_app": custom,
        "metadata": {"name": catalogus, "train": "stable"},
        "active_workloads": {"images": images, "container_details": details},
    }


APP_ACTIES = ("app.uninstall", "app.update", "app.rollback", "app.start", "app.restart", "app.stop")


def test_gestopte_app_herkenning_op_de_catalogusapp_en_anders_dicht() -> None:
    """TrueNAS toont bij een gestopte app geen image. Een catalogusapp blijft herkenbaar aan ``metadata.name``; een
    Custom App (``ix-app``) of compose-app zonder zichtbare image is niet herkenbaar en dan weigert het beleid elke
    actie op die app: het kan Emby, MediaGuard of de mediaserver zijn (dicht bij twijfel)."""
    emby = herken_app(POLICY, "mediaserver", _readback("mediaserver", "STOPPED", [], catalogus="emby"))
    assert emby.apps == ("emby",) and emby.volledig
    for aid in APP_ACTIES:
        c = classify(POLICY, action_id=aid, target=APP, parameters={}, actor_type="user", herkend_als=emby)
        assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades], aid
    for gestopt in (
        _readback("mediaserver", "STOPPED", []),
        _readback("media-guard", "STOPPED", []),
        _readback("my-house", "STOPPED", []),  # ook een bekende naam: wat erin draait is niet te zien
        _readback("web", "STOPPED", [], catalogus="", custom=True),
    ):
        h = herken_app(POLICY, str(gestopt["name"]), gestopt)
        assert not h.volledig, gestopt
        for aid in APP_ACTIES:
            c = classify(POLICY, action_id=aid, target=APP, parameters={}, actor_type="user", herkend_als=h)
            assert c.geweigerd and "doel_niet_herkenbaar" in [b.code for b in c.blokkades], (aid, gestopt)
            assert "DOEL-ONHERKENBAAR" in c.rule_ids
    # Tegenproeven: een zichtbare image, een gestopte catalogusapp en een nieuwe app zijn wél vast te stellen.
    draait = herken_app(POLICY, "my-house", _readback("my-house", "RUNNING", ["ghcr.io/lvos04/my_house:0.1.0"]))
    assert draait.volledig and draait.apps == ("my_house",)
    c = classify(POLICY, action_id="app.start", target=APP, parameters={}, actor_type="user", herkend_als=draait)
    assert not c.geweigerd and c.risk_class == "R1"
    jf = herken_app(POLICY, "films", _readback("films", "STOPPED", [], catalogus="jellyfin"))
    assert jf.volledig and jf.apps == ("jellyfin",)
    c = classify(POLICY, action_id="app.start", target=APP, parameters={}, actor_type="user", herkend_als=jf)
    assert not c.geweigerd and c.risk_class == "R1"
    c = classify(POLICY, action_id="app.uninstall", target=APP, parameters={}, actor_type="user", herkend_als=jf)
    assert [b.code for b in c.blokkades] == ["mediaserver_migratie_vraagt_rapport"]
    nieuw = herken_app(POLICY, "demo-app", None, ["ghcr.io/voorbeeld/demo-app"])
    assert nieuw.volledig and nieuw.apps == ()
    assert herken_app(POLICY, "nieuw", None, ["docker.io/emby/embyserver"]).apps == ("emby",)
    # De catalogusnaam telt ook bij een draaiende app mee (alleen strenger): naam en image van iets anders.
    mix = herken_app(POLICY, "films", _readback("films", "RUNNING", ["ghcr.io/x/y:1"], catalogus="emby"))
    assert mix.apps == ("emby",) and mix.volledig
    # Acties zonder app als doel kijken niet naar de herkenning van een app.
    leeg = herken_app(POLICY, "x", _readback("x", "STOPPED", []))
    melding = {"host_id": HOST}
    c = classify(
        POLICY, action_id="notification.send", target=melding, parameters={}, actor_type="user", herkend_als=leeg
    )
    assert "doel_niet_herkenbaar" not in [b.code for b in c.blokkades]


def test_executor_en_hub_geven_een_onvolledige_herkenning_door_aan_de_weigering() -> None:
    """``check_decision`` (Hub vlak vóór verzending én executor) weigert bij een onvolledige herkenning, ook met een
    geldige goedkeuring en R3 in het verzoek."""
    prop = proposal("app.uninstall", {"host_id": HOST, "app_id": "mediaserver"}, {})
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R3", now=NU)
    key = Ed25519PrivateKey.generate()
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R3", approval=approval, now=NU)
    gestopt = herken_app(POLICY, "mediaserver", _readback("mediaserver", "STOPPED", []))
    _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=gestopt, uitvoerder="executor")
    assert w is not None and w.status == 403 and w.code == "actie_geweigerd"
    assert [b["code"] for b in w.details["blokkades"]] == ["doel_niet_herkenbaar"]


def test_stoppen_van_een_custom_app_vraagt_goedkeuring_een_catalogusapp_niet() -> None:
    """Besluit van de gebruiker (2026-11-11; ADR-0030 besluit 21): een Custom App die het platform stopt, kan het
    daarna niet meer starten (``doel_niet_herkenbaar``). Daarom is ``app.stop`` op een Custom App R2: altijd een
    goedkeuring van een beheerder, ook op voorstel van de AI of een flow, nooit automatisch. Een catalogusapp blijft
    gestopt herkenbaar aan zijn catalogusnaam en ``app.stop`` blijft daar R1. Hub en executor rekenen dit allebei
    zelf uit (``check_decision``)."""
    custom = herken_app(POLICY, "my-house", _readback("my-house", "RUNNING", ["ghcr.io/lvos04/my_house:0.1.0"]))
    assert custom.volledig and not custom.na_stop_herkenbaar
    for actor in ("user", "ai", "flow"):
        c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type=actor, herkend_als=custom)
        assert not c.geweigerd and c.risk_class == "R2" and c.requires_approval, actor
        assert "STOP-EENRICHTING" in c.rule_ids, actor
    # Alleen stoppen: starten en herstarten van dezelfde Custom App blijven R1.
    for aid in ("app.start", "app.restart"):
        c = classify(POLICY, action_id=aid, target=APP, parameters={}, actor_type="user", herkend_als=custom)
        assert not c.geweigerd and c.risk_class == "R1" and not c.requires_approval, aid
    # Een compose-app en een Custom App zonder bekende naam net zo.
    for app in (
        _readback("web", "RUNNING", ["ghcr.io/x/web:1"], catalogus="", custom=True),
        _readback("iets-anders", "RUNNING", ["ghcr.io/x/y:1"]),
    ):
        h = herken_app(POLICY, str(app["name"]), app)
        assert h.volledig and not h.na_stop_herkenbaar, app
        c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=h)
        assert c.risk_class == "R2" and c.requires_approval and "STOP-EENRICHTING" in c.rule_ids, app
    # Een catalogusapp: draaiend én gestopt R1, zonder goedkeuring.
    for staat, images in (("RUNNING", ["jellyfin/jellyfin:10.11.0"]), ("STOPPED", [])):
        jf = herken_app(POLICY, "films", _readback("films", staat, images, catalogus="jellyfin"))
        assert jf.volledig and jf.na_stop_herkenbaar
        c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=jf)
        assert not c.geweigerd and c.risk_class == "R1" and not c.requires_approval, staat
        assert "STOP-EENRICHTING" not in c.rule_ids
    # Beschermd blijft beschermd: Emby als Custom App met een Emby-image wordt geweigerd, ook met goedkeuring.
    emby = herken_app(POLICY, "mediaserver", _readback("mediaserver", "RUNNING", ["docker.io/emby/embyserver:4.9"]))
    c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=emby)
    assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades]
    # Zonder readback (stap 1 in Hub en executor) is niet bekend of de app gestopt herkenbaar blijft: R2 (dicht bij
    # twijfel; S-P2-010, R-VEILIG-4). Alleen de readback van een catalogusapp brengt het terug naar R1 (hieronder).
    kaal = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user")
    assert kaal.risk_class == "R2" and kaal.requires_approval and "STOP-EENRICHTING" in kaal.rule_ids
    # Executor-kant: een R1-verzoek is te laag; R2 zonder goedkeuring ontbreekt die; met goedkeuring gaat het door.
    prop = proposal("app.stop", {"host_id": HOST, "app_id": "my-house"}, {})
    key = Ed25519PrivateKey.generate()
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU)
    _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=custom, uitvoerder="executor")
    assert w is not None and w.code == "risicoklasse_te_laag"
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R2", now=NU)
    _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=custom, uitvoerder="executor")
    assert w is not None and w.code == "goedkeuring_ontbreekt"
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R2", now=NU)
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R2", approval=approval, now=NU)
    _a, eigen, w = check_decision(POLICY, req, now=NU, herkend_als=custom, uitvoerder="executor")
    assert w is None and eigen is not None and eigen.risk_class == "R2"
    # Dezelfde catalogusapp als R1 zonder goedkeuring: geen weigering.
    req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R1", now=NU)
    _a, eigen, w = check_decision(POLICY, req, now=NU, herkend_als=jf, uitvoerder="executor")
    assert w is None and eigen is not None and eigen.risk_class == "R1"


def test_herkenning_zonder_na_stop_herkenbaar_bestaat_niet() -> None:
    """S-P2-010, bouwpunt 6c (dicht bij twijfel): ``na_stop_herkenbaar`` heeft geen standaardwaarde meer. Een
    :class:`Herkenning` die het niet zegt, kan niet ontstaan; zo wordt ``app.stop`` op een Custom App nooit stil R1."""
    from asm_policy.engine import Herkenning

    with pytest.raises(TypeError):
        Herkenning(("my_house",), True)  # type: ignore[call-arg]
    for herkenbaar, klasse in ((False, "R2"), (True, "R1")):
        h = Herkenning((), True, herkenbaar)
        c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=h)
        assert c.risk_class == klasse and c.requires_approval is (klasse == "R2"), herkenbaar
    # Een app die nog moet worden geïnstalleerd: niet "na een stop herkenbaar" tenzij het een catalogusapp is.
    assert not herken_app(POLICY, "demo-app", None, ["ghcr.io/voorbeeld/demo-app"]).na_stop_herkenbaar
    assert herken_app(POLICY, "films", None, [], catalogus="jellyfin").na_stop_herkenbaar


def test_installeren_van_een_catalogusapp_herkent_op_de_catalogusnaam() -> None:
    """S-P2-010, bouwpunt 6g (HARDE EIS): ``app.install`` met ``catalog_app: "emby"`` onder een andere naam is een
    tweede Emby en valt onder APP-EMBY; herkend op ``parameters.app_create.catalog_app``, niet alleen op de doelnaam.
    ``ix-app`` zegt niets over de inhoud en herkent niets."""
    from asm_policy.params import verwachte_catalogus

    params = install_params("mediaspeler")
    params["app_create"].update(catalog_app="emby", version="1.0.0", values={})
    params["manifest"] = {"app_id": "mediaspeler", "install_reason": "proef"}
    assert validate_parameters(POLICY, POLICY.acties["app.install"], {"app_id": "mediaspeler"}, params) == []
    assert verwachte_catalogus(params) == "emby"
    h = herken_app(POLICY, "mediaspeler", None, [], catalogus=verwachte_catalogus(params))
    assert h.apps == ("emby",) and h.volledig
    for actor in ("user", "ai"):
        c = classify(POLICY, action_id="app.install", target=APP, parameters=params, actor_type=actor, herkend_als=h)
        assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades], actor
    # Executorkant: ook een ondertekend en goedgekeurd verzoek (R3) wordt geweigerd.
    prop = proposal("app.install", {"host_id": HOST, "app_id": "mediaspeler"}, params)
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R3", now=NU)
    req = execution_request(
        Ed25519PrivateKey.generate(), prop, policy_hash=POLICY.hash, risk_class="R3", approval=approval, now=NU
    )
    _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=h, uitvoerder="executor")
    assert w is not None and w.code == "actie_geweigerd"
    # Tegenproeven: de standaard Custom App (ix-app) en een gewone catalogusapp herkennen niets extra.
    assert verwachte_catalogus(install_params()) is None
    assert herken_app(POLICY, "demo-app", None, [], catalogus=verwachte_catalogus(install_params())).apps == ()
    immich = install_params("fotos")
    immich["app_create"].update(catalog_app="immich")
    assert verwachte_catalogus(immich) == "immich"
    assert herken_app(POLICY, "fotos", None, [], catalogus="immich").apps == ("immich",)
    assert verwachte_catalogus({}) is None and verwachte_catalogus({"app_create": "x"}) is None


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


# Unicode-tekens uit de categorieën Cc (ook C1 en NEL), Cf (bidi, zero-width, BOM), Zl en Zp (S-P2-010, R-VEILIG-5 en
# R-TECH-3): een beheerder ziet ze niet of anders (bidi-omkering), dus ook geen gewone mapnaam.
HOSTPAD_UNICODE = ["\x85", "\x9b", " ", " ", "‮", "⁦", "​", "‎", "﻿", "؜"]


@pytest.mark.parametrize("teken", ["\t", "\n", "\r", "\x0b", "\x0c", "\x00", "\x7f", *HOSTPAD_UNICODE], ids=repr)
@pytest.mark.parametrize("vorm", ["/mnt/testpool/apps/a{t}b", "/mnt/testpool/apps/demo{t}", "/mnt/testpool/{t}.."])
def test_ex47_hostpad_met_een_stuurteken_wordt_geweigerd(teken: str, vorm: str) -> None:
    """Een tab of regeleinde in een hostpad (zoals ``'/mnt/testpool/x\\n'``) is geen gewone mapnaam: weigeren, net als
    elk ander stuurteken (S-P2-010, bouwpunt 6f), en ook elk teken uit de Unicode-categorieën Cc, Cf, Zl en Zp
    (R-VEILIG-5). Ook via ``host_path`` dieper in de waarden (``_deep_forbidden``)."""
    from asm_policy.params import host_path_problem

    pad = vorm.format(t=teken)
    assert host_path_problem(pad) is not None, repr(pad)
    inst = POLICY.acties["app.install"]
    opslag = [{"type": "host_path", "mount_path": "/data", "host_path_config": {"path": pad}}]
    codes = [f.code for f in validate_parameters(POLICY, inst, APP, install_params(storage=opslag))]
    assert "hostpad_verboden" in codes, (repr(pad), codes)


@pytest.mark.parametrize(
    "pad",
    [
        "/mnt/testpool/ x",
        "/mnt/testpool/x ",
        "/mnt/ testpool/x",
        "/mnt/testpool /x",
        "/mnt/testpool/apps/x\xa0",
        "/mnt/testpool/　apps",
        "/mnt/testpool/apps/ ",
    ],
    ids=repr,
)
def test_ex47_hostpad_met_een_spatie_aan_begin_of_eind_van_een_segment(pad: str) -> None:
    """S-P2-010, R-VEILIG-5: ``'/mnt/testpool/x '`` en ``'/mnt/testpool/ x'`` lijken op ``/mnt/testpool/x``. Een spatie
    (ook een harde of brede spatie) aan het begin of eind van een segment wordt geweigerd; ook dieper in de waarden."""
    from asm_policy.params import host_path_problem

    assert host_path_problem(pad) is not None, repr(pad)
    inst = POLICY.acties["app.install"]
    opslag = [{"type": "host_path", "mount_path": "/data", "host_path_config": {"path": pad}}]
    codes = [f.code for f in validate_parameters(POLICY, inst, APP, install_params(storage=opslag))]
    assert "hostpad_verboden" in codes, (repr(pad), codes)


def test_ex47_hostpad_zonder_stuurteken_blijft_geldig_en_notities_mogen_regeleinden() -> None:
    """Tegenproef: een gewoon hostpad blijft geldig, en de strengere hostpadcontrole raakt andere tekstvelden niet
    (een notitie of omgevingswaarde met een regeleinde blijft toegestaan)."""
    from asm_policy.params import host_path_problem

    assert host_path_problem("/mnt/testpool/apps/demo-app") is None
    # Een spatie midden in een segment en letters met accenten blijven gewone mapnamen (R-VEILIG-5).
    assert host_path_problem("/mnt/testpool/mijn map/café") is None
    inst = POLICY.acties["app.install"]
    params = install_params(notes="regel 1\nregel 2", envs=[{"name": "LIJST", "value": "a\tb\nc"}])
    assert validate_parameters(POLICY, inst, APP, params) == []


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


@pytest.mark.parametrize(
    "fout",
    [{"x": "\ud800"}, {"x": ["a", "b\udfff"]}, {"\udc80": 1}, {"a": {"b": "\ud83d"}}],
    ids=["waarde", "lijst", "sleutel", "genest"],
)
def test_canonieke_json_weigert_een_losse_surrogaat(fout: dict[str, Any]) -> None:
    """S-P2-010, R-VEILIG-6: een losse surrogaat is geen UTF-8. Dat is een ``CanonicalError`` (een nette weigering:
    ``parameters_ongeldig``/``niet_canoniek``), geen ``UnicodeEncodeError`` die als onverwachte fout een 500 geeft."""
    with pytest.raises(CanonicalError):
        canonical_json(fout)
    with pytest.raises(CanonicalError):
        canonical_sha256(fout)
    upd = POLICY.acties["app.update"]
    fouten = validate_parameters(POLICY, upd, APP, {"image": fout})
    assert [f.code for f in fouten] == ["niet_canoniek"], [f.as_dict() for f in fouten]
    # Tegenproef: een echt teken buiten het basisvlak (een paar surrogaten in UTF-16, één teken in Python) mag.
    assert canonical_json({"x": "\U0001f600"}) == '{"x":"\U0001f600"}'.encode()


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


# ------------------------------------------------------------------ herstel na de review van S-P2-010 (A-HERSTEL)
def _nest(diepte: int, blad: Any) -> Any:
    """``blad`` onder ``diepte`` extra objecten: ``_nest(2, x) == {"k1": {"k0": x}}``."""
    v = blad
    for i in range(diepte):
        v = {f"k{i}": v}
    return v


def _catalogus(values: Any, naam: str = "huis", **manifest: Any) -> dict[str, Any]:
    """``app.install`` van een catalogusapp (geen ix-app) met eigen waarden."""
    return {
        "app_create": {
            "app_name": naam,
            "catalog_app": "home-assistant",
            "train": "community",
            "version": "1.2.3",
            "values": values,
        },
        "manifest": {"app_id": naam, "install_reason": "proef met een catalogusapp", **manifest},
    }


def _codes(params: Any, actie: str = "app.install", target: dict[str, Any] | None = None) -> list[str]:
    doel = target or {"host_id": HOST, "app_id": "huis"}
    return [f.code for f in validate_parameters(POLICY, POLICY.acties[actie], doel, params)]


EX47_BLADEREN = [
    pytest.param({"privileged": True}, "privileged_verboden", id="privileged"),
    pytest.param({"host_path_config": {"path": "/"}}, "hostpad_verboden", id="hostpad"),
    pytest.param({"custom_compose_config": {"services": {}}}, "compose_verboden", id="compose"),
    pytest.param({"socket": "/var/run/docker.sock"}, "docker_socket_verboden", id="docker_sock"),
    # Herstelronde 2: ook een losse tekst in een lijst, tot de dieptegrens (de lijst telt als een niveau).
    pytest.param({"volumes": ["/var/run/docker.sock:/x"]}, "docker_socket_verboden", id="lijst.docker_sock"),
    pytest.param({"binds": ["/:/host"]}, "hostpad_verboden", id="lijst.hostpad"),
    pytest.param({"args": ["--privileged"]}, "privileged_verboden", id="lijst.privileged"),
]


@pytest.mark.parametrize(("blad", "code"), EX47_BLADEREN)
def test_ex47_tot_de_dieptegrens_gezien_en_dieper_geweigerd(blad: dict[str, Any], code: str) -> None:
    """S-P2-010, R-VEILIG-1 (dicht bij twijfel): EX47 geldt op elke diepte die de parameters mogen hebben, en dieper
    dan die grens weigert ``validate_parameters`` met ``te_diep_genest``. Er is geen diepte waarop een verboden waarde
    ongezien doorkomt (vroeger stopte ``_walk`` stil na 16 niveaus)."""
    from asm_policy.canonical import MAX_DIEPTE
    from asm_policy.params import MAX_PARAMETER_DIEPTE

    assert MAX_DIEPTE >= MAX_PARAMETER_DIEPTE  # de doorzoekers kijken minstens zo diep als de parameters mogen
    gezien = 0
    for diepte in range(0, MAX_DIEPTE):
        codes = _codes(_catalogus(_nest(diepte, blad)))
        assert codes, (diepte, "een verboden waarde komt ongezien door")
        if "te_diep_genest" in codes:
            break
        assert code in codes, (diepte, codes)
        gezien = diepte
    else:  # pragma: no cover - de grens moet onder de canonieke grens liggen
        pytest.fail("geen te_diep_genest gevonden")
    assert gezien >= 10  # gewone catalogusapp-waarden (opslag, ACL-regels) zijn zo diep; die blijven toegestaan
    assert _codes(_catalogus(_nest(gezien + 1, blad))) == ["te_diep_genest"]


def test_te_diep_geneste_parameters_worden_bij_elk_schema_geweigerd() -> None:
    """De dieptegrens staat vóór het schema: ook ``eigenaar``-acties (vrije parameters) en ``app.update``."""
    from asm_policy.params import MAX_PARAMETER_DIEPTE

    diep = _nest(MAX_PARAMETER_DIEPTE, "x")  # de tekst zit op diepte MAX + 0 onder het eerste object
    assert "te_diep_genest" not in _codes({"a": _nest(MAX_PARAMETER_DIEPTE - 2, "x")}, "sso.sessions.revoke", SSO)
    assert _codes({"a": diep}, "sso.sessions.revoke", SSO) == ["te_diep_genest"]
    assert _codes({"image": diep}, "app.update", APP) == ["te_diep_genest"]
    assert _codes({"herstel_van": diep}, "app.rollback", APP) == ["te_diep_genest"]


SSO = {"host_id": HOST, "app_id": "home-control-hub", "resource": "hub"}


def test_boiler_tot_de_scangrens_gezien_en_dieper_dicht() -> None:
    """S-P2-010, R-VEILIG-1 (EX27): de boilercontrole ziet alle sleutels en teksten tot de grens van de canonieke JSON
    (vroeger stopte ze stil na 12 niveaus), en weigert dieper genest dan die grens (dicht bij twijfel), ook zonder het
    woord boiler. Ook bij een ``eigenaar``-actie."""
    from asm_policy.canonical import MAX_DIEPTE
    from asm_policy.engine import mentions_boiler

    for diepte in (1, 12, 14, 16, MAX_DIEPTE - 4):
        for blad in ({"schakel": "boiler aan"}, {"water_heater": True}):
            params = _catalogus(_nest(diepte, blad))
            c = classify(POLICY, action_id="app.install", target=APP, parameters=params, actor_type="user")
            assert c.geweigerd and "boiler_verboden" in [b.code for b in c.blokkades], (diepte, blad)
            sso = classify(
                POLICY, action_id="sso.sessions.revoke", target=SSO, parameters=_nest(diepte, blad), actor_type="user"
            )
            assert "boiler_verboden" in [b.code for b in sso.blokkades], (diepte, blad)
    # Tot en met de grens zonder het woord: niets. Dieper dan de grens: dicht, ook zonder het woord.
    assert not mentions_boiler(POLICY, _nest(MAX_DIEPTE - 1, "lamp aan"))
    assert mentions_boiler(POLICY, _nest(MAX_DIEPTE + 1, "lamp aan"))
    assert mentions_boiler(POLICY, [_nest(MAX_DIEPTE + 5, {"a": 1})])
    c = classify(POLICY, action_id="app.restart", target=APP, parameters=_nest(MAX_DIEPTE + 1, "x"), actor_type="user")
    assert c.geweigerd and c.risk_class == "R3"


def test_ex47_doorzoeker_weigert_dieper_dan_zijn_grens() -> None:
    """``_deep_forbidden`` stopt niet meer stil: dieper dan de scangrens is een fout ``te_diep_genest``."""
    from asm_policy.canonical import MAX_DIEPTE
    from asm_policy.params import _deep_forbidden

    assert _deep_forbidden(_nest(MAX_DIEPTE - 1, {"a": "x"}), "w", {}) == []
    fouten = _deep_forbidden(_nest(MAX_DIEPTE + 3, {"a": "x"}), "w", {})
    assert [f.code for f in fouten] == ["te_diep_genest"]
    lijst = _deep_forbidden({"l": [[[[_nest(MAX_DIEPTE, "x")]]]]}, "w", {})
    assert [f.code for f in lijst] == ["te_diep_genest"]


def test_executor_weigert_een_ondertekend_verzoek_met_te_diepe_parameters() -> None:
    """Ook een ondertekend en goedgekeurd verzoek (R3) met te diep geneste waarden weigert ``check_decision`` zelf;
    met de boiler diep genest is het een statische weigering."""
    from asm_policy.params import MAX_PARAMETER_DIEPTE

    key = Ed25519PrivateKey.generate()
    for blad, code in (({"privileged": True}, "parameters_ongeldig"), ({"x": "boiler aan"}, "actie_geweigerd")):
        params = _catalogus(_nest(MAX_PARAMETER_DIEPTE, blad))
        prop = proposal("app.install", {"host_id": HOST, "app_id": "huis"}, params, expected_version=ABSENT)
        approval = approval_for(prop, policy_hash=POLICY.hash, risk_class="R3", now=NU)
        req = execution_request(key, prop, policy_hash=POLICY.hash, risk_class="R3", approval=approval, now=NU)
        assert _envelope(req, key) is None  # de handtekening klopt: de weigering komt uit het besluit
        _a, _c, w = check_decision(POLICY, req, now=NU, herkend_als=None, uitvoerder="executor")
        assert w is not None and w.code == code, (blad, w)
        if code == "parameters_ongeldig":
            assert "te_diep_genest" in [f["code"] for f in w.details["fouten"]]


def test_herkenning_ook_op_de_image_na_de_actie() -> None:
    """S-P2-010, R-VEILIG-2 en R-TECH-1 (HARDE EIS): ``app.update`` kan een bestaande app een andere image geven. De
    herkenning telt naast de huidige images ook de image ná de actie (``verwachte_images``): een Custom App omzetten
    naar een Emby-image is een tweede Emby en valt onder APP-EMBY. Herkenning maakt alleen strenger: wat er nu
    draait blijft tellen, en of de herkenning volledig is hangt alleen af van wat er nu te zien is."""
    huidig = _readback("my-house", "RUNNING", ["ghcr.io/lvos04/my_house:0.1.0"])
    emby = {"image": {"repository": "emby/embyserver", "tag": f"4.8.10.0@{DIGEST}"}}
    h = herken_app(POLICY, "my-house", huidig, ["emby/embyserver"])
    assert set(h.apps) == {"my_house", "emby"} and h.volledig and not h.na_stop_herkenbaar
    for actor in ("user", "ai"):
        c = classify(POLICY, action_id="app.update", target=APP, parameters=emby, actor_type=actor, herkend_als=h)
        assert c.geweigerd and "emby_nooit_door_platform" in [b.code for b in c.blokkades], actor
    # Ook naar de image van de mediaserver of MediaGuard: hun regels gelden dan.
    for repo, code in (
        ("ghcr.io/lvos04/mediaguard", "mediaguard_upgradebewijs_ontbreekt"),
        ("jellyfin/jellyfin", "mediaserver_migratie_vraagt_rapport"),
    ):
        hm = herken_app(POLICY, "my-house", huidig, [repo])
        c = classify(POLICY, action_id="app.update", target=APP, parameters={}, actor_type="user", herkend_als=hm)
        assert code in [b.code for b in c.blokkades], (repo, hm.apps)
    # Tegenproef: bijwerken binnen dezelfde repository blijft R2 met goedkeuring, zonder weigering.
    zelfde = herken_app(POLICY, "my-house", huidig, ["ghcr.io/lvos04/my_house"])
    assert zelfde.apps == ("my_house",)
    c = classify(POLICY, action_id="app.update", target=APP, parameters={}, actor_type="user", herkend_als=zelfde)
    assert not c.geweigerd and c.risk_class == "R2" and c.requires_approval
    # Een lege verwachte image (catalogusversie) verandert niets.
    assert herken_app(POLICY, "my-house", huidig, [""]).apps == ("my_house",)
    # Gestopt: een verwachte image maakt de herkenning niet volledig (wat er nu draait blijft onbekend).
    gestopt = herken_app(POLICY, "my-house", _readback("my-house", "STOPPED", []), ["ghcr.io/lvos04/my_house"])
    assert not gestopt.volledig
    c = classify(POLICY, action_id="app.update", target=APP, parameters={}, actor_type="user", herkend_als=gestopt)
    assert "doel_niet_herkenbaar" in [b.code for b in c.blokkades]


CATALOGUS_EXTRA_RECHTEN = [
    pytest.param({"capabilities": {"add": ["SYS_ADMIN"]}}, "capabilities_verboden", id="capabilities.add"),
    pytest.param({"capabilities": {"drop": ["ALL"], "add": []}}, "capabilities_verboden", id="capabilities.anders"),
    pytest.param({"capabilities": ["NET_ADMIN"]}, "capabilities_verboden", id="capabilities.lijst"),
    pytest.param({"cap_add": ["SYS_ADMIN"]}, "capabilities_verboden", id="cap_add"),
    pytest.param({"devices": [{"host_device": "/dev/sda"}]}, "devices_verboden", id="devices"),
    pytest.param({"devices": ["/dev/dri"]}, "devices_verboden", id="devices.lijst"),
    pytest.param({"host_pid": True}, "host_pid_verboden", id="host_pid"),
    pytest.param({"pid": "host"}, "host_pid_verboden", id="pid_host"),
    pytest.param({"host_ipc": True}, "host_ipc_verboden", id="host_ipc"),
    pytest.param({"ipc": "host"}, "host_ipc_verboden", id="ipc_host"),
    pytest.param({"host_network": True}, "host_network_zonder_reden", id="host_network"),
    pytest.param({"networks": ["gedeeld"]}, "netwerk_verboden", id="networks"),
    pytest.param({"networks": [{"name": "gedeeld"}]}, "netwerk_verboden", id="networks.object"),
    pytest.param({"gpus": {"use_all_gpus": True}}, "gpu_zonder_d08", id="gpus.use_all"),
    pytest.param({"use_all_gpus": True}, "gpu_zonder_d08", id="use_all_gpus"),
    pytest.param({"gpus": {"nvidia_gpu_selection": {"0000:01:00.0": {"use_gpu": True}}}}, "gpu_verboden", id="nvidia"),
]


@pytest.mark.parametrize(("waarde", "code"), CATALOGUS_EXTRA_RECHTEN)
@pytest.mark.parametrize("diepte", [0, 3], ids=["bovenaan", "genest"])
def test_catalogusapp_extra_rechten_op_elke_diepte_geweigerd(waarde: dict[str, Any], code: str, diepte: int) -> None:
    """S-P2-010, R-VEILIG-3 (ADR-0030 besluit 6): ook de eigen waarden van een catalogusapp krijgen geen extra
    capabilities, apparaten, host-PID/-IPC, host-netwerk zonder reden, gedeeld Docker-netwerk of GPU zonder
    ``gpu: intel_render`` in het manifest; op elke diepte, dicht bij twijfel. Vroeger keurde de catalogusapp-tak dit
    goed (alleen de ix-app-tak controleerde het)."""
    codes = _codes(_catalogus(_nest(diepte, {"resources": {"limits": {"cpus": 2}}, **waarde})))
    assert code in codes, codes


def test_catalogusapp_zonder_extra_rechten_blijft_geldig() -> None:
    """Tegenproef: lege waarden, uit-standen en GPU met ``gpu: intel_render`` (en host-netwerk met reden) mogen."""
    values = {
        "capabilities": {"add": []},
        "devices": [],
        "networks": [],
        "host_pid": False,
        "host_ipc": False,
        "pid": "container",
        "network": {"host_network": False, "web_port": {"port_number": 30200}},
        "resources": {"limits": {"cpus": 2}, "gpus": {"use_all_gpus": False, "nvidia_gpu_selection": {}}},
    }
    assert _codes(_catalogus(values)) == []
    gpu = _catalogus({"resources": {"gpus": {"use_all_gpus": True}}}, gpu="intel_render")
    assert _codes(gpu) == []
    host = _catalogus(
        {"network": {"host_network": True}}, host_network_reason="mDNS-ontdekking van apparaten op het LAN"
    )
    assert _codes(host) == []
    # De ix-app-tak meldt een extra recht niet dubbel (zelfde veld, zelfde code).
    fouten = validate_parameters(
        POLICY, POLICY.acties["app.install"], APP, install_params(capabilities={"add": ["SYS_ADMIN"]})
    )
    assert [f.code for f in fouten].count("capabilities_verboden") == 1


@pytest.mark.parametrize("herkend_als", [None, (), "my_house", ("web",), ("jellyfin",)], ids=repr)
def test_stoppen_zonder_herkenning_is_r2(herkend_als: Any) -> None:
    """S-P2-010, R-VEILIG-4 en R-TECH-4 (dicht bij twijfel): zonder :class:`Herkenning` weet ``classify`` niet of de
    app na een stop herkenbaar blijft. Dan is ``app.stop`` op een app R2 (``STOP-EENRICHTING``), net als bij een
    Custom App; alleen een Herkenning die zegt dat de app herkenbaar blijft (een catalogusapp) geeft R1."""
    from asm_policy.engine import Herkenning

    c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=herkend_als)
    assert c.risk_class == "R2" and c.requires_approval and "STOP-EENRICHTING" in c.rule_ids
    jf = Herkenning(("jellyfin",), True, True)
    c = classify(POLICY, action_id="app.stop", target=APP, parameters={}, actor_type="user", herkend_als=jf)
    assert c.risk_class == "R1" and not c.requires_approval and "STOP-EENRICHTING" not in c.rule_ids
    # Alleen app.stop: starten en herstarten zonder herkenning blijven R1.
    for aid in ("app.start", "app.restart"):
        c = classify(POLICY, action_id=aid, target=APP, parameters={}, actor_type="user", herkend_als=herkend_als)
        assert c.risk_class == "R1", aid


def test_dockerfiles_kopieren_precies_alle_policybestanden() -> None:
    """S-P2-010, R-TECH-2: de ``policy_hash`` telt elke ``policy/*.yaml``. Beide Dockerfiles kopiëren de bestanden bij
    naam; een vierde yaml (of een ontbrekende) zou de hash in de image anders maken dan in de repo. De rooktest
    (``deploy/smoke.sh``) vergelijkt daarnaast de hash van beide images met die van ``policy/``."""
    repo = POLICY_DIR.parent
    verwacht = [f"policy/{p.name}" for p in sorted(POLICY_DIR.glob("*.yaml"))]
    assert len(verwacht) >= 3
    for dockerfile in ("deploy/allinone/Dockerfile", "deploy/executor/Dockerfile"):
        regels = [
            r.split()
            for r in (repo / dockerfile).read_text(encoding="utf-8").splitlines()
            if r.startswith("COPY") and "/usr/local/share/asm/policy" in r
        ]
        assert len(regels) == 1, dockerfile
        bronnen = [d for d in regels[0][1:-1] if not d.startswith("--")]
        assert bronnen == verwacht, (dockerfile, bronnen)
    smoke = (repo / "deploy/smoke.sh").read_text(encoding="utf-8")
    assert "policy_hash" in smoke and "asm-smoke-exec" in smoke


# ------------------------------------------------------------------ S-P2-010 herstelronde 2: losse teksten
# Een tekst die los in een lijst staat, heeft geen sleutel. Wat in een object al geweigerd wordt, wordt daar ook
# geweigerd: een Docker-socket, een hostpad buiten een dataset in een bind- of volumevorm, een ongeldige
# kluisverwijzing en de vormen "sleutel", "sleutel=waarde", "sleutel: waarde", "--sleutel waarde" van de sleutels die
# in een object verboden zijn (privileged, compose, capabilities, devices, host-PID/-IPC, host-netwerk, netwerken, GPU).
LOSSE_TEKSTEN_FOUT = [
    pytest.param({"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}, "docker_socket_verboden", id="sock"),
    pytest.param({"binds": ["/:/host"]}, "hostpad_verboden", id="bind.root"),
    pytest.param({"volumes": ["/etc:/etc:ro"]}, "hostpad_verboden", id="volume.etc"),
    pytest.param({"volumes": ["/mnt/.ix-apps/x:/x"]}, "hostpad_verboden", id="volume.ix_apps"),
    pytest.param({"volumes": ["/mnt/testpool:/pool"]}, "hostpad_verboden", id="volume.pool"),
    pytest.param({"volumes": ["./data:/data"]}, "hostpad_verboden", id="volume.relatief"),
    pytest.param({"volumes": ["~/data:/data"]}, "hostpad_verboden", id="volume.thuismap"),
    pytest.param({"args": ["-v", "/:/host"]}, "hostpad_verboden", id="args.v_los"),
    pytest.param({"args": ["--volume=/root:/r"]}, "hostpad_verboden", id="args.volume_is"),
    pytest.param({"args": ["--mount=type=bind,source=/,target=/host"]}, "hostpad_verboden", id="args.mount"),
    pytest.param({"args": ["type=bind,src=/etc,dst=/e"]}, "hostpad_verboden", id="args.mount_src"),
    pytest.param({"args": ["vault://ander/x"]}, "vault_ref_ongeldig", id="kluis"),
    pytest.param({"args": ["--privileged"]}, "privileged_verboden", id="privileged.vlag"),
    pytest.param({"args": ["privileged=true"]}, "privileged_verboden", id="privileged.is"),
    pytest.param({"args": ["Privileged: yes"]}, "privileged_verboden", id="privileged.dubbelepunt"),
    pytest.param({"args": ["custom_compose_config=services: {}"]}, "compose_verboden", id="compose"),
    pytest.param({"args": ["--custom-compose-config-string"]}, "compose_verboden", id="compose.vlag"),
    pytest.param({"args": ["--cap-add=SYS_ADMIN"]}, "capabilities_verboden", id="cap_add.is"),
    pytest.param({"args": ["--cap-add", "SYS_ADMIN"]}, "capabilities_verboden", id="cap_add.los"),
    pytest.param({"args": ["capabilities: NET_ADMIN"]}, "capabilities_verboden", id="capabilities"),
    # Herstelronde 3: de echte Docker-optie heet --device (enkelvoud); het meervoud blijft ook geweigerd.
    pytest.param({"args": ["--device=/dev/sda"]}, "devices_verboden", id="--device=/dev/sda"),
    pytest.param({"args": ["--device", "/dev/sda"]}, "devices_verboden", id="device.los"),
    pytest.param({"args": ["--devices=/dev/sda"]}, "devices_verboden", id="devices.meervoud"),
    pytest.param({"args": ["--pid=host"]}, "host_pid_verboden", id="pid.host"),
    pytest.param({"args": ["--pid", "host"]}, "host_pid_verboden", id="pid.los"),
    pytest.param({"args": ["host_pid=true"]}, "host_pid_verboden", id="host_pid"),
    pytest.param({"args": ["ipc: host"]}, "host_ipc_verboden", id="ipc.host"),
    pytest.param({"args": ["--host-ipc"]}, "host_ipc_verboden", id="host_ipc"),
    pytest.param({"args": ["--host-network"]}, "host_network_zonder_reden", id="host_network"),
    pytest.param({"args": ["networks=gedeeld"]}, "netwerk_verboden", id="networks"),
    pytest.param({"args": ["use_all_gpus=true"]}, "gpu_zonder_d08", id="use_all_gpus"),
    pytest.param({"args": ["nvidia_gpu_selection=0000:01:00.0"]}, "gpu_verboden", id="nvidia"),
    # Herstelronde 3 (R-VEILIG-8, R-TECH-9): dezelfde tabel van verboden sleutels als in een object, dus ook andere
    # schrijfwijzen en de Docker-/compose-namen als vlag; een onzichtbaar opmaakteken (Unicode Cf) verbergt niets meer.
    pytest.param({"args": ["--Host-Network"]}, "host_network_zonder_reden", id="host_network.hoofdletters"),
    pytest.param({"args": ["hostPID=true"]}, "host_pid_verboden", id="hostPID"),
    pytest.param({"args": ["--pid=container:emby"]}, "host_pid_verboden", id="pid.container"),
    pytest.param({"args": ["--network=host"]}, "catalogus_waarde_verboden", id="network.host"),
    pytest.param({"args": ["--network host"]}, "catalogus_waarde_verboden", id="network.spatie"),
    pytest.param({"args": ["--network", "host"]}, "catalogus_waarde_verboden", id="network.los"),
    pytest.param({"args": ["--net=host"]}, "catalogus_waarde_verboden", id="net.host"),
    pytest.param({"args": ["net: container:emby"]}, "catalogus_waarde_verboden", id="net.container"),
    pytest.param({"args": ["network_mode=host"]}, "catalogus_waarde_verboden", id="network_mode"),
    pytest.param({"args": ["--security-opt=seccomp=unconfined"]}, "catalogus_waarde_verboden", id="security_opt"),
    pytest.param({"args": ["--security-opt", "no-new-privileges=false"]}, "catalogus_waarde_verboden", id="sec.los"),
    pytest.param({"args": ["--userns=host"]}, "catalogus_waarde_verboden", id="userns"),
    pytest.param({"args": ["--uts=host"]}, "catalogus_waarde_verboden", id="uts"),
    pytest.param({"args": ["--cgroupns=host"]}, "catalogus_waarde_verboden", id="cgroupns"),
    pytest.param({"args": ["--sysctl=net.ipv4.ip_forward=1"]}, "catalogus_waarde_verboden", id="sysctl"),
    pytest.param({"args": ["--volumes-from=emby"]}, "catalogus_waarde_verboden", id="volumes_from"),
    pytest.param({"args": ["--runtime=nvidia"]}, "catalogus_waarde_verboden", id="runtime"),
    pytest.param({"args": ["--entrypoint=/bin/sh"]}, "catalogus_waarde_verboden", id="entrypoint.vlag"),
    pytest.param({"args": ["apparmor=unconfined"]}, "catalogus_waarde_verboden", id="apparmor"),
    pytest.param({"args": ["profiel unconfined"]}, "catalogus_waarde_verboden", id="unconfined.tekst"),
    pytest.param({"args": ["--docker-compose-file=x.yml"]}, "compose_verboden", id="compose.deel_van_naam"),
    pytest.param({"args": ["services: {}"]}, "compose_verboden", id="compose.services"),
    pytest.param({"args": ["-v/:/host"]}, "hostpad_verboden", id="args.v_aaneen"),
    pytest.param({"args": ["--volume/etc:/etc"]}, "hostpad_verboden", id="args.volume_aaneen"),
    pytest.param({"args": ["\u200b/:/host"]}, "stuurteken", id="cf.bind"),
    pytest.param({"args": ["--privileged\u200b"]}, "stuurteken", id="cf.vlag"),
    pytest.param({"args": ["\u2066--pid=host"]}, "stuurteken", id="cf.bidi"),
]


def _in_vorm(vorm: str, waarde: dict[str, Any]) -> dict[str, Any]:
    if vorm == "bovenaan":
        return waarde
    if vorm == "genest":
        return dict(_nest(6, waarde))
    return {"lijsten": [[{"a": [waarde]}]]}  # lijst in lijst, met objecten ertussen


@pytest.mark.parametrize(("waarde", "code"), LOSSE_TEKSTEN_FOUT)
@pytest.mark.parametrize("vorm", ["bovenaan", "genest", "lijst_in_lijst"])
def test_losse_teksten_in_lijsten_op_elke_diepte_geweigerd(waarde: dict[str, Any], code: str, vorm: str) -> None:
    """S-P2-010, herstelronde 2 (besluit van de regisseur, optie a; dicht bij twijfel): ``_walk`` gaf alleen sleutels
    van objecten terug, dus een tekst die los in een lijst stond werd nooit bekeken. Zo kwamen bijvoorbeeld
    ``{"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}`` en ``{"binds": ["/:/host"]}`` in de waarden van
    een catalogusapp zonder fout door, terwijl dezelfde tekst in een object wel geweigerd werd. Nu op elke diepte."""
    codes = _codes(_catalogus(_in_vorm(vorm, waarde)))
    assert code in codes, codes


IX_LOSSE_TEKSTEN = [
    p for p in LOSSE_TEKSTEN_FOUT if p.id in {"sock", "bind.root", "volume.etc", "volume.ix_apps", "privileged.vlag"}
]


@pytest.mark.parametrize(("waarde", "code"), IX_LOSSE_TEKSTEN)
def test_losse_teksten_in_lijsten_ook_bij_de_standaard_custom_app(waarde: dict[str, Any], code: str) -> None:
    """Ook bij de standaard Custom App (ix-app) gelden voor een losse tekst in een lijst dezelfde regels.

    Aangepast in herstelronde 3 (R-TECH-8, besluit BN-2 optie b; P-VEILIG punt 9): tot dan stond de lijst in
    ``command``. ``command`` en ``entrypoint`` van de ix-app zijn de opdracht van het proces ín de container (het
    sjabloon geeft ze alleen door als ``command``/``entrypoint`` van de dienst); een vlag of bindtekst daar geeft geen
    recht en wordt niet meer geweigerd (:func:`test_opdracht_van_de_standaard_custom_app_is_geen_docker_optie`). In
    elke andere lijst van de ix-app blijft de weigering, en de Docker-socket blijft ook in ``command`` en
    ``entrypoint`` geweigerd."""
    lijst = next(iter(waarde.values()))
    opslag = install_params()["app_create"]["values"]["storage"][0]
    for values in ({"storage": [{**opslag, "opties": lijst}]}, {"dns_config": {"options": lijst}}):
        codes = [
            f.code for f in validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(**values))
        ]
        assert code in codes, (values, codes)
    for veld in ("command", "entrypoint"):
        codes = [
            f.code
            for f in validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(**{veld: lijst}))
        ]
        assert (code in codes) == (code == "docker_socket_verboden"), (veld, codes)


def test_losse_teksten_in_lijsten_tegenproef_en_kluisverwijzingen() -> None:
    """Tegenproef: gewone teksten in lijsten blijven geldig (een dataset als bron, een benoemd volume, adressen,
    gewone opties, ook ``--pid`` met een bestand en een uitgezette vlag). Een geldige kluisverwijzing in een lijst is
    geen schemafout, maar wordt nu wel gevonden: Hub en executor weigeren de installatie dan met
    ``capability_unavailable`` (dicht), net als bij een verwijzing in een object."""
    values = {
        "volumes": ["/mnt/testpool/media:/media:ro", "data:/data", "/mnt/testpool/apps/x:/x"],
        "dns": {"nameservers": ["127.0.0.1", "::1"], "search": ["voorbeeld.invalid"]},
        "args": ["--config", "/config/app.yml", "--pid=/run/app.pid", "--privileged=false", "--verbose", "web"],
        # Herstelronde 3: een eigen optie --network/--net van de app met een gewone waarde, en uitgezette Docker-namen.
        "meer": [
            "--network=mainnet",
            "--net=testnet",
            "--runtime=",
            "--device=none",
            "-v",
            "data:/data",
            "-verbose",
        ],
        "urls": ["https://voorbeeld.invalid/pad", "tcp://localhost:8080"],
        "tijden": ["12:00", "2026-11-12T08:00:00Z"],
        "geheim": ["vault://app/huis/db_wachtwoord"],
        "resources": {"limits": {"cpus": 2}},
    }
    params = _catalogus(values)
    assert _codes(params) == []
    assert vault_refs(params) == ["vault://app/huis/db_wachtwoord"]
    ix = install_params(command=["--config", "/config/app.yml"], entrypoint=["/app/start.sh"])
    assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, ix) == []
    assert vault_refs(install_params(command=["--token", "vault://app/demo-app/token"])) == [
        "vault://app/demo-app/token"
    ]
    # Host-netwerk als vlag mag met een reden in het manifest, GPU als vlag met gpu: intel_render (zoals in een object).
    assert _codes(_catalogus({"args": ["--host-network"]}, host_network_reason="mDNS-ontdekking op het LAN")) == []
    assert _codes(_catalogus({"args": ["use_all_gpus=true"]}, gpu="intel_render")) == []


HOST_NETWORK_VORMEN = [
    pytest.param({"network": {"host_network": True}}, id="object"),
    pytest.param({"args": ["--host-network"]}, id="vlag"),
]


@pytest.mark.parametrize("values", HOST_NETWORK_VORMEN)
@pytest.mark.parametrize(
    "reden",
    [
        pytest.param(" ", id="spatie"),
        pytest.param("kort", id="kort"),
        pytest.param("  negentien  ", id="9_tekens_met_spaties"),
    ],
)
def test_host_network_reden_te_kort(values: dict[str, Any], reden: str) -> None:
    """S-P2-010 (mutant MJ): een lege of te korte reden (minder dan 10 tekens na strip) telt niet als reden."""
    assert "host_network_zonder_reden" in _codes(_catalogus(values, host_network_reason=reden))


@pytest.mark.parametrize("values", HOST_NETWORK_VORMEN)
def test_host_network_reden_van_tien_tekens_mag(values: dict[str, Any]) -> None:
    """Grensgeval: precies 10 tekens na strip is genoeg."""
    assert _codes(_catalogus(values, host_network_reason="  tien_teken  ")) == []


def test_losse_teksten_tot_de_dieptegrens_gezien() -> None:
    """Een losse tekst in een lijst op de diepste toegestane plek wordt gezien; één niveau dieper: ``te_diep_genest``.
    Ook de doorzoeker zelf weigert een lijst dieper dan zijn grens (nooit stil stoppen)."""
    from asm_policy.canonical import MAX_DIEPTE
    from asm_policy.params import MAX_PARAMETER_DIEPTE, _deep_forbidden

    # parameters (0) -> app_create (1) -> values (2) -> _nest -> "b" -> lijst-element
    diepste = _catalogus(_nest(MAX_PARAMETER_DIEPTE - 4, {"b": ["/:/host"]}))
    assert "hostpad_verboden" in _codes(diepste)
    assert _codes(_catalogus(_nest(MAX_PARAMETER_DIEPTE - 3, {"b": ["/:/host"]}))) == ["te_diep_genest"]
    assert [f.code for f in _deep_forbidden({"b": _nest(MAX_DIEPTE, ["x"])}, "w", {})] == ["te_diep_genest"]


def test_losse_teksten_controle_blijft_snel_bij_lange_teksten() -> None:
    """De controle van een losse tekst is lineair: een tekst van 60 000 tekens met lange reeksen spaties (binnen de
    grootte die de parameters mogen hebben) kost geen seconden rekentijd in Hub of executor. Een eerdere opzet met een
    reguliere expressie die over de waarde terugzocht, deed hier enkele seconden over (gemeten 3 s bij 30 000 tekens).
    Ruime grens: de meting was 0,003 s."""
    import time

    from asm_policy.params import _losse_tekst

    teksten = ("a b" + " " * 60000 + "c", "a=" + (" " * 1000 + "x") * 60, " src" + " " * 60000 + "x")
    # Herstelronde 3: ook de herkenning van "-v/…" aaneen en de controle op onzichtbare opmaaktekens blijven lineair.
    for tekst in (*teksten, " " * 60000 + "-v", "-v" * 30000, "x" * 60000 + "\u200b"):
        start = time.perf_counter()
        _losse_tekst(tekst, "p", {})
        assert time.perf_counter() - start < 1.0, len(tekst)


# ------------------------------------------------------------------ S-P2-010 herstelronde 3: één tabel van sleutels
# Herstelronde 2 maakte een lijst strenger dan een object. Nu geldt één genormaliseerde tabel van verboden sleutels
# (kleine letters, alleen letters en cijfers; zelfde normalisatie als de manifestregels van appstore-en-fork), gelijk
# voor een sleutel in een object, een losse tekst in een lijst en de vlagvorm.
OBJECT_SLEUTELS_FOUT = [
    # R-VEILIG-7 / R-TECH-6: privileged en host-netwerk: elke waarde behalve afwezig, None of False.
    pytest.param({"privileged": 1}, "privileged_verboden", id="privileged.1"),
    pytest.param({"privileged": 0}, "privileged_verboden", id="privileged.0"),
    pytest.param({"privileged": "true"}, "privileged_verboden", id="privileged.tekst_true"),
    pytest.param({"privileged": "yes"}, "privileged_verboden", id="privileged.tekst_yes"),
    pytest.param({"privileged": "1"}, "privileged_verboden", id="privileged.tekst_1"),
    pytest.param({"privileged": "false"}, "privileged_verboden", id="privileged.tekst_false"),
    pytest.param({"privileged": [True]}, "privileged_verboden", id="privileged.lijst"),
    pytest.param({"privileged": {"enabled": True}}, "privileged_verboden", id="privileged.object"),
    pytest.param({"host_network": 1}, "host_network_zonder_reden", id="host_network.1"),
    pytest.param({"host_network": "true"}, "host_network_zonder_reden", id="host_network.tekst"),
    # R-VEILIG-8 / R-TECH-6 deel 2: andere schrijfwijzen van dezelfde sleutels.
    pytest.param({"Privileged": True}, "privileged_verboden", id="Privileged"),
    pytest.param({"PRIVILEGED": True}, "privileged_verboden", id="PRIVILEGED"),
    pytest.param({"hostNetwork": True}, "host_network_zonder_reden", id="hostNetwork"),
    pytest.param({"host-network": True}, "host_network_zonder_reden", id="host-network"),
    pytest.param({"hostPID": True}, "host_pid_verboden", id="hostPID"),
    pytest.param({"Host-IPC": 1}, "host_ipc_verboden", id="Host-IPC"),
    pytest.param({"CapAdd": ["SYS_ADMIN"]}, "capabilities_verboden", id="CapAdd"),
    pytest.param({"Capabilities": {"add": ["NET_ADMIN"]}}, "capabilities_verboden", id="Capabilities"),
    pytest.param({"Devices": ["/dev/sda"]}, "devices_verboden", id="Devices"),
    pytest.param({"device": "/dev/sda"}, "devices_verboden", id="device"),
    pytest.param({"Networks": ["gedeeld"]}, "netwerk_verboden", id="Networks"),
    pytest.param({"useAllGpus": True}, "gpu_zonder_d08", id="useAllGpus"),
    pytest.param({"NvidiaGpuSelection": {"0000:01:00.0": {"use_gpu": True}}}, "gpu_verboden", id="NvidiaGpuSelection"),
    # Compose: "compose" in de genormaliseerde sleutel, of de sleutel "services".
    pytest.param({"Custom-Compose-Config": {"services": {}}}, "compose_verboden", id="Custom-Compose-Config"),
    pytest.param({"customComposeConfigString": "services: {}"}, "compose_verboden", id="customComposeConfigString"),
    pytest.param({"docker_compose": "services: {}"}, "compose_verboden", id="docker_compose"),
    pytest.param({"services": {"web": {"image": "x"}}}, "compose_verboden", id="services"),
    # Docker-/compose-namen met een niet-lege waarde.
    pytest.param({"network_mode": "host"}, "catalogus_waarde_verboden", id="network_mode.host"),
    pytest.param({"network_mode": "container:emby"}, "catalogus_waarde_verboden", id="network_mode.container"),
    pytest.param({"networkMode": "service:emby"}, "catalogus_waarde_verboden", id="networkMode.service"),
    pytest.param({"net": "host"}, "catalogus_waarde_verboden", id="net.host"),
    pytest.param({"net": " Host "}, "catalogus_waarde_verboden", id="net.spaties"),
    pytest.param({"network": "host"}, "catalogus_waarde_verboden", id="network.tekst_host"),
    pytest.param({"network_mode": ["host"]}, "catalogus_waarde_verboden", id="network_mode.lijst"),
    pytest.param({"pid": "container:emby"}, "host_pid_verboden", id="pid.container"),
    pytest.param({"ipc": "service:emby"}, "host_ipc_verboden", id="ipc.service"),
    pytest.param({"pid_mode": "host"}, "catalogus_waarde_verboden", id="pid_mode"),
    pytest.param({"ipc_mode": "shareable"}, "catalogus_waarde_verboden", id="ipc_mode"),
    pytest.param({"uts": "host"}, "catalogus_waarde_verboden", id="uts"),
    pytest.param({"userns": "host"}, "catalogus_waarde_verboden", id="userns"),
    pytest.param({"userns_mode": "host"}, "catalogus_waarde_verboden", id="userns_mode"),
    pytest.param({"cgroup": "host"}, "catalogus_waarde_verboden", id="cgroup"),
    pytest.param({"cgroupns": "host"}, "catalogus_waarde_verboden", id="cgroupns"),
    pytest.param({"security_opt": ["no-new-privileges:false"]}, "catalogus_waarde_verboden", id="security_opt"),
    pytest.param({"seccomp": "profiel.json"}, "catalogus_waarde_verboden", id="seccomp"),
    pytest.param({"apparmor": "eigen-profiel"}, "catalogus_waarde_verboden", id="apparmor"),
    pytest.param({"sysctls": {"net.ipv4.ip_forward": "1"}}, "catalogus_waarde_verboden", id="sysctls"),
    pytest.param({"volumes_from": ["emby"]}, "catalogus_waarde_verboden", id="volumes_from"),
    pytest.param({"runtime": "nvidia"}, "catalogus_waarde_verboden", id="runtime"),
    pytest.param({"device_cgroup_rules": ["c 1:3 mr"]}, "catalogus_waarde_verboden", id="device_cgroup_rules"),
    pytest.param({"allowPrivilegeEscalation": True}, "catalogus_waarde_verboden", id="allowPrivilegeEscalation"),
    # "unconfined" in een tekst: een beveiligingsprofiel uitzetten.
    pytest.param({"profiel": "Unconfined"}, "catalogus_waarde_verboden", id="unconfined"),
    pytest.param({"opties": ["seccomp=unconfined"]}, "catalogus_waarde_verboden", id="unconfined.lijst"),
]
# Alleen bij een catalogusapp: een eigen opdracht (bij de standaard Custom App zijn command en entrypoint gewone
# velden).
CATALOGUS_OPDRACHT_FOUT = [
    pytest.param({"command": ["sh", "-c", "id"]}, "catalogus_waarde_verboden", id="command"),
    pytest.param({"Entrypoint": "/bin/sh"}, "catalogus_waarde_verboden", id="Entrypoint"),
]


@pytest.mark.parametrize(("waarde", "code"), [*OBJECT_SLEUTELS_FOUT, *CATALOGUS_OPDRACHT_FOUT])
@pytest.mark.parametrize("vorm", ["bovenaan", "genest", "lijst_in_lijst"])
def test_verboden_sleutels_in_elke_schrijfwijze_en_met_elke_waarde(
    waarde: dict[str, Any], code: str, vorm: str
) -> None:
    """S-P2-010, herstelronde 3 (R-VEILIG-7, R-VEILIG-8, R-TECH-6): in de waarden van een catalogusapp kwamen
    ``{"privileged": 1}``, ``{"privileged": "true"}``, ``{"Privileged": true}``, ``{"hostNetwork": true}``,
    ``{"network_mode": "host"}``, ``{"security_opt": [...]}``, ``{"sysctls": {...}}`` en
    ``{"Custom-Compose-Config": {...}}`` zonder fout door tot ``app.create``, terwijl de preview "privileged: false"
    toonde. Nu op elke diepte geweigerd, met de code van de sleutel."""
    codes = _codes(_catalogus(_in_vorm(vorm, waarde)))
    assert code in codes, codes


@pytest.mark.parametrize(("waarde", "code"), OBJECT_SLEUTELS_FOUT)
@pytest.mark.parametrize("plek", ["storage[0]", "resources", "dns_config"])
def test_verboden_sleutels_ook_in_een_onderdeel_van_de_standaard_custom_app(
    waarde: dict[str, Any], code: str, plek: str
) -> None:
    """De witte lijst van de ix-app geldt alleen bovenaan; in een onderdeel (een opslagregel, ``resources``) stonden
    ``{"privileged": 1}`` en ``{"privileged": "true"}`` zonder fout (R-VEILIG-7). Dezelfde tabel geldt nu ook daar."""
    basis = install_params()["app_create"]["values"]
    if plek == "storage[0]":
        values = {"storage": [{**basis["storage"][0], **waarde}]}
    elif plek == "resources":
        values = {"resources": {**basis["resources"], **waarde}}
    else:
        values = {"dns_config": {"nameservers": [], "extra": waarde}}
    fouten = validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(**values))
    assert code in [f.code for f in fouten], [f.as_dict() for f in fouten]


def test_verboden_sleutels_tegenproef_uit_standen_en_lege_waarden() -> None:
    """Tegenproef: afwezig, ``None``, ``False`` en lege waarden blijven geldig; host-netwerk mag met een reden in het
    manifest, een GPU met ``gpu: intel_render``. ``network_mode``/``net``/``network`` zijn alleen verboden met de
    waarde ``host`` of de namespace van een andere container (``container:…``, ``service:…``): ``network`` is bij
    catalogusapps een gewoon object en ``bridge`` is de standaard."""
    values = {
        "privileged": False,
        "Privileged": None,
        "hostNetwork": False,
        "host_pid": None,
        "hostIPC": False,
        "capAdd": [],
        "Capabilities": {"add": []},
        "device": "",
        "Devices": [],
        "network": {"host_network": False, "web_port": {"port_number": 30200}, "mode": "bridge"},
        "network_mode": "bridge",
        "net": None,
        "pid": "container",
        "ipc": "private",
        "pid_mode": "",
        "security_opt": [],
        "sysctls": {},
        "runtime": None,
        "allowPrivilegeEscalation": False,
        "command": [],
        "entrypoint": None,
        "resources": {"limits": {"cpus": 2}, "gpus": {"useAllGpus": False, "nvidia_gpu_selection": {}}},
    }
    assert _codes(_catalogus(values)) == []
    reden = "mDNS-ontdekking van apparaten op het LAN"
    assert _codes(_catalogus({"network": {"hostNetwork": 1}}, host_network_reason=reden)) == []
    assert _codes(_catalogus({"args": ["--hostNetwork"]}, host_network_reason=reden)) == []
    assert _codes(_catalogus({"gpus": {"UseAllGpus": "true"}}, gpu="intel_render")) == []
    # network_mode host blijft ook met een reden verboden: de reden hoort bij het veld host_network.
    assert "catalogus_waarde_verboden" in _codes(_catalogus({"network_mode": "host"}, host_network_reason=reden))
    # De velden van app_create zelf (naam, catalogusapp, trein) zijn geen waarden: een app die "network" of "services"
    # heet, wordt daar niet om geweigerd.
    for naam in ("network", "services", "privileged", "runtime"):
        doel = {"host_id": HOST, "app_id": naam}
        assert _codes(_catalogus({"resources": {"limits": {"cpus": 2}}}, naam=naam), target=doel) == [], naam
    # De standaard Custom App zonder iets extra's blijft geldig (geen onterechte weigering door de tabel).
    assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params()) == []


# R-VEILIG-9 / R-TECH-7: een tekst in vlag- of bindvorm als waarde in een object (alleen bij een catalogusapp).
OBJECT_TEKSTEN_FOUT = [
    pytest.param({"extra_args": "--privileged"}, "privileged_verboden", id="extra_args.vlag"),
    pytest.param({"opties": "pid=host"}, "host_pid_verboden", id="opties.pid"),
    pytest.param({"extra": "--network host"}, "catalogus_waarde_verboden", id="extra.network"),
    pytest.param({"extra": "--cap-add=SYS_ADMIN"}, "capabilities_verboden", id="extra.cap_add"),
    pytest.param({"volume": "/:/host"}, "hostpad_verboden", id="volume.root"),
    pytest.param({"volume": "/etc:/etc"}, "hostpad_verboden", id="volume.etc"),
    pytest.param({"volume": "-v/root:/r"}, "hostpad_verboden", id="volume.v_aaneen"),
    pytest.param({"mount": "type=bind,source=/etc,target=/e"}, "hostpad_verboden", id="mount.lange_vorm"),
    pytest.param({"mount": {"type": "bind", "source": "/", "target": "/host"}}, "hostpad_verboden", id="mount.source"),
    pytest.param({"mount": {"Src": "/root"}}, "hostpad_verboden", id="mount.src"),
    pytest.param({"hostPath": "/etc"}, "hostpad_verboden", id="hostPath"),
    pytest.param({"host-path": "/var/run"}, "hostpad_verboden", id="host-path"),
    pytest.param({"data": {"Path": "/etc/passwd"}}, "hostpad_verboden", id="path"),
    pytest.param({"waarde": "​/:/host"}, "stuurteken", id="cf"),
    pytest.param({"value": "--privileged"}, "privileged_verboden", id="value_zonder_naam"),
    pytest.param({"name": "EXTRA", "waarde": "--privileged"}, "privileged_verboden", id="naam_zonder_value"),
    pytest.param({"name": "EXTRA", "value": ["--privileged"]}, "privileged_verboden", id="paar_met_lijst"),
    # Alleen de waarde van een paar is vrije tekst; de naam ernaast niet (dicht bij twijfel).
    pytest.param({"name": "--privileged", "value": "x"}, "privileged_verboden", id="paar_naam_is_geen_vrije_tekst"),
]


@pytest.mark.parametrize(("waarde", "code"), OBJECT_TEKSTEN_FOUT)
@pytest.mark.parametrize("vorm", ["bovenaan", "genest", "lijst_in_lijst"])
def test_tekst_in_vlag_of_bindvorm_als_objectwaarde_geweigerd(waarde: dict[str, Any], code: str, vorm: str) -> None:
    """S-P2-010, herstelronde 3 (R-VEILIG-9, R-TECH-7): ``{"extra_args": "--privileged"}``, ``{"volume": "/:/host"}``
    en ``{"mount": {"source": "/"}}`` in de waarden van een catalogusapp kwamen zonder fout door, terwijl dezelfde
    tekst in een lijst geweigerd werd. Nu krijgt een tekstwaarde in een object dezelfde controle als een losse tekst
    in een lijst, en tellen ``source``, ``src``, ``hostpath`` en ``path`` (genormaliseerd) met een waarde die met "/"
    begint als hostpad."""
    codes = _codes(_catalogus(_in_vorm(vorm, waarde)))
    assert code in codes, codes


def test_vrije_tekst_in_catalogusapp_waarden_blijft_toegestaan() -> None:
    """Tegenproef (R-VEILIG-9, R-TECH-7): vrije tekst is uitgezonderd van de vlag- en bindcontrole: de waarde naast
    ``name`` of ``key`` in een paar (``envs[].value``, ``additional_envs[].value``, ``labels[].value``), ``notes`` en
    ``description``. Gewone waarden (tijdzone, URL, een dataset als hostpad, een pad in de container) blijven geldig.
    De Docker-socket, een ongeldige kluisverwijzing en "unconfined" blijven ook in vrije tekst geweigerd."""
    values = {
        "TZ": "Europe/Amsterdam",
        "additional_envs": [
            {"name": "PATH", "value": "/usr/local/bin:/usr/bin:/bin"},
            {"name": "EXTRA", "value": "--privileged"},
            {"name": "BIND", "value": "/:/host"},
        ],
        "envs": [{"name": "JAVA_OPTS", "value": "-cp /app/lib/*:/app/classes"}],
        "labels": [{"key": "a", "value": "/usr/bin:/bin"}, {"key": "b", "value": "pid=host"}],
        "notes": "privileged: nee. Zie /etc:/x, -v /:/host en --pid",
        "app": {"description": "--privileged en /:/host als voorbeeld in de uitleg"},
        "web": {"url": "https://voorbeeld.invalid/pad", "base_url": "/admin", "poort": "30200"},
        "opslag": {"source": "/mnt/testpool/media", "hostPath": "/mnt/testpool/apps/huis", "mount_path": "/data"},
        "geheim": {"name": "DB_PASSWORD", "value": "vault://app/huis/db_wachtwoord"},
        "resources": {"limits": {"cpus": 2}},
    }
    params = _catalogus(values)
    assert _codes(params) == []
    assert vault_refs(params) == ["vault://app/huis/db_wachtwoord"]
    for vrij, code in (
        (
            {"additional_envs": [{"name": "DOCKER_HOST", "value": "unix:///var/run/docker.sock"}]},
            "docker_socket_verboden",
        ),
        ({"notes": "mount /run/docker.sock"}, "docker_socket_verboden"),
        ({"labels": [{"key": "a", "value": "vault://ander/x"}]}, "vault_ref_ongeldig"),
        ({"notes": "seccomp=unconfined"}, "catalogus_waarde_verboden"),
        ({"envs": [{"name": "PROFIEL", "value": "unconfined"}]}, "catalogus_waarde_verboden"),
    ):
        assert code in _codes(_catalogus(vrij)), vrij
    # Bij de standaard Custom App is het schema vast: de teksten in zijn objecten worden geen Docker-opties en krijgen
    # deze controle niet (een portaalpad "/" en een hostnaam die op een sleutel lijkt blijven geldig).
    ix = install_params(
        hostname="runtime",
        notes="--privileged staat uit; zie /etc:/x",
        portals=[{"name": "web", "scheme": "http", "host": "0.0.0.0", "port": 30555, "path": "/"}],
        labels=[{"key": "toelichting", "value": "/usr/bin:/bin", "containers": ["demo-app"]}],
    )
    assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, ix) == []


def test_gewone_waarden_van_een_catalogusapp_blijven_geldig() -> None:
    """Tegenproef op de vorm die catalogusapps van TrueNAS gebruiken (tijdzone, ``run_as``, ``network`` als object
    met poorten, opslag met ``ix_volume`` en een dataset als ``host_path``, extra omgevingsvariabelen, labels,
    limieten): de tabel en de controle van tekstwaarden weigeren daar niets."""
    values = {
        "TZ": "Europe/Amsterdam",
        "app": {"additional_envs": [{"name": "LOG_LEVEL", "value": "info"}], "publish_server_url": ""},
        "run_as": {"user": 568, "group": 568},
        "network": {
            "host_network": False,
            "web_port": {"bind_mode": "published", "port_number": 30103, "host_ips": []},
            "dns_opts": [],
        },
        "storage": {
            "config": {"type": "ix_volume", "ix_volume_config": {"acl_enable": False, "dataset_name": "config"}},
            "media": {
                "type": "host_path",
                "host_path_config": {"acl_enable": False, "path": "/mnt/testpool/media"},
            },
            "transcodes": {"type": "tmpfs", "tmpfs_config": {"size": 500}},
            "additional_storage": [
                {
                    "type": "host_path",
                    "read_only": True,
                    "mount_path": "/media/films",
                    "host_path_config": {"acl_enable": False, "path": "/mnt/testpool/films"},
                }
            ],
        },
        "labels": [{"key": "soort", "value": "media", "containers": ["huis"]}],
        "resources": {
            "limits": {"cpus": 2, "memory": 4096},
            "gpus": {"use_all_gpus": False, "nvidia_gpu_selection": {}},
        },
    }
    assert _codes(_catalogus(values)) == []


OPDRACHTEN_IX_APP = [
    pytest.param("command", ["java", "-cp", "/app/lib/*:/app/classes", "nl.Main"], id="java_cp"),
    pytest.param("command", ["env", "PATH=/usr/bin:/bin", "app"], id="env_path"),
    pytest.param("command", ["PYTHONPATH=/app:/lib", "python", "-m", "x"], id="pythonpath"),
    pytest.param("command", ["gunicorn", "--pid", "/tmp/g.pid", "app:app"], id="gunicorn_pid"),
    pytest.param("command", ["mytool", "--privileged"], id="eigen_vlag_privileged"),
    pytest.param("command", ["lsblk", "--devices"], id="lsblk_devices"),
    pytest.param("entrypoint", ["/bin/sh", "-c", "exec /app/run --listen 0.0.0.0:8080"], id="sh_c"),
]


@pytest.mark.parametrize(("veld", "opdracht"), OPDRACHTEN_IX_APP)
def test_opdracht_van_de_standaard_custom_app_is_geen_docker_optie(veld: str, opdracht: list[str]) -> None:
    """S-P2-010, herstelronde 3 (R-TECH-8, besluit BN-2 optie b): ``command`` en ``entrypoint`` van de standaard Custom
    App zijn de opdracht van het proces ín de container. Vastgesteld in het ix-app-sjabloon (truenas/apps,
    ``ix-dev/stable/ix-app/templates/docker-compose.yaml``, ix-app 1.4.8): de twee velden gaan alleen naar
    ``set_command`` en ``set_entrypoint`` van de container. Een vlag of een tekst met een dubbele punt daar geeft geen
    Docker-recht; de rechten van de ix-app bewaakt het vaste schema. Deze zeven gewone opdrachten werden ten onrechte
    geweigerd."""
    params = install_params(**{veld: opdracht})
    assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, params) == []


def test_opdracht_van_de_standaard_custom_app_houdt_docker_socket_en_kluisregels() -> None:
    """De uitzondering voor ``command`` en ``entrypoint`` van de ix-app is smal: de Docker-socket, een ongeldige
    kluisverwijzing en "unconfined" blijven geweigerd, een geldige kluisverwijzing wordt nog steeds gevonden (Hub en
    executor geven dan 501), en de uitzondering geldt alleen voor de teksten direct in die twee lijsten: niet voor een
    catalogusapp, niet voor een andere lijst van de ix-app en niet voor een object of lijst ín de opdracht."""
    inst = POLICY.acties["app.install"]

    def ix(**values: Any) -> list[str]:
        return [f.code for f in validate_parameters(POLICY, inst, APP, install_params(**values))]

    for veld in ("command", "entrypoint"):
        assert "docker_socket_verboden" in ix(**{veld: ["app", "--sock=/var/run/docker.sock"]}), veld
        assert "vault_ref_ongeldig" in ix(**{veld: ["app", "vault://ander/x"]}), veld
        assert "catalogus_waarde_verboden" in ix(**{veld: ["app", "--seccomp=unconfined"]}), veld
        assert vault_refs(install_params(**{veld: ["--token", "vault://app/demo-app/token"]})) == [
            "vault://app/demo-app/token"
        ]
        # Geen teksten maar een lijst of object in de opdracht: het schema weigert, en de controle kijkt er wel in.
        genest = ix(**{veld: [["--privileged"]]})
        assert "lijst" in genest and "privileged_verboden" in genest, (veld, genest)
        # Bij een catalogusapp is een eigen opdracht verboden, en een vlag in zo'n lijst ook.
        codes = _codes(_catalogus({veld: ["mytool", "--privileged"]}))
        assert "catalogus_waarde_verboden" in codes and "privileged_verboden" in codes, (veld, codes)
    # Een andere lijst van de ix-app, en een lijst met dezelfde naam dieper in de waarden: geen uitzondering.
    opslag = install_params()["app_create"]["values"]["storage"][0]
    assert "privileged_verboden" in ix(storage=[{**opslag, "command": ["--privileged"]}])
    assert "hostpad_verboden" in ix(dns_config={"options": ["/:/host"]})


# KLEIN-76 (KLEIN-75 A5 en A1; besluit van de gebruiker 2026-11-14 "Nu herstellen"). De middleware van TrueNAS laat
# onbekende sleutels door (``extra='allow'``) en neemt ``ix_volume_config.properties`` mee bij het aanmaken van het
# dataset (ook ``mountpoint``); ``host_path_config.acl`` wordt ook bij ``acl_enable: false`` genormaliseerd. Afgeleid
# uit de bron; NIET GEVALIDEERD (echte NAS).
IX_VOLUME_PROPERTIES = [
    pytest.param({"mountpoint": "/etc"}, id="mountpoint_etc"),
    pytest.param({"compression": "lz4"}, id="gewone_eigenschap"),
    pytest.param({}, id="leeg"),
    pytest.param(None, id="null"),
]


def _ix_volume(properties: Any, sleutel: str = "properties") -> dict[str, Any]:
    return {"type": "ix_volume", "mount_path": "/config",
            "ix_volume_config": {"acl_enable": False, "dataset_name": "config", sleutel: properties}}  # fmt: skip


@pytest.mark.parametrize("properties", IX_VOLUME_PROPERTIES)
def test_zfs_eigenschappen_van_een_ixvolume_worden_altijd_geweigerd(properties: Any) -> None:
    """A5: ``ix_volume_config.properties`` gaat bij TrueNAS ongecontroleerd naar het aanmaken van een ZFS-dataset
    (``mountpoint`` kan dan een systeemmap zijn). Elke aanwezigheid wordt geweigerd met een eigen code, bij de
    standaard Custom App en in de waarden van een catalogusapp, ook in een andere schrijfwijze van de sleutel."""
    ix = validate_parameters(
        POLICY, POLICY.acties["app.install"], APP, install_params(storage=[_ix_volume(properties)])
    )
    assert "zfs_eigenschappen_verboden" in [f.code for f in ix], [f.as_dict() for f in ix]
    assert "parameters.app_create.values.storage[0].ix_volume_config.properties" in [f.veld for f in ix]
    for sleutel in ("properties", "Properties"):
        cat = _codes(_catalogus({"storage": {"config": _ix_volume(properties, sleutel)}}))
        assert "zfs_eigenschappen_verboden" in cat, (sleutel, cat)


MOUNTPOINT_FOUT = ["/etc", "/", "/mnt/.ix-apps/x", "/root", "/mnt/testpool/../etc"]


@pytest.mark.parametrize("pad", MOUNTPOINT_FOUT)
def test_mountpoint_is_overal_een_hostpad(pad: str) -> None:
    """A5: een tekst met "/" onder de sleutel ``mountpoint`` (ook ``mountPoint``) is overal een hostpad: bij de
    standaard Custom App (ook buiten ``properties``) en in de waarden van een catalogusapp."""
    in_properties = install_params(storage=[_ix_volume({"mountpoint": pad})])
    ix = validate_parameters(POLICY, POLICY.acties["app.install"], APP, in_properties)
    assert ("parameters.app_create.values.storage[0].ix_volume_config.properties.mountpoint", "hostpad_verboden") in [
        (f.veld, f.code) for f in ix
    ], [f.as_dict() for f in ix]
    opslag = install_params()["app_create"]["values"]["storage"][0]
    los = validate_parameters(
        POLICY, POLICY.acties["app.install"], APP, install_params(storage=[{**opslag, "mountPoint": pad}])
    )
    assert "hostpad_verboden" in [f.code for f in los], [f.as_dict() for f in los]
    assert "hostpad_verboden" in _codes(_catalogus({"opslag": {"mountpoint": pad}}))
    assert "hostpad_verboden" in _codes(_catalogus({"opslag": {"zfs": {"mountPoint": pad}}}))


def test_mountpoint_tegenproef_dataset_en_geen_pad() -> None:
    """Tegenproef: een ``mountpoint`` op een dataset onder /mnt/<pool>/<dataset> of zonder "/" (zoals bij de andere
    hostpad-sleutels) is geen fout; zonder ``properties`` blijft een ixVolume geldig."""
    opslag = install_params()["app_create"]["values"]["storage"][0]
    for waarde in ("/mnt/testpool/apps/demo-app", "legacy"):
        params = install_params(storage=[{**opslag, "mountpoint": waarde}])
        assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, params) == [], waarde
        assert _codes(_catalogus({"opslag": {"mountpoint": waarde}})) == [], waarde
    zonder = {
        "type": "ix_volume",
        "mount_path": "/config",
        "ix_volume_config": {"acl_enable": False, "dataset_name": "config"},
    }
    assert validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(storage=[zonder])) == []


ACL_BLOKKEN = [
    pytest.param({"path": "/etc", "entries": [{"id_type": "USER", "id": 0, "access": "FULL_CONTROL"}]}, id="etc"),
    pytest.param({"path": "/mnt/testpool/apps/demo-app", "entries": []}, id="dataset"),
    pytest.param({}, id="leeg"),
    pytest.param(None, id="null"),
]


@pytest.mark.parametrize("acl", ACL_BLOKKEN)
def test_acl_blok_bij_de_standaard_custom_app_ook_met_acl_enable_false_geweigerd(acl: Any) -> None:
    """A1: TrueNAS normaliseert ``host_path_config.acl`` ook als ``acl_enable`` false is en zou dan een ACL zetten op
    ``acl.path``. Bij de standaard Custom App is een aanwezig ``acl``-blok dezelfde weigering als ``acl_enable: true``
    (``acl_verboden``), en ``acl.path`` gaat ook door de hostpadregel."""
    cfg = {"path": "/mnt/testpool/apps/demo-app", "acl_enable": False, "acl": acl}
    opslag = [{"type": "host_path", "mount_path": "/data", "host_path_config": cfg}]
    fouten = validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(storage=opslag))
    paren = [(f.veld, f.code) for f in fouten]
    w = "parameters.app_create.values.storage[0].host_path_config"
    assert (w, "acl_verboden") in paren, paren
    if isinstance(acl, dict) and acl.get("path") == "/etc":
        assert (f"{w}.acl.path", "hostpad_verboden") in paren, paren


def test_acl_path_buiten_een_dataset_ook_zonder_acl_enable() -> None:
    """A1: ``acl.path`` gaat bij de standaard Custom App door de hostpadregel, ook als het geen tekst met "/" is."""
    for pad in ("/etc", "etc", "/mnt/.ix-apps/x", 5):
        cfg = {"path": "/mnt/testpool/apps/demo-app", "acl": {"path": pad}}
        opslag = [{"type": "host_path", "mount_path": "/data", "host_path_config": cfg}]
        fouten = validate_parameters(POLICY, POLICY.acties["app.install"], APP, install_params(storage=opslag))
        assert ("parameters.app_create.values.storage[0].host_path_config.acl.path", "hostpad_verboden") in [
            (f.veld, f.code) for f in fouten
        ], (pad, [f.as_dict() for f in fouten])
