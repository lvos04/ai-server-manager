# Stand bij overdracht — definitief 2026-11-09 12:56 (Nederlandse tijd)

Controleer de echte stand altijd zelf in git (de oude sessie kan na dit moment nog commits hebben gepusht).

## Afstemming tussen de twee machines

- **Overdrachtsstatus: OVERDRACHT VOLTOOID (2026-11-09 12:56 Nederlandse tijd).** De oude sessie werkt nergens meer. Alle 11 repos waren
  op dat moment schoon en gepusht (geen lokale of ongecommitte wijzigingen). Alle repos zijn vrij voor de nieuwe machine.
- Volgende stap: OVERDRACHT_PROMPT.md sectie 4 — contract 1.2 verwerken, open besluiten vragen, dan P1 (script `workflows/p1.js`).

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
  - ai-server-manager: **P0 klaar** — backend (12 commits), web-UI Next.js 16-PWA met P0-schermen en Playwright op 4 breedtes
    (6 commits), review (5 commits: setupcode echt eenmalig bij gelijktijdige verzoeken, 1 MiB ook bij chunked, rate-limit op
    wachtwoord, no-new-privileges in de image zelf, key nooit naar NAS bij onvertrouwd certificaat). GitHub Actions-run
    42608437675 groen (python, web, images). ai-server-manager blijft gereserveerd tot OVERDRACHT VOLTOOID (Excel-update).
  - appstore-en-fork: B08-001 manifeststandaard + validator gebouwd en gereviewd (review dichtte o.a. omzeiling via
    //mnt/.ix-apps; CI-run 42602759898 groen: 350 unit, 53 integratie, 2 dienst-E2E, 8 image-E2E). **P0 klaar.**
  - home-control-hub: scaffold + B13-001 gebouwd en gereviewd (fail-closed migratie bij mislukte pg_dump, 1 MiB-limiet;
    218 tests). **P0 klaar.**
  - zoeken-en-persoonlijke-ai: scaffold + B07-001 gebouwd en gereviewd (8 reparaties, o.a. geen ingetrokken bron in
    back-ups en zoekgeschiedenis). **P0 klaar.**
  - jelly-leon-platform: **P0 klaar** — lifecycle-scaffold, alles-in-één image, INSTALLATIE.md (2 Custom Apps), TRUENAS_APP_API.md
    (bronnen: middleware TS-25.04.2.6/25.10.8, apps f142a16), TrueNAS-simulator (profielen 25.04/25.10, ix-app, nepcatalogus,
    weigert compose, foutinjectie), Hub-simulator, e2e/README.md. Review repareerde een **kritieke auth-bypass** (JWKS van een
    niet-gekoppelde 'Hub' werd vertrouwd) en ongeldige ci.yml. GitHub Actions nog niet waargenomen.
  - jelly-leon: **P0 klaar** — FORK_STRATEGIE, PATCHES-register, INVENTARIS, CI + upstream-sync; build 0 fouten, tests 2544/2555
    (4 falen door omgeving: geen DNS jellyfin.org / geen IPv6), OpenAPI byte-gelijk. Review: 6 reparaties. Volledige image
    (met web) kon hier niet: npm-archief classList.js geblokkeerd door de proxy.
  - jelly-leon-web: **P0 klaar** — vitest 160/160, productiebuild, smoketest fork 30/30 / stock 24/24; GitHub Actions-runs
    42610233474 en 42611569594 groen (7/7 jobs). Review: 5 reparaties.
  - jelly-leon-clients: **P0 klaar** — subtrees byte-gelijk aan upstream (mpvqt als extra subtree voor desktop, JLC-0001), CI per
    client, desktop-build in container gelukt; Android/Android TV lokaal geblokkeerd (Android SDK/Gradle via proxy),
    Swiftfin NIET GEVALIDEERD (Mac/Xcode). Review: 6 reparaties.
- **Excel** bijgewerkt (tools/excel/update_excel.py + docs/platform-v2/EVIDENCE_PROGRAMMA.json): Werkpakketten 48 Bezig /
  16 Geblokkeerd / 241 Niet gestart; Testmatrix 6 Bezig; Besluiten 17 Open + D10 Ingevuld; Fasen P0 Bezig (NAS-gate open);
  Releases bijgewerkt (MSO v1.6.0 is getagd; my_house 0.2.0 niet gepubliceerd). Nergens Gereed/Geslaagd.

## Besluiten van de gebruiker (gevraagd via keuzemenu op de nieuwe machine, 2026-11-09)

1. **Android applicationId:** eigen ID, naast de officiële app installeerbaar (geregistreerde patch: android
   `applicationId`, androidtv daarnaast `app_id` en `app_search_suggest_authority`). iOS: eigen bundle-id (NIET GEVALIDEERD
   (Mac/Xcode)). **Gebouwde ID's** (bron: alleen de bouwopdracht van ronde 2, "het voorbeeld uit ADR-0004 dat de
   gebruiker in het keuzemenu koos"; bevestiging gevraagd, contract 1.3 §1.2): android `org.jellyfin.mobile.jellyleon`,
   androidtv `org.jellyfin.androidtv.jellyleon`, Swiftfin (voorstel) `org.jellyfin.swiftfin.jellyleon`. Regel sinds
   contract 1.3: nooit een ID, accounttype, authority, permissie, `app_search_suggest_*` of sharedpref-naam gelijk aan
   die van een officiële app.
2. **Swiftfin:** 1.6.1 blijft; de **server gaat naar de nieuwste stabiele Jellyfin 12.x (.NET 10) vóór P4**, zodat B03 direct
   op 12.x gebouwd wordt (jelly-leon + jelly-leon-web; Android-clients op 12.x-compatibiliteit controleren).
3. **Zichtbaarheid:** alle repos en GHCR-images **publiek**, pas na een scan van de volledige historie op geheimen en
   privégegevens (bevindingen eerst aan de gebruiker voorleggen).
4. **`JL_SYNC_PUSH_TOKEN`:** de gebruiker wil dat de bouwer dit regelt. Een fine-grained token kan alleen via de GitHub-web-UI;
   het alternatief (SSH-deploysleutel met schrijfrecht per fork als repo-geheim) vraagt nog uitdrukkelijke toestemming in de
   sessie — staat open.
5. **my_house 0.2.0:** release opnieuw starten (mag).
6. **Releases:** release-tags `v0.1.0` voor de nieuwe repos (images naar GHCR met digests) zodra hun CI groen is (mag).
7. **Ontwerptaal (nieuw):** één eigen ontwerptaal op Tailwind 4 + shadcn/ui + lucide, ontworpen door een aparte
   design-agent in de workflows (ontwerpstap vóór en ontwerpreview ná elke UI-bouwstap), voor de Hub-UI (P0-UI wordt omgezet),
   de statuspagina's van de nieuwe diensten en het **uiterlijk** van MediaGuard, MSO en my_house (functies/routes blijven).
   Jelly Leon web/clients vallen erbuiten. De design-agent beslist zelfstandig; resultaat wordt achteraf getoond.

## Vervolgbesluiten van de gebruiker (2026-11-09, middag)

- **Ontwerptaal Peil** (bron: `docs/platform-v2/ONTWERPTAAL.md` + `design/ontwerptaal/`, ADR-0015): productnaam in de Hub
  "TrueNAS Home Platform"; rol kind ziet Home · Kijken · Zoeken · Ik; in MediaGuard/MSO/my_house mogen een link "Terug naar de
  Hub", een themaknop (my_house) en een tabelweergave bij grafieken (MG/MSO) erbij; ook de native Android-apps van MediaGuard en
  my_house krijgen Peil; my_house fase 2 op Tailwind 4 + shadcn in de React 18-variant.
- **Openbaarheid** (na de scan van alle historie): 10 repos publiek; media-guard-ultimate niet (echte NAS-rapporten, volledige
  naam, LAN-adressen in de historie) → huidige repo wordt `media-guard-ultimate-archief` (privé), een nieuwe publieke
  `media-guard-ultimate` met schone historie volgt na de Peil-ronde. De openbare sideload-signingsleutel van MediaGuard blijft
  (bewuste keuze, risico geaccepteerd). Licentie voor de eigen repos: **GPL-3.0** (forks houden hun upstream-licenties).
- **my_house 0.2.0** is gepubliceerd (release-run opnieuw gestart, alle jobs groen).
- **B03 uitgebreid** met zes functies (Watch Together, aanbevelingen, NL-ondertitelvertaling, mediakwaliteitscontrole,
  apparaatprofielen, intro/outro/recap); plan en Excel-rijen zijn verwerkt (zie "B03 2.0 verwerkt" hieronder).
- **Sync-token** (`JL_SYNC_PUSH_TOKEN`): nog open — fine-grained token alleen via de GitHub-web-UI; deploysleutels aanmaken vraagt
  uitdrukkelijke toestemming in de sessie.

## B03 2.0 verwerkt (2026-11-09, avond)

- **Plan (goedgekeurd door de gebruiker):** `02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` versie 2.0 (versie 1 letterlijk
  behouden; hoofdstukken 8–19 en bijlagen nieuw; 72 werkpakketten: 66 nieuw B03-014…079 en 6 uitgebreid B03-004/005/007/
  009/010/013; 74 testrijen JLT-01…74), `B03_FASERING.md` (P4-0, golven 0–4, gates, prioriteiten) en `B03_BESLUITEN.md`
  (genomen besluiten bovenaan, open besluiten per fase/golf). Overgenomen in `OVERDRACHT_PROMPT.md` §2/§4 en
  `01_ARCHITECTUUR/06_FASERING_EN_GATES.md` (fase P4-0, P4/P5 aangevuld, nieuwe gates). ADR's die platform en Hub raken:
  ADR-0016 (foutcatalogus), ADR-0017 (Hub-koppeling/privacy), ADR-0018 (MediaGuard-grens + Δ-MG-DUAL), ADR-0019
  (optionele model-apps), ADR-0020 (HARDE EIS en Emby-overname). De overige ADR-voorstellen (ADR-B03-01…04, 07, 08, 10–12)
  horen bij de forks.
- **HARDE EIS van de gebruiker (letterlijk):** alle kijkgeschiedenis (gezien-status, hervatpunten, favorieten,
  beoordelingen, onthouden spoorkeuzes, gebruikers, rechten) en de MediaGuard-voortgang blijven altijd beschikbaar.
  Geen cutover zonder vóór/na-rapport per gebruiker en uitdrukkelijk akkoord van de gebruiker op elk verschil (ook door
  upstream-migraties); de bestaande installatie blijft ongewijzigd als terugval. Elke MediaGuard-release (ook de eerste uit
  de nieuwe publieke repo) bewijst een upgrade op een gevulde database van de vorige versie zonder gegevensverlies.
  Staat in bouwplan §10.9 en B03-015 (acceptatie) en in ADR-0020.
- **Emby (gebruiker):** de huidige mediaserver is **Emby**; de kijkgeschiedenis staat daar. "Het belangrijkste is mijn
  kijkgeschiedenis; als alles werkt verwijder ik Emby." Daarom: B03-015 = "Overname vanuit de bestaande mediaserver (Emby;
  ook Jellyfin als D07 dat meet)", prioriteit P0 en al in golf 0 tegen stock 12.4 met een echte Emby-container
  (`emby/embyserver:4.10.2.0@sha256:7082c63b…65cc1`, stabiel op 2026-11-09); alleen lezen uit Emby; koppelen op
  provider-ID's en pad met een afhandellijst; doel 100 % van gezien-status en hervatpunten; eerst JellyPlex-Watched (GPL-3.0)
  beoordelen. Nieuwe testen JLT-70…74 (P0; JLT-74 echte NAS = Geblokkeerd). Δ-MG-AUTH wordt per server (Emby houdt
  `X-Emby-Token`) en nieuw Δ-MG-DUAL: MediaGuard volgt Emby én Jelly Leon; de Emby-koppeling onderbreekt nooit. Controlelijst
  "Emby verwijderen" (bouwplan §10.9.2); de gebruiker verwijdert Emby zelf. APP-02 en I26-26-02 blijven gelden.
- **Genomen BG-besluiten (2026-11-09, keuzemenu):** BG-01 MediaGuard naar `Authorization: MediaBrowser Token=…`
  (Δ-MG-AUTH), legacy-auth blijft uit, derden-apps eerst testen; BG-02 geen release meer op 10.11.11, eerste Jelly
  Leon-release op 12.x, P4-0 als eigen fase (rij op het blad Fasen); BG-32 Intro Skipper alleen als ongewijzigde
  vergelijkingsbasis in een testcontainer, externe segmentdatabases uit, bestaande segmenten eenmalig als hint met
  voorbeeld; BG-34 de gebruiker (of een aangewezen persoon) labelt de echte afleveringen, met een eenvoudig labelscherm;
  BG-37 MovieLens en Pioneer One alleen lokaal, eenmalige evaluatie op de echte kijkhistorie (na B03-039; samengevat,
  afmelden kan, kinderen nooit), TMDb in een wegwerpcontainer, geen Netflix-masters zolang de schijf vol is; BG-38
  tijdelijke meetdata opgeruimd, testsets on demand, Android-images blijven, de gebruiker van de bouwmachine in de groepen render en kvm.
- **Later te vragen (per fase/golf; tot dan geldt de veiligste stand):** P4-0 (overname): BG-22 · vóór golf 1: BG-03,
  BG-04 · na golf 1: BG-07 · golf 2: BG-16, BG-27, BG-33, BG-35, BG-36 · vóór golf 3: BG-05 · golf 3: BG-10, BG-11,
  BG-13, BG-14, BG-19, BG-21, BG-23, BG-24, BG-25, en vóór B03-027 BG-09 · vóór golf 4: BG-08 · golf 4: BG-12, BG-15,
  BG-26, BG-28, BG-29, BG-30, BG-31 · bij B03-006: BG-17 · vóór P5: BG-06, BG-18 · P5: BG-20. Zonder BG-ID: akkoord op
  elk verschil per gebruiker (bij elke overnamerun), nieuw wachtwoord of SSO per gebruiker (vóór de echte overname), Emby
  uit (na JLT-74 en de controlelijst).
- **Excel (Δ-ASM-EXCEL opgeleverd):** `tools/excel/update_excel.py` voegt werkpakketten, testrijen en faserijen toe op
  XML-niveau (tabellen, dropdowns, voorwaardelijke opmaak, databar en Dashboard-formules lopen mee; idempotent; weigert
  Gereed/Geslaagd), met pytest op een klein test-werkboek en op de echte Excel (CI-job `excel`). Invoer:
  `08_EXCEL/b03/`. Brondata: `tasks.json` (439 rijen), `e2e_cases.json` (124), `EXCEL_TAKEN.json` van deze repo (+10
  B03-rijen, +5 testrijen). Werkboek na de B03-rijen en de EVIDENCE-samenvoeging: Werkpakketten 371 (48 Bezig / 21
  Geblokkeerd / 302 Niet gestart), Testmatrix 124 (9 Bezig / 8 Geblokkeerd / 107 Niet gestart), Besluiten 18 (17 Open /
  1 Ingevuld), Fasen 8 met P4-0 tussen P3 en P4 (P0 Bezig, rest Niet gestart). Nergens Gereed of Geslaagd.

## Contract 1.3 — inventaris (2026-11-10)

- `docs/platform-v2/CONTRACT_1.3_KANDIDATEN.md`: alle 151 meldingen uit ronde 2 plus de ADR's/EVIDENCE van alle repos
  sinds 1.2, de B03-delta's, de besluiten van de gebruiker, de P1-uitbreidingen van de Hub en de Peil-reviews,
  ontdubbeld in 74 groepen: 36 contractwijziging (met tekstvoorstel en geraakte repos), 8 al opgelost, 12 repowerk,
  2 afgewezen, 16 Peil-zaken (voor Peil 1.1.1). Contract 1.2 blijft bindend tot 1.3 is vastgesteld.
- Open besluiten die de inventaris oplevert: §8 van dat document (o.a. BG-05, BG-06, 100.64.0.0/10, bevestiging van
  de Android-ID's en de Swiftfin-bundle-id, GHCR-pakket van de nieuwe MediaGuard-repo).

## Contract 1.3 — vastgesteld (2026-11-10)

- `docs/platform-v2/PLATFORM_CONTRACTEN.md` is nu **`contracts 1.3`** (wijzigingslog 1.2 → 1.3 bovenaan, 36 punten,
  één per contractgroep A01–A36 uit de inventaris, plus de keuzes K1–K9). Keuzes en motivering:
  `docs/adr/ADR-0027-contract-1-3.md`. Per repo (alle 11) de concrete wijzigingen met bestanden en moment (NU of
  P2/P3/P4-0/P4/P5): `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md` (121 punten met ID `C1.3-<REPO>-<nn>`, na de
  review).
- Belangrijkste keuzes: `Host`-beperking tegen DNS-rebinding aangenomen; `servers[]` naast de bestaande velden van de
  MediaGuard-status; MediaGuard-acties via de Hub gereserveerd tot BG-05 en P3-02; strengste herkomstregel
  (`same-origin`, exacte `Origin`, `Sec-Fetch-Site`) voor alle statuspagina's; vingerafdruk over alle policy-sleutels
  (nieuwe testvector `HN69-2PHK-XV2D-X85W`); bounding set verplicht leeg bij start als root; Emby alleen lezen en
  HARDE EIS in §2.3; licentie GPL-3.0.
- **Nog niet** naar de andere repos gekopieerd (volgende stap van de orkestratie, C1.3-ALG-01) en nog nergens in code
  doorgevoerd; let op: media-guard-ultimate, media-source-optimizer en my_house hebben nog een kopie van **1.1**.
- Open besluiten (contract §1.2): BG-05, BG-04, BG-06/BG-18, `100.64.0.0/10` voor de noodlogin, bevestiging van de
  Android-ID's en de Swiftfin-bundle-id, GHCR-pakket van de nieuwe MediaGuard-repo, `JL_SYNC_PUSH_TOKEN`.

## Contract 1.3 — onafhankelijke review (2026-11-10)

- Blijft `contracts 1.3` (nog nergens gekopieerd); dertien correcties RV1–RV13 in het wijzigingslog, motivering in
  `docs/adr/ADR-0028-review-contract-1-3.md`. Belangrijkste: MediaGuard mag zijn bestaande Emby-koppeling houden
  (bibliotheek bijwerken na een vervanging) — de rest van het platform schrijft nooit in Emby; de HARDE EIS geldt ook
  voor upgrades met databasemigraties (10.11 → 12.x en later); geen kijkgedrag via de MediaGuard-adapter in de Hub;
  formulier-POST's van statuspagina's zijn met reden uitgezonderd van `Idempotency-Key`.
- Gemeten met de GitHub-API (alleen lezen, 2026-11-10): de nieuwe `lvos04/media-guard-ultimate` is publiek met één
  startcommit (schone historie) en `media-guard-ultimate-archief` is privé, dus alle 11 repos zijn publiek. Het
  GHCR-pakket `mediaguard-core` kon niet gelezen worden (geen leesrecht op pakketten): koppeling en zichtbaarheid
  blijven open (contract §1.2); tot dan geen nieuwe MediaGuard-release.
- Conformiteitslijst gecorrigeerd en aangevuld (121 punten). Alles alleen gelezen en met tests gecontroleerd; niets op
  een echte NAS, met echte accounts of op echte hardware.

## Contract 1.3 — toegepast in de Hub en de executor (2026-11-10)

- Alle punten die hoofdstuk 1 van `CONTRACT_1.3_CONFORMITEIT.md` als **NU** markeert, zijn gebouwd en Sim-getest
  (ADR-0029): C1.3-ASM-01…14, -16 en -23, plus de bronpin van het contract (C1.3-ALG-01) en Peil 1.1.1 (statuspagina
  van de executor, tokens en componentregels van de Hub-UI). Details per punt in `EVIDENCE.json`.
- **C1.3-ASM-17** (onafhankelijke review, 2026-11-10): nu C1.3-ASF-08 gecommit is, staan `healthcheck.monitor` (op
  `/readyz`) en `accepted_findings: digest_pending_release` in beide eigen manifesten; `--strict` geldig met de
  validator van appstore-en-fork op 7b3159d, ook als CI-job `manifest`.
- **Open:** C1.3-ASM-18…22 horen bij P2, P3, P4-0, P4 en P5. De overgangen `payload.severity` en de oude jobs-checknamen vervallen in de release na 0.1.x.
- Gevolg voor andere repos: `items`, `events` en `evidence` van de Hub-connector geven diensten nu 403
  `scope_ontbreekt` (gemeten: geen dienst leest ze); events buiten het eigen domein of met andere werkwoorden dan §7
  maken geen incident meer.
- Niets op een echte NAS, met echte accounts of op echte hardware gevalideerd.

### Onafhankelijke review van de conformiteitsronde (2026-11-10)

- Alles opnieuw gedraaid zoals de CI: lint en typecheck, pytest (830), migraties heen en terug, OpenAPI-drift,
  pip-audit, web (eslint, tsc, vitest, Playwright-E2E 180, Peil-review 0 harde bevindingen), Excel-bijwerker, beide
  images met de rooktest. Contract en Peil-kopieën byte-gelijk aan de bron.
- Gerepareerd: C1.3-ASM-17 afgerond (monitorplan op `/readyz`, `accepted_findings`, GPL-3.0, test en CI-job met de
  validator van appstore-en-fork); de executor gaf een kale 500 bij een formulier met te veel velden (nu 413 met vaste
  melding); docs verwezen nog naar contract 1.2.
- Nog open (bewust, met reden in `EVIDENCE.json`): "Geïmporteerd" voor `adopted` in de catalogus (C1.3-ASM-16) en
  Peil E15 in de Hub-UI (C1.3-ALG-05).

## Nieuwe machine (vanaf 2026-11-09 12:56)

- Ubuntu-ontwikkelmachine (geheugen is de grens voor parallelle builds), Docker 29 (systeemdaemon), PostgreSQL 16.15 +
  pgvector 0.8.7 (PGDG, alleen 127.0.0.1), python3.12 (deadsnakes), Node 22, pnpm 10, Java 21, .NET 9 via image,
  Android SDK (platform 36, build-tools 36.0.0), Playwright-Chromium, actionlint. Geen proxy of eigen CA meer.
- Workflow-scripts `workflows/p0.js` en `p1.js`: `OMGEVING:` aangepast aan deze machine, werkmap `<WERKMAP>`,
  filter per repo (`args.keys`), `git pull --rebase` vóór elke push, `flock` voor Gradle-, image- en stackbuilds, commits
  eindigen met alleen de Co-Authored-By-regel van de sessie.
- CI-stand bij overname (GitHub Actions, branch `ccr-c133d7a0-kuz1cv`): rood in jelly-leon (setup-dotnet vindt SDK 9.0.0 uit
  global.json niet), jelly-leon-platform (4 Ruff-fouten) en zoeken-en-persoonlijke-ai (rooktest alles-in-één image);
  home-control-hub werd in P1 gerepareerd. Deze P0-hiaten worden eerst afgemaakt.

## Contract 1.2 — verwerkt in `PLATFORM_CONTRACTEN.md` (`contracts 1.2`, 2026-11-09)

- Vastgesteld in `ai-server-manager` met `CONTRACT_1.2_CONFORMITEIT.md` (wat elke repo moet veranderen) en
  `docs/adr/ADR-0011-contract-1-2.md` (keuzes). **Nog niet** naar de andere repos gekopieerd (volgende stap) en
  nog nergens in code doorgevoerd. De punten hieronder waren de invoer.
- **Onafhankelijke review (2026-11-09):** `docs/adr/ADR-0012-review-contract-1-2.md`. Blijft `contracts 1.2`
  (sectie "Correcties uit de onafhankelijke review" R1–R12): `app_id` vast per image, `pending` naast `state`, strikte
  JWK-regels, rotatie zonder buitensluiten en zonder automatische rotatie (R2), 401 pas na `services/self` als
  intrekking, sleutelrotatie per doel, vaste `reason`-tabel, geen `action_id` voor koppelbeheer, TrueNAS-uitspraken
  als bronwaarneming, ook PID 1 niet als root, executor-bewijs tegen vastgelegd NAS-adres. Conformiteitslijst
  bijgewerkt naar de echte stand per repo (commits genoemd). Eigen reparaties: `deploy/smoke.sh` controleert nu ook
  `CapEff`, EVIDENCE.json D01–D18 volgens §11 + test.
- **Contract 1.2 toegepast in ai-server-manager (2026-11-09, ADR-0013):** Hub H1–H4 (enroll-schema exact, herhaling,
  `services/self`, rotatie na eerste gebruik, rotatie aanvragen 202, dienst-JWT, `key-rotations` leeg), H6-backend
  (noodlogin met TOTP), H5/H14-backend (ontkoppelen via de dienst, sleutelset kopiëren, TrueNAS-appnaam bevestigen),
  H7-deel (executor koppelt met koppelcode + vingerafdruk, pinning, inkomende JWT-controle; schrijfkey en ontkoppelen
  op de executor in P2), H8 (manifesten, gecontroleerd met de validator M1–M6 van appstore-en-fork) en H9
  (Custom App-tag met digest). Niet gedaan: UI-schermen "Diensten" en "Noodaccount" (wachten op de ontwerpstap, §13),
  H10/H11 (P2/P3), H12 (ontwerptaal nog niet in de repo), H13 (open punt). De diensten kunnen nu tegen de echte Hub
  testen; Sim-getest, niets op een echte NAS.
- **Onafhankelijke review van contract 1.2 in ai-server-manager (2026-11-09, ADR-0014).** Gerepareerd:
  - 1 MiB vóór routering en aanmelding, ook chunked: de Hub gaf eerst 401/405 en de executor had geen grens voor
    chunked verzoeken;
  - in de executor een persistente `jti`-replaycache, een verplichte `Idempotency-Key` en de rol `admin` op `unlink`;
  - de rol `kind` wint nu altijd, en een `iat` in de toekomst wordt geweigerd;
  - een CI-stap (controle na downgrade) die nooit kon falen;
  - via de webpoort werd een chunked upload > 1 MiB vaak `502` in plaats van `413`; de Node-doorgang telt nu zelf.

  Daarnaast negatieve tests toegevoegd, onder meer: koppelen na de eerste koppeling met een oude formuliercode, en een
  verlopen executor-koppelcode. Sim-getest; niets op een echte NAS.
- CI-stand na de P0-afronding (gezien in de review): groen in jelly-leon, jelly-leon-platform,
  zoeken-en-persoonlijke-ai, home-control-hub, appstore-en-fork, jelly-leon-clients en jelly-leon-web.


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
- Excel-bijwerker: `ai-server-manager/tools/excel/update_excel.py` — sinds 2026-11-09 ook rijen toevoegen (Δ-ASM-EXCEL);
  getest op een test-werkboek en op de echte Excel (CI-job `excel`).

## Besluiten van de gebruiker na contract 1.3 (2026-11-10)

- **Noodlogin (A07):** alleen vanaf het thuisnetwerk (RFC 1918 / fc00::/7). `100.64.0.0/10` (Tailscale/CGNAT) telt niet
  als privé; een beheerder kan het later in de Hub-UI expliciet toestaan (audit + waarschuwing).
- **App-ID's (A02) bevestigd:** `org.jellyfin.mobile.jellyleon` (Android), `org.jellyfin.androidtv.jellyleon` (Android TV),
  `org.jellyfin.swiftfin.jellyleon` (iOS/tvOS; NIET GEVALIDEERD (Mac/Xcode)).
- **BG-04 — MediaGuard-sleutel van Jelly Leon: via de Hub.** De Hub beheert de (alleen-lezen, gescopete) MediaGuard-sleutel
  in de eigen vault; Jelly Leon krijgt alleen wat nodig is — bij voorkeur zonder sleuteloverdracht (Jelly Leon vraagt de
  MediaGuard-gegevens via de Hub met een dienst-JWT). Vraagt de Hub-koppeling van de Jelly Leon-plugin (JL4, golf 1); tot
  dan `mediaguard: onbekend`.
- **Extra's (C09):** de Android-app van MediaGuard krijgt ook en-US; my_house krijgt een tabelweergave + toetsenbordbediening
  bij de grafiek "Laatste 24 uur".
- Nog open: BG-05 (vóór golf 3), BG-06/BG-18 (vóór P5), GHCR-pakketrechten MediaGuard (gebruiker), `JL_SYNC_PUSH_TOKEN`.

## Uitvoeringsplan P2 tot en met P6 en de stand na ronde 3 (2026-11-11)

- Bouwronde 3 is op 2026-11-11 afgebroken op verzoek van de gebruiker. De stand per repo (wat gepusht is, wat niet is
  gereviewd, wat als half werk niet-gecommit in de werkmap staat) staat in `UITVOERINGSPLAN/STAND_RONDE3.md`.
- Voor het vervolg is een uitvoeringsplan voor een regisseur met subagents geschreven: `UITVOERINGSPLAN/` (begin bij
  `00_LEES_EERST.md`). Stand 2026-11-11 12:05: afgemaakt en gecontroleerd (per bestand een eigen controle, drie rondes
  kruismeldingen en een droogloop; zie `UITVOERINGSPLAN/LEESMIJ.md`). Besluiten van de gebruiker van 2026-11-11 (Z-04, Z-05,
  C-11, C-12, Z-17, Z-19, Z-20) staan in `UITVOERINGSPLAN/BESLUITEN_EN_BLOKKADES.md` kop 1.5; de vastlegging in de
  besluitendocumenten volgt in stap S-P2-005.
- Het werkexemplaar met de bijgehouden voortgang staat op de bouwmachine in `<WERKMAP>/.lokaal/plan/uit`.

## Besluiten van de gebruiker van 2026-11-11 (keuzemenu)

Genomen via een keuzemenu van de regisseur op 2026-11-11; vastgelegd in stap S-P2-005. Geen van deze besluiten is een
BG-besluit, dus ze staan niet in `02_BOUWPLANNEN/B03_BESLUITEN.md`. Menu's, opties en gevolgen per stap:
`UITVOERINGSPLAN/BESLUITEN_EN_BLOKKADES.md`, kop "1.5 Besluiten uit het keuzemenu van 2026-11-11" en de kop per besluit.

- **Z-04 — Afwijkende attributieregels in oude commits (10:44).** Vraag: "In de commits tot en met 10 november staat
  een attributieregel met een modelnaam erin. Dat botst met de regel 'geen modelnaam in commits'. De historie aanpassen
  kan alleen met een force-push, en die is verboden. Wat wil je?" Antwoord: "Laten staan; alleen nieuwe commits volgen
  de regel." Gevolg: de historie wordt niet herschreven en er komt geen force-push; nieuwe commits eindigen met de vaste
  attributieregel zonder modelnaam.
- **Z-05 — Testwaarde met de vorm van een echt GitHub-token (10:44; omvang 11:47).** Vraag: "In een test van
  jelly-leon-web staat een nepwaarde die de vorm van een GitHub-token heeft. Mag die worden vervangen door een neutrale
  testwaarde?" Antwoord: "Ja, vervangen in een nieuwe commit" (de historie blijft ongewijzigd, zie Z-04); omvang
  (11:47): "test + ADR-0010 samen in één commit". Uitgevoerd in jelly-leon-web, commit `b586db650`
  (`tools/jelly-leon-web/tests/test_sync_workflow.py` en `docs/adr/ADR-0010-contract-1-2.md`); CI-run 43006625770
  (Jelly Leon Web CI) op die commit: success.
- **C-11 — Anonieme toegang tot de Node-RED-editor (10:52).** Onderwerp van de vraag (de letterlijke menutekst is niet
  bewaard): jelly-leon-platform (`install/manifests/node-red.manifest.yaml`, ADR-0023 besluit 4) staat anoniem alleen
  lezen toe, terwijl home-control-hub voor B11-001 eist dat een lezer zonder aanmelding 401 krijgt (controle
  `anoniem_geweigerd`). Antwoord: "Geen anonieme toegang; de editor is alleen bruikbaar via een beheerder. Het
  manifest/ADR-0023 in jelly-leon-platform wordt aangepast; home-control-hub houdt zijn controle." Gevolg: het manifest,
  de rooktest, de repotest en ADR-0023 in jelly-leon-platform krijgen een negatieve test (anonieme aanvraag → 401);
  home-control-hub houdt `anoniem_geweigerd` op 401. Zonder beheerder is de editor dicht tot C-12 is uitgevoerd.
- **C-12 — Hoe krijgt Node-RED een beheerder en een dienstaccount? (11:25).** Vraag: "Node-RED heeft na jouw besluit
  (geen anonieme toegang) een beheerder nodig, en home-control-hub een eigen dienstaccount om mee te lezen.
  home-control-hub kan nu formulierargumenten maken met die twee accounts en een sleutel voor de versleuteling. Het
  contract verbiedt geheimen in het Custom App-formulier. Hoe regelen we de accounts?" Antwoord (optie 1, "Voorziening
  zonder geheim"): de manifeststandaard (appstore-en-fork) krijgt een voorziening voor een beheerder en een dienstaccount
  zonder geheim in het Custom App-formulier; het profiel van home-control-hub (`build_profile` / `define_arguments` /
  `credentialSecret`) vervalt of wordt daaraan gelijkgetrokken. Gevolg: geen uitzondering in contract kop "3.1
  Uitgangspunten" (dat was optie 2). Eerst een ontwerp-ADR in appstore-en-fork, daarna de bouw in P3 (appstore-en-fork,
  jelly-leon-platform en home-control-hub, elk een eigen stap). Stelt dat ontwerp-ADR een wijziging van contract kop 3.1
  of kop 9 vast, dan komt die contractronde vóór de gate van P2.
- **Z-17 — Zigbee2MQTT in of naast de image van my_house (11:25).** Vraag: "my_house wordt één standaard Custom App met
  één image. Zigbee2MQTT, het programma dat de Zigbee-USB-stick bedient, kan op twee manieren mee. Of het
  TrueNAS-formulier op jouw NAS een USB-apparaat aan een app kan doorgeven, is nog niet getest. Welke manier wil je?"
  Antwoord (optie 1, variant a): "Zigbee2MQTT IN de image van my_house, optioneel (alleen aan als in het formulier een
  USB-apparaat is opgegeven)". Gevolg: in P3 komt Zigbee2MQTT als optioneel proces in de image en de bewaker van
  my_house; zonder doorgegeven USB-apparaat start het niet en is dat geen fout. MQTT blijft alleen binnen de container
  luisteren. Hoe het manifest de optionele stick vastlegt, is nog open (Z-21); zonder dat besluit krijgt het manifest
  geen apparaat. Werken met echte Zigbee-hardware blijft NIET GEVALIDEERD (hardware).
