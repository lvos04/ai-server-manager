# Peil-ontwerpreview van de gebouwde Hub-UI en de executor-statuspagina

**Datum:** 9 november 2026 · **Rol:** onafhankelijke ontwerp-agent (contract 1.2 §13) · **Onderwerp:** de gebouwde
`apps/web` (stand `333de88`, P1-webstap) en de statuspagina van de executor (`apps/executor`), met alle schermen van
beheerder, kijker en kind, de publieke pagina's en de toestanden NAS offline en browser offline.
**Toetsing aan:** ontwerptaal Peil 1.1.0 (`docs/platform-v2/ONTWERPTAAL.md`, `design/ontwerptaal/COMPONENTEN.md`,
ADR-0015 met de besluiten van de gebruiker), de prototypes en afdrukken in `design/ontwerptaal/` en ADR-0024.
**Besluiten:** ADR-0025. **Gereedschap:** `apps/web/review/` (`make web-review`).

> **Eerlijkheid.** Alles hieronder is gemeten in Chromium (Playwright) tegen de echte Hub-API, met de worker en een
> eigen PostgreSQL-database. TrueNAS, Uptime Kuma, Beszel, Gotify, de OIDC-issuer en de simulator-dienst zijn
> simulators: **Sim-getest**. **NIET GEVALIDEERD:** echte schermlezer (NVDA/TalkBack), echte Android-telefoon in fel
> licht, tv, echte NAS en echte accounts.

## Oordeel

**Goedgekeurd na herstel.** De Hub-UI volgt Peil goed:

- statuswoorden, vormen en kleuren kloppen;
- groen komt alleen voor bij "gemeten en goed";
- onbekend en verouderd zijn nooit groen;
- de laatst bekende waarde staat gedempt in een gearceerd vak;
- de kindschil bestaat en de microcopy is rustig.

De review vond wel fouten die de bestaande Playwright-suite niet ziet:

- de grafieken toonden nooit gegevens en zeiden ten onrechte "Geen meting";
- focus zonder ring of achter een balk;
- een axe-fout bij het open gebruikersmenu;
- overloop op 1024;
- losse links kleiner dan 44 px;
- iconen en woorden die van Peil afweken.

Alles binnen het mandaat (uiterlijk, tekst en toegankelijkheid) is gerepareerd en opnieuw gemeten.

**Eén blokkerende fout viel buiten het mandaat:** koppelen via de statuspagina van de executor werkt in geen enkele
echte browser (N-01). Die is gereproduceerd en overgedragen, niet gerepareerd.

| | Nulmeting (vóór) | Na herstel |
|---|---|---|
| Schermen en toestanden | 59 | 59 |
| Metingen (scherm × breedte × thema) | 548¹ | 700 |
| Harde bevindingen (per scherm en soort) | 35¹ | **0** |
| axe-overtredingen (WCAG 2.2 A/AA) | 8 (`aria-hidden-focus`, serious) | **0** |
| Laagste gerenderde tekstcontrast buiten de toestand NAS offline (alle tekst AAA) | 7,61:1 | 7,61:1 |
| Laagste tekstcontrast, bewust gedempte laatst-bekende waarde (`--stale-ink` op arcering) | 4,56:1 (eis ≥ 4,5:1) | 4,56:1 licht, 5,01:1 donker |
| Laagste focusring (met halo) | 5,13:1 | 5,13:1 |
| Grafieken met gegevens | 0 (lus: ± 1300 aanvragen in 6 s) | alle reeksen met metingen (3 aanvragen in 6 s) |

¹ Bij de nulmeting draaide door een fout in de projectfilter de breedtetest van 320 en 768 nog een keer mee, terwijl
de NAS offline stond. Een deel van de JSON van 360, 390, 1024 en 1440 is daarbij overschreven. De twee bevindingen die
alleen op 1024 voorkwamen (R-05 en R-07) staan in de eerste volledige uitvoer en in de afdrukken
(`instellingen-monitoring` op 1024 was 1066 px breed). Daarom staat er 33 + 2 = 35. De filter is gerepareerd (de
review en de toestanden zijn nu aparte projecten).

## Werkwijze

- **Skills:**
  - `design:design-critique` (indruk, bruikbaarheid, hiërarchie, consistentie);
  - `design:accessibility-review` (WCAG 2.2 AA-structuur);
  - `design:ux-copy` (NL-microcopy tegen de woordenlijst van Peil §11);
  - `design:design-system` (audit op hardgecodeerde waarden);
  - `dataviz` (vóór elk oordeel over de grafieken, met de anti-patronenlijst);
  - `design:design-handoff` (COMPONENTEN.md §28).
- **Echte dienst met testgegevens.**
  - `tests/e2e/web_stack.py` (API, worker, database en simulators) en `server/hub-server.mjs` (dezelfde server als
    in de image), met een productie-build van `apps/web`.
  - De opzet uit `e2e/00–01` maakt de testgegevens: beheerder, TrueNAS-koppeling, inventaris, apps, 100 identieke
    events → één incident, diensten, noodaccount, SSO-gate en monitoringbronnen.
  - De review maakt daarna een kijker en een kind aan, via de echte API.
  - De executor draaide als echte dienst (`python -m executor api`), nog nooit gekoppeld.
- **Meten.** `apps/web/review/peil-review.spec.ts` + `in-pagina.js` (afgeleid van `design/ontwerptaal/bouw/controle.cjs`).
  - Per scherm × 320/360/390/768/1024/1440 × licht/donker: axe-core (WCAG 2.0/2.1/2.2 A+AA) en gerenderd
    tekstcontrast, met opacity, `color-mix` en de donkerste arceerpixel.
  - Daarnaast: veld- en stippelranden, doelen van ≥ 44 px (losse links tellen mee; inline links in een zin niet),
    lettergrootte, overloop, afkappen met een ellips en tekstoverlap.
  - Verder: Peil-semantiek (groen alleen met "Gezond", onbekend en verouderd nooit groen, statusvorm nooit zonder
    woord) en de woordenlijst.
  - Uitklapblokken worden ook open gemeten.
  - Op 390 en 1440 een volledige Tab-doorloop: ring aanwezig, ring ≥ 3:1 tegen de achtergrond, niet bedekt door
    kop- of ondernavigatie, en niet afgesneden door een scrollkader.
- **Bekijken.** 700 volledige-pagina-afdrukken per meting. Ik heb ze met Read bekeken, als kolommen naast
  elkaar, en vergeleken met de prototypes (`design/ontwerptaal/shots/*`). Een selectie voor/na staat in
  `docs/ontwerp/review/`.
- **Gedrag los gecontroleerd:**
  - de grafiek met pijltjes, End en Esc, met voorlezen;
  - het aantal aanvragen van de grafieken;
  - de focus in een datumveld (deelvelden en kalenderknop);
  - koppelen op de executor-statuspagina, met de headers van het verzoek.

## Bevindingen en reparaties

Ernst: **Blokkerend** · **Hoog** (WCAG-fout of onware uitspraak) · **Middel** (Peil-regel, bruikbaarheid) ·
**Laag** (afwerking). Alle reparaties zitten in `apps/web`, behalve waar anders staat.

