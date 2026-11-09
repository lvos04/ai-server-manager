# Changelog

Alle noemenswaardige wijzigingen. Versies volgen `VERSION`; images krijgen exact deze tag (nooit `latest`).

## [0.1.0] — 2026-11-09 (fase P0, backend en web-UI; niet uitgebracht)
- Ontwerptaal **Peil** 1.1.0 als bron van waarheid: `docs/platform-v2/ONTWERPTAAL.md` + `design/ontwerptaal/` (tokens, CSS voor Tailwind 4 + shadcn/ui, statuspagina-sjabloon, aliaslagen, prototypes, schermafdrukken, contrast- en axe-controle) en ADR-0015 (vervangt ADR-0009 punt 1 deels).

### Gerepareerd — onafhankelijke review van contract 1.2 in Hub en executor (ADR-0014)
- **1 MiB vóór routering en aanmelding (§5):** Hub en executor lezen de body nu vóór alles, met hooguit 1 MiB in het
  geheugen. Een chunked verzoek van meer dan 1 MiB geeft altijd `413` met `details.max_bytes`; vroeger gaf de Hub dan
  401/405 op routes zonder body, en de executor kende helemaal geen grens voor chunked verzoeken.
- **Executor, `unlink` (§4.6, §3.8, §4.2):**
  - Een persistente `jti`-replaycache (`/appdata/executor.sqlite3`): een hergebruikte `jti` geeft `401 token_replayed`,
    ook na een herstart. Een exacte herhaling krijgt het opgeslagen antwoord. Is de cache onbruikbaar, dan `503`.
  - `Idempotency-Key` is verplicht en een gebruikers-JWT moet de rol `admin` hebben.
  - De rol `kind` wint nu altijd.
  - Een JWT met een `iat` in de toekomst wordt geweigerd.
- **CI:** de controle "na een downgrade is de database niet actueel" faalde nooit (`!` zet `errexit` uit). Dat is
  gerepareerd.
- **Webpoort (Node-doorgang):** een chunked upload van meer dan 1 MiB werd vaak `502` ("Hub-API niet bereikbaar")
  in plaats van `413`. De doorgang telt nu zelf en antwoordt met dezelfde 413-body als de API.
- **Rooktest:** controleert nu ook chunked verzoeken van meer dan 1 MiB (tot 3 MB, herhaald), zowel naar de Hub via
  de webpoort als naar de executor.

### Gewijzigd — contract 1.2 toegepast in de Hub en de executor (ADR-0013)
- **Enrollment (H1/H2):** `POST /api/v1/services/enroll` volgt §3.3 exact (strikte JWK, token- en koppelcodeformaat,
  `version`/`base_url`/`public_key_jwk` verplicht); antwoord met `schema_version`, `keyset_fingerprint`,
  `key_rotation_url` en `enrollment_replayed`; toegestane herhaling na een herstart halverwege; nieuw
  `GET /api/v1/services/self`; executor alleen met een koppelcode van 30 min; exacte `Retry-After` bij 429.
- **Rotatie (H3):** oud token vervalt 10 min na het eerste gebruik van het nieuwe (hooguit 24 uur);
  `Hub-Token-Rotation: required`; `POST /services/{id}/rotate` vraagt alleen aan (`202`, `Idempotency-Key`, geen token);
  na 180 dagen alleen een melding.
- **JWT's (H4):** `token_use: "user"` in gebruikers-JWT's; dienst-JWT `token_use: "hub_service"` voor Hub → dienst;
  `GET /api/v1/auth/key-rotations` (lege lijst) en `GET /api/v1/auth/keyset`.
- **Koppelbeheer (H5-backend, H14):** `POST /services/{id}/unlink` (via de dienst, daarna intrekken) en
  `PUT /services/{id}/truenas-app` (gemeten appnaam bevestigen). Het UI-scherm "Diensten" wacht op de ontwerpstap (§13).