- **Z-19 — "Module uit": 404 of 501 (11:25).** Vraag: "Als een module van Jelly Leon uit staat, wat krijgt een
  aangemelde gebruiker dan terug op de routes van die module? De pluginlaag geeft nu 404 ('niet gevonden'). De
  werkpakketten B03-033 en B03-035 vragen 501 `capability_unavailable` ('functie niet beschikbaar'). Wie niet is
  aangemeld krijgt in beide gevallen 401." Antwoord (optie 1): "'module uit' geeft 404 zoals ADR-0030; afwijking van
  WP-JSON in het bewijs vermelden". Gevolg: geen herstelstap in jelly-leon (ADR-0030 van jelly-leon, punt 2, blijft
  gelden). In deze commit staat de acceptatie van B03-033 en B03-035 in `08_EXCEL/b03/werkpakketten.json` (en dezelfde
  rijen in `08_EXCEL/tasks.json`) op 404. Het bouwplan `02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md`, kop "F2.5.1
  Algemene regels", noemt bij "Module uit" nog 501; dit besluit gaat voor.
- **Z-20 — Zes B03-werkpakketten zonder golf (11:25).** Vraag: "Volgens het fasedocument hoort bij P4 ook scene search,
  live-tv/DVR en offline apps waar haalbaar. In de golfplanning van B03 2.0 hebben zes oudere werkpakketten geen plek:
  universele bibliotheek, beschikbaarheid van clients, metadata en anime-mapping, semantische scènezoeker, offline
  downloaden en live-tv/DVR. Wat doen we ermee? Je mag per werkpakket anders kiezen." Antwoord (optie 1, voor alle zes):
  "B03-002, -003, -006, -008, -011, -012 IN P4 BOUWEN (per werkpakket eerst A-VERKEN, dan stappen in een golf)".
  Gevolg: golf 3 krijgt B03-006 (stappen S-G3-28 en S-G3-29; BG-17 wordt vóór S-G3-28 voorgelegd), B03-002 (S-G3-30;
  S-G3-31 alleen als de verkenning van S-G3-30 een webdeel noemt) en B03-003 (S-G3-32); golf 4 krijgt B03-008 (S-G4-49
  en S-G4-50; in P4 alleen zoeken in de tekst van ondertitelcues, spraak en embeddings wachten op BG-06), B03-011
  (S-G4-51 en S-G4-52) en B03-012 (S-G4-53 en S-G4-54). Stappen: `UITVOERINGSPLAN/STAPPEN_P4_GOLF3_4.md`. Vastgelegd
  in `02_BOUWPLANNEN/B03_FASERING.md` kop "3. Golven en werkpakketten" en in `08_EXCEL/b03/werkpakketten.json` (en
  dezelfde rijen in `08_EXCEL/tasks.json`). Delen die de echte NAS of echte apparaten vragen (bijvoorbeeld een
  live-tv-tuner) blijven NIET GEVALIDEERD (echte NAS) tot P6.
