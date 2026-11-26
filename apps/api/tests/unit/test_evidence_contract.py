"""Contract 1.3 §11: ``docs/platform-v2/EVIDENCE.json`` gebruikt alleen de vaste Excel-statussen en validatiewaarden.

- ``status`` uit de Excel-lijst; ``Gereed`` en ``Geslaagd`` worden in deze bouwomgeving nooit gezet.
- ``validatie``: één of meer waarden uit de vaste lijst, gescheiden door ``"; "``; nooit leeg; toelichting hoort in
  ``opmerking``. ``Niet getest`` alleen bij status ``Niet gestart`` (nieuw in 1.3).
- Elke ``NIET GEVALIDEERD (…)`` die in ``blokkade`` staat, staat ook in ``validatie`` (nieuw in 1.3).
- De vaste lijst hieronder is precies de tabel van §11 (sinds de aanvulling C-12 met ``NIET GEVALIDEERD (echte Hub)``).
- Naast Excel-ID's mogen contractpunten (``C1.3-<REPO>-<nn>``, ``C1.2-<code>``) en reviews (``REVIEW-<repo>-…``) een
  eigen regel hebben; ``tools/excel/update_excel.py`` meldt die in een eigen overzicht.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

EVIDENCE = Path(__file__).resolve().parents[4] / "docs" / "platform-v2" / "EVIDENCE.json"
CONTRACT = EVIDENCE.with_name("PLATFORM_CONTRACTEN.md")
STATUSSEN = {"Niet gestart", "Bezig", "Geblokkeerd", "N.v.t.", "Mislukt", "Open", "Ingevuld", "Getest"}
NOOIT = {"Gereed", "Geslaagd"}
VALIDATIE = {
    "Sim-getest",
    "Unit-getest",
    "Intel-iGPU-getest (ontwikkelmachine)",
    "NIET GEVALIDEERD (echte NAS)",
    "NIET GEVALIDEERD (hardware)",
    "NIET GEVALIDEERD (account)",
    "NIET GEVALIDEERD (Mac/Xcode)",
    "NIET GEVALIDEERD (echte Hub)",
    "Sim-geslaagd",
    "Sim-mislukt",
    "Niet getest",
}
VELDEN = {"id", "status", "validatie", "bewijs", "blokkade", "opmerking", "repo", "bijgewerkt"}
#: Contractpunten en reviews (contract 1.3 §11); andere ID's zijn Excel-ID's.
CONTRACTPUNT = re.compile(r"C1\.\d+-[A-Z0-9]+(?:-\d\d)?")
REVIEW = re.compile(r"REVIEW-ai-server-manager-[a-z0-9][a-z0-9.-]*")
NIET_GEVALIDEERD = re.compile(r"NIET GEVALIDEERD \([^)]*\)")


def _items() -> list[dict[str, Any]]:
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data
    return data


@pytest.mark.parametrize("item", _items(), ids=lambda e: str(e.get("id")))
def test_item_volgt_paragraaf_11(item: dict[str, Any]) -> None:
    assert set(item) == VELDEN
    assert item["repo"] == "ai-server-manager"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["bijgewerkt"])
    assert item["status"] in STATUSSEN
    assert item["status"] not in NOOIT
    assert item["validatie"].strip(), "een lege validatie is nooit toegestaan"
    waarden = item["validatie"].split("; ")
    assert waarden and all(w in VALIDATIE for w in waarden), item["validatie"]
    assert len(waarden) == len(set(waarden))
    if "Niet getest" in waarden:
        assert item["status"] == "Niet gestart", "'Niet getest' alleen bij status 'Niet gestart'"


@pytest.mark.parametrize("item", _items(), ids=lambda e: str(e.get("id")))
def test_niet_gevalideerd_in_blokkade_staat_ook_in_validatie(item: dict[str, Any]) -> None:
    waarden = item["validatie"].split("; ")
    for gevonden in NIET_GEVALIDEERD.findall(item["blokkade"]):
        assert gevonden in VALIDATIE, f"{gevonden!r} is geen waarde uit de vaste lijst"
        assert gevonden in waarden, f"{gevonden!r} staat in blokkade maar niet in validatie"


@pytest.mark.parametrize("item", _items(), ids=lambda e: str(e.get("id")))
def test_contractpunten_en_reviews_hebben_de_vaste_vorm(item: dict[str, Any]) -> None:
    rid = item["id"]
    if rid.startswith("C1."):
        assert CONTRACTPUNT.fullmatch(rid), rid
    if rid.startswith("REVIEW-"):
        assert REVIEW.fullmatch(rid), rid


@pytest.mark.parametrize("rid", ["EX45", "EX46", "B12-001"])
def test_flowproef_vermeldt_het_vereiste_dienstaccount(rid: str) -> None:
    per_id = {regel["id"]: regel for regel in _items()}
    assert "NIET GEVALIDEERD (account)" in per_id[rid]["validatie"].split("; ")


@pytest.mark.parametrize(
    ("rid", "soort"),
    [
        ("B01-001", "account"),
        ("B01-004", "account"),
        ("B01-007", "account"),
        ("B01-008", "account"),
        ("B01-009", "echte NAS"),
        ("B01-009", "account"),
        ("B02-001", "echte NAS"),
        ("B02-001", "account"),
        ("B02-002", "echte NAS"),
        ("B02-002", "account"),
        ("B02-003", "echte NAS"),
        ("B02-003", "account"),
        ("B02-004", "echte NAS"),
        ("B02-004", "account"),
        ("B02-006", "account"),
        ("B02-007", "echte NAS"),
        ("B02-007", "account"),
        ("B02-008", "echte NAS"),
        ("B02-008", "account"),
        ("B02-010", "echte NAS"),
        ("B02-010", "account"),
        ("B02-011", "account"),
        ("B02-012", "echte NAS"),
        ("B02-012", "account"),
        ("B09-001", "account"),
        ("B09-002", "account"),
        ("B09-003", "hardware"),
        ("B09-004", "account"),
        ("B09-006", "echte NAS"),
        ("B09-006", "account"),
        ("B12-003", "account"),
        ("B12-004", "hardware"),
        ("B12-005", "account"),
        ("B12-007", "account"),
        ("C1.3-ALG-05", "echte NAS"),
        ("C1.3-ASM-05", "account"),
        ("C1.3-ASM-07", "account"),
        ("C1.3-ASM-10", "echte NAS"),
        ("C1.3-ASM-18", "account"),
        ("C1.3-ASM-19", "account"),
        ("C1.3-ASM-20", "account"),
        ("C1.3-ASM-21", "account"),
        ("C1.3-ASM-22", "echte NAS"),
        ("C1.3-ASM-22", "hardware"),
        ("D01", "account"),
        ("D02", "account"),
        ("D03", "account"),
        ("D04", "echte NAS"),
        ("D05", "echte NAS"),
        ("D06", "hardware"),
        ("D06", "account"),
        ("D07", "account"),
        ("D08", "hardware"),
        ("D09", "echte NAS"),
        ("D11", "echte NAS"),
        ("D12", "echte NAS"),
        ("D13", "echte NAS"),
        ("D14", "echte NAS"),
        ("D15", "echte NAS"),
        ("D15", "account"),
        ("D16", "account"),
        ("D17", "hardware"),
        ("D17", "account"),
        ("EX16", "account"),
        ("EX19", "account"),
        ("EX20", "account"),
        ("EX21", "echte NAS"),
        ("EX21", "account"),
        ("EX23", "hardware"),
        ("EX28", "echte NAS"),
        ("EX30", "echte NAS"),
        ("EX39", "account"),
        ("EX40", "account"),
        ("EX50", "account"),
        ("I01-01-04", "account"),
        ("I23-23-03", "account"),
        ("I23-23-05", "account"),
        ("I23-23-06", "account"),
    ],
)
def test_praktijkproef_vermeldt_de_vereiste_validatie(rid: str, soort: str) -> None:
    """De acceptatiestappen N-P6 en de installatiechecklists bepalen welke praktijkproef openstaat."""
    per_id = {regel["id"]: regel for regel in _items()}
    assert f"NIET GEVALIDEERD ({soort})" in per_id[rid]["validatie"].split("; ")


def test_ids_uniek() -> None:
    ids = [e["id"] for e in _items()]
    assert len(ids) == len(set(ids))


def test_vaste_lijst_is_de_tabel_van_paragraaf_11() -> None:
    """De lijst van deze test volgt het contract: een waarde erbij of eraf zonder contracttekst is rood."""
    tekst = CONTRACT.read_text(encoding="utf-8")
    begin = tekst.index("## 11. Bewijs en Excel")
    p11 = tekst[begin : tekst.index("## 12.", begin)]
    in_tabel: set[str] = set()
    for regel in p11.splitlines():
        regel = regel.strip()
        if regel.startswith("| `"):
            eerste_cel = regel.split(" | ")[0]
            in_tabel.update(re.findall(r"`([^`]+)`", eerste_cel))
    assert in_tabel == VALIDATIE, f"verschil met contract §11: {sorted(in_tabel ^ VALIDATIE)}"
