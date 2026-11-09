# Peil-ontwerpreview van de echte Hub-UI

Gereedschap van de onafhankelijke ontwerpreview (`docs/ontwerp/PEIL_REVIEW.md`). Het meet de **gebouwde** Hub-UI en
de executor-statuspagina, niet de prototypes. Alleen voor ontwikkeling en CI: het draait tegen de web-E2E-teststack
(echte Hub-API, worker en database, met simulators voor TrueNAS, Uptime Kuma, Beszel, Gotify en een OIDC-issuer).
Alles is dus **Sim-getest**. Niets hiervan is gevalideerd op een echte NAS, telefoon of schermlezer.

## Wat er gemeten wordt

Elk scherm wordt gemeten op 320, 360, 390, 768, 1024 en 1440 px, in licht en donker. Dat zijn alle schermen van
beheerder, kijker en kind, de publieke pagina's, het open gebruikersmenu, NAS offline (verouderd) en browser offline.

| Controle | Eis (Peil §12) | Hard? |
|---|---|---|
| axe-core, tags `wcag2a/aa`, `wcag21a/aa` en `wcag22aa` | 0 overtredingen | ja |
| Gerenderd tekstcontrast (met opacity, `color-mix` en de donkerste arceerpixel) | ≥ 4,5:1, groot ≥ 3:1 | ja |
| Veldranden en stippelranden (Onbekend/Verouderd) | ≥ 3:1 | ja |
| Aanraakdoelen; inline links in een zin tellen niet mee | ≥ 44 × 44 px | ja |
| Lettergrootte | ≥ 14 px | ja |
| Horizontale overloop, afkappen met een ellips, overlappende tekst | geen | ja |
| Tab-doorloop op 390 en 1440: ring aanwezig, ring ≥ 3:1, niet bedekt door kop- of ondernavigatie | volledig | ja |
| Eén h1, geen kopsprongen, geen dubbele id's, geen kapotte `aria-*`-verwijzingen | — | ja |
| Onbekend of verouderd in een groen element | nooit | ja |
| Statusvorm zonder woord of naam (alleen kleur) | nooit | ja |
| Groen zonder het woord "Gezond", statusvorm zonder icoon, woordenlijst (§11), focusring afgesneden door een scrollkader | — | nee, handmatig beoordelen |

Uitklapblokken (`details`) worden ook open gemeten. De woordenlijstcontrole slaat code en mono over, want dat zijn
technische waarden.

## Draaien

```bash
make web-build            # productie-build (de review gebruikt server/hub-server.mjs, net als de image)
make web-review           # start de teststack, doet de opzet (e2e/00–01) en de review, en vat streng samen
```

`make web-review` faalt bij een harde bevinding. De schermafdrukken (`review/uit/shots/<breedte>/<scherm>-<thema>.jpg`)
en de ruwe metingen (`review/uit/metingen-*.json`) komen niet in Git.

### Tijdens het repareren

Laat de stack en de web-server draaien en meet daarna alleen wat je wilt zien:

```bash
# eenmalig: API-stack (eigen database) en de web-server op vaste poorten
HUB_E2E_API_PORT=39451 HUB_E2E_CONTROL_PORT=39452 HUB_E2E_STATE_DIR=$PWD/e2e/.state ../../.venv/bin/python ../../tests/e2e/web_stack.py &
PORT=39450 HOSTNAME=127.0.0.1 HUB_API_URL=http://127.0.0.1:39451 node server/hub-server.mjs &
export HUB_E2E_WEB_PORT=39450 HUB_E2E_API_PORT=39451 HUB_E2E_CONTROL_PORT=39452 HUB_E2E_STATE_DIR=$PWD/e2e/.state
npx playwright test -c playwright.review.config.ts --project opzet      # één keer per database
# daarna, zo vaak als nodig (na elke `next build` de web-server herstarten):
PEIL_REVIEW_ZONDER_OPZET=1 PEIL_REVIEW_ALLEEN='^(home|apps)$' PEIL_REVIEW_BREEDTES=320,1440 \
  npx playwright test -c playwright.review.config.ts --project review
node review/samenvat.mjs
```

Wil je de executor-statuspagina ook meten? Start dan de executor (`python -m executor api` met
`EXECUTOR_DATA_DIR`, `EXECUTOR_PORT`, `EXECUTOR_HOST=127.0.0.1` en `EXECUTOR_ALLOW_LOOPBACK_HUB=true`) en zet
`PEIL_REVIEW_EXECUTOR_URL=http://127.0.0.1:<poort>`.

## Bestanden

- `00-gebruikers.spec.ts`: maakt kijker en kind één keer aan (project `review-opzet`), vóór de parallelle breedtes.
- `peil-review.spec.ts`: schermen, rollen, toestanden en de meetlus. Elke breedte is één test; drie draaien tegelijk.
- `in-pagina.js`: de metingen in de pagina (init-script, gewone JavaScript). Afgeleid van
  `design/ontwerptaal/bouw/controle.cjs` en aangevuld met de Peil-semantiek, de woordenlijst en tekstoverlap.
- `samenvat.mjs`: samenvatting per scherm over alle breedtes en thema's (`--json`, `--streng`).
- `../playwright.review.config.ts`: dezelfde teststack als de web-E2E; servers die al draaien worden hergebruikt.
