# ai-server-manager — centrale Hub van TrueNAS Home Platform V2

De Hub van het platform: **B01** (centrale web-UI en beheer-API), **B02** (AI-beheer met risicobeleid en executor),
**B09** (monitoring/incidenten) en **B12** (back-up en herstel). Taal: Nederlands. Bron van waarheid voor de
platformcontracten: [`docs/platform-v2/PLATFORM_CONTRACTEN.md`](docs/platform-v2/PLATFORM_CONTRACTEN.md) (versie 1.2;
wat elke repo moet veranderen: [`CONTRACT_1.2_CONFORMITEIT.md`](docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md)).

## Stand (versie 0.1.0, fase P0 + contract 1.2 — backend en web-UI)

| Onderdeel | Stand | Validatie |
|---|---|---|
| Hub-API (`apps/api`, pakket `hub`) | first-start-init, setupcode → eerste admin, login/rollen/CSRF, JWKS + gebruikers-JWT (`token_use: user`) en dienst-JWT (`token_use: hub_service`), enrollment volgens contract 1.2 (exact schema, vingerafdruk, toegestane herhaling, `services/self`, rotatie na eerste gebruik, rotatie aanvragen, ontkoppelen via de dienst), noodlogin met TOTP, onboarding-wizard D01–D18, gates, alleen-lezen TrueNAS-inventaris, dienstenregister met bevestigde TrueNAS-appnaam, back-updekking, eigen pg_dump, events-inbox, connectorcontract | Sim-getest (fake TrueNAS), echte PostgreSQL 16 |
| Executor (`apps/executor`) | healthz/readyz, statuspagina met koppelen (koppelcode + Hub-vingerafdruk, pinning in `hub-link.json`), controle van inkomende Hub-JWT's, allowlist die **alles weigert**; TrueNAS-schrijfkey volgt in P2 | Unit-getest + Sim-getest tegen de echte Hub-API + image-rooktest |
| Web-UI (`apps/web`, Next.js-PWA) | eerste start met setupcode, inloggen/uitloggen, onboarding-wizard D01–D18, TrueNAS-koppeling met vingerafdruk, Server-inventaris, Apps, Backups-dekking, Home, Instellingen; latere fasen eerlijk "nog niet beschikbaar" | Unit-getest (vitest) + Sim-getest (Playwright 360/390/768/1440 + axe, ook tegen de image) |
| Images | `deploy/allinone` (Hub + web-UI, alles-in-één, één poort 30400) en `deploy/executor` | gebouwd en gestart in Docker; **NIET GEVALIDEERD (echte NAS)** |
| Policy/AI | volgt in P2; AI staat standaard uit, geen modellen, geen betaalde aanroepen | — |

Echte NAS-, hardware- en accounttests zijn in deze bouwomgeving niet mogelijk. Zie
[`docs/platform-v2/EVIDENCE.json`](docs/platform-v2/EVIDENCE.json) voor de status per Excel-ID.

## Installeren (gebruiker)

Uitsluitend als **standaard TrueNAS Custom App** (formulier: image + tag, poort, opslag) — nooit via YAML of compose.
De tag is `<versie>@sha256:<digest>` uit `release/digests.json` (of alleen de exacte versie als het formulier `@` niet
accepteert; NIET GEVALIDEERD op een echte NAS). De images zijn publiek na de scan van besluit 3; registry-login is
alleen een terugval. Twee formulieren: [`deploy/truenas/CUSTOM_APP.md`](deploy/truenas/CUSTOM_APP.md). Daarna open je de Hub in de browser;
de pagina **Eerste start** vraagt de setupcode uit de app-log (TrueNAS → Apps → ai-server-manager → Logs) en maakt het
eerste beheerdersaccount, waarna de onboarding-wizard volgt.

## Ontwikkelen

```sh
make venv          # .venv met exact vastgezette versies + editable pakketten
make lint type     # ruff + mypy (strict)
make test          # unit + integratie (PostgreSQL op 127.0.0.1:5432) + dienst-E2E met fake TrueNAS
make openapi       # docs/openapi/*.openapi.json bijwerken (CI faalt bij drift)
make images smoke  # beide images bouwen en de rooktest draaien
make web-install web-lint web-test   # web-UI: npm ci, eslint + tsc, vitest
make web-e2e       # Playwright (360/390/768/1440, axe) tegen de echte API + fake TrueNAS
```

Details over de web-UI: [`apps/web/README.md`](apps/web/README.md).

`deploy/dev/compose.yaml` is alleen voor ontwikkeling/CI. Variabelen: [`.env.example`](.env.example) (geen echte
waarden; de Custom App heeft geen verplichte variabelen).

## Mappen

| Map | Inhoud |
|---|---|
| `apps/api` | Hub-API: `src/hub`, Alembic-migraties, unit- en integratietests |
| `apps/executor` | executor (eigen image/app) |
| `apps/web` | web-UI (Next.js-PWA), eigen webserver met API-doorgang, vitest en Playwright |
| `tests/e2e`, `tests/fakes` | dienst-E2E, teststack voor de web-E2E (`web_stack.py`) en de fake TrueNAS-WebSocketserver |
| `deploy/allinone`, `deploy/executor` | Dockerfiles, procesbewaker, healthchecks |
| `deploy/truenas` | formuliervelden van de twee Custom Apps |
| `deploy/manifest` | manifesten (manifeststandaard v1, `install.method: custom_app`) |
| `policy/` | risicobeleid (volgt in P2) |
| `docs/openapi`, `docs/adr` | OpenAPI-export en besluiten (ADR's) |
| `docs/screenshots/p0` | schermafbeeldingen (mobiel en desktop) uit de Playwright-suite |
| `docs/platform-v2` | pakketdocumentatie, contracten, Excel-taken en `EVIDENCE.json` |

Geen licentie toegevoegd (contract §10: alleen na vraag aan de gebruiker).