| # | Ernst | Scherm (breedte) | Bevinding | Regel | Reparatie |
|---|---|---|---|---|---|
| R-01 | Hoog | Server → Metrieken, appdetail → Metrieken | Elke grafiek zei "Geen meting in deze periode", terwijl de API metingen had. `queryPath` zette `van` en `tot` op de milliseconde: het pad veranderde bij elke weergave en `useApi` haalde eindeloos opnieuw op (gemeten: 1357 aanvragen in 6 s). | Peil §1 (eerlijk), §10 | `van` op de hele minuut en geen `tot` (de Hub neemt "nu"); tijdens het laden "Meetreeks ophalen…" en bij een fout "Onbekend — …", nooit "Geen meting". Na herstel: 3 aanvragen in 6 s en een lijn met 6 punten. |
| R-02 | Hoog | Besluit D02/D03, veld "Uitgevoerd op" (alle breedtes) | Tab naar de kalenderknop in het datumveld gaf geen ring (`:focus-visible` geldt dan niet op het veld). | WCAG 2.4.7, Peil §12 | Peil-ring op `:focus-within` voor datum- en tijdvelden. |
| R-03 | Hoog | Kindschil, Ik (1024–1440) | "Intrekken" verdween bij Tab volledig achter de ondernavigatie: Peil zet de scroll-padding onder vanaf 1024 op 0,75 rem, maar de kindschil heeft daar ook een ondernavigatie. | WCAG 2.4.11 | `html:has([data-schil=kind])` krijgt de scroll-padding van de ondernavigatie. |
| R-04 | Hoog | Gebruikersmenu open (alle breedtes) | axe `aria-hidden-focus` (serious): het modale Radix-menu zet `aria-hidden` op de pagina met focusbare inhoud. | WCAG 4.1.2 | Menu niet-modaal; Esc, Tab en klikken buiten sluiten het. |
| R-05 | Hoog | Instellingen → Monitoring (1024) | Tabel Alertregels 42 px breder dan het scherm (naast de subnavigatie). | WCAG 1.4.10 | Tabel pas vanaf 1280, daaronder kaarten. |
| R-06 | Middel | 6 fase-schermen, 404, besluiten, Server, Metrieken, Backups, TrueNAS, appslijst | Losse links van 22–24 px hoog ("Terug naar Home", "Naar Home", "TrueNAS-koppeling", "Alle details per app", "Meetdekking per metriek en bron", "Leg RPO/RTO vast in D16", "← Terug naar de onboarding" en de app-namen in de lijst). | Peil §6 (44 px overal), WCAG 2.5.8 | Recept `.losse-link` (44 px); "← Terug" werd een kruimelpad; rijlink in de appslijst 44 px. |
| R-07 | Middel | Toegang → SSO "Groep → rol" (1024) | Groepsveld 26 px breed (drie kolommen in een smalle kolom). | Peil §6, WCAG 1.4.10 | Containerquery: naast elkaar pas vanaf 36 rem kolombreedte. |
| R-08 | Middel | Incidentdetail (< 1280) | Kopsprong h1 → h3 (en h4 in het stappenplan). | WCAG 1.3.1, Peil A-02 | Kopniveau volgt de context: eigen pagina h1/h2/h3, master-detail h2/h3/h4. |
| R-09 | Middel | Server → Metrieken | Op elke verse StatKaart een neutrale pil "✓ Gemeten", naast "· gemeten" bij het getal: een versheidsbadge. | Peil §4.4, K3 | Geen badge bij een verse waarde; alleen afwijkingen krijgen een pil. |
| R-10 | Middel | Zijbalk, ondernavigatie, Meer, kopbalk, Home | Iconen weken af van §7. Huis was hetzelfde huisje als Home, Backups `archive`, Kosten `euro`, Media `film`, Problemen `circle-alert`, AI `sparkles`, Meer `ellipsis`; op Home GPU `cpu`. | Peil §7, WCAG 3.2.4 | Vaste koppeling §7: `sofa`, `database-backup`, `wallet`, `clapperboard`, `inbox`, `bot`, `menu`, GPU `microchip`. |
| R-11 | Middel | Ik (kind), Account | Op Ik zag een kind IP-adressen, "gestart/verloopt" en een rode knop "Intrekken"; ook voor volwassenen was intrekken rood. | Peil A-19 (kind), §4.1 regel 2 | Kindvariant "Waar je bent ingelogd" ("Dit apparaat", "Uitloggen op dat apparaat"; IP achter "Details voor een volwassene"); intrekken is een gewone knop. |
| R-12 | Middel | Zijbalk (≥ 1024) | Focusring van de navigatielinks links en rechts afgesneden door het scrollkader. | WCAG 2.4.7/2.4.13 | Scrollkader 6 px ruimer dan de items. |
| R-13 | Middel | Server (alle) | De ankerlijst (Overzicht · Systeem · Pools …) zag er precies zo uit als de subnavigatie (Overzicht · Apps · Metrieken …): twee knoppenrijen met twee keer "Overzicht" en "Apps". | Peil §9 ("één tabrij"), hiërarchie | Lichte ankerlijst "Op deze pagina:" met onderstreepte links (C-64). |
| R-14 | Laag | Home, Logs, SSO, appdetail, Diensten, Server, Metrieken, Onboarding | Taal: "pool(s)", "kanaal/kanalen", "sleutel(s)", "regel(s)", "Data-dataset(s)", "0 dagen oud", "Klaar", "— unknown", "realtime: ok", "Geprobeerd … · stale", redencode als losse tekst, "—" voor "n.v.t.". | Peil §11 | Echte meervouden (`aantal()`); "van vandaag"; "Aangemaakt"; "geslaagd / deels gelukt / mislukt (stand onbekend)"; "live-meting … werkt"; "Reden `code`"; "Geprobeerd … · geen antwoord (`unreachable`)"; "n.v.t." of "onbekend". |
| R-15 | Laag | KopieerVeld (320–390) | Digest en URL stonden in een kolom van 12 tekens naast de knop (6 regels). | Peil §5 (codes breken, leesbaar) | Veld minstens 12 rem; anders springt de knop eronder. |
| R-16 | Laag | Appdetail, Monitoring | Iconen in een lange regel krompen tot een stip; de aan/uit-knop stond bij "Uptime over 30 dagen" en "Uitgelezen om". | Peil §7 | `svg.lucide` krimpt nooit; `info` en `check` in plaats van `power`. |
| R-17 | Laag | Metrieken, GPU's | Tekst "Geen meting — er is nog geen reeks." tegen de stippelrand. | afwerking | Opvulling en gecentreerd. |
| R-18 | Laag | Onboarding, besluitenlijst (390) | De pil "Ingevuld (nog niet getest)" werd een ovaal van drie regels. | afwerking | Rij loopt om: de pil komt onder de titel als hij niet past. |
| R-19 | Laag | Kind-403 | Tabtitel "Server — TrueNAS Home Platform" (een beheerterm voor een kind). | Peil A-19 | "Niet voor jou — TrueNAS Home Platform". |
| R-20 | Laag | Grafieken | Geen toetsenbord-draadkruis (afwijking in ADR-0024), geen eindpunt of direct label, geen arcering in een gat, geen bron en tijd bij de grafiek, dubbele patroon-id's per pagina, tabelregio niet met het toetsenbord bereikbaar. | Peil §10, C-32, A-08 | Volgens C-32 gebouwd (COMPONENTEN.md §28): pijltjes, Home, End en Esc, draadkruis, uitlezing en `aria-live`, eindpunt met label, gat "Geen meting", bronregel, `useId` en een benoemde regio. |
| R-21 | Laag | Backups (768) | Een lege tabel in een scrollkader was als focusdoel 40 px hoog. | Peil §6 | Scrollkader minstens 44 px. |
| R-22 | Laag | Problemen (≥ 1280) | Zonder gekozen incident alleen een lijst over de volle breedte; na een klik sprong de indeling naar master-detail. | Peil §9 | Ook zonder keuze master-detail met de regel "Kies links een incident…". |
| R-23 | Middel | Metrieken, Netwerk | Een gemeten kleine waarde las als 0: de tegel zei "0 Mbit/s" en de y-as "0, 0, 0, 0, 0" (één decimaal). | Peil §1 (nooit 0 voor iets dat niet 0 is), dataviz | Kleine waarden met 2 significante cijfers ("0,03 Mbit/s"), op de as en in de labels. |
| R-24 | Laag | Metrieken, Opslag | Poolmeter boven de drempel had alleen een kleur en een tekst zonder icoon; "Onbekend" stond als losse tekst. | Peil §4.2/§10 (nooit alleen kleur) | `triangle-alert` + "… gebruikt — boven de drempel van 90%" in `degraded-ink`; Onbekend als StatusBadge. |
| R-25 | Laag | Besluiten (schemaformulier) | "Verwijder" bij een rij in een nog niet opgeslagen formulier was een rode gevaarknop; de knop "Meet D01" stond in de gebiedende wijs. | Peil §4.1 regel 2, §11 | Gewone knop "Verwijderen" met prullenbak; "D01 meten". |
| R-26 | Middel | Monitoring (1024), Server bij NAS offline (320) | Met een breder systeemlettertype (DejaVu Sans, het standaardlettertype van de Ubuntu-runner in CI) liep het meldingenlogboek op 1024 9 px over. Op 320 liepen lange woorden zonder breekpunt ('pool.snapshottask.query', 'ConnectionRefusedError') 5 px over. Lokaal (Noto Sans) gebeurde dat niet. | WCAG 1.4.10, Peil §5 (systeemfont) | Logboektabel pas vanaf 1280; `main` krijgt `overflow-wrap: break-word`. De review kan een lettertype afdwingen (`PEIL_REVIEW_LETTER`); met DejaVu Sans: 0 harde bevindingen. |

