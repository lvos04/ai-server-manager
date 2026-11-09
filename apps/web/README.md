# Hub-web-UI (`apps/web`)

De centrale, Nederlandstalige web-UI van **TrueNAS Home Platform** (B01): Next.js (App Router, TypeScript) als PWA. In de
alles-in-één image luistert hij op poort **30400** en zet hij `/api/*`, `/connector/*`, `/healthz` en `/readyz` door
naar de interne Hub-API op `127.0.0.1:8400`. Zie [ADR-0009](../../docs/adr/ADR-0009-web-ui.md).

## Ontwerptaal

Peil 1.1.0 (ADR-0015, [ADR-0024](../../docs/adr/ADR-0024-hub-ui-in-peil-en-p1-schermen.md)): Tailwind CSS 4 met alleen
tokenkleuren uit `src/app/peil/ontwerptaal.css` (versie-gepinde kopie van `design/ontwerptaal/ontwerptaal.css`; opnieuw
maken met `node scripts/peil-kopie.mjs`), shadcn/ui-componenten in `src/components/ui` (met de Peil-codemod) en
lucide-react. Platformcomponenten: `StatusBadge` (C-03/C-03a), `StatCard` (C-05), `Freshness` (Versheid C-06),
`ErrorPanel` (C-14) + `KopieerVeld` (C-15), `NotYetAvailable` (C-12/C-12a), `Loading` (C-18), `PageHeader` + kruimelpad
(C-02), `ResponsiveList` (C-34), `Subnav` (C-62), `Controles` (C-58), `Aftellen` (C-22), `LineChart` (C-32, recharts).
Productnaam: **TrueNAS Home Platform**; "Hub" is de centrale app daarin.

## Schermen (P0 + P1 + contract 1.2)

| Pad | Inhoud | Bron |
|---|---|---|
| `/eerste-start`, `/inloggen`, `/inloggen/nood` | setupcode → eerste beheerder; inloggen (+ SSO-knop als aan, `sso_fout`-meldingen); noodlogin (alleen privé-adressen) | `/api/v1/setup/*`, `/api/v1/auth/*`, `/api/v1/auth/break-glass/login` |
| `/` Home | systeemstatus (Peil-totaal) + "wat actie nodig heeft" + kaarten met P1-bronnen | catalogus, incidenten, monitoring, meldingen, inventaris, gates, dekking, audit |
| `/onboarding…` | besluiten D01–D18, TrueNAS-koppeling, executor (koppelcode 30 min) | `/api/v1/decisions`, `/api/v1/truenas*`, `/api/v1/services/pairing-codes` |
| `/server`, `/server/metrieken`, `/server/meetdekking`, `/server/logs` | inventaris; live metingen en grafieken; dekking per metriek × bron; log-index (operator) | `/api/v1/inventory*`, `/observability/nas`, `/metrics/*`, `/monitoring/coverage`, `/logs*` |
| `/apps`, `/apps/[id]?tab=…` | appcatalogus; appdetail met gezondheid per onderdeel en tabs (acties volgen in P2) | `/api/v1/apps*` |
| `/problemen`, `/problemen/[id]` | incidenten-inbox en -detail | `/api/v1/incidents*` |
| `/backups` | back-upgate, dekking per app en dataset, eigen Hub-back-up | `/api/v1/backups/*`, gates |
| `/instellingen/…` | account · toegang (rollen, sessies, SSO) · noodaccount (H6) · diensten (H5) · monitoring en meldingen · apparaat · audit · over | `/api/v1/auth/*`, `/users`, `/sessions`, `/services*`, `/monitoring/*`, `/notifications*`, `/audit*` |
| `/kijken`, `/zoeken`, `/ik` | kindschil (alleen rol kind) | — |
| `/ai` (P2), `/automatisering` (P2), `/media` (P3/P4), `/huis` (P3), `/netwerk` (P5), `/kosten` (P5) | "Nog niet beschikbaar — volgt in fase Px" — geen nepdata | — |

Navigatie volgens `01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`: onder 1024 px een ondernavigatie (Home, Apps, Problemen,
AI, Meer), vanaf 1024 px een zijbalk (Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten,
Instellingen) met een kopbalk (Problemen-teller, AI, gebruikersmenu).

