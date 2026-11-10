"""C1.3-ASM-17 (contract 1.3 §9, A11/A30/A32): de eigen manifesten van Hub en executor.

Deze test bewaakt de contractregels die niet van de versie van de validator afhangen, op tekstniveau (geen extra
YAML-afhankelijkheid): kop "platformcontract 1.3", geen ``HUB_*`` als parameter of env (gereserveerd, §3.2), een
monitorplan ``healthcheck.monitor`` op ``/readyz``, ``accepted_findings`` alleen uit de vaste lijst van §9 (en
``digest_pending_release`` alleen zolang de digest leeg is), installatie als standaard Custom App en de licentie
GPL-3.0 (§1.1 besluit 8). De volledige controle met de validator van appstore-en-fork in ``--strict`` draait in CI
(job ``manifest``, vaste commit).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
MANIFESTEN = sorted((ROOT / "deploy" / "manifest").glob("*.manifest.yaml"))
# Contract 1.3 §9: alleen deze waarschuwingen mogen met reden geaccepteerd worden; fouten nooit.
TOEGESTAAN = {"backup_db_export_none", "secret_in_form", "digest_pending_release"}
MONITOR = re.compile(
    r"^  monitor: \{pad: (?P<pad>/[a-z]+), verwachte_status: (?P<status>\d{3}), "
    r"timeout_s: (?P<timeout>\d+), interval_s: (?P<interval>\d+)\}$",
    re.MULTILINE,
)


def bevindingen(tekst: str) -> list[str]:
    """Overtredingen van de contractregels hierboven; leeg = in orde."""
    fout: list[str] = []
    regels = tekst.splitlines()
    if not regels or "platformcontract 1.3" not in regels[0]:
        fout.append("kop_niet_1_3")
    inhoud = [r for r in regels if not r.lstrip().startswith("#")]
    if any("HUB_" in r for r in inhoud):
        fout.append("reserved_env")
    if not re.search(r"^install:\n  method: custom_app$", tekst, re.MULTILINE):
        fout.append("geen_custom_app")
    if any(re.search(r"\b(compose|custom_compose_config)\b\s*:", r) for r in inhoud):
        fout.append("compose_verboden")
    if any(re.search(r"\btag:\s*\"?latest\"?\s*$", r) for r in inhoud):
        fout.append("latest_tag")
    if "  license: GPL-3.0" not in inhoud:
        fout.append("licentie_niet_gpl3")
    m = MONITOR.search(tekst)
    if m is None:
        fout.append("healthcheck_monitor_missing")
    elif m["pad"] != "/readyz" or m["status"] != "200" or not (1 <= int(m["timeout"]) < int(m["interval"])):
        fout.append("monitor_ongeldig")
    _kop, gevonden, rest = tekst.partition("\naccepted_findings:\n")
    codes = re.findall(r"^  - code: ([a-z_]+)$", rest, re.MULTILINE) if gevonden else []
    if set(codes) - TOEGESTAAN:
        fout.append("accepted_finding_niet_toegestaan")
    digest_leeg = re.search(r"^  digest: null$", tekst, re.MULTILINE) is not None
    if ("digest_pending_release" in codes) != digest_leeg:
        fout.append("digest_pending_release_klopt_niet")
    return fout


def test_beide_eigen_manifesten_gevonden() -> None:
    assert [p.name for p in MANIFESTEN] == [
        "ai-server-manager-executor.manifest.yaml",
        "ai-server-manager.manifest.yaml",
    ]


@pytest.mark.parametrize("pad", MANIFESTEN, ids=lambda p: p.name)
def test_eigen_manifest_volgt_contract_1_3(pad: Path) -> None:
    assert bevindingen(pad.read_text(encoding="utf-8")) == []


def test_monitorpad_bestaat_achter_de_webpoort() -> None:
    """Het monitorplan van de Hub wijst naar /readyz op de webpoort: de Node-doorgang stuurt dat door naar de API."""
    proxy = (ROOT / "apps" / "web" / "server" / "proxy.mjs").read_text(encoding="utf-8")
    assert '"/readyz"' in proxy


@pytest.mark.parametrize(
    ("wijziging", "verwacht"),
    [
        (lambda t: t.replace("platformcontract 1.3", "platformcontract 1.2", 1), "kop_niet_1_3"),
        (lambda t: t.replace("  env: []", "  env:\n    - name: HUB_URL\n      value: x"), "reserved_env"),
        (lambda t: re.sub(r"^  monitor: .*\n", "", t, flags=re.MULTILINE), "healthcheck_monitor_missing"),
        (lambda t: t.replace("pad: /readyz", "pad: /healthz"), "monitor_ongeldig"),
        (
            lambda t: t.replace("- code: digest_pending_release", "- code: install_reason_ontbreekt"),
            "accepted_finding_niet_toegestaan",
        ),
        (
            lambda t: t.replace("  digest: null", '  digest: "sha256:' + "a" * 64 + '"'),
            "digest_pending_release_klopt_niet",
        ),
        (lambda t: t.replace('  tag: "0.1.0"', '  tag: "latest"'), "latest_tag"),
        (lambda t: t.replace("  method: custom_app", "  method: catalog_app"), "geen_custom_app"),
        (lambda t: t.replace("  license: GPL-3.0", "  license: null"), "licentie_niet_gpl3"),
        (lambda t: t + "compose: {}\n", "compose_verboden"),
    ],
)
def test_controle_vangt_elke_overtreding(wijziging: Callable[[str], str], verwacht: str) -> None:
    """Negatieve gevallen: elke bewust ingebouwde fout in een kopie van het Hub-manifest wordt gevonden."""
    tekst = (ROOT / "deploy" / "manifest" / "ai-server-manager.manifest.yaml").read_text(encoding="utf-8")
    assert bevindingen(tekst) == []
    gewijzigd = wijziging(tekst)
    assert gewijzigd != tekst
    assert verwacht in bevindingen(gewijzigd)
