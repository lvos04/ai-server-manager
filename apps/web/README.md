# Hub-web-UI (`apps/web`)

De centrale, Nederlandstalige web-UI van het platform (B01): Next.js (App Router, TypeScript) als PWA. In de
alles-in-één image luistert hij op poort **30400** en zet hij `/api/*`, `/connector/*`, `/healthz` en `/readyz` door
naar de interne Hub-API op `127.0.0.1:8400`. Zie [ADR-0009](../../docs/adr/ADR-0009-web-ui.md).

## Schermen (fase P0)

| Pad | Inhoud | Bron |
|---|---|---|
| `/eerste-start` | setupcode (uitleg: TrueNAS → Apps → ai-server-manager → Logs) → eerste beheerder | `POST /api/v1/setup/admin` |
| `/inloggen` | inloggen; uitloggen via de gebruikersbalk/Instellingen | `/api/v1/auth/*` |
| `/` Home | systeemstatus + "wat actie nodig heeft" + kaarten (waarde, eenheid, bron, laatst bijgewerkt, vervolgstap) | inventaris, besluiten, gates, dekking, audit |
| `/onboarding` | voortgang, stappen, besluiten D01–D18, gates | `/api/v1/decisions`, `/api/v1/gates` |
| `/onboarding/besluit/Dxx` | uitleg, gate, status, schemaformulier zonder voorbeeldwaarden, meten, bewijs, status | `/api/v1/decisions/{id}` |
| `/onboarding/truenas` | NAS-adres (D03), alleen-lezen-key, verbindingstest, vingerafdruk bevestigen, inventaris + metingen | `/api/v1/truenas*` |
| `/onboarding/executor` | uitleg tweede Custom App; koppelen volgt in P2 (status eerlijk onbekend) | — |
| `/server` | inventaris alleen-lezen: systeem, pools, datasets, apps, GPU's, schijven/SMART, snapshot-taken, meldingen, netwerk | `/api/v1/inventory*` |
| `/apps` | apps volgens TrueNAS + deep-link naar hun eigen UI (dienstenregister) | inventaris, `/api/v1/registry/services` |
| `/backups` | back-upgate, dekking per app en dataset, eigen Hub-back-up | `/api/v1/backups/*`, gates |
| `/instellingen` | account, wachtwoord, thema, sessies, gebruikers (admin), auditspoor (admin), PWA-status | `/api/v1/auth/*`, `/api/v1/users`, `/api/v1/audit` |
| `/problemen` (P1), `/ai` (P2), `/automatisering` (P2), `/media` (P3/P4), `/huis` (P3), `/netwerk` (P5), `/kosten` (P5) | "Nog niet beschikbaar (volgt in fase Px)" — geen nepdata | — |

Navigatie volgens `01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`: onder 1024 px een ondernavigatie (Home, Apps, Problemen,
AI, Meer), vanaf 1024 px een zijbalk (Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten,
Instellingen).

## Regels die de UI afdwingt

- Elke waarde toont **bron** en **laatst bijgewerkt**; niet (vers) gemeten = **onbekend**, nooit groen. Bij een fout
  verdwijnen oude gegevens in plaats van als actueel te blijven staan.
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
Projecten: `opzet` (eerste start, inloggen, TrueNAS-koppeling, metingen) → `mobiel-360`, `mobiel-390`, `tablet-768`,
`desktop-1440` (navigatie, axe, horizontaal scrollen, aanraakdoelen ≥ 44 px, donker thema) → `afsluiting` (NAS offline,
browser offline + service worker, rolrechten, vervalste `X-Forwarded-For`). Schermafbeeldingen:
`docs/screenshots/p0/<project>/`.

Tegen de alles-in-één image (zelfde suite):

```sh
docker run -d --name asm-web-e2e --network host -e HUB_PORT=39410 -e HUB_INTERNAL_API_PORT=39411 \
  -v "$(mktemp -d)":/appdata ai-server-manager:dev
HUB_E2E_BASE_URL=http://127.0.0.1:39410 \
HUB_E2E_SETUP_CODE="$(docker logs asm-web-e2e 2>&1 | grep -o 'SETUPCODE[^:]*: [A-Z0-9-]*' | tail -1 | awk '{print $NF}')" \
  npx playwright test
```

(`--network host` alleen hier, zodat de container de fake TrueNAS op de testmachine bereikt.)

### Schemafixture

`tests/unit/fixtures/decision-schemas.json` is een kopie van de besluitschema's uit de API
(`make web-schema-fixture`). `apps/api/tests/unit/test_web_schema_fixture.py` faalt als hij afdrijft.

Validatie: **Sim-getest** (fake TrueNAS) en in Docker; **NIET GEVALIDEERD** op een echte NAS, een Android-telefoon of
een tv/speler.
