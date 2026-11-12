"""Operator-runbooks (B09-006): getypeerde catalogus, vaste fasen, alleen allowlist-acties, geen terminal."""

from __future__ import annotations

from datetime import UTC, datetime

from hub.models import Incident
from hub.runbooks.catalogus import (
    ALLOWLIST,
    ALLOWLIST_CUSTOM_APP,
    BY_ID,
    FASEN,
    NA_STOP_GEWEIGERD,
    RUNBOOKS,
    H,
    L,
    Runbook,
    V,
    runbook_hash,
    validate,
)
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


def test_stoppen_van_een_custom_app_is_r2_en_daarna_doet_het_platform_niets_meer() -> None:
    """S-P2-010, bouwpunt 6a (R-VEILIG-5 van S-P2-005): elke ``app.stop`` in een runbook noemt R2 voor een Custom App,
    gelijk aan wat de engine uitrekent (``STOP-EENRICHTING``). Na een stop biedt een runbook ``app.rollback`` of
    ``app.start`` alleen aan met de vermelding dat het platform dat op een gestopte Custom App weigert, en geeft het de
    weg via de TrueNAS-web-UI. ``docs/RUNBOOKS.md`` zegt niet meer alleen "minimaal R1"."""
    from asm_policy import load_policy
    from asm_policy.engine import Herkenning, classify

    from hub.runbooks.export import render

    policy = load_policy()
    custom = Herkenning((), True, False)  # draaiende Custom App: na een stop niet meer herkenbaar
    for aid, klasse in ALLOWLIST_CUSTOM_APP.items():
        c = classify(policy, action_id=aid, target={}, parameters={}, actor_type="user", herkend_als=custom)
        assert c.risk_class == klasse and klasse != ALLOWLIST[aid], aid
    stops = [s for r in RUNBOOKS for f in FASEN for s in r.stappen()[f] if s.action_id == "app.stop"]
    assert len(stops) >= 2 and all(s.custom_app == "R2" for s in stops)
    db = BY_ID["db_migratie_mislukt"]
    terug = [s for s in db.terugdraaien if s.action_id in ("app.rollback", "app.start")]
    assert terug and all(s.custom_app == NA_STOP_GEWEIGERD for s in terug)
    assert any(s.soort == "handmatig" and s.bron == "TrueNAS-web-UI" for s in db.terugdraaien)
    md = render()
    assert "`app.stop` (minimaal R1)" not in md and md.count("`app.stop` (minimaal R1; Custom App: R2)") == len(stops)
    # S-P2-010, R-TECH-5: het platform weigert, niet de app ("een gestopte Custom App weigert het platform" zei het
    # omgekeerde).
    na_stop = [s for r in RUNBOOKS for f in FASEN for s in r.stappen()[f] if s.custom_app == NA_STOP_GEWEIGERD]
    assert na_stop and "een gestopte Custom App weigert het platform" not in md
    assert md.count("; het platform weigert dit bij een gestopte Custom App)") == len(na_stop)


def test_validatie_vangt_app_stop_zonder_custom_app_klasse_en_terugzetten_na_een_stop() -> None:
    def rb(*stappen: object) -> Runbook:
        return Runbook(
            "proef",
            "Proef",
            "test",
            observeren=(L("x"),),
            isoleren=(H("x"),),
            mitigeren=tuple(stappen),  # type: ignore[arg-type]
            terugdraaien=(V("Zet terug.", "app.rollback", "R2"),),
            bewijs=(L("x"),),
            oorzaak=(H("x"),),
            test_na_herstel=("Binnenkant gezond.",),
        )

    fouten = validate((rb(V("Stop de app.", "app.stop", "R1")),))
    assert any("app.stop" in e and "Custom App" in e for e in fouten), fouten
    assert any("app.rollback" in e and "na app.stop" in e for e in fouten), fouten
    assert validate((rb(V("Herstart.", "app.restart", "R1")),)) == []  # zonder stop mag terugzetten gewoon
    goed = Runbook(
        "proef",
        "Proef",
        "test",
        observeren=(L("x"),),
        isoleren=(H("x"),),
        mitigeren=(V("Stop de app.", "app.stop", "R1", custom_app="R2"),),
        terugdraaien=(V("Zet terug.", "app.rollback", "R2", custom_app=NA_STOP_GEWEIGERD),),
        bewijs=(L("x"),),
        oorzaak=(H("x"),),
        test_na_herstel=("Binnenkant gezond.",),
    )
    assert validate((goed,)) == []
    assert any("onbekende waarde" in e for e in validate((rb(V("Stop.", "app.stop", "R1", custom_app="R9")),)))


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


def test_runbooks_md_actueel() -> None:
    from pathlib import Path

    from hub.runbooks.export import export

    out = Path(__file__).resolve().parents[4] / "docs" / "RUNBOOKS.md"
    assert export(out, check=True) == 0, "draai `make runbooks`"