R-26 vond pas de CI-run: daar is het systeemlettertype breder. Daarna is de volledige review lokaal ook met
DejaVu Sans gedraaid: 59 schermen en toestanden, 700 metingen, 0 harde bevindingen.

Tijdens het herstel kwam R-13 terug in een nieuwe vorm: de nieuwe ankerlinks waren 39–43 px breed. Dat is direct
gerepareerd (`min-w-touch`) en opnieuw gemeten.

### Niet gerepareerd (buiten het mandaat of een functionele toevoeging)

| # | Ernst | Bevinding | Waarom niet | Voorstel |
|---|---|---|---|---|
| N-01 | **Blokkerend** — opgelost in de QA-review (ADR-0026: `Referrer-Policy: same-origin`, exacte Origin blijft; browsertest in `e2e/90-afsluiting.spec.ts`) | **Executor: koppelen via de statuspagina mislukt in elke echte browser.** De pagina stuurt `Referrer-Policy: no-referrer`; bij een formulier-POST zet de browser dan `Origin: null`. `POST /koppelen` accepteert alleen `http(s)://<host>` en zegt "Geweigerd: het formulier komt niet van deze pagina." Gereproduceerd in Chromium: het verzoek had `Origin: null`. De pytest-client stuurt wel een Origin, dus de tests zagen dit niet. | Functionele en beveiligingscode van de executor; de ontwerp-agent repareert alleen uiterlijk, tekst en toegankelijkheid. | Zoals home-control-hub, appstore-en-fork, jelly-leon-platform en zoeken-en-persoonlijke-ai: `Origin: null` of een ontbrekende Origin accepteren en blijven vertrouwen op het CSRF-cookie (`SameSite=Strict`, HttpOnly) met de formuliertoken. Of de statuspagina `Referrer-Policy: same-origin` geven. Daarbij een browser-E2E-test (Playwright) op het koppelformulier. |
| N-02 | Middel | De kopbalk mist Zoeken (C-51) en de Live-indicator. | Functionele toevoeging (ADR-0024 punt 8); er is in P1 geen zoekindex of live-stroom. | In P2/P5 bouwen; tot dan geen schijnknop (zo is het nu ook). |
| N-03 | Laag | De tabs in het appdetail hebben geen iconen (het prototype wel). | Cosmetisch; de tabs zijn duidelijk. | Bij de volgende webstap `activity`, `chart-line`, `logs`, `tag` en `list-checks`. |
| N-04 | Laag | Nog een paar inline styles in P0-schermen (`DecisionScreen`, `ValueView`, `RefreshInventory`). Geen kleuren: alleen afstanden. | Fase 3 "opruimen" (ADR-0024 punt 3). | Vervangen door utilities. |
| N-05 | Laag | Gezondheid per onderdeel in het appdetail is op mobiel een stapel kaarten met de labels "Onderdeel/Status/Toelichting"; het prototype heeft compacte rijen (naam, bron, pil rechts). | Werkt en is toegankelijk; het is een dichtheidskeuze. | Compacte rijen zoals in `appdetail-p1.html` (minder scrollen op 360). |
| N-06 | Laag — opgelost in de QA-review (ADR-0026: 409 `username_taken`) | Backend: twee gelijktijdige `POST /api/v1/users` met dezelfde naam geven een 500 (UniqueViolation) in plaats van 409 `username_taken`. De controle "bestaat al" en de insert zijn niet atomair. Zo gevonden in CI-run 42711876495: drie reviewwerkers maakten tegelijk dezelfde kijker aan. | API-code, buiten het mandaat. | `IntegrityError` op `app_user_username_key` vertalen naar 409 `username_taken`. De review maakt de gebruikers nu één keer aan (`review-opzet`). |
| N-07 | Middel | Backend en capaciteit: met drie reviewbrowsers tegelijk in CI stond een pagina > 30 s op "Aanmelding controleren…" (run 42724137831; trace en screencast bekeken). De andere API-aanvragen in die trace duurden < 200 ms. **Vermoedelijke oorzaak (niet bewezen):** Home doet ± 16 API-aanvragen tegelijk, terwijl de API 10 databaseverbindingen heeft (`pool_size=5`, `max_overflow=5`, standaard 30 s wachten op een vrije verbinding). | Backend en capaciteit, buiten het mandaat. | De pool laten meegroeien met de threadpool, of één samengestelde Home-route. Tot dan draait de CI-review met 2 werkers en één herkansing. |

## Ontwerpkritiek (design-critique)

**Eerste indruk.** Op elk scherm valt eerst de status op: SysteemStatusPaneel, "Wat actie nodig heeft",
StatusBadge rechts in de kop. Dat klopt met Peil §1.2. Het rustige koele neutraal met inkt en één diep blauw leest
goed in licht en donker. De rode rand van het systeemstatuspaneel bij Storing is het sterkste signaal, en terecht.

**Bruikbaarheid.**

- Rollen: kijker en kind zien uitgeschakelde bediening met de reden ernaast. Het kind ziet een eigen, kleine wereld:
  Home · Kijken · Zoeken · Ik. Het kind ziet geen beheertermen meer, ook niet in de tabtitel of op Ik.
- Grafieken: tot R-01 nutteloos, nu bruikbaar met muis én toetsenbord.
- Server: de dubbele knoppenrij (R-13) was het grootste hiërarchieprobleem; nu is het duidelijk wat naar een andere
  pagina gaat en wat binnen de pagina springt.

**Visuele hiërarchie.** Paginakop h1 → intro → meta "Bijgewerkt … · vernieuwt elke … s" → acties. Kaarten hebben
titel, (alleen bij een afwijking) een pil, de waarde en de bron. Na R-09 hebben verse waarden geen pil meer, en dat
maakt Metrieken rustiger: alleen afwijkingen vallen op (Peil §1.4).

**Consistentie.**

- Hetzelfde begrip heeft overal hetzelfde woord en icoon (na R-10 en R-16).
- Status, ernst, zekerheid, validatie en gate hebben elk hun eigen vorm: pil, linkerbalk, drie stippen, gestippelde
  mono en slot.
- De executor-statuspagina is het exacte Peil-sjabloon, met "Gekoppeld" neutraal en "Niet gereed — deels onbekend"
  als eerlijke kop.

**Wat goed werkt.**

- O-03: de laatst bekende waarde staat gearceerd en gedempt (gemeten 4,56:1 licht, 5,01:1 donker; eis ≥ 4,5:1) met
  status Onbekend/Verouderd, en geen enkel groen element bij NAS offline.
- "Geen open problemen" verschijnt alleen bij verse monitoring.
- P2-acties zijn zichtbaar maar uit, met "Volgt in fase P2" en zonder schijn-risicoklasse.
- "Data verwijderen (R3) staat hier bewust niet."
- De foutpanelen hebben een kopieerbare trace-ID; de terugval voor kopiëren noemt geen Ctrl+C.
- Thema Systeem/Licht/Donker zet altijd het opgeloste thema; de focusring heeft een halo en haalt overal ≥ 5:1.

**Vergelijking met de prototypes.**

- Indeling en componenten volgen de prototypes voor Home, Apps, appdetail, Problemen (master-detail ≥ 1280),
  Metrieken, Diensten, Noodaccount, Instellingen (index + subnavigatie), kindschil en statuspagina.
- Bewuste afwijkingen uit ADR-0024:
  - geen Zoeken en geen Live in de kopbalk;
  - "Meer" als pagina in plaats van een sheet;
  - tabs zonder iconen.
