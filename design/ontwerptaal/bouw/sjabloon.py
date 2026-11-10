"""Referentie-renderer voor het Peil-statuspagina-sjabloon (Peil 1.1.1), gelijk aan bouw/sjabloon.mjs.

Voor de Python-diensten (FastAPI, HTML zonder JS). Kopieer deze functie of vergelijk de eigen renderer ermee:
de test bouw/test-sjabloon.mjs controleert dat beide byte-gelijke uitvoer geven voor alle statuspagina-prototypes.

{{x}} = tekst (HTML-escaped) · <!--ALS:x-->…<!--/ALS:x--> · <!--NIET:x-->…<!--/NIET:x--> · <!--ELK:l-->…<!--/ELK:l-->
Eén doorgang: een ingevulde waarde wordt nooit opnieuw als sjabloon gelezen (E07). Waar = niet leeg: False, None, '',
0 en een lege lijst zijn onwaar. Geef tekst door (str); True/False worden "true"/"false" zoals in JavaScript.

Gebruik als script (voor de test): python3 -I sjabloon.py <sjabloon.html> <gegevens.json>  → uitvoer op stdout.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

_TOKEN = re.compile(r"<!--(/?)(ELK|ALS|NIET):(\w+)-->|\{\{(\w+)\}\}")


def _esc(waarde: Any) -> str:
    if waarde is None:
        tekst = ""
    elif isinstance(waarde, bool):
        tekst = "true" if waarde else "false"
    else:
        tekst = str(waarde)
    return (tekst.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _waar(waarde: Any) -> bool:
    return bool(waarde)


def lees(sjabloon: str) -> list:
    """Leest het sjabloon in een boom; geeft ValueError bij een niet-gesloten of verkeerd genest blok."""
    wortel: dict = {"kids": []}
    stapel = [wortel]
    pos = 0
    for m in _TOKEN.finditer(sjabloon):
        top = stapel[-1]
        if m.start() > pos:
            top["kids"].append(sjabloon[pos:m.start()])
        pos = m.end()
        if m.group(4):
            top["kids"].append({"plek": m.group(4)})
        elif not m.group(1):
            blok = {"soort": m.group(2), "naam": m.group(3), "kids": []}
            top["kids"].append(blok)
            stapel.append(blok)
        else:
            if len(stapel) == 1 or top["soort"] != m.group(2) or top["naam"] != m.group(3):
                raise ValueError(f"sjabloon: onverwachte sluiting {m.group(0)}")
            stapel.pop()
    if len(stapel) != 1:
        raise ValueError(f"sjabloon: blok niet gesloten: {stapel[-1]['soort']}:{stapel[-1]['naam']}")
    if pos < len(sjabloon):
        wortel["kids"].append(sjabloon[pos:])
    return wortel["kids"]


def _schrijf(knopen: list, gegevens: dict) -> str:
    uit = []
    for k in knopen:
        if isinstance(k, str):
            uit.append(k)
        elif "plek" in k:
            uit.append(_esc(gegevens.get(k["plek"])))
        elif k["soort"] == "ELK":
            for item in gegevens.get(k["naam"]) or []:
                uit.append(_schrijf(k["kids"], {**gegevens, **item}))
        elif k["soort"] == "ALS":
            if _waar(gegevens.get(k["naam"])):
                uit.append(_schrijf(k["kids"], gegevens))
        elif not _waar(gegevens.get(k["naam"])):  # NIET
            uit.append(_schrijf(k["kids"], gegevens))
    return "".join(uit)


def render(sjabloon: str, gegevens: dict) -> str:
    return _schrijf(lees(sjabloon), gegevens)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        tpl = f.read()
    with open(sys.argv[2], encoding="utf-8") as f:
        data = json.load(f)
    sys.stdout.write(render(tpl, data))