- **Noodlogin (H6-backend):** `/api/v1/auth/break-glass` (status, setup, rotate, confirm, login, selftest) met TOTP,
  privé-bereiken, sessie ≤ 60 min, event `auth.break_glass.used` en rotatieplicht. UI wacht op de ontwerpstap.
- **Executor (H7, deel):** koppelen op de statuspagina met koppelcode + vingerafdruk, pinning in `hub-link.json`,
  controle van inkomende Hub-JWT's (`GET /connector/v1/hub-link`); ontkoppelen geeft eerlijk `501` tot P2.
- **Manifesten (H8)** zonder `joins_platform_network`/`custom_app.ports`; **Custom App-instructies (H9)** met tag
  `<versie>@sha256:<digest>`, publieke image en registry-login als terugval.
- Migratie `0002`; OpenAPI bijgewerkt; rooktest controleert ook het enroll-schema, de lege sleutelrotaties en de
  executor-weigering zonder koppeling.

### Gewijzigd — onafhankelijke review van contract 1.2
- `docs/platform-v2/PLATFORM_CONTRACTEN.md` blijft `contracts 1.2`, met correcties R1–R12 (zie
  `docs/adr/ADR-0012-review-contract-1-2.md`): `app_id` vast per image; `pending` naast `state` in `hub-link.json`;
  strikte JWK-regels in het enroll-verzoek; rotatie van service-tokens zonder buitensluiten en alleen op verzoek van
  een beheerder; intrekking pas na `services/self`; sleutelrotatie per doel en zonder authenticatie; vaste
  `reason`-tabel; koppelbeheer is geen `action_id`; TrueNAS-uitspraken als bronwaarneming (NIET GEVALIDEERD); ook
  PID 1 niet als root; executor-bewijs tegen het vastgelegde NAS-adres.
- `docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md` bijgewerkt naar de echte stand per repo (gecontroleerde commits),
  met nieuwe punten A7, AS8, JP12, H14 en root-PID 1 (A6).
- `deploy/smoke.sh`: controleert nu voor elk proces in Hub en executor ook `CapEff 0000000000000000` (naast
  `NoNewPrivs 1`), zoals contract §2.2 vraagt.
- `docs/platform-v2/EVIDENCE.json`: `validatie` van D01–D18 alleen nog met waarden uit de vaste lijst van §11
  (toelichting naar `opmerking`); nieuwe test `apps/api/tests/unit/test_evidence_contract.py` bewaakt dat.

### Gewijzigd — platformcontract 1.2 (alleen documentatie)
- `docs/platform-v2/PLATFORM_CONTRACTEN.md` naar `contracts 1.2` met wijzigingslog: exact enroll-schema, dienst-JWT
  voor Hub → dienst, sleutelpinning met sleutelset-vingerafdruk, `jti`-replaycache, opslag in
  `/appdata/secrets/hub-link.json`, koppelen via de statuspagina alleen vóór de eerste koppeling, Custom App-realiteit,
  manifestwijzigingen, noodlogin in de Hub, besluiten van de gebruiker en nieuw §13 Ontwerptaal.
- Nieuw: `docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md` (wat elke repo moet veranderen) en
  `docs/adr/ADR-0011-contract-1-2.md` (keuzes). De code van de Hub volgt in een volgende stap (H1–H13).
- `apps/api/src/hub/keys.py`: referentie-implementatie van de RFC 7638-thumbprint en de sleutelset-vingerafdruk
  (contract 1.2 §4.5) met de testvectoren uit het contract (`apps/api/tests/unit/test_keyset_fingerprint.py`); nog
  niet gebruikt in het enroll-antwoord.

### Gerepareerd — tests
- `tests/e2e/test_wizard_inventory.py`: de controle op een klare-tekstsleutel in de vault faalde willekeurig als de
  AES-GCM-cijfertekst een 0x00-byte bevatte (`convert_from(…, 'LATIN1')`); nu een bytevergelijking.

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
