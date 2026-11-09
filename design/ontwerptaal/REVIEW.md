# Ontwerpreview Peil 1.0.0 → 1.1.0

**Datum:** 9 november 2026 · **Rol:** onafhankelijke ontwerpreviewer (design-agent) · **Onderwerp:** `definitief/` (ONTWERPTAAL.md,
COMPONENTEN.md, ADR-ONTWERPTAAL.md, tokens, CSS, aliaslagen, statuspagina-sjabloon, prototypes).
**Toetsing aan:** `ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md` (1.2, o.a. §3.7, §3.9, §6, §8, §13) en
`01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`. Alleen gelezen; in de 11 repos is niets gewijzigd (`git status`: 0 wijzigingen in alle
repos), niets gecommit en ai-factory niet aangeraakt.

## Oordeel

**Goedgekeurd na herstel, als versie 1.1.0.** De ontwerptaal zelf (principes, vijf assen, palet, typografie, 44 px, focus)
is sterk en goed onderbouwd. De review vond wel **2 blokkerende** en **4 hoge** fouten. Alle fouten zijn in
`definitief/` hersteld en opnieuw gemeten. Geen enkele herstelling verandert een besluit van de gebruiker of uit het ADR.

| Ernst | Aantal | Hersteld |
|---|---|---|
| Blokkerend | 2 | 2 |
| Hoog | 4 | 4 |
| Middel | 9 | 9 |
| Laag | 7 | 7 |
| Bewust niet gewijzigd (met reden) | 8 | — |

## Werkwijze

- **Skills:** `dataviz` (vóór elk oordeel over grafiekkleuren; validator zelf gedraaid), `design:ux-copy` (NL-microcopy),
  `design:accessibility-review` (WCAG 2.1 AA-structuur).
- **Eigen gereedschap** (los van de scripts van de maker), in `.review-tools/`:
  - `scripts/contrast-review.mjs`: leest de **gegenereerde** `ontwerptaal.css` (wat bouwers importeren), lost `var()` op en
    rekent een eigen matrix van **367 paren per thema** door (wcag-contrast + culori). Vergelijkt ook met `tokens.json` en
    `contrast.json`.
  - `scripts/axe-review.cjs`: eigen axe-core 4.14 (`npm i --prefix .review-tools axe-core`), tags wcag2a/aa/21a/21aa/22aa
    **plus best-practice**, op 11 schermen × 320/360/390/768/1024/1440 × licht/donker (132 runs). Meet daarnaast overloop,
    doelen < 44 px en **tekstoverlap** (tekstvakken die elkaar raken; deze controle had de maker niet).
  - `scripts/statuspagina-nojs.cjs`: statuspagina met JavaScript uit, onder CSP `default-src 'none'; style-src 'unsafe-inline'`.
  - `tw-test/`: Tailwind 4.3.5-compilatie met letterlijke shadcn new-york v4-klassen + Peil-utilities, en gemeten in Chromium
    (licht, `.dark` en `[data-theme=dark]`); ook de aliaslagen van Hub en MediaGuard tegen de echte `mg.css`.
- **Schermafdrukken** bekeken (Read) op 360 en 1440, licht en donker, vóór en na herstel (`.review-tools/shots-voor/`,
  `definitief/shots/`). Lange 360-afdrukken als kolommen naast elkaar (`.review-tools/montage-na/`).
- Een kopie van `definitief/` vóór de review staat in `.review-tools/backup-definitief-voor-review/` (mag weg na akkoord).

## Bevindingen en reparaties

### Opdracht 1 — contrast (licht en donker)