- **Vault-verwijzingen ook voor Custom Apps (12:00, bij stap S-P2-500 in appstore-en-fork).** Vraag (uit de verkenning
  van die stap): krijgt ook een Custom App de vault-verwijzing (`custom_app.env[].value_from` naar een geheim dat de Hub
  maakt), of alleen de `values` van een catalogusapp? Antwoord: "vault-verwijzingen ook voor Custom Apps (env), niet
  alleen catalogusapps". Gevolg: dit botst met contract kop "3.1 Uitgangspunten" ("Nooit geheimen in het Custom
  App-formulier"; punt (a) noemt alleen catalogusapps). Daarvoor is een uitzondering in het contract nodig, in een eigen
  contractronde in deze repo met de kopieën in alle repos; het contract is bij dit vastleggen niet gewijzigd. De
  executor vult zulke verwijzingen nog niet in (ADR-0030 besluit 28: eerlijk `501 capability_unavailable`).

## Start van P3 terwijl Gate P2 nog open is (2026-11-16)

Vastgelegd door de regisseur op 2026-11-16, zoals `UITVOERINGSPLAN/STAPPEN_P3.md` kop "2.1 Gate ervoor (P2 naar P3)"
vraagt ("mogen wel starten zodra de regisseur dat vastlegt in STATUS.md").

