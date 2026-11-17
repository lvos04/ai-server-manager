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
#: Bron van contract 1.3 met de aanvulling C-12 (ADR-0031, stap S-P2-C12; blijft 1.3). De volle hash van de eind-commit
#: van die stap staat in de pins van de kopieën in de andere repos. Daarvoor: 02b119c (na de review, RV1–RV13).
BRON_COMMIT = "aanvulling C-12 (S-P2-C12)"
PINS = {
    "PLATFORM_CONTRACTEN.md": "3e12ae564e3ea926784659817285d8e9f2bd7b024639e60f26247813a29cc56e",
    "CONTRACT_1.3_CONFORMITEIT.md": "a9c5c63b4d5f4bc80c2b1a43652d2a8712ee4279d82b42e25344e21c7c1f6f03",
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
