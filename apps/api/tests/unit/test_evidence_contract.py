"""Contract 1.2 §11: ``docs/platform-v2/EVIDENCE.json`` gebruikt alleen de vaste Excel-statussen en validatiewaarden.

- ``status`` uit de Excel-lijst; ``Gereed`` en ``Geslaagd`` worden in deze bouwomgeving nooit gezet.
- ``validatie``: één of meer waarden uit de vaste lijst, gescheiden door ``"; "``; toelichting hoort in ``opmerking``.
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
    "NIET GEVALIDEERD (echte NAS)",
    "NIET GEVALIDEERD (hardware)",
    "NIET GEVALIDEERD (account)",
    "NIET GEVALIDEERD (Mac/Xcode)",
    "Sim-geslaagd",
    "Sim-mislukt",
}
VELDEN = {"id", "status", "validatie", "bewijs", "blokkade", "opmerking", "repo", "bijgewerkt"}


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
    waarden = item["validatie"].split("; ")
    assert waarden and all(w in VALIDATIE for w in waarden), item["validatie"]
    assert len(waarden) == len(set(waarden))


def test_ids_uniek() -> None:
    ids = [e["id"] for e in _items()]
    assert len(ids) == len(set(ids))
