# Onderzoek: bestaande UI's (MediaGuard, MSO, my_house, Hub)

Ontwerp-agent · TrueNAS Home Platform V2 · 9 november 2026 · alleen-lezen-onderzoek, er is niets gewijzigd in de repos.

Dit rapport is input voor de ADR over de ene ontwerptaal. Die gebruikt Tailwind CSS 4, shadcn/ui (new-york, CSS-variabelen) en lucide-react. Het beschrijft per app hoe het er nu uitziet en hoe de code in elkaar zit. Daarna volgt wat er moet veranderen en wat dat kost aan tests en schermafdrukken.

**Bronnen**
- De bindende documenten:
  - `ai-server-manager/docs/platform-v2/PLATFORM_CONTRACTEN.md`
  - `01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`
- De code in `apps/web` van de vier repos.
- De ontwerpdocumenten van MediaGuard (`docs/design/*.md`).
- ADR-0009 van de Hub.
- De schermafdrukken in de repos. Die zijn bekeken met de Read-tool.

**Werkwijze**
- Skills:
  - `design:design-system`: audit van tokens, naamgeving en componenten.
  - `design:accessibility-review`: WCAG 2.1 AA.
  - `dataviz`: de bestaande grafiekpaletten zijn gecontroleerd met `validate_palette.js`. Er is nog geen nieuw palet gekozen.
- Contrast is berekend met `wcag-contrast`; zie `scripts/contrast.mjs`.
- my_house heeft geen schermafdrukken in de repo. Daarom is de bestaande `my_house/apps/web/dist` (al gebouwd, niet opnieuw gebouwd) in Chromium geladen:
  - Script: `scripts/myhouse-render.mjs`.
  - De API-antwoorden komen uit de unit-testfixtures van de repo, aangevuld met fictieve voorbeeldwaarden. Alles is gemarkeerd als "voorbeeld"/"Voorbeeldhuis".
  - Uitvoer: `schermafdrukken/myhouse-*.png`, 8 stuks.

**Beperkingen**
- Er is niets gebouwd of gestart, alleen de bestaande dist geladen. Het gedrag is dus afgeleid uit code en bestaande afdrukken.
- Er is niet getest met een schermlezer.

---

## 0. Kernbevindingen

1. **"Tailwind 4 + shadcn" is bij MediaGuard en MSO alleen een label.**
   - Beide importeren `tailwindcss`, maar alleen de preflight wordt echt gebruikt. Er zijn vrijwel geen utility-klassen.
   - Het uiterlijk komt uit een eigen BEM-achtig CSS-systeem: `styles/mg.css` met 63 `--mg-*`-tokens en ongeveer 230 klassen.
   - Daarbovenop staan 823 (MG) en 736 (MSO) inline `style={{…}}`-attributen.
   - MediaGuard heeft een `components.json` (new-york, slate). De drie bestanden in `components/ui/` (badge, button, card) zijn echter geen shadcn-componenten en worden **nergens** geïmporteerd.
   - MSO heeft helemaal geen shadcn.
   - MSO's `recharts 3.10.1` is een **dode afhankelijkheid**: geen enkele import. Alle grafieken zijn eigen SVG.
2. **my_house en de Hub gebruiken geen Tailwind, geen shadcn en geen lucide.**
   - my_house heeft eigen CSS (40 tokens) en 18 eigen SVG-iconen.
   - De Hub heeft eigen CSS (29 tokens) en 15 eigen icoonpaden. ADR-0009 punt 1 legt "geen CSS-framework, geen iconenbibliotheek" uitdrukkelijk vast. De nieuwe ontwerptaal-ADR moet dat punt **vervangen**.
3. **Vier verschillende uitstralingen:**
   - MediaGuard en MSO: één familie, blauw accent, standaard donker. MSO is een kopie (PROVENANCE).
   - my_house: warm, beige/steen, Space Grotesk-koppen, radius 18 px, alleen thema via het systeem.
   - Hub: neutraal grijs/blauw, systeemfont, radius 12 px.
4. **Vier statusvocabulaires voor hetzelfde begrip:**
   - MG/MSO: `success/warning/danger/info/accent/neutral`.
   - my_house: `ok/warn/error/unknown/not_configured`.
   - Hub: `ok/info/warn/bad/unknown/neutral`.
   - Alleen de Hub en my_house hebben een **eigen** `unknown`-toon. MediaGuard toont onbekend als `neutral` met een **pauze-icoon**, en in de zijbalk als "Laden…".
   - Ook de Nederlandse woorden verschillen: degraded heet "Verminderd" (MG), "Verstoord" (MSO), "Let op" (my_house), en het platform heeft er nog geen woord voor.
5. **Platformeis "waarde + eenheid + bron + laatst bijgewerkt" op elke kaart:**
   - Alleen de Hub voldoet volledig, met de componenten `StatCard` en `Freshness`.
   - De KPI-kaarten van MG/MSO tonen geen bron en geen tijdstip; alleen "verouderd" als het verversen mislukt.
   - my_house heeft wel meetkwaliteit ("gemeten/afgeleid/geschat") en een tijd, maar geen bron.
6. **Foutweergave met code, NL-melding en kopieerbare trace_id: geen enkele app heeft een kopieerknop.**
   - MG/MSO tonen een correlation-id onder "Technische details". Die komt uit de header `x-correlation-id` of uit het body-veld `correlation_id`, niet uit `trace_id`.
   - De Hub toont code en trace-id als tekst.
   - my_house toont alleen de melding.
7. **Concrete toegankelijkheidsfouten:**
   - Hub: invoervelden hebben een rand met **1,42:1** (licht) en **1,48:1** (donker) contrast. WCAG 1.4.11 vraagt 3:1.
   - MSO: mist de touch-target-regels die MediaGuard later kreeg. Knoppen zijn op de telefoon 34 px (28 px voor `--sm`). De platformeis is ≥ 44 px.
   - MediaGuard donker: witte tekst op `--mg-danger` haalt 3,18:1 (`.btn--danger-solid`, ongelezen-badge). WCAG 1.4.3 vraagt 4,5:1.
   - MediaGuard mobiel: de titels van "Wacht op jou" worden met een ellips afgekapt.
   - my_house heeft geen geautomatiseerde axe-controle.
8. **De bestaande grafiekpaletten halen de dataviz-validator niet.**
   - MG/MSO `--mg-viz-*`: in donker FAIL op de lichtheidsband, in licht FAIL op de chroma-ondergrens. CVD-scheiding valt in beide thema's in de randzone (7,2 en 7,6).
   - Statuskleuren (success/warning/danger) worden ook als reekskleur gebruikt. Zo krijgt "onzeker" in de verdelingsbalk rood.
   - my_house-energie gebruikt bijna-zwart (`--text-2`) als reekskleur.
9. **De belangrijkste risico's bij migratie zijn naamconflicten en preflight, niet de tests.**
   - De naamconflicten met shadcn:
     - `--muted`: tekstkleur in Hub en my_house, maar achtergrond in shadcn.
     - `--accent`: merkblauw in MG, maar hover-achtergrond in shadcn.
     - `--primary`: bijna-zwart in my_house.
     - `--radius`: 18 px (my_house), 12 px (Hub) en 0,625 rem (shadcn).
   - De Tailwind-preflight haalt nummering van `<ol>` weg (Hub `ol.howto`, my_house `.steps-list`) en zet de marges van koppen op 0.
