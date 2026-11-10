"""Inventaris voor contract 1.3 (``docs/platform-v2/CONTRACT_1.3_KANDIDATEN.md``): niets kwijt, alles traceerbaar.

- Elk van de 151 meldingen uit ronde 2 (``CONTRACT_1.3_MELDINGEN_RONDE2.json``) staat precies één keer in de tabel
  melding → groep, met de juiste repo.
- Elke genoemde groep staat in het overzicht, met een klasse (a)–(e) die past bij de letter van de groep, en heeft een
  eigen detailsectie.
- Elke groep (a) heeft een tekstvoorstel en geraakte repos; elke groep heeft minstens één melding of bron.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[4] / "docs" / "platform-v2"
KANDIDATEN = DOCS / "CONTRACT_1.3_KANDIDATEN.md"
MELDINGEN = DOCS / "CONTRACT_1.3_MELDINGEN_RONDE2.json"

GROEP = r"[A-E]\d\d"
OVERZICHT_RIJ = re.compile(rf"^\| \[({GROEP})\]\(#([a-e]\d\d)\) \| \(([a-e])\) \|")
R2_RIJ = re.compile(rf"^\| R2-(\d{{3}}) \| ([^|]+?) \| [^|]+ \| ({GROEP}) \| \(([a-e])\) \| ([^|]+?) \|$")
BRON_ID = r"(?:U|P|X)-\d\d|Δ-[^|]+?|ADR-\d{4}|B03-§[\d.]+"
BRON_RIJ = re.compile(rf"^\| ({BRON_ID}) \| [^|]+ \| [^|]+ \| ({GROEP}) \| \(([a-e])\) \| ([^|]+?) \|$")


def _tekst() -> str:
    return KANDIDATEN.read_text(encoding="utf-8")


def _overzicht() -> dict[str, str]:
    groepen: dict[str, str] = {}
    for regel in _tekst().splitlines():
        m = OVERZICHT_RIJ.match(regel)
        if m:
            assert m.group(1).lower() == m.group(2), regel
            assert m.group(1) not in groepen, f"groep dubbel in het overzicht: {m.group(1)}"
            groepen[m.group(1)] = m.group(3)
    return groepen


def _ook(veld: str) -> list[str]:
    return [] if veld.strip() == "—" else [g.strip() for g in veld.split(",")]


def test_bron_heeft_151_meldingen() -> None:
    data = json.loads(MELDINGEN.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 151
    assert all(isinstance(r, list) and len(r) == 2 and all(isinstance(x, str) and x for x in r) for r in data)


def test_overzicht_klassen_passen_bij_de_groepletter() -> None:
    groepen = _overzicht()
    assert len(groepen) > 50, "te weinig groepen gevonden: klopt de tabelvorm nog?"
    for groep, klasse in groepen.items():
        assert klasse == groep[0].lower(), (groep, klasse)


def test_elke_melding_precies_een_keer_in_een_bestaande_groep() -> None:
    data = json.loads(MELDINGEN.read_text(encoding="utf-8"))
    groepen = _overzicht()
    gezien: dict[int, str] = {}
    for regel in _tekst().splitlines():
        m = R2_RIJ.match(regel)
        if not m:
            continue
        nr = int(m.group(1))
        assert 1 <= nr <= 151, regel
        assert nr not in gezien, f"R2-{nr:03d} staat twee keer in de tabel"
        assert m.group(2).strip() == data[nr - 1][0], f"R2-{nr:03d}: repo klopt niet met de bron"
        groep, klasse = m.group(3), m.group(4)
        assert groepen.get(groep) == klasse, f"R2-{nr:03d}: groep {groep} ({klasse}) niet (zo) in het overzicht"
        for ook in _ook(m.group(5)):
            assert ook in groepen and ook != groep, f"R2-{nr:03d}: 'ook in' {ook} bestaat niet"
        gezien[nr] = groep
    ontbreekt = sorted(set(range(1, 152)) - set(gezien))
    assert not ontbreekt, f"meldingen zonder groep: {ontbreekt}"


def test_overige_bronnen_wijzen_naar_bestaande_groepen() -> None:
    groepen = _overzicht()
    rijen = [m for r in _tekst().splitlines() if (m := BRON_RIJ.match(r))]
    assert len(rijen) > 50, "te weinig overige bronnen gevonden: klopt de tabelvorm nog?"
    ids = [m.group(1) for m in rijen]
    assert len(ids) == len(set(ids)), "een bron-ID staat twee keer in de tabel"
    for m in rijen:
        assert groepen.get(m.group(2)) == m.group(3), m.group(0)
        for ook in _ook(m.group(4)):
            assert ook in groepen, m.group(0)


def test_elke_groep_heeft_een_sectie_en_een_melding() -> None:
    tekst = _tekst()
    groepen = _overzicht()
    gebruikt = {m.group(3) for r in tekst.splitlines() if (m := R2_RIJ.match(r))}
    gebruikt |= {m.group(2) for r in tekst.splitlines() if (m := BRON_RIJ.match(r))}
    for groep in groepen:
        assert f'<a id="{groep.lower()}"></a>\n### {groep} — ' in tekst, f"detailsectie ontbreekt: {groep}"
        assert groep in gebruikt, f"groep {groep} heeft geen melding of bron"


def test_groepen_a_hebben_tekstvoorstel_en_geraakte_repos() -> None:
    tekst = _tekst()
    for groep, klasse in _overzicht().items():
        if klasse != "a":
            continue
        start = tekst.index(f'<a id="{groep.lower()}"></a>')
        volgende = re.search(r'\n<a id="|\n## ', tekst[start + 1 :])
        sectie = tekst[start : start + 1 + volgende.start()] if volgende else tekst[start:]
        assert "**Tekstvoorstel" in sectie, f"{groep}: geen tekstvoorstel"
        assert "**Geraakte repos:**" in sectie, f"{groep}: geen geraakte repos"
        assert "**Uitvoering:**" in sectie, f"{groep}: geen uitvoering"
