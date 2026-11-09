# ai-server-manager — centrale Hub van TrueNAS Home Platform V2

De Hub van het platform: **B01** (centrale web-UI en beheer-API), **B02** (AI-beheer met risicobeleid en executor),
**B09** (monitoring/incidenten) en **B12** (back-up en herstel). Taal: Nederlands. Bron van waarheid voor de
platformcontracten: [`docs/platform-v2/PLATFORM_CONTRACTEN.md`](docs/platform-v2/PLATFORM_CONTRACTEN.md) (versie 1.1).

## Stand (versie 0.1.0, fase P0 — backend)

| Onderdeel | Stand | Validatie |
|---|---|---|
| Hub-API (`apps/api`, pakket `hub`) | first-start-init, setupcode → eerste admin, login/rollen/CSRF, JWKS + dienst-JWT, enrollment + service-tokens, onboarding-wizard D01–D18, gates, alleen-lezen TrueNAS-inventaris, dienstenregister, back-updekking, eigen pg_dump, events-inbox, connectorcontract | Sim-getest (fake TrueNAS), echte PostgreSQL 16 |
| Executor (`apps/executor`) | healthz/readyz, statuspagina "nog niet gekoppeld", allowlist die **alles weigert** | Unit-getest + image-rooktest |
| Images | `deploy/allinone` (Hub, alles-in-één) en `deploy/executor` | gebouwd en gestart in Docker; **NIET GEVALIDEERD (echte NAS)** |
| Web-UI (`apps/web`, PWA) | volgt (volgende stap); plek in de Dockerfile is gemarkeerd | — |
| Policy/AI | volgt in P2; AI staat standaard uit, geen modellen, geen betaalde aanroepen | — |

Echte NAS-, hardware- en accounttests zijn in deze bouwomgeving niet mogelijk. Zie
[`docs/platform-v2/EVIDENCE.json`](docs/platform-v2/EVIDENCE.json) voor de status per Excel-ID.

## Installeren (gebruiker)

Uitsluitend als **standaard TrueNAS Custom App** (formulier: image + tag, poort, opslag) — nooit via YAML of compose.
Twee formulieren: [`deploy/truenas/CUSTOM_APP.md`](deploy/truenas/CUSTOM_APP.md). De setupcode voor het eerste
beheerdersaccount staat in de app-log (TrueNAS → Apps → ai-server-manager → Logs).

## Ontwikkelen

```sh
make venv          # .venv met exact vastgezette versies + editable pakketten
make lint type     # ruff + mypy (strict)
make test          # unit + integratie (PostgreSQL op 127.0.0.1:5432) + dienst-E2E met fake TrueNAS
make openapi       # docs/openapi/*.openapi.json bijwerken (CI faalt bij drift)
make images smoke  # beide images bouwen en de rooktest draaien
```

`deploy/dev/compose.yaml` is alleen voor ontwikkeling/CI. Variabelen: [`.env.example`](.env.example) (geen echte
waarden; de Custom App heeft geen verplichte variabelen).

## Mappen

| Map | Inhoud |
|---|---|
| `apps/api` | Hub-API: `src/hub`, Alembic-migraties, unit- en integratietests |
| `apps/executor` | executor (eigen image/app) |
| `tests/e2e`, `tests/fakes` | dienst-E2E en de fake TrueNAS-WebSocketserver |
| `deploy/allinone`, `deploy/executor` | Dockerfiles, procesbewaker, healthchecks |
| `deploy/truenas` | formuliervelden van de twee Custom Apps |
| `deploy/manifest` | manifesten (manifeststandaard v1, `install.method: custom_app`) |
| `policy/` | risicobeleid (volgt in P2) |
| `docs/openapi`, `docs/adr` | OpenAPI-export en besluiten (ADR's) |
| `docs/platform-v2` | pakketdocumentatie, contracten, Excel-taken en `EVIDENCE.json` |

Geen licentie toegevoegd (contract §10: alleen na vraag aan de gebruiker).