10. **De impact op tests is beheersbaar.**
    - Geen enkele app gebruikt visuele snapshot-asserties (`toHaveScreenshot`). Schermafdrukken worden alleen als documentatie weggeschreven.
    - Tests leunen vooral op `data-testid` en rollen: MG 225 en 238, Hub vrijwel alleen testids en rollen.
    - Wel geraakt:
      - een kleine set klasse-selectors;
      - het attribuut `data-theme`;
      - de unit-test van de Hub die het `?`-symbool van `StatusBadge` controleert;
      - de unit-tests van my_house op CSS-klassen;
      - het opnieuw maken van alle doc-schermafdrukken: 56 (MG `after`), 64 (MSO), 29 (Hub).

---

## 1. Vergelijking in één tabel

| Onderdeel | (a) MediaGuard | (b) MSO | (c) my_house | (d) Hub (ai-server-manager) |
|---|---|---|---|---|
| Stack | Next 16.3.3, React 19.2.8, TS 6, Tailwind 4.3.3 (postcss) | idem; recharts 3.10.1 (ongebruikt) | Vite 5.4, React 18.3, react-router 7, TanStack Query 5, vite-plugin-pwa | Next 16.4.5, React 19.3.1, TS 5.9, PWA (eigen SW) |
| CSS-architectuur | `styles/mg.css` (980 r.) + `av1.css` (119 r.), BEM-achtig; Tailwind alleen preflight | kopie van `mg.css` (794 r., commit `e92c2acc`, **verouderd**) + `mso.css` (51 r.) | `styles.css` (357 r.) + 4 domein-CSS (241 r.); geen Tailwind | `globals.css` (907 r.); geen Tailwind |
| shadcn | `components.json` (new-york/slate); 3 niet-shadcn stubs, **ongebruikt** | geen | geen | geen |
| Tokens | 63 `--mg-*` (kleur, type, spacing, radius, schaduw, layout) | identiek aan MG + logo-kleuren | 40 (warm palet + domein: heat/cool/boiler/light-on) | 29 (kleur + tones + layout) |
| Hardcoded | 823 inline styles, 157 font-size-declaraties met 18 waarden (9–28 px), 11 radiuswaarden | 736 inline, 16 font-sizes | 211 inline, 14 font-sizes (11–34 px), 17 radiuswaarden | 41 inline, 11 font-sizes (rem), 5 radii |
| Lettertype | Inter Variable + JetBrains Mono (zelf gehost, `next/font/local`) | idem | Inter (400/500/600) + **Space Grotesk** (koppen) via fontsource | **systeemfont-stack**, systeem-mono |
| Iconen | lucide-react 1.66.0, 16 px, stroke 1.75 | idem | 18 eigen SVG's (stroke 1.8, 20 px) | 15 eigen paden (stroke 1.8, 22 px) |
| Thema | `data-theme` op `<html>`, **standaard donker**, keuze Donker/Licht/Systeem (`mg.theme`) | idem (`mso.theme`) | alleen `prefers-color-scheme`, **geen keuze** | `data-theme` licht/donker, zonder attribuut = systeem (`hub-thema`) |
| Radius | 6/8/10/12/14 | idem | 10 (knop), 14, **18 (kaart)** | 10 (knop), **12 (kaart)** |
| Breekpunt navigatie | ≤ 860 px onderbalk | ≤ 860 px | ≤ 820 px | < 1024 px onderbalk |
| Ondernavigatie | 5: Overzicht, Activiteit, Bibliotheek, Ruimte, Aanvragen (rest in profielmenu) | 4 + Meer | 4 + Meer (sheet) | 5: Home, Apps, Problemen, AI, Meer (platformeis) |
| Status-tonen | success/warning/danger/info/accent/neutral | idem | ok/warn/error/unknown/not_configured/info | ok/info/warn/bad/unknown/neutral |
| Onbekend ≠ groen | ja, maar als `neutral` + pauze-icoon | ja (`neutral` + CircleHelp) | ja (grijze stip + "Onbekend") | ja, eigen `unknown` + `?` |
| Bron + laatst bijgewerkt | nee (alleen stale-melding) | deels ("getest 2 min geleden") | tijd + meetkwaliteit, geen bron | **ja, overal** (`Freshness`) |
| Fout | `ErrorState`: NL-tekst, HTTP, pad, correlation-id in `<details>` | idem + `code` | `ErrorNote`: NL-tekst, geen code/id | `ErrorPanel`: NL-tekst, code, HTTP, trace-id (geen kopieerknop) |
| Laden | skeleton | skeleton | tekst "Laden…" | tekst "Laden…" |
| Leeg | `StateView empty` (icoon, titel, tekst, actie) | idem | kleine grijze tekst | per scherm tekst |
| Niet beschikbaar | `StateView unavailable` (toont endpoint) | `UnavailableState` (connector niet ingesteld) | `not_configured` | `NotYetAvailable` (fase + bron), `capability_unavailable` als tekst |
| Offline | `StateView offline` + "Live"-indicator | idem | banner, data gedimd, acties uit | banner, data onbekend |
| Risico/acties | `DangerDialog` (impact, dataset, snapshot, oud→nieuw, rollback, getypte bevestiging), `DiffViewer`, dry-run | `RiskChip` (advies / automatisch veilig / toestemming nodig), `change-preview` | geen eigen patroon | nog niet (P2) |
| a11y-tests | axe (licht: color-contrast) op enkele schermen, 44 px-test, overflow | axe wcag2a/aa/21aa/22aa per scherm × thema × 1440/390 | **geen axe**; wel focus/rollen in unit-tests | axe WCAG 2.2 A/AA op 360/390/768/1440, 44 px, overflow, skiplink |
| Visuele snapshots | geen (`page.screenshot` → docs) | geen (→ `docs/screenshots`) | geen | geen (→ `docs/screenshots/p0`) |

---

## 2. Per app

### (a) MediaGuard (`media-guard-ultimate/apps/web`)

**Stack**
- Next 16.3.3 (App Router), React 19.2.8, TypeScript 6.0.3.
- Tailwind 4.3.3 via `@tailwindcss/postcss`.
- lucide-react 1.66.0, `@tanstack/react-virtual`.
- Eigen server (`server.mjs`).
- i18n: nl-NL en en-US. `lang` wordt dynamisch gezet.
- 124 tsx-bestanden.

**Tokens en kleur** (`styles/mg.css`)
- Gedocumenteerd in `docs/design/DESIGN_SYSTEM.md` en `CONTRAST_REPORT.md`: 82 combinaties, allemaal AA.
- Donker (standaard):
  - Oppervlakken: bg `#0C111B`, surface `#141C29`, raised `#1C2735`, sunken `#0A0E16`.
  - Tekst: `#F0F4FA`, `#A4B0C1`, `#8592A5`.
  - Accent `#4F9CF9`.
  - Status: success `#35B587`, warning `#E8A44D`, danger `#E36B71`, info `#8C9DF5`.
  - Tints met 12 % kleur.
- Licht: bg `#F4F6FA`, accent `#1D66C9`, success `#167650`, warning `#8F5300`, danger `#BE2F39`.
- Verder in het bestand:
  - `--mg-viz-1…6` (categorisch) en `--mg-lane-gpu/cpu`.
  - Fontgroottes 11–28 px, spacing 4–32, radius 6–14.
  - Drie schaduwniveaus en layoutmaten (zijbalk 256, topbalk 60, content max 1520).

**Typografie**
- Inter Variable (latin-subset) en JetBrains Mono (preload uit), zelf gehost met OFL-licenties.
- Body 14 px, paginatitel 24/680, KPI 28/680, kaarttitel 14/650, eyebrow 11 px kapitalen.
- In de praktijk staan er in de CSS 18 verschillende groottes, waaronder 9 px (`.poster-fallback`), 10 px en 10,5 px. In inline styles komen `fontSize: 12/12.5/13/11.5` samen 180 keer voor.

