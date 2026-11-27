"""C1.4-ALG-01 in de bronrepo: de vastgestelde versie van ``PLATFORM_CONTRACTEN.md`` en
``CONTRACT_1.4_CONFORMITEIT.md`` is gepind op een vaste bron-commit.

De andere repos kopiëren deze twee bestanden byte-gelijk en pinnen dezelfde sha256 in hun drifttest. Wijzigt iemand
hier het contract, dan faalt deze test: een nieuwe contracttekst is een bewuste stap (nieuwe pin + melding aan de
orkestratie voor nieuwe kopieën), nooit een stille wijziging waarmee de kopieën ongemerkt afwijken.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

PV2 = Path(__file__).resolve().parents[4] / "docs" / "platform-v2"
BRON_COMMIT = "02f65746d30a29e192bc27343a33b32b9152aabd"
PINS = {
    "PLATFORM_CONTRACTEN.md": "1976152f65827308789aeb921b0d496927d5afba4858d35de5e25e9c6da7211b",
    "CONTRACT_1.4_CONFORMITEIT.md": "d5fcd7cb477e96bb892f1f429ece9d3e8872cc0dc4dd926d02cf3879ae929112",
    "CONTRACT_1.3_CONFORMITEIT.md": "b5ebba073a8fe8beb715d58e6760feae38e33ad445956d107e64840133dd7924",
}


@pytest.mark.parametrize(("naam", "sha"), sorted(PINS.items()))
def test_contract_is_de_gepinde_versie(naam: str, sha: str) -> None:
    data = (PV2 / naam).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha, (
        f"{naam} wijkt af van de vastgestelde versie (bron-commit {BRON_COMMIT}). Een nieuwe contracttekst vraagt een "
        "nieuwe pin hier én nieuwe byte-gelijke kopieën in alle repos (orkestratie)."
    )


def test_kop_en_conformiteitslijst_horen_bij_elkaar() -> None:
    contract = (PV2 / "PLATFORM_CONTRACTEN.md").read_text(encoding="utf-8")
    assert "Versie: `contracts 1.4`" in contract
    assert "CONTRACT_1.4_CONFORMITEIT.md" in contract
    lijst = (PV2 / "CONTRACT_1.4_CONFORMITEIT.md").read_text(encoding="utf-8")
    assert lijst.startswith("# Conformiteit met contract 1.4")
    for punt in ("C1.4-ALG-01", "C1.4-ASM-01", "C1.4-MGU-01"):
        assert lijst.count(punt) == 1
    for onderdeel in ("poolstatus.lezen", "GET /api/v1/inventory/pools"):
        assert onderdeel in contract and onderdeel in lijst
