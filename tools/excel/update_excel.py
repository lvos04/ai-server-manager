#!/usr/bin/env python3
"""Werk de afvinklijst-Excel bij vanuit EVIDENCE.json-bestanden van alle repos.

Bewerkt de werkbladen rechtstreeks op XML-niveau, zodat opmaak, tabellen,
dropdowns en voorwaardelijke opmaak (ook de databar op 'Appoverzicht')
behouden blijven. Alleen de bladen Werkpakketten, Testmatrix, Besluiten,
Fasen, Releases en Instructies worden aangeraakt.

Regels (PLATFORM_CONTRACTEN.md §11, keuze van de gebruiker):
- 'Gereed' en 'Geslaagd' worden NOOIT door dit hulpmiddel gezet; zulke
  invoer wordt teruggezet naar 'Bezig' met een waarschuwing.
- Meerdere bewijsregels voor dezelfde ID worden samengevoegd; de
  voorzichtigste status wint.

Gebruik:
  python3 update_excel.py --xlsx <pad.xlsx> --evidence <EVIDENCE.json> [...]
         [--program <EVIDENCE_PROGRAMMA.json>] [--date JJJJ-MM-DD]
Vereist: lxml.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/package/2006/relationships"
X = "{%s}" % NS

ALLOWED = {
    "Werkpakketten": ["Niet gestart", "Bezig", "Gereed", "Geblokkeerd", "N.v.t."],
    "Fasen": ["Niet gestart", "Bezig", "Gereed", "Geblokkeerd", "N.v.t."],
    "Testmatrix": ["Niet gestart", "Bezig", "Geslaagd", "Mislukt", "Geblokkeerd", "N.v.t."],
    "Besluiten": ["Open", "Ingevuld", "Getest", "Geblokkeerd", "N.v.t."],
}
FORBIDDEN = {"Gereed", "Geslaagd"}
# Hogere waarde = voorzichtiger (wint bij samenvoegen).
PRECEDENCE = {
    "N.v.t.": 0, "Niet gestart": 1, "Open": 1, "Ingevuld": 2, "Bezig": 2,
    "Getest": 3, "Geblokkeerd": 4, "Mislukt": 5,
}
# Kolommen (1-based) per blad: id, status, bewijs, en nieuwe kolommen.
LAYOUT = {
    "Werkpakketten": dict(id=1, status=10, bewijs=11, extra_start=15),
    "Testmatrix": dict(id=1, status=6, bewijs=7, extra_start=9),
    "Besluiten": dict(id=1, status=5, bewijs=7, extra_start=9, waarde=6),
    "Fasen": dict(id=1, status=4, bewijs=5, extra_start=6),
}
EXTRA_HEADERS = ["Validatie", "Blokkade / opmerking", "Bijgewerkt"]


def col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def cell_text(c) -> str:
    v = c.find(X + "v")
    if v is not None and v.text is not None:
        return v.text
    t = c.find(f"{X}is/{X}t")
    return t.text if t is not None and t.text else ""


def set_cell(row, col: int, value: str, style: str | None = None) -> None:
    ref = f"{col_letter(col)}{row.get('r')}"
    cells = row.findall(X + "c")
    target = None
    for c in cells:
        if c.get("r") == ref:
            target = c
            break
    if target is None:
        target = etree.Element(X + "c")
        target.set("r", ref)
        # Invoegen op de juiste kolompositie.
        idx = len(cells)
        for i, c in enumerate(cells):
            if col_index(c.get("r")) > col:
                idx = i
                break
        row.insert(idx, target)
    for child in list(target):
        target.remove(child)
    if style is not None:
        target.set("s", style)
    target.set("t", "str")
    v = etree.SubElement(target, X + "v")
    v.text = value


def merge(entries: list[dict], sheet: str, warnings: list[str]) -> dict:
    status = None
    validaties, bewijzen, blokkades, data = [], [], [], ""
    waarde = None
    for e in entries:
        s = (e.get("status") or "").strip()
        if s in FORBIDDEN:
            warnings.append(f"{e.get('id')}: status '{s}' door hulpmiddel teruggezet naar 'Bezig' (alleen na echte acceptatie handmatig)")
            s = "Bezig"
        if s and s not in ALLOWED[sheet]:
            warnings.append(f"{e.get('id')}: onbekende status '{s}' genegeerd")
            s = ""
        if s and (status is None or PRECEDENCE.get(s, 0) > PRECEDENCE.get(status, 0)):
            status = s
        repo = e.get("repo", "")
        for key, bucket in (("validatie", validaties), ("bewijs", bewijzen), ("blokkade", blokkades), ("opmerking", blokkades)):
            val = (e.get(key) or "").strip()
            if val:
                bucket.append(f"[{repo}] {val}" if repo and len(entries) > 1 else val)
        if e.get("waarde"):
            waarde = str(e["waarde"])
        data = max(data, e.get("bijgewerkt", ""))
    return dict(status=status, validatie=" | ".join(dict.fromkeys(validaties)),
                bewijs=" | ".join(dict.fromkeys(bewijzen)), blokkade=" | ".join(dict.fromkeys(blokkades)),
                bijgewerkt=data, waarde=waarde)


def sheet_paths(z: zipfile.ZipFile) -> dict[str, str]:
    wb = etree.fromstring(z.read("xl/workbook.xml"))
    rels = etree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {r.get("Id"): r.get("Target") for r in rels.findall("{%s}Relationship" % PNS)}
    out = {}
    for s in wb.iter(X + "sheet"):
        target = rid_to_target[s.get("{%s}id" % RNS)]
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        out[s.get("name")] = target
    return out


def table_for_sheet(z: zipfile.ZipFile, sheet_path: str) -> str | None:
    rel_path = sheet_path.replace("worksheets/", "worksheets/_rels/") + ".rels"
    if rel_path not in z.namelist():
        return None
    rels = etree.fromstring(z.read(rel_path))
    for r in rels.findall("{%s}Relationship" % PNS):
        if r.get("Type").endswith("/table"):
            t = r.get("Target").lstrip("/")
            return t if t.startswith("xl/") else "xl/" + t.split("../")[-1]
    return None


def update_sheet(xml: bytes, sheet: str, evidence: dict[str, list[dict]], warnings: list[str], stats: dict) -> tuple[bytes, int]:
    root = etree.fromstring(xml)
    lay = LAYOUT[sheet]
    data = root.find(X + "sheetData")
    rows = data.findall(X + "row")
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
                c.set("min", str(n)); c.set("max", str(n)); c.set("width", str(width)); c.set("customWidth", "1")
    last_row = int(rows[-1].get("r"))
    for row in rows[1:]:
        id_cell = next((c for c in row.findall(X + "c") if col_index(c.get("r")) == lay["id"]), None)
        if id_cell is None:
            continue
        rid = cell_text(id_cell).strip()
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
    return etree.tostring(root, xml_declaration=True, encoding="utf-8", standalone=None), last_row


def update_table(xml: bytes, new_last_col: int) -> bytes:
    root = etree.fromstring(xml)
    ref = root.get("ref")
    start, end = ref.split(":")
    end_row = re.sub(r"[A-Z]+", "", end)
    root.set("ref", f"{start}:{col_letter(new_last_col)}{end_row}")
    af = root.find(X + "autoFilter")
    if af is not None:
        af.set("ref", root.get("ref"))
    tcs = root.find(X + "tableColumns")
    names = [tc.get("name") for tc in tcs.findall(X + "tableColumn")]
    next_id = max(int(tc.get("id")) for tc in tcs.findall(X + "tableColumn")) + 1
    start_col = col_index(start)
    needed = new_last_col - start_col + 1
    # Kolommen tussen bestaande einde en nieuwe kolommen krijgen een naam.
    i = 0
    while len(names) < needed:
        idx = len(names)
        abs_col = start_col + idx
        name = None
        for j, h in enumerate(EXTRA_HEADERS):
            if abs_col == new_last_col - len(EXTRA_HEADERS) + 1 + j:
                name = h
        name = name or f"Kolom{abs_col}"
        tc = etree.SubElement(tcs, X + "tableColumn")
        tc.set("id", str(next_id)); tc.set("name", name)
        next_id += 1; names.append(name); i += 1
    tcs.set("count", str(len(names)))
    return etree.tostring(root, xml_declaration=True, encoding="utf-8")


def update_simple_rows(xml: bytes, key_col: int, updates: dict[str, dict[int, str]]) -> bytes:
    root = etree.fromstring(xml)
    for row in root.find(X + "sheetData").findall(X + "row"):
        key_cell = next((c for c in row.findall(X + "c") if col_index(c.get("r")) == key_col), None)
        if key_cell is None:
            continue
        key = cell_text(key_cell).strip()
        if key in updates:
            for col, val in updates.pop(key).items():
                set_cell(row, col, val)
    return etree.tostring(root, xml_declaration=True, encoding="utf-8")


def append_rows(xml: bytes, rows_to_add: list[list[str]]) -> bytes:
    root = etree.fromstring(xml)
    data = root.find(X + "sheetData")
    existing_keys = set()
    rows = data.findall(X + "row")
    for row in rows:
        c = row.find(X + "c")
        if c is not None:
            existing_keys.add(cell_text(c))
    n = int(rows[-1].get("r")) if rows else 0
    for values in rows_to_add:
        if values[0] in existing_keys:
            # Bijwerken i.p.v. dupliceren.
            for row in rows:
                c = row.find(X + "c")
                if c is not None and cell_text(c) == values[0]:
                    for i, v in enumerate(values):
                        set_cell(row, i + 1, v)
            continue
        n += 1
        row = etree.SubElement(data, X + "row")
        row.set("r", str(n))
        for i, v in enumerate(values):
            set_cell(row, i + 1, v)
    dim = root.find(X + "dimension")
    if dim is not None:
        dim.set("ref", f"A1:{col_letter(max(len(r) for r in rows_to_add) if rows_to_add else 2)}{n}")
    return etree.tostring(root, xml_declaration=True, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--evidence", nargs="*", default=[])
    ap.add_argument("--program", help="EVIDENCE_PROGRAMMA.json met Fasen/Releases/Instructies")
    ap.add_argument("--out", help="uitvoerpad (standaard: in plaats)")
    args = ap.parse_args(argv)

    warnings: list[str] = []
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
            if rid.startswith("EX"):
                sheet = "Testmatrix"
            elif re.fullmatch(r"D\d\d", rid):
                sheet = "Besluiten"
            elif re.fullmatch(r"P\d", rid):
                sheet = "Fasen"
            else:
                sheet = "Werkpakketten"
            e.setdefault("repo", Path(p).parts[-4] if len(Path(p).parts) >= 4 else "")
            by_sheet[sheet].setdefault(rid, []).append(e)

    program = {}
    if args.program:
        program = json.loads(Path(args.program).read_text(encoding="utf-8"))
        for e in program.get("fasen", []):
            by_sheet["Fasen"].setdefault(e["id"], []).append(e)

    src = Path(args.xlsx)
    out = Path(args.out) if args.out else src
    with zipfile.ZipFile(src) as z:
        paths = sheet_paths(z)
        contents = {n: z.read(n) for n in z.namelist()}
        infos = {i.filename: i for i in z.infolist()}
        stats: dict[str, int] = {}
        for sheet in LAYOUT:
            sp = paths[sheet]
            new_xml, _ = update_sheet(contents[sp], sheet, by_sheet[sheet], warnings, stats)
            contents[sp] = new_xml
            tp = table_for_sheet(z, sp)
            if tp and tp in contents:
                contents[tp] = update_table(contents[tp], LAYOUT[sheet]["extra_start"] + len(EXTRA_HEADERS) - 1)
        for sheet, leftovers in by_sheet.items():
            for rid in leftovers:
                warnings.append(f"{rid}: geen rij gevonden in blad {sheet}")
        if program.get("releases"):
            # Releases: kolom A = project; B..G zoals in de werkmap.
            colmap = {"gecontroleerde_stand": 2, "bewijsstatus": 3, "peildatum": 4, "commit": 5, "bron": 6, "actie": 7}
            upd = {r["project"]: {colmap[k]: str(v) for k, v in r.items() if k in colmap} for r in program["releases"]}
            contents[paths["Releases"]] = update_simple_rows(contents[paths["Releases"]], 1, upd)
            if upd:
                contents[paths["Releases"]] = append_rows(contents[paths["Releases"]], [[k] + [v.get(i, "") for i in range(2, 8)] for k, v in upd.items()])
        if program.get("instructies"):
            contents[paths["Instructies"]] = append_rows(contents[paths["Instructies"]], [[r["onderwerp"], r["instructie"]] for r in program["instructies"]])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in contents.items():
            info = infos[name]
            zi = zipfile.ZipInfo(name, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    if out == src:
        shutil.copy2(src, src.with_suffix(".xlsx.bak"))
    out.write_bytes(buf.getvalue())
    print(json.dumps({"bijgewerkt_per_blad": stats, "waarschuwingen": warnings}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