| # | Ernst | Bevinding | Bewijs | Reparatie |
|---|---|---|---|---|
| 1.1 | Blokkerend | **Hub-aliaslaag maakte `--info-bg` en `--unknown-bg` ongeldig.** `hub-p0.css` bevatte `--info-bg: var(--info-bg)` en `--unknown-bg: var(--unknown-bg)` op `:root`. Dat is een cyclus; de browser maakt de variabele dan leeg. Elk Onbekend- en Info-vlak in de Hub (ook Peils eigen `bg-unknown-bg`) werd transparant. | Chromium: `--info-bg=""`, achtergrond `rgba(0,0,0,0)` in licht en donker (`tw-test/alias.cjs`). Na herstel: `#E3ECFA`/`#132440` en `#E9EDF2`/`#222932`. | Beide regels weg (Peil levert de namen al). De generator weigert nu elke zelfverwijzing. `bouw/aliaslagen.mjs` |
| 1.2 | Hoog | **MediaGuard/MSO-aliaslaag miste correcties.** Noodstop ingedrukt: wit op `--down` = **2,02:1** in donker. AV1-lanetekst in `--domain-lane-cpu` = **3,20:1** in licht (tekst van 11,5 px). | Gemeten met de echte `mg.css` + oude aliaslaag (`tw-test/mg-oud.cjs`). | Noodstop → `destructive`/`-foreground` (9,66 / 7,61:1); lanetekst → `foreground`, alleen het icoon in de lanekleur. `bouw/aliaslagen.mjs` |
| 1.3 | Hoog | **Boilervlak en -inkt niet te onderscheiden van Gezond.** `domain-boiler-bg` lag ΔE **0,6** (licht) / 1,1 (donker) van `healthy-bg`; `domain-boiler-ink` ΔE 2,5 van `healthy-ink`. Een boilerchip zou eruitzien als "Gezond", terwijl de boiler alleen meten is. De harde ΔE ≥ 15-controle keek alleen naar de volle kleuren, niet naar vlak en inkt. | `.review-tools/scripts/tint-review.mjs` | `domain-boiler-bg` en `-ink` neutraal (`#E4E8EE`/`#1E252E`, `#0B0F14`/`#F2F5F8`). Nu ΔE 3,3/5,2 en een andere tint. `bouw/tokens.mjs` |
| 1.4 | Middel | **Domeinkleur op het eigen vlak haalt 3:1 niet.** In licht: heat 2,76, boiler 2,70, licht-aan 2,82:1. Gebruikt voor de chip-iconen en de lamp in `huis.html`. | brede matrix | Nieuwe regel 11 (§4.1): een icoon of tekst op `domain-*-bg` krijgt `-ink`. Prototype en COMPONENTEN aangepast. In de matrix staan deze paren als "niet gebruiken". |
| 1.5 | Laag | **my_house-paren uit `styles.css` ontbraken in de meting:** `heat-ink` op `heat-soft` (`.schedule-bar .warm`), `cool-ink` op `cool-soft`, `bg` op `primary` (`.brand-mark`), `text`/`muted` op `surface-2`. | eigen parsing van `my_house/apps/web/src/styles.css` | Toegevoegd. 60 paren, 0 fouten (laagste: heat-ink op heat-soft, 5,49 licht en 4,93 donker). |
| 1.6 | Laag | **Inleiding zei "voor tekst haalt Peil AAA".** `--stale-ink` haalt met opzet ≈ 6:1, en 4,56:1 op de arcering. | — | Tekst verduidelijkt: beide tekstniveaus halen AAA, de gedempte laatste waarde haalt AA. |

**Uitkomst na herstel**
- `contrast.json`: 154 paren per thema, 0 harde fouten. Daarnaast een nieuwe **brede matrix** van 367 paren per thema,
  0 harde fouten (stap `bouw/contrast-breed.mjs` in `alles.mjs`).
- `tokens.json` ↔ `ontwerptaal.css`: 0 verschillen. `contrast.json` ↔ eigen herberekening: 0 afwijkingen.
- Laagste tekstpaar: 4,56:1 licht (stale-ink op arcering) en 4,93:1 donker (heat-ink op heat-soft).
- ΔE tussen grafiek-/domeinkleur en status: minimaal 16,1 (eis ≥ 15).
- Ringcontrast ≥ 5,13:1. Tweekleurige ring onderling: 9,45 (licht) en 9,51 (donker).
- Paletvalidator (dataviz, zelf gedraaid op `--card` `#FFFFFF`/`#141920`): PASS in beide thema's. Aangrenzend CVD
  8,8/8,4, normaal zicht 17,7/19,3; de eerste 3 slots ook op alle paren.

### Opdracht 2 — bouw en schermafdrukken

`node bouw/alles.mjs --shots --controle` bouwt alles opnieuw zonder fouten: 11 prototypes, `peil.css` 58,3 KB en
**88 schermafdrukken** (11 × 360/390/768/1440 × licht/donker).

