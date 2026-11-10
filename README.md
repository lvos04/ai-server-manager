# ai-server-manager — centrale Hub van TrueNAS Home Platform V2

De Hub van het platform: **B01** (centrale web-UI en beheer-API), **B02** (AI-beheer met risicobeleid en executor),
**B09** (monitoring/incidenten) en **B12** (back-up en herstel). Taal: Nederlands. Bron van waarheid voor de
platformcontracten: [`docs/platform-v2/PLATFORM_CONTRACTEN.md`](docs/platform-v2/PLATFORM_CONTRACTEN.md) (versie 1.3,
vastgesteld 2026-11-10, ADR-0027; reviewcorrecties ADR-0028; wat elke repo moet veranderen:
[`CONTRACT_1.3_CONFORMITEIT.md`](docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md)). De Hub en de executor volgen
contract 1.3 voor alle punten die hoofdstuk 1 van die lijst als **NU** markeert (ADR-0029), ook de eigen manifesten
(C1.3-ASM-17, `--strict` geldig met de validator van appstore-en-fork); de punten voor P2–P5 (C1.3-ASM-18…22) staan
open in [`docs/platform-v2/EVIDENCE.json`](docs/platform-v2/EVIDENCE.json). De statuspagina van de executor en de Hub-UI
volgen Peil 1.1.1.

## Stand (versie 0.1.0, fase P0 + P1 + contract 1.3 — backend en web-UI)

Contract 1.3 in deze repo (ADR-0029): enroll-antwoord `"1.3"` met `rotation_sequence` en een tolerante `base_url`;
oude tokens pas ingetrokken bij het eerste gebruik van een nieuw token; vingerafdruk over alle policy-sleutels;
`100.64.0.0/10` standaard niet privé (beheerinstelling); 401 alleen voor authenticatie; vaste leesscopes per dienst;
paginering over een momentopname; inbox met domeinen per eigenaar, vaste werkwoorden en ernst in vijf woorden;
`sso.access.*` op (`issuer`, `sub`); connector-health = slechtste check en versheid met `max_age`; log-sink met
zichtbaar ingekorte opslag; healthchecks die als eerste naar 568 wisselen en een lege bounding set; de executor als
dienst (adresregels, onleesbaar koppelbestand fail-closed, herkomst- en `Host`-regels, JWT-regels). Alles Sim-getest;
niets op een echte NAS.