- **Gate P2: NOG NIET gehaald.** Stap S-P2-910 (de gate-controle van A-GATE, `UITVOERINGSPLAN/STAPPEN_P2.md`) staat
  open. Deze kop is dus geen afvinking van Gate P2; die komt pas met S-P2-910.
- **Wat wel start (vanaf 2026-11-16):** alleen de P3-stappen die alleen lezen of alleen de eigen app raken (geen
  schrijven via de Hub, geen executor), volgens de lijst onder kop 2.1 van `STAPPEN_P3.md`.
- **Wat niet start:**
  - S-P3-110, S-P3-120 en S-P3-130 (schrijven via de Hub): pas na Gate P2, met "Risk policy + privileged executor
    tested" in de simulator aangetoond.
  - S-P3-010 (ai-server-manager) en S-P3-300 (home-control-hub; wacht op het ADR van S-P3-010): niet zolang de baan
    `ai-server-manager` van P2 loopt. In één repo werken nooit twee schrijvers tegelijk.
- **Nulmeting S-P3-000:** afgevinkt op 2026-11-16. Het dossier staat lokaal op de bouwmachine en hoort niet in de repo.
- **Contract:** blijft 1.3 tijdens P3 (V-018), met één uitzondering: de geplande contractronde van C-12. Die komt vóór
  de P3-schrijvers in appstore-en-fork. Een contractwijziging is nooit een losse stap van A-BOUW.

