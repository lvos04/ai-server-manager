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
   (Mac/Xcode)).
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
  tijdelijke meetdata opgeruimd, testsets on demand, Android-images blijven, `transcode` in de groepen render en kvm.
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
