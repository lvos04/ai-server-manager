# ADR-0025 — Peil-ontwerpreview van de gebouwde Hub-UI: reparaties en meetgereedschap

Status: aanvaard · Datum: 2026-11-09 · Rol: ontwerp-agent (onafhankelijke review, contract §13)
Bouwt op: ADR-0015 (ontwerptaal Peil), ADR-0024 (Hub-UI in Peil, OB-01–OB-14) · Verslag: `docs/ontwerp/PEIL_REVIEW.md`

## Context

ADR-0024 bracht de Hub-UI naar Peil. De Playwright-suite controleert 360/390/768/1440 met axe, overloop en doelen
≥ 44 px voor knoppen en navigatie. De review mat de **echte** UI breder: 320 tot 1440, licht en donker, gerenderd
contrast, een volledige Tab-doorloop, uitklapinhoud, losse links, de Peil-semantiek en de woordenlijst. Daarbij kwamen
fouten boven die de suite niet ziet. De reparaties vragen een paar keuzes die hier vastliggen. Alle keuzes gaan over
uiterlijk, tekst of toegankelijkheid. Er verandert geen API en geen gedrag van de backend.

## Besluiten

1. **Meetgereedschap blijft in de repo** (`apps/web/review/`, `playwright.review.config.ts`, `make web-review`).
   Het meet dezelfde dingen als `design/ontwerptaal/bouw/controle.cjs`, maar dan op de gebouwde UI met de
   web-E2E-teststack (Sim-getest). Bij een harde bevinding faalt het. Het draait als aparte CI-stap na de web-E2E.
2. **Verse waarden krijgen geen badge.** De StatKaart toont bij een verse meting alleen de waarde met "· gemeten" en
   de tijd (Peil §4.4 en K3). De neutrale pil "Gemeten" op Server → Metrieken is weg, want die werkte als een badge
   "Actueel".
3. **Losse links zijn 44 px hoog.** Een link die alleen in een alinea of rij staat, krijgt het recept `.losse-link`.
   De WCAG-uitzondering (2.5.8) geldt alleen voor links in een zin. Rijlinks in de appslijst krijgen hetzelfde.
   "← Terug naar de onboarding" wordt een kruimelpad, zoals op de andere detailpagina's.
4. **Datum- en tijdvelden krijgen de Peil-ring via `:focus-within`.** Chromium zet de focus soms op de kalenderknop
   in het veld. `:focus-visible` geldt dan niet op het veld, en er was geen ring te zien.
5. **Het gebruikersmenu is niet-modaal.** Een modaal Radix-menu zet `aria-hidden` op de pagina terwijl daar focusbare
   elementen blijven (axe `aria-hidden-focus`). Esc, Tab en klikken buiten het menu sluiten het nog steeds.
6. **Grafieken volgens C-32.** Het plotvak is `role=img` met `tabindex=0`. Je bedient het met de pijltjes, Home, End
   en Esc. Er is een draadkruis, een zichtbare uitlezing en voorlezen via `aria-live`. Verder: een eindpunt met ring
   en, bij één reeks, een direct label. Een gat krijgt arcering met "Geen meting". Onder de grafiek staat een regel
   met bron en tijd, en "Toon als tabel" is een benoemde scrollregio. Dit vervangt de afwijking in ADR-0024 punt 7.
   Zolang de reeks nog laadt, staat er "Meetreeks ophalen…" en nooit "Geen meting". Mislukt het ophalen, dan zegt de
   grafiek "Onbekend". Kleine gemeten waarden houden 2 significante cijfers ("0,03 Mbit/s"), zodat een as of tegel
   nooit "0" zegt voor iets dat niet 0 is.
7. **Het querypad van een grafiek is stabiel.** `van` staat op de hele minuut en `tot` laat de UI weg (de Hub neemt
   dan "nu"). Eerder veranderde het pad bij elke weergave. Dan haalde `useApi` eindeloos opnieuw op (± 1300
   aanvragen in 6 s) en toonde elke grafiek ten onrechte "Geen meting in deze periode". Dit is een
   weergavefout met een onware tekst, en de oplossing zit alleen in de UI.