## Besluiten van de gebruiker (2026-11-23)

- **Afvinken door de gebruiker blijft staan (keuzemenu van de regisseur, stap S-P6-52).** Vraag: wat doet het
  Excel-gereedschap (`tools/excel/update_excel.py`) met een "Gereed" of "Geslaagd" die de gebruiker zelf in de Excel
  heeft gezet, als een volgende run voor die rij bewijs uit een `EVIDENCE.json` verwerkt? Antwoord: optie 1 "Laten
  staan". Het gereedschap laat een handmatige "Gereed"/"Geslaagd" in de statuscel staan, meldt die rijen in zijn
  uitvoer (lijst `handmatig_afgevinkt`) en waarschuwt als het bewijs voor zo'n rij "Geblokkeerd" of "Mislukt" meldt
  (tegenstrijdig bewijs). Het gereedschap en geen enkele agent zet zelf ooit "Gereed" of "Geslaagd"; dat blijft alleen
  de gebruiker. Niet gekozen: optie 2 (geen wijziging; de gebruiker vinkt pas af na de allerlaatste run) en optie 3
  (iets anders). Geen BG-besluit; het contract (§1.1, §1.2) wordt niet geraakt.

## P2 — veilig automatiseren: gebouwd en in de simulator getest (2026-11-24)