**Spacing en radius**
- Er bestaat een schaal, maar inline `gap/margin` worden veel gebruikt (73× `gap: N`, 45× `margin`).
- In CSS staan 11 verschillende radiuswaarden (2–12 px).

**Iconen**
- lucide, 16 px, stroke 1.75, `aria-hidden`.
- Vaste icoonkoppeling per status:
  - `CircleCheck`: ok;
  - `TriangleAlert`: waarschuwing;
  - `CircleX`: fout;
  - `LoaderCircle`: bezig;
  - `Info`: info;
  - `Pause`: neutraal;
  - `Lock`: vergrendeld.

**Componenten** (`components/mg/*`, ongeveer 60 bestanden)
- Primitieven:
  - `StatusChip`, `Button` en `LinkButton` (primary/secondary/ghost/danger/danger-solid, sm, icon);
  - `Switch` (role=switch), `Card` (section + heading + eigen ErrorBoundary), `PageHeader`;
  - `Segmented`, `Tabs` (ook `variant="chips"`), `Modal`/`DangerDialog`, `Toast`.
- Toestanden: `StateView` (loading/empty/error/offline/unavailable/forbidden/not_found), `ErrorState`, `ResourceView` (met stale-markering), `Skeleton`, `StaleMark`.
- Domein: `KpiCard`, `EvidenceCard`, `DiffViewer`, `Stepper`, `Timeline`, `SeasonHeatmap`, `QualityRibbon`, `Poster`, `JobCard`, `InstanceCard`, `SettingField` met overervingstrace, `DistributionBar`.
- Grafieken: eigen `LineChart`/`BarChart` (SVG). Die vervingen recharts.
- Shell: zijbalk, topbalk met zoeken, aandachtspil, meldingen, noodstop en profiel; onderbalk; skip-link.
- `components/ui/*` zijn drie stubs (`badge`, `button`, `card`) die naar niet-bestaande klassen verwijzen (`.badge-…`, `.button-…`). Ze worden nergens geïmporteerd.

**Patronen**
- Status is altijd kleur + icoon + tekst. Dat is vastgelegd als principe.
- Fout: `ErrorState` toont gewone taal. Daaronder staan "Technische details" (HTTP, pad, correlation-id) en "Opnieuw proberen".
- Leeg: icoon in een tegel, titel en tekst.
- Laden: skeleton.
- Stale: "Metadata N min oud".
- Niet beschikbaar: toont het endpoint.
- Gevaarlijke acties: `DangerDialog` met impactblok en snapshot/rollback.
- "Wacht op jou"-lijst met één actie per regel.

**Licht/donker**
- `data-theme` op `<html>`, standaard `dark`.
- Een inline script zet het thema vóór de eerste paint.
- Keuze in topbalk en profielmenu, met standaard per server (`ui.theme`).

**Navigatie**
- Vijf hoofdonderdelen en Instellingen onderaan. Telefoon: onderbalk met 5 items, de rest in het profielmenu.
- Sneltoetsen `g o`, `/` en `?`.
- Maximaal één tabrij per pagina, afgedwongen in de e2e.

**Schermafdrukken in de repo**

| Map | Aantal | Inhoud |
|---|---|---|
| `docs/design/after` | 56 | 14 schermen × 1440/390 × licht/donker |
| `before` | 8 | |
| `previews/screenshots` | 42 | |
| `prototype` | 12 | |
| `screenshots-app` | 56 | |
| `android` | 32 | native app, valt buiten deze opdracht |
| `docs/reports` | 55 | jpg |

Bekeken: `after/overzicht-1440-dark.png`, `overzicht-390-light.png` en `ruimte-1440-light.png`.
- Rustig en informatiedicht. De rode kaart "N dingen hebben je hulp nodig" springt eruit.
- Op 390 px worden lijsttitels afgekapt ("Vervangen van besta…").
- De vaste onderbalk staat in full-page-afdrukken midden in het beeld. Dat komt door de afdruk, niet door de UI.
- De zijbalk toont groen "Live" terwijl de pagina tegelijk "Live verbinding maken…" meldt (ruimte-1440-light).
- KPI's zonder data tonen een grote "—" met "Nog niet beschikbaar".
- Items in "Wacht op jou" krijgen het icoon `CircleCheck`. Een vinkje betekent "in orde", dus dat is verwarrend voor een openstaande taak.

**Toegankelijkheid**

| # | Bevinding | WCAG | Ernst |
|---|---|---|---|
| 1 | Wit op `--mg-danger` `#E36B71` in donker = **3,18:1** (`.btn--danger-solid` 13 px semibold in de bevestigknop van `DangerDialog`; `.dot-badge` 10 px bij ongelezen meldingen) | 1.4.3 | Groot |
| 2 | Lijsttitels "Wacht op jou" op de telefoon met ellips afgekapt, volledige tekst niet beschikbaar | 1.4.10 / bruikbaarheid | Groot |
| 3 | `CircleCheck` als icoon voor openstaande taken; `Pause` als icoon voor `neutral`, dat ook voor "onbekend" wordt gebruikt | 1.3.1 (betekenis van icoon) | Middel |
| 4 | Zijbalk-gezondheid `unknown` toont "Laden…" in plaats van "Onbekend" | 4.1.3 / eerlijkheid | Middel |
| 5 | Lettergroottes 9–10,5 px (posterfallback, badges, stapnummers) | leesbaarheid | Klein |
| 6 | Grafiek-tooltips alleen via pointer; geen tabelweergave | 2.1.1 / 1.1.1 | Middel |
| 7 | Groen "Alles in orde" in de zijbalk volgt het aantal regels in "Wacht op jou", niet `health.level`. Als die bronnen niet laden, blijft het groen (af te leiden uit de code, niet gereproduceerd) | eis "nooit groen bij onbekend" | Middel (te verifiëren) |

Wat goed is:
- skip-link, `:focus-visible` (2 px + offset) en `prefers-reduced-motion`;
- 44 px-doelen bij ≤ 860 px (`werk-r030.spec.ts` controleert `main .btn`);
- `aria-sort`, `role=switch` en `alertdialog` met focus op Annuleren.

**Wat moet veranderen**
- Tokens: `--mg-*` gaat over op platformtokens, met shadcn-variabelen als technische laag.
- Statusvocabulaire: een eigen `unknown`-toon met eigen icoon (bijvoorbeeld `CircleHelp`), en "Verminderd" wordt het platformwoord.
- KPI-kaart krijgt bron + laatst bijgewerkt.
- Fout: `trace_id` met kopieerknop.
- Grafiekpalet en contrast van danger-solid.
- Inline styles naar utilities.
- De stubs in `components/ui` vervangen door echte shadcn-componenten.
- Lettertype, radius en accent volgen de platformkeuze.
- De routes, functies, sneltoetsen, IA, testids en rollen blijven.

**Migratiepad**
1. **Aliaslaag.** `mg.css` blijft, maar elke `--mg-*` verwijst naar een platformtoken (`--mg-surface: var(--card)` enzovoort). Daarmee volgen alle 980 regels en 823 inline styles direct de nieuwe taal, zonder dat de componenten veranderen.
2. **Dark-variant.** `data-theme` als dark-selector in Tailwind (`@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *))`), zodat tests op `data-theme` blijven werken.
3. **Primitieven vervangen.** `Button`, `StatusChip`, `Card`, `Modal`, `Tabs`, `Switch`, `Segmented` en `Toast` worden shadcn-componenten. De bestaande component-API, `data-testid`, rollen en een paar hook-klassen blijven (`.btn`, `.sidebar`, `.nav-item`, `.bottomnav`, `.state--error`, `.tech-details`, `.search-sheet`, `.savebar`, `.top-pill`, `.list-row`, `.chip`, `.card-title`, `.inline-state--danger`, `.hide-md`).
4. **Inline styles per scherm omzetten** naar utilities.
5. **Opruimen:** `mg.css` uitfaseren, `components.json` naar `baseColor` van het platform.