- Onbewuste afwijkingen, nu gerepareerd: R-09 (badge "Gemeten" staat niet in het prototype), R-10 (iconen),
  R-20 (grafiek).

## Toegankelijkheid (accessibility-review, WCAG 2.2 AA)

| Criterium | Uitkomst na herstel | Hoe gemeten |
|---|---|---|
| 1.1.1, 1.3.1 | 0 axe-overtredingen; één h1 per scherm, geen kopsprongen, geen dubbele id's of kapotte `aria-*`-verwijzingen | axe-core 4.14 + structuurcontrole, alle schermen × 6 breedtes × 2 thema's |
| 1.4.3 / Peil 7:1 | Buiten NAS offline is elke tekst ≥ 7,61:1 (AAA). In NAS offline is alleen de bewust gedempte laatst-bekende waarde lager (4,56:1 licht, 5,01:1 donker; AA en de Peil-uitzondering) | gerenderd in de DOM, met de donkerste arceerpixel |
| 1.4.10 | Geen overloop van 320 tot 1440, ook niet met uitklapblokken open | `scrollWidth` − `clientWidth` |
| 1.4.11 | Veldranden en stippelranden ≥ 3:1 | gerenderd |
| 2.4.7 / 2.4.11 / 2.4.13 | Tab-doorloop op 390 en 1440: elke stop heeft een ring van 3 px + 2 px halo (≥ 5,13:1), nooit volledig bedekt en nooit afgesneden | volledige Tab-doorloop, `elementFromPoint` op 5 punten |
| 2.5.8 / Peil 44 px | Elk bedienbaar element ≥ 44 × 44 px, ook losse links; inline links in een zin zijn uitgezonderd | gemeten per element |
| 4.1.2 | Menu, tabs en grafiek hebben een naam, rol en waarde; het grafiekplotvak is `role=img` met samenvatting, en de waarde per punt komt via `aria-live` | axe + gedragstest |

**Toetsenbord.**

| Element | Tab | Enter/Spatie | Esc | Pijltjes |
|---|---|---|---|---|
| Skiplink "Naar de inhoud" | eerste stop | naar `main` | — | — |
| Gebruikersmenu | stop | opent | sluit | door de items |
| Tabs in het appdetail | één stop (roving) | — | — | ← → Home End |
| Grafiekplotvak | stop (ring om het plotvak) | — | wist het draadkruis | ← → per punt, Home/End; voorlezen "22:45: 23,5%" of "Geen meting" |
| "Toon als tabel" | stop | klapt open | — | scrollregio met naam is een stop |
| Datumveld | dag, maand, jaar, kalender | — | — | ring op het hele veld (R-02) |

**Schermlezer (niet echt getest).** Alleen de toegankelijkheidsboom is gecontroleerd. Een echte NVDA/TalkBack-sessie
staat nog open: NIET GEVALIDEERD.

## Microcopy (ux-copy)

- De vaste woorden (Gezond · Beperkt · Storing · Onbekend + reden · Verouderd · Nog niet beschikbaar · Alles gezond ·
  Deels onbekend) worden overal gelijk gebruikt.