8. **Sessies intrekken is geen gevaar.** De knop is gewoon, niet rood (Peil §4.1 regel 2): opnieuw inloggen kan
   altijd. Hetzelfde geldt voor een rij weghalen uit een nog niet opgeslagen formulier ("Verwijderen"). Op Ik (rol kind) heet het blok "Waar je bent ingelogd" en de knop "Uitloggen op dat apparaat". IP-adres
   en tijden staan daar achter "Details voor een volwassene".
9. **Kindschil: focus nooit achter de ondernavigatie.** De kindschil heeft op elke breedte een ondernavigatie. Daarom
   geldt de scroll-padding onder (`html:has([data-schil=kind])`) ook vanaf 1024. De tabtitel van de kind-403 is
   "Niet voor jou" en niet de beheerterm van de route.
10. **Navigatie-iconen exact volgens ONTWERPTAAL §7.** Huis is `sofa` (eerst hetzelfde huisje als Home), Media
    `clapperboard`, Backups `database-backup`, Kosten `wallet`, Problemen `inbox`, AI `bot` en Meer `menu`. De
    Home-kaarten volgen dezelfde koppeling (GPU `microchip`).
11. **Lijsten naast een subnavigatie.** De tabel van Alertregels begint pas bij 1280 (`tabelVanaf`). Op 1024 liep
    hij 42 px over. De rij "Groep → rol" van SSO gebruikt een containerquery: op 1024 werd het groepsveld 26 px
    breed.
12. **Taal.** Echte meervouden (`aantal()`: "1 pool", "3 kanalen") in plaats van "pool(s)" en "kanaal/kanalen".
    Ruwe statuswoorden worden Nederlands: een ophaalronde is "geslaagd", "deels gelukt" of "mislukt (stand
    onbekend)", en de live-meting "werkt" of is "onbekend". Redenen staan als `code`. Een tokenleeftijd is "van
    vandaag" in plaats van "0 dagen oud". Een afgeronde stap heet "Aangemaakt" in plaats van "Klaar". "Geprobeerd" krijgt
    gewone woorden met de code erbij ("geen antwoord (`unreachable`)"). Knoppen zijn een werkwoord in de onbepaalde
    wijs ("D01 meten").
13. **Problemen vanaf 1280 is altijd master-detail.** Zonder gekozen incident staat rechts "Kies links een incident…".
    Daardoor springt de indeling niet meer na de eerste klik.

## Niet in deze review gerepareerd (buiten het mandaat: alleen uiterlijk, tekst en toegankelijkheid)

- **Executor: koppelen via de statuspagina werkt in een echte browser niet.** De executor stuurt
  `Referrer-Policy: no-referrer`. Een browser zet bij een formulier-POST dan `Origin: null`, en `POST /koppelen`
  weigert alles behalve `http(s)://<host>`. Gereproduceerd in Chromium (Playwright): de pagina zegt dan "Geweigerd:
  het formulier komt niet van deze pagina." De diensten (home-control-hub, appstore-en-fork, jelly-leon-platform en
  zoeken-en-persoonlijke-ai) accepteren `Origin: null` en vertrouwen op het CSRF-cookie met `SameSite=Strict`.
  Overgedragen aan de executor-bouwer (zie PEIL_REVIEW.md, blokkerend voor H5/§3.9).
- Kopbalk: Zoeken (C-51) en de Live-indicator ontbreken nog (ADR-0024 punt 8). Problemen zonder selectie op ≥ 1280
  toont alleen de lijst, zonder lege detailkolom. Beide zijn functionele toevoegingen.

## Gevolgen

- Op de gebouwde UI geeft de review 0 harde bevindingen over 6 breedtes × 2 thema's (zie PEIL_REVIEW.md). Dat geldt
  voor de schermen van beheerder, kijker en kind, de publieke pagina's, de executor-statuspagina en de toestanden
  NAS offline en browser offline.
- De review draait in CI met het systeemlettertype van de runner (DejaVu Sans, breder dan lokaal Noto Sans). Lokaal
  kun je dat nadoen met `PEIL_REVIEW_LETTER="DejaVu Sans"`. Peil gebruikt bewust het systeemfont, dus reflow moet
  met elk gangbaar systeemfont kloppen.
- Alles is **Sim-getest** in Chromium. NIET GEVALIDEERD: echte schermlezer (NVDA/TalkBack), echte Android-telefoon in
  fel licht, tv, echte NAS.