| # | Ernst | Bevinding (gezien in de afdrukken) | Reparatie |
|---|---|---|---|
| 2.1 | Middel | **Labels botsen in de geheugengrafiek** op 320/360: "Geen meting" over "Limiet 512 MiB". Mijn overlapdetector zag ook "0" over "06:00". | "Geen meting" staat nu onderaan in het gat. `bouw/ui.mjs` |
| 2.2 | Middel | **x-aslabels stonden verschoven.** Oorzaak is een Tailwind 4-valkuil: `-translate-x-1/2` zet de eigenschap `translate`, en de inline `transform:none` / `translateX(-100%)` telde daar bovenop. Het eerste label stond daardoor gecentreerd op de rand, het laatste 150 % naar links. | Inline `translate:` gebruikt. De valkuil staat nu als regel in §6. |
| 2.3 | Middel | **Offline-scherm was niet consistent.** (a) De waarden zagen er vers uit, met "· gemeten" in vet, en alleen een badge gaf aan dat ze verouderd waren. Dat botst met §4.4 (gearceerd vak, gestippelde rand). (b) "Onboarding verder" stond op één scherm zowel uit als aan. (c) Lezen ("Incident bekijken") was geblokkeerd, terwijl "Downloads bekijken" werkte. (d) Kosten toonde offline nog "ophalen…". | Elke kaart is nu verouderd: gestippelde rand en een vak "Laatst bekend · 11:52". Lezen blijft werken ("Toont de stand van 11:52"); wat iets wijzigt staat uit. Kosten = Onbekend, nooit opgehaald. De regel staat in §9. `bouw/pagina-home.mjs` |
| 2.4 | Middel | **De actieve modus "Verwarmen" was primair-blauw.** Blauw is in het huisdomein "koelen", en my_house kleurt deze knop oranje. | Domeinstijl (heat-vlak, heat-rand, check-icoon) met `aria-pressed`. `bouw/pagina-huis.mjs`, COMPONENTEN KlimaatZone |
| 2.5 | Middel | **De goedkeuringsteller stond mobiel op "AI".** Goedkeuringen komen ook van gebruikers (zoals de R3 "Aangevraagd door Beheerder"). | De teller staat nu op "Meer"; de Meer-sheet begint met Goedkeuringen, en op de goedkeuringspagina is Meer het actieve item. `bouw/ui.mjs`, §4.6, COMPONENTEN |
| 2.6 | Laag | **Twee uitklapblokken zonder zichtbare aanwijzing:** "Details voor een volwassene" en "Technische details". `inline-flex` verbergt de standaardmarker. | `chevron-down` die bij openen draait. `componenten.css`, `ui.mjs`, `pagina-kind.mjs` |
| 2.7 | Laag | **Bron als losse zin.** De energiekaart had de bron als zin in plaats van de vaste `dl`. De laadkaart Kosten had geen Bron/Bijgewerkt. | Beide hebben nu de standaard-`dl` (Bijgewerkt: "nog niet — wordt opgehaald sinds 11:55"). |

Gecontroleerd en in orde: geen overloop op 320–1440, geen afgekapte tekst, geen onleesbare vlakken in donker, de tabs
lopen op mobiel netjes om, en het kruimelpad en de R3-stappen zijn duidelijk.

### Opdracht 3 — axe-core (eigen run)

| Meting | Vóór | Na herstel |
|---|---|---|
| axe WCAG 2.0/2.1/2.2 A+AA, 10 → 11 schermen × 6 breedtes × 2 thema's | 0 | **0** |
| axe best-practice | `region` 12× per scherm (voorbeeldbanner buiten een landmark) | **0** (banner is nu `<aside aria-label="Voorbeeldgegevens">`) |
| horizontale overloop | 0 | 0 |
| doelen < 44 px (radio/checkbox: label telt) | 0 | 0 |
| tekstoverlap (eigen detector) | 2 echte (2.1) | 0 |
| controle van de maker (`controle/samenvatting.txt`) en het gedragstest | alles geslaagd | alles geslaagd (11 schermen) |

axe kan het contrast op de arcering zelf niet bepalen (gradiënt). Dat is apart gedekt: de controle van de maker meet de
donkerste arceerpixel (≥ 4,56:1), en mijn matrix rekent `stale-ink` op `stale-hatch` uit.

### Opdracht 4 — platformeisen en NL-teksten

