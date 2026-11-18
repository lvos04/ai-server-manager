"""C1.3-ALG-01 (contract 1.3 kop, §10, A35) in de bronrepo: de vastgestelde versie van ``PLATFORM_CONTRACTEN.md`` en
``CONTRACT_1.3_CONFORMITEIT.md`` is gepind op een vaste bron-commit.

De andere repos kopiëren deze twee bestanden byte-gelijk en pinnen dezelfde sha256 in hun drifttest. Wijzigt iemand
hier het contract, dan faalt deze test: een nieuwe contracttekst is een bewuste stap (nieuwe pin + melding aan de
orkestratie voor nieuwe kopieën), nooit een stille wijziging waarmee de kopieën ongemerkt afwijken.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

PV2 = Path(__file__).resolve().parents[4] / "docs" / "platform-v2"
# Contract 1.3 bevat de aanvulling C-12 (ADR-0031) en het M3-besluit over catalogusbeschikbaarheid (KLEIN-111).
BRON_COMMIT = "7ebed6523dcb643b4f3c8510bda46c918a49ea14 (M3, KLEIN-111)"
PINS = {
    "PLATFORM_CONTRACTEN.md": "c06eebdc23b52fd4e3ffa5be18abc481c2fbbf0938d86c58bebb78a870fd8159",
    "CONTRACT_1.3_CONFORMITEIT.md": "b5ebba073a8fe8beb715d58e6760feae38e33ad445956d107e64840133dd7924",
}


@pytest.mark.parametrize(("naam", "sha"), sorted(PINS.items()))
def test_contract_1_3_is_de_gepinde_versie(naam: str, sha: str) -> None:
    data = (PV2 / naam).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha, (
        f"{naam} wijkt af van de vastgestelde versie (bron-commit {BRON_COMMIT}). Een nieuwe contracttekst vraagt een "
        "nieuwe pin hier én nieuwe byte-gelijke kopieën in alle repos (orkestratie)."
    )


def test_kop_en_conformiteitslijst_horen_bij_elkaar() -> None:
    contract = (PV2 / "PLATFORM_CONTRACTEN.md").read_text(encoding="utf-8")
    assert "Versie: `contracts 1.3`" in contract
    assert "CONTRACT_1.3_CONFORMITEIT.md" in contract
    lijst = (PV2 / "CONTRACT_1.3_CONFORMITEIT.md").read_text(encoding="utf-8")
    assert lijst.startswith("# Conformiteit met contract 1.3")
