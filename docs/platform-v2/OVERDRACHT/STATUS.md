# Stand bij overdracht — 9 november 2026, ±11:45 (Nederlandse tijd)

Controleer de echte stand altijd zelf in git (de oude sessie kan na dit moment nog commits hebben gepusht).

## Afstemming tussen de twee machines

- **Overdrachtsstatus: OUDE MACHINE NOG BEZIG.** Zolang deze regel er staat werkt de oude sessie nog in: ai-server-manager,
  jelly-leon-platform, jelly-leon, jelly-leon-web, jelly-leon-clients (bijgewerkt 12:00).
  Daar niets committen of pushen (alleen lezen).
- Vrij voor de nieuwe machine: home-control-hub, media-guard-ultimate, media-source-optimizer, my_house, appstore-en-fork,
  zoeken-en-persoonlijke-ai (P0 + review klaar en gepusht).
- Als de oude sessie klaar is, vervangt ze de regel hierboven door **OVERDRACHT VOLTOOID** (met tijdstip) en werkt ze
  deze STATUS.md bij met de definitieve P0-stand. Controleer met `git -C ai-server-manager pull` (bijv. elk kwartier).

## Klaar en gepusht (branch `ccr-c133d7a0-kuz1cv`)

- **Alle repos:** `docs/platform-v2/` (pakketdocs per repo), `PLATFORM_CONTRACTEN.md` 1.1, `EXCEL_TAKEN.json`.
- **Forks:** jelly-leon + jelly-leon-web met volledige upstream-historie v10.11.11; jelly-leon-clients met 4 subtrees.
- **P0 delta's (klaar, met tweede controle):**
  - media-guard-ultimate: `INVENTARIS.md` (432 routes), `DELTA_MATRIX.md` (185 rijen; tweede lezing: 177 bevestigd, 8
    weerlegd, 24 nieuw), ADR-0013/0014, EVIDENCE.json. Testbaseline: core 1069 passed / 2 skipped, encoder 124 passed.
  - media-source-optimizer: 137 rijen (129 bevestigd, 8 weerlegd, 15 nieuw), 50 echte hiaten, ADR-0001…0004.
  - my_house: 125 claims (109 bevestigd, 15 weerlegd, 14 nieuw), ADR-0001…0006.
  - Elke DELTA_MATRIX.md eindigt met een geprioriteerde bouwlijst voor P3.