| # | Ernst | Bevinding | Reparatie |
|---|---|---|---|
| 4.1 | Hoog | **"Gekoppeld" was een groene pil** op de statuspagina. Dat botst met §4.1 regel 1: groen nooit voor "verbonden". | Neutrale pil `pil-neutraal` met `link-2`. Nieuwe rij "Gekoppeld" in §4.3. |
| 4.2 | Middel | **`capability_unavailable` (GPU per app) gebruikte `circle-help`** (Onbekend). Het vaste icoon is `circle-slash`, en in `problemen.html` stond dat wel goed. | Status `nietbeschikbaar` met `circle-slash`. Rij toegevoegd in §4.3. |
| 4.3 | Middel | **Tegenstrijdige regels.** §4.1 zegt "rood nooit voor 'nog niet ingevuld'", maar de wizard toont een rode veldfout bij "Kies ja of nee". | Regel 12: een veldfout ná een verzendpoging is rood; een open besluit of instelling is neutraal. |
| 4.4 | Laag | **Anglicismen:** Snoozen / Gesnoozed, Safe mode, Blast radius, Runbook, Healthcheck, allowlist. | Uitstellen / Uitgesteld tot, Veilige modus, Reikwijdte, Stappenplan, Gezondheidscontrole, lijst met toegestane acties. Alles staat nu in de vaste woordenlijst (§11.1). Vaktermen van de bron zelf (scrub, digest, crashloop tussen haakjes) blijven. |

Gecontroleerd en in orde:
- `unknown` en `stale` zijn nergens groen. Totaalstatus = slechtste onderdeel.
- Elke kaart heeft waarde + eenheid + bron + bijgewerkt (na 2.7).
- De risicoklassen in de prototypes kloppen met contract §8: herstart/stop R1, update/uninstall/rollback R2, data
  verwijderen R3 en nooit door AI aangeboden. Woord en treden-glyph staan er altijd bij.
- De boiler is alleen meten: er is geen schakelaar in de DOM.
- Status is nooit alleen kleur: icoon + woord + vorm, de meter met tekst, de segmentbalk met tabel.
- Kindprofiel: geen codes in beeld.
- Fout = code + NL-melding + kopieerbare trace-ID.

### Opdracht 5 — werkt het met Tailwind 4 + shadcn/ui, en de statuspagina zonder JS?

- **Tailwind 4.3.5 + shadcn new-york v4** (`tw-test/test.html`, letterlijke klassen uit Button, Card, Input, Tabs, Dialog-overlay
  en Sidebar):
  - Werkt: `bg-background`, `text-foreground`, `border`, `ring-ring/50`, `bg-primary/90`, `bg-black/50`, `dark:bg-input/30`,
    `fill-chart-2`, `bg-sidebar-*`, `shadow-xs` en alle statusklassen (`text-degraded-ink bg-degraded-bg border-degraded`,
    `bg-risk-2-solid`, `arcering`, `focus-ring`, `cijfers`, `h-touch`, `max-w-content`).
  - Donker werkt via `.dark` en via `[data-theme=dark]`.
  - `text-red-500` en `bg-green-600` bestaan niet, zoals bedoeld.
- **2.8 · Hoog — `z-nav`, `z-sticky`, `z-overlay` en `z-toast` bestonden niet.** COMPONENTEN schrijft ze voor
  (`sticky top-0 z-nav`), maar de tokens stonden alleen in `:root`. Gemeten: `z-index: auto`.
  **Hersteld:** `--z-index-*` in `@theme`; gemeten nu `z-index: 30`.
- **2.9 · Middel — `max-w-prose` compileert altijd naar 65ch.** De documentatie zei 40 rem, en een eigen `--spacing-prose`
  veranderde daar niets aan. **Hersteld:** de token is nu 65ch, `--spacing-prose` is weg en de documentatie is aangepast.
- **Codemod nodig, bevestigd:** shadcn `bg-destructive text-white dark:bg-destructive/60` geeft in donker wit op een
  doorschijnend lichtrood. Dat staat al in de codemodtabel. Twee regels toegevoegd:
  - de `@custom-variant dark` en het variabelenblok die `shadcn init` schrijft, moeten weg;
  - shadcn-`z-50` wordt `z-overlay`/`z-toast`.
- **Statuspagina:**
  - `statuspagina.css` is 6 748 B (2 257 B gzip).
  - Zonder JS, onder CSP `default-src 'none'; style-src 'unsafe-inline'`: 0 CSP-schendingen en 0 externe verzoeken.
  - Licht/donker volgt `prefers-color-scheme`.
  - Alle 9 inline iconen renderen.

### Opdracht 6 — ONTWERPTAAL.md compleet en eenduidig; migratiepad per app

