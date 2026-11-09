# ADR-0007 — Besluiten D01–D18 en gates

Status: aangenomen · 2026-11-09 · fase P0 (B01-001)

## Besluit
- Model `decision`: `id`, `titel`, `wat_vastleggen`, `gate`, `status` (Open|Ingevuld|Getest|Geblokkeerd|N.v.t.),
  getypte `waarde` (pydantic-schema per besluit, `extra=forbid`), `waarde_bron` (gebruiker|meting|vast), `bewijs`
  (lijst records), `reden`, wie/wanneer ingevuld en getest, `laatste_meting`, `version` (ETag/If-Match).
- **Geen voorbeeldwaarden:** verplichte velden hebben geen standaardwaarde; plaatshouders (`<POOL>`, `TODO`,
  `x.x.x.x`, `example`, …) worden geweigerd. Alleen D10 (mini-pc uitgesloten) is vooraf `Ingevuld` als vast besluit.
  D09 dwingt `overage_toegestaan=false` en `harde_stop=true`; D14 dwingt dat de boiler alleen gemeten wordt.
- **Getest** alleen door (a) een echte meting via TrueNAS-readback (D01 versie, D02 bestaan van pools/datasets,
  D03 geslaagde aanmelding op het adres, D06 poolstatus, D07 apps) of (b) een expliciet bewijsrecord met resultaat
  `geslaagd`. D05 vereist daarnaast geregistreerde geslaagde hersteltests van een foto én een database.
  Een waardewijziging na Getest zet het besluit terug op Ingevuld.
- **NAS-adres** komt uitsluitend uit D03; zonder D03 is de TrueNAS-koppeling `not_configured`.
- **Gates** (`GET /api/v1/gates`) worden afgeleid uit besluiten + gemeten toestand (poolstatus uit de inventaris
  binnen de TTL, geverifieerde eigen back-up, executorkoppeling). Status `toegestaan|geblokkeerd|unknown`; `unknown`
  en `N.v.t.` openen nooit een gate. Er is geen override-endpoint (B12-006: gate niet weg te klikken). In P0 is de
  executor niet gekoppeld, dus `deployment`, `upgrades` en `r2_r3_acties` blijven dicht.
