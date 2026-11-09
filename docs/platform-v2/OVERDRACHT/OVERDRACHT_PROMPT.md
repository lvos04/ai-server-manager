# Overdrachtsprompt — TrueNAS Home Platform V2 (verhuizing naar eigen Ubuntu-machine)

Plak alles onder de streep in een nieuwe Claude Code-sessie op de Ubuntu-desktop (via SSH in de Claude-app).
De machine heeft sudo-rechten.

---

Je neemt een lopend project over: **TrueNAS Home Platform V2**. De vorige sessie draaide in een cloud-sandbox met maar 4 CPU's.
Deze machine is van de gebruiker (Ubuntu-desktop, sudo-rechten, meer CPU's). Antwoord in het Nederlands. Stel vragen via een
keuzemenu als iets onduidelijk is en gok niets. ai-factory niet aanraken. Maak geen PR's zonder te vragen.

## 0. Eerst doen (in deze volgorde)

1. **Machine opzetten** volgens `docs/platform-v2/OVERDRACHT/SETUP_UBUNTU.md` uit de repo `lvos04/ai-server-manager`. Kort:
   git, gh, Docker (met buildx/compose, gebruiker in groep docker), Python 3.12 + venv, Node 22 + pnpm, Java 21, cmake,
   PostgreSQL 16 + pgvector op 127.0.0.1:5432 (rol `postgres`, trust alleen op 127.0.0.1 — de tests gebruiken
   `postgresql+psycopg://postgres@127.0.0.1:5432/...` zonder wachtwoord), Playwright + Chromium, .NET 9 via de image
   `mcr.microsoft.com/dotnet/sdk:9.0`, en optioneel Android SDK command-line tools (in de sandbox geblokkeerd, hier wel mogelijk).
   Controleer `nproc` en het geheugen en noteer die.
2. **GitHub-toegang:** controleer `gh auth status`. Zo niet: vraag de gebruiker `gh auth login` te doen (apparaatcode via telefoon)
   met schrijfrechten op de repos hieronder. Gebruik git via HTTPS met de gh-credentialhelper (`gh auth setup-git`).
3. **Repos klonen** in één werkmap, bv. `~/truenas-v2/` (de map zelf is geen repo), en overal branch `ccr-c133d7a0-kuz1cv` uitchecken:
   `ai-server-manager, home-control-hub, appstore-en-fork, jelly-leon-platform, jelly-leon, jelly-leon-web, jelly-leon-clients,
   zoeken-en-persoonlijke-ai, media-guard-ultimate, media-source-optimizer, my_house` (allemaal `github.com/lvos04/<naam>`).
   Voor `jelly-leon`, `jelly-leon-web` en `jelly-leon-clients` (grote historie) mag `git clone --filter=blob:none`.
   Voeg in jelly-leon en jelly-leon-web de remote `upstream` toe (`https://github.com/jellyfin/jellyfin.git` resp.
   `.../jellyfin-web.git`).
4. **Lees** in `ai-server-manager/docs/platform-v2/`: `README.md`, `PLATFORM_CONTRACTEN.md` (bindend), `OVERDRACHT/STATUS.md`
   (stand bij overdracht + open punten), `00_START/*`, `01_ARCHITECTUUR/*`, `05_TESTS/*`. Het volledige pakket en het originele
   zip-bestand staan daar ook (`pakket/`), plus de Excel (`08_EXCEL/`).
5. **Stel de echte stand vast per repo** (vertrouw niet alleen op STATUS.md — de vorige sessie werkte na het schrijven ervan nog
   door): `git log --oneline -15`, `docs/platform-v2/EVIDENCE.json`, `docs/platform-v2/EXCEL_TAKEN.json`, en voor bestaande
   repos `DELTA_MATRIX.md`. Bepaal per repo welke P0-taken af zijn en of de P0-review (tweede agent) al gedaan is
   (reviewcommits beginnen meestal met "Review"/"Bewijs na review" of staan in CHANGELOG). Niet-gecommit werk uit de oude
   sandbox is verloren; dat is geen probleem.
6. Rapporteer de stand kort aan de gebruiker en ga dan door met de fasering (sectie 4).

## 1. De opdracht (ongewijzigd)

Werk het pakket `TrueNAS_Home_Platform_V2_VOLLEDIG_2026-11-09.zip` (staat in `ai-server-manager/docs/platform-v2/pakket/`)
volledig door en bouw alles wat erin staat.

Repo-indeling (vast besluit):
- **ai-server-manager:** B01 centrale Hub-web-UI, B02 AI-beheer (agent, risicopolicy R0–R3, executor), B09 monitoring/incidenten, B12 back-up/herstel
- **home-control-hub:** integraties B10 netwerk/privacy, B11 Node-RED, B13 Authentik/SSO, B14 energie/resources
- **appstore-en-fork:** B08-001 manifeststandaard, B08-002 import bestaande apps, B08-005 forkbeheer
- **jelly-leon-platform:** installatie, updates, rollback, verwijderen/verhuizen van het hele platform (B08-003, B08-004, B08-006) + alle 03_INSTALLATIE/Ixx-docs als installeerbare manifests + de integrale E2E-omgeving
- **jelly-leon:** B03 mediaserver, fork van jellyfin/jellyfin v10.11.11 (GPL-2.0), patches gescheiden van plugins, upstream-sync
- **jelly-leon-web:** fork van jellyfin/jellyfin-web v10.11.11
- **jelly-leon-clients:** jellyfin-android 2.7.3, jellyfin-androidtv 0.19.10, jellyfin-desktop 2.0.0, Swiftfin 1.6.1 (iOS/tvOS kan zonder Mac/Xcode niet → NIET GEVALIDEERD)
- **zoeken-en-persoonlijke-ai:** B07 persoonlijke zoekmachine (pgvector) + B15 spraak/persoonlijke AI
- **media-guard-ultimate / media-source-optimizer / my_house:** B04 / B05 / B06 — alleen ontbrekende punten (delta)

## 2. Vaste keuzes en genomen besluiten (niet opnieuw vragen)

- Techniek nieuwe repos: Python 3.12 FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16; frontend Next.js/React PWA.
- **Alle schermen centraal in de Hub-UI** (ai-server-manager). Andere nieuwe repos: zelfstandige API-diensten met alleen een kleine
  eigen statuspagina. Bestaande apps (MediaGuard, MSO, my_house) houden hun eigen UI; de Hub toont kaarten met deep-links.
- **Installatie: niets via YAML.** Alles als **standaard TrueNAS Custom App** (gewoon formulier), zonder terminal.
  Eén **alles-in-één image per repo** (ingebouwde PostgreSQL via unix-socket, API, worker; voorbeeld: MSO `deploy/allinone`).
  Eerste installatie = twee handmatige Custom Apps: `ai-server-manager` (Hub, poort 30400, eenmalige setupcode in de app-logs) en
  `ai-server-manager-executor` (poort 30410; aparte app; koppelen met koppelcode via de web-UI; de TrueNAS-schrijfkey wordt
  alleen op de executorpagina ingevoerd). Daarna installeert de Hub via de executor alles via de TrueNAS-API als standaard Custom
  App (`app.create` met ix-app-waarden, nooit `custom_compose_config`). Derden-apps met meerdere containers via de officiële
  TrueNAS-catalogusapp met vaste versie; anders Custom App met één gepinde image. Compose alleen voor ontwikkeling/CI/E2E.
- **Forks:** server/web met volledige upstream-historie; clients als `git subtree --squash` per map, sync via `git subtree pull`.
  Technische identiteit/API blijft "Jellyfin"; alleen de zichtbare naam wordt "Jelly Leon". GPL en credits blijven.
- **Lokale modellen** (Ollama, faster-whisper, Piper, lokaal embeddingmodel): optionele apps, standaard uit. Claude API alleen
  binnen inbegrepen credits met harde stop (0 overage); regelgebaseerde fallback werkt altijd.
- **Excel:** code + CI + simulator-E2E geslaagd ⇒ status "Bezig" (of "Geblokkeerd" als echte NAS/hardware/account nodig is) +
  kolom "Validatie" (Sim-getest / NIET GEVALIDEERD (echte NAS|hardware|account|Mac/Xcode)) + bewijs. "Gereed"/"Geslaagd" alleen
  na echte acceptatie op de NAS — nooit zelf zetten. D01–D18 blijven "Open" tot de gebruiker ze invult. Bijwerken met
  `ai-server-manager/tools/excel/update_excel.py` (bewerkt op XML-niveau; openpyxl zou de databar op 'Appoverzicht' slopen).
- **Delta-basis = huidige HEAD:** MediaGuard v1.2.2 (+2 CI-commits), MSO 1.6.0, my_house 0.2.0 (pakket noemt nog 0.1.0).
- NAS-gegevens D01–D18 zijn onbekend: nooit voorbeeldwaarden als echte waarden; invullen via de onboarding-wizard of meten via
  de TrueNAS-API. Bestaande integriteit/rollback/monitoring nooit dubbel bouwen of uitschakelen.
- Veiligheid (03_RISICO_AUTONOMIE): geen shell/root voor AI, geen sh -c/sudo-endpoint, geen Docker-socket in containers, geen
  latest-tags (base images op @sha256), boiler nooit schakelen, geen betaalde API-overage; deterministische policy, executor
  controleert handtekening/nonce/vervaltijd/allowlist/policy-hash zelf opnieuw.
- Echte NAS-, hardware- en accounttests kunnen hier niet: NIET GEVALIDEERD / Geblokkeerd. Nooit doen alsof ze geslaagd zijn.
- **HARDE EIS van de gebruiker (2026-11-09):** alle kijkgeschiedenis (gezien-status, hervatpunten, favorieten, beoordelingen,
  onthouden spoorkeuzes, gebruikers, rechten) en de MediaGuard-voortgang blijven altijd beschikbaar; geen cutover zonder
  vóór/na-rapport per gebruiker en akkoord op elk verschil; de bestaande installatie blijft als terugval. De huidige
  mediaserver is **Emby**; de overname daarvandaan (B03-015, JLT-70…74) is P0; Emby verwijdert de gebruiker zelf na de
  controlelijst (ADR-0020). Genomen en open B03-besluiten: `02_BOUWPLANNEN/B03_BESLUITEN.md`.
- Git: branch `ccr-c133d7a0-kuz1cv` in elke repo, NL-commitberichten, geen force-push, geen geheimen, geen modelnaam in
  commits/code. Sluit commits af met de attributieregels die jouw sessie voorschrijft.

## 3. Werkwijze

- Per fase P0–P6; per onderdeel: code, unit/integratie/E2E-tests, OpenAPI, CI, alles-in-één image + `deploy/truenas/CUSTOM_APP.md`
  + manifest met gepinde images, `.env.example`, ADR's. Na elke bouwstap een **onafhankelijke review-agent** die tests opnieuw
  draait, contract en veiligheid controleert, eerlijkheid van EVIDENCE.json bewaakt en zelf repareert.
- Bestaande repos: delta-matrix (bestaand/onvolledig/ontbrekend) is in P0 gemaakt en door een tweede agent gecontroleerd;
  bouw in P3 alleen de hiaten uit de geprioriteerde bouwlijst onderaan elke `DELTA_MATRIX.md`.
- Integrale E2E-omgeving in `jelly-leon-platform/e2e` met simulators (TrueNAS-API incl. standaard Custom App- en
  catalogusmethoden en foutinjectie, Beszel, Uptime Kuma, Gotify, Authentik, apparaten), getoetst aan
  `05_TESTS/INTEGRALE_E2E_TESTMATRIX.md` (EX01–EX50).
- **Orkestratie:** de workflow-scripts van de vorige sessie staan in `docs/platform-v2/OVERDRACHT/workflows/` (p0.js, p1.js +
  README). Pas daarin het blok `OMGEVING:` aan deze machine aan (geen proxy/CA meer; echte CPU-telling; lokale paden) en vervang
  `/home/user` door je werkmap. Als de Workflow-tool beschikbaar is: draai per groep een eigen workflow (args `{"groups":[...]}`)
  zodat groepen parallel lopen; anders dezelfde opdrachten als parallelle subagents (één agent per repo tegelijk, nooit twee
  agents in dezelfde repo). Stem het aantal parallelle zware builds af op `nproc`.

## 4. Fasering (wat waar hoort)

- **P0** (bezig bij overdracht): delta's MediaGuard/MSO/my_house (klaar); fork-inventaris + bouw-/sync-basis drie Jellyfin-repos;
  basis nieuwe repos (alles-in-één image, CUSTOM_APP.md, CI); Hub: setupcode, auth, enrollment, wizard D01–D18 + gates,
  TrueNAS-adapter (read-only), inventaris, B12-001…003, PWA-basis; appstore: B08-001 manifeststandaard + validator (EX47);
  platform: TrueNAS-simulator, INSTALLATIE.md (2 Custom Apps), TRUENAS_APP_API.md; zoeken: B07-001; integraties: B13-001.
  → Maak eerst af wat volgens sectie 0.5 ontbreekt (inclusief ontbrekende reviews), daarna contract 1.2 (zie STATUS.md).
- **P1:** B01-002/004/005/006, B09-001…006, B13-002…005, B08-002 + APP-01…20, manifests I07/I08/I09/I13/I23, simulators
  Beszel/Uptime Kuma/Gotify/Authentik (script `p1.js` staat klaar).
- **P2:** B02, B01-003/007/008/009, B11, B12-004…007, B08-003/004, executor + koppelen, manifest I10.
- **P3:** hiaten B04/B05/B06 (incl. my_house als alles-in-één Custom App en herstelprocedures zonder terminal), Hub-adapters
  MediaGuard/MSO/my_house op hun bestaande routes, B14, B01-011, manifests I03/I04/I05/I15–I20.
- **P4-0 (nieuw, vóór P4):** upgrade jelly-leon + jelly-leon-web naar de nieuwste stabiele Jellyfin 12.x (ADR-0011 in
  jelly-leon; B03-014), overname vanuit de bestaande mediaserver — **Emby**, en Jellyfin als D07 dat meet — met een
  vóór/na-rapport per gebruiker en akkoord van de gebruiker op elk verschil (B03-015; HARDE EIS, ADR-0020), definitieve
  stock-baselines op dezelfde 12.x-digest (B03-016), register `UPSTREAM_GEDRAG.md` (B03-019). Exitcriterium: Δ-MG-AUTH per
  server en Δ-MG-DUAL in media-guard-ultimate; zonder Δ-MG-AUTH geen B03-batch op de NAS. Golf 0 (corpus, harnas,
  voormetingen tegen stock 12.4 en — met voorrang, P0 van de gebruiker — de Emby-overname-proefrun JLT-70…73 met een echte
  Emby-container) mag al parallel aan P0–P3. Plan: `02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md`, `B03_FASERING.md`,
  `B03_BESLUITEN.md`.
- **P4:** B03 in jelly-leon, jelly-leon-web, jelly-leon-clients (plugins vóór core-patches), in golven: golf 1
  gemeenschappelijke basis (één plugin met modules, connector/Hub-pin JL4, foutcatalogus, MediaGuard-viewerclient,
  analysewerker, globale planner, belastingtest; B03-009/010/017/018); golf 2–4 de zes functies F1–F6 (Watch Together,
  aanbevelingen, ondertitels klassiek, kwaliteitscontrole, apparaatprofielen, intro/outro/recap; B03-004/005/007 en
  B03-020…079 zonder de P5-rijen); patches en Hub-kaarten in golf 4; manifests I06/I22/I24. Ontwerpstap en -review
  alleen voor de Hub-kaarten (Jelly Leon zelf valt buiten de ontwerptaal).
- **P5:** B10, B07, B15, B08-005/006, B01-010/012, B02-009, manifests I11/I12/I14/I21/I25/I26 + lokale modellen, **plus de
  P5-delen van B03** (B03-038, B03-044…046, B03-048, B03-049-rest, B03-059, B03-079) met één producent per modelsoort
  (Δ-CONTRACT-MODEL, Δ-CONTRACT-MT); alles optioneel en standaard uit.
- **P6:** integrale E2E EX01–EX50, regressie, documentatie, Excel bijwerken, eindreview; plus de NAS-testrijen van B03
  (JLT-06/15/26/39/49/59/69/74), de echte overname vanuit Emby met laatste delta en akkoord (B03-015), de terugzetproef
  B03-013 en de controlelijst "Emby verwijderen" (de gebruiker verwijdert Emby zelf, APP-02/I26-26-02).

Na elke fase: alle repos schoon en gepusht, Excel bijwerken en committen in ai-server-manager, korte statusmelding aan de
gebruiker met wat NIET GEVALIDEERD/Geblokkeerd is en welke menselijke input nodig is.
