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

## Schermen

| Pad | Inhoud | Bron |
|---|---|---|
| `/eerste-start`, `/inloggen`, `/inloggen/nood` | setupcode → eerste beheerder; inloggen (+ SSO-knop als aan, `sso_fout`-meldingen); noodlogin (alleen privé-adressen) | `/api/v1/setup/*`, `/api/v1/auth/*`, `/api/v1/auth/break-glass/login` |
| `/` Home | systeemstatus (Peil-totaal) + "wat actie nodig heeft" + kaarten met P1-bronnen | catalogus, incidenten, monitoring, meldingen, inventaris, gates, dekking, audit |
| `/onboarding…` | besluiten D01–D18, TrueNAS-koppeling, executor (koppelcode 30 min) | `/api/v1/decisions`, `/api/v1/truenas*`, `/api/v1/services/pairing-codes` |
| `/server`, `/server/metrieken`, `/server/meetdekking`, `/server/logs` | inventaris; live metingen en grafieken; dekking per metriek × bron; log-index (operator) | `/api/v1/inventory*`, `/observability/nas`, `/metrics/*`, `/monitoring/coverage`, `/logs*` |
| `/apps`, `/apps/[id]?tab=…` | appcatalogus; appdetail met gezondheid per onderdeel en tabs (acties volgen in P2) | `/api/v1/apps*` |
| `/problemen`, `/problemen/[id]` | incidenten-inbox en -detail | `/api/v1/incidents*` |
| `/backups` | back-upgate met voorwaarden, vier appmeldingen, dekking per app en dataset, eigen Hub-export | `/api/v1/backups/*`, gates |
| `/backups/herstelpunten`, `/backups/extern` | punten per app met RPO, databasebewijs en leeftijd, afzonderlijke stand en eindtijd van D04-uploadtaken | `/api/v1/backups/herstelpunten`, `/coverage` en `/extern` onder dezelfde prefix |
| `/backups/hersteltests`, `/backups/rampenscenarios` | zandbakproef voor de beheerder, bewijsrecords voor de kijker en stappen per scenario | Hub-acties en de back-uproutes `restore-tests`, `herstelpunten/{id}/hersteltest` en `rampenscenario` |
| `/automatisering` | flows, flowdetail, testmodus, ontvangen eventtypen, actieverzoeken en flowherstel | diensteninventaris, `/api/v1/events` en `/api/v1/actions` |
| `/instellingen/…` | account · toegang (rollen, sessies, SSO) · noodaccount (H6) · diensten (H5) · monitoring en meldingen · apparaat · audit · over | `/api/v1/auth/*`, `/users`, `/sessions`, `/services*`, `/monitoring/*`, `/notifications*`, `/audit*` |
| `/kijken`, `/zoeken`, `/ik` | kindschil (alleen rol kind) | — |
| `/ai` (P2), `/media` (P3/P4), `/huis` (P3), `/netwerk` (P5), `/kosten` (P5) | "Nog niet beschikbaar — volgt in fase Px" — geen nepdata | — |

Navigatie volgens `01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`: onder 1024 px een ondernavigatie (Home, Apps, Problemen,
AI, Meer), vanaf 1024 px een zijbalk (Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten,
Instellingen) met een kopbalk (Problemen-teller, AI, gebruikersmenu).

### Back-ups en automatisering (S-P2-190)

Bij **Backups → Hersteltests** kiest de beheerder een herstelpunt. **Nieuwe hersteltest** opent de R1-actie-preview voor een kloon in de zandbak. Bij meerdere datasets doorloopt de beheerder deze stap voor elke dataset. Na het uitvoeren van de kloon kan de beheerder terug naar Hersteltests. De Hub start de robot met de ID’s van de uitgevoerde kloonverzoeken. De robot controleert de kloon, de database en de ongewijzigde productie. Het directe antwoord bevat het deelbewijs. De blijvende lijst bevat afzonderlijke bewijsrecords. Bij een onduidelijk antwoord leest de Hub eerst de lijst opnieuw.

De automatiseringshistorie toont per verzoek de beleidsklasse, de goedkeuringsvereiste en het verloop. **Bekijk actie-preview** opent het bestaande verzoek. Bij flowherstel levert de API de momentopname-ID pas in het gecontroleerde resultaat van de eigenaar. De beheerder kan een voorgestelde monitorregel in **Instellingen → Monitoring** handmatig bevestigen na overname in Uptime Kuma. De bevestiging hoort bij de hash van die regel en heeft een neutrale badge.

De Hub heeft geen browserroute voor de flowdefinities, droogtest, volledige runhistorie, momentopnamelijst of geverifieerde editorbestemming. De tijd van een inventarislezing staat apart van de ontbrekende flowmeettijd. Ook de oefendatum per rampenscenario, het blijvend opvraagbare robotdeelbewijs en de bestandstelling en versleuteling van een externe upload zijn nog niet beschikbaar. De schermspecificatie staat in `docs/ontwerp/HUB_P2_ONTWERP.md`, S-110 t/m S-115 en S-120 t/m S-127.

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
`HUB_E2E_SHOTS=<map>` schrijft ze naar een andere map; P3 (Diensten, Media, Huis, Kosten en de toestanden van Media
en koppelen via `HUB_MEDIA_SHOTS` en `HUB_KOPPELSCHERM_SHOTS`) staat in `docs/screenshots/p3/`.

Met `HUB_E2E_SHOTS=p2 make web-e2e` vanuit de repo-root legt de suite de P2-schermen vast zodra hun testtoestand
zichtbaar is. De map `docs/screenshots/p2/` bevat ook de huidige appcatalogus en AI-pagina in beide thema’s. Het monitorplan
toont twee synthetische planregels als afzonderlijk paneel. De browser schrijft JPEG-bestanden. Zet ze vanuit de
repo-root met Pillow om naar het WebP-formaat van de ingecheckte afdrukken.

```sh
python3 - <<'PY'
from pathlib import Path
from PIL import Image

for bron in Path("docs/screenshots/p2").glob("*/*.jpg"):
    with Image.open(bron) as beeld:
        beeld.save(bron.with_suffix(".webp"), quality=84, method=4)
PY
```

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

Met `HUB_E2E_BASE_URL` meldt Playwright de proef **SSO via HTTPS** als overgeslagen. De image-opstelling
heeft geen vertrouwde testproxy. Draai `make web-e2e` zonder `HUB_E2E_BASE_URL` voor de lokale opstelling met
die proxy. Daar toont de HTTP-pagina geen geheimveld en bewijst de HTTPS-proef dat het clientgeheim wordt
opgeslagen en de testlogin slaagt. De dienst-E2E-proef `test_geheim_http_geweigerd_zonder_mutatie` controleert
de HTTP-weigering door de API.

### Schemafixture

`tests/unit/fixtures/decision-schemas.json` is een kopie van de besluitschema's uit de API
(`make web-schema-fixture`). `apps/api/tests/unit/test_web_schema_fixture.py` faalt als hij afdrijft.

Validatie: **Sim-getest** (simulators) en in Docker; **NIET GEVALIDEERD** op een echte NAS, een Android-telefoon, een
tv/speler, met een echte schermlezer, of tegen een echte Authentik, Uptime Kuma, Beszel of Gotify.