- Knoppen beginnen met een werkwoord en een object ("Inventaris vernieuwen", "Testmelding versturen", "Incident
  bekijken"). Er staat geen "OK", "Doorgaan" of "Weet je het zeker?".
- Gerepareerd: R-14 (meervouden, ruwe Engelse statuswoorden, "Klaar", "0 dagen oud") en R-11 (kindertaal op Ik).
- De woordenlijstcontrole gaf na herstel 0 treffers. Een aanvullende scan van alle 1346 unieke zichtbare teksten op Engelse of ruwe woorden vond alleen brongegevens (simulator-logregels, de SMART-tekst van TrueNAS), en de hierboven gerepareerde "stale" in "Geprobeerd … · stale" (nu "geen nieuwe meting (`stale`)").
- Teksten uit de simulator (bijv. "home-control-hub: app.process crashed (Node-RED)") zijn gegevens van de bron en
  geen UI-tekst.

## Grafieken (dataviz)

- **Vorm:** een trend is een lijn met één y-as; een huidige waarde is een StatKaart; geheugen is een meter. Geen
  dubbele as en geen taart.
- **Kleur:** reeks 1 is `--chart-1` en netwerk Ontvangen/Verzonden zijn `--chart-1`/`--chart-2` met een legenda. Het
  palet is ongewijzigd en was al gevalideerd (dataviz-validator: PASS in licht en donker, `contrast.json`). Er is geen
  nieuwe kleur.
- **Merktekens:** lijn 2 px, raster en as als solide haarlijn, eindpunt met een ring in de vlakkleur, en een direct
  label alleen bij één reeks.
- **Eerlijkheid:** een gat is arcering met "Geen meting" (nooit 0); verouderd is arcering met "Verouderd sinds …";
  laden en een fout zijn eigen toestanden.
- **Interactie:** tooltip en draadkruis met de aanwijzer én het toetsenbord; de tabel is de WCAG-tweeling.
- **Anti-patronen:** geen dubbele as, geen hercoloreren bij een filter, de periodefilter staat boven alle grafieken
  en er is geen skeletflits bij verversen.
- **Rest:** het pad wisselt eens per minuut, en dan staat er kort "Meetreeks ophalen…" (geen skelet).

## Bewijs

- Voor/na-afdrukken (WebP): `docs/ontwerp/review/*.webp`.
- Opnieuw meten: `make web-build && make web-review`. CI draait dezelfde review als stap na de web-E2E en faalt bij
  een harde bevinding.
- Unit-tests voor de reparaties: `apps/web/tests/unit/peil-review.test.tsx` (stabiel querypad, gaten, meervouden,
  bronlabel, StatKaart zonder badge).
- De web-E2E-suite (Playwright, 360/390/768/1440 × licht/donker met axe) blijft groen: 179 geslaagd. Eén eerdere run
  faalde op een wedloop in de opzettest: het incident stond er al met ×32, terwijl de worker de 100 events nog
  verwerkte. De test wacht nu tot alle 100 meetellen. Het was geen fout in de Hub.
- CI (GitHub Actions) op deze branch:
  - run 42711876495 faalde in de nieuwe reviewstap: de gebruikers werden gelijktijdig aangemaakt (N-06);
  - run 42715050190 faalde op overloop met DejaVu Sans (R-26);
  - runs 42721759007 en 42724137831 faalden op een pagina die > 30 s bleef laden (N-07). De eerste keer maakte dat ook
    zichtbaar dat een grafiek bij een mislukte reekslijst eindeloos bleef laden; dat is gerepareerd;
  - **run 42727322898 (`f609246`) is volledig groen** (python, web, excel, images). De reviewstap had 25 geslaagd en
    geen herkansing nodig: 57 schermen en toestanden (zonder de executor, die in CI niet draait), 676 metingen, 0 harde
    bevindingen, axe 0. Dit staat ook in EVIDENCE.json (I23-23-08, B01-004).
- `docs/screenshots/p1` toont nog de stand vóór deze review (`333de88`). De actuele afdrukken maakt `make web-review`
  (`apps/web/review/uit/shots`, niet in Git); de voor/na-selectie staat in `docs/ontwerp/review/`.

---

## Stap S-P2-005: teksten over de executor (11 november 2026)

**Rol:** R-ONTWERP (ontwerpreview achteraf, alleen microcopy). **Bereik:** de twee tekstwijzigingen van stap S-P2-005
in `apps/web/src/app/onboarding/executor/page.tsx` en `apps/web/src/app/instellingen/diensten/DienstenScreen.tsx`
(`55bb5bb..31c19fc`, commit `8131e27`). Geen nieuw scherm, daarom geen ontwerpstap vooraf (stap S-P2-005, "Agents").
**Toetsing aan:** Peil 1.1.1 (`docs/platform-v2/ONTWERPTAAL.md` §1, §4, §11, §12), `deploy/truenas/CUSTOM_APP.md`
kop 5, `policy/acties.yaml` en de code van Hub en executor (zie "Feiten nagelopen").

> **Eerlijkheid.** Gemeten in Chromium (Playwright) tegen de echte Hub-API, worker en database van de web-E2E-teststack
> (`tests/e2e/web_stack.py`, `server/hub-server.mjs`, productie-build), met simulators voor TrueNAS en de bronnen:
> **Sim-getest**. De toestand "koppelstatus onleesbaar" van de executor is in de teststack niet echt op te wekken
> (de Hub vindt de executor niet in de nagebootste inventaris en meldt dan `dienst_adres_onbekend`). Daarvoor is in een
> tijdelijke, niet gecommitte reviewtoestand alleen het antwoord van `GET /api/v1/services/{id}/koppelstatus`
> onderschept, met precies de vorm die de Hub in die tak teruggeeft (`status: "onleesbaar"`). De executor zelf was echt
> gekoppeld (browsertest `e2e/90-afsluiting.spec.ts`, "executor koppelen"). **NIET GEVALIDEERD:** echte NAS, echte
> schermlezer, echte telefoon.

### Feiten nagelopen (de tekst moet kloppen met wat de code doet)

| Bewering in de tekst (stand `31c19fc`) | Wat de code zegt | Uitkomst |
|---|---|---|
| Vaste lijst "(apps starten, stoppen, herstarten, installeren, verwijderen zonder data, bijwerken en terugzetten, en snapshots maken)" | `policy/acties.yaml`, `uitvoerder: executor`: ook `zfs.snapshot.clone_to_sandbox`; `app.update` en `app.rollback` weigert de Hub zolang er geen herstelpunten per app zijn (`CUSTOM_APP.md` kop 5, `backup_checkpoint_ontbreekt`) | onvolledig, hersteld (T-01) |
| "wijkt er iets af, dan stopt hij en volgt er een melding" | executor stopt (`executor_gestopt`) tot een beheerder hem op de statuspagina vrijgeeft; de Hub maakt een incident `actie.afwijking`, ernst kritiek (`hub/incidents/rules.py`) | vaag, hersteld (T-01) |
| "Zolang de executor niet is gekoppeld, blijven de gates … dicht" | `hub/onboarding/gates.py`: beide gates vragen ook besluiten (D01–D03) of de gates `backup_gate` en `data_mutatie` | klopt, maar suggereert dat koppelen genoeg is; aangevuld (T-02) |
| "Het beleid, de goedkeuringen en de uitvoering werken al via de Hub-API" | `CUSTOM_APP.md` kop 5 en ADR-0030 Open punten: zonder schermen is het voor een gebruiker niet te bedienen (`X-CSRF-Token`, `/api/docs`) | wekt een verkeerde verwachting, hersteld (T-03) |
| Diensten, executor onleesbaar: "vul daar de TrueNAS-schrijfsleutel in, kies ‘Ontkoppelen van de Hub’" | `executor/statuspagina.py` `onleesbaar_melding`: dat kan alleen als er al een sleutel is ingesteld (blok "Ontkoppelen of sleutel vervangen"); zonder sleutel verwijst de statuspagina naar de installatie-instructies | klopte niet voor het geval zonder sleutel, hersteld (T-04) |
| Kop "Status" boven een uitleg wat de executor doet | de sectie bevat geen status meer; de koppeltoestand staat in "2. Koppelen" | kop hernoemd naar "Wat de executor uitvoert" (zelfde woorden als de statuspagina: "Wat deze versie uitvoert") (T-05) |

### Hersteld (alleen tekst; geen gedrag, gegevens of API)

| # | Scherm | Was | Wordt |
|---|---|---|---|
| T-01 | Executor installeren en koppelen | lijst zonder klonen; "volgt er een melding" | volledige lijst incl. "een snapshot klonen naar een afgeschermde testdataset"; "Bijwerken en terugzetten weigert de Hub nog, tot er herstelpunten per app zijn."; bij een afwijking: incident onder Problemen en niets meer uitvoeren tot een beheerder hem op zijn statuspagina vrijgeeft |
| T-02 | idem | alleen "blijven dicht" | plus "Koppelen alleen opent ze niet: ze hebben ook andere voorwaarden." |
| T-03 | idem, melding "Schermen voor voorstellen en goedkeuren volgen later in fase P2" | "werken al via de Hub-API" | "zitten al in de Hub, maar … nog niet gebouwd. Tot die er zijn, kun je zelf nog geen actie voorstellen of goedkeuren." |
| T-04 | Instellingen → Diensten, executor met onleesbare koppelstatus | één herstelweg | herstel met sleutel (blok ‘Ontkoppelen of sleutel vervangen’ → ‘Ontkoppelen van de Hub’ → nieuwe koppelcode) én het geval zonder sleutel |
| T-05 | Executor installeren en koppelen | kop "Status" | kop "Wat de executor uitvoert" |

### Metingen (na herstel)

Gereedschap `apps/web/review/` (`peil-review.spec.ts`, `in-pagina.js`, `samenvat.mjs --streng`), breedtes 320, 360,
390, 768, 1024 en 1440, licht en donker, met en zonder `PEIL_REVIEW_LETTER="DejaVu Sans"` (lettertype van de CI-runner).

| Scherm / toestand | Metingen | axe (WCAG 2.2 A/AA) | Tekst min. | Overloop | Doelen < 44 px | Focus (390/1440) | Harde bevindingen |
|---|---|---|---|---|---|---|---|
| `executor-koppelen` (beheerder) | 12 + 12 | 0 | 9,32:1 | 0 | 0 (alleen de inline link "Wat mag nu?", uitgezonderd) | ring overal, niets bedekt, ring ≥ 8,34:1 | 0 |
| `diensten` (beheerder; tweede run met gekoppelde executor) | 12 + 12 | 0 | 7,61:1 | 0 | 0 | ring overal, niets bedekt, ring ≥ 5,81:1 | 0 |
| `kijker-diensten` | 12 + 12 | 0 | 8,34:1 | 0 | 0 | ring overal, niets bedekt, ring ≥ 8,34:1 | 0 |
| `diensten-executor-onleesbaar` (tijdelijk, zie Eerlijkheid) | 12 + 12 | 0 | 7,61:1 | 0 | 0 | niet gemeten (de reviewtool slaat de Tab-doorloop over bij een toestand met interactie; de melding heeft geen bediening) | 0 |

- **Peil-semantiek:** de melding "Koppelstatus onleesbaar" is `fout` (Storing: `octagon-x`, woord en vlak), zoals
  Peil §13.2 voor onleesbaar voorschrijft; "Niet gekoppeld" blijft de stippelpil, "Gekoppeld" neutraal; geen groen.
  De fase-melding gebruikt `hourglass` op `muted` (Nog niet beschikbaar).
- **Microcopy (§11):** woordenlijstcontrole 0 treffers; geen "allowlist", "runbook" of Engelse statuswoorden;
  rustige toon, eerst wat er is, dan waarom, dan wat je kunt doen.
- **Afdrukken** (alle breedtes × thema's) met Read bekeken; niet in Git (`apps/web/review/uit/`).
- **Volledige review (regressie, alle schermen):** zoals de CI (`PEIL_REVIEW_WORKERS=2 npx playwright test -c
  playwright.review.config.ts` en `node review/samenvat.mjs --streng`): 57 schermen en toestanden, 676 metingen,
  0 harde bevindingen, axe 0. Een extra lokale run met `PEIL_REVIEW_EXECUTOR_URL` (de executor-statuspagina, die de CI
  niet meet) gaf 59 schermen, 700 metingen en 1 harde bevinding op `executor-statuspagina-fout`; zie O-S2-005-3.

### Open (buiten het mandaat van deze review)

- **O-S2-005-1 (belangrijk) — HERSTELD in `4ef4ad4`, nagemeten bij de herreview (zie hieronder):** de statuspagina van de executor (`apps/executor/src/executor/statuspagina.py`,
  `onleesbaar_melding` en de rij `sleutelopslag_onleesbaar`) en `apps/executor/README.md` verwijzen naar
  "`deploy/truenas/CUSTOM_APP.md` (herstel)", maar dat document heeft geen herstelkop en noemt een onleesbaar
  koppelbestand of een onleesbare sleutelopslag niet. Een beheerder zonder ingestelde schrijfsleutel heeft zo geen
  beschreven herstelweg. Bestaat al sinds `b309042` (vóór deze stap). Voorstel: een kop "Herstel" in `CUSTOM_APP.md`
  met de stappen voor beide toestanden, en de verwijzing daarop laten aansluiten.
- **O-S2-005-2 (klein) — HERSTELD in `636dbf4`, nagemeten bij de herreview (zie hieronder):** de intro van "Executor installeren en koppelen" (ongewijzigd in deze stap) zegt
  "ondertekende, goedgekeurde acties uit uit een vaste lijst": "uit uit" leest stroef, en "goedgekeurd" is in Peil het
  woord voor een menselijke goedkeuring (R2/R3), terwijl R1 automatisch binnen het beleid loopt. Voorstel bij de
  volgende webstap: "Hij voert alleen acties uit een vaste lijst uit die de Hub heeft ondertekend — nooit shell, sudo
  of Docker."
- **O-S2-005-3 (klein) — open, verplaatst naar een latere webstap (besluit van de regisseur, 2026-11-12: niet in
  S-P2-010):** de reviewcontrole "status alleen kleur" meldt op de executor-statuspagina na een mislukte
  koppelpoging `input#koppelcode` en `input#vingerafdruk` (rand in `down`). Op de afdruk staat onder elk veld wel een
  `octagon-x` met de fouttekst ("Koppelcode: 12 tekens in groepen van 4 …"), dus de status is niet alleen kleur; de
  controle in `apps/web/review/in-pagina.js` (`semantiek`) ziet de fouttekst naast het veld niet. De statuspagina is in
  deze stap niet gewijzigd (laatste wijziging `b309042`) en de CI meet haar niet. Voorstel: in `semantiek()` een veld
  met `aria-invalid="true"` en een `aria-describedby` naar een zichtbare fouttekst niet als "alleen kleur" tellen, en
  de executor-statuspagina ook in de CI-review meten.

### Herreview (11 november 2026, bereik `4023e9e..636dbf4`)

**Rol:** R-ONTWERP (herreview na A-HERSTEL). **Bereik:** `4ef4ad4` (kop "Herstel" in `deploy/truenas/CUSTOM_APP.md`,
de verwijzing daarnaar in `apps/executor/src/executor/statuspagina.py` en `apps/executor/README.md`, en een test) en
`636dbf4` (intro van "Executor installeren en koppelen"), plus de open punten O-S2-005-1 en O-S2-005-2.

> **Eerlijkheid.** Gemeten in Chromium tegen de echte Hub (web-E2E-teststack, productie-build, simulators voor TrueNAS
> en de bronnen) en een **eigen echte executor** (`executor.app` met een eigen datamap). Die executor is eerst echt via
> de browser met de Hub gekoppeld (koppelcode uit de Hub-pagina, formulier op de statuspagina); daarna zijn de
> bestanden in zijn eigen datamap kapotgemaakt (`hub-link.json` en/of `naslink.json` met ongeldige inhoud, rechten
> 0600), zodat de executor de toestanden zelf afleidt. Niets is onderschept. **Sim-getest**; echte NAS, echte
> schermlezer en echte telefoon: **NIET GEVALIDEERD**.

**Feiten nagelopen (kop "Herstel" tegen de code):** de twee codes en bestanden (`hublink.py` en `naslink.py`, `_load`:
geen geldige JSON, andere hoofdversie, symlink, andere eigenaar, rechten buiten 0600); herstart zet alleen bij een
andere eigenaar van de map `/appdata/secrets` map en bestanden terug op 568 (`deploy/executor/entrypoint.py`; de tekst
zegt precies dat); met sleutel het blok "Ontkoppelen of sleutel vervangen" met "Nieuwe sleutel" en "Ontkoppelen van de
Hub" (`statuspagina.html`); "Koppelcode voor de executor maken" en "Uitleg executor" bestaan in de Hub-UI
(`ExecutorKoppelen.tsx`, `OnboardingScreen.tsx`); `certificaat_gewijzigd` bestaat (`truenas.py`, `app.py`). De kop beschrijft
alleen de TrueNAS-web-UI, geen terminal (V-096). Uitkomst: klopt.

**Gevonden en hersteld (alleen tekst):**

| # | Scherm | Was | Wordt |
|---|---|---|---|
| T-06 | Executor-statuspagina, koppelstatus onleesbaar zonder bruikbare sleutel | "… en er is nog geen TrueNAS-schrijfsleutel ingesteld waarmee je dit hier kunt herstellen." | "… en er is geen bruikbare TrueNAS-schrijfsleutel (niet ingesteld of onleesbaar) waarmee je dit hier kunt herstellen." |

Waarom: als ook de sleutelopslag onleesbaar is, geeft de executor deze melding (`app.py`, `_page`:
`sleutel_ingesteld=bool(nas.get("ingesteld"))`, en `naslink.public()` zegt dan `ingesteld: False`). Op dezelfde pagina
staat dan de rij "TrueNAS-schrijfsleutel · Onleesbaar". De melding zei dus iets wat de rij eronder tegenspreekt
(gezien op de draaiende executor). Test: `apps/executor/tests/test_statuspagina.py`,
`test_onleesbaar_zonder_bruikbare_sleutel_zegt_niet_dat_er_geen_sleutel_is` (rood met de oude tekst, mutatieproef).

**Metingen** (`apps/web/review/`, 320/360/390/768/1024/1440 × licht/donker, `samenvat.mjs --streng`; tweede ronde met
`PEIL_REVIEW_LETTER="DejaVu Sans"`):

| Scherm / toestand | Metingen | axe | Tekst min. | Overloop | Doelen < 44 px | Focus (390/1440) | Harde bevindingen |
|---|---|---|---|---|---|---|---|
| `executor-koppelen` (nieuwe intro) | 12 + 12 | 0 | 9,32:1 | 0 | 0 | ring overal, niets bedekt, ≥ 8,34:1 | 0 |
| executor-statuspagina, gekoppeld + `sleutelopslag_onleesbaar` | 12 + 12 | 0 | 8,34:1 | 0 | 0 | idem | 0 |
| executor-statuspagina, `koppelstatus_onleesbaar` zonder sleutel | 12 (oud) + 12 + 12 (na T-06) | 0 | 8,34:1 | 0 | 0 | idem | 0 |
| executor-statuspagina, beide onleesbaar | 12 (oud) + 12 + 12 (na T-06) | 0 | 8,34:1 | 0 | 0 | idem | 0 |

- Eén zachte treffer van de woordenlijst op elke statuspagina: "de eigen controles zijn **in orde**" in de vaste
  Gereed-zin. Dat is de letterlijke voorbeeldzin uit Peil §11.2 ("Statuspagina: Gereed"); geen statuswoord. Laten staan.
- Het pad `deploy/truenas/CUSTOM_APP.md` breekt op 320 px netjes (ook met DejaVu Sans); afdrukken met Read bekeken.
- De nieuwe intro: geen "goedgekeurd" meer, geen "uit uit"; past op 320 px zonder overloop.

**Open na de herreview (buiten het mandaat; niet gewijzigd):**

- **O-S2-005-4 (belangrijk, Peil-sjabloon):** het gepinde sjabloon (`apps/executor/src/executor/statuspagina.html`,
  kopie van `design/ontwerptaal/statuspagina.html`, Peil 1.1.1) toont op de executor bij `koppelstatus_onleesbaar`
  "Herstel gaat alleen met een nieuw koppeltoken: maak het in de Hub (Instellingen → Diensten). …". De executor kent
  geen koppeltoken (contract §3.9); de melding bovenaan dezelfde pagina zegt dat ook. Op de draaiende executor staan
  beide teksten tegelijk. Daarnaast toont het blok "gekoppeld" van hetzelfde sjabloon "Ontkoppelen of opnieuw koppelen
  gaat via de Hub", terwijl ontkoppelen bij de executor op de statuspagina zelf gebeurt (§3.9) en bij een onleesbare
  sleutelopslag alleen via een nieuwe datamap (`CUSTOM_APP.md`, kop "Herstel"). Oplossen vraagt een nieuwe Peil-versie
  (uitzondering voor de executor in het sjabloon); dat is een besluit, geen ontwerpreview.
- **O-S2-005-5 (klein):** `ERRORS_NL["koppelstatus_onleesbaar"]` in `apps/executor/src/executor/hublink.py` zegt
  alleen "Herstel gaat met de TrueNAS-schrijfsleutel op deze pagina (Ontkoppelen van de Hub)". Die tekst verschijnt bij
  een formulierverzoek dat de executor met deze code weigert, en in `last_error` van de koppelstatus. Zonder bruikbare
  sleutel klopt hij niet; voorstel: dezelfde tweedeling als `onleesbaar_melding`.
- **O-S2-005-6 (klein):** `deploy/truenas/CUSTOM_APP.md`, stap 3, "Koppelen met de Hub", punt 1 zegt nog dat het scherm
  "Diensten" er niet is en dat je de koppelcode via `/api/docs` maakt; kop 5 zegt dat `/api/docs` geen
  `X-CSRF-Token` meestuurt, en de kop "Herstel" verwijst (terecht) naar de Hub-pagina "Executor installeren en
  koppelen". Punt 1 is verouderd (V-104).

## Stap S-P2-010: runbookteksten en weigerteksten van het beleid (12 november 2026)

**Rol:** R-ONTWERP (korte review, alleen teksten). **Bereik (besluit van de regisseur):** de gewijzigde runbookteksten
van deze stap (`apps/api/src/hub/runbooks/catalogus.py`, `apps/api/src/hub/runbooks/export.py` met de toevoeging
"het platform weigert dit bij een gestopte Custom App", en het daaruit gemaakte `docs/RUNBOOKS.md`; bereik
`c63b32e..5d2efa9`, o.a. `9779b80`) en de Nederlandse foutteksten (`fout` in `{veld, code, fout}`) die een beheerder
krijgt bij de weigercodes van `apps/policy/src/asm_policy/params.py` (`catalogus_waarde_verboden`, `compose_verboden`,
`privileged_verboden`, `hostpad_verboden`, `host_network_zonder_reden`, `capabilities_verboden`, `devices_verboden`).
Er is in deze stap geen scherm gebouwd of gewijzigd: de weigerteksten komen alleen in het API-antwoord
(`parameters_ongeldig`, Hub `apps/api/src/hub/actions/service.py` `_fouten_dict`; executor
`apps/executor/src/executor/uitvoeren.py`); de runbookteksten verschijnen in `docs/RUNBOOKS.md` en ongewijzigd in het
stappenplan van een incident (`apps/web/src/app/problemen/IncidentDetail.tsx`, `Stappenplan`).
**Toetsing aan:** Peil 1.1.1 (`docs/platform-v2/ONTWERPTAAL.md` §11 Nederlandse microcopy) en de code (engine-regels
`DOEL-ONHERKENBAAR` en `STOP-EENRICHTING` in `apps/policy/src/asm_policy/engine.py`, `host_path_problem` en
`_sleutel_fout` in `params.py`).

> **Eerlijkheid.** Niets gemeten op een draaiende dienst: geen schermafdrukken, geen axe, geen contrast- of
> toetsenbordmeting (geen scherm in het bereik). De toets is op papier: tekst tegen code. Gedrag, codes, API en
> `policy/*.yaml` zijn niet gewijzigd; `policy_hash` blijft gelijk.

### Feiten nagelopen

| Tekst | Wat de code doet | Uitkomst |
|---|---|---|
| Export: "(minimaal R2; het platform weigert dit bij een gestopte Custom App)" bij `app.rollback` en `app.start` na een stop | `NA_STOP_GEWEIGERD`; engine `DOEL-ONHERKENBAAR`: geen image te zien bij een gestopte Custom App, elke actie geweigerd | klopt |
| Export: "(minimaal R1; Custom App: R2)" bij `app.stop` | `ALLOWLIST_CUSTOM_APP`, engine `STOP-EENRICHTING` | klopt |
| `db_migratie_mislukt`, mitigeren: "daarna weigert het platform app.rollback en app.start op die app" | `DOEL_ONHERKENBAAR`: "weigert elke actie op deze app"; `NA_STOP_ACTIES` noemt ook update, restart en uninstall | onvolledig, hersteld (T-10) |
| `schijf_vol`, mitigeren: "en start de app daarna alleen weer in de TrueNAS-web-UI" | idem | dubbelzinnig (leest als een opdracht), hersteld (T-11) |
| `hostpad_verboden`: "ongeldig hostpad" (twee keer, zonder reden) | `host_path_problem`: stuurtekens/onzichtbare tekens, `//`, `/` aan het eind, meer dan 512 tekens | geen reden en geen uitweg, hersteld (T-12) |
| `hostpad_verboden`: "het hostpad moet absoluut zijn" | idem | hersteld met voorbeeldvorm (T-12) |
| `host_network_zonder_reden`: "host network alleen met een reden in het manifest" | `_sleutel_fout`: `host_network_reason`, minstens 10 tekens | Engels zonder uitleg, veldnaam en grens ontbraken, hersteld (T-13) |
| `compose_verboden`: "compose/YAML-installatie is nooit toegestaan" | geraakt bij een sleutel met "compose" of de sleutel `services`, ook in de waarden van een catalogusapp | zei niet waarom déze sleutel, hersteld (T-14) |
| `compose_verboden` bij `custom_app`: "custom_app=true is een compose-app (Install via YAML)" | weigering | zei niet dat het geweigerd is en wat wel kan, hersteld (T-14) |
| `privileged_verboden`: "privileged is nooit toegestaan" | weigering | klopt; uitleg toegevoegd (T-15) |
| `catalogus_waarde_verboden` (`_DOCKER`): "Docker-/compose-optie (…) is in deze waarden nooit toegestaan" | geldt voor netwerk/namespace van host of andere container, beveiligings- en rechtenopties, cgroups, userns, sysctls, runtime, `volumes_from`, en bij een catalogusapp `command`/`entrypoint` | zin zonder lidwoord, lijst onvolledig, hersteld (T-16) |
| `capabilities_verboden` "geen extra capabilities"; `devices_verboden` "geen apparaten in v1 (render-node volgt met D08/B03)" | weigering | uitweg ontbrak / "v1" vaag, hersteld (T-17) |
| `stuurteken`, `host_pid_verboden`, `host_ipc_verboden`, `netwerk_verboden`, "unconfined" | | klopt, niet gewijzigd |

### Hersteld (alleen tekst; geen gedrag, codes, API of beleid)

| # | Plek | Wordt |
|---|---|---|
| T-10 | `catalogus.py`, `db_migratie_mislukt`, mitigeren | "… Bij een Custom App vraagt dit goedkeuring van een beheerder (R2), en daarna weigert het platform elke actie op die app, ook app.rollback en app.start (doel_niet_herkenbaar): …" |
| T-11 | `catalogus.py`, `schijf_vol`, mitigeren | "… Bij een Custom App vraagt dit goedkeuring van een beheerder (R2), en daarna kun je de app alleen in de TrueNAS-web-UI weer starten." |
| T-12 | `params.py`, `host_path_problem` | "het hostpad moet absoluut zijn: begin met /, bijvoorbeeld /mnt/<pool>/<dataset>"; "ongeldig hostpad: tabs, regeleinden en andere onzichtbare tekens zijn niet toegestaan"; "ongeldig hostpad: geen dubbele / en geen / aan het eind"; "ongeldig hostpad: hooguit 512 tekens" (dezelfde weigeringen, alleen per reden een eigen tekst) |
| T-13 | `params.py`, `host_network_zonder_reden` | "het netwerk van de host (host network) alleen met een reden van minstens 10 tekens in het manifest (host_network_reason)" |
| T-14 | `params.py`, `compose_verboden` | "compose en YAML zijn nooit een installatieweg; een sleutel met compose of services wordt daarom geweigerd"; bij `custom_app`: "… en is nooit toegestaan; installeer als standaard Custom App (ix-app)" |
| T-15 | `params.py`, `privileged_verboden` | "privileged (volledige toegang tot de host) is nooit toegestaan" |
| T-16 | `params.py`, `catalogus_waarde_verboden` | "deze Docker- of compose-optie is in de waarden van een app nooit toegestaan (netwerk of namespace van de host of van een andere container, beveiligings- en rechtenopties, cgroups, sysctls, runtime, volumes van een andere container of een eigen opdracht)" |
| T-17 | `params.py`, `capabilities_verboden`, `devices_verboden` | "geen extra capabilities: laat dit leeg"; "apparaten (devices) zijn in deze versie niet toegestaan; de render-node voor de GPU volgt met besluit D08 (B03)" |

`docs/RUNBOOKS.md` is opnieuw gemaakt met `make runbooks` (nieuwe `runbook_hash`). Geen test controleert deze teksten
letterlijk; de tests controleren de codes (die zijn gelijk gebleven).

### Open (buiten het bereik van deze review; niet gewijzigd)

- **O-S2-010-1 (klein):** het stappenplan in `apps/web/src/app/problemen/IncidentDetail.tsx` (`Stappenplan`) zegt bij
  elk voorstel nog "voorstel — uitvoeren volgt in fase P2". Fase P2 loopt; uitvoeren via de executor bestaat, alleen
  de schermen voor voorstellen en goedkeuren nog niet. Voorstel: dezelfde zin als de executorpagina ("Schermen voor
  voorstellen en goedkeuren volgen later in fase P2"), in de webstap die die schermen bouwt.
- **O-S2-010-2 (klein):** `docs/RUNBOOKS.md` heet "Operator-runbooks" en zegt "executor-allowlist"; Peil §11.1 zegt
  "stappenplan" en "lijst met toegestane acties". Ouder dan deze stap (`export.py`, kop en intro).
- **O-S2-010-3 (klein):** de code `catalogus_waarde_verboden` kan ook bij de standaard Custom App (ix-app) komen
  (`_deep_forbidden` toetst "unconfined" en de losse teksten in een lijst ook bij `ix_app`); de codenaam suggereert
  alleen catalogusapps. Een code is API; niet gewijzigd.

## Stap S-P2-020: meldingen van de executorpagina na ontkoppelen (12 november 2026)

Korte ontwerpreview (R-ONTWERP) op `85226f1` van de nieuwe vaste meldingen op de executorpagina: ontkoppelen,
opnieuw koppelen, sleutelbeheer en de hersteltekst bij een onleesbaar koppelbestand. Alleen teksten hersteld; geen
gedrag, codes, API, beleid of Peil-bron (`design/ontwerptaal/statuspagina.html` en
`apps/executor/src/executor/statuspagina.html` zijn niet gewijzigd).

### Werkwijze

De echte dienst (`python -m executor init` en `python -m executor api`) draaide lokaal met een nagebootste TrueNAS
(`tests/fakes/fake_truenas.py`) en twee nep-Hubs (alleen testwaarden). Chromium (Playwright uit
`design/ontwerptaal/bouw`) verstuurde de echte formulieren: koppelen, de sleutel in twee stappen, beheer met een
verkeerde sleutel, ontkoppelen, opnieuw koppelen met een andere Hub, en een koppelformulier uit een oud tabblad. Per
toestand: schermafdrukken op 320, 360, 390, 768 en 1440 px, licht en donker (50 in totaal, buiten de repo); axe-core
(WCAG 2.0/2.1/2.2 A en AA) op 320 en 1440 px in beide thema's; horizontale overloop en aanraakdoelen op elke breedte;
toetsenbord: Tab door de hele pagina, focus zichtbaar en niet bedekt. Let op: de rate-limit (5 pogingen per 15 min per
bron-IP, §3.7) maakt dat de toestanden in drie aparte runs met een verse datamap zijn gemeten.

### Metingen (na herstel)

| Toestand | axe | Overloop | Aanraakdoelen < 44 px | Toetsenbord |
|---|---|---|---|---|
| `sleutel_niet_huidig` (beheer met een verkeerde sleutel) | 0 | geen | geen | 8 stops, focus zichtbaar, niets bedekt |
| Ontkoppelen gelukt | 0 | geen | geen | 7 stops, idem |
| Ontkoppeld (bestaande toestand, `ONTKOPPELD_MELDING`) | 0 | geen | geen | 7 stops, idem |
| Opnieuw gekoppeld zonder sleutel (`OPNIEUW_GEKOPPELD_MELDING`) | 0 | geen | geen | 6 stops, idem |
| `al_gekoppeld` (formulier uit een oud tabblad) | 0 | geen | geen | 6 stops, idem |

Onbekend en verouderd zijn nergens groen: de status toont "Onbekend" of "Niet gereed" met een icoon en een gestippelde
rand, nooit alleen kleur. `/api/v1/status` gaf in de toestand ontkoppeld de nieuwe toelichting terug.

### Hersteld (alleen tekst)

- `FORM_MESSAGES["al_gekoppeld"]`: "opnieuw koppelen gaat via de Hub" klopte niet voor de executor. Nu: opnieuw
  koppelen kan alleen na "Ontkoppelen van de Hub" op deze pagina, met de huidige sleutel als bewijs; dat blok staat er
  alleen als de sleutel is ingesteld. Test: `test_ontkoppelen_met_bewijs_en_opnieuw_koppelen_mogelijk`.
- `ONTKOPPELD_MELDING` en de succestekst van ontkoppelen: volgorde Peil §11 (wat er is, gevolg, wat je doet); "het
  certificaat van TrueNAS"; "tot de executor opnieuw gekoppeld is en de sleutel opnieuw is ingesteld" (beide zijn
  nodig); "de vingerafdruk uit jouw Hub".
- `OPNIEUW_GEKOPPELD_MELDING`: het risico benoemd (in de tussentijd kon iedereen op het netwerk koppelen), "Hub-UI"
  vervangen door "wat jouw Hub toont", en wat te doen bij een andere Hub (nieuwe datamap, zoals CUSTOM_APP.md "Herstel").
- Vervangen tijdens een stop: waarom de executor gestopt blijft, en het veld bij zijn echte label ("Huidige
  TrueNAS-API-sleutel met schrijfrechten"). Bij elk vervangen: de oude sleutel bestaat in TrueNAS nog.
- Sleutel opnieuw instellen: verwijzing naar de status voor of de executor weer uitvoert.
- `schrijfrechten_onvolledig`: titel "De sleutel heeft niet alle schrijfrechten"; de dubbelzinnige zin herschreven.
- `sleutel_niet_huidig`: "Heb je die sleutel niet meer?" met de verwijzing naar Herstel.
- `sleutelopslag_niet_schrijfbaar`: eerlijk dat de wijziging deels opgeslagen kan zijn; eerst de pagina opnieuw laden.
- `sleutel_al_ingesteld`: "misschien net in een ander tabblad", "Er is niets gewijzigd", pagina opnieuw laden.
- Status-toelichting "ontkoppeld": waar je opnieuw koppelt (de executorpagina).
- `onleesbaar_melding` (met sleutel): de veldnaam "huidige TrueNAS-API-sleutel" en "laat 'Nieuwe sleutel' leeg".

### Open (Peil-bron of gedrag; niet gewijzigd)

- Het Peil-sjabloon zegt in de toestand Gekoppeld "Ontkoppelen of opnieuw koppelen gaat via de Hub." Voor de executor
  klopt dat niet meer (ontkoppelen gaat op de eigen pagina); de vaste melding erboven zegt nu iets anders.
- In de toestand ontkoppeld toont het sjabloon "Deze dienst is nog niet met de Hub gekoppeld" en de Hub-weg
  "Instellingen → Diensten → Koppelcode maken"; CUSTOM_APP.md noemt voor de executor "Koppelcode voor de executor
  maken" op de pagina "Executor installeren en koppelen". De melding erboven corrigeert het eerste, niet het tweede.
- De hint "Laat leeg als je alleen wilt ontkoppelen." bij "Nieuwe sleutel" noemt vrijgeven niet.
- Deze drie horen bij de geplande Peil-stap (vaste teksten voor ontkoppeld, een sleutelveld in het koppelformulier en
  een eigen knop "Vrijgeven").
- Een tweede melding als de nieuwe Hub een andere vingerafdruk heeft dan vóór de ontkoppeling (R-VEILIG-7) is gedrag:
  vervolgpunt.
