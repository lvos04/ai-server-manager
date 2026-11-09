# Excel-bijwerker

`update_excel.py` werkt `docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx` bij. Het werkt op XML-niveau,
zodat opmaak, stijlen, tabellen, dropdowns, voorwaardelijke opmaak en de databar op 'Appoverzicht' blijven. Een onderdeel
van het werkboek dat inhoudelijk niet verandert, blijft byte voor byte gelijk.

Het hulpmiddel kan vier dingen, in één run of apart:

| Optie | Wat | Blad |
|---|---|---|
| `--werkpakketten RIJEN.json …` | rijen in het formaat van `08_EXCEL/tasks.json` toevoegen. Een **bestaand ID** wordt inhoudelijk vervangen (bijv. de uitgebreide B03-004/005/007/009/010/013); status, bewijs en de kolommen *Validatie*, *Blokkade / opmerking* en *Bijgewerkt* blijven staan. Nieuwe rijen komen op ID-volgorde binnen hun reeks (B03-014 na B03-013), een nieuwe reeks achteraan. Startstatus: `--status-werkpakketten` (standaard *Niet gestart*). | Werkpakketten |
| `--testen TESTEN.json …` + `--testmeta EXCEL_TAKEN_PER_REPO.json` + `--testdocument DOC` | testrijen in het formaat van `08_EXCEL/e2e_cases.json` (`[ID, scenario, uitvoeren, verwacht resultaat]`) toevoegen. Prioriteit en startstatus per rij komen uit `per_test.<ID>.prioriteit`/`.startstatus`. Een rij die *Geblokkeerd* start, krijgt in *Validatie* de NIET GEVALIDEERD-labels uit de eigen tekst. | Testmatrix |
| `--fasen FASEN.json` | faserijen `{"id", "beschrijving", "go_nogo", "status", "na"}` toevoegen, bijv. P4-0 met `"na": "P3"` (tussen P3 en P4). Het fasenblok op het Dashboard groeit mee, inclusief de samengevoegde cel ernaast. | Fasen |
| `--evidence …` / `--program …` | alle `docs/platform-v2/EVIDENCE.json`-bestanden samenvoegen (zoals voorheen). `JLT-…` en `EX…` gaan naar de Testmatrix, `D01`–`D18` naar Besluiten, `P0`…`P6` en `P4-0` naar Fasen, de rest naar Werkpakketten. | alle |

Bij het invoegen groeien mee, zoals Excel dat bij "rij invoegen" doet: het tabelbereik (`ref`), de dropdowns
(`dataValidations`), de voorwaardelijke opmaak, samengevoegde cellen en de formules op andere bladen (Dashboard en
Appoverzicht tellen dus ook de nieuwe rijen). Daarna worden de opgeslagen formuleresultaten opnieuw berekend
(COUNTA, COUNTIF, COUNTIFS, IFERROR, + − × ÷ en celverwijzingen), zodat de cijfers ook kloppen in een programma dat niet zelf
herberekent. Een onbekende formule blijft ongewijzigd (met een waarschuwing).

**Regels.** Het hulpmiddel zet nooit *Gereed* of *Geslaagd*. Bewijs met zo'n status wordt *Bezig* (met waarschuwing); een
nieuwe rij of faserij met zo'n (start)status wordt geweigerd: exitcode 2 en er wordt niets geschreven. Bij meerdere bronnen
voor één ID wint de voorzichtigste status. Dezelfde invoer twee keer verwerken verandert de tweede keer niets
(idempotent). Bij een wijziging in het origineel komt er een `.xlsx.bak` naast; verwijder die na controle.

```bash
python3 -m venv /tmp/excel-venv && /tmp/excel-venv/bin/pip install -r tools/excel/requirements-test.txt
# B03 2.0: werkpakketten, testrijen en de faserij P4-0
/tmp/excel-venv/bin/python tools/excel/update_excel.py \
  --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx \
  --werkpakketten docs/platform-v2/08_EXCEL/b03/werkpakketten.json \
  --testen docs/platform-v2/08_EXCEL/b03/testen.json \
  --testmeta docs/platform-v2/08_EXCEL/b03/EXCEL_TAKEN_PER_REPO.json \
  --testdocument 02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md \
  --fasen docs/platform-v2/08_EXCEL/b03/fasen.json
# bewijs samenvoegen (alleen lezen in de andere repos)
/tmp/excel-venv/bin/python tools/excel/update_excel.py \
  --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx \
  --evidence ../*/docs/platform-v2/EVIDENCE.json --program docs/platform-v2/EVIDENCE_PROGRAMMA.json
```

`EVIDENCE_PROGRAMMA.json` (optioneel): `{"fasen":[{"id":"P0","status":"Bezig","validatie":"…","bewijs":"…"}],
"releases":[{"project":"my_house","gecontroleerde_stand":"0.2.0","peildatum":"…","commit":"…"}],
"instructies":[{"onderwerp":"…","instructie":"…"}]}`.

**Tests.** `python -m pytest -q tools/excel/tests` (CI-job `excel`): een klein, met de hand opgebouwd test-werkboek met
dezelfde onderdelen als de afvinklijst (rij-aantallen, tabel- en validatiebereiken, Dashboard-formules en fasenblok,
databar, byte-gelijke andere bladen, idempotentie, weigeren van *Gereed*/*Geslaagd*, routering van bewijs) en een test op
de echte Excel in een tijdelijke kopie met de B03-invoer uit `docs/platform-v2/08_EXCEL/b03/`.