**Impact op tests**
- Geen snapshot-baselines.
- Raakt wel:
  - de 14 klasse-selectors uit stap 3: behouden of de test aanpassen;
  - `werk-r030` (selector `main .btn` voor 44 px);
  - `mediaguard.spec`, `werk-ia` en `werk-apikeys` (thema via `data-theme` en `mg.theme`);
  - axe color-contrast in licht: moet 0 blijven.
- `design-shots.spec.ts` maakt `docs/design/after` opnieuw: 56 afbeeldingen opnieuw genereren en committen.
- De Playwright-config draait alleen `desktop-1440`. Mobiel wordt per test gezet.

### (b) Media Source Optimizer (`media-source-optimizer/apps/web`)

**Stack**
- Next 16.3.3, React 19.2.8, Tailwind 4.3.3 en lucide 1.66.0, gelijk aan MG.
- `recharts 3.10.1` staat in `dependencies` maar **wordt nergens geïmporteerd**. Grafieken zijn eigen SVG (`goals-card.tsx`, `usenet/categories.tsx`, `Sparkline`).
- Alleen NL. 89 tsx-bestanden.

**Herkomst**
- `PROVENANCE.md` noemt `styles/mg.css`, `primitives.tsx`, `states.tsx`, `domain.tsx`, de shell, de API-client enzovoort een "internally versioned copy" van MediaGuard commit `e92c2acc`.
- Volgens `PROVENANCE.md` is `mg.css` verbatim gekopieerd. Hij is inmiddels **verouderd**:
  - MG is 980 regels, de MSO-kopie 794 regels; 192 regels verschillen.
  - Onder meer ontbreken de telefoonregels "raakvlak minimaal 44 px, tekst minimaal 13 px", de meldingen-popover en de overflowbewaking van meterrijen.
- De tokens zijn wel identiek.
- `mso.css` voegt toe: de merktegel "MSO", `.estop--pause` (pauzeknop in warning-kleur), logokleuren per connector met lichte varianten voor contrast, dialoogmaten en inactieve rijen zonder opacity.

**Tokens, typografie, iconen en radius:** als MG.

**Componenten**
- Overgenomen: `StatusChip`, `Button`, `Card`, `StateView`, `ErrorState`, `KpiCard`, `DiffViewer`, `Stepper`, `Timeline`, `DangerDialog`, `PendingAction`.
- Hernoemd: `ConnectorCard`, `ConnectorStatusChip` (met `CircleHelp` voor onbekend), `ConnectorLogo`.
- Eigen: `RiskChip`, `UnavailableState`, `change-preview`, `mode-gate`, en domeinkaarten voor automatisering, kosten, indexers, usenet, torrent en recovery.

**Patronen**
- `healthTone()` zet alles wat niet bekend is op `neutral` met het label "Onbekend", "Niet ingesteld" of "Uitgeschakeld".
- `UnavailableState` linkt naar Instellingen → Verbindingen en toont nooit placeholderdata.
- `RiskChip` heeft drie niveaus:
  - `advies` (info);
  - `automatisch_veilig` (**success-groen**);
  - `toestemming_nodig` (warning).
- Dat model past niet op R0–R3. Groen voor een risiconiveau botst bovendien met groen voor "gezond".

**Licht/donker:** als MG, sleutel `mso.theme`, standaard donker.

**Navigatie**
- Gegroepeerde zijbalk met 15 items in 6 groepen: Zoeken & bronnen, Usenet, Torrents, Operaties, Integraties, Systeem.
- Onderbalk: Overzicht, Zoeken, Downloads, Ontbrekend en Meer (lade).
- Topbalk: "wacht op jou", modus "Alleen-lezen" en "Automatisering pauzeren".

**Schermafdrukken:** `docs/screenshots/` bevat 64 afdrukken (16 schermen × 1440/390 × licht/donker), gemaakt door `e2e/screens.spec.ts`. Bekeken: `overzicht-light-1440`, `overzicht-dark-390` en `kosten-dark-1440`.
- Erg informatiedicht en vrijwel identiek aan MediaGuard.
- "Gezondheid: Verstoord" staat in grote oranje tekst.
- Groene chips worden ook voor gewone waarden gebruikt: "Laatste back-up 2m 41s" en "Mislukte taken 0".
- Op 390 px oogt de knop "Automatisering" in de kop ongeveer 34 px hoog.

**Toegankelijkheid**

| # | Bevinding | WCAG / eis | Ernst |
|---|---|---|---|
| 1 | Geen 44 px-regel op de telefoon: `.btn` 34 px, `.btn--sm` 28 px, `.icon-btn` 34 px, segmented 28 px | platformeis ≥ 44 px (2.5.5) | Groot |
| 2 | Wit op danger in donker 3,18:1, als bij MG (`.btn--danger-solid`) | 1.4.3 | Groot |
| 3 | Groene chips voor waarden die geen gezondheidsoordeel zijn ("2m 41s", "0") | consistentie: groen = gezond | Middel |
| 4 | Groen voor risico "Automatisch veilig" | consistentie | Middel |
| 5 | Grafiek-tooltips via `<title>`, alleen bij hover | 2.1.1 | Klein |

**Wat moet veranderen**
- Alles wat bij MG staat, plus:
  - de 44 px-regels;
  - `recharts` verwijderen, of het als grafiekbasis van het platform kiezen; dat is een open besluit;
  - `RiskChip` omzetten naar de R-klasse-badge van het platform. De MSO-niveaus blijven bestaan en worden visueel gekoppeld.
- Na de migratie kopieert MSO het ontwerpsysteem **niet langer uit MG**. Beide gebruiken de platformlaag, en `PROVENANCE.md` wordt voor de CSS-onderdelen bijgewerkt.

**Impact op tests**
- `screens.spec.ts`:
  - axe op tags wcag2a/aa/21aa/22aa per scherm × thema × 1440/390;
  - wacht op `.skeleton`-telling 0;
  - controleert `.state--error` en `data-theme`.
- `dialogs.spec.ts`: dialoog volledig zichtbaar.
- `smoke.spec.ts`.
- Geen snapshot-baselines. Wel 64 afdrukken in `docs/screenshots` opnieuw maken.

### (c) my_house (`my_house/apps/web`)

**Stack**
- Vite 5.4.21, React 18.3.1, react-router-dom 7.18.5, TanStack Query 5.
- `vite-plugin-pwa`: manifest "Huis", `theme_color #1C1B19`, `background_color #F5F4F0`. Pagina's network-first, `/api` nooit in de cache.
- QR-codes. Vitest met 23 unit-testbestanden en Playwright e2e (10 bestanden).
- nginx-CSP: `style-src 'self' 'unsafe-inline'`, `font-src 'self'`. Dat is geschikt voor Radix/shadcn.

**Tokens en kleur** (`src/styles.css`)
- Warm palet:
  - Oppervlakken: bg `#F5F4F0`, surface `#FFF`, surface-2 `#F0EEE8`, sunken `#EAE8E2`.
  - Tekst `#1C1B19`, `--muted #5F5C55`.
  - `--primary #1C1B19`: de primaire knop is **bijna zwart**.
  - Links/focus `#1F5FBF`.
  - Status: ok `#1E7A46`, warn `#9A5B00`, error `#B42318`.
