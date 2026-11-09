# B03 2.0 — invoer voor de Excel-bijwerker

Invoer voor `tools/excel/update_excel.py` (Δ-ASM-EXCEL), overgenomen uit de synthese van het goedgekeurde B03 2.0-plan
(2026-11-09, aangevuld met de Emby-overname en de HARDE EIS van de gebruiker). Bouwplan:
`../../02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md`; fasering en besluiten: `B03_FASERING.md`, `B03_BESLUITEN.md`.

| Bestand | Inhoud | Optie |
|---|---|---|
| `werkpakketten.json` | 72 werkpakketrijen in exact het `tasks.json`-formaat: 66 nieuw (B03-014…079) en 6 uitgebreid (B03-004, 005, 007, 009, 010, 013; de oorspronkelijke tekst staat letterlijk vooraan) | `--werkpakketten` |
| `testen.json` | 74 testrijen JLT-01…74 in het `e2e_cases`-formaat; JLT-70…74 = overname vanuit Emby (P0) | `--testen` |
| `EXCEL_TAKEN_PER_REPO.json` | per rij en per test: in welke repo, wie uitvoert, prioriteit en startstatus van de testrij (`per_test`), de wijzigingsnotitie per uitgebreide rij (`per_rij.<ID>.wijziging`) | `--testmeta` |
| `fasen.json` | de faserij P4-0 (na P3, vóór P4) voor het blad Fasen | `--fasen` |

Dezelfde rijen staan ook in `../tasks.json` (werkpakketten) en `../e2e_cases.json` (testrijen). Startstatus: werkpakketten
*Niet gestart*; testrijen volgens `per_test.<ID>.startstatus` (de NAS-rijen JLT-06/15/26/39/49/59/69/74 *Geblokkeerd*). Nooit
*Gereed* of *Geslaagd*.