## Regels die de UI afdwingt

- Elke waarde toont **bron** en **bijgewerkt**; niet (vers) gemeten = **onbekend**, nooit groen. Bij een fout blijft de
  laatst bekende waarde staan als **verouderd** (gedempt, "Laatst bekend · 10:12", status Onbekend) — nooit als actueel.
- Groen alleen voor *gemeten en goed*; Gekoppeld, Draait, Geslaagd en Aan zijn neutraal; dichte gates zijn geen storing.
- Formulieren starten leeg; verplichte ja/nee-vragen hebben geen standaardantwoord. De server valideert altijd opnieuw;
  zijn meldingen worden per veld in het Nederlands getoond.
- Mutaties sturen `X-CSRF-Token` (uit cookie `hub_csrf`) en een `Idempotency-Key`; die werkt ook via `http://`
  (geen `crypto.randomUUID` nodig).
- De service worker bewaart alleen de app-schil, nooit API-gegevens. Hij is alleen actief via HTTPS of `localhost`.

## Ontwikkelen

```sh
cd apps/web
npm ci
HUB_API_URL=http://127.0.0.1:8400 npm run dev   # Next.js-ontwikkelmodus + API-doorgang (API apart starten)
npm run lint && npm run typecheck && npm test    # eslint (jsx-a11y strict), tsc, vitest
npm run build && PORT=3000 HUB_API_URL=http://127.0.0.1:8400 npm start
```

Vanuit de repo-root: `make web-install web-lint web-test web-build web-e2e web-audit`.

### E2E (Playwright)

`npx playwright test` start zelf `tests/e2e/web_stack.py` (echte Hub-API + worker in een tijdelijke database
`asm_web_e2e_<id>` op `HUB_TEST_ADMIN_URL`, plus de fake TrueNAS) en de productie-build via `server/hub-server.mjs`.
De teststack start ook simulators voor Uptime Kuma, Beszel, Gotify, een OIDC-issuer en een simulator-dienst, en draait
de periodieke worker-taken. Projecten: `opzet` (eerste start, inloggen, TrueNAS-koppeling, metingen; daarna P1-gedrag:
catalogus, bronnen, diensten, incidenten, noodaccount, SSO) → `mobiel-360`, `mobiel-390`, `tablet-768`, `desktop-1440`
(elk scherm in licht én donker: axe, horizontaal scrollen, aanraakdoelen ≥ 44 px) → `afsluiting` (NAS offline met
O-03, browser offline + service worker, rolrechten, kind, intrekken, vervalste `X-Forwarded-For`).
Schermafbeeldingen: `docs/screenshots/p1/<project>/<scherm>-<licht|donker>.webp` (P0: `docs/screenshots/p0/`).

Tegen de alles-in-één image (zelfde suite):

```sh
docker run -d --name asm-web-e2e --network host -e HUB_PORT=39410 -e HUB_INTERNAL_API_PORT=39411 \
  -e HUB_OUTBOUND_ALLOW_LOOPBACK=true \
  -v "$(mktemp -d)":/appdata ai-server-manager:dev
HUB_E2E_BASE_URL=http://127.0.0.1:39410 \
HUB_E2E_SETUP_CODE="$(docker logs asm-web-e2e 2>&1 | grep -o 'SETUPCODE[^:]*: [A-Z0-9-]*' | tail -1 | awk '{print $NF}')" \
  npx playwright test
```

(`--network host` en `HUB_OUTBOUND_ALLOW_LOOPBACK=true` alleen hier, zodat de container de simulators op de
testmachine bereikt; nooit in een echte installatie.)

### Schemafixture

`tests/unit/fixtures/decision-schemas.json` is een kopie van de besluitschema's uit de API
(`make web-schema-fixture`). `apps/api/tests/unit/test_web_schema_fixture.py` faalt als hij afdrijft.

Validatie: **Sim-getest** (simulators) en in Docker; **NIET GEVALIDEERD** op een echte NAS, een Android-telefoon, een
tv/speler, met een echte schermlezer, of tegen een echte Authentik, Uptime Kuma, Beszel of Gotify.
