"""Tegenproeven voor de controles van de rooktest (``deploy/smoke-controles.sh``, gebruikt door ``deploy/smoke.sh``).

S-P3-170 herstel R-TECH-2 en -3: UID's worden exact numeriek vergeleken (5680 is niet 568), elk blijvend proces moet
reëel én effectief een toegestane UID hebben, en een afwijkende executor-identiteit na herstart of harde stop breekt
de rooktest af. Draait zonder Docker; de volledige rooktest draait in de CI-job ``images``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
CONTROLES = REPO / "deploy" / "smoke-controles.sh"
SMOKE = REPO / "deploy" / "smoke.sh"


def bash(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Draai ``script`` onder ``set -euo pipefail`` met de controles geladen, zoals in smoke.sh."""
    return subprocess.run(
        ["bash", "-c", f'set -euo pipefail; . "{CONTROLES}"; {script}', "rook", *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("regels", "toegestaan", "ok"),
    [
        ("568 568\n569 569", "568 569", True),
        ("568 568", "568", True),
        ("0 0\n568 568", "568 569", False),  # rootproces
        ("568 0", "568", False),  # effectief root
        ("0 568", "568", False),  # reëel root
        ("5680 5680", "568", False),  # deeltekst van 568
        ("568 5680", "568", False),
        ("56 56", "568", False),
        ("569 569", "568", False),  # runner-UID in de executor
        ("", "568", False),  # niets gelezen
        ("568", "568", False),  # onvolledige regel
        ("568 568 1", "568", False),
        ("abc 568", "568", False),
    ],
)
def test_uids_toegestaan_exact_numeriek(regels: str, toegestaan: str, ok: bool) -> None:
    r = bash(f'uids_toegestaan proef "$1" {toegestaan}', regels)
    assert (r.returncode == 0) is ok, r.stderr


@pytest.mark.parametrize(
    ("regels", "ok"),
    [("568 568\n569 569", True), ("568 568\n5690 5690", False), ("568 568\n569 568", False), ("568 568", False)],
)
def test_uid_aanwezig_runner_569(regels: str, ok: bool) -> None:
    assert (bash('uid_aanwezig runner "$1" 569', regels).returncode == 0) is ok


@pytest.mark.parametrize(
    ("uitvoer", "ok"),
    [
        ("Uid\t568\nCapEff\t0000000000000000", True),
        ("Uid\t5680\nCapEff\t0000000000000000", False),
        ("Uid\t0\nCapEff\t0000000000000000", False),
        ("XUid\t568", False),
    ],
)
def test_healthcheck_regel_exact(uitvoer: str, ok: bool) -> None:
    assert (bash("exacte_regel hc \"$1\" $'Uid\\t568'", uitvoer).returncode == 0) is ok


@pytest.mark.parametrize("hoe", ["restart", "kill"])
def test_afwijkende_executor_identiteit_breekt_de_rooktest_af(hoe: str) -> None:
    # Zelfde vorm als de herstartlus in smoke.sh: na de vergelijking mag het script niet verder lopen.
    lus = 'gelijk "na $2: executor-identiteit ongewijzigd" "$3" "$1" || exit 1; echo VERDER'
    afwijkend = bash(lus, "id-oud", hoe, "id-nieuw")
    assert afwijkend.returncode == 1 and "VERDER" not in afwijkend.stdout, afwijkend
    gelijk = bash(lus, "id-oud", hoe, "id-oud")
    assert gelijk.returncode == 0 and f"ok: na {hoe}: executor-identiteit ongewijzigd" in gelijk.stdout


def test_smoke_gebruikt_de_exacte_controles() -> None:
    tekst = SMOKE.read_text(encoding="utf-8")
    assert '. "$(dirname "${BASH_SOURCE[0]}")/smoke-controles.sh"' in tekst
    # Een vergelijking in een &&-lijst breekt onder set -e niet af (R-TECH-3).
    assert "&& echo" not in tekst
    assert '"$(exec_id)" "$EXEC_ID" || exit 1' in tekst
    assert 'uids_toegestaan "Hub: elk proces reëel en effectief 568 of 569" "$v" 568 569 || exit 1' in tekst
    assert 'uids_toegestaan "executor: elk proces reëel en effectief 568" "$v" 568 || exit 1' in tekst
    assert 'exacte_regel "healthcheck $1 na de wissel:' in tekst
    assert re.search(r"for how in restart kill; do", tekst)
