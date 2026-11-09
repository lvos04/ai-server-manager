"""Operator-runbooks (B09-006): getypeerde catalogus, vaste fasen, alleen allowlist-acties, geen terminal."""

from __future__ import annotations

from datetime import UTC, datetime

from hub.models import Incident
from hub.runbooks.catalogus import BY_ID, FASEN, RUNBOOKS, H, L, Runbook, V, runbook_hash, validate
from hub.runbooks.engine import runbook_for

SCENARIO_IDS = {
    "service_offline",
    "db_migratie_mislukt",
    "schijf_vol",
    "slechte_deployment",
    "toegang_kwijt",
    "jellyfin_client",
    "gree_onbekend",
    "mso_provider_uitval",
}


def test_catalogus_is_geldig_en_dekt_de_acht_scenarios() -> None:
    assert validate() == []
    assert set(BY_ID) == SCENARIO_IDS  # 05_OPERATIES_EN_UPDATES: acht scenario's
    for r in RUNBOOKS:
        assert tuple(r.stappen()) == FASEN
        assert all(r.stappen()[f] for f in FASEN)
    assert len(runbook_hash()) == 64 and runbook_hash() == runbook_hash()


def test_validatie_vangt_verboden_stappen() -> None:
    bad = Runbook(
        "fout",
        "Fout",
        "test",
        observeren=(L("Open een terminal en kijk rond."),),
        isoleren=(H("x"),),
        mitigeren=(V("Herstart via shell", "shell.exec", "R0"),),
        terugdraaien=(V("Terugzetten", "app.rollback", "R1"),),
        bewijs=(),
        oorzaak=(H("x"),),
        test_na_herstel=("De poort is open.",),
    )
    errors = validate((bad,))
    assert any("terminal" in e for e in errors) and any("shell.exec" in e for e in errors)
    assert any("minimale klasse" in e for e in errors) and any("bewijs is leeg" in e for e in errors)
    assert any("poort open" in e for e in errors)


def _inc(soort: str, bron: str = "ai-server-manager") -> Incident:
    now = datetime.now(UTC)
    return Incident(soort=soort, bron=bron, eerste_op=now, laatste_op=now, geopend_op=now)


def test_koppeling_incident_naar_runbook() -> None:
    cases = {
        ("alert.app-down", "hub:alerts"): "service_offline",
        ("app.gezondheid", "home-control-hub"): "service_offline",
        ("migration.cutover", "mediaguard"): "db_migratie_mislukt",
        ("alert.pool-vol", "hub:alerts"): "schijf_vol",
        ("app.update", "jelly-leon-platform"): "slechte_deployment",
        ("network.tailscale", "home-control-hub"): "toegang_kwijt",
        ("auth.noodlogin", "hub:auth"): "toegang_kwijt",
        ("media.client", "jelly-leon"): "jellyfin_client",
        ("climate.gree", "my_house"): "gree_onbekend",
        ("provider.usenet", "media-source-optimizer"): "mso_provider_uitval",
    }
    for (soort, bron), want in cases.items():
        rb = runbook_for(_inc(soort, bron))
        assert rb is not None and rb.id == want, (soort, bron)
    assert runbook_for(_inc("sso.authentik_sync", "home-control-hub")) is None  # eerlijk: geen runbook