- Domeintokens: `--heat/-ink/-bg/-soft` (oranje), `--cool*` (blauw), `--boiler`, `--light-on/-ink`, `--rest` (Overig), `--stale`, `--input-border`.
- Donker staat in `@media (prefers-color-scheme: dark)`: bg `#151412`, tekst `#F2F0EA`, en de domeinkleuren lichter.

**Typografie**
- Body: Inter 400/500/600, 15 px.
- Koppen: **Space Grotesk** 500/600 (h1 32 px, op mobiel 26 px). `.big-num` voor temperaturen.
- Code: systeem-mono.
- 14 groottes (11–34 px).

**Spacing en radius:** kaart radius **18 px** en padding 20, knop 10, segmented 12. In totaal 17 radiuswaarden; de bel-/stapknoppen zijn rond.

**Iconen:** `src/components/Icons.tsx` met 18 eigen lijniconen (Home, Grid, Thermo, Bulb, Bolt, …), stroke 1.8, `aria-hidden`.

**Componenten** (`components/bits.tsx` en domeinmappen)
- Algemeen:
  - `QualityBadge` (gemeten/afgeleid/geschat/ontbreekt);
  - `Dot` en `StateLabel` (stip + NL-woord);
  - `ActionButton` (offline automatisch uit, met uitleg in `title`);
  - `Loading` (tekst), `ErrorNote`, `Empty`, `CopyButton` (met live-melding), `ProgressBar` (ARIA);
  - `Tabs` (role=tablist), "Meer"-sheet met focus-trap, `OfflineBanner`, `NoHome`;
  - wizard (stappen), `choice-card`, `stack-mobile`-tabellen.
- Domein:
  - klimaatdial/setpoint, `mode-btn` (geblokkeerd = gestippeld);
  - lichttegels, energiebalken (gestapeld, gearceerd "Overig", "onvolledig" gestippeld), live vermogen;
  - apparaatkaarten, kalibratie.

**Patronen**
- Offline-regel: offline na 3 mislukkingen of 15 s. Dan verschijnt een banner, live-data wordt gedimd (`opacity .55`, grijs) en alle acties gaan uit.
- Data uit een snapshot wordt eveneens gedimd.
- Meetkwaliteit staat per waarde. Een verouderde sensor geeft grijze cijfers en de tekst "Sensor verouderd (5 uur geleden)" in warn-kleur.
- Foutmeldingen in het NL, per code met een link naar de juiste instelling.
- Leeg/laden alleen als tekst.

**Licht/donker:** alleen het systeem, **geen keuze in de app**. De Hub en MG/MSO hebben die keuze wel.

**Navigatie**
- Zijbalk met 7 items (Overzicht, Klimaat, Verlichting, Energie, Optimalisatie, Apparaten, Systeem).
- Mobiel: topbalk en een onderbalk met Overzicht, Klimaat, Licht, Energie en Meer (Optimalisatie, Apparaten, Systeem, Account, Help). Breekpunt 820 px.

**Schermafdrukken:** de repo heeft er geen. Nu gemaakt, als render van de bestaande dist met fictieve fixtures:

| Bestand | Inhoud |
|---|---|
| `schermafdrukken/myhouse-overzicht-licht-1440.png` | Overzicht, licht, desktop |
| `schermafdrukken/myhouse-overzicht-donker-390.png` | Overzicht, donker, telefoon |
| `myhouse-overzicht-{licht,donker}-{390,1440}.png` | overige combinaties |
| `myhouse-inloggen-*` | inlogscherm, 4 combinaties |

Wat opvalt:
- Warm, ruim en vriendelijk ("Goedemiddag", groot 20,6°). De sfeer is duidelijk anders dan bij MG en de Hub.
- Een verouderde waarde (18,2°, sensor 5 uur oud) staat naast een **groene "gemeten"-badge**. Kwaliteit en versheid spreken elkaar visueel tegen.
- De onbereikbare lichttegel "Woonkamer" staat met `opacity .6` in grijs. In donker is die tekst nauwelijks leesbaar.
- Zigbee "Nog niet gemeten" heeft een grijze stip. Dat is correct: onbekend is niet groen.

**Toegankelijkheid**

| # | Bevinding | WCAG / eis | Ernst |
|---|---|---|---|
| 1 | Groene badge "gemeten" naast een verouderde waarde | eis "stale nooit als gezond" | Groot |
| 2 | Uitgeschakelde lichttegel "niet bereikbaar" met `opacity .6`: de statusinformatie wordt onleesbaar, vooral in donker | 1.4.3 (statustekst is informatie, ook al is de tegel uitgeschakeld) | Middel |
| 3 | Knopranden `--border-strong` 1,50:1 (licht) en 1,80:1 (donker), ook bij de ronde −/+ knoppen | 1.4.11 (grensgeval: het symbool zelf heeft wel contrast) | Klein |
| 4 | Geen axe-controle in e2e of unit-tests | testdekking | Middel |
| 5 | Geen themakeuze in de app (alleen systeem) | platformeis licht/donker, gebruikerskeuze | Middel |

Wat goed is:
- overal ≥ 44 px (knoppen, nav, tabs, velden 44, `mode-btn` 48, bottom-link 56);
- focusring 3 px, skip-link en `prefers-reduced-motion`;
- invoerranden `--input-border` 4,21:1;
- statusstip met tekst, en "Overig" in de energiegrafiek gearceerd (niet alleen kleur);
- `ProgressBar` met waardetekst, `CopyButton` met live-melding.

**Wat moet veranderen**
- Tokens naar het platform. De domeintokens heat/cool/boiler/light-on blijven als domeinuitbreiding, maar dan afgeleid van de platformramps.
- Space Grotesk en de radius van 18 px volgen de platformkeuze. `--primary` wordt de platform-primary in plaats van zwart.
- lucide vervangt de 18 eigen iconen.
- Themakeuze toevoegen.
- Fout krijgt code + trace_id + kopieerknop.
- Skeleton- en leegpatroon van het platform.
- Kwaliteitsbadge en stale-markering samenvoegen.
- De manifestkleuren aanpassen.
- De routes, functies, offline-regel en snapshotgedrag blijven.

**Migratiepad**
1. Tailwind 4 toevoegen via `@tailwindcss/vite`. De ondersteuning voor Vite 5.4 moet nog gecontroleerd worden in de peer-afhankelijkheden van de gekozen versie.
2. Een aliaslaag `--bg: var(--background)` enzovoort. Let op de naamconflicten in §3.4: `--muted`, `--primary`, `--radius` en `--border` bestaan al met een **andere betekenis** dan in shadcn. Daarom eerst hernoemen (bijvoorbeeld `--mh-muted`) en pas daarna de shadcn-variabelen invoeren.
3. Preflight: `.steps-list` (`<ol>`, 8 `<ol>`-elementen in de code) verliest zijn nummering, en koppen en lijsten worden gereset. Die stijlen moeten expliciet worden gezet.
4. shadcn op **React 18**:
   - De componenten van de shadcn Tailwind-v4-registry gebruiken geen `forwardRef` meer. In React 18 komt `ref` dan niet bij een functiecomponent aan.
   - Daardoor kunnen Radix `asChild`-triggers (Popover/Dialog/Tooltip met `<Button>`) hun anker niet meten.
   - Kies dus een van twee: forwardRef-varianten van de componenten, of een aparte, geteste upgrade naar React 19. Dat laatste is een functionele afhankelijkheidswijziging en geen uiterlijk; zie §6.
5. `Icons.tsx` vervangen door lucide (nieuwe afhankelijkheid).
6. Themakeuze toevoegen (`data-theme` + `localStorage`), naast `prefers-color-scheme`.