### Wat er per repo staat

| Repo | Stappen | Resultaat op de werkbranch |
|---|---|---|
| ai-server-manager | S-P2-005 t/m S-P2-220 | De Hub toont voorstel, diff en goedkeuring. De executor toetst het verzoek opnieuw en leest de uitvoering terug. De simulator dekt onder meer appbeheer, back-upgates en flowverzoeken. Het monitorplan en de P2-schermen zijn vastgelegd. S-P2-110, S-P2-120, S-P2-130 en het resterende deel van S-P2-200 staan op versie 2. |
| home-control-hub | S-P2-290 t/m S-P2-340 | De connector verwerkt events en flowverzoeken, bewaakt de isolatie van Node-RED en ondersteunt momentopnamen, herstel en Authentik-acties. De proef tegen de Hub-code gebruikte testdiensten. |
| jelly-leon-platform | S-P2-395 t/m S-P2-420 | De lifecycle-planner controleert catalogusbeschikbaarheid. Een losse installatie- of updatepreview geeft geen uitvoerbare stap. Het Node-RED-manifest sluit anonieme toegang tot de editor. |
| appstore-en-fork | S-P2-500 t/m S-P2-520 | De catalogus verwijst naar de kluis. Het ontwerp voor beheerder en dienstaccount en de validatie van manifestvelden houden geheime waarden uit het formulier. |
| media-guard-ultimate | S-P2-590 t/m S-P2-620 | Simulatorproeven dekken aanmelden per mediaserver en het gelijktijdig volgen van Emby en Jelly Leon. Het upgrade- en terugzetbewijs gebruikt een gevulde 1.2.2-testdatabase. Het mediaserver-tabblad en de Engelse Android-weergave zijn beoordeeld. |
| my_house | S-P2-700 en S-P2-710 | De grafiek ‘Laatste 24 uur’ heeft een tabel en toetsenbordbediening. De bewijsregels benoemen de resterende apparaat- en meterproeven. |
| jelly-leon | S-P2-800 en S-P2-810 | De review van contract 1.3 en de controle van het risicobeleid zijn vastgelegd bij de serverfork. |
| jelly-leon-web | S-P2-850 en S-P2-860 | Een neutrale testwaarde vervangt de oude fixture. Het webproject heeft het risicobeleid en de bewijsaantekeningen overgenomen. |
| jelly-leon-clients | S-P2-870 | Het risicobeleid en het clientbewijs zijn gecontroleerd. Op dezelfde commit is de forkcontrole groen en de upstream-sync rood. Run 42 is het door de regisseur aanvaarde signaal. |
| zoeken-en-persoonlijke-ai | S-P2-880 | Het risicobeleid is gelijk aan de bron. Vier zoekscenario’s vermelden het simulatorresultaat, het resterende integratiewerk en de NAS-proef. |
| media-source-optimizer | S-P2-890 | Het risicobeleid is gelijk aan de bron. Bij B05-004 resteert de groeimeting van dertig UTC-dagen op de installatie. |

