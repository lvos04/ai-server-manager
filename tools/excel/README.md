# Excel-bijwerker

`update_excel.py` voegt alle `docs/platform-v2/EVIDENCE.json`-bestanden samen in
`docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx`. Werkt op XML-niveau zodat opmaak, tabellen,
dropdowns en de databar op 'Appoverzicht' blijven. Voegt kolommen *Validatie*, *Blokkade / opmerking*, *Bijgewerkt* toe.
Zet nooit 'Gereed'/'Geslaagd' (wordt teruggezet naar 'Bezig' met waarschuwing); bij meerdere bronnen wint de voorzichtigste status.

```bash
pip install lxml
python3 tools/excel/update_excel.py --xlsx docs/platform-v2/08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx \
  --evidence ../*/docs/platform-v2/EVIDENCE.json [--program docs/platform-v2/EVIDENCE_PROGRAMMA.json]
```
`EVIDENCE_PROGRAMMA.json` (optioneel): `{"fasen":[{"id":"P0","status":"Bezig","validatie":"…","bewijs":"…"}],
"releases":[{"project":"my_house","gecontroleerde_stand":"0.2.0","peildatum":"…","commit":"…"}],
"instructies":[{"onderwerp":"…","instructie":"…"}]}`. Er wordt een `.xlsx.bak` naast het origineel gezet.