**Impact op tests**
- Unit (vitest):
  - `toHaveClass('note','warn')`;
  - `.note.error, .error-text`;
  - `incomplete`, `is-complete/is-incomplete/is-future`, `.en-flag`, `.en-seg-rest`, `.bar`, `.en-col`.
- E2E:
  - `.state-line` met klasse `ok`;
  - `.lt-conflict`, `.c-dial`, `.big-num`;
  - `.shell` met klasse `is-offline`.
- Deze klassen behouden als semantische haken, of de tests omzetten naar rollen en testids.
- Geen snapshots en geen doc-afdrukken. Er is wel een aanbeveling: afdrukken toevoegen, zoals bij de andere apps.

### (d) Hub (`ai-server-manager/apps/web`, P0)

**Stack**
- Next 16.4.5, React 19.3.1, TypeScript 5.9.3, Node 22.
- Eigen webserver (`server/hub-server.mjs`) en een eigen service worker die alleen de schil bewaart.
- **Geen CSS-framework, geen iconenbibliotheek, systeemfonts.** Dat is een expliciet besluit in ADR-0009 punt 1.
- CSP: `style-src 'self' 'unsafe-inline'`, `font-src 'self'`. Dat is geschikt voor Tailwind, shadcn en een zelf gehost font.
- 47 tsx-bestanden.

**Tokens en kleur** (`src/app/globals.css`)
- Licht:
  - bg `#f5f6f8`, surface `#fff`, surface-2 `#eef1f5`;
  - tekst `#141820`, `--muted #475162` (tekst!), `--border #d3d9e2`;
  - primary `#1d4ed8`, danger `#b91c1c`.
- Tone-paren (bg/fg): ok, info, warn, bad, unknown, neutral.
- Donker: primary `#8db4ff`, tonen als donkere tint met lichte tekst. De donkere set staat **twee keer** in de CSS (media query en `[data-theme=dark]`).

**Typografie**
- `system-ui, -apple-system, "Segoe UI", Roboto, …` en `ui-monospace`. Het uiterlijk verschilt dus per besturingssysteem.
- rem-schaal: h1 1,6, h2 1,25, h3 1,05, stat 1,6 rem/700.

**Spacing en radius:** kaart 12 px en padding 16, knop 10, gap 8/12/16. Dit is de soberste set.

**Iconen:** `src/components/Icon.tsx` met 15 eigen paden (home, apps, alert, ai, server, media, house, …), 22 px, stroke 1.8.

**Componenten** (15)
- `AppShell` (zijbalk ≥ 1024, onderbalk, gebruikersbalk, offline-banner, sessie-guard).
- `StatusBadge`: tekstsymbool ✓ i ! ✕ ? – plus label, `data-tone`.
- `StatCard`: titel, badge, waarde + eenheid, `Freshness`, één vervolglink.
- `Freshness`: `<dl>` met "Laatst bijgewerkt" (absoluut + relatief, `<time>`) en "Bron", of "nog nooit gemeten / onbekend".
- `ErrorPanel` en `KindSection` (status, versheid, reden/advies).
- `NotYetAvailable` (fase + bron, geen nepdata).
- `Loading`, `PageHeader`, `TableWrap` (scrollregio met naam en tabindex).
- `SchemaForm`, `Field` en `ValueView`: formulier uit JSON-schema met lege beginwaarden en NL-veldfouten.
- `RefreshInventory`.

**Patronen**
- `worstTone()`: de totaalstatus is nooit beter dan het slechtste onderdeel, en onbekend weegt zwaarder dan ok.
- "Draait" telt als info en niet als groen.
- Bij een fout verdwijnt oude data.
- Schermen uit latere fasen zeggen eerlijk "Nog niet beschikbaar (volgt in fase Px)".

**Licht/donker:** keuze systeem/licht/donker in Instellingen (`hub-thema`). Bij "systeem" wordt **geen attribuut** gezet; de media query doet dan het werk.

**Navigatie:** precies volgens 08_UI.
- Onder 1024 px: ondernavigatie Home, Apps, Problemen, AI, Meer.
- Vanaf 1024 px: zijbalk met 9 items. Apps hangt onder Server, onboarding onder Instellingen.

**Schermafdrukken:** `docs/screenshots/p0/` bevat 29 JPEG's (desktop-1440, mobiel-390, opzet, afsluiting). Bekeken: `desktop-1440/home.jpg`, `home-donker.jpg` en `besluit-D03.jpg`, plus `mobiel-390/home.jpg`.
- Sober en duidelijk.
- Elke kaart heeft bron + laatst bijgewerkt. Onbekend staat als grijze "? Onbekend".
- De hiërarchie is vlak: alle kaarten wegen even zwaar en de metatekst is groot.
- Links zijn onderstreept. Er zijn bijna geen iconen.

**Toegankelijkheid**

| # | Bevinding | WCAG | Ernst |
|---|---|---|---|
| 1 | Invoerranden `--border #d3d9e2` op wit = **1,42:1**, donker `#2f3946` op `#161b22` = **1,48:1**. Ook checkbox-, radio- en fieldset-randen | 1.4.11 (3:1) | Kritiek: alle wizardformulieren |
| 2 | Status alleen met tekstsymbolen (✓ ! ✕ ?); die zijn klein en vallen in het systeemfont per platform anders uit | consistentie | Klein |
| 3 | Laden is alleen tekst; geen skeleton, waardoor de layout verspringt | bruikbaarheid | Klein |
| 4 | trace-id niet kopieerbaar met een knop (alleen selecteren) | platformeis | Middel |

Wat goed is:
- axe WCAG 2.2 op alle viewports;
- 44 px-doelen, geen horizontaal scrollen en een skiplink-test;
- `TableWrap` als focusbare regio, focusring 3 px;
- het rollenmodel kent `kind` (kinderprofiel).

**Wat moet veranderen**
- De Hub is de **referentie-implementatie** van de ontwerptaal. Hij krijgt eerst Tailwind 4, shadcn en lucide.
- Tokens naar het platform.
- `StatusBadge` gaat naar lucide-iconen. Het `unknown`-concept blijft.
- `Freshness`, `worstTone` en `NotYetAvailable` blijven **als platformpatroon** bestaan.
- `ErrorPanel` krijgt een kopieerknop.
- Inputranden ≥ 3:1.
- Zelf gehost platformfont.
- Skeleton- en lege toestanden.
- Navigatie en schermen blijven.

**Migratiepad**
1. Afhankelijkheden toevoegen: `tailwindcss`, `@tailwindcss/postcss`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, Radix-pakketten.
2. ADR-0009 punt 1 vervangen door een nieuwe ADR.
3. `globals.css` gaat over naar platformtokens. Let op: `--muted` is hier een tekstkleur, maar in shadcn een achtergrond. Ook `--border` en `--radius` botsen.
4. Themascript: altijd het opgeloste `data-theme` zetten en naar `matchMedia` luisteren. Een Tailwind-dark-variant op het attribuut werkt anders niet in de stand "systeem".
5. Preflight: `ol.howto` verliest zijn nummering.

**Impact op tests**
- Unit: `components.test.tsx` controleert `aria-hidden="true">?</span>` en `data-tone="unknown"`. Na de omzetting naar lucide moet die test mee.
- E2E: vrijwel alleen `data-testid` (`kaart-*`, `waarde-*`, `freshness`, `error-panel`, `loading`, `not-yet-available`) en rollen. Ook de controles op aanraakdoelen en axe moeten blijven slagen.
- Geen snapshots. Wel 29 afdrukken in `docs/screenshots/p0` opnieuw maken.

---

