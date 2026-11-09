#!/usr/bin/env python3
"""Werk de afvinklijst-Excel bij: rijen toevoegen en EVIDENCE.json-bestanden samenvoegen.

Bewerkt de werkbladen rechtstreeks op XML-niveau, zodat opmaak, tabellen,
dropdowns en voorwaardelijke opmaak (ook de databar op 'Appoverzicht')
behouden blijven. Een deel van het werkboek dat inhoudelijk niet verandert,
wordt byte voor byte ongewijzigd teruggeschreven.

Wat het hulpmiddel kan:
- ``--werkpakketten``: rijen in het formaat van ``08_EXCEL/tasks.json`` toevoegen
  aan het blad Werkpakketten. Een rij met een bestaand ID wordt inhoudelijk
  vervangen (bijv. een uitgebreide B03-rij); status, bewijs en de kolommen
  Validatie/Blokkade/Bijgewerkt blijven dan staan.
- ``--testen``: testrijen in het formaat van ``08_EXCEL/e2e_cases.json``
  (``[ID, scenario, uitvoeren, verwacht resultaat]``) toevoegen aan het blad
  Testmatrix; Prioriteit en startstatus per rij uit ``--testmeta`` (het veld
  ``per_test`` van ``EXCEL_TAKEN_PER_REPO.json``).
- ``--fasen``: faserijen (bijv. P4-0 na P3) toevoegen aan het blad Fasen; het
  fasenblok op het Dashboard groeit mee.
- ``--evidence``/``--program``: de bekende samenvoeging van bewijs.

Bij het invoegen groeien tabelbereiken, dropdowns (dataValidations),
voorwaardelijke opmaak en formules op andere bladen (Dashboard, Appoverzicht)
mee, zoals Excel dat bij het invoegen van een rij zou doen. Daarna worden de
opgeslagen formuleresultaten opnieuw berekend (alleen eenvoudige formules:
COUNTA, COUNTIF(S), IFERROR, + - * /, celverwijzingen).

Regels (PLATFORM_CONTRACTEN.md §11, keuze van de gebruiker):
- 'Gereed' en 'Geslaagd' worden NOOIT door dit hulpmiddel gezet. Bewijs met zo'n
  status wordt teruggezet naar 'Bezig' met een waarschuwing; een nieuwe rij met
  zo'n (start)status wordt geweigerd en er wordt niets geschreven.
- Meerdere bewijsregels voor dezelfde ID worden samengevoegd; de
  voorzichtigste status wint.
- Idempotent: dezelfde invoer twee keer verwerken verandert de tweede keer niets.

Gebruik:
  python3 update_excel.py --xlsx <pad.xlsx> [--werkpakketten RIJEN.json ...]
         [--testen TESTEN.json ...] [--testmeta EXCEL_TAKEN_PER_REPO.json]
         [--testdocument DOC] [--fasen FASEN.json] [--evidence <EVIDENCE.json> ...]
         [--program <EVIDENCE_PROGRAMMA.json>] [--date JJJJ-MM-DD] [--out <pad.xlsx>]
Vereist: lxml.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/package/2006/relationships"
X = f"{{{NS}}}"

ALLOWED = {
    "Werkpakketten": ["Niet gestart", "Bezig", "Gereed", "Geblokkeerd", "N.v.t."],
    "Fasen": ["Niet gestart", "Bezig", "Gereed", "Geblokkeerd", "N.v.t."],
    "Testmatrix": ["Niet gestart", "Bezig", "Geslaagd", "Mislukt", "Geblokkeerd", "N.v.t."],
    "Besluiten": ["Open", "Ingevuld", "Getest", "Geblokkeerd", "N.v.t."],
}
FORBIDDEN = {"Gereed", "Geslaagd"}
# Hogere waarde = voorzichtiger (wint bij samenvoegen).
PRECEDENCE = {
    "N.v.t.": 0,
    "Niet gestart": 1,
    "Open": 1,
    "Ingevuld": 2,
    "Bezig": 2,
    "Getest": 3,
    "Geblokkeerd": 4,
    "Mislukt": 5,
}
# Kolommen (1-based) per blad: id, status, bewijs, en nieuwe kolommen.
LAYOUT = {
    "Werkpakketten": {"id": 1, "status": 10, "bewijs": 11, "extra_start": 15},
    "Testmatrix": {"id": 1, "status": 6, "bewijs": 7, "extra_start": 9},
    "Besluiten": {"id": 1, "status": 5, "bewijs": 7, "extra_start": 9, "waarde": 6},
    "Fasen": {"id": 1, "status": 4, "bewijs": 5, "extra_start": 6},
}
EXTRA_HEADERS = ["Validatie", "Blokkade / opmerking", "Bijgewerkt"]
# tasks.json-veld -> kolom op Werkpakketten (J = status en K = bewijs staan niet in tasks.json).
TASK_FIELDS = [
    "ID",
    "Project",
    "Fase",
    "Soort",
    "Taak",
    "Uitvoering",
    "Acceptatie",
    "Risico",
    "Prioriteit",
    "Afhankelijkheid",
    "Bron",
    "Document",
]
TASK_COLUMNS = {
    "ID": 1,
    "Project": 2,
    "Fase": 3,
    "Soort": 4,
    "Prioriteit": 5,
    "Risico": 6,
    "Taak": 7,
    "Uitvoering": 8,
    "Acceptatie": 9,
    "Afhankelijkheid": 12,
    "Document": 13,
    "Bron": 14,
}
# Testmatrix: A ID, B scenario, C uitvoeren, D verwacht, E prioriteit, F status, G bewijs, H document.
TEST_COLUMNS = {"ID": 1, "Scenario": 2, "Uitvoeren": 3, "Verwacht": 4, "Prioriteit": 5, "Document": 8}
# Fasen: A fase, B beschrijving, C go/no-go, D status, E bewijs/akkoord.
FASE_COLUMNS = {"id": 1, "beschrijving": 2, "go_nogo": 3}
FASEN_BLAD = "Fasen"
PRIORITEITEN = {"P0", "P1", "P2", "P3"}
NIET_GEVALIDEERD_RE = re.compile(r"NIET GEVALIDEERD \([^)]*\)")
BLOKKADE_START = "Startstatus Geblokkeerd: alleen een echte uitvoering telt (zie Verwacht resultaat)"

_SST: list[str] = []


class ExcelFout(Exception):
    """Invoer die het hulpmiddel weigert; er wordt dan niets geschreven."""


# ------------------------------------------------------------------ cellen en verwijzingen
def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(ref: str) -> int:
    m = re.match(r"\$?([A-Z]+)", ref)
    if not m:
        raise ValueError(f"geen celverwijzing: {ref}")
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n


def row_index(ref: str) -> int:
    m = re.search(r"(\d+)$", ref)
    if not m:
        raise ValueError(f"geen rijnummer: {ref}")
    return int(m.group(1))


def cell_text(c) -> str:
    if c is None:
        return ""
    v = c.find(X + "v")
    if v is not None and v.text is not None:
        if c.get("t") == "s":
            try:
                return _SST[int(v.text)]
            except (ValueError, IndexError):
                return v.text
        return v.text
    t = c.find(f"{X}is/{X}t")
    return t.text if t is not None and t.text else ""


def find_cell(row, col: int):
    for c in row.findall(X + "c"):
        if col_index(c.get("r")) == col:
            return c
    return None


def _cell_for(row, col: int):
    ref = f"{col_letter(col)}{row.get('r')}"
    cells = row.findall(X + "c")
    for c in cells:
        if c.get("r") == ref:
            return c
    target = etree.Element(X + "c")
    target.set("r", ref)
    idx = len(cells)
    for i, c in enumerate(cells):
        if col_index(c.get("r")) > col:
            idx = i
            break
    row.insert(idx, target)
    return target


def set_cell(row, col: int, value: str, style: str | None = None) -> bool:
    """Zet een tekstwaarde; geeft True als er iets veranderde. Lege tekst = cel zonder <v>."""
    bestaand = find_cell(row, col)
    if (
        bestaand is not None
        and bestaand.find(X + "f") is None
        and bestaand.get("t") in ("str", None, "inlineStr")
        and cell_text(bestaand) == value
        and (style is None or bestaand.get("s") == style)
        and (value or bestaand.find(X + "v") is None)
    ):
        return False
    target = _cell_for(row, col)
    for child in list(target):
        target.remove(child)
    if style is not None:
        target.set("s", style)
    target.set("t", "str")
    if value:
        v = etree.SubElement(target, X + "v")
        v.text = value
    return True


REF_RE = r"\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?"
QUAL_RE = re.compile(r"(?P<sheet>'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!(?P<ref>" + REF_RE + ")")
UNQUAL_RE = re.compile(r"(?<![A-Za-z0-9_!.$'])(?P<ref>" + REF_RE + r")(?![A-Za-z0-9_(!])")


def _split_cell(part: str) -> tuple[str, str, str, int]:
    m = re.fullmatch(r"(\$?)([A-Z]{1,3})(\$?)(\d+)", part)
    if not m:
        raise ValueError(part)
    return m.group(1), m.group(2), m.group(3), int(m.group(4))


def shift_ref(ref: str, at: int, n: int, tail: bool) -> str:
    """Pas een verwijzing aan voor het invoegen van n rijen vóór rij `at` (Excel-semantiek).

    tail=True: rijen worden direct na de laatste gegevensrij toegevoegd; een bereik dat precies op rij at-1 eindigt,
    groeit dan mee (zoals een Excel-tabel die uitbreidt).
    """
    if ":" in ref:
        a, b = ref.split(":")
        d1, c1, e1, r1 = _split_cell(a)
        d2, c2, e2, r2 = _split_cell(b)
        if r1 >= at:
            r1 += n
        if r2 >= at or (tail and r2 == at - 1 and r1 <= r2):
            r2 += n
        return f"{d1}{c1}{e1}{r1}:{d2}{c2}{e2}{r2}"
    d, c, e, r = _split_cell(ref)
    if r >= at:
        r += n
    return f"{d}{c}{e}{r}"


def _sheet_name(token: str) -> str:
    return token[1:-1].replace("''", "'") if token.startswith("'") else token


def shift_formula(formula: str, sheet: str, own_sheet: bool, at: int, n: int, tail: bool) -> str:
    """Pas de verwijzingen naar `sheet` in een formule aan; tekst tussen aanhalingstekens blijft ongemoeid."""
    parts = formula.split('"')
    for i in range(0, len(parts), 2):
        seg = parts[i]

        def qual(m: re.Match) -> str:
            if _sheet_name(m.group("sheet")) != sheet:
                return m.group(0)
            return f"{m.group('sheet')}!{shift_ref(m.group('ref'), at, n, tail)}"

        seg = QUAL_RE.sub(qual, seg)
        if own_sheet:
            # alleen onbenoemde verwijzingen buiten de al behandelde 'Blad!'-verwijzingen
            stukken = re.split(r"((?:'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!" + REF_RE + ")", seg)
            for j in range(0, len(stukken), 2):
                stukken[j] = UNQUAL_RE.sub(lambda m: shift_ref(m.group("ref"), at, n, tail), stukken[j])
            seg = "".join(stukken)
        parts[i] = seg
    return '"'.join(parts)


# ------------------------------------------------------------------ werkboek
def _parse_rels(data: bytes) -> dict[str, tuple[str, str]]:
    rels = etree.fromstring(data)
    return {r.get("Id"): (r.get("Type"), r.get("Target")) for r in rels.findall(f"{{{PNS}}}Relationship")}


def _resolve(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    parts = (base_dir + "/" + target).split("/")
    out: list[str] = []
    for p in parts:
        if p == "..":
            if out:
                out.pop()
        elif p and p != ".":
            out.append(p)
    return "/".join(out)


class Werkboek:
    def __init__(self, path: Path):
        with zipfile.ZipFile(path) as z:
            self.infos = list(z.infolist())
            self.origineel = {i.filename: z.read(i.filename) for i in self.infos}
        self.bomen: dict[str, Any] = {}
        global _SST
        _SST = []
        if "xl/sharedStrings.xml" in self.origineel:
            sst = etree.fromstring(self.origineel["xl/sharedStrings.xml"])
            _SST = ["".join(t.text or "" for t in si.iter(X + "t")) for si in sst.findall(X + "si")]
        wb = etree.fromstring(self.origineel["xl/workbook.xml"])
        rels = _parse_rels(self.origineel["xl/_rels/workbook.xml.rels"])
        self.paden: dict[str, str] = {}
        self.volgorde: list[str] = []
        for s in wb.iter(X + "sheet"):
            target = rels[s.get(f"{{{RNS}}}id")][1]
            self.paden[s.get("name")] = _resolve("xl", target)
            self.volgorde.append(s.get("name"))
        self.tabellen: dict[str, list[str]] = {}
        for naam, pad in self.paden.items():
            rel_pad = pad.rsplit("/", 1)[0] + "/_rels/" + pad.rsplit("/", 1)[1] + ".rels"
            if rel_pad not in self.origineel:
                continue
            for typ, target in _parse_rels(self.origineel[rel_pad]).values():
                if typ.endswith("/table"):
                    self.tabellen.setdefault(naam, []).append(_resolve(pad.rsplit("/", 1)[0], target))

    def boom(self, part: str):
        if part not in self.bomen:
            self.bomen[part] = etree.fromstring(self.origineel[part])
        return self.bomen[part]

    def blad(self, naam: str):
        if naam not in self.paden:
            raise ExcelFout(f"blad '{naam}' ontbreekt in het werkboek")
        return self.boom(self.paden[naam])

    def tabel(self, naam: str):
        tps = self.tabellen.get(naam, [])
        return self.boom(tps[0]) if tps else None

    def inhoud(self) -> dict[str, bytes]:
        uit = dict(self.origineel)
        for part, root in self.bomen.items():
            nieuw = etree.tostring(root, xml_declaration=True, encoding="utf-8")
            canoniek = etree.tostring(etree.fromstring(self.origineel[part]), xml_declaration=True, encoding="utf-8")
            if nieuw != canoniek:
                uit[part] = nieuw
        return uit

    def gewijzigd(self) -> list[str]:
        uit = self.inhoud()
        return [n for n in uit if uit[n] != self.origineel[n]]

    def schrijf(self, out: Path) -> None:
        inhoud = self.inhoud()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in self.infos:
                zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = info.external_attr
                zout.writestr(zi, inhoud[info.filename])
        out.write_bytes(buf.getvalue())


# ------------------------------------------------------------------ rijen invoegen
def data_rows(root) -> list:
    return root.find(X + "sheetData").findall(X + "row")


def last_row(root) -> int:
    rows = data_rows(root)
    return int(rows[-1].get("r")) if rows else 0


def row_id(row, col: int = 1) -> str:
    return cell_text(find_cell(row, col)).strip()


def _shift_sqref(sqref: str, at: int, n: int, tail: bool) -> str:
    return " ".join(shift_ref(part, at, n, tail) for part in sqref.split())


def insert_rows(wb: Werkboek, sheet: str, at: int, n: int) -> None:
    """Schuif rijen >= at op en pas alle verwijzingen aan; daarna is rij at..at+n-1 vrij."""
    root = wb.blad(sheet)
    laatste = last_row(root)
    tail = at == laatste + 1
    for row in reversed(data_rows(root)):
        r = int(row.get("r"))
        if r < at:
            break
        row.set("r", str(r + n))
        for c in row.findall(X + "c"):
            c.set("r", f"{col_letter(col_index(c.get('r')))}{r + n}")
    dim = root.find(X + "dimension")
    if dim is not None:
        dim.set("ref", shift_ref(dim.get("ref"), at, n, tail))
    for el in root.iter(X + "mergeCell"):
        el.set("ref", shift_ref(el.get("ref"), at, n, tail))
    for tag in ("conditionalFormatting", "dataValidation"):
        for el in root.iter(X + tag):
            el.set("sqref", _shift_sqref(el.get("sqref"), at, n, tail))
    af = root.find(X + "autoFilter")
    if af is not None:
        af.set("ref", shift_ref(af.get("ref"), at, n, tail))
    for tp in wb.tabellen.get(sheet, []):
        t = wb.boom(tp)
        t.set("ref", shift_ref(t.get("ref"), at, n, tail))
        taf = t.find(X + "autoFilter")
        if taf is not None:
            taf.set("ref", t.get("ref"))
    for naam in wb.volgorde:
        blad = wb.blad(naam)
        for f in blad.iter(X + "f"):
            if f.text:
                nieuw = shift_formula(f.text, sheet, naam == sheet, at, n, tail)
                if nieuw != f.text:
                    f.text = nieuw


def _new_row(root, r: int, template) -> Any:
    row = etree.Element(X + "row")
    row.set("r", str(r))
    if template is not None:
        for k, v in template.attrib.items():
            if k != "r" and k != "spans":
                row.set(k, v)
    data = root.find(X + "sheetData")
    idx = 0
    for i, bestaand in enumerate(data.findall(X + "row")):
        if int(bestaand.get("r")) < r:
            idx = i + 1
    data.insert(idx, row)
    return row


def _style_of(template, col: int) -> str | None:
    if template is None:
        return None
    c = find_cell(template, col)
    return c.get("s") if c is not None else None


def _id_key(rid: str) -> tuple[str, int, str]:
    m = re.match(r"^(.*?)(\d+)$", rid)
    if not m:
        return (rid, -1, rid)
    return (m.group(1), int(m.group(2)), rid)


def _group(rid: str) -> str:
    return rid.rsplit("-", 1)[0] + "-" if "-" in rid else re.sub(r"\d+$", "", rid)


def insert_position(root, rid: str, id_col: int = 1) -> int:
    """Rijnummer voor een nieuw ID: na het grootste kleinere ID van dezelfde reeks; anders achteraan."""
    groep = _group(rid)
    kandidaten = [(row, row_id(row, id_col)) for row in data_rows(root)[1:]]
    zelfde = [(row, i) for row, i in kandidaten if i and _group(i) == groep]
    if not zelfde:
        return last_row(root) + 1
    kleiner = [row for row, i in zelfde if _id_key(i) < _id_key(rid)]
    if kleiner:
        return int(kleiner[-1].get("r")) + 1
    return int(zelfde[0][0].get("r"))


def _rows_by_id(root, id_col: int = 1) -> dict[str, Any]:
    return {row_id(row, id_col): row for row in data_rows(root)[1:] if row_id(row, id_col)}


def _check_status(status: str, sheet: str, wat: str) -> None:
    if status in FORBIDDEN:
        raise ExcelFout(
            f"{wat}: status '{status}' geweigerd; 'Gereed'/'Geslaagd' alleen na echte acceptatie, handmatig"
        )
    if status not in ALLOWED[sheet]:
        raise ExcelFout(f"{wat}: onbekende status '{status}' (toegestaan: {', '.join(ALLOWED[sheet])})")


def add_werkpakketten(wb: Werkboek, rijen: list[dict], status: str, stats: dict) -> None:
    _check_status(status, "Werkpakketten", "startstatus werkpakketten")
    for r in rijen:
        if list(r) != TASK_FIELDS:
            raise ExcelFout(f"{r.get('ID', '?')}: geen tasks.json-formaat (velden of volgorde wijken af)")
        if not re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9A-Z-]+", r["ID"]):
            raise ExcelFout(f"{r['ID']}: ongeldig ID")
    root = wb.blad("Werkpakketten")
    for r in rijen:
        bestaand = _rows_by_id(root).get(r["ID"])
        if bestaand is not None:
            veranderd = False
            for veld, col in TASK_COLUMNS.items():
                veranderd |= set_cell(bestaand, col, r[veld])
            if veranderd:
                stats["werkpakketten_vervangen"] = stats.get("werkpakketten_vervangen", 0) + 1
            continue
        at = insert_position(root, r["ID"])
        rows = {int(x.get("r")): x for x in data_rows(root)}
        template = rows.get(at - 1) if at - 1 >= 2 else rows.get(2)
        insert_rows(wb, "Werkpakketten", at, 1)
        row = _new_row(root, at, template)
        waarden = {col: r[veld] for veld, col in TASK_COLUMNS.items()}
        waarden[LAYOUT["Werkpakketten"]["status"]] = status
        waarden[LAYOUT["Werkpakketten"]["bewijs"]] = ""
        for col in range(1, max(waarden) + 1):
            set_cell(row, col, waarden.get(col, ""), _style_of(template, col))
        stats["werkpakketten_toegevoegd"] = stats.get("werkpakketten_toegevoegd", 0) + 1


def add_testen(
    wb: Werkboek,
    testen: list[list[str]],
    meta: dict,
    document: str | None,
    datum: str,
    warnings: list[str],
    stats: dict,
) -> None:
    plan = []
    for t in testen:
        if not (isinstance(t, list) and len(t) == 4 and all(isinstance(x, str) and x.strip() for x in t)):
            raise ExcelFout(f"{t[0] if t else t}: geen e2e_cases-formaat ([ID, scenario, uitvoeren, verwacht])")
        m = meta.get(t[0], {})
        prio = m.get("prioriteit") or "P1"
        if not m.get("prioriteit"):
            warnings.append(f"{t[0]}: geen prioriteit in --testmeta; P1 gebruikt")
        if prio not in PRIORITEITEN:
            raise ExcelFout(f"{t[0]}: onbekende prioriteit '{prio}'")
        start = m.get("startstatus") or "Niet gestart"
        _check_status(start, "Testmatrix", f"{t[0]} startstatus")
        doc = m.get("document") or document
        if not doc:
            raise ExcelFout(f"{t[0]}: geen document (gebruik --testdocument)")
        plan.append((t, prio, start, doc))
    root = wb.blad("Testmatrix")
    for t, prio, start, doc in plan:
        inhoud = {
            TEST_COLUMNS["Scenario"]: t[1],
            TEST_COLUMNS["Uitvoeren"]: t[2],
            TEST_COLUMNS["Verwacht"]: t[3],
            TEST_COLUMNS["Prioriteit"]: prio,
            TEST_COLUMNS["Document"]: doc,
        }
        bestaand = _rows_by_id(root).get(t[0])
        if bestaand is not None:
            veranderd = False
            for col, v in inhoud.items():
                veranderd |= set_cell(bestaand, col, v)
            if veranderd:
                stats["testen_vervangen"] = stats.get("testen_vervangen", 0) + 1
            continue
        at = insert_position(root, t[0])
        rows = {int(x.get("r")): x for x in data_rows(root)}
        template = rows.get(at - 1) if at - 1 >= 2 else rows.get(2)
        insert_rows(wb, "Testmatrix", at, 1)
        row = _new_row(root, at, template)
        lay = LAYOUT["Testmatrix"]
        waarden = dict(inhoud)
        waarden[TEST_COLUMNS["ID"]] = t[0]
        waarden[lay["status"]] = start
        waarden[lay["bewijs"]] = ""
        if start == "Geblokkeerd":
            labels = list(dict.fromkeys(NIET_GEVALIDEERD_RE.findall(" ".join(t))))
            waarden[lay["extra_start"]] = "; ".join(labels) or "NIET GEVALIDEERD (echte NAS)"
            waarden[lay["extra_start"] + 1] = BLOKKADE_START
            waarden[lay["extra_start"] + 2] = datum
        for col in range(1, max(waarden) + 1):
            set_cell(row, col, waarden.get(col, ""), _style_of(template, col))
        stats["testen_toegevoegd"] = stats.get("testen_toegevoegd", 0) + 1


def add_fasen(wb: Werkboek, fasen: list[dict], datum: str, stats: dict) -> None:
    for f in fasen:
        for k in ("id", "beschrijving", "go_nogo"):
            if not isinstance(f.get(k), str) or not f[k].strip():
                raise ExcelFout(f"faserij {f.get('id', '?')}: veld '{k}' ontbreekt")
        _check_status(f.get("status") or "Niet gestart", "Fasen", f"fase {f['id']}")
    root = wb.blad(FASEN_BLAD)
    lay = LAYOUT["Fasen"]
    for f in fasen:
        rows = _rows_by_id(root)
        bestaand = rows.get(f["id"])
        if bestaand is not None:
            veranderd = False
            for k, col in FASE_COLUMNS.items():
                if k != "id":
                    veranderd |= set_cell(bestaand, col, f[k])
            if veranderd:
                stats["fasen_vervangen"] = stats.get("fasen_vervangen", 0) + 1
            continue
        na = rows.get(f.get("na", ""))
        at = int(na.get("r")) + 1 if na is not None else last_row(root) + 1
        template = na if na is not None else data_rows(root)[-1]
        insert_rows(wb, FASEN_BLAD, at, 1)
        row = _new_row(root, at, template)
        waarden = {FASE_COLUMNS[k]: f[k] for k in FASE_COLUMNS}
        waarden[lay["status"]] = f.get("status") or "Niet gestart"
        waarden[lay["bewijs"]] = f.get("bewijs", "")
        waarden[lay["extra_start"]] = f.get("validatie", "")
        waarden[lay["extra_start"] + 1] = f.get("blokkade", "")
        waarden[lay["extra_start"] + 2] = datum
        for col in range(1, max(waarden) + 1):
            set_cell(row, col, waarden.get(col, ""), _style_of(template, col))
        stats["fasen_toegevoegd"] = stats.get("fasen_toegevoegd", 0) + 1
    update_fasenblok(wb)


def update_fasenblok(wb: Werkboek) -> None:
    """Een blok rijen met =Fasen!A<n> (zoals op het Dashboard) toont alle faserijen in volgorde; groeit zo nodig mee."""
    fasen = [int(r.get("r")) for r in data_rows(wb.blad(FASEN_BLAD))[1:] if row_id(r)]
    rx = re.compile(r"^(?:'?" + re.escape(FASEN_BLAD) + r"'?)!(\$?)([A-Z]{1,3})(\$?)(\d+)$")
    for naam in wb.volgorde:
        if naam == FASEN_BLAD:
            continue
        root = wb.blad(naam)
        blok = []
        for row in data_rows(root):
            c = find_cell(row, 1)
            f = c.find(X + "f") if c is not None else None
            if f is not None and f.text and rx.match(f.text) and rx.match(f.text).group(2) == "A":
                blok.append(row)
        if not blok:
            continue
        nummers = [int(r.get("r")) for r in blok]
        if nummers != list(range(nummers[0], nummers[0] + len(nummers))):
            continue
        tekort = len(fasen) - len(blok)
        bezet = {int(r.get("r")) for r in data_rows(root)}
        if tekort > 0 and not any(nummers[-1] + i in bezet for i in range(1, tekort + 1)):
            einde = nummers[-1]
            for i in range(1, tekort + 1):
                kopie = copy.deepcopy(blok[-1])
                kopie.set("r", str(einde + i))
                for c in kopie.findall(X + "c"):
                    c.set("r", f"{col_letter(col_index(c.get('r')))}{einde + i}")
                    v = c.find(X + "v")
                    if v is not None:
                        c.remove(v)
                blok[-1].addnext(kopie)
                blok.append(kopie)
            for m in root.iter(X + "mergeCell"):
                a, b = m.get("ref").split(":")
                if row_index(b) == einde and nummers[0] <= row_index(a) <= einde:
                    m.set("ref", f"{a}:{re.sub(r'[0-9]+$', '', b)}{einde + tekort}")
        for row, fr in zip(blok, fasen, strict=False):
            for c in row.findall(X + "c"):
                f = c.find(X + "f")
                if f is not None and f.text:
                    m = rx.match(f.text)
                    if m:
                        nieuw = f"{FASEN_BLAD}!{m.group(1)}{m.group(2)}{m.group(3)}{fr}"
                        if f.text != nieuw:
                            f.text = nieuw


# ------------------------------------------------------------------ formuleresultaten
class NietOndersteund(Exception):
    pass


class Rekenaar:
    """Berekent eenvoudige formules opnieuw zodat de opgeslagen resultaten kloppen (ook zonder herberekening)."""

    TOKEN = re.compile(
        r'\s*(?:(?P<str>"(?:[^"]|"")*")|(?P<num>\d+(?:\.\d+)?)|'
        r"(?P<ref>(?:(?:'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_.]*)!)?" + REF_RE + r")(?![A-Za-z0-9_(])|"
        r"(?P<fn>[A-Z][A-Z0-9.]*)\(|(?P<op>[-+*/(),&]))"
    )

    def __init__(self, wb: Werkboek):
        self.wb = wb
        self.cellen: dict[str, dict[str, Any]] = {}
        for naam in wb.volgorde:
            m = {}
            for c in wb.blad(naam).iter(X + "c"):
                m[c.get("r")] = c
            self.cellen[naam] = m
        self.memo: dict[tuple[str, str], Any] = {}

    def waarde(self, blad: str, ref: str) -> Any:
        ref = ref.replace("$", "")
        sleutel = (blad, ref)
        if sleutel in self.memo:
            return self.memo[sleutel]
        c = self.cellen.get(blad, {}).get(ref)
        if c is None:
            return None
        f = c.find(X + "f")
        if f is not None and f.text:
            w = self.evalueer(f.text, blad)
            self.memo[sleutel] = w
            return w
        t = c.get("t")
        tekst = cell_text(c)
        if t in ("str", "s", "inlineStr", "e"):
            return tekst if tekst != "" else None
        if t == "b":
            return tekst == "1"
        if tekst == "":
            return None
        try:
            return float(tekst)
        except ValueError:
            return tekst

    def bereik(self, blad: str, ref: str) -> list:
        ref = ref.replace("$", "")
        if ":" not in ref:
            return [self.waarde(blad, ref)]
        a, b = ref.split(":")
        c1, c2 = col_index(a), col_index(b)
        r1, r2 = row_index(a), row_index(b)
        return [self.waarde(blad, f"{col_letter(c)}{r}") for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]

    def evalueer(self, formule: str, blad: str) -> Any:
        tokens = []
        pos = 0
        while pos < len(formule):
            m = self.TOKEN.match(formule, pos)
            if not m or m.end() == pos:
                if formule[pos:].strip() == "":
                    break
                raise NietOndersteund(formule)
            tokens.append(m)
            pos = m.end()
        bewaard = (getattr(self, "_t", None), getattr(self, "_i", 0), getattr(self, "_blad", None))
        self._t, self._i, self._blad = tokens, 0, blad
        try:
            w = self._expr()
            if self._i != len(self._t):
                raise NietOndersteund(formule)
            return w
        finally:
            self._t, self._i, self._blad = bewaard

    def _peek(self):
        return self._t[self._i] if self._i < len(self._t) else None

    def _op(self, ch: str) -> bool:
        p = self._peek()
        if p is not None and p.group("op") == ch:
            self._i += 1
            return True
        return False

    def _expr(self):
        w = self._term()
        while True:
            if self._op("+"):
                w = _num(w) + _num(self._term())
            elif self._op("-"):
                w = _num(w) - _num(self._term())
            else:
                return w

    def _term(self):
        w = self._factor()
        while True:
            if self._op("*"):
                w = _num(w) * _num(self._factor())
            elif self._op("/"):
                d = _num(self._factor())
                if d == 0:
                    raise ZeroDivisionError
                w = _num(w) / d
            else:
                return w

    def _ref_arg(self):
        p = self._peek()
        if p is None or not p.group("ref"):
            raise NietOndersteund("bereik verwacht")
        self._i += 1
        tekst = p.group("ref")
        if "!" in tekst:
            blad, ref = tekst.rsplit("!", 1)
            return _sheet_name(blad), ref
        return self._blad, tekst

    def _args(self) -> list:
        args = []
        if self._op(")"):
            return args
        while True:
            args.append(self._i)
            self._skip_arg()
            if self._op(")"):
                return args
            if not self._op(","):
                raise NietOndersteund("argumenten")

    def _skip_arg(self) -> None:
        diep = 0
        while self._i < len(self._t):
            p = self._t[self._i]
            if p.group("fn") or p.group("op") == "(":
                diep += 1
            elif p.group("op") == ")":
                if diep == 0:
                    return
                diep -= 1
            elif p.group("op") == "," and diep == 0:
                return
            self._i += 1

    def _factor(self):
        p = self._peek()
        if p is None:
            raise NietOndersteund("einde")
        if self._op("-"):
            return -_num(self._factor())
        if self._op("("):
            w = self._expr()
            if not self._op(")"):
                raise NietOndersteund("haakje")
            return w
        self._i += 1
        if p.group("str") is not None:
            return p.group("str")[1:-1].replace('""', '"')
        if p.group("num") is not None:
            return float(p.group("num"))
        if p.group("ref") is not None:
            tekst = p.group("ref")
            blad, ref = (
                (_sheet_name(tekst.rsplit("!", 1)[0]), tekst.rsplit("!", 1)[1]) if "!" in tekst else (self._blad, tekst)
            )
            if ":" in ref:
                raise NietOndersteund("bereik buiten een functie")
            return self.waarde(blad, ref)
        fn = p.group("fn")
        starts = self._args()
        einde = self._i
        return self._functie(fn, starts, einde)

    def _eval_at(self, start: int):
        bewaar = self._i
        self._i = start
        try:
            return self._expr()
        finally:
            self._i = bewaar

    def _range_at(self, start: int) -> list:
        bewaar = self._i
        self._i = start
        try:
            blad, ref = self._ref_arg()
            return self.bereik(blad, ref)
        finally:
            self._i = bewaar

    def _functie(self, fn: str, starts: list[int], einde: int):
        if fn == "COUNTA":
            return float(sum(1 for s in starts for v in self._range_at(s) if v is not None and v != ""))
        if fn in ("COUNTIF", "COUNTIFS"):
            if len(starts) % 2 or not starts:
                raise NietOndersteund(fn)
            paren = [(self._range_at(starts[i]), self._eval_at(starts[i + 1])) for i in range(0, len(starts), 2)]
            for _, crit in paren:
                if isinstance(crit, str) and crit[:1] in "<>=":
                    raise NietOndersteund("criterium met operator")
            lengte = {len(r) for r, _ in paren}
            if len(lengte) != 1:
                raise NietOndersteund("bereiken van ongelijke grootte")
            n = 0
            for i in range(lengte.pop()):
                if all(_gelijk(r[i], crit) for r, crit in paren):
                    n += 1
            return float(n)
        if fn == "IFERROR":
            if len(starts) != 2:
                raise NietOndersteund(fn)
            try:
                return self._eval_at(starts[0])
            except (ZeroDivisionError, TypeError, ValueError):
                return self._eval_at(starts[1])
        if fn == "SUM":
            totaal = 0.0
            for s in starts:
                for v in self._range_at(s):
                    if isinstance(v, float):
                        totaal += v
            return totaal
        raise NietOndersteund(fn)


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, float):
        return v
    raise ValueError(f"geen getal: {v!r}")


def _gelijk(v: Any, crit: Any) -> bool:
    if crit is None:
        return v is None or v == ""
    if isinstance(crit, str):
        return isinstance(v, str) and v.casefold() == crit.casefold()
    return isinstance(v, float) and v == crit


def _format(v: Any) -> tuple[str, str]:
    if isinstance(v, bool):
        return "b", "1" if v else "0"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return "n", str(int(v))
        return "n", repr(v)
    if v is None:
        return "str", ""
    return "str", str(v)


def herbereken(wb: Werkboek, warnings: list[str]) -> int:
    """Zet de opgeslagen resultaten van alle formules opnieuw; onbekende formules blijven staan (met waarschuwing)."""
    rek = Rekenaar(wb)
    aantal = 0
    for naam in wb.volgorde:
        for c in wb.blad(naam).iter(X + "c"):
            f = c.find(X + "f")
            if f is None or not f.text:
                continue
            try:
                w = rek.waarde(naam, c.get("r"))
            except (NietOndersteund, ValueError, TypeError, ZeroDivisionError, RecursionError) as exc:
                warnings.append(f"{naam}!{c.get('r')}: formule niet herberekend ({exc!r}); opgeslagen resultaat blijft")
                continue
            t, tekst = _format(w)
            v = c.find(X + "v")
            huidig = (c.get("t") or "n", v.text if v is not None and v.text is not None else "")
            if huidig == (t, tekst):
                continue
            c.set("t", t)
            if v is None:
                v = etree.SubElement(c, X + "v")
            if tekst:
                v.text = tekst
            else:
                c.remove(v)
            aantal += 1
    return aantal


# ------------------------------------------------------------------ bewijs samenvoegen (ongewijzigd gedrag)
def merge(entries: list[dict], sheet: str, warnings: list[str]) -> dict:
    status = None
    validaties: list[str] = []
    bewijzen: list[str] = []
    blokkades: list[str] = []
    data = ""
    waarde = None
    for e in entries:
        s = (e.get("status") or "").strip()
        if s in FORBIDDEN:
            warnings.append(
                f"{e.get('id')}: status '{s}' door hulpmiddel teruggezet naar 'Bezig' "
                "(alleen na echte acceptatie handmatig)"
            )
            s = "Bezig"
        if s and s not in ALLOWED[sheet]:
            warnings.append(f"{e.get('id')}: onbekende status '{s}' genegeerd")
            s = ""
        if s and (status is None or PRECEDENCE.get(s, 0) > PRECEDENCE.get(status, 0)):
            status = s
        repo = e.get("repo", "")
        for key, bucket in (
            ("validatie", validaties),
            ("bewijs", bewijzen),
            ("blokkade", blokkades),
            ("opmerking", blokkades),
        ):
            val = (e.get(key) or "").strip()
            if val:
                bucket.append(f"[{repo}] {val}" if repo and len(entries) > 1 else val)
        if e.get("waarde"):
            waarde = str(e["waarde"])
        data = max(data, e.get("bijgewerkt", ""))
    return {
        "status": status,
        "validatie": " | ".join(dict.fromkeys(validaties)),
        "bewijs": " | ".join(dict.fromkeys(bewijzen)),
        "blokkade": " | ".join(dict.fromkeys(blokkades)),
        "bijgewerkt": data,
        "waarde": waarde,
    }


def route(rid: str) -> str:
    if rid.startswith("EX") or rid.startswith("JLT-"):
        return "Testmatrix"
    if re.fullmatch(r"D\d\d", rid):
        return "Besluiten"
    if re.fullmatch(r"P\d(?:-\d+)?", rid):
        return "Fasen"
    return "Werkpakketten"


def update_sheet(wb: Werkboek, sheet: str, evidence: dict[str, list[dict]], warnings: list[str], stats: dict) -> None:
    root = wb.blad(sheet)
    lay = LAYOUT[sheet]
    rows = data_rows(root)
    header = rows[0]
    header_style = header.find(X + "c").get("s")
    for i, h in enumerate(EXTRA_HEADERS):
        set_cell(header, lay["extra_start"] + i, h, header_style)
    cols = root.find(X + "cols")
    if cols is not None:
        existing = {int(c.get("min")) for c in cols.findall(X + "col")}
        for i, width in enumerate((34, 40, 12)):
            n = lay["extra_start"] + i
            if n not in existing:
                c = etree.SubElement(cols, X + "col")
                c.set("min", str(n))
                c.set("max", str(n))
                c.set("width", str(width))
                c.set("customWidth", "1")
    for row in rows[1:]:
        rid = row_id(row, lay["id"])
        if rid not in evidence:
            continue
        m = merge(evidence[rid], sheet, warnings)
        if m["status"]:
            set_cell(row, lay["status"], m["status"])
        if m["bewijs"]:
            set_cell(row, lay["bewijs"], m["bewijs"][:32000])
        if sheet == "Besluiten" and m["waarde"]:
            set_cell(row, lay["waarde"], m["waarde"][:32000])
        set_cell(row, lay["extra_start"], m["validatie"][:32000])
        set_cell(row, lay["extra_start"] + 1, m["blokkade"][:32000])
        set_cell(row, lay["extra_start"] + 2, m["bijgewerkt"])
        stats[sheet] = stats.get(sheet, 0) + 1
        evidence.pop(rid)
    for tp in wb.tabellen.get(sheet, []):
        update_table(wb.boom(tp), lay["extra_start"] + len(EXTRA_HEADERS) - 1)


def update_table(root, new_last_col: int) -> None:
    ref = root.get("ref")
    start, end = ref.split(":")
    end_row = re.sub(r"[A-Z$]+", "", end)
    if col_index(end) < new_last_col:
        root.set("ref", f"{start}:{col_letter(new_last_col)}{end_row}")
    af = root.find(X + "autoFilter")
    if af is not None:
        af.set("ref", root.get("ref"))
    tcs = root.find(X + "tableColumns")
    names = [tc.get("name") for tc in tcs.findall(X + "tableColumn")]
    next_id = max(int(tc.get("id")) for tc in tcs.findall(X + "tableColumn")) + 1
    start_col = col_index(start)
    needed = new_last_col - start_col + 1
    while len(names) < needed:
        abs_col = start_col + len(names)
        name = None
        for j, h in enumerate(EXTRA_HEADERS):
            if abs_col == new_last_col - len(EXTRA_HEADERS) + 1 + j:
                name = h
        name = name or f"Kolom{abs_col}"
        tc = etree.SubElement(tcs, X + "tableColumn")
        tc.set("id", str(next_id))
        tc.set("name", name)
        next_id += 1
        names.append(name)
    if tcs.get("count") != str(len(names)):
        tcs.set("count", str(len(names)))


def update_simple_rows(root, key_col: int, updates: dict[str, dict[int, str]]) -> None:
    for row in data_rows(root):
        key = row_id(row, key_col)
        if key in updates:
            for col, val in updates.pop(key).items():
                set_cell(row, col, val)


def append_rows(root, rows_to_add: list[list[str]]) -> None:
    rows = data_rows(root)
    bestaand = {row_id(row): row for row in rows}
    n = int(rows[-1].get("r")) if rows else 0
    data = root.find(X + "sheetData")
    for values in rows_to_add:
        if values[0] in bestaand:
            for i, v in enumerate(values):
                set_cell(bestaand[values[0]], i + 1, v)
            continue
        n += 1
        row = etree.SubElement(data, X + "row")
        row.set("r", str(n))
        for i, v in enumerate(values):
            set_cell(row, i + 1, v)
        bestaand[values[0]] = row
    dim = root.find(X + "dimension")
    if dim is not None and rows_to_add:
        dim.set("ref", f"A1:{col_letter(max(len(r) for r in rows_to_add))}{n}")


# ------------------------------------------------------------------ hoofdprogramma
def _lees_json(pad: str) -> Any:
    try:
        return json.loads(Path(pad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExcelFout(f"{pad}: niet leesbaar ({exc})") from exc


def _testmeta(pad: str | None) -> dict:
    if not pad:
        return {}
    d = _lees_json(pad)
    return d.get("per_test", d) if isinstance(d, dict) else {}


def run(args: argparse.Namespace) -> dict:
    warnings: list[str] = []
    stats: dict[str, int] = {}
    datum = args.date or datetime.date.today().isoformat()
    src = Path(args.xlsx)
    out = Path(args.out) if args.out else src
    wb = Werkboek(src)

    # 1. rijen toevoegen of vervangen (alles of niets: fouten worden vóór het schrijven gemeld)
    rijen: list[dict] = []
    for p in args.werkpakketten:
        d = _lees_json(p)
        if not isinstance(d, list):
            raise ExcelFout(f"{p}: verwacht een lijst in tasks.json-formaat")
        rijen += d
    if rijen:
        add_werkpakketten(wb, rijen, args.status_werkpakketten, stats)
    testen: list[list[str]] = []
    for p in args.testen:
        d = _lees_json(p)
        if not isinstance(d, list):
            raise ExcelFout(f"{p}: verwacht een lijst in e2e_cases-formaat")
        testen += d
    if testen:
        add_testen(wb, testen, _testmeta(args.testmeta), args.testdocument, datum, warnings, stats)
    if args.fasen:
        fasen = _lees_json(args.fasen)
        if isinstance(fasen, dict):
            fasen = fasen.get("fasen", [])
        add_fasen(wb, fasen, datum, stats)

    # 2. bewijs samenvoegen
    by_sheet: dict[str, dict[str, list[dict]]] = {s: {} for s in LAYOUT}
    for p in args.evidence:
        try:
            items = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"{p}: niet leesbaar ({exc})")
            continue
        if isinstance(items, dict):
            items = items.get("items", [])
        for e in items:
            rid = str(e.get("id", "")).strip()
            if not rid:
                continue
            e.setdefault("repo", Path(p).parts[-4] if len(Path(p).parts) >= 4 else "")
            by_sheet[route(rid)].setdefault(rid, []).append(e)
    program: dict = {}
    if args.program:
        program = _lees_json(args.program)
        for e in program.get("fasen", []):
            by_sheet["Fasen"].setdefault(e["id"], []).append(e)
    if args.evidence or args.program:
        for sheet in LAYOUT:
            update_sheet(wb, sheet, by_sheet[sheet], warnings, stats)
        for sheet, leftovers in by_sheet.items():
            for rid in leftovers:
                warnings.append(f"{rid}: geen rij gevonden in blad {sheet}")
        if program.get("releases"):
            colmap = {"gecontroleerde_stand": 2, "bewijsstatus": 3, "peildatum": 4, "commit": 5, "bron": 6, "actie": 7}
            upd = {r["project"]: {colmap[k]: str(v) for k, v in r.items() if k in colmap} for r in program["releases"]}
            update_simple_rows(wb.blad("Releases"), 1, upd)
            if upd:
                append_rows(wb.blad("Releases"), [[k] + [v.get(i, "") for i in range(2, 8)] for k, v in upd.items()])
        if program.get("instructies"):
            append_rows(wb.blad("Instructies"), [[r["onderwerp"], r["instructie"]] for r in program["instructies"]])

    # 3. formuleresultaten bijwerken en schrijven
    stats["formules_herberekend"] = herbereken(wb, warnings)
    gewijzigd = wb.gewijzigd()
    if gewijzigd or out != src:
        if out == src and gewijzigd:
            shutil.copy2(src, src.with_suffix(".xlsx.bak"))
        wb.schrijf(out)
    return {"bijgewerkt_per_blad": stats, "gewijzigde_onderdelen": gewijzigd, "waarschuwingen": warnings}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--werkpakketten", nargs="*", default=[], help="JSON in tasks.json-formaat (toevoegen/vervangen)")
    ap.add_argument("--status-werkpakketten", default="Niet gestart", help="startstatus nieuwe werkpakketten")
    ap.add_argument("--testen", nargs="*", default=[], help="JSON in e2e_cases-formaat (toevoegen/vervangen)")
    ap.add_argument("--testmeta", help="EXCEL_TAKEN_PER_REPO.json (per_test.<ID>.prioriteit/startstatus)")
    ap.add_argument("--testdocument", help="kolom 'Document in ZIP' voor nieuwe testrijen")
    ap.add_argument("--fasen", help="JSON-lijst met faserijen {id, beschrijving, go_nogo, status, na}")
    ap.add_argument("--evidence", nargs="*", default=[])
    ap.add_argument("--program", help="EVIDENCE_PROGRAMMA.json met Fasen/Releases/Instructies")
    ap.add_argument("--date", help="datum voor de kolom Bijgewerkt van nieuwe rijen (standaard vandaag)")
    ap.add_argument("--out", help="uitvoerpad (standaard: in plaats, met .xlsx.bak)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        resultaat = run(args)
    except ExcelFout as exc:
        print(f"FOUT: {exc} — er is niets geschreven", file=sys.stderr)
        return 2
    print(json.dumps(resultaat, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