### NIET GEVALIDEERD op de echte omgeving

| Onderdeel | Open praktijkproef | Vervolg |
|---|---|---|
| Hub en executor | Beide installeren als standaard Custom App. De koppeling, schrijfrechten en methoden per TrueNAS-versie toetsen. Een goedgekeurde R1-herstart op een toegestane app uitvoeren en de toestand teruglezen. | N-P6-03, S-P6-18 |
| Appbeheer | Installeren op een gepinde releasedigest, bijwerken, terugzetten en verwijderen met behoud van gegevens. Het gedrag van het Custom App-formulier controleren. | N-P6-03, S-P6-02 t/m S-P6-06, S-P6-20 |
| Opslag en boiler | De blokkade bij een ongezonde pool toetsen met echte pool- en schijfmetingen. Met een aangesloten meter de leesstand en de weigering van een schakelverzoek controleren. | N-P6-01, N-P6-06, S-P6-20 en S-P6-21 |
| Back-up en herstel | OneDrive-aanmelding en upload bevestigen, een foto en database-export teruglezen en ZFS-momentopnamen op de pool toetsen. De rampenoefening vraagt herstel op andere hardware. | N-P6-02 en N-P6-14 |
| AI-aanbieder | Na de bouw van versie 2 het werkelijke tegoed, de harde stop en de monitor voor betaalde overschrijding toetsen. | D09, N-P6-08 |
| Node-RED | De Custom App installeren, beheerder en dienstaccount inrichten, flows en diensttoegang plaatsen en de flows uitvoeren. Herstel naar een verse instantie toetsen. | N-P6-04, S-P6-19 |
| Monitoring en SSO | De monitors in Uptime Kuma bevestigen. Bij een echte Authentik de catalogusgeheimen via de executor invullen, de OIDC-client registreren, sessies intrekken en de upgradegate toetsen. | T-18, D17, N-P6-04 |
| MediaGuard en mediaservers | Emby en een geïnstalleerde Jelly Leon tegelijk volgen. De contracttest met de Jelly Leon-image en de upgrade van de productiedatabase staan open. Kijkgeschiedenis en MediaGuard-voortgang moeten beschikbaar blijven, met voor/na-rapport, getest terugvalpad en akkoord van de gebruiker. Emby blijft de terugval. | S-P6-32, S-P6-33, N-P6-05 en N-P6-11 |
| MediaGuard-release en Android | De gebruiker koppelt de GHCR-pakketten aan de nieuwe repo en bevestigt de zichtbaarheid. De Engelse Android-app moet op een echte telefoon worden bediend met schermlezer en in fel licht. | T-01, N-P6-05 |
| my_house | De tabel en grafiek toetsen met echte airco en sensor, afwijkende apparaatklok, schermlezer, telefoon in fel licht, Firefox, Safari en 200% zoom. | N-P6-06 |
| Fase als geheel | De open praktijkproeven uit het NAS-acceptatiedraaiboek uitvoeren en hun resultaat aan de faseregel koppelen. | S-P6-50 |

### Open besluiten en gegevens

- D01, D02, D04, D05, D06 en D16 vragen de werkelijke TrueNAS-versie, pools en datasets, back-upmethode, herstelbewijs, poolgezondheid en hersteldoelen. D17 vraagt domein, HTTPS, herstelaccount en rollen. Deze gegevens worden bij de praktijkproeven ingevuld.
- Bij D09 ontbreken het bevestigde inbegrepen tegoed en het productieaccount. AI staat standaard uit. De AI-chat, kennisgereedschappen, kostenbewaking en afzonderlijke veiligheidssuite zijn uitgesteld naar versie 2. Ook de resterende catalogusweergave ‘Geïmporteerd’ en E15 voor verouderde storingen of beperkingen staan open.
- Voor BG-05 geldt de vastgelegde stand ‘niet’ voor zoeken of herstellen via de Hub. De noodstop in MediaGuard zelf blijft beschikbaar. De Hub-actie uit S-P3-110 is uitgesteld naar versie 2 tot er een actienaam in contract en beleid staat.
- T-01 houdt de nieuwe MediaGuard-release tegen. Onder Z-06 blijft het werk op de werkbranch tot de gebruiker beslist over opname in de standaardbranch. Z-03 is op 16 november beslist. Elke databasemigratie van een mediaserver vraagt een voor/na-rapport. Z-04 en Z-05 zijn op 11 november beslist.
- De grenzen uit hoofdstuk 8 blijven gelden. De installatie wacht op een vooraf beschikbare dataset (C-2). Bij Node-RED blijven de inrichtingsproeven uit C-5 open. De flow voor een verouderde my_house-sensor wacht op de contractroute (C-6). C-11 en C-12 leggen toegang via een beheerder en inrichting zonder geheim in het formulier vast.

### Uitkomst van de gate

volgt — S-P2-910. De faseregel P2 staat op `Bezig` met `Sim-getest; NIET GEVALIDEERD (echte NAS)`.

## P3 — eigen apps koppelen: gebouwd en in de simulator getest (2026-11-24)

Versie 1 volgt variant B. De Hub beheert de bestaande apps en Emby blijft de mediaserver. De tabel noemt de gepushte broncommits waarop het fasebewijs rust. De cijfers tussen haakjes zijn de bijbehorende Forgejo-runs.