## 3. Dwarsdoorsnede

### 3.1 Statusvocabulaire → platform `healthy | degraded | down | unknown`

| Platform | MediaGuard | MSO | my_house | Hub | Opmerking |
|---|---|---|---|---|---|
| `healthy` | `success` "Gezond" + CircleCheck | `success` "Gezond" | `ok` "In orde" | `ok` "Gezond"/"Actueel"/"Getest" | |
| `degraded` | `warning` "Verminderd" | `warning` "Verstoord" | `warn` "Let op" | `warn` | **drie verschillende NL-woorden** |
| `down` | `danger` "Offline" | `danger` "Offline" | `error` "Probleem" | `bad` "Niet gezond"/"Gecrasht" | |
| `unknown` | `neutral` + **Pause-icoon** / zijbalk "Laden…" | `neutral` + CircleHelp "Onbekend" | `unknown` grijze stip "Onbekend" | `unknown` "?" "Onbekend"/"Verouderd (onbekend)" | eigen toon nodig in MG/MSO |
| (bezig) | `accent` + draaiend icoon | idem | — | `info` "Bezig" | geen gezondheidsstatus |
| (info/advies) | `info` | `info` "Advies" | `info` | `info` | |
| (niet ingesteld / uit) | `neutral` | `neutral` "Niet ingesteld" / "Uitgeschakeld" | `not_configured` | `neutral` "N.v.t." | dicht bij `capability_unavailable` |

Advies voor de ADR:
- Vier gezondheidstonen met elk een eigen icoon **en** woord.
- Daarnaast drie niet-gezondheidstonen: bezig, info en neutraal/niet-ingesteld.
- Stale is een **toestand bovenop** de status: de status verandert dan in `unknown` met de reden "verouderd". Zo doet de Hub het al.
- Het woord voor degraded kiest de `design:ux-copy`-ronde.

### 3.2 Contrastmetingen (eigen berekening, WCAG 2.x)

| App/thema | Paar | Ratio | Eis | Oordeel |
|---|---|---|---|---|
| Hub licht | invoerrand `#d3d9e2` op `#fff` | 1,42 | 3,0 | ❌ |
| Hub donker | invoerrand `#2f3946` op `#161b22` | 1,48 | 3,0 | ❌ |
| Hub licht/donker | tekst, muted, alle tone-paren | 7,1–16,4 | 4,5 | ✅ |
| MG/MSO donker | wit op danger `#E36B71` | 3,18 | 4,5 | ❌ |
| MG/MSO donker | text-3 op raised (slechtste) | 4,78 | 4,5 | ✅ krap |
| MG/MSO donker | danger op danger-tint | 4,65 | 4,5 | ✅ krap |
| MG/MSO donker/licht | border-strong (velden) | 3,10 / 3,33 | 3,0 | ✅ krap |
| my_house licht | `--stale` op wit (alleen grote cijfers) | 3,53 | 3,0 (groot) | ✅ |
| my_house licht | ok op ok-bg (badge "gemeten") | 4,65 | 4,5 | ✅ krap |
| my_house licht | heat op heat-bg ("Verwarmen") | 4,62 | 4,5 | ✅ krap |
| my_house licht/donker | knoprand `--border-strong` | 1,50 / 1,80 | 3,0 | ⚠️ grensgeval 1.4.11 |
| my_house licht/donker | invoerrand `--input-border` | 4,21 / 4,55 | 3,0 | ✅ |

### 3.3 Grafieken (dataviz-validator; nog geen paletkeuze)

| Palet | Resultaat |
|---|---|
| MG/MSO `--mg-viz-1…6` donker (op `#141C29`) | **FAIL** lichtheidsband (L 0,67–0,78, band ≈ 0,48–0,67); CVD **WARN** amber↔groen ΔE 7,2 (protan); contrast ✅ |
| MG/MSO `--mg-viz-1…6` licht (op `#fff`) | **FAIL** chroma (cyaan `#0E7F8C` C 0,091 < 0,1); CVD **WARN** amber↔groen ΔE 7,6; contrast ✅ |
| my_house energie licht (airco, boiler, overig apparaat, rest) | **FAIL** `--text-2 #4A4740` (bijna-zwart als reeks, L 0,40, C 0,01); grijs "Overig" onder de chroma-ondergrens (bewust neutraal, wel gearceerd en gelabeld) |
| my_house energie donker | **FAIL** lichtheid (L 0,72–0,87) en chroma (blauw C 0,099) |

Anti-patronen die in de code voorkomen:
- **Statuskleur als reekskleur.** viz-2 = success, viz-3 = warning en viz-5 = danger. In `DistributionBar` krijgt "onzeker" rood (viz-5).
- **Domeinkleur gelijk aan statuskleur.** Boiler-oranje ligt dicht bij heat en warning.
- **Tooltips alleen via de pointer**, zonder toetsenbord en zonder tabelweergave.

Wat al goed is: lijnen van 1,75–2 px, gaps van 2 px in stapelbalken, arcering en een legenda met absolute aantallen.

Eis voor de ontwerptaal:
- een eigen categorisch palet, apart van de statuskleuren, per thema gevalideerd;
- een "Overig"-slot (neutraal + textuur);
- een tabelweergave en tooltips die ook met het toetsenbord werken.

### 3.4 Naamconflicten met shadcn-variabelen (migratierisico)

| Variabele | Bestaande betekenis | shadcn-betekenis | Gevolg bij naïeve import |
|---|---|---|---|
| `--muted` | my_house en Hub: **tekstkleur** voor bijzaken | achtergrond (`bg-muted`); tekst is `--muted-foreground` | secundaire tekst wordt lichtgrijs vlak of onleesbaar |
| `--accent` | MG/MSO (`--mg-accent`): merkblauw / primaire actie | hover-/selectie-achtergrond | alleen een conflict als `--mg-` wegvalt; let op bij het hernoemen |
| `--primary` | my_house: bijna-zwart `#1C1B19`; Hub: blauw | merk-/primaire kleur | my_house-knoppen veranderen van kleur |
| `--border` | my_house en Hub: decoratieve rand | `--border` (rand) + `--input` (veldrand) | Hub-velden blijven 1,42:1 zolang `--input` niet apart wordt gezet |
| `--radius` | my_house 18 px, Hub 12 px | basisradius waar `--radius-sm/md/lg` van worden afgeleid | alle shadcn-radii schalen mee |
| `--surface`, `--surface-2`, `--text` | my_house en Hub | bestaan niet in shadcn | geen conflict; wel opruimen |
| dark-selector | MG/MSO/Hub `[data-theme=dark]`; my_house media query | `.dark`-klasse | eigen `@custom-variant dark` nodig |

### 3.5 Volledigheid t.o.v. platformeisen (audit)

