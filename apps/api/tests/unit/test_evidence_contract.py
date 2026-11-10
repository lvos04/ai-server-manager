"""Contract 1.3 §11: ``docs/platform-v2/EVIDENCE.json`` gebruikt alleen de vaste Excel-statussen en validatiewaarden.

- ``status`` uit de Excel-lijst; ``Gereed`` en ``Geslaagd`` worden in deze bouwomgeving nooit gezet.
- ``validatie``: één of meer waarden uit de vaste lijst, gescheiden door ``"; "``; nooit leeg; toelichting hoort in
  ``opmerking``. ``Niet getest`` alleen bij status ``Niet gestart`` (nieuw in 1.3).
- Elke ``NIET GEVALIDEERD (…)`` die in ``blokkade`` staat, staat ook in ``validatie`` (nieuw in 1.3).
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


def test_ids_uniek() -> None:
    ids = [e["id"] for e in _items()]
    assert len(ids) == len(set(ids))