| # | Ernst | Bevinding | Reparatie |
|---|---|---|---|
| 6.1 | Blokkerend | **Het statuspagina-sjabloon volgde contract 1.1, niet 1.2.** Er was een "Ontkoppelen"-formulier met lokale ontkoppelcode, terwijl §3.7 zegt: *geen ontkoppelen, geen lokale ontkoppelcode*. Het verplichte veld **Hub-vingerafdruk** ontbrak. De schrijfsleutel van de executor zat in het koppelformulier, terwijl §3.9 die *na het koppelen* vraagt. Het formulier verscheen bij elke niet-gekoppelde toestand, terwijl het er alleen mag zijn als de dienst *nog nooit* gekoppeld was. De geldigheid stond vast op "30 minuten" (diensten: 60). | Sjabloon herschreven met precies één koppeltoestand: `koppelformulier` / `gekoppeld` / `ontkoppeld` / `ingetrokken`. Drie verplichte velden (adres, code, vingerafdruk). `{{koppelcode_geldig}}`. Alleen de executor heeft `schrijfsleutel_formulier` (na koppelen) en `executor_beheer` (ontkoppelen of sleutel vervangen, alleen met de opnieuw ingevoerde en live geverifieerde schrijfsleutel). Tweede prototype `statuspagina-gekoppeld.html`. §13.2, COMPONENTEN §25 en ADR bijgewerkt. |
| 6.2 | Middel | **Pad van de bron van waarheid** was `design/peil/`; contract §13 schrijft `docs/platform-v2/ONTWERPTAAL.md` + `design/ontwerptaal/` voor. | Overal aangepast: ONTWERPTAAL §14, ADR "Vervolg", kopteksten van de aliaslagen en de statuspagina. |
| 6.3 | Middel | **Hub-migratiepad was incompleet.** Het themascript moet vóór de aliaslaag komen, en alle drie de eigen kleurblokken van `globals.css` moeten weg. Anders wint het media-blok (specificiteit 0,2,0) en krijg je een half donker thema. | §13.1 stap 3/4 herschreven; de kop van `hub-p0.css` noemt de drie stappen. |
| 6.4 | Middel | **MediaGuard/MSO fase 1 beloofde "alle 980 regels en inline styles volgen direct" en "≥ 14 px".** Kleuren volgen wel. Lettermaten niet: mg.css heeft ± 120 harde maten < 14 px (MSO ± 98), inline ± 189 (MSO ± 254). | §13.3 eerlijk gemaakt: ≥ 14 px pas na fase 2/3. De episodekaart blijft in fase 1 kleur-alleen; in fase 2 komen textuur + tabel. Extra aliascorrecties uit 1.2 (zie boven) en: pauze = Gepauzeerd, diff zonder rood/groen, AI-zekerheid in inkt, DV/HDR/AV1 neutraal, fasebalk zonder opacity. Gemeten met de echte `mg.css`. |
| 6.5 | Laag | **home-control-hub `status_page.py` heeft nog het 1.1-gedrag** (ontkoppelcode, geen vingerafdruk). | Als contractpunt genoemd in §13.2 (niet ontwerp). De tests op `ontkoppelcode_onjuist` vervallen bij de ombouw. |
| 6.6 | Laag | **Prototype en specificatie liepen uiteen:** master-detail op mobiel (het prototype stapelt), en "Opslaan en later verder" ontbreekt < 640 px. | Beide expliciet beschreven in §9. |
| 6.7 | Laag | **Bouwscripts hingen stil af van MediaGuards `node_modules` (axe-core).** | `controle.cjs`: `$AXE_CORE` → `.review-tools` → MediaGuard, met een duidelijke fout als axe-core ontbreekt. (De dataviz-validator gebruikt al `$DATAVIZ_VALIDATOR`.) |

Gecontroleerd: de migratiepaden voor my_house (fase 1 hex-aliaslaag, klassen en testids ongewijzigd) en de statuspagina's
(gepinde kopie + sha256-CI) zijn concreet. Na 6.1 en 6.3 geldt dat ook voor de Hub en MediaGuard/MSO. In de docs verwijst
geen `--token` of utility meer naar iets dat niet bestaat (eigen kruiscontrole).

## Bewust niet gewijzigd

1. `domain-heat-bg` ligt ΔE 1,6 van `degraded-bg`, en `domain-light-on-bg` 2,3. Het zijn gevestigde my_house-betekenissen.
   Ze onderscheiden zich door icoon (flame/lightbulb tegen triangle-alert), woord en vorm (geen 2 px statusrand). Regel 9
   noemt de meting nu expliciet.