| Onderdeel | Stand | Validatie |
|---|---|---|
| Hub-API (`apps/api`, pakket `hub`) | first-start-init, setupcode → eerste admin, login/rollen/CSRF, JWKS + gebruikers-JWT (`token_use: user`) en dienst-JWT (`token_use: hub_service`), enrollment volgens contract 1.3 (exact schema met `rotation_sequence`, tolerante `base_url`, vingerafdruk, toegestane herhaling, `services/self`, rotatie na eerste gebruik, rotatie aanvragen, ontkoppelen via de dienst), noodlogin met TOTP, onboarding-wizard D01–D18, gates, alleen-lezen TrueNAS-inventaris, dienstenregister met bevestigde TrueNAS-appnaam, back-updekking, eigen pg_dump, events-inbox, connectorcontract | Sim-getest (fake TrueNAS), echte PostgreSQL 16 |
| Executor (`apps/executor`) | healthz/readyz, statuspagina (Peil 1.1.1) met koppelen (koppelcode + Hub-vingerafdruk, pinning in `hub-link.json`, herkomst- en `Host`-regels van contract 1.3 §3.7), onleesbaar koppelbestand fail-closed, controle van inkomende Hub-JWT's (§4.7, `jti` per POST), allowlist die **alles weigert**; TrueNAS-schrijfkey volgt in P2 | Unit-getest + Sim-getest tegen de echte Hub-API + browsertest + image-rooktest |
| Web-UI (`apps/web`, Next.js-PWA, ontwerptaal Peil) | "TrueNAS Home Platform": eerste start, inloggen (+ SSO-knop, noodlogin), onboarding D01–D18, TrueNAS-koppeling, Home met P1-bronnen, Server (inventaris, metrieken, meetdekking, logs), appcatalogus + appdetail, Problemen-inbox + incidentdetail, Backups, Instellingen (account, toegang/SSO, noodaccount, diensten, monitoring en meldingen, audit, over), kindschil; latere fasen eerlijk "nog niet beschikbaar" (ADR-0024) | Unit-getest (vitest) + Sim-getest (Playwright 360/390/768/1440 × licht/donker + axe tegen simulators, ook tegen de image) |
| Images | `deploy/allinone` (Hub + web-UI, alles-in-één, één poort 30400) en `deploy/executor` | gebouwd en gestart in Docker; **NIET GEVALIDEERD (echte NAS)** |
| Policy/AI | volgt in P2; AI staat standaard uit, geen modellen, geen betaalde aanroepen | — |
| P1 deel 1 (backend, ADR-0021) | **appcatalogus** (B01-002: identiteit = TrueNAS-app-id, idempotente discovery, installatiewijze, image/tag/digest + readback, opslag → dataset, deep-link, appstore-koppeling), **gezondheidsmodel** (truenas/buitenkant/binnenkant, verouderd = unknown), **bronnen** Uptime Kuma, Beszel (alleen het NAS-systeem), connector-health en heartbeat van eigen diensten (B09-002), **tijdreeksen** ruw → 5 min → 1 uur met retentie, **alerts** met drempel/duur/hysterese en **Gotify**-meldingen zonder pushstorm (B09-003, `notification.send` R0), **live NAS-metingen** uit `reporting.realtime` (B01-004) en **meetdekking** (B09-001). Uitleg: [`docs/MONITORING.md`](docs/MONITORING.md) | Sim-getest (fakes TrueNAS, Uptime Kuma, Beszel, Gotify, appstore, eigen dienst); **NIET GEVALIDEERD** tegen echte installaties; UI-schermen volgen in de P1-webstap |
| P1 deel 2 (backend, ADR-0022/0023) | **incidenten-inbox** (B01-005: dedupe/correlatie per vingerafdruk, herstel sluit alleen het eigen incident, heropenen, erkennen/snooze met verval, escalatie, readback bij oplossen, hypothese met zekerheid en bewijs of "ik weet het niet"), **log-index** (B09-004: alleen geschoond — geheimen, tokens, IP-adressen — begrensd, met trace_id en supportbundel), **out-of-band** (B09-005: Hub niet in het meldpad van Uptime Kuma; EX23 nooit "gedekt"), **runbooks** (B09-006: acht getypeerde scenario's, veilige modus), **SSO-login via OIDC** (B01-006: code + PKCE, groep→rol, sessie-intrekking, noodlogin blijft werken) en een **append-only auditspoor met hash-ketting**. Uitleg: [`docs/INCIDENTEN.md`](docs/INCIDENTEN.md), [`docs/RUNBOOKS.md`](docs/RUNBOOKS.md), [`docs/SSO.md`](docs/SSO.md) | Sim-getest (fakes OIDC/Authentik, home-control-hub, Uptime Kuma, Gotify, TrueNAS); **NIET GEVALIDEERD** tegen echte Authentik/Kuma/Gotify/NAS; UI-schermen volgen in de P1-webstap |

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
| `tests/e2e`, `tests/fakes` | dienst-E2E, teststack voor de web-E2E (`web_stack.py`), de fake TrueNAS-WebSocketserver en HTTP-fakes (Uptime Kuma, Beszel, Gotify, appstore, eigen dienst) |
| `deploy/allinone`, `deploy/executor` | Dockerfiles, procesbewaker, healthchecks |
| `deploy/truenas` | formuliervelden van de twee Custom Apps |
| `deploy/manifest` | manifesten (manifeststandaard v1, `install.method: custom_app`) |
| `policy/` | risicobeleid (volgt in P2) |
| `docs/openapi`, `docs/adr` | OpenAPI-export en besluiten (ADR's) |
| `docs/screenshots/p0` | schermafbeeldingen (mobiel en desktop) uit de Playwright-suite |
| `docs/platform-v2` | pakketdocumentatie, contracten, Excel-taken en `EVIDENCE.json` |

Licentie: **GPL-3.0** (zie [`LICENSE`](LICENSE); besluit van de eigenaar, 2026-11-09).
