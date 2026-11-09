# Hub-UI in Peil — ontwerpstap P0 + P1 + contract 1.2

**Status:** ontwerpstap (vooraf aan de webbouw, contract §13) · 9 november 2026 · door de ontwerp-agent
**Repo:** `ai-server-manager` · **Doel:** `apps/web` (Next.js 16.4.5 / React 19.3.1-PWA)
**Bindend:** `docs/platform-v2/ONTWERPTAAL.md` (Peil 1.1.0), `design/ontwerptaal/COMPONENTEN.md` (nu met §27),
`docs/adr/ADR-0015-ontwerptaal-peil.md` (met de besluiten van de gebruiker), `design/ontwerptaal/onderzoek/EISEN_EN_SCHERMEN.md`
(scherm-ID's S-xxx, toestanden T-xx, componenten C-xx), `docs/platform-v2/PLATFORM_CONTRACTEN.md` 1.2 en
`CONTRACT_1.2_CONFORMITEIT.md` (H5, H6, H12), `docs/openapi/hub-api.openapi.json` (stand na P1 deel 1 en 2).
**Gebruikte skills:** `design:design-system` (uitbreiding, §5), `dataviz` (vóór de grafiekkeuzes, validator opnieuw
gedraaid, §6), `design:ux-copy` (microcopy in §4), `design:accessibility-review` en `design:design-critique` (op de
nieuwe prototypes en hun schermafdrukken, §9), `design:design-handoff` (opbouw van dit document).

> **Eerlijkheid.** Dit is een ontwerp, geen gebouwde UI. De prototypes zijn statische HTML met **fictieve data**
> (gemarkeerd met "Voorbeeld"). Ze zijn automatisch gecontroleerd (axe, contrast in de DOM, overloop, doelen, focus;
> §9). **NIET GEVALIDEERD:** echte schermlezer (NVDA/TalkBack), echte Android-telefoon in fel licht, echte NAS,
> Authentik, Uptime Kuma, Beszel en Gotify. Niets in dit document claimt dat een scherm werkt.

---

## 0. Leeswijzer en wat deze stap oplevert

| Onderdeel | Plaats |
|---|---|
| Dit document: migratie P0 → Peil, de nieuwe schermen per scherm-ID, tests en besluiten | `docs/ontwerp/HUB_PEIL_ONTWERP.md` |
| Zeven nieuwe prototypes (licht/donker, 360/390/768/1440 als afdruk; gecontroleerd op 320–1440) | `design/ontwerptaal/prototypes/{apps,appdetail-p1,server-metrieken,diensten,noodaccount,instellingen-toegang,instellingen-bronnen}.html` |
| Bouwscripts van die prototypes | `design/ontwerptaal/bouw/pagina-{apps,server,diensten,noodaccount,instellingen}.mjs` |
| Productnaam in de schil van **alle** prototypes (ook de kindschil) | `design/ontwerptaal/bouw/ui.mjs` |
| Nieuwe klasserecepten (geen nieuwe tokens; Peil blijft 1.1.0) | `design/ontwerptaal/bouw/componenten.css` (blok "Hub P1-ontwerpstap") |
| Nieuwe/uitgebreide componenten C-03a, C-12a, C-40a, C-41a, C-57…C-62 | `design/ontwerptaal/COMPONENTEN.md` §27 |
| Tien extra lucide-iconen (zelfde paden als lucide-react 1.66) | `design/ontwerptaal/bouw/iconen.mjs` → `iconen.json` |
| Controle-uitkomst van alle 18 prototypes | `design/ontwerptaal/controle/samenvatting.txt`, `controle/uit/*.json` |
| 144 schermafdrukken (18 × 4 breedtes × 2 thema's), met pngquant verkleind | `design/ontwerptaal/shots/` |

Opnieuw bouwen en controleren: `cd design/ontwerptaal/bouw && npm ci && cd .. && DATAVIZ_VALIDATOR=<pad naar
validate_palette.js> node bouw/alles.mjs --shots --controle`. `shot.mjs` gebruikt `pngquant` als dat op het systeem
staat (kleuren worden nooit op afdrukken gemeten, alleen in de DOM).

---

## 1. Uitgangspunten

1. **Peil is de enige ontwerptaal.** Tokens, vijf assen met vijf vormen, vaste woorden (ONTWERPTAAL §11) en de
   componentspecificaties zijn bindend. Afwijkingen staan als besluit in §8, nergens anders.
2. **Status eerst, eerlijk boven geruststellend.** Groen alleen voor *gemeten en goed* (een verse gezondheidsmeting).
   Een geslaagde eenmalige test, "gekoppeld", "aan" of "draait" is **neutraal**. Verouderd is nooit gezond;
   onbekend is nooit 0.
3. **Wat in P1 nog niet kan, staat er eerlijk** (T-08a "Nog niet beschikbaar — volgt in fase P2"), zichtbaar waar de
   gebruiker het zoekt, met de reden. Geen schijnknoppen die iets lijken te doen.
4. **Server bepaalt rechten.** De UI verbergt mutaties voor rollen zonder recht (T-16, één RolMelding per pagina),
   maar de API is de poortwachter (`Viewer`/`Operator`/`Admin`; rol `kind` haalt bij elke beheerroute 403).
5. **Bestaande `data-testid`'s blijven.** Nieuwe elementen krijgen kebab-case NL-testids (lijst per scherm in §4).
6. **Productnaam "TrueNAS Home Platform"** en **rol kind = Home · Kijken · Zoeken · Ik** (besluiten van de gebruiker,
   `design/ontwerptaal/BESLUITEN_GEBRUIKER.md`), uitgewerkt in §3.

---

## 2. Migratie van de P0-UI naar Peil

### 2.1 Vertrekpunt (gemeten in `apps/web`, stand `e30bae6`)

- Eigen CSS in `src/app/globals.css` (907 regels, ±50 klassen: `.btn*`, `.card`, `.badge`, `.tone-*`, `.notice`,
  `.stat*`, `.kv`, `.meta`, `.table-wrap`, `.choice`, `.steps`, `.howto`, …), drie eigen kleurblokken
  (`:root`, `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])`, `:root[data-theme="dark"]`) en 9×
  `var(--muted)` als tekstkleur.
- Eigen iconen (`src/components/Icon.tsx`, 15 paden), tekstsymbolen in `StatusBadge` (`✓ i ! ✕ ? –`).
- Thema: `THEME_SCRIPT` zet `data-theme` **alleen** bij Licht/Donker; bij Systeem geen attribuut (dan volgt de CSS
  `prefers-color-scheme`). Peil kent bewust geen `prefers-color-scheme`-terugval → dit moet anders (fase 1, stap 1).
- Toon-model `Tone = ok | info | warn | bad | unknown | neutral` in `src/lib/status.ts`; `worstTone` ordent
  `bad > unknown > warn > info > neutral > ok`.
- ADR-0009 punt 3: bij een fout wordt oude data gewist. Peil O-03 vraagt het omgekeerde (laatst bekend, gedempt, status
  Onbekend). De backend levert dat nu al voor observability (`status: unknown`, `reden: verouderd`, `laatst_bekend`).

### 2.2 Fase 1 — aliaslaag (alleen uiterlijk; geen component- of tekstwijziging)

Volgorde (ONTWERPTAAL §13.1, gecontroleerd tegen de huidige code):

1. **Themascript** (`src/lib/theme.ts`): zet **altijd** het opgeloste thema — `data-theme="light|dark"` én de klasse
   `dark` — ook bij Systeem (luister naar `matchMedia('(prefers-color-scheme: dark)')` en wissel live).
   `applyTheme("systeem")` mag `data-theme` dus niet meer verwijderen. Sleutel `hub-thema` en de knoppen
   `thema-systeem|licht|donker` blijven.
2. **Kopie van de tokens:** `src/app/peil/ontwerptaal.css` en `src/app/peil/hub-p0.css` als versie-gepinde kopie
   met herkomstkop (`Peil 1.1.0 · sha256:…`, O-14) + een unit-test die de checksum vergelijkt met
   `design/ontwerptaal/`.
3. **Codemod:** elke `var(--muted)` in `globals.css` → `var(--muted-foreground)` (9×).
4. **Kleurblokken weg:** de drie eigen kleurblokken volledig verwijderen (anders wint het media-blok met specificiteit
   0,2,0 en ontstaat een half donker thema).
5. **Imports** bovenaan `globals.css`: `@import "tailwindcss"; @import "./peil/ontwerptaal.css";
   @import "./peil/hub-p0.css";` (Tailwind 4 vanaf hier al aanwezig, utilities nog ongebruikt).
6. **Preflight:** `ol.howto` krijgt `data-genummerd` (Tailwind-preflight haalt lijstnummers weg).
7. **Viewport `themeColor`** in `layout.tsx` naar `--background` licht/donker (`#EEF1F5` / `#0A0D12`).

Wat de gebruiker ziet: Peil-kleuren, systeemfont, veldranden ≥ 3:1, tweekleurige focusring. Wat **niet** verandert:
componenten, teksten, testids, routes. Tests: alles moet groen blijven zonder aanpassing; axe 0 in licht én donker.

### 2.3 Fase 2 — Tailwind 4 + shadcn/ui (new-york) + lucide-react

**Afhankelijkheden** (exact gepind zoals de rest van `package.json`; geen `^`): `tailwindcss`, `@tailwindcss/postcss`,
`class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, Radix-pakketten via `npx shadcn add`
(`components.json` uit `design/ontwerptaal/`, `css: "src/app/globals.css"`; `init` één keer en het gegenereerde
variabelenblok vervangen door de Peil-import). `recharts` alleen via shadcn `Chart` (O-13). Codemod na elke
`shadcn add`: COMPONENTEN.md §1 (44 px, geen `text-xs`, Peil-focus, `destructive-foreground`, geen opacity-vlakken,
`z-overlay`/`z-nav`).

**Componenten P0 → Peil** (de semantiek van P0 blijft; alleen vorm en woorden volgens Peil):

| P0-component | Peil-doel | Wat verandert |
|---|---|---|
| `AppShell` (Brand, Navigation, UserBox, OfflineBanner, Guard) | **AppSchil C-01** + VerbindingsBanner C-16 + gebruikersmenu (DropdownMenu) + Meer-sheet (Sheet) + kindschil | merk "TrueNAS Home Platform" (§3); Uitloggen uit de kop naar het gebruikersmenu (K4) en Instellingen → Account; kopbalk ≥ 1280: Zoeken (P1: alleen schermen), Live, Problemen-teller, AI (P2: NogNietBeschikbaar); `/meer` wordt een Sheet maar de route `/meer` blijft bestaan (test) |
| `PageHeader` | **PageHeader + Kruimelpad C-02** | meta-regel "Bijgewerkt 11:56 (zojuist) · vernieuwt elke 60 s"; Vernieuwen = secundaire knop met icoon én label; focus naar h1 bij routewissel, `document.title` = "<pagina> — TrueNAS Home Platform" |
| `StatusBadge` (`Tone`) | **StatusBadge C-03/C-03a** (`status`), **BesluitStatusBadge C-10**, **GateBlokkade C-11**, **TestResultaat C-58** | tekstsymbolen → lucide (vaste koppeling §7); per gebruik de juiste as kiezen (tabel 2.4) |
| `Freshness` | **Versheid C-06** + Meetkwaliteit C-07 | `dl` Bron / Bijgewerkt / Geprobeerd; verouderd = gearceerd waardevak "Laatst bekend · 10:12" + status Onbekend; "nog nooit gemeten" blijft |
| `StatCard` | **StatKaart C-05** | waarde + eenheid + meetkwaliteit + status + versheid + **één** vervolglink; toestanden vers/verouderd/nooit/onbekend/niet beschikbaar/fout/laden |
| `ErrorPanel` | **Foutpaneel C-14** + **KopieerVeld C-15** | wat · waarom · wat je kunt doen; Code; Trace-ID kopieerbaar met terugval zonder secure context (Hub draait via http tot D17); "Opnieuw proberen"; `details` Technische details; `data-testid="error-panel"` en `data-code` blijven |
| `NotYetAvailable` | **NogNietBeschikbaar C-12** (pagina) / **C-12a** (inline) | `hourglass`, "Nog niet beschikbaar — volgt in fase Px (…)"; testid `not-yet-available` blijft |
| `KindSection` (inventarissoort) | StatKaart-sectie met **Versheid** en **Onbekend C-17** | `onbekend-<id>` blijft; verouderd toont laatst bekend (O-03) in plaats van leeg |
| `TableWrap` | **ResponsieveLijst C-34** | ≥ 1024 (≤ 4 kolommen vanaf 768) een echte tabel, kleiner een kaartenlijst; **geen** horizontaal scrollkader meer voor kerninformatie (K1) |
| `Loading` | **Laden C-18** | skelet alleen de eerste keer; verversen houdt de vorige weergave + "Bijwerken…"; testid `loading` blijft |
| `Field`, `SchemaForm` | **Veld + SchemaFormulier C-37**, **GeheimVeld C-39** | label boven veld, hulp via `aria-describedby`, bron-tag, veldfout `octagon-x`; ja/nee zonder standaard; foutsamenvatting `role=alert` + links |
| `RefreshInventory` | Knop "Inventaris vernieuwen" + `role=status`-regel | testids `inventaris-vernieuwen`, `vernieuwen-status` blijven |
| `ValueView` | `dl` met mono-waarden (paden met `<wbr>` na `/`) | — |
| `Icon` | `lucide-react` | vaste koppeling ONTWERPTAAL §7 + §27-aanvulling |

### 2.4 Statusvertaling P0 → Peil (`src/lib/status.ts`)

De huidige functies blijven bestaan als bron, maar geven een Peil-weergave terug. **Rood en groen alleen waar Peil het
toestaat.**

| P0-functie en waarde | Nu | Peil-weergave |
|---|---|---|
| `kindStatus` ok / verouderd | ✓ "Actueel" (groen) / ? | **geen badge** bij vers (de tijd zegt genoeg, K3); verouderd = StatusBadge `stale` "Verouderd · laatst bekend …" + status Onbekend |
| `decisionStatus` Open / Ingevuld / Getest / Geblokkeerd / N.v.t. | ! amber / i / ✓ groen / ✕ rood / – | **BesluitStatusBadge C-10** zonder statuskleur: Open `circle-dot` · Ingevuld `square-pen` · Getest `flask-conical` · Geblokkeerd `lock` (gate-stijl) · N.v.t. `minus` (regel 12: open is nooit rood of amber) |
| `gateStatus` toegestaan / geblokkeerd / onbekend | ✓ groen / ✕ rood / ? | Toegestaan = neutraal `lock-open`; geblokkeerd = **GateBlokkade C-11** (slot, neutraal-sterk, "Dit is geen storing; er wacht een voorwaarde."), alleen bij gemeten falen (pool DEGRADED, back-up mislukt) T-14a in `down`; onbekend = T-14b (`unknown`, "onbekend opent nooit") |
| `poolHealth` gezond / niet gezond | ✓ / ✕ "Niet gezond" | Gezond / **Storing** ("Niet gezond" staat op de lijst "niet meer"); zodra de API de poolstatus levert: DEGRADED = **Beperkt**, FAULTED/UNAVAIL = Storing |
| `appState` draait / gestopt / gecrasht / bezig | i "Draait (gezondheid onbekend)" | TrueNAS-staat als **neutrale** pil (`power` "Draait"/"Gestopt"); de gezondheid komt uit de catalogus (§4.3); gecrasht = Storing (gemeten falen) |
| `coverageStatus` gedekt/geverifieerd/niet_gedekt/ontbreekt/verouderd/binnen/overschreden | ✓/✓/✕/✕/!/✓/✕ | **DekkingsMatrix C-33**: cel = symbool + woord (Ja `check` · Nee `x` · Onbekend `circle-help` · N.v.t. `minus`), geen kleurvlakken; verouderd = `stale`; "Doel overschreden" = Beperkt (gemeten) |
| `testResult` geslaagd / mislukt / geen | ✓ groen / ✕ / ? | **TestResultaat C-58**: Geslaagd neutraal `check`; Mislukt `octagon-x`/down; "Geen hersteltest" = Onbekend |
| `measurementStatus` geslaagd / afwijking / voorstel / mislukt | ✓ / ! / i / ✕ | geslaagd neutraal; afwijking en mislukt = controle `fout` (gemeten verschil); voorstel = info ("Voorstel — kies zelf") |
| Home totaal "In orde (gemeten)" / "Aandacht nodig" / "Actie nodig" / "Deels onbekend" | | vaste woorden: **Alles gezond** (alleen alles vers én gezond) · **Beperkt** · **Storing** · **Deels onbekend** |
| `worstTone` volgorde `bad > unknown > warn` | | Peil: **Storing > Beperkt > (Deels) Onbekend > Gezond**; Gepauzeerd en Nog niet beschikbaar tellen niet mee maar staan in de telling. Dit is een gedragswijziging (OB-06) |

### 2.5 Fase 3 — opruimen

`globals.css` alleen nog imports + `@layer base` voor de Hub-eigen restjes; alle `.btn`, `.card`, `.tone-*`,
`.notice`, `.table-wrap`, `.choice` weg; `hub-p0.css` weg; `Icon.tsx` weg; `scripts/make-icons.mjs` maakt de
PWA-iconen met het nieuwe merk (`server`-glyph op `--foreground`, zoals de prototypes). Lintregels: geen `#hex`,
`rgb(`, `oklch(` buiten de tokenkopie; geen `text-xs`. ADR-0009 punt 3 ("oude data wissen") vervalt voor O-03.

### 2.6 Bestaande schermen → doelcomponenten

| Route (scherm-ID) | P0-inhoud | Peil-doel | Prototype / patroon |
|---|---|---|---|
| `/eerste-start` (S-001) | uitleg setupcode, codeveld, account | publieke schil (geen nav) met merk; codeveld = InputOTP-patroon in groepen (plakken van de hele code); Foutpaneel `invalid_setup_code`; wachtwoordsterkte als hulptekst | `wizardstap.html` (formulier) |
| `/inloggen` (S-002) | lokaal inloggen | + knop **Inloggen met SSO** (alleen als `GET /api/v1/auth/oidc/beschikbaar` ja zegt), meldingen per `sso_fout` (§4.8.6), link "Noodlogin (alleen vanaf je eigen netwerk)" | — (spec §4.2.4) |
| `/` Home (S-020) | systeemstatus + 8 kaarten | SysteemStatusPaneel + "Wat actie nodig heeft" + StatKaarten met **P1-bronnen** (§4.6) | `home.html`, `offline.html` |
| `/onboarding` (S-010) | voortgang, stappen, besluitenlijst, gates-tabel | Wizardoverzicht; besluiten met BesluitStatusBadge; **gates als kaartenlijst < 768** (K1) met GateBlokkade; stap Executor met KoppelcodeKaart (30 min) | `wizardstap.html`, `diensten.html` |
| `/onboarding/besluit/[Dxx]` (S-011) | uitleg, waarde, meten, formulier, bewijs, status | PageHeader + kruimelpad; SchemaFormulier C-37; "Meten" + TestResultaat; bewijs als lijst; waarschuwing vóór opslaan na Getest | `wizardstap.html` |
| `/onboarding/truenas` (S-012) | adres, key, test, vingerafdruk TLS, meten | stappen als Wizard C-36; GeheimVeld C-39; testuitkomst = TestResultaat (`data-reason` blijft); TLS-vingerafdruk in KopieerVeld + bevestigvakje (`keuze`) + knop "Vingerafdruk vertrouwen" (`aria-disabled` tot aangevinkt) | `noodaccount.html` (controles) |
| `/onboarding/executor` (S-013) | uitleg, "Koppelen volgt in P2" | stap 1 installeren (uitleg Custom App), stap 2 **KoppelcodeKaart (30 min)** + uitleg dat de schrijfsleutel alleen op de executorpagina komt (executor-statuspagina koppelt al met code + vingerafdruk, H7 deel P0/P1); de write-key-flow zelf blijft op de executorpagina | `diensten.html` |
| `/server` (S-030) | inventaris per soort | subnavigatie C-62 (Overzicht · Apps · Metrieken · Meetdekking · Logs); inventaris als StatKaart-secties met Versheid; tabellen → ResponsieveLijst; **label voor de soort `images`** ("Images") in `KIND_LABEL` | `server-metrieken.html` |
| `/apps` (S-040) | inventarislijst | **Appcatalogus** (`GET /api/v1/apps`), §4.3 | `apps.html` |
| `/backups` (S-120) | gate, bronnen, dekking per app/dataset, eigen back-up | GateBlokkade (geen rood bij "wacht op invulwerk"); DekkingsMatrix C-33; "Synchronisatie is geen herstelgarantie" blijft letterlijk (test); eigen back-up met TestResultaat | `home.html` (kaartpatroon) |
| `/instellingen` (S-160…S-171) | account, weergave, sessies, gebruikers, audit, over | **indexpagina + subpagina's** (§4.8); ThemaKeuze C-50 als ToggleGroup | `instellingen-toegang.html`, `instellingen-bronnen.html` |
| `/meer` | linklijst | Meer-sheet; de route blijft als pagina voor directe links en de test | — |
| `/problemen` (S-050/S-051) | NogNietBeschikbaar P1 | **echte inbox + detail** (§4.5) | `problemen.html` (+ P1-delta's) |
| `/ai`, `/media`, `/huis`, `/netwerk`, `/automatisering`, `/kosten` | NogNietBeschikbaar | blijven NogNietBeschikbaar (C-12) met fase en bron | — |

---

## 3. Schil, productnaam en de rol kind

### 3.1 Productnaam "TrueNAS Home Platform" (O-07)

- **Merk linksboven:** zijbalk (≥ 1024): glyph `server` (40 px, `bg-foreground text-background`, `rounded-lg`) +
  "TrueNAS Home Platform" (`text-lg font-bold leading-6`, loopt natuurlijk om naar twee regels binnen 256 px).
  Kop (< 1024): glyph 36 px + naam `text-base leading-5` in maximaal 8,5 rem (twee regels), de link blijft ≥ 44 px.
  Gecontroleerd op 320 px: geen overloop (`controle/samenvatting.txt`).
- **Titel per route:** `"<pagina> — TrueNAS Home Platform"`; publieke pagina's "Inloggen — TrueNAS Home Platform".
- **PWA-manifest:** `name` "TrueNAS Home Platform", `short_name` "Home Platform"; `layout.tsx` `applicationName` en
  `appleWebApp.title` idem.
- **"Hub" blijft de naam van de centrale app ín het product** (zijbalkvoet "Hub 0.2.0", "De Hub ziet deze sleutel
  nooit", "Vingerafdruk van de Hub"). Zo blijven de contractteksten en statuspagina's ("Onderdeel van TrueNAS Home
  Platform") kloppen.
- **Authenticator-label:** de backend zet nu `issuer = "AI Server Manager"` in de otpauth-URI van het noodaccount;
  dat hoort "TrueNAS Home Platform" te worden (followup backend; het prototype toont de doelwaarde).

### 3.2 Navigatie (ongewijzigd volgens 08_UI, met P1-invulling)

- Zijbalk exact 9 items; ondernavigatie Home · Apps · Problemen · AI · Meer; Apps onder Server (ADR-0009).
- **Kopbalk P1:** Zoeken (C-51: alleen schermen en apps in P1; de zoekindex volgt in P5), Live-indicator (neutraal),
  **Problemen** met inktteller uit `GET /api/v1/incidents/samenvatting` (aantal actieve incidenten; nooit rood),
  **AI** (NogNietBeschikbaar P2). **Goedkeuringen** verschijnt pas in P2 (er bestaan in P1 geen goedkeuringen; geen
  lege ingang). Tellers > 99 = "99+", exact getal in de sr-tekst.
- **Server-subnavigatie** (C-62): Overzicht `/server` · Apps `/apps` · Metrieken `/server/metrieken` · Meetdekking
  `/server/meetdekking` · Logs `/server/logs` (operator).
- **Instellingen** wordt een index met subpagina's (≥ 1024 een vaste subnavigatie links, 14 rem):
  Account `/instellingen/account` · Gebruikers en toegang `/instellingen/toegang` · Noodaccount
  `/instellingen/noodaccount` · Diensten `/instellingen/diensten` · Monitoring en meldingen
  `/instellingen/monitoring` · Apparaat en app `/instellingen/apparaat` · Auditspoor `/instellingen/audit` · Over
  deze Hub `/instellingen/over`. Bestaande ankers (`/instellingen#audit`, `#gebruikers`, `#sessies`) krijgen een
  doorverwijzing naar de subpagina (links op Home en in tests).

### 3.3 Rol kind: Home · Kijken · Zoeken · Ik (O-05)

- **Eigen schil** (C-01 kindvariant, `kind.html`): kop met merk + gebruikersmenu; ondernavigatie op **elke** breedte
  (ook desktop) Home `house` · Kijken `monitor-play` · Zoeken `search` · Ik `smile`; geen zijbalk, geen tellers, geen
  Live, geen beheertermen, geen codes in beeld.
- **Routes** (de Guard kiest op `me.user.role === "kind"`): `/` (Home kind, S-021), `/kijken` (S-087),
  `/zoeken` (S-140 kind), `/ik` (naam, thema, uitloggen, eigen sessies). Elke andere route toont in de kindschil
  "Dit scherm is niet voor jou. Ga terug naar Home." + **Details voor een volwassene** (code `forbidden`, trace-ID).
  De API weigert kind al op elke `Viewer`-route (403); de UI is nooit de poortwachter.
- **P1-inhoud:** Kijken en Zoeken bestaan nog niet → kindertaal: "Kijken komt later. Tot dan kijk je in Jelly Leon."
  (deep link alleen als het adres gemeten is) en "Zoeken komt later." met `details` "Details voor een volwassene"
  (volgt in fase P4 / P5). Home kind toont alleen "Hoi <naam>" + die twee kaarten. **Nooit** systeemstatus of
  incidenten.
- **Rolkeuze:** in Gebruikers en rollen (§4.8.1) en via SSO-groepen; **kind wint** bij meerdere groepen (backend
  `map_role`).

---

## 4. Nieuwe schermen per scherm-ID

Voor elk scherm gelden de algemene eisen E-04/E-29 (leeg, laden, fout, offline, rolcontrole, bron + bijgewerkt,
toetsenbord) en het offline-gedrag van C-16 (lezen blijft, alles wat wijzigt `aria-disabled` + "Uit: je bent
offline", niets in een wachtrij). Alleen de afwijkingen en bijzonderheden staan hieronder.

### 4.1 S-166 Diensten + S-014 Dienst koppelen (contract 1.2 H5) — `diensten.html`

**Route:** `/instellingen/diensten` · **Rol:** beheerder (kijker/operator: alleen lezen, RolMelding; koppelen,
rotatie, ontkoppelen en intrekken verborgen) · **API:** `GET /api/v1/services`, `GET /api/v1/auth/keyset`,
`POST /api/v1/services/pairing-codes`, `POST /api/v1/services/enrollment-tokens`,
`POST /api/v1/services/{id}/rotate` · `/unlink` · `/revoke` (Idempotency-Key), `PUT /api/v1/services/{id}/truenas-app`,
`GET /api/v1/registry/services` (adres van de statuspagina).

**Opbouw** (één kolom; ≥ 1280 de dienstkaarten in twee kolommen):

1. **PageHeader** "Diensten" + kruimelpad Instellingen › Diensten + primaire knop "Dienst koppelen" (springt naar 2).
2. **Vingerafdruk van deze Hub** (C-57): KopieerVeld met `keyset_fingerprint` (`XXXX-XXXX-XXXX-XXXX`) + uitleg
   "Komt die niet overeen, koppel dan niet en trek de dienst in." + `details` met de publieke sleutelset (JSON van
   `/auth/keyset`) voor MediaGuard, MSO en my_house (§2.3 regel 3: "alleen publieke sleutels").
3. **Dienst koppelen** (S-014): Select "Welke dienst?" (eigen diensten: `home-control-hub`, `appstore-en-fork`,
   `jelly-leon-platform`, `zoeken-en-persoonlijke-ai`; de executor koppel je via Onboarding → Executor) +
   RadioGroup **zonder standaard** "Hoe koppel je?":
   - *Enrollment-token in het Custom App-formulier (aanbevolen)* → resultaat: drie KopieerVelden met exact de namen
     `HUB_URL` (adres van de Hub zoals de browser hem ziet, met waarschuwing als dat `localhost` is), `HUB_ENROLLMENT_TOKEN`
     (één keer getoond, `no-store`) en `HUB_KEY_FINGERPRINT`; stappen "Open in TrueNAS Apps → <app> → Bewerken →
     Omgevingsvariabelen; vul deze drie in; Opslaan." (geen YAML, geen terminal).
   - *Koppelcode op de statuspagina* → **KoppelcodeKaart (C-40a)**: code in groepen + KopieerVeld code + KopieerVeld
     vingerafdruk (contract §3.7: samen tonen), Aftellen (60 min; executor 30 min), "Deze code zie je maar één keer.
     Hij werkt één keer en verloopt na 60 minuten. Een nieuwe code maakt deze niet ongeldig." (zo werkt de API:
     grants zijn los van elkaar), stappen met het **gemeten** adres van de statuspagina (registry: NAS-adres D03 +
     hostpoort; onbekend → "Adres onbekend — vernieuw de inventaris"), wachtregel "Wacht op de dienst — deze pagina
     toont de koppeling zodra <app> zich meldt." (polling 5 s zolang de kaart open is; daarna de dienstkaart).
   - Aftellen (C-22): elke seconde zichtbaar, aankondiging alleen op 5 min, 1 min en verlopen. Verlopen: code weg,
     "Verlopen — maak een nieuwe code." + knop.
4. **Gekoppelde diensten** (C-41a DienstKaart): pillen **neutraal** "Gekoppeld" (`link-2`) — nooit groen; uitleg
   "'Gekoppeld' zegt alleen dat de dienst een geldige sleutel heeft. Of hij gezond is, zie je bij Apps." `dl` met
   App-id, Versie, Gekoppeld (datum + via), **Laatste contact** (= `laatst_gebruikt` van het nieuwste geldige token),
   Token (`••••` + `laatste4` + leeftijd), TrueNAS-app (H14: "gemeten: <naam> — Bevestigen" zolang niet bevestigd).
   - **Rotatie aanvragen** (`key-round`): AlertDialog "Rotatie aanvragen voor <app>?" — "De dienst krijgt bij zijn
     volgende aanroep het verzoek om zelf een nieuw token te maken. Er is geen onderbreking. Je ziet geen token." →
     pil `status-info` "Rotatie aangevraagd" tot de dienst geroteerd heeft. Token > 180 dagen: `melding-info` "Token
     ouder dan 180 dagen. We raden aan rotatie aan te vragen. De Hub roteert nooit zelf en de AI kan het niet
     aanvragen."
   - **Ontkoppelen…** (`unlink`): eigen bevestigingsblok onder de kaart (geen kleine dialoog): "Ontkoppelen
     <app>? De Hub vraagt de dienst om de koppeling te wissen en trekt daarna de registratie in. De dienst houdt zijn
     eigen data. Opnieuw koppelen kan daarna alleen via deze pagina." Knoppen **<app> ontkoppelen** / Annuleren.
     Fouten: 409 `service_address_unknown` → "Het adres van deze dienst is niet gemeten. Vernieuw de inventaris of
     trek de registratie alleen in."; 502 `service_unreachable`/`unlink_refused` → **Foutpaneel in de kaart** "Ontkoppelen
     is mislukt — De dienst is niet bereikbaar; er is niets ontkoppeld en niets ingetrokken." + "Opnieuw proberen"
     (prototype).
   - **Intrekken…** (`shield-x`): bevestiging met **getypte app-id** (onomkeerbaar zonder opnieuw koppelen): "Typ
     `<app_id>` om te bevestigen." · knop **Registratie intrekken** (uit tot de tekst klopt; reden ernaast).
     Daarna pil neutraal "Ingetrokken" (`shield-x`), acties "Opnieuw koppelen" (vult het formulier voor).
   - Ingetrokken diensten standaard verborgen: vinkje "Ingetrokken diensten tonen (n)".
   - Executor: zelfde kaart, regel "Schrijfsleutel: alleen op de executorpagina; de Hub ziet hem nooit." + deep link
     "Executorpagina openen"; geen rotatie-/ontkoppelknop in de Hub (contract §3.9: alleen op de executorpagina met
     een live geverifieerde schrijfsleutel); wel Intrekken.

**Toestanden:** leeg ("Nog geen diensten gekoppeld. Een dienst koppelen geeft hem een eigen sleutel voor de Hub.
**Dienst koppelen**"); laden (skelet van twee kaarten); register onbereikbaar (Foutpaneel paginaniveau); verouderde
inventaris → adres onbekend in de stappen. **Testids:** `dienst-koppelen`, `koppelcode`, `dienstenregister`,
`dienst-<app_id>`, `vingerafdruk-hub`. **A11y:** de grote code is `aria-hidden` (dubbel met het KopieerVeld);
knoppen dragen de dienstnaam in de toegankelijke naam ("Intrekken…: home-control-hub").

### 4.2 S-165 Noodaccount + S-003 Noodlogin (contract 1.2 H6, §4.1) — `noodaccount.html`

**Route:** `/instellingen/noodaccount` (beheerder) · **API:** `GET /api/v1/auth/break-glass`,
`POST …/setup` (eigen wachtwoord + gebruikersnaam + wachtwoord ≥ 20 + sessieduur), `POST …/confirm` (TOTP),
`POST …/rotate`, `POST …/selftest` (geen mutatie, geen Idempotency-Key), `POST …/login` (publiek).

**Opbouw** (≥ 1280 twee kolommen: links status + instellen/vernieuwen, rechts zelftest + gebruik):

1. **Status** (`data-testid="noodaccount-status"`): pillen **neutraal** "Ingesteld" (`life-buoy`) of Onbekend "Niet
   ingesteld"; "Rotatie loopt"/"Rotatie vereist" als `status-info`. Werkt de noodlogin niet (`werkend: false`), dan een
   `melding-onbekend` met de reden in één zin, bijvoorbeeld **"Noodlogin werkt nu niet: de nieuwe TOTP is nog niet
   bevestigd."** Belangrijk (gemeten in `breakglass.py`): tijdens een rotatie is `totp_confirmed_at` leeg, dus werkt
   de noodlogin **pas weer na de bevestiging** — de UI zegt dat vóór de gebruiker begint ("Tot je de nieuwe code
   bevestigt, werkt de noodlogin niet."). `dl`: Account (mono), Rol "Beheerder (vast)", Sessieduur "60 min, niet te
   verlengen", Laatst gebruikt (+ "incident gemeld"), Herbevestiging "Volgende uiterlijk <datum>. Elke 90 dagen een
   melding, nooit een blokkade.", Inloggen kan "Alleen vanaf privé-adressen (LAN of VPN), nooit vanaf internet."
2. **Instellen / vernieuwen** (TotpInstellen C-59): stepper "Nieuw wachtwoord · Authenticator-app en code".
   Stap 1 vraagt **je eigen wachtwoord** + het nieuwe noodwachtwoord (≥ 20 tekens, niet de gebruikersnaam) + sessieduur.
   Stap 2 toont het geheim **één keer**: KopieerVeld "Geheim (handmatig invoeren)" in groepen van 4, KopieerVeld
   "Koppeling voor de app (otpauth)", `melding-info` "Dit geheim zie je maar één keer. Zet het nu in je
   authenticator-app en bewaar een kopie offline, bijvoorbeeld op papier bij je herstelkit. De Hub toont het hierna
   nooit meer." en het veld "Code uit de authenticator-app" (6 cijfers, `inputmode=numeric`,
   `autocomplete=one-time-code`) → "Code bevestigen". **Geen QR-code** zolang er geen lokaal gebundelde generator is
   (OB-07). Verlaat de gebruiker de pagina vóór bevestiging: waarschuwing "Het geheim is dan weg; je moet opnieuw
   beginnen." Fout 401 `invalid_totp` → veldfout "Deze code klopt niet. Wacht op de volgende code en probeer opnieuw."
3. **Zelftest** (C-58): knop "Zelftest uitvoeren" (`list-checks`); samenvatting met `role=status` ("Uitkomst om 11:56:
   noodlogin werkt nu niet (1 controle mislukt)."); controles: Noodaccount · TOTP · "Privé-adres wordt toegelaten"
   (`10.0.0.1`) · "Internetadres wordt geweigerd" (`192.0.2.10`, RFC 5737) · **"Jouw adres zoals de Hub het
   ziet"**: privé → neutraal vinkje; **lijkt Docker-gateway** (`lijkt_docker_gateway`) → `controle-onbekend` "Onbekend:
   dit lijkt het gateway-adres van het Docker-netwerk. Dan ziet de Hub niet het echte adres van je apparaat en is de
   controle op privé-adressen zwakker. Niet gevalideerd op de NAS."; niet privé → `controle-beleid` (`lock`) "Vanaf dit
   adres wordt noodlogin geweigerd (alleen privé-adressen)." Uitleg boven de knop: "zonder in te loggen en zonder
   Authentik of het netwerk te gebruiken. Er verandert niets."
4. **Noodlogin gebruiken:** KopieerVeld met het adres van de noodlogin (`<Hub-adres>/inloggen/nood`, "zet dit in je
   herstelkit"), sessieduur (5–240), slotregel "Wijzigen vraagt je eigen wachtwoord. Dit zijn geen acties voor de
   AI: die kan het noodaccount niet zien, voorstellen of wijzigen."

**4.2.4 Noodlogin-pagina** (`/inloggen/nood`, publiek, S-003): publieke schil (merk, geen navigatie), h1 "Noodlogin",
`melding-info` "Alleen voor als inloggen via SSO niet werkt. Werkt alleen vanaf je eigen netwerk (LAN of VPN). Elke
noodlogin wordt vastgelegd en gemeld; daarna moet je wachtwoord en TOTP vernieuwen.", velden Gebruikersnaam,
Wachtwoord, Code uit de authenticator-app, knop **Noodlogin**. Fouten: 403 `source_not_private` → "Noodlogin kan
alleen vanaf je eigen netwerk. Dit apparaat komt binnen via een adres buiten het netwerk." (met code + trace-ID); 401 →
"Gebruikersnaam, wachtwoord of code klopt niet." (nooit zeggen wélk deel); 429 → "Te veel pogingen vanaf dit apparaat.
Probeer het over <n> minuten opnieuw." Na inloggen: vaste balk boven de kop (`status-info`-stijl, `role=status`)
"Noodsessie — eindigt om 12:56 (nog 59 min). Niet te verlengen." (Aftellen C-22) + een link naar Noodaccount
(rotatieplicht). Op `/inloggen` staat een gewone tekstlink "Noodlogin (alleen vanaf je eigen netwerk)".

### 4.3 S-040 Apps (catalogus, P1) — `apps.html`

**Route:** `/apps` · **Rol:** kijker+ (Catalogus bijwerken: operator) · **API:** `GET /api/v1/apps?limit=200&q=&status=`
(`per_status`, `inventaris`), `POST /api/v1/apps/discover`.

- PageHeader "Apps" + kruimelpad Server › Apps; meta-regel "Catalogus bijgewerkt 11:56 · inventaris van 11:54
  (TrueNAS app.query)" (beide tijden, want de catalogus is zo vers als de inventaris); knop "Catalogus bijwerken"
  (operator; uitleg na afloop: "Alleen de catalogus is bijgewerkt; op de NAS is niets gewijzigd.").
- **FilterBalk C-35:** zoekveld (naam, app-id of image) + ToggleGroup-chips **met aantallen uit `per_status`**: Alle ·
  Storing · Beperkt · Onbekend · Gezond (`aria-pressed`) + "Meer filters" (Sheet op mobiel: installatiewijze,
  eigenaar, "Ook verdwenen apps tonen"). Resultaatteller `aria-live`: "7 apps · slechtste status eerst · filter: alle".
- **Volgorde:** slechtste status eerst (Storing > Beperkt > Onbekend > Gezond), dan naam. De API sorteert op naam;
  de UI haalt `limit=200` op en sorteert zelf. Geeft de API een `next_cursor` (meer dan 200 apps), dan volgorde op
  naam + melding "Meer dan 200 apps: gesorteerd op naam." (OB-08; voorstel `sorteer=status` aan de API).
- **ResponsieveLijst:** ≥ 1024 tabel App (titel + `runtime_id` mono) · Gezondheid (StatusBadge + **reden zichtbaar**) ·
  Versie (tag + ingekorte digest `sha256:91c4…7d02`; kopiëren in het detail) · Installatie en eigenaar ("Custom App
  (standaardformulier)" voor `ix-app`, "Compose (YAML)" voor `custom_app=true`, "Catalogusapp") · Openen (deep link,
  `square-arrow-out-up-right`, "(opent in een nieuw tabblad)"); < 1024 een kaart per app met dezelfde velden.
- Uitlegregel boven de lijst: "Gezond betekent: bereikbaar én (voor apps met eigen taken) een verse controle van
  binnenuit. 'Draait' volgens TrueNAS alleen is nooit gezond."
- **Toestanden:** inventaris verouderd → elke rij Onbekend + Verouderd met laatst bekende TrueNAS-staat, banner per
  sectie "Inventaris verouderd (laatst 10:12). Vernieuw de inventaris." · lege catalogus → "Nog geen apps in de
  catalogus. De catalogus vult zich na een geslaagde inventaris. **Inventaris vernieuwen**" · geen deep link →
  knop `aria-disabled` + reden uit `reden_geen_url`. Verdwenen apps: neutraal label "Verdwenen sinds <datum>"
  (nooit verwijderd, alleen verborgen). **Testids:** `app-lijst` (blijft), `app-<runtime_id>`, `app-filter`.

### 4.4 S-041…S-045 Appdetail in P1 — `appdetail-p1.html` (+ `appdetail*.html` voor P2)

**Route:** `/apps/[id]?tab=status|metrieken|logs|versies|acties` (tab in de URL, zodat terug/vooruit werkt) ·
**API:** `GET /api/v1/apps/{id}` (ETag, `gezondheid` met componenten, `acties` per rol), `GET /api/v1/monitoring/health`,
`GET /api/v1/metrics/series` + `/metrics/query`, `GET /api/v1/logs?bron=` (operator), `GET /api/v1/incidents?bron=`.

- **Kop:** kruimelpad Server › Apps › <naam>; h1 naam; omschrijving "<eigenaar> · <installatiewijze> · versie x";
  DeepLink "Openen in <app>" (de enige actie die in P1 kan; alleen lezen).
- **Gezondheidskaart** boven de tabs (`data-testid="app-gezondheid"`): StatusBadge groot + reden in één zin + link
  naar het incident; daaronder **Gezondheid per onderdeel** (ResponsieveLijst): TrueNAS-staat (neutrale pil `power`
  "Draait", met de zin "Draaien alleen is geen bewijs van gezond.") · Buitenkant (Uptime Kuma; StatusBadge + latency +
  tijd) · Binnenkant (connector-health / heartbeat / worker; StatusBadge + naam van de controle + tijd). Ontbreekt een
  onderdeel: Onbekend met reden ("Geen Uptime Kuma-monitor gekoppeld", "Binnenkant volgt in fase P3 (koppeling met
  MediaGuard)"). Daarnaast KopieerVeld Image-digest en Versheid met Image, Data-dataset(s) (paden met `<wbr>`) en
  **Resourcegrenzen: "Onbekend — de Hub leest de app-configuratie niet (kan geheimen bevatten)."**
- **Tabs** (shadcn Tabs volgens COMPONENTEN §21; < 768 omlopende knoppen):
  - *Status:* controles per onderdeel met historie (laatste 24 u), uptime 30 d (alleen als Kuma levert), laatste
    incidenten (IncidentRij C-27), eigenaar/documentatie.
  - *Metrieken:* periodekiezer; latency (lijn, één reeks, bron Uptime Kuma). **CPU en geheugen per app: "Niet
    beschikbaar — nog geen bron per container." (`capability_unavailable`-tegel, B09-001 hiaat).** Geen lege grafiek.
  - *Logs:* eigen diensten: LogWeergave C-52 uit de log-index (`GET /api/v1/logs?bron=<app_id>`, operator); andere
    apps: "Niet beschikbaar — de Hub leest TrueNAS-containerlogs (nog) niet. Bekijk ze in TrueNAS → Apps → <app> →
    Logs." (`capability_unavailable`). Kijker: RolMelding "Logs bekijken kan vanaf de rol operator."
  - *Versies:* huidige tag + digest + `image_historie` (wanneer welke digest gezien); "Bijwerken en terugzetten volgen
    in fase P2."
  - *Acties* (C-12a): `melding-nogniet` "Nog niet beschikbaar — volgt in fase P2 (veilig automatiseren). Dan opent
    elke actie eerst een voorstel met preview, het risico volgens het beleid, een back-up vooraf en een controle na
    uitvoering. Tot dan wijzigt de Hub niets aan apps." + rijen Herstarten (`app.restart`) · Stoppen · Bijwerken ·
    Terugzetten · Verwijderen (container), elk met **knop `aria-disabled`** (`hourglass`), zichtbare regel "Volgt in
    fase P2" en tekst "risico bepaalt het beleid" — **geen RisicoBadge** zolang de policy-engine de klasse niet bepaalt
    (een badge zou een besluit suggereren dat er nog niet is). "Data verwijderen (R3) staat hier bewust niet."
    Rollen zonder recht zien de rijen niet, wel de RolMelding. In P2 wordt dit `appdetail.html` (ActiePreview).

### 4.5 S-050 Problemen-inbox + S-051 incidentdetail (P1) — `problemen.html` met deze P1-delta's

**Routes:** `/problemen` (≥ 1280 master-detail: lijst 24 rem + detail), `/problemen/[id]` (kleiner: apart scherm) ·
**API:** `GET /api/v1/incidents` (+ filters status, ernst, bron, soort, oorzaak, tekst; cursor),
`/incidents/samenvatting`, `/incidents/{id}` (ETag), `/bewijs`, `/events`, `/onderzoek`, `/supportbundel`,
`POST …/erkennen` · `/snooze` · `/oplossen` · `/notities` · `/herstel-voorstellen` · `/veilige-modus`.

Het prototype `problemen.html` blijft de referentie voor vorm en volgorde. **In P1 wijkt de inhoud op deze punten af**
(bouw de P1-versie, niet de P2-teksten):

| Onderdeel in `problemen.html` | P1-weergave | Waarom |
|---|---|---|
| "AI-hypothese · 11:55" en knop "Onderzoek met AI" | "Hypothese (vaste regel) · 11:55" en knop **Onderzoek** (`list-checks`) die het stappenplan + readback toont (`/onderzoek`) | de hypothese komt uit vaste regels, er is geen AI in P1 |
| ZekerheidLabel uit de API | API geeft een getal (0,3–0,9) per regel. Weergave als woord, **nooit als percentage**: ≥ 0,85 Zeker · ≥ 0,6 Waarschijnlijk · lager Onzeker · leeg **Ik weet het niet** (volwaardige kaart). Het getal en de regelnaam staan alleen in "Toon bewijs" | Peil T-24: geen percentage zonder model (OB-04) |
| ErnstLabel Kritiek/Hoog/Middel/Laag/Info | API kent drie niveaus: `kritiek` → **Kritiek**, `waarschuwing` → **Middel**, `info` → **Info**. Hoog en Laag worden in P1 niet gebruikt | vaste woorden behouden, rangorde blijft gelijk (OB-05, contract-issue) |
| IncidentStatus Open/Erkend/Uitgesteld/Opgelost | `open` · `erkend` (met "erkend tot 14:00" = verval/escalatie) · `gesnoozed` → **"Uitgesteld tot 08:00"** (Peil: uitstellen, niet snoozen) · `opgelost`; heropend: neutrale tag "Heropend" | vaste termen |
| Knoppen Erkennen · Uitstellen… · Oplossen | Erkennen (minuten) · Uitstellen… (kritiek hooguit 24 u; de keuzes erboven) · Oplossen. Weigert de API met 409 `nog_actief`: veldloze melding "Oplossen kan niet: <bron> meldt het probleem nog (readback 11:56)." | readback is leidend |
| "Herstel voorstellen" opent de ActiePreview | opent een **alleen-lezen voorstel**: action_id, doel, parameters, vervaltijd; **"Risico: bepaalt het beleid (P2). Voorgestelde klasse R1 is een claim en telt niet."**; `melding-nogniet` "Uitvoeren volgt in fase P2. Tot dan voer je dit zelf uit in TrueNAS → Apps." Geen knop Uitvoeren/Goedkeuring aanvragen | `uitvoerbaar: false`, policy-engine bestaat nog niet |
| Veilige modus "Niet beschikbaar" | `veilige_modus.actief` → `melding-gate` (`lock`) "Veilige modus sinds 10:09: de Hub stelt geen herstart meer voor (2× opnieuw mislukt binnen een uur)." + knop **Veilige modus opheffen…** (operator, reden verplicht, audit) | B09-006 |
| "Geschoonde incidentgegevens kopiëren" | KopieerVeld/knop op basis van `/supportbundel` (operator), met regel "Geheimen, tokens en IP-adressen zijn gemaskeerd." | B09-004 |
| Tijdlijn | uit `/events` (cursor "Meer laden"); actor-label systeem/gebruiker/dienst; logtekst altijd als geciteerde data | E-21 |

- **Inbox:** IncidentRij C-27 als één link (ernst · titel · bron · eerste–laatste · `×n` · status); FilterBalk met
  status (Actief standaard), ernst, bron; "groepeer op oorzaak" uit `/samenvatting`. Leeg en monitoring vers: "Geen
  open problemen. Gecontroleerd om 11:56."; monitoring niet vers: **Onbekend** "We weten niet of er problemen zijn:
  de monitoring is niet vers (laatst 10:12)." — nooit "geen problemen".
- **Testids:** `incidenten-inbox`, `incident-<id>`, `incident-detail`, `hypothese`, `bewijs`, `stappenplan`,
  `veilige-modus`. Bestaande test op `/problemen` als NogNietBeschikbaar vervalt (§7).

### 4.6 S-020 Home met echte data (P1) — `home.html`, `offline.html`

Opbouw blijft (SysteemStatusPaneel + "Wat actie nodig heeft" naast elkaar ≥ 1280, daaronder StatKaarten). **Bronnen
per onderdeel in P1:**

| Onderdeel | Bron (API) | Weergave |
|---|---|---|
| Systeemstatus · Apps | `GET /api/v1/apps` → `per_status` | slechtste app bepaalt; reden = de slechtste app + reden |
| Systeemstatus · Opslag | `GET /api/v1/observability/nas` (pools) / inventaris pools | Gezond / Beperkt / Storing; verouderd = Onbekend + laatst bekend |
| Systeemstatus · Problemen | `GET /api/v1/incidents/samenvatting` | aantal actieve per ernst; Kritiek actief = Storing-rij |
| Systeemstatus · Monitoring | `GET /api/v1/monitoring/sources`, `/monitoring/status` | bron mislukt = Storing ("Beszel: inloggen geweigerd"); geen bron = Onbekend "Geen monitoringbron ingesteld" |
| Systeemstatus · Meldingen | `GET /api/v1/notifications/channels` | kanaal gestopt (token geweigerd) = Storing; geen kanaal = Onbekend; anders **niet** groen maar neutraal "Aan" (een kanaal is geen gezondheid) — telt niet mee in de totaalstatus |
| Systeemstatus · Back-ups | `GET /api/v1/gates`, `/backups/coverage` | gate dicht door invulwerk = **gate-rij** (neutraal, telt niet als storing); gemeten falen = Storing |
| Systeemstatus · Media, Huis, Netwerk | — | **Nog niet beschikbaar** (P3/P5), telt niet mee |
| Wat actie nodig heeft | incidenten (actief, kritiek eerst) > (P2: goedkeuringen) > gates dicht > onboarding open | per item as-label (ErnstLabel / Gate / Onboarding) + werkwoordknop "Incident bekijken" / "Invullen" / "Onboarding verder" |
| Kaart Apps en uptime | `/apps` + Kuma (uptime 30 d alleen als gemeten) | "13 van 14 apps gezond · gemeten"; Onbekend telt niet als gezond |
| Kaart GPU en AV1 | `/observability/nas` (gpus) | gebruik per GPU (A310 en UHD 770 apart); **temperatuur altijd Onbekend** ("geen bron, nooit 0 °C"); AV1-wachtrij = Nog niet beschikbaar (MediaGuard, P3) |
| Kaart Veiligheid en back-ups | coverage + gate + hersteltests | ongewijzigd t.o.v. P0, nu in Peil-vorm |
| Kaart Problemen (nieuw) | `/incidents/samenvatting` | "2 actief · 1 kritiek"; vervolglink "Problemen bekijken" |
| Kaart Nieuwste acties | `/audit?limit=3` (beheerder) | kijker: "alleen voor beheerders" als Onbekend-reden, geen waarde |
| Kaart Onboarding | `/decisions` | voortgangsbalk (`chart-1` op `chart-meter-track`, `role=progressbar`) — nooit groen |
| Kaarten Downloads, Huis, Kosten | — | NogNietBeschikbaar (P3/P5) |

Vernieuwen elke 60 s zonder skeletflits; bij een fout **blijft de laatst bekende waarde staan als verouderd** (O-03).
Testids `kaart-*`, `waarde-*`, `totaalstatus`, `systeemstatus`, `acties` blijven.

### 4.7 S-031 Server → Metrieken (+ S-036 Meetdekking, S-035 Logs) — `server-metrieken.html`

**Route:** `/server/metrieken` · **API:** `GET /api/v1/observability/nas` (nu), `GET /api/v1/metrics/series` +
`GET /api/v1/metrics/query?reeks=&van=&tot=` (trend; auto-resolutie ≤ 6 u ruw, ≤ 7 d per 5 min, langer per uur),
`GET /api/v1/monitoring/coverage`.

- Subnavigatie Server (C-62) → **periodekiezer** (ToggleGroup 1 u · 6 u · 24 u · 7 d · 30 d, standaard 6 u; regel met de
  resolutie van de API) boven alles; alle kaarten en grafieken volgen dezelfde periode.
- **Nu-tegels** (StatKaart, KPI-rij): CPU-gebruik % · CPU-temperatuur °C · Geheugen (meter "41,2 GiB van 62,6 GiB") ·
  ZFS-cache (ARC) + trefkans. Bron per tegel uit de API ("TrueNAS (reporting.realtime)" gaat voor Beszel).
- **CPU-gebruik:** lijngrafiek C-32, één reeks (`chart-1`), y 0–100 %, gat = "Geen meting".
- **GPU's als small multiples:** per GPU een tegel (PCI-slot mono; gebruik %, vermogen W; temperatuur **altijd**
  Onbekend-blok) en een eigen grafiek met **dezelfde schaal 0–100 %**. ≥ 1280 tegels naast elkaar en grafieken naast
  elkaar (CSS `order`; DOM-volgorde per GPU tegel → grafiek). Verouderde GPU: kaart gestippeld, Onbekend + Verouderd,
  waardevak "Laatst bekend · 09:45", grafiek stopt bij het laatste punt met arcering "Verouderd sinds 09:45".
  Vermogen niet geleverd = "Niet beschikbaar" + `capability_unavailable`.
- **Opslag:** meter per pool (drempel 90 % → Beperkt met tekst "boven de drempel van 90%").
- **Netwerk:** tegels Ontvangen / Verzonden (Mbit/s) en een lijngrafiek met **twee reeksen** (Ontvangen `chart-1`,
  Verzonden `chart-2`), legenda + directe labels aan het eind; nooit een tweede y-as.
- **Meetdekking-kaart:** "14 van 19 metrieken hebben nu een verse bron. Hiaten: …" + link naar `/server/meetdekking`
  (DekkingsMatrix C-33: metriek × bron, cel kan/levert/hiaat met reden) + regel "Het Beszel-systeem *mini-pc* telt
  niet mee (D10)" (uit `uitgesloten`).
- **Logs** `/server/logs` (operator): FilterBalk (bron uit `/logs/bronnen`, niveau, tijd, tekst, trace-ID) +
  LogWeergave C-52; bronnen zonder logs ("TrueNAS-containerlogs") als Niet beschikbaar in de bronkeuze.

### 4.8 Instellingen (P1) — `instellingen-toegang.html`, `instellingen-bronnen.html`

#### 4.8.1 S-161 Gebruikers en rollen (incl. kind) en sessies

**Route:** `/instellingen/toegang` · **API:** `GET/POST /api/v1/users`, `PATCH /api/v1/users/{id}`,
`POST /users/{id}/sessions/revoke`, `GET /api/v1/sessions` (alle), `GET /api/v1/auth/sessions` (eigen).

- Kop "Gebruikers en rollen" + primaire knop "Gebruiker toevoegen" (`user-plus`).
- Lijst (≥ 1280 tabel, kleiner kaarten; prototype: bij 1024 was de tabel 64 px te breed → tabel pas vanaf 1280):
  Gebruiker (naam + gebruikersnaam mono) · Rol (tekst, géén statuskleur) · Aanmelden (Lokaal wachtwoord / SSO · groep /
  Noodlogin) · Sessies · acties "Rol wijzigen" en "Sessies intrekken" (toegankelijke naam met de gebruiker). Het
  noodaccount heeft alleen "Noodaccount beheren". Gedeactiveerde gebruikers verborgen achter een vinkje.
- **RolUitleg C-61** achter `details` "Wat mag elke rol?": Beheerder · Operator · Kijker · **Kind** ("Alleen Home,
  Kijken, Zoeken en Ik — met toegestane titels. Nooit beheer.") + "Via SSO bepaalt de groep de rol. Hoort iemand bij
  meerdere groepen, dan wint Kind; anders de hoogste rol. Zonder passende groep: geen toegang. De AI kan rollen nooit
  wijzigen." **RolKiezer** in "Gebruiker toevoegen"/"Rol wijzigen": RadioGroup zonder standaard met dezelfde zinnen.
- Sessies: tabel per gebruiker (bron lokaal/oidc/noodlogin, laatst actief, bron-IP), "Intrekken"; eigen sessies
  staan ook onder Account. Testids `gebruikers`, `sessies` blijven.

#### 4.8.2 S-163 Inloggen via SSO (OIDC-config + test)

**API:** `GET/PUT /api/v1/auth/oidc`, `POST /auth/oidc/discover`, `POST /auth/oidc/test`, `POST /auth/oidc/inschakelen`,
`GET /api/v1/sso/status`.

- Kop "Inloggen via SSO" + pil neutraal "Uit"/"Aan" (`power`).
- **GateBlokkade** zolang inschakelen niet mag: "Inschakelen kan nog niet: geblokkeerd door de HTTPS-voorwaarde —
  nodig: besluit D17 (HTTPS) op Getest. De testlogin hieronder is wel geslaagd." + knop "D17 openen". Geen
  "toch doorgaan".
- Formulier: Issuer-adres (alleen https; "Wijzigen zet SSO uit tot een nieuwe testlogin slaagt."), Client-ID,
  Clientgeheim (GeheimVeld: `••••` + laatste 4 + datum, "Geheim vervangen"), **Terugkeer-adres** als KopieerVeld
  ("zet dit in Authentik") met `melding-info` bij http ("De aanmeldcode is beschermd met PKCE en een browsercookie,
  maar zet HTTPS aan zodra D17 klaar is."), scopes, groepen-claim, sessieduur (15–720 min).
- **Controle van de issuer** (C-58 na `discover`): issuer exact · zelfde oorsprong · sleutels (alleen asymmetrisch).
- **Groep → rol** (tabel; rij toevoegen/verwijderen; rol als Select met Kind).
- **Testlogin** (`log-in`): uitkomst neutraal "Geslaagd om 11:50 als <gebruiker> · groep → rol. Er is geen sessie
  gemaakt." of Foutpaneel met de reden.
- **OIDC verplicht:** knop `aria-disabled` + reden "Kan pas als SSO aanstaat én het noodaccount werkt (nu niet: …)".
- **Advies van home-control-hub** (`/sso/status`): `deels_gecontroleerd` = `melding-onbekend` "Minste rechten deels
  gecontroleerd"; `verouderd` = Verouderd; nooit groen.

#### 4.8.3 Monitoringbronnen met verbindingstest (B09-002)

**Route:** `/instellingen/monitoring` · **API:** `GET/POST /api/v1/monitoring/sources`, `GET/PATCH /…/{id}`,
`POST /…/{id}/test`, `POST /api/v1/monitoring/poll`.

- BronKaart C-60 per bron: soort (met gevonden versie), adres (mono), sleutel `••••`+4, **pil neutraal "Uitgelezen om
  11:55"** of StatusBadge Storing "Uitlezen mislukt" + reden ("Inloggen geweigerd sinds 11:20: het wachtwoord van de
  readonly-gebruiker klopt niet meer. GPU- en CPU-metingen uit Beszel zijn nu onbekend; er is een incident
  geopend.") + primaire knop "Wachtwoord vervangen". Uptime Kuma: "23 monitors · 19 gekoppeld aan een app · 4 niet
  gekoppeld (koppelen)" → koppelscherm monitor → app (PATCH, handmatig).
- **Bron toevoegen:** soort zonder standaard (Uptime Kuma / Beszel), velden per soort (Kuma: API-sleutel en/of
  statuspagina's; Beszel: readonly-gebruiker + wachtwoord + NAS-systeem), adres "Vorm: http(s)://<adres>:<poort>. Geen
  localhost; de Hub draait in een eigen container." (nooit een voorbeeld-IP), knop **Opslaan en testen** (de API slaat
  eerst op en test daarna; mislukt de test, dan blijft de bron opgeslagen met de reden: dat staat onder de knop).
- Alertregels (B09-003) als sectie "Alertregels": lijst met drempel, duur, hysterese, dempen per regel/alert; standaard
  regels gemarkeerd; bewerken alleen beheerder.

#### 4.8.4 S-168 Meldingskanalen (Gotify) en out-of-band (B09-005)

**API:** `GET/POST /api/v1/notifications/channels`, `PATCH /…/{id}`, `POST /…/{id}/test`, `GET /api/v1/notifications`,
`GET /api/v1/monitoring/out-of-band`, `POST /api/v1/monitoring/out-of-band/bevestiging`.

- KanaalKaart: adres, app-token `••••`+4, vanaf ernst, stille uren ("kritiek gaat altijd door"), hoogstens n per venster
  ("daarna één samenvatting"), pil neutraal "Aan"/"Uit"; token geweigerd → Storing "Kanaal gestopt: Gotify weigerde het
  token. Vul een nieuw token in." **Testmelding versturen** (`send`) → "Om 11:30 door Gotify aangenomen. Of hij op je
  telefoon aankwam, kan de Hub niet zien." (nooit "afgeleverd").
- **"Meldt er nog iets als de Hub uitvalt?"** (C-58): Kuma bewaakt de Hub (ja/nee/onbekend) · Kuma → Gotify
  (`circle-help` "Handmatig bevestigd op …; niet door de Hub gevalideerd") · "Als de hele NAS uitvalt" (`circle-slash`
  "Dan meldt niemand iets: Uptime Kuma en Gotify draaien op dezelfde NAS.") + knop "Handmatige test vastleggen".
- Meldingenlogboek (`/notifications`): status wachtrij / uitgesteld / verzonden / onderdrukt (rate-limit) / mislukt /
  dead-letter, als ResponsieveLijst.

#### 4.8.5 Overige subpagina's

- **Account** (S-160): naam, wachtwoord wijzigen (testids `pw-*`), ThemaKeuze, eigen sessies, uitloggen
  (`uitloggen-instellingen` blijft).
- **Auditspoor** (S-164): AuditTijdlijn C-25 + knop "Ketting controleren" (`/audit/verify`) → TestResultaat
  (nummering, koppeling, inhoud, anker); "staart ontbreekt" na een bewuste restore als `controle-onbekend` met de
  uitleg uit `docs/INCIDENTEN.md`. Testid `audit` blijft.
- **Over deze Hub** (S-170): versies, Validatielabel C-09 per onderdeel (exact de strings uit §11), PWA-status
  (`pwa-status` blijft), licenties. Testid `over-de-hub` blijft.

#### 4.8.6 Inloggen met SSO-meldingen (`/inloggen?sso_fout=…`)

| `sso_fout` | Melding (Foutpaneel, met code) |
|---|---|
| `sso_uit` | "Inloggen via SSO staat uit. Log in met je eigen account." |
| `sso_gewijzigd` | "De SSO-instellingen zijn net gewijzigd. Probeer opnieuw." |
| `geen_rol` | "Je account hoort bij geen enkele groep die toegang heeft. Vraag een beheerder om je groep te koppelen." |
| `account_uitgeschakeld` | "Dit account is uitgeschakeld. Vraag een beheerder." |
| andere (`exc.reden` uit de OIDC-controles) | "Inloggen via SSO is mislukt." + code; bij onbekende issuer of netwerkfout: "Authentik is niet bereikbaar. Gebruik je eigen account of de noodlogin." |

---

## 5. Nieuwe en uitgebreide componenten

Volledige specificatie in `design/ontwerptaal/COMPONENTEN.md` §27; samengevat (design-system *extend*):

| Probleem | Bestaand | Waarom niet genoeg | Nieuw |
|---|---|---|---|
| Toestanden die geen gezondheid zijn (Gekoppeld, Ingesteld, Aan, Draait, Geslaagd, Ingetrokken) zagen eruit als Gezond of hadden geen vorm | StatusBadge "Gekoppeld" (alleen in de statuspagina) | geen Hub-variant, geen regel voor "geslaagd" | **C-03a** `status-neutraal` / `status-info` |
| Acties die pas in P2 werken | C-12 (pagina/tegel/knop) | geen rij-patroon met gedeelde reden | **C-12a** `melding-nogniet` + `aria-disabled`-rijen |
| Koppelcode samen met vingerafdruk (contract §3.7) | C-40 CodeWeergave | geen vingerafdruk, geen gemeten adres | **C-40a** KoppelcodeKaart |
| Register van diensten met rotatie/ontkoppelen/intrekken | C-41 DienstRij | rij te smal voor 3 acties + fout | **C-41a** DienstKaart |
| Publieke sleutelset kopiëren | C-15 | geen samenhang met vingerafdruk | **C-57** SleutelsetPaneel |
| Uitkomst van tests/zelftests | — | eenmalige test ≠ gezondheid | **C-58** TestResultaat/Controlelijst |
| TOTP eenmalig tonen en bevestigen | C-39 GeheimVeld | geheim moet juist één keer zichtbaar zijn | **C-59** TotpInstellen |
| Monitoringbron/meldingskanaal | C-39, C-41 | sleutel + uitlezen + test in één kaart | **C-60** BronKaart/KanaalKaart |
| Rollen uitleggen en kiezen (incl. kind) | C-49 RolMelding | geen uitleg per rol | **C-61** RolUitleg/RolKiezer |
| Sub-navigatie Server en Instellingen | Tabs (§21) | "maximaal één tabrij"; dit is navigatie | **C-62** Subnavigatie |

---

## 6. Grafieken (dataviz-procedure, vóór de keuzes gevolgd)

1. **Vorm:** één huidige waarde → StatKaart (CPU, temperatuur, ARC, netwerk nu); verhouding tot een grens → meter
   (geheugen, pools); trend → lijn met één y-as; twee entiteiten op dezelfde schaal (A310 en UHD 770) → **small
   multiples** (zelfde 0–100 %-schaal, elk één reeks) in plaats van twee kleuren in één grafiek, zodat de GPU-kleur
   niet botst met de domeinkleuren GPU-/CPU-lane (`chart-1`/`chart-2`) en een verouderde GPU de andere niet stoort;
   twee maten van dezelfde eenheid (netwerk in/uit) → één lijn met twee reeksen + legenda.
2. **Kleur:** Peil-palet in vaste volgorde (`chart-1` blauw … `chart-5` magenta), status gereserveerd; meter boven de
   drempel = Beperkt met icoon en tekst.
3. **Validator opnieuw gedraaid** (`validate_palette.js` uit de dataviz-skill, via `DATAVIZ_VALIDATOR`): licht op
   `#FFFFFF` en donker op `#141920` **ALL CHECKS PASS** (lichtheidsband, chromavloer, CVD aangrenzend ΔE 8,8 / 8,4,
   normaal zicht 17,7 / 19,3, contrast ≥ 3:1); `contrast.json` toont nu weer een eigen meting in plaats van
   "overgenomen".
4. **Markeringen en eerlijkheid:** lijn 2 px, vlak 10 %, gat = arcering + "Geen meting" (nooit doorgetrokken, nooit 0),
   **verouderd = lijn stopt + arcering "Verouderd sinds 09:45"** (nieuw in `lijngrafiek()`), directe labels alleen op
   het eindpunt.
5. **Interactie:** draadkruis + tooltip met aanwijzer én pijltjes/Home/End/Esc, voorlezen via `aria-live`; "Toon als
   tabel" bij elke grafiek; verversen houdt de vorige weergave. In de Hub: shadcn `Chart` op recharts met
   `connectNulls={false}`, `isAnimationActive` uit bij reduced motion, tooltip als eigen component met `textContent`.
6. **Bekeken:** `shots/server-metrieken-*.png` (geen labelbotsingen; bij 360 alleen eerste/laatste x-label).

---

## 7. Tests: wat geraakt wordt en wat erbij komt

### 7.1 Bestaande tests (`apps/web`)

| Test | Fase 1 (aliaslaag) | Fase 2/3 + P1-schermen |
|---|---|---|
| `tests/unit/components.test.tsx` "status heeft symbool én tekst" (`aria-hidden">?</span>`) | groen | **aanpassen:** controleer een lucide-`svg[aria-hidden]` + het woord + `data-status` |
| idem "nog niet beschikbaar" met `PLANNED.problemen` | groen | **aanpassen:** Problemen is in P1 echt; gebruik `PLANNED.ai` (P2) |
| `tests/unit/home.test.ts`, `status-nav.test.ts` | groen | **aanpassen** voor de Peil-labels (Alles gezond / Deels onbekend), `worstTone` (Beperkt vóór Onbekend) en de kindnavigatie |
| `e2e/10-schermen.spec.ts` navigatie (`bottom-nav`, `sidebar`, `meer-lijst`, labels) | groen | blijft geldig: labels en testids ongewijzigd; `meer-lijst` moet ook in de Meer-sheet bestaan |
| idem skiplink "Naar de inhoud" | groen | tekst blijft **"Naar de inhoud"** (prototypes zeggen "Naar inhoud"; de Hub houdt zijn bestaande tekst) |
| idem per scherm: h1, geen `loading`/`error-panel`, geen overloop, doelen ≥ 44 px, axe | groen | **helpers aanpassen:** `expectTouchTargets` selecteert ook `[data-slot=button]`, `[role=tab]`, `label.keuze`/RadioGroup-items in plaats van `.btn`/`label.choice`/`.link-list a`; `expectNoHorizontalScroll` heeft de `.table-wrap`-uitzondering niet meer nodig (ResponsieveLijst) — laat de uitzondering alleen voor LogWeergave/diff (2D-inhoud) |
| idem SCREENS-lijst | — | **uitbreiden** met `/apps/[id]`, `/server/metrieken`, `/server/meetdekking`, `/server/logs`, `/problemen/[id]`, `/instellingen/{account,toegang,noodaccount,diensten,monitoring,audit,over}`, `/inloggen/nood` (publiek); `/problemen` uit de lijst "nog niet beschikbaar" |
| idem Home-kaarten (`kaart-*`, `freshness` met "Laatst bijgewerkt" en "Bron", precies 1 link) | groen | **aanpassen:** Peil-Versheid zegt "Bijgewerkt" (niet "Laatst bijgewerkt") — óf de test op "Bijgewerkt" zetten, óf het label in de Hub "Laatst bijgewerkt" houden (OB-09: test aanpassen); `freshness`-testid blijft; nieuwe kaart `kaart-problemen` |
| idem `totaalstatus` "Deels onbekend" | groen | blijft (vast woord) |
| idem Server (`sectie-pools` "Gezond", `pool.query`, A310, `onbekend`) | groen | blijft; "onbekend" wordt "Onbekend" (hoofdletter) → **matcher hoofdletterongevoelig** maken |
| idem Backups (`sectie-backupgate` "Geblokkeerd", `capability_unavailable`, "Synchronisatie is geen herstelgarantie") | groen | blijft; de gate toont "Geblokkeerd door de back-upgate …" (bevat "Geblokkeerd") |
| idem donker thema (axe op `/`, besluit D03, `/backups`) | groen | uitbreiden naar **alle** schermen (Peil-matrix) |
| `e2e/00-opzet.spec.ts` (setupcode, foute code, TrueNAS-koppeling, `data-reason`, `vingerafdruk-vertrouwen` `toBeDisabled`, D02/D04/D16) | groen | blijft: `aria-disabled` telt voor Playwright `toBeDisabled` (rol button); "Verbonden (alleen-lezen)" blijft als tekst maar wordt neutraal; `#wachtwoord-fout` blijft |
| `e2e/90-afsluiting.spec.ts` (NAS offline → "Verouderd", `onbekend-pools`, `waarde-opslag` "onbekend"; browser offline; kijker; geen NAS-mutaties) | groen | **aanpassen:** met O-03 blijft de laatst bekende waarde staan → `waarde-opslag` toont het verouderde waardevak + "Laatst bekend"; assertie wordt "bevat Verouderd én niet 'Gezond'". Offline-banner-tekst wordt Peil: "Je bent offline. Gegevens zijn niet actueel; acties zijn uitgeschakeld." → assertie op "niet actueel" in plaats van "Gegevens zijn nu onbekend" |

### 7.2 Nieuwe tests (minimaal, per scherm met de echte API + fakes)

- **Peil-matrix** (ONTWERPTAAL §12): Playwright-projecten **320 en 1024** erbij (nu 360/390/768/1440); axe-tags
  `wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa` = 0 in licht én donker op elk scherm; Tab-doorloop op 390 en 1440 met
  "focus niet bedekt" (scroll-padding); geen tekst < 14 px; `prefers-reduced-motion`; forced colors houdt
  stippelranden. Referentie: `design/ontwerptaal/bouw/controle.cjs` en `gedrag.cjs`.
- **Diensten:** koppelcode maken → KoppelcodeKaart met code + vingerafdruk + aftellen; een simulator-dienst koppelt
  met de code → kaart "Gekoppeld" (neutraal, nooit groen: assert geen `data-status="healthy"`); rotatie aanvragen → pil
  "Rotatie aangevraagd"; ontkoppelen bij onbereikbare dienst → `error-panel` `data-code=service_unreachable` en de
  dienst blijft gekoppeld; intrekken pas na het typen van de app-id; kijker ziet geen mutatieknoppen.
- **Noodaccount:** setup → geheim één keer (na herladen weg) → foute code (veldfout) → goede code (TOTP berekend in de
  test) → werkend; zelftest toont het bron-IP; rotatie zet "werkt nu niet" tot bevestiging; noodlogin vanaf
  `127.0.0.1` wordt **geweigerd** (loopback telt niet als privé: `source_not_private`) en de zelftest zegt dat; "OIDC verplicht" `aria-disabled` zolang niet werkend.
- **Apps/appdetail:** status-chips met aantallen; `Draait` is nooit Gezond; acties-tab: alle knoppen
  `aria-disabled` met "Volgt in fase P2"; deep link opent in een nieuw tabblad.
- **Problemen:** 100 identieke events → één rij `×100`; Oplossen bij actieve bron → melding `nog_actief`; "Herstel
  voorstellen" toont geen Uitvoeren-knop; zekerheid als woord, nooit "%".
- **Server-metrieken:** GPU-temperatuur altijd "Onbekend" (nooit "0 °C"); gat in de reeks → "Geen meting" in de tabel.
- **Instellingen:** SSO-gate zichtbaar zonder D17; testlogin tegen de fake-issuer; bron toevoegen met foute sleutel →
  opgeslagen + "Uitlezen mislukt"; testmelding → "door Gotify aangenomen".
- **Kind:** inloggen als kind → kindschil (4 items, geen `sidebar`, geen tellers); `/server` → kindvriendelijke 403.

### 7.3 Schermafdrukken

`docs/screenshots/p0/` (29 JPEG's) blijft als bewijs van P0. De webstap schrijft naar `docs/screenshots/p1/<project>/`
(`SCREENSHOT_DIR` in `e2e/helpers.ts`): alle bestaande namen (home, server, apps, backups, onboarding, besluit-D03,
truenas, executor, instellingen, problemen, home-donker) **opnieuw** plus apps-detail, problemen-detail,
server-metrieken, diensten, noodaccount, instellingen-toegang, instellingen-monitoring, inloggen-nood en kind-home,
op 360/390/768/1440 × licht/donker (Peil §12). Geen pixel-baselines.

---

## 8. Ontwerpbesluiten (ADR-vorm; over te nemen als volgend ADR-nummer door de webbouwer)

> Deze stap mag alleen `docs/ontwerp` en `design/` wijzigen. De besluiten staan daarom hier; de webbouwer neemt ze
> op als volgend vrij ADR-nummer in `docs/adr/` (nu ADR-0024; nummering is gedeeld tussen bouwers).

| # | Besluit | Keuze | Waarom |
|---|---|---|---|
| OB-01 | Merk | "TrueNAS Home Platform" linksboven (zijbalk + kop), ook in de kindschil; titel "<pagina> — TrueNAS Home Platform"; "Hub" blijft de naam van de centrale app; `short_name` "Home Platform" | besluit gebruiker O-07; één naam (WCAG 3.2.4) |
| OB-02 | Kindschil | aparte schil en routes `/`, `/kijken`, `/zoeken`, `/ik`; rest = kindvriendelijke 403; Kijken/Zoeken in P1 "komt later" | besluit gebruiker O-05; backend weigert kind al op beheerroutes |
| OB-03 | Niet-gezondheidstoestanden | neutrale pil (`status-neutraal`) voor Gekoppeld, Ingesteld, Aan/Uit, Draait, Geslaagd, Ingetrokken; `status-info` voor lopende processen | Peil regel 1: groen alleen "gemeten en goed"; een eenmalige test of koppeling is geen gezondheid |
| OB-04 | Zekerheid van regel-hypothesen | getal → woord (≥ 0,85 Zeker · ≥ 0,6 Waarschijnlijk · lager Onzeker · leeg Ik weet het niet); getal alleen in "Toon bewijs"; label "Hypothese (vaste regel)" | Peil T-24 (geen percentage zonder model); P1 heeft geen AI |
| OB-05 | Ernst (API 3 niveaus) | kritiek → Kritiek, waarschuwing → Middel, info → Info | vaste woorden behouden, rangorde gelijk; geen nieuw woord. Zie contract-issue |
| OB-06 | Totaalstatus | Storing > Beperkt > Deels onbekend > Gezond (Peil), in plaats van P0 `bad > unknown > warn` | Peil §4.3; een gemeten beperking is ernstiger dan een ontbrekende meting |
| OB-07 | TOTP zonder QR | handmatige sleutel + otpauth-URI als KopieerVeld; QR pas met een lokaal gebundelde, gepinde generator (eigen besluit van de webbouwer, geen externe dienst, geen afbeelding van internet) | CSP `default-src 'self'`; geen nieuwe afhankelijkheid zonder ADR |
| OB-08 | Volgorde Apps | slechtste status eerst via `limit=200` en sorteren in de UI; > 200 apps → op naam + melding | API sorteert op naam; status eerst (Peil principe 2) |
| OB-09 | Versheid-label | "Bijgewerkt" (Peil) in plaats van "Laatst bijgewerkt"; tests volgen | één woord overal (Peil §11) |
| OB-10 | Acties in P1 | zichtbaar maar `aria-disabled` met "Volgt in fase P2", **zonder** RisicoBadge ("risico bepaalt het beleid") | geen schijnbesluit van de policy; reden op de plek waar de gebruiker zoekt |
| OB-11 | Intrekken van een dienst | getypte app-id als bevestiging, in de pagina (geen kleine dialoog) | onomkeerbaar zonder opnieuw koppelen; Peil C-21-patroon |
| OB-12 | Instellingen-structuur | index + subpagina's met vaste subnavigatie ≥ 1024 | de P0-pagina wordt met P1 te lang; ankers krijgen een doorverwijzing |
| OB-13 | Iconen | `power` = aan/uit/draait; `plug-zap` = bron uitlezen/verbinding testen; `send` = testmelding; `unlink` = ontkoppelen; `shield-x` = intrekken; `life-buoy` = noodaccount; `fingerprint-pattern` = vingerafdruk | één icoon per betekenis (Peil §7) |
| OB-14 | Skiplink-tekst | de Hub houdt "Naar de inhoud" (bestaande test); de prototypes zeggen "Naar inhoud" — zelfde betekenis | minste churn in tests |

---

## 9. Controle-uitkomst van de prototypes (echt gedraaid)

- `node bouw/alles.mjs --shots --controle` (met `DATAVIZ_VALIDATOR`): **18 prototypes × 320/360/390/768/1024/1440 ×
  licht/donker**: axe 0 overtredingen, 0 tekstfouten, 0 overloop, 0 afgekapt, 0 doelen < 44 px, 0 bedekte focus, één
  h1 per pagina, geen kopsprongen, geen dubbele id's, geen kapotte `aria-*`-verwijzingen
  (`design/ontwerptaal/controle/samenvatting.txt`); laagste tekst in de nieuwe schermen 8,34:1 licht / 9,24:1 donker,
  behalve `server-metrieken` 4,56 / 5,01 = de bewust gedempte laatst-bekende waarde (`--stale-ink`, eis ≥ 4,5:1).
  `contrast.json`: harde fouten 0; brede matrix 367 paren per thema, 0 fouten.
- **Gevonden en hersteld tijdens de review:** gebruikerstabel 64 px te breed op 1024 (tabel nu pas ≥ 1280); knoppen in
  de kaartenlijst liepen 10 px over op 1024 (`flex-wrap`); GPU-small multiples stonden niet op één lijn (CSS `order`);
  dienstkaarten rekten mee in de rij (`items-start`); TOTP-stappen 2 en 3 stonden tegelijk open met "stap 2" als
  huidige (nu één stap "Authenticator-app en code"); live-regio's omvatten hele lijsten (nu alleen de samenvatting);
  "Uitgelezen"/"Aan" gebruikten het vinkje van "Geslaagd" (nu `power` voor aan/uit); vooringevulde naam in "Bron
  toevoegen" (formulieren starten leeg); "Draait" gebruikte het navigatie-icoon `server`.
- **Bekeken met Read:** `diensten`, `noodaccount`, `apps`, `appdetail-p1`, `server-metrieken`,
  `instellingen-toegang` (390), `instellingen-bronnen`, `kind` (360).
- **NIET GEVALIDEERD:** echte schermlezer (NVDA/TalkBack), echte Android-telefoon in fel licht, tv; de echte
  Hub-implementatie; gedrag tegen een echte NAS, Authentik, Uptime Kuma, Beszel of Gotify.

---

## 10. Hiaten en vervolg

**API/backend (voor de webbouwer of de backendbouwer):**

1. `issuer` in de otpauth-URI van het noodaccount → "TrueNAS Home Platform" (nu "AI Server Manager").
2. `GET /api/v1/apps?sorteer=status` (nu sorteert de UI zelf tot 200 apps).
3. Ernst kent drie niveaus (`info`/`waarschuwing`/`kritiek`), Peil vijf woorden — mapping OB-05; vastleggen in het
   contract of de API uitbreiden.
4. Poolstatus (ONLINE/DEGRADED/FAULTED) als veld naast `gezond`, zodat Beperkt mogelijk wordt.
5. Een lijst van **openstaande** koppelcodes/tokens (zonder geheim) zou de Diensten-pagina na herladen eerlijker maken;
   nu is een code na herladen niet meer te zien (dat is ook veilig: we tonen hem maar één keer).
6. CPU/geheugen per app en schijftemperatuur ontbreken (hiaten B09-001) → tegels blijven "Niet beschikbaar".

**Ontwerp:** na de webbouw een **ontwerpreview** (contract §13) op de echte schermen (360/390/768/1440, licht/donker,
axe, Tab-doorloop), en `ONTWERPTAAL.md` §0/§12 bijwerken naar 18 prototypes en 144 afdrukken (dat bestand valt buiten
deze stap). P2: `appdetail.html` (ActiePreview) en `goedkeuring-r3.html` worden dan de bron voor de acties.