| Repo en bronstand | Stappen | Wat is gebouwd en beproefd |
|---|---|---|
| ai-server-manager · `a6cc363` (#77) | S-P3-010 t/m S-P3-100, S-P3-170 | Media toont beschikbare MediaGuard-cijfers en de openbare MSO-gezondheid. Zonder aantoonbaar leesrecht blijft de diagnose onbekend. Huis toont gegevens van de bevestigde my_house-koppeling. Ontbrekende back-upmetingen sluiten de poort. De rooktest controleert de Hub- en executor-images. Kosten toont een plaatshouder. |
| media-guard-ultimate · `1e05ba5` (#55, #56) | S-P3-600 t/m S-P3-680 | Sleutels hebben begrensde rechten. De connector levert leesgegevens, events met cursor en een herstelrapport. De schemacontrole, de healthcheck en het Custom App-manifest zijn gebouwd. Het upgrade- en terugzetbewijs vergelijkt de voortgang in een gevulde 1.2.2-testdatabase. |
| media-source-optimizer · `dca9ccf` (#31) | S-P3-200 t/m S-P3-290 | De machinesleutel begrenst lezen en wijzigen. De connector koppelt een wijziging aan de goedgekeurde voorvertoning. De testdatabase doorloopt de upgrade. De image heeft een healthcheck als gebruiker 568 en een Custom App-manifest. |
| my_house · `517cd5b` (#82) | S-P3-700 t/m S-P3-755 | De alles-in-één-image bevat Zigbee2MQTT als optioneel proces. Het bedieningspad toetst de sleutel, het doel en de inbedrijfstelling. De boiler blijft alleen leesbaar. De webapp herstelde een versleutelde export van testinstantie A op B. |
| home-control-hub · `f2dd141` (#19) | S-P3-300, S-P3-310, S-P3-360 | De energietijdreeks houdt bron, meetkwaliteit, reset, meterwisseling en tijdvak bij. Bij Node-RED is het oude beveiligingsprofiel vervallen. Zonder dienstaanmelding krijgt de meting de stand onbekend. |
| jelly-leon-platform · `3677179` (#30) | S-P3-400 t/m S-P3-450 | De controlelijsten I03, I04, I05 en I15 t/m I20, en de manifestkopieën van de drie bestaande apps zijn vastgelegd. Het Node-RED-manifest blijft in de afgesproken wachtstand. De editor weigert anonieme toegang. |
| appstore-en-fork · `936b2da` (#10) | S-P3-490 | De manifestvalidator ondersteunt de voorziening voor beheerder en dienstaccount en weigert geheimen in het installatieformulier. |

### Wat versie 2 nog moet leveren

De noodstop AAN vanuit de Hub (S-P3-110) wacht op een actienaam, risicoklasse en goedkeuringsregel in contract en beleid. De noodstop is in MediaGuard zelf beschikbaar. De Hub-goedkeuring van MSO-wijzigingen (S-P3-120), het bewaakte schrijfpad naar my_house (S-P3-130), de module voor energie en kosten en het bijbehorende scherm (S-P3-150, S-P3-160) zijn uitgesteld. B01-011 heeft daarom de status `Niet gestart`.

De versieplanning stelt ook de bijwerking van de appdocumenten en het register (S-P3-180, S-P3-500), energieplanning, kostenadvies, meldingen en statusweergave (S-P3-320 t/m S-P3-350), de Android-schermronde en de extra poolbron van MediaGuard (S-P3-685, S-P3-690) en de schermronde van my_house (S-P3-765) uit.

### NIET GEVALIDEERD op de echte omgeving

| Wat nog getoetst moet worden | Proef |
|---|---|
| MediaGuard, MSO en my_house als standaard Custom App installeren. De Hub koppelen aan de geïnstalleerde apps en de echte bronrechten, foutredenen en versheid meten. Bij MediaGuard de upgrade en de terugval controleren met behoud van kijkgeschiedenis en voortgang. T-01 houdt een nieuwe MediaGuard-release tegen zolang de pakketkoppeling openstaat. | N-P6-05, N-P6-06 |
| Lampen, airco en meters koppelen en hun teruggelezen toestand vergelijken met de fysieke toestand. De boiler mag uitsluitend meetwaarden leveren. De Zigbee-stick via het formulier doorgeven, vaststellen of gebruiker 568 hem kan openen en de werking na een herstart toetsen. | D01, D12, D13, D14 en N-P6-06 |
| Op de echte pool een momentopname en database-export maken. De kopie herstellen en met de bron vergelijken. Ook de installatie en rechten van de Hub en de executor en de aanmelding met de benodigde accounts staan open. | N-P6-02, N-P6-03, N-P6-04 |
| De volledige scenario’s voor MSO, Hub-goedkeuring, Node-RED, opslag, huis en energie doorlopen. Voor EX50 moeten Hub, my_house en aanmelding na herstel op een tweede omgeving met een ander adres samen blijven werken. | S-P6-16, S-P6-18 t/m S-P6-21 en N-P6-14 |

De Testmatrix gebruikt voor deze integrale scenario’s de status `Geblokkeerd` (§8.2). Het bewijsveld vermeldt welke deelproef al in een repo is uitgevoerd.

### Besluiten die bij P3 gelden

- **Z-02, Z-03, Z-08 en Z-10.** Op 16 november koos de gebruiker telkens optie 1. De hostbeperking voor het koppelen via een statuspagina geldt. Elke databasemigratie van een mediaserver vraagt een voor/na-rapport. Het ingestelde Hub-adres in my_house is zonder inloggen leesbaar. MSO draait CI bij een push op de werkbranch.
- **BG-05.** Voor zoeken en herstellen via de Hub geldt ‘niet’. MediaGuard houdt de bediening. De afzonderlijke Hub-noodstop valt onder het uitstel van S-P3-110.
- **Z-18.** Op 21 november koos de gebruiker optie 2. S-P3-438 en S-P3-440 gebruiken voor I05-05-02 ‘Formulier standaard Custom App zonder Zigbee/tunnel’ en voor I05-05-03 ‘TrueNAS Install via formulier standaard Custom App’.
- **Z-17 en Z-21.** Op 11 november koos de gebruiker Zigbee2MQTT in de image van my_house, alleen actief wanneer een USB-apparaat is opgegeven. Voor Z-21 koos de gebruiker optie 2. S-P3-755 laat de apparatenlijst in het manifest leeg en beschrijft de optionele stick in het veld Devices van het formulier. De doorgifte en toegang op de NAS zijn nog te meten (D01, D13).
- **C-12.** Op 11 november koos de gebruiker voor inrichting van beheerder en dienstaccount via de manifeststandaard, zonder geheim in het formulier (S-P3-490, S-P3-445, S-P3-360). Voor de officiële Node-RED-image geldt de keuze ‘Wachten’. Het manifest bevat nog geen accounts en de editor blijft dicht tot een ondersteunde inrichting beschikbaar is.

### Uitkomst van de gate

volgt — S-P3-910. De faseregel P3 staat op `Bezig` met `Sim-getest; NIET GEVALIDEERD (echte NAS)`.