- **P0 nieuwe repos (op het moment van schrijven):**
  - ai-server-manager: backend P0 klaar (12 commits: scaffold, first-start-init, auth/enrollment, wizard D01–D18 + gates,
    TrueNAS-adapter, inventaris, back-updekking, events-inbox, EVIDENCE). PWA (apps/web) werd nog gebouwd → controleer of die
    gecommit is; daarna nog de **review**.
  - appstore-en-fork: B08-001 manifeststandaard + validator gebouwd en gereviewd (review dichtte o.a. omzeiling via
    //mnt/.ix-apps; CI-run 42602759898 groen: 350 unit, 53 integratie, 2 dienst-E2E, 8 image-E2E). **P0 klaar.**
  - home-control-hub: scaffold + B13-001 gebouwd en gereviewd (fail-closed migratie bij mislukte pg_dump, 1 MiB-limiet;
    218 tests). **P0 klaar.**
  - zoeken-en-persoonlijke-ai: scaffold + B07-001 gebouwd en gereviewd (8 reparaties, o.a. geen ingetrokken bron in
    back-ups en zoekgeschiedenis). **P0 klaar.**
  - jelly-leon-platform: scaffold, TrueNAS-simulator, INSTALLATIE.md, TRUENAS_APP_API.md, CI (4 commits); review nog niet.
  - jelly-leon: FORK_STRATEGIE, INVENTARIS, bouwverificatie, CI/upstream-sync (7 commits); review nog niet.
  - jelly-leon-web: P0 werd nog gebouwd → controleren; review nog niet.
  - jelly-leon-clients: inventaris, CI per client, desktop-build in container gelukt (8 commits); review nog niet.

## Openstaande besluiten voor de gebruiker (via keuzemenu vragen)

1. **Android applicationId** van de clients: zelfde ID (vervangt de officiële app) of eigen ID (naast elkaar installeerbaar).
   Advies bouwer: eigen ID.
2. **Swiftfin 1.6.1** gebruikt een SDK voor Jellyfin-API 12.0, de server is 10.11.11 (app toont "Update to Jellyfin"):
   1.6.1 houden, terug naar 1.5.x, of jelly-leon later naar upstream 12.x (.NET 10) — zie jelly-leon-clients ADR-0009.
3. **Repos en GHCR-pakketten publiek of privé** (GPL: bron beschikbaar stellen; TrueNAS moet de image kunnen pullen —
   privé vraagt registry-login in TrueNAS).
4. Optioneel geheim `JL_SYNC_PUSH_TOKEN` (upstream-sync-branches pushen).
5. **my_house 0.2.0** is niet gepubliceerd (release-run faalde op een Gradle-download, HTTP 504): opnieuw starten?
6. Eerste GitHub Actions-runs van de nieuwe CI-workflows en release-tags `v0.1.0` (pas na akkoord: publiceren is extern).

## Contract 1.2 — nog te verwerken (uit P0-meldingen; daarna naar alle repos kopiëren)

- **Bestaande apps** (MediaGuard, MSO, my_house, Jellyfin): eigen poorten (MG 30080 + fork-poorten, MSO 38081), eigen DB
  (MG SQLite-WAL, mounts /config,/work,/data), eigen UI, eigen foutformaat op bestaande routes; contractformaat alleen op nieuwe
  routes. Hub-adapter leeft in de Hub en gebruikt hun bestaande routes met een gescopete sleutel; geen enrollment voor v1.
  my_house krijgt een alles-in-één Custom App-image (nu nog install.sh/YAML) en herstelprocedures zonder terminal (P3).
- **Enrollment:** één vastgelegd schema voor `POST /api/v1/services/enroll` (de repos kozen elk iets in hun ADR — gelijktrekken)
  en env-naam `HUB_ENROLLMENT_TOKEN`; hoe de Hub zich bij een dienst authenticeert (per-app service-token).
- **Beveiliging:** JWKS via HTTP op het LAN (pinning van de Hub-sleutel bij enrollment / HTTPS), koppelen via de statuspagina
  alleen vóór eerste koppeling + rate-limit per bron, JWT-replay (`jti` + korte cache), max. verzoekgrootte 1 MiB → 413.
- **Custom App-realiteit:** het standaardformulier (ix-app 1.4.8) verwijdert no-new-privileges/cap_drop; root → 568 vraagt
  CHOWN/SETUID/SETGID/FOWNER/DAC_OVERRIDE → images zetten zelf `PR_SET_NO_NEW_PRIVS` na de eigenaarschapsstap. Digest in het
  tagveld als `versie@sha256:…` (update-detectie TrueNAS niet geverifieerd). `app.rollback` werkt niet voor image-tags van
  custom apps → terugzetten = `app.update` met vorige waarden. Catalogustreinen houden alleen de nieuwste versie →
  "vaste versie" kan verdwijnen; plan moet dat melden.
- Manifest: `joins_platform_network` weg; `custom_app.ports` = `network.ports`; optionele GPU-parameter (`intel_render`).
- Hub: AI-runner als eigen uid (569); noodlogin (break-glass) in de Hub (B13-001 hangt ervan af); D10 = Ingevuld.

## Omgevingsbeperkingen van de oude sandbox (hier opgelost?)

- 4 CPU's → max. 2 agents per workflow; 4 workflows parallel gebruikt.
- Proxy blokkeerde: GHCR-blobs (pkg-containers.githubusercontent.com), dl.google.com + downloads.gradle.org (Android),
  invent.kde.org (mpvqt; GitHub-spiegel gebruikt), classList.js-archief (npm ci jelly-leon-web), officiële TrueNAS-docs.
  → Op de Ubuntu-machine opnieuw proberen en EVIDENCE bijwerken.
- Excel-bijwerker: `ai-server-manager/tools/excel/update_excel.py` (getest; nog niet op de echte Excel gedraaid).
