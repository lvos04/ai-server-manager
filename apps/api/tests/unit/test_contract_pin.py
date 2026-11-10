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
#: Vastgestelde bron-commit van contract 1.3 (na de review, RV1–RV13): 02b119c.
BRON_COMMIT = "02b119c"
PINS = {
    "PLATFORM_CONTRACTEN.md": "15b30cf17f91b606451ef9c41f02327076ef76ce655ee94e40e3538106962310",
    "CONTRACT_1.3_CONFORMITEIT.md": "f0a2352ddb27088ae668013501c62a1eaaf879efe742a2d4422ffe8d33b43466",
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
