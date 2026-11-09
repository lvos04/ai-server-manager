# Changelog

Alle noemenswaardige wijzigingen. Versies volgen `VERSION`; images krijgen exact deze tag (nooit `latest`).

## [0.1.0] — 2026-11-09 (fase P0, backend en web-UI; niet uitgebracht)

### Toegevoegd — web-UI (`apps/web`)
- Next.js 16-PWA (App Router, TypeScript, Nederlands, licht/donker, toetsenbord/screenreader, aanraakdoelen ≥ 44 px):
  eerste start met setupcode, inloggen/uitloggen, onboarding-wizard D01–D18 (uitleg, gate, status, schemaformulier
  zonder voorbeeldwaarden, meten, bewijs), TrueNAS-koppeling (NAS-adres, alleen-lezen-key, verbindingstest,
  vingerafdruk bevestigen), uitleg executor, Server-inventaris, Apps, Backups-dekking, Home-kaarten met bron en
  "laatst bijgewerkt", Instellingen (wachtwoord, sessies, thema, gebruikers, auditspoor, PWA-status).
- Navigatie volgens 08_UI (ondernavigatie < 1024 px, zijbalk ≥ 1024 px); latere fasen eerlijk "nog niet beschikbaar".
- Eigen webserver (`server/hub-server.mjs`) met strikte API-doorgang en echte client-IP (vervalste
  `X-Forwarded-For` genegeerd); service worker alleen voor de app-schil, nooit voor API-gegevens.
- Alles-in-één image: web-stage (Node 22 op digest), web op 30400, API alleen op 127.0.0.1:8400; healthcheck en
  rooktest controleren beide. Makefile-doelen `web-*`, CI-job `web` (eslint, tsc, vitest, npm audit, next build,
  Playwright 360/390/768/1440 met axe).
- Teststack `tests/e2e/web_stack.py` (echte API + worker + fake TrueNAS) en schermafbeeldingen in `docs/screenshots/p0`.

### Gerepareerd
- `Makefile`: de optionele BuildKit-secret `ca_bundle` werd door een komma in `$(if …)` zonder `src=` doorgegeven.

### Gerepareerd — onafhankelijke review P0 (ADR-0010)
- Setupcode: twee gelijktijdige verzoeken met dezelfde geldige code konden twee beheerders opleveren; nu een
  advisory lock + hercontrole. Ontbrekende `setup-completed`-markering naast een bestaande beheerder wordt hersteld.
- 1 MiB-grens per verzoek gold alleen bij een `Content-Length`-header; nu ook voor chunked verzoeken (413).
- `POST /api/v1/auth/password` had geen rate-limit op het huidige wachtwoord.
- Images zetten zelf `no-new-privileges` (prctl) na de gebruikerswissel; rooktest controleert dat per proces.
- Rooktest (ook CI) controleert nu herstart en harde kill zonder dataverlies (beheerder, geen nieuwe setupcode,
  executor-identiteit).
- Nieuwe rechtenmatrix-test over alle routes; integratiefixture faalt in CI zonder PostgreSQL i.p.v. over te slaan.

### Toegevoegd — backend
- Hub-API (`hub`): FastAPI + SQLAlchemy 2 + Alembic + pydantic-settings; processen `api`, `worker`, `ai-runner`
  (stub, aparte gebruiker 569 zonder toegang tot geheimen), `init`, `migrate`, `backup-now`, `export-openapi`.
- First-start-init: ontbrekende geheimen in `/appdata/secrets` (0600, nooit overschrijven; Ed25519 voor identiteit,
  JWT en policy; `vault.key`), eenmalige setupcode in de app-log.
- Aanmelden: setupcode → eerste admin; login/logout (argon2id, rate-limit), sessies met CSRF, rollen
  admin/operator/viewer/kind, sessies intrekken, JWKS en dienst-JWT (EdDSA, exp ≤ 120 s).
- Enrollment: eenmalige enrollment-tokens (60 min) en koppelcodes, service-tokens (alleen hashes), rotatie met
  overgangstijd, intrekken.
- Onboarding-wizard-API voor D01–D18 met getypte waarden, bewijs, metingen via TrueNAS-readback en `GET /api/v1/gates`.
- Alleen-lezen TrueNAS JSON-RPC-adapter (wss, TLS-verificatie of bevestigde vingerafdruk, capability-map per versie,
  reason codes), inventaris met `observed_at`/veroudering, dienstenregister.
- Back-up en herstel: dekking per app/dataset, snapshotbeleid als voorstel, geverifieerde pg_dump van de eigen database,
  hersteltests als bewijsrecord.
- Events-inbox met dedupe, connectorcontract van de Hub, OpenAPI-export.
- Executor (P0): statuspagina "nog niet gekoppeld", allowlist die alles weigert.
- Alles-in-één Hub-image en executor-image (supervisor als PID 1, na de init geen root-proces), Custom App-formulieren,
  manifesten, CI (lint, types, tests met PostgreSQL, migraties, OpenAPI-drift, pip-audit, images + rooktest) en
  release-workflow (GHCR, SBOM, digests).

### Validatie
Sim-getest en tegen een echte PostgreSQL 16 getest; images gebouwd en gestart in Docker; web-UI met Playwright tegen de
echte API en tegen de image (fake TrueNAS). **NIET GEVALIDEERD op een echte NAS, Android-telefoon of tv/speler.**
