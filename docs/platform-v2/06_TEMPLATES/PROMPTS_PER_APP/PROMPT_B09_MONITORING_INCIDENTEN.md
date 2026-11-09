# Startopdracht — Monitoring & incidentrespons — volledige bouwspecificatie

Werk uitsluitend aan dit onderdeel van het TrueNAS Home Platform v2. Lees vóór je iets wijzigt:

1. `00_START/LEES_MIJ_EERST.md`
2. `01_ARCHITECTUUR/02_DATA_EIGENAARSCHAP.md`, `03_RISICO_AUTONOMIE.md`, `06_FASERING_EN_GATES.md`
3. **`02_BOUWPLANNEN/B09_MONITORING_INCIDENTEN.md` — deze volledige spec is leidend**
4. `08_EXCEL/TrueNAS_V2_Uitvoering_en_Afvinken.xlsx`, filter op de relevante app/projectcode.

Start met een actuele repository- en functie-inventaris, bestaande tests en migratiedekking; schrijf een delta-matrix **bestaand / onvolledig / ontbrekend**, prioriteer alleen hiaten. Werk strikt per F0..F6; bij iedere fase: implementatie, review, unit/integratie/E2E, fallback, echte capabilityprobe, deployment-gate, bewijs en Excel-update. Geen mocks als productieclaims. Stop bij blocker en documenteer precieze ontbrekende invoer.

## Verplichte werkstukken uit de specificatie
- B09-001 — Metrics coverage
- B09-002 — App healthchecks
- B09-003 — Time-series en alerts
- B09-004 — Logs en correlatie
- B09-005 — Out-of-band melding
- B09-006 — Operator runbooks

## Productie- en veiligheidskaders
- Alleen TrueNAS i7-14700 + Intel Arc A310/UHD 770 voor deze thuisapps. Mini-pc blijft exclusief video/andere projecten.
- Behoud MediaGuard, Media Source Optimizer, my_house en hun eigen data; integraties via gedocumenteerde, gescopeerde API's.
- Bestaande foto's en appdatabases worden offsite naar OneDrive geback-upt; valideer een echt herstel vóór mutatie. ZFS snapshots zijn aanvullend.
- Automatische acties via risk engine/executor, geen generieke AI shell/root. R2/R3 expliciete approvals, R3 destructief nooit stiekem.
- Claude Max bestaande inbegrepen API credits mogen uitsluitend als geclaimd en binnen zero overage. ChatGPT Plus is geen gratis API.

## Oplevering
Git commit(s), OpenAPI of contracten, migration/rollback, tests met link naar bewijs, versie/digest, screenshots van echte relevante schermen, hardware/driver-beperkingen, release notes, documentatie, complete go/no-go en status in Excel. Test op echte NAS alleen na autorisatie; nooit blind productieconfig aanpassen.