2. `chart-3` "aqua" (#00a672, tint 162°) ligt dicht bij groen. Het staat wel ΔE ≥ 16 van `healthy`, valideert in de
   dataviz-skill, en de referentiepalet van de skill behandelt aqua en groen als twee aparte tinten. Het vlak en de inkt
   van de boiler zijn nu neutraal (1.3).
3. De episodekaart van MediaGuard (`.heat-cell--*`) blijft in fase 1 kleur-alleen. Een textuur of tabel is een
   UI-toevoeging (fase 2, en akkoord van de gebruiker zoals bij de andere grafiektoevoegingen).
4. De `instance-logo`-kleuren van MediaGuard/MSO blijven. Het zijn logo's met `aria-hidden` (merkuitzondering in WCAG 1.4.3).
5. De grafiek heeft `role="img"` met toetsenbordbediening. In de bladermodus van een schermlezer werken de pijltjes niet.
   De tabelweergave is de toegankelijke tweeling, dus dit voldoet. Een echte NVDA/TalkBack-test blijft open.
6. Uitgeschakelde radio's zijn zwak van contrast. Dat is uitgezonderd in WCAG, en de reden staat er in volle tekst naast.
7. Kindprofiel: `hourglass` voor "Een volwassene kijkt ernaar". De betekenis "nog niet beschikbaar" klopt voor het kind.
8. Het totaal op de statuspagina gebruikt alleen de vaste toonlijst. "Niet gekoppeld" in de controles toont daarom het
   Onbekend-icoon; het koppelblok gebruikt `link-2-off`.

## Open (niet door de review op te lossen)

- Besluiten van de gebruiker blijven zoals de maker ze meldde: O-05, O-07, O-09, O-11, de tabelweergave bij de bestaande
  grafieken en de native Android-apps.
- Niet getest: een echte schermlezer (NVDA/TalkBack), een echte Android-telefoon in fel licht en een tv/speler (08_UI).
- Na "OVERDRACHT VOLTOOID": commit naar de contractpaden (6.2) en O-03 in de Hub-code.

## Gewijzigde bestanden (alleen in `<werkmap ontwerp>/`)

- **Bron (`definitief/bouw/`):**
  - `tokens.mjs` (1.1.0; boiler neutraal; prose 65ch)
  - `genereer.mjs` (z-index-thema, icoon-map, herkomstpad)
  - `aliaslagen.mjs`
  - `statuspagina.sjabloon.html`, `statuspagina.bron.css`
  - `ui.mjs`, `componenten.css`
  - `pagina-home.mjs`, `pagina-huis.mjs`, `pagina-problemen.mjs`, `pagina-appdetail.mjs`, `pagina-kind.mjs`,
    `pagina-statuspagina.mjs`
  - `iconen.mjs`/`iconen.json` (+ `link-2`)
  - `bouw.mjs`, `alles.mjs`, `docs.mjs`, `controle.cjs`
  - nieuw: `contrast-breed.mjs`
- **Gegenereerd** (opnieuw gebouwd):
  - `tokens.json`, `ontwerptaal.css`, `statuspagina.css`, `statuspagina.html`, `contrast.json`
  - `aliaslagen/*.css`
  - `prototypes/*.html` (+ `statuspagina-gekoppeld.html`), `prototypes/css/peil.css`
  - `shots/` (88), `controle/`
- **Documentatie:** `ONTWERPTAAL.md`, `COMPONENTEN.md`, `ADR-ONTWERPTAAL.md` (versie 1.1.0, herstellingen beschreven).

## Opnieuw uitvoeren

```sh
cd design/ontwerptaal
node bouw/alles.mjs --shots --controle                    # bouw, contrast (2 matrices), afdrukken, axe, gedrag
cd ../.review-tools
node scripts/contrast-review.mjs ../definitief            # onafhankelijke matrix (domein-op-eigen-vlak telt hier als fout:
                                                          #   3 paren, sinds regel 11 verboden en niet meer gebruikt)
node scripts/axe-review.cjs ../definitief/prototypes uit/axe.json
node scripts/statuspagina-nojs.cjs ../definitief/prototypes/statuspagina.html
(cd tw-test && cp ../../definitief/ontwerptaal.css . && npx --prefix design/ontwerptaal/bouw @tailwindcss/cli -i in.css -o out.css && node check.cjs)
```