| Eis | MG | MSO | my_house | Hub |
|---|---|---|---|---|
| Status = icoon + tekst, nooit alleen kleur | ✅ | ✅ | ✅ (stip + woord) | ✅ (symbool + woord) |
| Eigen `unknown`, nooit groen | ⚠️ neutral + Pause | ⚠️ neutral + CircleHelp | ✅ | ✅ |
| Stale nooit als gezond | ⚠️ stale-markering; groen kan blijven | ⚠️ idem | ⚠️ groene "gemeten" bij stale | ✅ |
| Kaart: waarde + eenheid + bron + laatst bijgewerkt | ❌ | ⚠️ | ⚠️ (geen bron) | ✅ |
| Fout: code + NL + kopieerbare trace_id | ⚠️ (correlation-id, niet kopieerbaar) | ⚠️ (+ code) | ❌ | ⚠️ (niet kopieerbaar) |
| `capability_unavailable` eerlijk | ✅ | ✅ | ⚠️ | ✅ |
| Laden / leeg | ✅ skeleton / ✅ | ✅ / ✅ | ⚠️ tekst / ⚠️ tekst | ⚠️ tekst / ⚠️ |
| Offline / reconnect | ✅ | ✅ | ✅✅ (gedimd, acties uit) | ✅ |
| Preview / diff / backup / readback vóór acties | ✅ (DangerDialog, DiffViewer) | ✅ (change-preview, RiskChip) | ⚠️ | ❌ (P2) |
| R0–R3-weergave | ❌ (eigen) | ❌ (3 eigen niveaus) | ❌ | ❌ |
| Aanraakdoelen ≥ 44 px | ✅ (≤ 860) | ❌ | ✅ | ✅ |
| Licht/donker met keuze | ✅ (standaard donker) | ✅ (standaard donker) | ⚠️ alleen systeem | ✅ |
| Toetsenbord / skip-link / focus | ✅ | ✅ | ✅ | ✅ |
| Rol `kind` | n.v.t. (eigen rollen) | n.v.t. | n.v.t. (admin/viewer) | ✅ in rollenmodel; nog geen eigen UI-variant |
| Automatische a11y-test | ⚠️ (deels) | ✅ | ❌ | ✅ |

---

## 4. Aanbevolen migratiestrategie (input voor de ADR)

**Fase 0: platformlaag (in ai-server-manager)**
- Eén tokenbestand met Tailwind-4 `@theme` en de shadcn-variabelen (licht en donker), plus platformuitbreidingen:
  - status: healthy/degraded/down/unknown en bezig/info/neutraal;
  - risico R0–R3;
  - categorische grafiekreeksen, gevalideerd;
  - domeinramps (warm/koud/licht aan) voor my_house.
- Een dark-variant op `data-theme`, één breekpunt voor de navigatie, en het font zelf gehost.
- Bron van waarheid is `ai-server-manager`, zoals bij `PLATFORM_CONTRACTEN.md`.
- Verspreiding als **geversioneerde kopie met herkomstkop en checksum**, net als MSO's PROVENANCE-werkwijze. Een CI-check slaat alarm bij drift.
- Geen npm-registry: de builds moeten offline en zonder geheimen blijven werken.

**Fase 1: aliaslaag per app**
- Oude tokennamen wijzen naar platformtokens. Waar nodig eerst hernoemen (§3.4).
- Effect: een groot visueel resultaat met weinig codewijziging, en de tests blijven groen.

**Fase 2: componenten**
- De primitieven worden shadcn-componenten met platformvarianten.
- Behouden: component-API, testids, rollen en een kleine lijst hook-klassen.
- De Hub eerst, dan MG, dan MSO (dezelfde code), dan my_house (Vite/React 18).

**Fase 3: opruimen**
- Inline styles naar utilities.
- `mg.css`, `styles.css` en `globals.css` uitfaseren.
- Dode code weg: `components/ui`-stubs in MG, `recharts` in MSO (of juist inzetten), dubbele dark-set in de Hub.

**Per fase opnieuw maken**
- Alle doc-schermafdrukken: MG 56, MSO 64, Hub 29, en nieuw voor my_house.
- axe-runs licht/donker op 360/390/768/1440.

**Wat behouden blijft (sterk, gaat de ontwerptaal in)**
- MediaGuard:
  - `StateView`-set (zeven toestanden);
  - "Technische details" uitklapbaar;
  - `DangerDialog` (impact, snapshot, oud→nieuw, rollback, getypte bevestiging), `DiffViewer`, `Stepper`, `Timeline`;
  - "Wacht op jou" met één actie per regel; maximaal één tabrij.
- MSO: `UnavailableState` met een directe link naar de verbinding.
- my_house:
  - meetkwaliteitsbadges;
  - offline-dimmen en acties uit;
  - geblokkeerde modus gestippeld met reden;
  - gearceerd "Overig".
- Hub:
  - `Freshness` (bron + laatst bijgewerkt, "nog nooit gemeten");
  - `worstTone`;
  - `NotYetAvailable`;
  - `TableWrap`;
  - schemaformulieren zonder standaardwaarden.

---

## 5. Belangrijkste te kiezen punten (beslist de ontwerp-agent in de ADR)

1. **Basispalet en uitstraling.** Het koele MG-blauw, de warme my_house-toon en de sobere Hub-toon gaan naar één basis. Domeinaccenten (my_house warm/koud) zijn alleen toegestaan als uitbreiding.
2. **Font.** Inter, al in gebruik bij drie apps, of een systeemstack. Plus mono voor id's en trace_id.
3. **Standaardthema.** MG/MSO staan nu op donker, de Hub en my_house op systeem. Voorstel: systeem, met een keuze per gebruiker.
4. **Navigatiebreekpunt.** MG/MSO 860, my_house 820, Hub 1024. Tailwind `lg` = 1024 sluit aan op de Hub.
5. **Radius-schaal en dichtheid.** MG/MSO zijn compact (knop 34 px op desktop), Hub en my_house ruim (44 px overal).
6. **Grafiekbasis.** Eigen SVG zoals nu, of recharts, of shadcn charts op recharts. Het palet volgt de dataviz-methode; zie §3.3.
7. **Woorden voor status en risico.** Daarvoor een `design:ux-copy`-ronde.

## 6. Open punten (buiten de bevoegdheid van de ontwerp-agent of om te verifiëren)

- **Native apps.** `media-guard-ultimate/apps/android` heeft 32 eigen ontwerpafdrukken en `my_house/apps/android` bestaat. Beide vallen niet in de reikwijdte ("alleen web-UI's genoemd"). Na de migratie wijken ze visueel af van het web. Vraag: blijft dat zo?
- **my_house React 18.** shadcn (Tailwind-v4-registry) werkt het makkelijkst met React 19. De keuze is forwardRef-varianten (puur uiterlijk) of een upgrade naar React 19, die functioneel risico geeft. "Alleen uiterlijk" wijst op het eerste.
- **MediaGuard en-US.** MediaGuard heeft een Engelse vertaling; het platform is NL. Die functie blijft volgens de reikwijdte, maar elke nieuwe ontwerptaaltekst heeft dan ook een EN-sleutel nodig.
- **Te verifiëren:**
  - groen "Alles in orde" in de MG-zijbalk bij bronnen die niet laden (§2a #7);
  - de Vite 5-ondersteuning van `@tailwindcss/vite` in de gekozen versie.

---

## 7. Bestanden van dit onderzoek

| Bestand | Inhoud |
|---|---|
| `<werkmap ontwerp>/onderzoek/BESTAANDE_UI.md` | dit rapport |
| `<werkmap ontwerp>/onderzoek/scripts/contrast.mjs` | contrastberekening van de tokenparen |
| `<werkmap ontwerp>/onderzoek/scripts/myhouse-render.mjs` | render van de bestaande my_house-dist met fictieve fixtures, zonder server en zonder build |
| `<werkmap ontwerp>/onderzoek/schermafdrukken/myhouse-{inloggen,overzicht}-{licht,donker}-{390,1440}.png` | 8 afdrukken van my_house |

Bestaande afdrukken die zijn bekeken:
- `media-guard-ultimate/docs/design/after/{overzicht-1440-dark,overzicht-390-light,ruimte-1440-light}.png`
- `media-source-optimizer/docs/screenshots/{overzicht-light-1440,overzicht-dark-390,kosten-dark-1440}.png`
- `ai-server-manager/docs/screenshots/p0/{desktop-1440/home,desktop-1440/home-donker,desktop-1440/besluit-D03,mobiel-390/home}.jpg`
