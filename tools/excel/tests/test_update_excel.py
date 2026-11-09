# ruff: noqa: E501  (lange XML-regels in het test-werkboek)
"""Tests voor tools/excel/update_excel.py (Δ-ASM-EXCEL).

Twee soorten:
- een klein, met de hand opgebouwd werkboek met dezelfde onderdelen als de echte afvinklijst (tabellen, dropdowns,
  voorwaardelijke opmaak, databar met extLst, Dashboard-formules en een samengevoegd fasenblok);
- de echte Excel uit docs/platform-v2/08_EXCEL, in een tijdelijke kopie, met de B03 2.0-invoer uit 08_EXCEL/b03/.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")
etree = pytest.importorskip("lxml.etree")

HIER = Path(__file__).resolve().parent
REPO = HIER.parents[2]
SPEC = importlib.util.spec_from_file_location("update_excel", HIER.parent / "update_excel.py")
assert SPEC and SPEC.loader
ue = importlib.util.module_from_spec(SPEC)
sys.modules["update_excel"] = ue
SPEC.loader.exec_module(ue)

X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
EXCEL = REPO / "docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx"
B03 = REPO / "docs/platform-v2/08_EXCEL/b03"

# ------------------------------------------------------------------ klein test-werkboek
NSDECL = 'xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
RDECL = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_WS = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
CT_TB = "application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"
BLADEN = ["Dashboard", "Werkpakketten", "Testmatrix", "Besluiten", "Fasen", "Appoverzicht", "Releases", "Instructies"]


def _c(ref: str, waarde: str | None = None, s: str | None = None, f: str | None = None, t: str = "str") -> str:
    attr = f' r="{ref}"' + (f' s="{s}"' if s else "")
    if f is not None:
        return f'<x:c{attr} t="{t}"><x:f>{f}</x:f><x:v>{waarde or 0}</x:v></x:c>'
    if waarde is None:
        return f'<x:c{attr} t="str"/>'
    return f'<x:c{attr} t="str"><x:v>{waarde}</x:v></x:c>'


def _row(r: int, cellen: list[str], extra: str = "") -> str:
    return f'<x:row r="{r}"{extra}>' + "".join(cellen) + "</x:row>"


def _kop(r: int, namen: list[str]) -> str:
    return _row(
        r, [_c(f"{ue.col_letter(i + 1)}{r}", n, s="1") for i, n in enumerate(namen)], ' ht="30" customHeight="1"'
    )


def _blad(rows: list[str], na_data: str = "", cols: int = 8) -> str:
    colsxml = "".join(f'<x:col min="{i}" max="{i}" width="20" customWidth="1"/>' for i in range(1, cols + 1))
    return (
        f'<?xml version="1.0" encoding="utf-8"?><x:worksheet {NSDECL}><x:sheetViews><x:sheetView workbookViewId="0">'
        f'<x:pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></x:sheetView></x:sheetViews>'
        f'<x:sheetFormatPr defaultRowHeight="15"/><x:cols>{colsxml}</x:cols><x:sheetData>{"".join(rows)}</x:sheetData>'
        f"{na_data}</x:worksheet>"
    )


def _cf(sqref: str, kol: str) -> str:
    return (
        f'<x:conditionalFormatting sqref="{sqref}"><x:cfRule type="expression" dxfId="0" priority="1">'
        f'<x:formula>${kol}2="Bezig"</x:formula></x:cfRule></x:conditionalFormatting>'
    )


def _dv(sqref: str, lijst: str) -> str:
    return (
        f'<x:dataValidations count="1"><x:dataValidation type="list" sqref="{sqref}">'
        f'<x:formula1>"{lijst}"</x:formula1></x:dataValidation></x:dataValidations>'
    )


def _tabel(i: int, naam: str, ref: str, kolommen: list[str]) -> str:
    tc = "".join(f'<x:tableColumn id="{k + 1}" name="{n}"/>' for k, n in enumerate(kolommen))
    return (
        f'<?xml version="1.0" encoding="utf-8"?><x:table {NSDECL} id="{i}" name="{naam}" displayName="{naam}" '
        f'ref="{ref}" headerRowCount="1" totalsRowCount="0" totalsRowShown="0"><x:tableColumns count="{len(kolommen)}">'
        f'{tc}</x:tableColumns><x:tableStyleInfo name="TableStyleMedium2" showRowStripes="1"/></x:table>'
    )


WP_KOP = [
    "ID",
    "App / project",
    "Fase",
    "Soort",
    "Prioriteit",
    "Risico",
    "Uitvoerbare taak",
    "Wat de bouwer moet doen",
    "Concreet acceptatiecriterium",
    "Status / afvinken",
    "Bewijs / link",
    "Afhankelijkheden",
    "Document in ZIP",
    "Bron URL",
    "Validatie",
    "Blokkade / opmerking",
    "Bijgewerkt",
]
TM_KOP = [
    "Test-ID",
    "Scenario",
    "Uitvoeren",
    "Verwacht resultaat",
    "Prioriteit",
    "Status / afvinken",
    "Bewijs / link",
    "Document in ZIP",
    "Validatie",
    "Blokkade / opmerking",
    "Bijgewerkt",
]
BS_KOP = [
    "ID",
    "Ontbrekende beslissing / bron",
    "Wat vastleggen",
    "Gate",
    "Status",
    "Jouw waarde / keuze",
    "Bewijs",
    "Belangrijk voor",
    "Validatie",
    "Blokkade / opmerking",
    "Bijgewerkt",
]
FA_KOP = [
    "Fase",
    "Beschrijving",
    "Go / No-go voor volgende fase",
    "Status",
    "Bewijs / akkoord",
    "Validatie",
    "Blokkade / opmerking",
    "Bijgewerkt",
]


def _wp(r: int, rid: str, project: str, status: str, bewijs: str | None = None, validatie: str | None = None) -> str:
    cellen = [
        _c(f"A{r}", rid),
        _c(f"B{r}", project),
        _c(f"C{r}", "F1 - Kern en contracten"),
        _c(f"D{r}", "Bouwen"),
        _c(f"E{r}", "P1"),
        _c(f"F{r}", "Middel"),
        _c(f"G{r}", f"taak {rid}", s="2"),
        _c(f"H{r}", f"uitvoering {rid}", s="2"),
        _c(f"I{r}", f"acceptatie {rid}", s="2"),
        _c(f"J{r}", status),
        _c(f"K{r}", bewijs),
        _c(f"L{r}", "afh"),
        _c(f"M{r}", "doc.md"),
        _c(f"N{r}", "https://bron"),
    ]
    if validatie:
        cellen += [_c(f"O{r}", validatie), _c(f"P{r}", "opm"), _c(f"Q{r}", "2026-11-01")]
    return _row(r, cellen, ' ht="40" customHeight="1"')


def maak_werkboek(pad: Path) -> None:
    dash_rows = [
        _row(9, [_c("A9", "Werkpakketten totaal"), _c("B9", "3", f="COUNTA(Werkpakketten!$A$2:$A$4)", t="n")]),
        _row(10, [_c("A10", "Bezig"), _c("B10", "0", f='COUNTIF(Werkpakketten!$J$2:$J$4,"Bezig")', t="n")]),
        _row(11, [_c("A11", "Tests"), _c("B11", "2", f="COUNTA(Testmatrix!$A$2:$A$3)", t="n")]),
        _row(12, [_c("A12", "Voortgang"), _c("B12", "0", s="3", f="IFERROR(B10/B9,0)", t="n")]),
    ]
    for i, r in enumerate(range(26, 29)):
        dash_rows.append(
            _row(
                r,
                [_c(f"A{r}", "P", f=f"Fasen!A{2 + i}"), _c(f"B{r}", "x", f=f"Fasen!D{2 + i}")]
                + [_c(f"{k}{r}", "toelichting" if (k == "D" and r == 26) else None, s="2") for k in "DEFGH"],
            )
        )
    dashboard = _blad(dash_rows, '<x:mergeCells count="1"><x:mergeCell ref="D26:H28"/></x:mergeCells>')
    werk = _blad(
        [
            _kop(1, WP_KOP),
            _wp(2, "B01-001", "Home Control Hub", "Bezig"),
            _wp(3, "B03-001", "Universele mediaserver", "Niet gestart"),
            _wp(4, "B03-004", "Universele mediaserver", "Bezig", bewijs="bewijs-004", validatie="Sim-getest"),
        ],
        _cf("J2:J4", "J")
        + _dv("J2:J4", "Niet gestart,Bezig,Gereed,Geblokkeerd,N.v.t.")
        + '<x:tableParts count="1"><x:tablePart '
        + RDECL
        + ' r:id="rT1"/></x:tableParts>',
        cols=17,
    )
    tm_rows = [_kop(1, TM_KOP)] + [
        _row(
            r,
            [
                _c(f"A{r}", f"EX0{r - 1}"),
                _c(f"B{r}", "s", s="2"),
                _c(f"C{r}", "u", s="2"),
                _c(f"D{r}", "v", s="2"),
                _c(f"E{r}", "P1"),
                _c(f"F{r}", "Niet gestart"),
                _c(f"G{r}"),
                _c(f"H{r}", "testmatrix.md"),
            ],
            ' ht="38" customHeight="1"',
        )
        for r in (2, 3)
    ]
    test = _blad(
        tm_rows,
        _cf("F2:F3", "F")
        + _dv("F2:F3", "Niet gestart,Bezig,Geslaagd,Mislukt,Geblokkeerd,N.v.t.")
        + '<x:tableParts count="1"><x:tablePart '
        + RDECL
        + ' r:id="rT2"/></x:tableParts>',
        cols=11,
    )
    besl = _blad(
        [_kop(1, BS_KOP), _row(2, [_c("A2", "D01"), _c("B2", "TrueNAS versie"), _c("E2", "Open")])],
        _dv("E2:E2", "Open,Ingevuld,Getest,Geblokkeerd,N.v.t.")
        + '<x:tableParts count="1"><x:tablePart '
        + RDECL
        + ' r:id="rT3"/></x:tableParts>',
        cols=11,
    )
    fasen = _blad(
        [_kop(1, FA_KOP)]
        + [
            _row(
                r,
                [
                    _c(f"A{r}", fid),
                    _c(f"B{r}", f"beschrijving {fid}", s="2"),
                    _c(f"C{r}", f"go {fid}", s="2"),
                    _c(f"D{r}", "Niet gestart"),
                    _c(f"E{r}"),
                ],
                ' ht="47" customHeight="1"',
            )
            for r, fid in ((2, "P0"), (3, "P3"), (4, "P4"))
        ],
        _dv("D2:D4", "Niet gestart,Bezig,Gereed,Geblokkeerd,N.v.t."),
    )
    ext = (
        '<x:extLst><x:ext xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main" '
        'uri="{78C0D931-6437-407d-A8EE-F0AAD7539E65}"><x14:conditionalFormattings><x14:conditionalFormatting '
        'xmlns:xm="http://schemas.microsoft.com/office/excel/2006/main"><x14:cfRule type="dataBar" id="{00000000-0000-0000-0000-000000000001}">'
        '<x14:dataBar minLength="0" maxLength="100"><x14:cfvo type="autoMin"/><x14:cfvo type="autoMax"/></x14:dataBar>'
        "</x14:cfRule><xm:sqref>F2:F2</xm:sqref></x14:conditionalFormatting></x14:conditionalFormattings></x:ext></x:extLst>"
    )
    app = _blad(
        [
            _kop(1, ["App", "Soort", "Document", "Taken", "Gereed", "Voortgang"]),
            _row(
                2,
                [
                    _c("A2", "Universele mediaserver"),
                    _c("B2", "Nieuw bouwen"),
                    _c("C2", "b03.md"),
                    _c("D2", "2", f="COUNTIF(Werkpakketten!$B$2:$B$4,A2)", t="n"),
                    _c("E2", "0", f='COUNTIFS(Werkpakketten!$B$2:$B$4,A2,Werkpakketten!$J$2:$J$4,"Gereed")', t="n"),
                    _c("F2", "0", s="3", f="IFERROR(E2/D2,0)", t="n"),
                ],
            ),
        ],
        '<x:conditionalFormatting sqref="F2:F2"><x:cfRule type="dataBar" priority="1"><x:dataBar>'
        '<x:cfvo type="min"/><x:cfvo type="max"/><x:color rgb="FF2563EB"/></x:dataBar></x:cfRule>'
        "</x:conditionalFormatting>" + ext,
    )
    rel = _blad([_kop(1, ["Project", "Stand"]), _row(2, [_c("A2", "MediaGuard Ultimate"), _c("B2", "1.2.2")])])
    instr = _blad([_kop(1, ["Onderwerp", "Instructie"]), _row(2, [_c("A2", "Status"), _c("B2", "nooit Gereed")])])
    styles = (
        '<?xml version="1.0" encoding="utf-8"?><x:styleSheet ' + NSDECL + '><x:fonts count="1"><x:font><x:sz val="11"/>'
        '<x:name val="Calibri"/></x:font></x:fonts><x:fills count="2"><x:fill><x:patternFill patternType="none"/></x:fill>'
        '<x:fill><x:patternFill patternType="gray125"/></x:fill></x:fills><x:borders count="1"><x:border/></x:borders>'
        '<x:cellStyleXfs count="1"><x:xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></x:cellStyleXfs>'
        '<x:cellXfs count="4"><x:xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<x:xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<x:xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><x:alignment wrapText="1"/></x:xf>'
        '<x:xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></x:cellXfs>'
        '<x:dxfs count="1"><x:dxf><x:fill><x:patternFill><x:bgColor rgb="FFFFEB9C"/></x:patternFill></x:fill></x:dxf>'
        "</x:dxfs></x:styleSheet>"
    )
    bladen = [dashboard, werk, test, besl, fasen, app, rel, instr]
    sheets = "".join(f'<x:sheet name="{n}" sheetId="{i + 1}" r:id="rS{i + 1}" {RDECL}/>' for i, n in enumerate(BLADEN))
    workbook = f'<?xml version="1.0" encoding="utf-8"?><x:workbook {NSDECL}><x:sheets>{sheets}</x:sheets></x:workbook>'
    wbrels = (
        '<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Type="{REL}/styles" Target="/xl/styles.xml" Id="rSt"/>'
        + "".join(
            f'<Relationship Type="{REL}/worksheet" Target="/xl/worksheets/sheet{i + 1}.xml" Id="rS{i + 1}"/>'
            for i in range(len(BLADEN))
        )
        + "</Relationships>"
    )
    ct = (
        '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="{CT_WS}"/>' for i in range(len(BLADEN))
        )
        + "".join(f'<Override PartName="/xl/tables/table{i}.xml" ContentType="{CT_TB}"/>' for i in (1, 2, 3))
        + "</Types>"
    )
    rootrels = (
        '<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Type="{REL}/officeDocument" Target="/xl/workbook.xml" Id="R1"/></Relationships>'
    )

    def tabelrel(i: int) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Type="{REL}/table" Target="/xl/tables/table{i}.xml" Id="rT{i}"/></Relationships>'
        )

    with zipfile.ZipFile(pad, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rootrels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/styles.xml", styles)
        for i, b in enumerate(bladen):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", b)
        for i, blad in ((1, 2), (2, 3), (3, 4)):
            z.writestr(f"xl/worksheets/_rels/sheet{blad}.xml.rels", tabelrel(i))
        z.writestr("xl/tables/table1.xml", _tabel(1, "WorkItems", "A1:Q4", WP_KOP))
        z.writestr("xl/tables/table2.xml", _tabel(2, "EndToEndTests", "A1:K3", TM_KOP))
        z.writestr("xl/tables/table3.xml", _tabel(3, "DecisionsTracker", "A1:K2", BS_KOP))


def taak(rid: str, uitvoering: str = "Programmafase: P4. nieuw") -> dict:
    return {
        "ID": rid,
        "Project": "Universele mediaserver",
        "Fase": "F1 - Kern en contracten",
        "Soort": "Bouwen",
        "Taak": f"nieuwe taak {rid}",
        "Uitvoering": uitvoering,
        "Acceptatie": f"acceptatie {rid} nieuw",
        "Risico": "Hoog",
        "Prioriteit": "P0",
        "Afhankelijkheid": "B03-014",
        "Bron": "https://jellyfin.org",
        "Document": "02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md",
    }


@pytest.fixture()
def klein(tmp_path: Path) -> dict[str, Path]:
    xlsx = tmp_path / "klein.xlsx"
    maak_werkboek(xlsx)
    wp = tmp_path / "wp.json"
    wp.write_text(
        json.dumps(
            [taak("B03-004", "uitvoering B03-004 Aanvulling: meer"), taak("B03-014"), taak("B03-002"), taak("C01-001")],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tm = tmp_path / "tm.json"
    tm.write_text(
        json.dumps(
            [
                ["JLT-01", "Scenario 1", "Doe iets", "Iets gebeurt; validatie Sim-geslaagd"],
                [
                    "JLT-06",
                    "Echte NAS",
                    "NAS nodig",
                    "tot dan Geblokkeerd met NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware)",
                ],
            ]
        ),
        encoding="utf-8",
    )
    meta = tmp_path / "meta.json"
    meta.write_text(
        json.dumps(
            {
                "per_test": {
                    "JLT-01": {"prioriteit": "P0", "startstatus": "Niet gestart"},
                    "JLT-06": {"prioriteit": "P1", "startstatus": "Geblokkeerd"},
                }
            }
        ),
        encoding="utf-8",
    )
    fa = tmp_path / "fasen.json"
    fa.write_text(
        json.dumps(
            [
                {
                    "id": "P4-0",
                    "na": "P3",
                    "beschrijving": "Upgrade naar 12.x",
                    "go_nogo": "geen verlies",
                    "status": "Niet gestart",
                }
            ]
        ),
        encoding="utf-8",
    )
    return {"xlsx": xlsx, "wp": wp, "tm": tm, "meta": meta, "fa": fa, "dir": tmp_path}


def args_voor(p: dict[str, Path], *extra: str) -> list[str]:
    return [
        "--xlsx",
        str(p["xlsx"]),
        "--werkpakketten",
        str(p["wp"]),
        "--testen",
        str(p["tm"]),
        "--testmeta",
        str(p["meta"]),
        "--testdocument",
        "02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md",
        "--fasen",
        str(p["fa"]),
        "--date",
        "2026-11-09",
        *extra,
    ]


def onderdelen(pad: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(pad) as z:
        return {n: z.read(n) for n in z.namelist()}


def blad(delen: dict[str, bytes], nr: int):
    return etree.fromstring(delen[f"xl/worksheets/sheet{nr}.xml"])


def ids(root, col: str = "A") -> list[str]:
    uit = []
    for row in root.find(X + "sheetData").findall(X + "row")[1:]:
        for c in row.findall(X + "c"):
            if re.sub(r"\d", "", c.get("r")) == col:
                uit.append(ue.cell_text(c))
    return uit


def waarde(root, ref: str) -> str:
    for c in root.iter(X + "c"):
        if c.get("r") == ref:
            return ue.cell_text(c)
    return ""


def formule(root, ref: str) -> str:
    for c in root.iter(X + "c"):
        if c.get("r") == ref:
            return c.find(X + "f").text
    return ""


def sqrefs(root) -> list[str]:
    return [el.get("sqref") for tag in ("conditionalFormatting", "dataValidation") for el in root.iter(X + tag)]


# ------------------------------------------------------------------ tests klein werkboek
def test_klein_werkboek_rijen_testrijen_en_fase(klein):
    voor = onderdelen(klein["xlsx"])
    assert ue.main(args_voor(klein)) == 0
    na = onderdelen(klein["xlsx"])
    # werkpakketten: op ID-volgorde binnen de reeks; nieuwe reeks achteraan
    wp = blad(na, 2)
    assert ids(wp) == ["B01-001", "B03-001", "B03-002", "B03-004", "B03-014", "C01-001"]
    assert etree.fromstring(na["xl/tables/table1.xml"]).get("ref") == "A1:Q7"
    assert sqrefs(wp) == ["J2:J7", "J2:J7"]
    # uitgebreide rij: inhoud vervangen, status/bewijs/validatie behouden
    assert waarde(wp, "H5") == "uitvoering B03-004 Aanvulling: meer"
    assert (waarde(wp, "J5"), waarde(wp, "K5"), waarde(wp, "O5")) == ("Bezig", "bewijs-004", "Sim-getest")
    # nieuwe rij: startstatus, stijl en rijhoogte van de buurrij
    assert waarde(wp, "J4") == "Niet gestart" and waarde(wp, "G4") == "nieuwe taak B03-002"
    rij4 = next(r for r in wp.iter(X + "row") if r.get("r") == "4")
    assert rij4.get("ht") == "40" and next(c for c in rij4 if c.get("r") == "H4").get("s") == "2"
    # testmatrix
    tm = blad(na, 3)
    assert ids(tm) == ["EX01", "EX02", "JLT-01", "JLT-06"]
    assert etree.fromstring(na["xl/tables/table2.xml"]).get("ref") == "A1:K5"
    assert sqrefs(tm) == ["F2:F5", "F2:F5"]
    assert (waarde(tm, "E4"), waarde(tm, "F4"), waarde(tm, "H4")) == (
        "P0",
        "Niet gestart",
        "02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md",
    )
    assert waarde(tm, "F5") == "Geblokkeerd"
    assert waarde(tm, "I5") == "NIET GEVALIDEERD (echte NAS); NIET GEVALIDEERD (hardware)"
    # fasen: P4-0 na P3 en vóór P4; dropdown groeit mee
    fa = blad(na, 5)
    assert ids(fa) == ["P0", "P3", "P4-0", "P4"]
    assert sqrefs(fa) == ["D2:D5"]
    # dashboard: bereiken groeien mee, fasenblok toont alle fasen, samengevoegde cel groeit mee
    db = blad(na, 1)
    assert formule(db, "B9") == "COUNTA(Werkpakketten!$A$2:$A$7)" and waarde(db, "B9") == "6"
    assert formule(db, "B11") == "COUNTA(Testmatrix!$A$2:$A$5)" and waarde(db, "B11") == "4"
    assert waarde(db, "B10") == "2"
    assert waarde(db, "B12") == repr(2 / 6)
    assert [formule(db, f"A{r}") for r in range(26, 30)] == ["Fasen!A2", "Fasen!A3", "Fasen!A4", "Fasen!A5"]
    assert [waarde(db, f"A{r}") for r in range(26, 30)] == ["P0", "P3", "P4-0", "P4"]
    assert formule(db, "B28") == "Fasen!D4" and waarde(db, "B28") == "Niet gestart"
    assert [m.get("ref") for m in db.iter(X + "mergeCell")] == ["D26:H29"]
    # appoverzicht: formules groeien mee, databar (extLst) en opmaak byte-gelijk
    app_voor, app_na = blad(voor, 6), blad(na, 6)
    assert formule(app_na, "D2") == "COUNTIF(Werkpakketten!$B$2:$B$7,A2)" and waarde(app_na, "D2") == "5"
    for tag in ("extLst", "conditionalFormatting", "cols", "sheetViews"):
        assert etree.tostring(app_voor.find(X + tag)) == etree.tostring(app_na.find(X + tag))
    # onderdelen die niet geraakt mogen worden: byte-gelijk
    for naam in (
        "xl/worksheets/sheet4.xml",
        "xl/worksheets/sheet7.xml",
        "xl/worksheets/sheet8.xml",
        "xl/tables/table3.xml",
        "xl/styles.xml",
        "xl/workbook.xml",
        "[Content_Types].xml",
        "xl/_rels/workbook.xml.rels",
    ):
        assert voor[naam] == na[naam], naam
    assert (klein["dir"] / "klein.xlsx.bak").read_bytes() != klein["xlsx"].read_bytes()


def test_idempotent(klein):
    assert ue.main(args_voor(klein)) == 0
    eerste = klein["xlsx"].read_bytes()
    assert ue.main(args_voor(klein, "--date", "2030-01-01")) == 0
    assert klein["xlsx"].read_bytes() == eerste


def test_openpyxl_read_only_zelfde_structuur(klein):
    voor = openpyxl.load_workbook(klein["xlsx"], read_only=True)
    kop_voor = {n: next(voor[n].iter_rows(max_row=1, values_only=True)) for n in voor.sheetnames}
    assert ue.main(args_voor(klein)) == 0
    na = openpyxl.load_workbook(klein["xlsx"], read_only=True)
    assert na.sheetnames == voor.sheetnames == BLADEN
    assert {n: next(na[n].iter_rows(max_row=1, values_only=True)) for n in na.sheetnames} == kop_voor
    assert len(list(na["Werkpakketten"].iter_rows(values_only=True))) == 7
    assert len(list(na["Testmatrix"].iter_rows(values_only=True))) == 5


@pytest.mark.parametrize("wat", ["werkpakket", "test", "fase"])
def test_weigert_gereed_en_geslaagd(klein, wat, capsys):
    voor = klein["xlsx"].read_bytes()
    extra: list[str] = []
    if wat == "werkpakket":
        extra = ["--status-werkpakketten", "Gereed"]
    elif wat == "test":
        klein["meta"].write_text(json.dumps({"per_test": {"JLT-01": {"prioriteit": "P0", "startstatus": "Geslaagd"}}}))
    else:
        klein["fa"].write_text(
            json.dumps([{"id": "P4-0", "na": "P3", "beschrijving": "b", "go_nogo": "g", "status": "Gereed"}])
        )
    assert ue.main(args_voor(klein, *extra)) == 2
    assert "geweigerd" in capsys.readouterr().err
    assert klein["xlsx"].read_bytes() == voor
    assert not (klein["dir"] / "klein.xlsx.bak").exists()


def test_weigert_ander_formaat(klein):
    klein["wp"].write_text(json.dumps([{"ID": "B03-099", "Taak": "x"}]))
    assert ue.main(args_voor(klein)) == 2


def test_bewijs_jlt_naar_testmatrix_en_p4_0_naar_fasen(klein):
    assert ue.main(args_voor(klein)) == 0
    ev = klein["dir"] / "repo" / "docs" / "platform-v2" / "EVIDENCE.json"
    ev.parent.mkdir(parents=True)
    ev.write_text(
        json.dumps(
            [
                {
                    "id": "JLT-01",
                    "status": "Geslaagd",
                    "validatie": "Sim-geslaagd",
                    "bewijs": "run 1",
                    "bijgewerkt": "2026-11-09",
                },
                {"id": "P4-0", "status": "Bezig", "validatie": "Sim-getest", "bewijs": "b", "bijgewerkt": "2026-11-09"},
                {"id": "B03-014", "status": "Gereed", "bewijs": "x", "bijgewerkt": "2026-11-09"},
            ]
        ),
        encoding="utf-8",
    )
    uit = klein["dir"] / "uit.xlsx"
    assert ue.main(["--xlsx", str(klein["xlsx"]), "--evidence", str(ev), "--out", str(uit)]) == 0
    na = onderdelen(uit)
    tm, fa, wp = blad(na, 3), blad(na, 5), blad(na, 2)
    assert (waarde(tm, "F4"), waarde(tm, "G4"), waarde(tm, "I4")) == ("Bezig", "run 1", "Sim-geslaagd")
    assert (waarde(fa, "A4"), waarde(fa, "D4"), waarde(fa, "F4")) == ("P4-0", "Bezig", "Sim-getest")
    assert waarde(wp, "J6") == "Bezig"  # B03-014: 'Gereed' teruggezet
    assert waarde(blad(na, 1), "B28") == "Bezig"  # Dashboard toont de status van P4-0


def test_herberekening_en_verwijzingen():
    assert ue.shift_ref("$A$2:$A$306", 307, 5, True) == "$A$2:$A$311"
    assert ue.shift_ref("$A$2:$A$306", 40, 1, False) == "$A$2:$A$307"
    assert ue.shift_ref("A6", 6, 1, False) == "A7" and ue.shift_ref("A5", 6, 1, True) == "A5"
    f = 'COUNTIF(Werkpakketten!$J$2:$J$306,"Werkpakketten!A1")+Fasen!A6'
    assert (
        ue.shift_formula(f, "Werkpakketten", False, 307, 2, True)
        == 'COUNTIF(Werkpakketten!$J$2:$J$308,"Werkpakketten!A1")+Fasen!A6'
    )
    assert ue.route("JLT-12") == "Testmatrix" and ue.route("P4-0") == "Fasen" and ue.route("EX01") == "Testmatrix"
    assert ue.route("D07") == "Besluiten" and ue.route("B03-015") == "Werkpakketten"


# ------------------------------------------------------------------ test op de echte Excel (tijdelijke kopie)
@pytest.mark.skipif(not (EXCEL.exists() and B03.exists()), reason="echte Excel of B03-invoer ontbreekt")
def test_echte_excel_in_tijdelijke_kopie(tmp_path: Path):
    kopie = tmp_path / "echt.xlsx"
    shutil.copy2(EXCEL, kopie)
    voor = onderdelen(kopie)
    rijen = json.loads((B03 / "werkpakketten.json").read_text(encoding="utf-8"))
    testen = json.loads((B03 / "testen.json").read_text(encoding="utf-8"))
    meta = json.loads((B03 / "EXCEL_TAKEN_PER_REPO.json").read_text(encoding="utf-8"))["per_test"]
    ids_voor = set(ids(blad(voor, 2)))
    tids_voor = set(ids(blad(voor, 3)))
    args = [
        "--xlsx",
        str(kopie),
        "--werkpakketten",
        str(B03 / "werkpakketten.json"),
        "--testen",
        str(B03 / "testen.json"),
        "--testmeta",
        str(B03 / "EXCEL_TAKEN_PER_REPO.json"),
        "--testdocument",
        "02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md",
        "--fasen",
        str(B03 / "fasen.json"),
        "--date",
        "2026-11-09",
    ]
    assert ue.main(args) == 0
    na = onderdelen(kopie)
    wp, tm, fa, db = blad(na, 2), blad(na, 3), blad(na, 5), blad(na, 1)
    wids, tids, fids = ids(wp), ids(tm), ids(fa)
    # rij-aantallen: elke rij precies één keer
    assert len(wids) == len(set(wids)) == len(ids_voor | {r["ID"] for r in rijen})
    assert len(tids) == len(set(tids)) == len(tids_voor | {t[0] for t in testen})
    assert {t[0] for t in testen} <= set(tids) and {r["ID"] for r in rijen} <= set(wids)
    assert fids.index("P4-0") == fids.index("P3") + 1 == fids.index("P4") - 1
    # tabel- en validatiebereiken lopen tot de laatste rij
    for nr, tabel, kol in ((2, "table1.xml", "J"), (3, "table2.xml", "F")):
        laatste = int(blad(na, nr).find(X + "sheetData").findall(X + "row")[-1].get("r"))
        assert etree.fromstring(na[f"xl/tables/{tabel}"]).get("ref").endswith(str(laatste))
        assert set(sqrefs(blad(na, nr))) == {f"{kol}2:{kol}{laatste}"}
    assert sqrefs(fa) == [f"D2:D{len(fids) + 1}"]
    # B03-rijen gegroepeerd, prioriteit en startstatus per testrij uit EXCEL_TAKEN_PER_REPO
    b03 = [i for i in wids if i.startswith("B03-")]
    assert wids[wids.index(b03[0]) : wids.index(b03[0]) + len(b03)] == sorted(b03)
    for rij in tm.find(X + "sheetData").findall(X + "row")[1:]:
        tid = ue.row_id(rij)
        if tid in meta:
            assert ue.cell_text(ue.find_cell(rij, 5)) == meta[tid]["prioriteit"]
    # geen eindstatus
    for root, kol in ((wp, 10), (tm, 6), (fa, 4)):
        for rij in root.find(X + "sheetData").findall(X + "row")[1:]:
            assert ue.cell_text(ue.find_cell(rij, kol)) not in {"Gereed", "Geslaagd"}
    # Dashboard telt alle rijen
    assert waarde(db, "B9") == str(len(wids)) and waarde(db, "B14") == str(len(tids))
    assert [waarde(db, f"A{r}") for r in range(26, 26 + len(fids))] == fids
    # ongewijzigde onderdelen
    for naam in (
        "xl/worksheets/sheet4.xml",
        "xl/worksheets/sheet7.xml",
        "xl/worksheets/sheet8.xml",
        "xl/tables/table3.xml",
        "xl/styles.xml",
        "xl/workbook.xml",
        "[Content_Types].xml",
    ):
        assert voor[naam] == na[naam], naam
    a6, b6 = blad(voor, 6), blad(na, 6)
    for tag in ("extLst", "conditionalFormatting", "cols"):
        assert etree.tostring(a6.find(X + tag)) == etree.tostring(b6.find(X + tag))
    # idempotent en leesbaar
    eerste = kopie.read_bytes()
    assert ue.main(args) == 0
    assert kopie.read_bytes() == eerste
    wb = openpyxl.load_workbook(kopie, read_only=True)
    assert wb.sheetnames == [
        "Dashboard",
        "Werkpakketten",
        "Testmatrix",
        "Besluiten",
        "Fasen",
        "Appoverzicht",
        "Releases",
        "Instructies",
    ]
    for naam in wb.sheetnames:
        assert next(wb[naam].iter_rows(max_row=1, values_only=True)) == next(
            openpyxl.load_workbook(EXCEL, read_only=True)[naam].iter_rows(max_row=1, values_only=True)
        )
