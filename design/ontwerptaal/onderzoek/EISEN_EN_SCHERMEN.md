# Ontwerptaal TrueNAS Home Platform V2 — eisen en schermen (onderzoek)

Status: onderzoek, versie 1 · 9 november 2026 · opgesteld door de ontwerp-agent
Plaats: `<werkmap ontwerp>/onderzoek/` (buiten de repos; niets in de repos gewijzigd)

Dit document is de **invoer** voor de ontwerptaal. Er staan nog geen kleuren, lettertypen of maten in: die volgen in de
volgende stappen (tokens, componenten, prototypes, ADR's). Hier staat wat de ontwerptaal **moet kunnen**:

1. alle schermen en flows van de Hub-UI over P0–P6 (§4 en §5);
2. de statuspagina's van de nieuwe diensten (§6);
3. alle terugkerende UI-toestanden en hun betekenis, met vaste Nederlandse teksten (§7);
4. de benodigde componenten: shadcn/ui-basis en platformspecifiek (§8);
5. de eisen voor toegankelijkheid en responsief gedrag (§9).

Daarnaast: de huidige stand en wat daaruit volgt (§3), wat de ontwerptaal voor de bestaande apps betekent (§10) en de
open ontwerpbesluiten die in ADR's moeten worden vastgelegd (§11).

---

## 0. Bronnen, reikwijdte en notatie

### 0.1 Gelezen bronnen (alleen lezen)

Pakket `ai-server-manager/docs/platform-v2/`:

- `README.md`, `00_START/LEES_MIJ_EERST.md`, `00_START/BESLUITEN_EN_ONBEKENDEN.md` (D01–D18);
- `PLATFORM_CONTRACTEN.md` (contracts 1.1, bindend);
- `01_ARCHITECTUUR/01`–`08`, en dan vooral `08_UI_EN_INTERACTIES`, `03_RISICO_AUTONOMIE`, `05_OPERATIES_EN_UPDATES` en
  `06_FASERING_EN_GATES`;
- `02_BOUWPLANNEN/B01`–`B15` (de schermlijsten, en per werkpakket "Gewenst gedrag", "Schermen/bediening" en "Acceptatie");
- `05_TESTS/INTEGRALE_E2E_TESTMATRIX.md` (EX01–EX50) en `GEBRUIKERSWENSEN_TRACEERBAARHEID.md`;
- `EXCEL_TAKEN.json` (55 taken voor ai-server-manager), `03_INSTALLATIE/I23`, `04_BESTAANDE_APPS/APP_REGISTER.md`;
- `OVERDRACHT/STATUS.md` (stand en het voorstel voor contract 1.2).

De huidige code (alleen gelezen):

- `ai-server-manager/apps/web`: de P0-schermen, `nav.ts`, de componenten, `globals.css`, CSP en ADR-0007/0009;
- de screenshots in `docs/screenshots/p0`;
- de statuspagina's: de executor (`apps/executor/src/executor/app.py`), home-control-hub, appstore-en-fork,
  jelly-leon-platform en zoeken-en-persoonlijke-ai;
- `home-control-hub/docs/runbooks/NOODTOEGANG.md`;
- de ontwerptalen van MediaGuard (`apps/web/styles/mg.css` en `docs/design/*`), MSO (`apps/web/styles/*`) en my_house
  (`apps/web/src/styles.css`).

Gebruikte skills:

- `design:design-system`: de opbouw van de componentinventaris;
- `design:accessibility-review`: de WCAG-eisenlijst;
- `design:ux-copy`: de NL-microcopypatronen;
- `design:design-critique`: kritiek op de P0-schermen;
- `dataviz`: grafiekvormen, stattegels en de regels voor tabelweergave. Grafiekkleuren zijn hier bewust nog **niet**
  gekozen.

### 0.2 Reikwijdte (besluiten van de gebruiker, vast)

| Valt onder de ontwerptaal | Valt er níet onder |
|---|---|
| De Hub-UI in `ai-server-manager` (Next.js 16 / React 19-PWA): alle schermen van alle nieuwe diensten | Jelly Leon web en de Jelly Leon-clients |
| De NL-statuspagina's (`GET /`, HTML zonder JS-framework) van home-control-hub, appstore-en-fork, jelly-leon-platform, zoeken-en-persoonlijke-ai en de executor | Interfaces van derden: Node-RED-editor, Authentik, Uptime Kuma, Beszel, AdGuard, NetAlertX, Immich, Seerr, arr-apps, SABnzbd, qBittorrent en TrueNAS zelf. De Hub verwijst daarnaar met een deep link. |
| Het **uiterlijk** van MediaGuard, MSO en my_house. Hun functies, routes en eigen UI-structuur blijven. | Functionele wijzigingen in MediaGuard, MSO of my_house |

Techniek (vast): Tailwind CSS 4, shadcn/ui (stijl new-york als basis, CSS-variabelen) en lucide-react. Niets via een
CDN of van internet; lettertypen zijn systeemfonts of worden lokaal meegeleverd. WCAG 2.1 AA is het minimum.

### 0.3 Notatie

- **E-xx**: bindende eis, met de bron tussen haken. Bijvoorbeeld [08_UI] = `01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md`,
  [§8] = PLATFORM_CONTRACTEN §8, [B01-003] = werkpakket, [EX19] = E2E-test.
- **S-xxx**: scherm, **F-xx**: flow (gebruikersreis), **T-xx**: UI-toestand, **C-xx**: component.
- **Fase** volgens `06_FASERING_EN_GATES` en de fasetoewijzing in de Hub-README: P0 inspecteren, P1 ogen en toegang,
  P2 veilig automatiseren, P3 eigen apps koppelen, P4 mediaplatform, P5 netwerk/persoonlijke AI/kosten, P6 oplevering.
- **Rollen** [§4]: `admin` (beheerder), `operator`, `viewer` (kijker) en `kind` (kinderprofiel).

---

## 1. Bindende eisen (samengevat en genummerd)

### 1.1 Taal en toon

- **E-01** De UI-taal is Nederlands, zonder taalkeuze [§1]. Foutmeldingen zijn in het Nederlands [B01 §1]. Technische
  codes (`app.restart`, `capability_unavailable`) blijven code en staan in een monospace-letter.
- **E-02** Getallen, datums en tijden volgen de NL-notatie. De API levert ISO-8601 UTC [§5]; de UI toont lokale tijd.
- **E-03** Het systeem legt "waarom" uit [01 §Kwaliteitsattributen]. "Ik weet het niet" is een geldige uitkomst [08_UI].

### 1.2 Eerlijke gegevens

- **E-04** Elke kaart toont waarde + eenheid + bron + **laatst bijgewerkt** en een duidelijke vervolghandeling [§1, 08_UI].
- **E-05** Onbekend is `unknown`, **nooit groen** [§1]. Er is geen fictief "alles groen" bij een onbekende status [08_UI].
- **E-06** Stale data is nooit gezond: een bron die langer dan de TTL niets levert, wordt `unknown` [B01-004, 05_OPS,
  P1-no-go "GUI toont oude data als gezond"].
- **E-07** Er staat nooit nepdata of een voorbeeldwaarde als echte waarde in de UI [README, ADR-0007]. Formulieren
  starten leeg; verplichte ja/nee-vragen hebben geen standaardantwoord.
- **E-08** Een ontbrekende functie is `capability_unavailable` of `unknown`, **nooit gesimuleerd succes** [§6].
- **E-09** Herkomst en meetkwaliteit staan bij elk getal: gemeten, afgeleid, geschat of onbekend [B01-011, B14-001,
  B10-004, B05-004]. Er is geen schijnprecisie. Twee voorbeelden: geen wattage uit CPU% zonder kalibratie, geen
  verbruik per airco-binnenunit.
- **E-10** "Verstuurd" is geen "klaar". Pas na **readback** zegt de UI "uitgevoerd" [§8, B06-002, B06-007].
- **E-11** Een geslaagde synchronisatie is geen herstelgarantie. "Back-up gezond" vraagt checksums, een hersteltest en
  recentheid [08_UI Backups, 03_RISICO §7, 04 §Gate].
- **E-12** Een voorspelling op minder dan 24 uur historie wordt niet verzonnen [B02-009]. Een besparing zonder meter
  wordt niet als bedrag in euro's getoond [B14-004].

### 1.3 Status en semantiek

- **E-13** Er zijn vier gezondheidsstatussen: `healthy` / `degraded` / `down` / `unknown` [§6]. Een status is **nooit
  alleen kleur** [opdracht, WCAG 1.4.1]: altijd ook een symbool en tekst.
- **E-14** De totaalstatus is nooit beter dan het slechtste onderdeel [ADR-0009 §3].
- **E-15** Een app die 200 teruggeeft maar geen jobs uitvoert, is `degraded` [B09-002]. Een bewuste pauze, zoals de
  AV1-pauze of de MediaGuard-noodstop, is "gepauzeerd" en geen storing [B02-003, B04-003].

### 1.4 Risico, acties en gates

- **E-16** Er zijn vier risicoklassen, R0–R3. De **policy** bepaalt de klasse; de claim van een AI of flow telt niet
  [§8, EX18]. Een risicobadge is "niet decoratief maar een onderbouwde categorie, met blokkadereden" [B02-005].
- **E-17** Vóór elke actie komen preview, risico, blast radius, verantwoordelijke, benodigde back-up, downtime,
  rollbackrecept en readback [03_RISICO §4, 08_UI Appbeheer]. Bij een installatie zijn alle hostpaden, netwerk- en
  GPU-rechten zichtbaar vóór de bevestiging [08_UI].
- **E-18** R0/R1 lopen automatisch binnen allowlist, cooldown en anti-flap. R2/R3 vragen menselijke goedkeuring **per
  gebonden diff**. Een goedkeuring verloopt na ≤ 15 min en vervalt als een gebonden veld verandert (drift, EX19). Een
  nonce werkt één keer (EX20) [§8].
- **E-19** Gates kun je niet wegklikken; er bestaat geen override [B12-006, ADR-0007]. R2/R3 zijn niet beschikbaar
  zolang de back-upgate rood is [08_UI].
- **E-20** Sommige blokkades gelden altijd, ook met goedkeuring [§8]:
  - boiler schakelen (EX27);
  - automatisch verwijderen van media, torrents, foto's of datasets;
  - policy of rollen wijzigen door de AI;
  - betaalde acties;
  - opslagmutaties bij een `DEGRADED`/onbekende pool of een rode back-upgate.

  `app.uninstall_data` wordt nooit door de AI aangeboden.
- **E-21** "Repareer" in de AI-chat leidt naar een actie-preview, nooit naar een terminal [08_UI]. Er bestaat geen
  vrij-tekstcommando [§8].
- **E-22** Een abortknop voorkomt nieuwe acties. De UI belooft niet dat een lopende OS-operatie stopt [03_RISICO §6].

### 1.5 Fouten

- **E-23** Een fout toont code + NL-melding + kopieerbare `trace_id` [opdracht, §5]. Geschoonde incidentgegevens zijn
  kopieerbaar [08_UI Toegankelijkheid, B09-004].
- **E-24** De UI toont nooit een geheim terug, alleen de laatste 4 tekens + datum [§3]. Logs en bewijs worden geschoond.

### 1.6 Rollen en toegang

- **E-25** De UI controleert rollen. Een viewer kan nooit updaten, stoppen of geheimen exporteren [B01-006, B13-004].
  Een kind ziet "alleen de eigen (media)weergave, nooit beheer" (code `Role.kind`). Bij het zoeken ziet een kind
  alleen bronnen met `kid_allowed` [EX36, EX43, B15-005].
- **E-26** Er is een noodlogin (break-glass) via LAN/VPN als Authentik uitvalt [B13-001, I23 stap 4].

### 1.7 Navigatie

- **E-27** Mobiel heeft een ondernavigatie met **Home, Apps, Problemen, AI en Meer**. Desktop heeft een zijbalk met
  **Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten en Instellingen** [08_UI]. De bestaande apps
  blijven via een deep link bereikbaar. De centrale kaarten werken zonder dat je de losse UI's opent.

### 1.8 Responsief, toegankelijk en PWA

- **E-28** Getest op 360/390/768/1440 px, licht/donker, toetsenbord + screenreader, touch targets ≥ 44 px, echte
  foutstates, offline/reconnect en NL. Daarnaast komt er een test op een Android-telefoon en een tv/speler [08_UI, B01 §1].
- **E-29** Elk scherm heeft minimaal [B01–B14 §1, "Per scherm minimaal"]:
  - de toestanden leeg, laden, storing en offline;
  - gedocumenteerde navigatie;
  - zoeken, filteren en pagineren;
  - een rolcontrole;
  - de datum van de laatste update en de bronherkomst;
  - een NL-fout, toetsenbordbediening en een zichtbaar auditspoor voor wijzigingen.
- **E-30** "Zero empty screens": geen dode schermen. Een latere fase toont eerlijk "Nog niet beschikbaar (volgt in
  fase Px)" [I23 stap 8, ADR-0009].
- **E-31** De service worker bewaart alleen de app-schil, nooit API-gegevens. Hij werkt pas via HTTPS of localhost
  [ADR-0009 §5].

### 1.9 Techniek en beveiliging die het ontwerp raken

- **E-32** De CSP van de Hub is `default-src 'self'`, `style-src 'self' 'unsafe-inline'` en `frame-ancestors 'none'`.
  Er zijn **geen externe bronnen**, dus geen CDN, geen webfont van internet en geen iframe-embedding van andere apps.
- **E-33** De CSP van de statuspagina's is `default-src 'none'; style-src 'unsafe-inline'; form-action 'self'`. Dat
  betekent: geen JS, geen externe CSS-bestanden, geen afbeeldingen, alleen inline `<style>` en inline `<svg>`. De
  formulieren gebruiken CSRF en een vaste lijst meldingen (geen weerspiegelde invoer).
- **E-34** Tot HTTPS er is (D17) draait de Hub via `http://<NAS-adres>:30400`. Dat is geen *secure context*, en dat
  heeft twee gevolgen:
  - `navigator.clipboard` en de service worker zijn niet beschikbaar;
  - de knop **Kopiëren** (trace_id, codes) heeft een terugvaloptie nodig.

---

## 2. Gebruikers en context

- **Hoofdgebruiker:** één thuisbeheerder (admin). Die werkt op een Android-telefoon (vaak), een tablet en een pc, en
  af en toe op de tv/speler (alleen Jelly Leon, niet in deze reikwijdte). Hij is technisch vaardig maar wil zonder
  terminal en zonder YAML werken [§1].
- **Huisgenoten:** de rol `viewer` (meekijken: storing? huis?) of `operator` (beperkt beheer).
- **Kinderen:** de rol `kind`, met een eigen mediaweergave en zoeken binnen toegestane bronnen. Nooit beheer.
- **Gebruiksmomenten:**
  - een snelle blik op de telefoon: "is er iets?";
  - een melding (Gotify) → incident → diagnose → goedkeuren, op de telefoon, vaak 's avonds of onderweg via VPN;
  - langer werk aan de pc: onboarding, installaties, back-ups en hersteltests;
  - in huis: klimaat, licht en energie.
- **Emotionele toestand bij fouten:** gespannen (data, storing). De toon is rustig, feitelijk en zonder alarmisme,
  maar risico's worden nooit verbloemd.

---

## 3. Huidige stand en bevindingen

### 3.1 Hub-UI (P0, `ai-server-manager/apps/web`)

**Techniek.** Next.js 16.4.5 en React 19.3.1, **zonder** CSS-framework of iconenbibliotheek, met eigen CSS-variabelen
en systeemfont [ADR-0009 §1]. De overstap naar Tailwind 4, shadcn/ui en lucide is dus een **migratie** van de
P0-schermen, geen kleine aanpassing.

**Bestaande schermen (P0):**

- `/eerste-start`, `/inloggen` en `/` (Home);
- `/onboarding`, `/onboarding/besluit/[Dxx]`, `/onboarding/truenas` en `/onboarding/executor`;
- `/server`, `/apps`, `/backups`, `/instellingen` en `/meer`;
- plaatshouders "Nog niet beschikbaar" voor `/problemen`, `/ai`, `/automatisering`, `/media`, `/huis`, `/netwerk` en
  `/kosten`.

**Bestaande componenten:** `StatusBadge` (symbool ✓ i ! ✕ ? – + tekst), `Freshness` (laatst bijgewerkt + bron),
`StatCard`, `ErrorPanel`, `NotYetAvailable`, `SchemaForm`, `PageHeader`, `TableWrap`, `Loading`, `ValueView` en `Field`.
De semantiek is goed en moet behouden blijven; alleen het uiterlijk verandert.

**Kritiek op de P0-schermen** (`design:design-critique`, op basis van de screenshots in `docs/screenshots/p0`):

| # | Bevinding | Ernst | Gevolg voor de ontwerptaal |
|---|---|---|---|
| K1 | Op 390 px wordt de gate-tabel van de onboarding ("Wat mag nu?") geknepen: de kolom met de reden is ±1 teken breed en onleesbaar. | Hoog | Tabellen worden onder 768 px een **lijst van kaarten** (C-34). Kerninformatie krijgt nooit een horizontale scroll of een geknepen kolom. |
| K2 | Een gate die alleen nog op invulwerk wacht, staat als rood "✕ Geblokkeerd", dezelfde stijl als een storing. Ook "Back-upgate: geblokkeerd" leest als een fout. | Middel | Er komt een aparte toestand **Gate dicht** (slot, neutraal/aandacht). Rood is alleen voor een gemeten falen (T-13). |
| K3 | "Actueel" krijgt een groen vinkje en ziet er dus uit als "gezond". | Middel | **Groen betekent alleen "gemeten en goed"**. Versheid is een eigenschap en geen gezondheid: neutrale tekst met tijd (T-02). |
| K4 | De mobiele kop besteedt de rechterbovenhoek aan "Uitloggen". | Laag | Uitloggen gaat naar een gebruikersmenu of naar Meer. De kop toont de context: paginatitel en verbindingsstatus. |
| K5 | Lange inleidende alinea's en een grote "Vernieuwen"-knop duwen de status op mobiel onder de vouw. | Middel | Status eerst: de systeemstatus staat bovenaan. Uitleg gaat in een korte ondertitel of achter "Meer uitleg". Vernieuwen wordt een icoonknop met label, en daarbij staat "laatst bijgewerkt". |
| K6 | Badges staan midden in lopende tekst ("(R2/R3-acties: ✕ Geblokkeerd)"). | Laag | Badges staan op vaste plekken (kaartkop of rij-einde), niet inline in zinnen. |
| K7 | Teksten als "D04 is Open; nodig: Ingevuld." zijn jargon-achtig. | Middel | Patroon: "**OneDrive-methode (D04)** — nog niet ingevuld. *Invullen*" (§7.3). |
| K8 | De productnaam in de kop is "AI Server Manager", terwijl de docs "Hub" en "Home Control Hub" gebruiken. | Laag | Open besluit O-07. |
| + | Wat goed werkt: status = symbool + tekst; bron en laatst bijgewerkt op elke kaart; eerlijk "onbekend" en "nog niet beschikbaar"; vaste navigatie volgens 08_UI. | — | Behouden en formaliseren. |

### 3.2 Statuspagina's van de nieuwe diensten

Er bestaan vier pagina's en één executorpagina, elk met **eigen, handgeschreven** CSS:

- home-control-hub en zoeken: dezelfde kaarten en tags;
- appstore: CSS-variabelen en secties;
- jelly-leon-platform: eigen variabelen;
- executor: minimaal, met een gele badge.

De labels verschillen per pagina ("gezond/beperkt/storing/onbekend" versus andere varianten). Ze moeten één gedeelde
sjabloon-CSS en één labelset krijgen (§6).

### 3.3 Bestaande apps (alleen uiterlijk)

| App | Techniek | Huidige ontwerptaal |
|---|---|---|
| MediaGuard | Next 16, Tailwind 4, shadcn (`components.json`: new-york, baseColor slate, cssVariables; maar slechts 3 ui-componenten), lucide 1.66, Inter + JetBrains Mono via fontsource (lokaal) | Eigen `mg.css`: donker als standaard, `data-theme` + `localStorage["mg.theme"]`, "Media Operations Control Center", AA-contrastrapport (82 combinaties), viz-tokens, AV1-lanetokens, sneltoetsen, dicht informatieontwerp. Er zijn 21 schermspecificaties (S1–S21). |
| MSO | Next 16, Tailwind 4, lucide, recharts 3.10, Inter + JetBrains Mono | Een afgeleide kopie van `mg.css` + `mso.css` (PROVENANCE.md) |
| my_house | Vite 5, React 18, react-router 7, vite-plugin-pwa, **geen Tailwind**, Inter + Space Grotesk (fontsource) | Eigen CSS-variabelen: warm gebroken wit, radius 18 px, domeintokens `heat`/`cool`/`boiler`/`light-on`/`stale`. Volgt alleen `prefers-color-scheme`. |

Een uitgebreide analyse van de bestaande UI's (contrastmetingen, statusvocabulaire, naamconflicten met de
shadcn-variabelen en een migratiestrategie) staat in het parallelle onderzoek `onderzoek/BESTAANDE_UI.md`. Dit document
herhaalt dat niet.

**Conclusie.** Er zijn drie verschillende stijlen: een donker controlecentrum, een warme huisapp en een sobere Hub. De
nieuwe ontwerptaal moet één familie vormen en tegelijk de **domeinbetekenissen** behouden: warmte/koeling, boiler,
GPU/CPU-lanes en integriteit.

---

## 4. Informatiearchitectuur en navigatie

### 4.1 Hoofdstructuur (vast volgens E-27)

| Plek | Mobiel en tablet (< 1024 px) | Desktop (≥ 1024 px) |
|---|---|---|
| Primair | Ondernavigatie: Home · Apps · Problemen · AI · Meer | Zijbalk: Home · Server · Media · Huis · Netwerk · Automatisering · Backups · Kosten · Instellingen |
| "Meer" | Een sheet met: Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten, Instellingen, Zoeken en Onboarding (zolang die nog niet af is) | — |
| Globaal (voorstel, vastleggen in ADR) | Kopbalk: paginatitel, verbindingsstatus, Zoeken (icoon), gebruikersmenu | Kopbalk: **Zoeken** (`/` of Ctrl+K), **Problemen** (teller), **Goedkeuringen** (teller), **AI** (opent de chat), gebruikersmenu (account, thema, uitloggen) |

**Toelichting.** Apps, Problemen, AI, Zoeken en Goedkeuringen staan niet in de vaste zijbalk. Op desktop moeten ze
toch met één klik bereikbaar zijn. ADR-0009 hangt Apps nu onder Server. Het voorstel (O-04) is: Apps blijft onder
Server (subnavigatie "Overzicht · Apps · Metrieken · Opslag · GPU · Logs"), en Problemen, Goedkeuringen, AI en Zoeken
komen in de kopbalk met tellers. Zo blijft de zijbalk exact zoals 08_UI hem voorschrijft.

**Kinderprofiel (`kind`).** Een eigen, beperkte schil met alleen Home (kindvariant), Media (eigen weergave) en Zoeken
(`kid_allowed`). Er is geen Problemen, AI-beheer, Server, Netwerk, Backups, Kosten of Instellingen (behalve "Mijn
profiel"). Zie O-05.

### 4.2 Routekaart (voorstel; de bestaande P0-routes blijven)

| Route | Scherm | Desktop-plek | Mobiel-plek | Fase |
|---|---|---|---|---|
| `/eerste-start` | S-001 | — (geen schil) | — | P0 |
| `/inloggen`, `/inloggen/nood` | S-002, S-003 | — | — | P0 / P1 |
| `/` | S-020 Home | Home | Home | P0 |
| `/onboarding/**` | S-010…S-016 | via Instellingen en Home-kaart | Meer | P0 (executor P2) |
| `/server/**` | S-030…S-038 | Server | Meer → Server | P0 inventaris, P1 live |
| `/apps/**` | S-040…S-049 | Server → Apps | Apps | P0 lijst, P2 acties, P5 appstore |
| `/problemen/**` | S-050…S-054 | kopbalk | Problemen | P1 |
| `/ai/**`, `/goedkeuringen/**`, `/acties/**` | S-060…S-075 | kopbalk | AI (goedkeuringen ook als badge op AI) | P2 |
| `/media/**` | S-080…S-088 | Media | Meer → Media | P3 / P4 |
| `/huis/**` | S-090…S-096 | Huis | Meer → Huis | P3 |
| `/netwerk/**` | S-100…S-106 | Netwerk | Meer → Netwerk | P5 |
| `/automatisering/**` | S-110…S-116 | Automatisering | Meer → Automatisering | P2 / P4 |
| `/backups/**` | S-120…S-129 | Backups | Meer → Backups | P0 dekking, P1+ |
| `/kosten/**` | S-130…S-134 | Kosten | Meer → Kosten | P2 credits, P5 |
| `/zoeken/**` | S-140…S-145 | kopbalk | Meer → Zoeken + kopbalkicoon | P5 |
| `/instellingen/**` | S-160…S-171 | Instellingen | Meer → Instellingen | P0+ |

---

## 5. Schermen en flows van de Hub-UI (P0–P6)

Per scherm staan doel, kerninhoud, acties (met risicoklasse), bijzondere toestanden, rollen, fase en bron. Algemene
eisen die voor elk scherm gelden (E-04, E-29) worden niet herhaald.

### 5.1 Toegang en eerste start

| ID | Scherm | Kerninhoud en gedrag | Bijzondere toestanden | Rollen | Fase · bron |
|---|---|---|---|---|---|
| S-001 | **Eerste start: setupcode → eerste beheerder** | Uitleg waar de code staat: *TrueNAS-web-UI → Apps → ai-server-manager → Logs*. Daarna een codeveld (groepen, plakken toegestaan) en het account (naam, wachtwoord met sterkte-uitleg). | Code onjuist of verlopen; te veel pogingen (429); er bestaat al een beheerder → doorsturen naar inloggen | publiek | P0 · §2, ADR-0004 |
| S-002 | **Inloggen** | Lokaal account. De knop "Inloggen met SSO" verschijnt pas als B13 actief is. Na inloggen alleen een interne terugsprong. | Sessie verlopen; Authentik onbereikbaar → verwijzing naar noodlogin; 429 | publiek | P0 / P1 · §4, B13-002 |
| S-003 | **Noodlogin (break-glass)** | Lokaal noodaccount, alleen via LAN/VPN. Toont de duur van de noodsessie en dat de sessie geaudit wordt. | Buiten LAN/VPN: "Niet beschikbaar vanaf dit netwerk" | publiek | P1 · B13-001, NOODTOEGANG.md |
| S-004 | **Sessie verlopen / opnieuw inloggen** | Een dialoog die waarschuwt vóór het verlopen ("nog 2 min — Verlengen"). Daarna opnieuw inloggen zonder dat ingevoerd formulierwerk verloren gaat. | — | alle | P0 · WCAG 2.2.1 |
| S-005 | **Geen toegang (403)** | "Je rol (*viewer*) kan dit scherm niet gebruiken." Plus een terugweg. | — | alle | P0 · B13-004 |
| S-006 | **Hub-API onbereikbaar / onderhoud** | `502 api_unavailable` of een Hub-update: wat er aan de hand is, de trace_id, en waar je anders kijkt (Uptime Kuma, Gotify, de TrueNAS-logs). | — | alle | P0 · ADR-0009, EX22 |
| S-007 | **Offline-pagina (PWA-schil)** | `offline.html`: "Geen verbinding met de Hub. Gegevens zijn onbekend tot de verbinding terug is." | Alleen bij HTTPS | alle | P0 · E-31 |

### 5.2 Onboarding en koppelen (P0, executor P2)

| ID | Scherm | Kerninhoud en gedrag | Bijzondere toestanden | Fase · bron |
|---|---|---|---|---|
| S-010 | **Onboarding-overzicht** | Voortgang in getallen ("5 van 18 getest · 12 open"). Stappen: (1) beheerder, (2) TrueNAS alleen-lezen, (3) besluiten D01–D18, (4) executor, (5) diensten. Daarna een lijst van de besluiten met status, en **"Wat mag nu?"** met de gates en hun reden. | Gates als kaartenlijst op mobiel (K1); onderscheid tussen gate dicht en gate onbekend | P0 · B01-001, ADR-0007 |
| S-011 | **Besluit Dxx (18 varianten)** | Titel + "wat leg je vast", de gate die ervan afhangt, de status (Open/Ingevuld/Getest/Geblokkeerd/N.v.t.) en de waardebron (gebruiker/meting/vast). Daaronder het **formulier uit het schema**, de knop **Meten** (D01, D02, D03, D06, D07, D08) en het bewijs (records met resultaat). Ook staat erbij wie/wanneer ingevuld en getest. Een wijziging na Getest zet de status terug op Ingevuld (waarschuwing vóór opslaan). | Plaatshouders geweigerd (`<POOL>`, `x.x.x.x`); D09 harde stop / geen overage verplicht (vaste bevestiging); D10 vast; D14 boiler alleen meten (vast); D05 vraagt een geregistreerde hersteltest van een foto én een database; ETag-conflict (409) | P0 · ADR-0007, BESLUITEN |
| S-012 | **TrueNAS koppelen (alleen-lezen)** | NAS-adres (uit D03), een alleen-lezen-API-key (geheim veld) en een verbindingstest. **De certificaatvingerafdruk bevestigen** (vergelijken, niet blind accepteren). Daarna inventaris en metingen. | Geen autorisatie → gerichte fout; vingerafdruk gewijzigd → blokkeren met uitleg; NAS offline → onbekend | P0 · B01-001, §8 |
| S-013 | **Executor koppelen** | Uitleg van de tweede Custom App. **Eenmalige koppelcode (30 min)** met aftelklok en kopieerknop. Instructie: open `http://<NAS-adres>:30410` en vul daar de code + de TrueNAS-schrijfkey in. De Hub wacht op de koppeling. Daarna: de identiteit (vingerafdruk), sinds wanneer, de laatste 4 tekens van de key (zoals de executor ze meldt), ontkoppelen/roteren (verwijzing naar de executorpagina). | Code verlopen → nieuwe code; executor onbereikbaar; in P0/P1 eerlijk "Koppelen volgt in P2"; **de Hub vraagt nooit zelf om de schrijfkey** | P0 uitleg, P2 werkend · §3 |
| S-014 | **Dienst koppelen (koppelcode)** | Voor een handmatig geïnstalleerde eigen dienst: kies de dienst, en de Hub maakt een eenmalige code. Instructie: open de statuspagina van de dienst. | Code verlopen of al gebruikt | P0 · §3 |
| S-015 | **Diensten installeren (vervolg-onboarding)** | Na de executor: de eigen diensten (appstore-en-fork, jelly-leon-platform, home-control-hub, zoeken) installeren via flow F-05. | Gate deployment dicht | P2 · §2 |
| S-016 | **Inventaris bevestigen** | "Gevonden: MediaGuard, MSO, my_house, …" alleen-lezen, zonder installatie of mutatie. Ontbrekende informatie moet je expliciet bevestigen. | Ontbrekend privilege → onbekend (niet overslaan) | P0 · B01-001 |

### 5.3 Home

| ID | Scherm | Kerninhoud en gedrag | Fase · bron |
|---|---|---|---|
| S-020 | **Home** | Bovenaan de **totale systeemstatus** (nooit beter dan het slechtste onderdeel) + **"Wat actie nodig heeft"** (geordend: storing > goedkeuring wacht > gate dicht > onboarding open). Daaronder een kaartraster: downloads/bibliotheek · GPU/AV1 · apps/uptime · huiscomfort/energie · veiligheid/back-ups · nieuwste acties (+ onboarding zolang die niet af is). Elke kaart volgt het kaartcontract (C-05). Automatisch vernieuwen (60 s) met zichtbare laatst-bijgewerkt-tijd. | P0 (kaarten worden per fase "echt") · 08_UI Home |
| S-021 | **Home (kindvariant)** | Alleen eigen media (verder kijken, verzoekstatus) en zoeken. Geen systeemstatus, geen beheertermen. | P3/P4 · E-25 |

### 5.4 Server en observability

| ID | Scherm | Kerninhoud | Bijzonder | Fase · bron |
|---|---|---|---|---|
| S-030 | **Server-overzicht (inventaris)** | Systeem (versie), pools, datasets, apps, GPU's, schijven/SMART, snapshottaken, TrueNAS-meldingen en netwerk. Alleen-lezen. | Per blok bron (`pool.query`, …) + tijd; NAS offline → alles onbekend | P0 · B01-001 |
| S-031 | **Metrieken (live dashboard)** | CPU (i7, threads), RAM/ZFS ARC, GPU (A310 en UHD 770 **apart benoemd**), schijven, netwerk en taken. Periodekiezer (1 u, 24 u, 7 d, 30 d) boven alles. Per metriek de herkomst en versheid. | Ontbrekende GPU-temperatuur is "onbekend" en **nooit 0 °C** [B09-001]; stale > TTL → gat in de grafiek + onbekend | P1 · B01-004, B09-003 |
| S-032 | **Opslag / ZFS** | Pools (status ONLINE/DEGRADED/…), scrub, vrije ruimte (meter), snapshotcapaciteit en schrijffouten. | Pool degraded → globale blokkade-banner voor opslagmutaties [EX11] | P1 · B09, D06 |
| S-033 | **GPU en werklast** | A310/UHD 770, lanes (AV1, transcode), wachtrij en **"waarom wacht AV1"** (stream heeft voorrang, back-up, scrub). | Bewuste pauze ≠ defect [EX07, EX08] | P1/P3 · B04-005, B14-003 |
| S-034 | **Services / uptime** | Per dienst up/down, latency, laatste 24 u, methode (buitenkant-URL / binnenkant-health / heartbeat) en een link naar de logs. | 200 zonder jobs = beperkt | P1 · B09-002 |
| S-035 | **Logs** | Zoeken op app, incident en tijd. Geschoond en in monospace. **Supportbundel kopiëren** (gemaskeerd). | Geheimen nooit zichtbaar; grote logs gepagineerd | P1 · B09-004 |
| S-036 | **Meetdekking** | Welke velden de TrueNAS-API en Beszel echt leveren, en welke onbekend zijn (matrix). | — | P1 · B09-001 |
| S-037 | **Werklastplanner** | Dagplanner: AV1, transcodes, zoekindex, back-ups en scrub, met de reden waarom een taak wacht. | — | P3/P5 · B14-003 |
| S-038 | **Prognoses** | Opslagtrend, poolcapaciteit en back-upverloop, met model + onderliggende meetwaarden en onzekerheid. | < 24 u historie → "Nog te weinig historie voor een voorspelling" | P2 · B02-009 |

### 5.5 Apps en appstore

| ID | Scherm | Kerninhoud | Acties (klasse) | Bijzonder | Fase · bron |
|---|---|---|---|---|---|
| S-040 | **Apps (lijst)** | Per app: status, uptime, versie + digest (ingekort, kopieerbaar), data-dataset, resourcegrenzen, eigenaar, beheerstatus (*Beheerd / Geïmporteerd / Niet beheerd*), voorgenomen besluit uit het app-register, deep link "Openen". Zoeken, filters (status, eigenaar, beheerstatus) en paginering. | Openen (deep link); Herstarten R1/R2 (alleen bij privilege) | App offline → stale tijd + onbekend, niet gezond [B01-002] | P0 lijst, P1 status, P2 acties · B01-002, B08-002 |
| S-041 | **Appdetail, tab Status** | Gezondheid + checks (naam, status, tijd, detail), uptime, laatste incidenten, eigenaar, documentatie en herkomst (repo, image, digest). | — | Verlopen credential → onbekend + incident [EX16] | P1 · 08_UI |
| S-042 | **Appdetail, tab Metrieken** | CPU/RAM/GPU per app en I/O, met periodekiezer. | — | Capability ontbreekt → C-12 | P1 |
| S-043 | **Appdetail, tab Logs** | Zoals S-035, gefilterd op de app. | Supportbundel kopiëren | — | P1 |
| S-044 | **Appdetail, tab Versies** | Huidige versie/digest, beschikbare versies, changelog, migratierisico, `tag_only_rollback_safe`, client-compatibiliteit (Jelly Leon) en canary-status. | Update R2; Terugzetten R2 (R3 bij DB-herstel) | DB-schema incompatibel → tag-only rollback **geblokkeerd** + volledig herstelplan (dataset + DB) [B01-010, EX15]; catalogusversie verdwenen (contract 1.2) | P2 · B01-010, B08-004 |
| S-045 | **Appdetail, tab Acties** | Een lijst van de toegestane acties met klasse, wat ze doen, de benodigde back-up, downtime en wie mag goedkeuren. Elke actie opent de actie-preview (S-061). | app.restart/stop/start R1/R2, update R2, rollback R2/R3, uninstall R2 | Gate dicht → actie zichtbaar maar geblokkeerd met reden; rol zonder recht → verborgen + rolmelding | P2 · 08_UI, §8 |
| S-046 | **Appstore-catalogus** | Goedgekeurde manifests: categorie, beschrijving en **transparante eisen** (image + digest, poorten, mounts, GPU, privileges + reden, SSO, back-up-RPO/RTO, risico per installeren/updaten/verwijderen) + `validation_status`. | Installeren → F-05 | Ongeldig manifest (privileged, Docker-socket, `latest`, hostpad `/`) → "Geweigerd" met de regel [EX47] | P5 (kern P2) · B08-001, §9 |
| S-047 | **Installatiewizard** | (1) app kiezen, (2) parameters (bron: wizard / datasetkiezer / geheim / gegenereerd / standaard; nooit een voorbeeldwaarde), (3) preflight (poortconflict, afhankelijkheden, gates, vrije ruimte), (4) **preview**: alle hostpaden, netwerk en poorten, GPU, privileges, image + digest, resources, geheimen (alleen namen), back-up en dataretentie, (5) risico R2 → goedkeuring, (6) uitvoering + voortgang, (7) readback + resultaat. | install R2 | Poortconflict of ontbrekende afhankelijkheid blokkeert [B08-003]; manifest geweigerd vóór uitvoering | P2 · B01-003, B08-003 |
| S-048 | **Verwijderen** | **Twee bevestigingsstappen.** Standaard alleen de container ("Data blijft bewaard op <dataset>"). Een herstelkaart: hoe je terugkomt. `uninstall_data` (R3) is een aparte flow met een eigen bevestiging en wordt nooit door de AI aangeboden. | uninstall R2; uninstall_data R3 | Wist nooit Immich-media of de MediaGuard-database [B08-006] | P2 · B08-006 |
| S-049 | **Forks en upstream** | Per fork: afwijkingen ten opzichte van upstream, CI/test-evidence, licentieverplichtingen (GPL-credits) en een merge-/rebasevoorstel. Bij Jelly Leon ook de **client-compatibiliteitsmatrix** (alleen-lezen beheer). | Voorstel → PR (buiten productie) | Falende patch stopt vóór productie | P4/P5 · B08-005, B03-001, B03-013 |

B08 noemt nog meer schermen: Toevoegen, Afhankelijkheden, Builds, Review, Rollback en Audit. Die zijn ondergebracht
in S-046 (toevoegen = manifest valideren), in S-047 (afhankelijkheden en preflight), in S-044 (versies, builds en
rollback), in S-049 (review) en in S-164 (audit).

### 5.6 Problemen en incidenten (P1)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-050 | **Problemen-inbox** | Eén inbox met per item: severity, titel, bron (app), eerste/laatste gebeurtenis, aantal onderliggende events (dedupe: "×100"), status (open / erkend / gesnoozed tot … / opgelost) en de verantwoordelijke app. Filters (severity, bron, status) en groepering op oorzaak. | 100 identieke crashes → één incident [B01-005]; geen pushstorm; een onbekende bron is zelf een incident | 08_UI, B01-005, B09 |
| S-051 | **Incidentdetail** | Tijdlijn van de events (tijd, bron, actor). **Oorzaakhypothese met zekerheid** + "Toon bewijs" (citaten naar logs en metrieken). Wat er al geprobeerd is (herstelreeks: aantal pogingen, cooldown, safe mode). Knoppen **Onderzoek** (AI-uitleg) en **Herstel voorstellen** (→ S-061). Deep link "Openen in MediaGuard/MSO". **Geschoonde incidentgegevens kopiëren.** | "Ik weet het niet" als hypothese; crashloop na 2 pogingen stopt [B02-007]; acties erkennen, snoozen en oplossen (R0) | 08_UI, B02-003, B02-007, B09-006 |
| S-052 | **Meldingsregels / out-of-band** | Prioriteitsregels voor Gotify en Uptime Kuma, plus **Testmelding sturen**. Uitleg: deze meldingen werken ook als de Hub uitvalt. | Hub offline → verwijzing naar UK/Gotify [EX22] | B09-005 |
| S-053 | **Eventbezorging en dead letters** | Per bron: outbox-achterstand, retries en dead letters (zichtbaar volgens §7), plus de onbekende schemaversies [B11-002]. | Een event mag niet stil verdwijnen | §7 |
| S-054 | **Runbooks** | Per storingstype: observeren → isoleren → mitigeren → terugdraaien → bewijs → oorzaak. Gekoppeld aan incidenten. | — | 05_OPS, B09-006 |

### 5.7 AI, acties en goedkeuring (P2)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-060 | **AI-chat** | Gesprek met **bronnen/citaten** per bewering, twijfel ("zeker/waarschijnlijk/onzeker"), **"Ik weet het niet"** + wat er nodig is om het te weten. Een plan in stappen met per actie de status. Knoppen: *Bekijk voorstel* (→ S-061), *Goedkeuren/Weigeren* (alleen in de gebonden context). Bovenaan: model/provider, **tegoedindicator**, privacy (wat naar de cloud gaat) en de spraakknop (P5). | 0 tegoed → "Cloudmodel uit (harde stop). Regels zonder AI blijven werken." [EX21]; prompt-injectie in logs heeft geen effect [EX17] (de UI toont logtekst altijd als geciteerde data, nooit als instructie); kind/viewer: alleen R0 | B01-009, B02-001/002/004, 08_UI |
| S-061 | **Actie-preview** (gedeeld: vanuit apps, incidenten, chat, flows en spraak) | `action_id` (code), doel, parameters, **risicoklasse volgens de policy** + regels (`rule_ids`) + "AI stelde voor: R0 → beleid: R3" als die afwijken. **Diff**, blast radius, downtime, precondities (ETag/digest), **back-up-checkpoint**, rollbackrecept, vervaltijd, verantwoordelijke en uitvoerder (executor of eigenaar-connector). Knoppen: *Simuleren* (dry-run) · *Uitvoeren* (R1) · *Goedkeuring aanvragen* (R2/R3). | Onbekend action_id → 422 "Deze actie bestaat niet in de allowlist" [B02-004]; gate dicht → C-11; altijd geblokkeerd (boiler, auto-delete) → "Wordt nooit uitgevoerd" | §8, 03_RISICO §4, B02-004 |
| S-062 | **Goedkeuringen (lijst)** | Openstaande verzoeken met klasse, doel, aanvrager (gebruiker/AI/flow/spraak), **verloopt over mm:ss**, status. Tellers in de kopbalk en op het AI-icoon. | Vervallen (tijd), vervallen (drift), geweigerd, uitgevoerd | B01-007 |
| S-063 | **Goedkeuring (detail)** | Alles uit S-061 + de **gebonden velden** (preview_hash, resource_etag, policy_hash), concrete herstelpunt-ID's [B12-006] en de gate-status. *Goedkeuren* / *Weigeren* (met reden). **R3**: een aparte tweede stap met het doel overtypen ("typ `<appnaam>` om te bevestigen") + de expliciete gevolgen. | Drift → "**Goedkeuring vervallen**: <veld> is gewijzigd na de preview. Vraag een nieuw voorstel aan." [EX19]; dubbel indrukken → één uitvoering [EX20, B05-009]; mobiel = volledige pagina, geen modale dialoog | §8, B01-007, B12-006 |
| S-064 | **Uitvoering / verloop** | Stappen (gecontroleerd → uitgevoerd → readback), voor/na-toestand en -hash, duur. Bij een afwijking **gestopt + incident**. Knop **Afbreken**: "voorkomt nieuwe stappen; een lopende TrueNAS-bewerking kan doorlopen". | Herstart tijdens uitvoering → status hervat of onbekend | B02-006, 03_RISICO §6 |
| S-065 | **AI-overzicht** | Providerkaart: tegoed (inbegrepen, verbruikt, bron, tijd), harde stop, model, kosten per taak, lokale terugval, status van de lokale modellen (optioneel, standaard uit). | Tegoed onbekend → cloud uit tot bekend | B02-001, D09 |
| S-066 | **Risicobeleid (alleen lezen)** | Policyregels per action_id, klasse, cooldowns en blokkades. `policy_hash` + versie. Uitleg: "Het beleid kan niet door de AI worden gewijzigd." | Geen bewerkknoppen in de UI | §8, B02-005 |
| S-067 | **Taken** | AI- en achtergrondtaken: status, duur, resultaat en bewijs. | — | B02 §1 |
| S-068 | **Audit (globaal)** | Wie/wat/wanneer/bron/actor-type (systeem / gebruiker / AI / flow), met filters en export (geschoond). | — | B02 §1, §7 |
| S-069 | **Veiligheidsdashboard / evaluatie** | Laatste red-team- en policytests (adversarial, secrets-lekken, replay, drift) met bewijs, en de release-blokkade bij een kritieke fout. | — | B02-011 |
| S-070 | **Noodstop** | Een globale stop van nieuwe acties (Hub), plus de status van de MediaGuard-noodstop (gerespecteerd, niet omzeild). Een globale **gepauzeerd-balk** met oorzaak, sinds, door wie en de laatste heartbeat. | Opheffen vraagt een bevestiging | B02 §1, B04-003, EX06 |
| S-071 | **Aanbevelingen** | Lessen uit incidenten: aanbeveling, gemeten effect en "verwijder feedbackdata". | De AI verlaagt nooit zelf een grens | B02-012 |
| S-072 | **Voorstel voor code/config** | Een PR-voorstel met test-evidence, veiligheidsimpact en diff. Uitrol alleen na goedkeuring, back-up en canary. | Falende tests → geen merge/deploy | B02-008 |
| S-073 | **Automatiseringsvoorstel van de AI** | "Wanneer X, dan Y" + testevents + overschrijfknoppen → sandbox → goedkeuring. | Een flow met exfiltratie of destructieve actie wordt geweigerd | B02-010 |

### 5.8 Media (P3/P4)

Media is een Hub-overzicht over MediaGuard (bibliotheek, selectie, import, AV1), MSO (bronnen) en Jelly Leon
(afspelen, alleen via deep link).

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-080 | **Media (5 tabs: Film · Serie · Anime · Muziek · Live TV)** | Per tab: verder kijken, mediakwaliteit, downloads en verzoekstatus. Afspelen = deep link naar Jelly Leon. | MediaGuard offline → onbekend, MSO blijft (en andersom) [EX01, EX02] | 08_UI Media |
| S-081 | **Titel/aflevering** | Status, kwaliteit, bestanden (alleen lezen), **"Waarom ontbreekt dit?"**: de diagnoseketen MediaGuard → releasekandidaten → MSO-bronstatus → clientfout → import/vervangroute, met reden en bron. Knop "Vraag aan / zoek betere versie" (via de MediaGuard-actie). | Geen tweede downloader; noodstop → knop geblokkeerd met reden | B04-004, B03-009 |
| S-082 | **Downloads** | Wachtrij (alleen lezen) van SABnzbd/qBittorrent via MediaGuard/MSO. Per mislukking: de oorzaak, de bewijsbron, de laatste poging en een veilige vervolgstap. | Geen torrent-delete uit de Hub; de categorie-`*`-diagnose (MSO) | B05-002, B05-003, 02_DATA |
| S-083 | **MediaGuard-status** | Noodstop, AV1-lanes (GPU/CPU), wachtrij, quarantaine-bezetting, en de compatibiliteit met MSO. | Gepauzeerd ≠ storing | B04-002/003/005 |
| S-084 | **MSO-status** | Autopilotmodus, **"Wat MSO deed / Wacht op jou"**, providerhealth en de compatibiliteitsmatrix met de ontbrekende route. | Een provider zonder statistieken is onbekend | B05-005/006 |
| S-085 | **Live TV** | Tunerstatus, gids (samenvatting), geplande opnames en een **overlapwaarschuwing** (alleen lezen). Kijken en plannen doe je in Jelly Leon. | — | 08_UI, B03-012 |
| S-086 | **Jelly Leon-beheer** | Versie, upstreambasis, client-compatibiliteit (D15), transcode-lanes (A310/UHD 770) en het updatecentrum (→ S-044). | Staging moet dezelfde of een betere clientcompatibiliteit hebben [08_UI] | B03-001/004/013 |
| S-087 | **Media (kindvariant)** | Alleen toegestane titels, verder kijken en verzoekstatus. Geen technische termen. | Geen geblokkeerde titels in resultaten of thumbnails [EX36] | E-25 |

### 5.9 Huis (P3)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-090 | **Huis (per kamer)** | Een kamerkaart met verlichting, actuele temperatuur, luchtvochtigheid, temperatuurdoel, snelle bediening (volgens rol), energie, **sensorversheid** en waarschuwingen. my_house is de eigenaar; de Hub delegeert. | my_house offline → laatst bekende waarden gemarkeerd als verouderd, **geen bediening** [B06-006, EX24] | 08_UI Huis |
| S-091 | **Kamerdetail** | Apparaten, sensoren, historie (dag) en meldingen. | — | B06 §1 |
| S-092 | **Klimaat (Gree-zones)** | Per zone: modus, doel, actieve sensor, versheid, **handmatige override** (afstandsbediening: "Blijft uit tot je hervat") en de **blokkadereden**. De gedeelde buitenunit maakt een conflict tussen verwarmen en koelen mogelijk; dat staat er als **expliciet geblokkeerd** (409). | Adapter niet ondersteund → "Bediening niet ondersteund" en nooit schijnbediening [EX30]; een stale Zigbee-sensor stopt de optimalisatie [EX29]; bediening alleen na D12 | B06-004, EX25/26 |
| S-093 | **Energie (huis)** | P1-totaal, **boiler (alleen meten)**, airco-1-fasemeter. Dag/week/maand/jaar, prijs, verbruiksbron, gemeten tegenover geschat, en een kwaliteitslabel bij een meterreset of zomertijd. | **Boilerkaart zonder schakelknop**, met het label "Alleen meten — schakelen is uitgeschakeld" [EX27]; geen verbruik per binnenunit | B06-003/005, B14-002, EX28 |
| S-094 | **Apparaten en sensoren** | Per apparaat: compatibel / getest / niet ondersteund + datum, een testknop per adapter met feedback, en de readbackstatus. | Zonder readback nooit "uitgevoerd" | B06-001/002 |
| S-095 | **Verhuizen / aanpassen** | Deep link naar my_house (eigen UI). De Hub toont alleen de status van een droogtest. | — | B06-008 |
| S-096 | **Huisbediening via AI/spraak** | De bevestigde apparaatstatus. Klimaatacties met grote impact vragen goedkeuring; de boiler wordt geweigerd. | — | B06-007, B15-003 |

### 5.10 Netwerk (P5)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-100 | **Netwerk-overzicht** | Topologie (lijst eerst, optioneel een diagram): subnetten, gateway, DNS en de status van de VPN/tunnel. | — | B10-001 |
| S-101 | **Apparaten** | Eerst/laatst gezien, fabrikant + zekerheid, IP/MAC-historie, onbekende namen, en een melding bij een nieuw apparaat. | **Geen malwareclaim zonder bewijs** [EX33]; een andere IP met dezelfde MAC is hetzelfde apparaat | B10-002 |
| S-102 | **DNS (AdGuard)** | Status, de meest geblokkeerde categorieën, uitzonderingen, de pilot op één testclient en de **terugvalroute** (getest ja/nee). | DNS-cutover gate (D11); rollback-test [EX31, EX32] | B10-003 |
| S-103 | **Verkeer per app** | Uitgaande bestemmingen en bandbreedte: **geobserveerd / geschat / niet beschikbaar**. | Afwezig in DNS ≠ geen verkeer | B10-004 |
| S-104 | **VPN en tunnel** | Tailscale-sessies, Cloudflared-health, certificaten en vernieuwingsmeldingen. | Token ingetrokken → geen externe admin, lokaal werkt [EX34] | B10-005 |
| S-105 | **Verdachte signalen en firewallvoorstel** | Bewijs + risico per voorstel. WAN- en firewallregels zijn **R3** en vragen een test vanaf een onafhankelijke verbinding + een automatische terugval. | Geen LAN-afsluiting zonder goedkeuring | B10-006, 03_RISICO |
| S-106 | **Rechten** | Wie mag wat zien en wijzigen op het netwerk. | — | B10 §1 |

### 5.11 Automatisering (P2/P4)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-110 | **Flows (overzicht)** | Per flow: status (actief / gepauzeerd / fout), trigger, laatste uitvoering, aantal acties en de goedkeuringsvereiste. **Pauzeren** (R1). | — | B11 §1, B01-008 |
| S-111 | **Flowdetail** | Triggers (eventtype + schema), acties met per node de **goedkeuringsvereiste en klasse**, en versies. Knop *Openen in Node-RED* (eigen editor achter SSO, deep link). | Verboden node (exec, boiler) → geweigerd met reden [EX45]; de viewer bereikt de editor niet | B11-001/003 |
| S-112 | **Testmodus / dry-run** | Events opnieuw afspelen in de testmodus, met runlog, uitzonderingen en impact. "Er zijn geen echte apparaten gewijzigd." | — | B11-004 |
| S-113 | **Eventtypen-catalogus** | Een keuzelijst van gebeurtenissen met een voorbeeldschema en de bron-app. | Onbekende schemaversie is zichtbaar | B11-002 |
| S-114 | **Uitvoeringshistorie** | Runs, resultaat, idempotentie (een dubbel event leidt tot één actie [EX46]) en de traceerlink. | — | B11 §1 |
| S-115 | **Versies en herstel** | Een diff tussen versies en herstellen (zonder geheimen in de log). | — | B11-005 |
| S-116 | **Sjablonen** | Veilige startpunten, bijvoorbeeld "melding bij back-upfout". | — | B01-008 |

### 5.12 Backups en herstel (P0+)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-120 | **Backups (overzicht)** | De **back-upgate** (toegestaan / dicht / onbekend) met de reden per voorwaarde en een link om die op te lossen. Daaronder de **dekkingsmatrix** per app/dataset: lokale snapshot · OneDrive · consistente DB-export · laatste hersteltest, en de back-up van de Hub zelf. | "Synchronisatie geslaagd ≠ herstelgarantie"; de gate is niet weg te klikken | 08_UI Backups, B12, ADR-0008 |
| S-121 | **App/dataset-detail** | Herstelpunten (ID, leeftijd, soort, consistent ja/nee), RPO/RTO (D16) en de laatste hersteltest. | Een snapshot zonder DB-consistentie telt niet als volledige back-up [B12-002] | B12-002/003 |
| S-122 | **Snapshotplanning** | Beleid per dataset, retentie, ruimtebudget, en de snapshot vóór een deployment of schema-update. | — | B12-002 |
| S-123 | **Offsite (OneDrive)** | Tijdstip, aantal, bronkaart, fouten en versleuteling. | Verlopen auth of een stale upload → een incident met hoge prioriteit | B12-004 |
| S-124 | **Hersteltests** | Resultaat geslaagd / gedeeltelijk / mislukt, met bewijs (checksums, DB-integriteit). **Nieuwe hersteltest** (sandbox, R1). | Productie wordt nooit overschreven | B12-005, EX13/14 |
| S-125 | **Herstellen (wizard)** | Kies een herstelpunt → kies het doel (sandbox eerst) → preview → R2/R3 → uitvoering via de **data-eigenaar** → readback. | — | 03_RISICO §7 |
| S-126 | **Sleutels** | Herstelsleutels en escrow-status (nooit de waarden), met de plek en de datum. | — | B12 §1 |
| S-127 | **Rampenscenario's** | Herstelstappen per scenario (poolverlies, gelekte credential, mislukte migratie, verhuizing) en de laatste oefening. | — | B12-007 |
| S-128 | **Exporteren en verhuizen (Hub)** | Een versleutelde export en een herstelwizard met **droogtest** ("alles aanwezig?"). | Geen dubbele apps; audit blijft | B01-012 |
| S-129 | **Kosten en opslag van back-ups** | Groei per datasoort en retentie. | — | B12 §1 |

### 5.13 Kosten en energie (P2 tegoed, P5 rest)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-130 | **Kosten (overzicht)** | AI-tegoed (inbegrepen / verbruikt / harde stop), externe diensten (MSO-providers), energie (NAS: exact alleen met een eigen meter) en budgetwaarschuwingen. | Geen dubbeltelling; onbekend blijft onbekend | B01-011 |
| S-131 | **Verbruiksbronnen / dekking** | Een herkomst- en kwaliteitslabel per getal: gemeten / afgeleid / geschat / onbekend. | — | B14-001 |
| S-132 | **Energietijdreeks** | Dag/week/maand, tarief vast of dynamisch, en dagen met 23/25 uur. | — | B14-002 |
| S-133 | **Vergelijken en prognose** | Aannames + een besparingsbereik, "niet gegarandeerd". | Zonder meter geen bedrag in euro's | B14-004 |
| S-134 | **Afwijkingsmeldingen** | Meter offline, ongebruikelijk boilerverbruik en een overschreden budget. | De boiler blijft alleen meten | B14-005 |
| — | MSO-kostensimulatie | "Wat als ik provider X stop": een bereik met betrouwbaarheid. Deep link naar MSO. | — | B05-008 |

### 5.14 Zoeken (P5)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-140 | **Zoeken** | Een zoekbalk + filters (type, bron, datum, score). Resultaten met bronlink, fragment en reden. Ook bereikbaar via de globale zoekfunctie (C-51). | ACL vóór de ranking: geen lek van titel, thumbnail of bestaan [EX43] | B07-003 |
| S-141 | **Zoek een moment** | Media: een tijdcode + deep link naar de speler op dat moment. | **Geen verzonnen tijdcodes** zonder transcript [B07-004] | B07-004, B03-008 |
| S-142 | **Antwoord met citaten** | Een AI-antwoord alleen uit toegestane passages, met bronnen en onzekerheid. | "Ik weet het niet" als niets relevant is | B07-005 |
| S-143 | **Bronnen en toestemming (wizard)** | Opt-in per bron (media, documenten, Immich-metadata, logs), paden, scopes, `kid_allowed`, privacydekking. Alleen de eigenaar geeft toestemming. | Een niet-geselecteerde share indexeert niets | B07-001 |
| S-144 | **Indexstatus** | Laatste run, mislukte bestanden en voortgang. | — | B07-002 |
| S-145 | **Privacy en opschonen** | "Verwijder mijn indexdata", een bron intrekken (purge met bevestiging) en een privacyrapport. | Het origineel blijft onaangeroerd [EX44] | B07-006 |

### 5.15 Spraak (P5)

| ID | Scherm/onderdeel | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-150 | **Spraak in de AI-chat** | **Ingedrukt houden om te praten** (standaard; geen permanente luisterstand). Toestemming per browser. Een privacy-indicator: *lokaal* / *cloud (opt-in)*. Het transcript wordt eerst ter bevestiging getoond. TTS staat aan/uit, er is een mute-knop en geen automatisch afspelen. | Microfoon geweigerd → getypte invoer [B15-001]; foute herkenning van "verwijder dataset" blijft tekst en wordt geen actie [EX49]; STT/TTS-app niet geïnstalleerd → capability_unavailable | B15-001…004 |
| S-151 | **Spraakgeschiedenis en privacy** | Opnamegeschiedenis staat standaard **uit**. Sessie verwijderen wist de transcripts. Er wordt geen audio bewaard. | — | B15-006 |
| S-152 | **Context en apparaten** | De kamer, het profiel en het apparaat als context, met expliciete toestemming, vervaltijd en intrekken. | Kind/viewer: geen admin-doelen | B15-005 |

### 5.16 Instellingen (P0+)

| ID | Scherm | Kerninhoud | Bijzonder | Bron |
|---|---|---|---|---|
| S-160 | **Account** | Naam, wachtwoord, thema (Systeem / Licht / Donker), eigen sessies en uitloggen. | — | P0 |
| S-161 | **Gebruikers en rollen** | Gebruikers, rol (beheerder / operator / kijker / kind) met per rol een uitleg van wat die mag, uitnodigen, deactiveren en sessies intrekken. | Rolwijziging door de AI kan niet | B01-006, B13-004 |
| S-162 | **Kinderprofiel** | Per kindaccount: toegestane mediabronnen en zoekbronnen (`kid_allowed`). Het profiel kan nooit beheren. | Leeftijdsfilters en pincodes horen bij Jelly Leon (buiten de reikwijdte) | E-25 |
| S-163 | **SSO (Authentik)** | Status/health, de provider, inloggen via SSO, de **SSO-dekkingsmatrix per app** (OIDC / eigen login / geen), groepen naar rollen, MFA-status, sessies en audit. | Geen aanname dat OIDC bestaat [B13-003]; geen toegang via een onbeveiligde header | B13-002…005 |
| S-164 | **Auditspoor** | Het globale auditspoor (= S-068) in de context van instellingen. | — | P0 |
| S-165 | **Toegang → Herstel** | Het herstelregister (accounts + soort login), het noodaccount, noodtoegang (CIDR-bereiken LAN/VPN en de duur van een noodsessie, 5–240 min), MFA bevestigen, de **herstelkit** maken en controleren, de **zelftest**, en een oefening registreren. Status ok / risico / onbekend. | Nooit wachtwoorden of codes invoeren; een internetbereik wordt geweigerd | B13-001, NOODTOEGANG.md |
| S-166 | **Diensten** | Het dienstenregister: eigen diensten met versie, adres, koppelstatus, laatste contact, token roteren, ontkoppelen en een koppelcode maken (→ S-014). | — | §3 |
| S-167 | **Koppelingen met bestaande apps** | Credentials (MediaGuard-`X-Api-Key`, my_house-token, TrueNAS-alleen-lezen-key, …): de vault-referentie, de laatste 4 tekens + datum, testen en roteren. | De waarde wordt nooit teruggetoond | §3 |
| S-168 | **Meldingen** | Gotify-koppeling en voorkeuren (= S-052). | — | B09-005 |
| S-169 | **Apparaat en PWA** | Status van de offline-schil ("niet actief zonder HTTPS"), installeren als app en een snelkoppeling op het startscherm. | — | ADR-0009 §5 |
| S-170 | **Over deze Hub** | Versies van de Hub, executor en diensten, digests, de **validatiestatus** (Sim-getest / NIET GEVALIDEERD …), licenties en upstream-credits (GPL voor Jelly Leon). | — | §11 |
| S-171 | **Onboarding** | Een snelkoppeling naar S-010 (op desktop vanuit Instellingen). | — | ADR-0009 §6 |

### 5.17 Primaire flows (gebruikersreizen)

De Definition of Done eist een E2E-test per primaire reis (01 §DoD). Flows met een R2/R3-stap lopen altijd via
S-061 → S-063 → S-064.

| ID | Flow | Stappen (schermen) | Fase |
|---|---|---|---|
| F-01 | **Eerste installatie** | De gebruiker maakt 2 Custom Apps in TrueNAS (buiten de Hub) → S-001 setupcode → beheerder → S-010 → S-012 TrueNAS (vingerafdruk) → S-011 besluiten → S-013 executor (koppelcode → executorpagina → terug) → S-015 diensten | P0–P2 |
| F-02 | **App openen** | Home/Apps → S-040 → deep link (eigen UI; een nieuw tabblad wordt aangekondigd) | P0 |
| F-03 | **Incidentdiagnose** | Gotify-melding → S-050 → S-051 (hypothese + bewijs) → *Onderzoek* (S-060) → *Herstel voorstellen* (S-061) | P1–P2 |
| F-04 | **Goedkeuren (R2/R3)** | Melding of teller → S-062 → S-063 (diff, herstelpunt, aftelklok) → Goedkeuren (R3: tweede stap) → S-064 → readback → klaar of incident | P2 |
| F-05 | **App installeren** | S-046 → S-047 (parameters → preflight → preview) → F-04 → S-064 → S-040 | P2/P5 |
| F-06 | **Update en terugzetten** | S-044 → preview (migratierisico, herstelplan) → F-04 → health-venster → bij een fout: terugzetten (tag-only geblokkeerd bij een DB-wijziging) | P2 |
| F-07 | **Back-up verifiëren** | S-120 (gate) → S-124 *Nieuwe hersteltest* (R1) → resultaat met bewijs → gate herberekend | P0–P1 |
| F-08 | **Herstellen** | S-121 → S-125 (sandbox eerst) → F-04 → eigenaar voert uit → readback | P1–P2 |
| F-09 | **Media zoeken / ontbrekende aflevering** | S-080 → S-081 *Waarom ontbreekt dit?* → MediaGuard/MSO-context → *Vraag aan* (MediaGuard-actie) | P3 |
| F-10 | **Apparaat lezen en bedienen** | S-090 → kamer → bedienen → "Verstuurd — wacht op bevestiging" → "Bevestigd" of "Niet bevestigd" | P3 |
| F-11 | **AI-vraag met actie** | S-060 vraag → antwoord met citaten → plan → S-061 → R0/R1 direct, R2/R3 via F-04 | P2 |
| F-12 | **Spraakopdracht** | S-150 ingedrukt houden → transcript bevestigen → S-061 (nooit automatisch) | P5 |
| F-13 | **SSO inrichten** | S-165 herstel eerst (noodaccount + kit) → S-163 OIDC → test-login → dekkingsmatrix | P1 |
| F-14 | **Noodtoegang** | Authentik weg → S-002 → S-003 noodlogin (LAN/VPN) → herstellen → rotatie registreren | P1 |
| F-15 | **Dienst handmatig koppelen** | S-166 → S-014 code → statuspagina van de dienst (§6) → koppelstatus in de Hub | P0 |
| F-16 | **Zoekbron toevoegen / intrekken** | S-143 opt-in → S-144 indexstatus → S-145 intrekken (purge-bevestiging) | P5 |
| F-17 | **Kind kijkt** | Inloggen (kind) → S-021 → S-087 → afspelen via deep link | P3/P4 |
| F-18 | **Verhuizen van de Hub** | S-128 export → nieuwe host → herstelwizard + droogtest | P6 |

---

## 6. Statuspagina's van de nieuwe diensten (`GET /`)

### 6.1 Welke pagina's

| Dienst | Poort | Bijzondere inhoud |
|---|---|---|
| `ai-server-manager-executor` | 30410 | **Koppelformulier: koppelcode + TrueNAS-API-key met schrijfrechten**. Daarna alleen de laatste 4 tekens. Ontkoppelen/roteren. De allowlist (lijst met action_id's; in P0 leeg = "voert niets uit"). Het gevoeligste formulier van het platform. |
| `home-control-hub` | 30420 | Integraties (B10/B11/B13/B14) op totaalniveau en het niveau van beheerherstel (ok / risico / onbekend; details alleen in de Hub) |
| `appstore-en-fork` | 30430 | Catalogusbronnen (bron, soort, status, laatste synchronisatie) |
| `jelly-leon-platform` | 30440 | "Wat deze versie wel en niet doet" (de lifecycle-uitvoering volgt in P2 via de executor) |
| `zoeken-en-persoonlijke-ai` | 30450 | De status van B07 (zoekmachine) en B15 (spraak/AI), zonder bronnamen of aantallen die privé zijn |

### 6.2 Vaste opbouw (één sjabloon voor alle diensten)

1. **Kop:** dienstnaam (NL) + een omschrijving van één zin + "Onderdeel van TrueNAS Home Platform".
2. **Statusblok:** de gezondheid (gezond / beperkt / storing / onbekend) met symbool + tekst, de checks (naam, status,
   tijd), "gereed / niet gereed" (readyz), de **versie** en **bron + laatst bijgewerkt**.
3. **Koppeling met de Hub:** niet gekoppeld / gekoppeld (sinds, met welke Hub, als adres + vingerafdruk) / koppelen
   mislukt (de reden uit een vaste lijst).
4. **Koppelen** (alleen als de dienst niet gekoppeld is): het Hub-adres + de koppelcode (+ bij de executor de
   TrueNAS-schrijfkey). Een uitleg waar je de code maakt (Hub → Instellingen → Diensten).
5. **Ontkoppelen:** de lokale ontkoppelcode uit de app-log (*TrueNAS → Apps → <app> → Logs*). Uitleg wanneer dit nodig
   is.
6. **Dienstspecifiek blok** (§6.1).
7. **Voet:** links naar `/healthz` en `/readyz`, "Alle schermen staan in de Hub" (+ een link als de dienst gekoppeld is)
   en de versie.

### 6.3 Eisen

- **Geen JavaScript.** Alleen inline `<style>` (CSP) en inline `<svg>` voor iconen (lucide-paden, `aria-hidden`).
  Geen afbeeldingen of fonts. Systeemfont.
- **Eén gedeelde sjabloon-CSS** (≤ ±8 KB, gegenereerd uit dezelfde tokens als de Hub). Elke repo krijgt er een
  **versie-gepinde kopie** van; de repos blijven zelfstandig.
- Licht/donker via `prefers-color-scheme` (zonder JS is er geen wisselknop). Contrast AA in beide thema's.
- Responsief vanaf 320 px, één kolom, maximaal ±760 px breed. Touch targets ≥ 44 px. Zichtbare focus.
- **Formulieren:**
  - een `<label for>` bij elk veld;
  - `autocomplete="off"` voor codes;
  - het geheime veld als `type="password"` met uitleg ("wordt versleuteld opgeslagen; je ziet daarna alleen de
    laatste 4 tekens");
  - de verwachte vorm in de hulptekst (`http(s)://<NAS-adres>:<poort>`, geen voorbeeld-IP);
  - fouten bovenaan in een melding (`role="alert"`) **en** bij het veld (`aria-describedby`), uit de vaste lijst.
- De statuslabels zijn gelijk aan die van de Hub (§7.1). Zonder JS kun je de trace_id niet kopiëren met een knop: toon
  hem in een selecteerbaar veld (`user-select: all`) met de tekst "Selecteer en kopieer".
- Er staan geen geheimen, accountnamen of privé-aantallen op de pagina (dat is al beleid in home-control-hub en
  zoeken).
- Een paginatitel per toestand ("Executor — niet gekoppeld"). Kopniveaus h1 → h2. Landmarks (`<main>`, `<section
  aria-labelledby>`).

---

## 7. Terugkerende UI-toestanden en semantiek

### 7.1 Overzicht (T-01 … T-24)

**Kleurrol** is een betekenisrol en geen kleurwaarde. De waarden volgen in de tokenstap.

| ID | Toestand | Betekenis en wanneer | Visuele eisen | NL-label(s) |
|---|---|---|---|---|
| T-01 | **Gezondheid** | `healthy` / `degraded` / `down` / `unknown` uit de connector of monitoring | Symbool + tekst + kleurrol: ok / aandacht / fout / onbekend. Groen alleen bij "gemeten en goed". | **Gezond** · **Beperkt** · **Storing** · **Onbekend** |
| T-01a | **Totaalstatus** | Afgeleid: storing > beperkt > (deels) onbekend > gezond | Nooit beter dan het slechtste onderdeel | **Alles gezond** (alleen als alles vers en gezond is) · **Beperkt** · **Storing** · **Deels onbekend** · **Onbekend** |
| T-02 | **Versheid** | Vers (binnen de TTL) / verouderd (> TTL) / nooit gemeten | Altijd absolute + relatieve tijd. Verouderd: de waarde wordt gedempt, krijgt het label "laatst bekend" en de status wordt T-01 **Onbekend**. Versheid is **nooit groen**. | "Bijgewerkt 11:56 (2 min geleden)" · "**Verouderd** — laatst bekend 10:12" · "Nog nooit gemeten" |
| T-03 | **Meetkwaliteit en herkomst** | Gemeten / afgeleid / geschat / niet beschikbaar | Een label bij het getal. Geschat krijgt "≈" en een visueel onderscheid in grafieken (nooit dezelfde look als gemeten; uitwerking in de dataviz-stap). | **Gemeten** · **Afgeleid** · **Geschat** · **Niet beschikbaar** |
| T-04 | **Risicoklasse** | R0–R3 volgens de policy | Een vorm die afwijkt van de statusbadge (bijvoorbeeld een tag met cijfer). De nadruk loopt op met de klasse. R3 gebruikt de rol "gevaar". Altijd "waarom" beschikbaar (`rule_ids`). | **R0 · Alleen lezen** · **R1 · Omkeerbaar** · **R2 · Goedkeuring nodig** · **R3 · Destructief — extra bevestiging** |
| T-05 | **Actiestatus** | De levenscyclus van een voorstel | Een tijdlijn met stappen; "klaar" pas na readback | Voorstel · Wacht op goedkeuring (verloopt over 12:30) · Goedgekeurd · Bezig · Controleren (readback) · **Uitgevoerd en gecontroleerd** · Mislukt · **Gestopt: afwijking na uitvoering** · Teruggedraaid · Vervallen · Geweigerd door beleid · Geweigerd door <naam> |
| T-06 | **Goedkeuring vervallen** | De tijd is verstreken, of er is drift in een gebonden veld [EX19] | Melding (aandacht) + "Nieuw voorstel aanvragen" | "Goedkeuring vervallen: de app-versie is gewijzigd na de preview." |
| T-07 | **Validatiestatus** | Het bewijsniveau van een functie of build [§11] | Neutraal/informatief, nooit de stijl van "geslaagd". De exacte strings blijven. | **Sim-getest** · **Unit-getest** · **NIET GEVALIDEERD (echte NAS)** · **NIET GEVALIDEERD (hardware)** · **NIET GEVALIDEERD (account)** · *(alleen na echte acceptatie:* **Gereed / Geslaagd***)* |
| T-07a | **Apparaatcompatibiliteit** | my_house [B06-001] | Hetzelfde patroon als T-07 | **Getest op <datum>** · **Compatibel (niet getest)** · **Niet ondersteund** |
| T-08 | **capability_unavailable** | De bron of versie heeft de functie niet (`501`) | Een inline melding of een paneel met code, bron en endpoint. Knoppen zijn uitgeschakeld **met reden**. Nooit schijnsucces. | "**Niet beschikbaar** — <bron> ondersteunt dit (nog) niet." · code `capability_unavailable` |
| T-08a | **Nog niet beschikbaar (fase)** | Een scherm of functie uit een latere fase | Een rustig paneel met wat er komt en wanneer, en geen nepdata | "Nog niet beschikbaar — volgt in fase P3 (eigen apps koppelen)." |
| T-09 | **Fout** | Een API-fout `{code, message, details, trace_id}` | Kleurrol fout. Opbouw: wat er gebeurde + waarom + wat je kunt doen, dan de code + trace_id (kopieerbaar) + "Opnieuw proberen", en de details uitklapbaar. Veldfouten staan bij het veld + in een samenvatting bovenaan het formulier. | Zie §7.3 |
| T-10 | **Offline (browser)** | `navigator.onLine === false` | Een vaste banner bovenaan. Alle waarden worden onbekend of verouderd. **Mutaties uitgeschakeld** (er wordt nooit een actie in de wachtrij gezet). | "Je bent offline. Gegevens zijn niet actueel; acties zijn uitgeschakeld." |
| T-10a | **Hub onbereikbaar** | 502 `api_unavailable` / time-out | Banner met fout + trace_id | "De Hub reageert niet. Gegevens zijn onbekend." |
| T-10b | **Live-updates onderbroken** | De eventstream valt weg | Een kleine banner + aftellen tot het opnieuw verbinden | "Live-updates onderbroken — opnieuw verbinden over 10 s." |
| T-10c | **Verbinding hersteld** | Na T-10/a/b | 5 s zichtbaar en `aria-live="polite"`; daarna verversen | "Weer verbonden. Gegevens worden ververst." |
| T-10d | **Bron onbereikbaar** | Connector `unknown` (bijvoorbeeld MediaGuard offline) | Per kaart (T-01 Onbekend + reden); geen globale banner | "MediaGuard reageert niet sinds 10:12." |
| T-11 | **Laden** | De eerste keer laden | Een skelet in de vorm van de inhoud, nooit "0" of "—" als waarde; `aria-busy` | Schermlezer: "Laden…". Na 10 s: "Dit duurt langer dan verwacht." |
| T-11a | **Verversen** | Opnieuw ophalen binnen de TTL | De vorige weergave gedempt houden + "Bijwerken…". Geen skeletflits [dataviz]. | "Bijwerken…" |
| T-12 | **Leeg** | Gemeten, en er is echt niets | Wat dit is + waarom het leeg is + hoe je begint. "Geen problemen" mag alleen als de monitoring vers is. | "Geen open problemen. Gecontroleerd om 11:56." |
| T-12a | **Niet gekoppeld / niet ingericht** | Er is nog geen bron | Een paneel met een directe vervolgstap | "Nog niet gekoppeld. *MediaGuard koppelen*" |
| T-13 | **Onbekend** | Niet gemeten / verouderd / bron onbereikbaar / geen rechten / niet ondersteund | Neutraal + "?"-symbool + **altijd een reden**. Nooit groen, nooit 0. | "**Onbekend** — niet gemeten" · "… bron onbereikbaar" · "… verouderd" · "… geen toegang" |
| T-14 | **Gate dicht** | Een gate wacht op een voorwaarde (besluit, meting, koppeling) | Slotsymbool + aandacht/neutraal (geen foutrood). Een lijst van voorwaarden met links. **Geen knop "toch doorgaan".** | "**Geblokkeerd door de back-upgate** — nodig: OneDrive-methode (D04) ingevuld. *Invullen*" |
| T-14a | **Gate dicht door een gemeten falen** | Pool DEGRADED, back-up mislukt of verouderd [EX11, EX12] | Slot + foutrol + een link naar het incident | "Geblokkeerd: de opslagpool is beperkt (DEGRADED). Opslagacties zijn uit tot de pool gezond is." |
| T-14b | **Gate onbekend** | Er zijn te weinig gegevens; onbekend opent nooit [ADR-0007] | Slot + onbekend-rol | "Geblokkeerd: poolstatus onbekend." |
| T-15 | **Altijd geblokkeerd (beleid)** | Boiler, auto-delete, policy door AI, betaalde acties | Slot + "beleid", geen uitvoerknop. Het element blijft zichtbaar waar de gebruiker de knop zou verwachten (boiler). | "**Alleen meten** — schakelen is altijd uitgeschakeld (beleid)." |
| T-16 | **Rolbeperking** | Je rol mag dit niet | Mutatieknoppen zijn verborgen. Eén rolmelding per pagina. | "Je kijkt als **kijker**: je kunt hier niets wijzigen." |
| T-17 | **Gepauzeerd / noodstop** | Een bewuste pauze (MediaGuard-noodstop, AV1-pauze, flow gepauzeerd) | Een globale balk of statusvariant "Gepauzeerd" (info/aandacht), **geen storing** | "**Gepauzeerd** door de MediaGuard-noodstop sinds 21:04 (door <naam>)." |
| T-18 | **Apparaat-readback** | Een commando aan my_house | Twee fasen: verstuurd → bevestigd / niet bevestigd | "Verstuurd — wacht op bevestiging" · "Bevestigd: 21 °C" · "**Niet bevestigd** — het apparaat reageerde niet. Er is niets gewijzigd." |
| T-19 | **Override / handmatig** | De afstandsbediening gaat voor de AI [EX26] | Een eigen symbool (hand) + uitleg | "Handmatig uitgezet — blijft uit tot je hervat." |
| T-20 | **Severity (incident)** | Kritiek / hoog / middel / laag / info | Een andere vorm dan T-01 (rangorde in plaats van gezondheid), met tekst | **Kritiek** · **Hoog** · **Middel** · **Laag** · **Info** |
| T-20a | **Incidentstatus** | De levenscyclus | Een tekstlabel + symbool | Open · Erkend · Gesnoozed tot 08:00 · Opgelost |
| T-21 | **Besluitstatus (D01–D18)** | Excel-statussen [§11] | Eén consistente set badges | Open · Ingevuld · Getest · Geblokkeerd · N.v.t. |
| T-22 | **Hersteltest-resultaat** | [B12-005] | Gedeeltelijk krijgt de aandachtrol, nooit succes | Geslaagd · **Gedeeltelijk** · Mislukt |
| T-23 | **Aftellen / vervaltijd** | Goedkeuring (≤ 15 min), koppelcode (30 of 60 min), sessie | De visuele klok elke seconde. De schermlezer krijgt het alleen bij een drempel (5 min, 1 min, verlopen) te horen. | "Verloopt over 4:59" · "**Verlopen** — maak een nieuwe code." |
| T-24 | **AI-zekerheid** | Hypothese of antwoord | Een label (geen percentage zonder model), met bronnen | **Zeker** (bewijs direct) · **Waarschijnlijk** · **Onzeker** · **Ik weet het niet** |

### 7.2 Betekenisregels (gelden overal, ook in de statuspagina's en de bestaande apps)

1. **Groen = gemeten en goed.** Nooit voor "actueel", "verbonden met de sessie", "nieuw" of "aanbevolen".
2. **Rood = gemeten falen of gevaar (R3, destructief).** Nooit voor "nog niet ingevuld" of "wacht op een voorwaarde"
   (dat is T-14).
3. **Grijs/neutraal = onbekend of niet van toepassing**, altijd met een reden.
4. **Statuskleuren zijn gereserveerd** en worden nooit als grafiekreeks gebruikt (dataviz-regel). Een grafiekreeks met
   dezelfde kleurfamilie als een status leunt op legenda + label.
5. **Symbool + tekst bij elke status**, ook in tabellen, grafieklegenda's en de tellers van de navigatie.
6. **Gezondheid, severity, risico, validatie en beslisstatus zijn vijf verschillende assen.** Ze krijgen verschillende
   vormen, zodat ze naast elkaar op één kaart niet te verwarren zijn.
7. **Een getal zonder eenheid, bron en tijd bestaat niet** in de UI.
8. **Stale is nooit gezond.** De laatst bekende waarde mag blijven staan met het label "verouderd", maar de status
   wordt onbekend en grafieken tonen een gat na het laatste meetpunt (O-03).

### 7.3 Microcopy-patronen (NL)

| Situatie | Patroon | Voorbeeld |
|---|---|---|
| Fout | Wat er gebeurde. Waarom (als bekend). Wat je kunt doen. + code + trace_id | "Opslaan is mislukt. De app is gewijzigd sinds je de preview opende. Open het voorstel opnieuw. · Code `etag_mismatch` · Trace-ID `…` *Kopiëren*" |
| Lege lijst | Wat dit is + waarom het leeg is + hoe je begint | "Nog geen hersteltests. Een hersteltest zet een back-up terug in een afgeschermde omgeving. *Hersteltest starten*" |
| Bevestiging | Een werkwoord + het object in de knop. De gevolgen in de tekst. Geen "OK" of "Weet je het zeker?". | Titel "App *Uptime Kuma* herstarten?" · knoppen **App herstarten** / **Annuleren** |
| R3-bevestiging | De gevolgen opgesomd, typen ter controle, en een aparte stap | "Dit verwijdert de data van *<app>* op *<dataset>*. Dit kun je niet ongedaan maken zonder herstelpunt *<id>*. Typ *<app>* om te bevestigen." |
| Gate | "Geblokkeerd door <gate>" + nodig + actie | "Geblokkeerd door de back-upgate — nodig: hersteltest van foto én database (D05). *Hersteltest registreren*" |
| Onbekend | "Onbekend" + de reden in één bijzin | "Onbekend — Beszel levert geen GPU-temperatuur." |
| Ik weet het niet | Wat er ontbreekt + hoe je het te weten komt | "Ik weet het niet. Er zijn geen logregels van na 10:12. *Logs van MediaGuard openen*" |
| Laden, lang | Verwachting geven | "Inventaris ophalen bij TrueNAS… dit kan een minuut duren." |
| Gelukt | Feitelijk en controleerbaar, zonder uitroepteken | "Herstart uitgevoerd en gecontroleerd om 11:58 (gezond na 34 s)." |
| Deep link | De bestemming noemen | "Openen in MediaGuard" (+ een icoon voor een externe app; "opent in een nieuw tabblad" voor de schermlezer) |

**Vaste termen** (één term per begrip):

| Gebruik | Niet |
|---|---|
| app (iets in TrueNAS Apps) | — |
| dienst (een eigen platformonderdeel) | — |
| Problemen (navigatie) / incident (één item) | — |
| goedkeuring | akkoord, approval |
| voorstel | action request (in de UI) |
| herstelpunt | restore point |
| hersteltest | restore-test |
| back-up (lopende tekst) | — |
| Backups (navigatielabel, zo vastgelegd in 08_UI) | — |
| koppelen / ontkoppelen | — |
| koppelcode, setupcode, ontkoppelcode | — |
| beheerder / operator / kijker / kind (de UI-namen van de rollen) | — |
| bijgewerkt | geüpdatet |
| verouderd | stale (in de UI) |

**Notatie:**

- `Intl` met nl-NL: decimale komma, punt als duizendtalscheiding;
- 24-uurs tijd en "9 nov 2026, 11:56";
- relatief: "2 min geleden";
- een vaste spatie tussen getal en eenheid ("42 °C", "1,2 TiB": de binaire eenheden zoals de bron ze levert);
- percentages als "42%".

---

## 8. Componenten

### 8.1 shadcn/ui-basis (stijl new-york als uitgangspunt; de platformtokens overschrijven het uiterlijk)

| Component | Gebruik in het platform | Aandachtspunt |
|---|---|---|
| Button | Primaire, secundaire, ghost- en destructieve acties. Icoonknop met zichtbaar of `aria-label`. | Minimaal 44 × 44 px; varianten `danger` (R3) en `link` |
| Badge | Basis voor de C-03/04/07/09-badges | Nooit alleen kleur |
| Card | De basis van het kaartcontract (C-05) | Kop / waarde / meta / actie als vaste slots |
| Alert | Inline meldingen (T-08, T-09, T-14) | `role="alert"` alleen bij fouten die je net veroorzaakt |
| AlertDialog | R1-bevestiging, verlaten met niet-opgeslagen werk | Focus op de veiligste knop |
| Dialog, **Sheet** | Desktop-details, het mobiele Meer-menu, filters op mobiel | R2/R3-goedkeuring nooit in een kleine dialoog (pagina) |
| Drawer (vaul) | Optioneel voor mobiele acties onderin | Altijd met knoppen, nooit alleen vegen (2.5.1) |
| Tabs | Appdetail (5), Media (5), periodes | Horizontaal scrollbaar op mobiel; patroon `tablist` |
| Table | Desktoplijsten | < 768 px → C-34 kaartenlijst |
| Input, Textarea, Select, RadioGroup, Checkbox, Switch, Label | Formulieren (C-38) | Ja/nee zonder standaardantwoord = RadioGroup zonder waarde |
| Form-patroon | Validatie per veld + samenvatting | De server is leidend; de NL-meldingen komen van de API |
| **InputOTP** | Setupcode, koppelcode, ontkoppelcode (`XXXX-XXXX-XXXX`) | Plakken van de hele code; één label voor de groep |
| Tooltip, HoverCard, Popover | Uitleg van een risicoregel of een afkorting | **Nooit de enige plek voor informatie** (1.4.13: sluitbaar, aanwijsbaar, blijvend) |
| DropdownMenu | Gebruikersmenu, rijacties | Gevaarlijke items gescheiden en gemarkeerd |
| **Command** | Globaal zoeken / navigeren (C-51) | `/` en Ctrl+K; alleen-toetsenbordgebruik |
| Sidebar (block) | De desktopzijbalk (C-01) | Vaste 9 items; samenklapbaar met tooltips |
| Breadcrumb | Diepe schermen (appdetail, besluit) | — |
| Skeleton | T-11 | Alleen de eerste keer laden |
| Progress | Wizards, uitvoering, voortgang | Met tekst ("stap 3 van 7") |
| Sonner (toast) | Alleen niet-kritieke bevestigingen ("Gekopieerd") | Kritieke uitkomsten altijd in de pagina zelf; `aria-live` |
| Accordion / Collapsible | "Toon bewijs", "Technische details" | — |
| ScrollArea | Logs, lange diffs | Toetsenbord-scrollbaar |
| Pagination | Cursor-paginering ("Meer laden") | — |
| ToggleGroup | Periodekiezer, Systeem/Licht/Donker | — |
| Calendar + datumbereik | Filters (periode) | Presets eerst (dataviz) |
| Separator, Avatar, Kbd | Diversen | — |
| Chart (shadcn op recharts) | Grafieken (C-32) | MSO gebruikt al recharts; tabelweergave verplicht |

### 8.2 Platformspecifieke componenten

| ID | Component | Doel | Belangrijkste varianten en toestanden | A11y-kern | Eerste fase |
|---|---|---|---|---|---|
| C-01 | **AppShell** | Zijbalk ≥ 1024 / ondernavigatie < 1024, kopbalk, Meer-sheet en de kindschil | Actief item; tellers (Problemen, Goedkeuringen); kindvariant | Landmarks, skiplink "Naar inhoud", `aria-current="page"`; safe areas (PWA) | P0 |
| C-02 | **PageHeader** | Titel, korte omschrijving, primaire actie, paginabrede versheid en Vernieuwen | Met/zonder broodkruimel | Focus op de h1 na een routewissel; `<title>` per pagina | P0 |
| C-03 | **StatusBadge** | T-01 / T-01a | gezond, beperkt, storing, onbekend, gepauzeerd, niet gekoppeld | Symbool `aria-hidden` + tekst | P0 |
| C-04 | **SystemStatusPanel** | Totaalstatus + onderdelen + "Wat actie nodig heeft" | Alles gezond / deels onbekend / storing | Lijstsemantiek; acties als links | P0 |
| C-05 | **MetricCard (kaartcontract)** | Label · waarde · eenheid · status · meetkwaliteit · bron · laatst bijgewerkt · vervolghandeling · optioneel sparkline/meter | vers / verouderd (laatst bekend) / nooit gemeten / onbekend / niet beschikbaar / fout / laden | De hele kaart is geen knop; één primaire link; de waarde + eenheid lees je als één zin | P0 |
| C-06 | **FreshnessMeta** | T-02 + bron | vers / verouderd / nooit; TTL-uitleg | `<time datetime>` + een absolute tijd als tekst | P0 |
| C-07 | **QualityLabel** | T-03 | gemeten / afgeleid / geschat / niet beschikbaar | Tekst; "≈" voor de schermlezer als "ongeveer" | P1 |
| C-08 | **RiskBadge** | T-04 + regeluitleg | R0–R3; "AI stelde R0 voor → beleid R3" | Tekst + popover (geen tooltip-only) | P2 |
| C-09 | **ValidationBadge** | T-07 / T-07a | Sim-getest, Unit-getest, NIET GEVALIDEERD (x), Gereed | Tekst | P0 |
| C-10 | **DecisionStatusBadge** | T-21 | 5 statussen + waardebron | Tekst | P0 |
| C-11 | **GateNotice** | T-14 / 14a / 14b | dicht-voorwaarde / dicht-falen / onbekend / toegestaan | Een lijst met voorwaarden + links; geen override-knop | P0 |
| C-12 | **CapabilityUnavailable** | T-08 / T-08a | inline / paneel / uitgeschakelde knop met reden | De reden is focusbaar en leesbaar (geen tooltip-only) | P0 |
| C-13 | **PolicyLock** | T-15 (boiler, auto-delete) | Inline label / kaartslot | Tekst "Alleen meten" | P3 |
| C-14 | **ErrorPanel** | T-09 | inline (veld), sectie, pagina (502/403/404) | Samenvatting met links naar de velden; `role="alert"` bij een nieuwe fout | P0 |
| C-15 | **CopyField** | trace_id, codes, digests, supportbundel | Kopieerknop; **terugval zonder secure context**: selecteer-alles + instructie | Bevestiging via `aria-live` ("Gekopieerd") | P0 |
| C-16 | **ConnectionBanner** | T-10 / a / b / c | offline / Hub weg / live onderbroken / hersteld | `role="status"`; niet focus stelen | P0 |
| C-17 | **EmptyState** | T-12 / T-12a / T-13 | leeg-gemeten / niet gekoppeld / onbekend | Kop + tekst + actie | P0 |
| C-18 | **LoadingState** | T-11 / T-11a | skelet / gedempt verversen | `aria-busy`; time-outmelding | P0 |
| C-19 | **ActionPreview** | S-061 | R0–R3; met of zonder diff; geblokkeerd; dry-run-resultaat | Kopstructuur per sectie; samenvatting eerst | P2 |
| C-20 | **DiffView** | Voor/na per veld, configuratiediff | Naast elkaar (desktop) / onder elkaar (mobiel); toegevoegd / gewijzigd / verwijderd met **tekenmarkering** (+ / ~ / −), niet alleen kleur | Een tabelsemantiek of lijst met "was / wordt" | P2 |
| C-21 | **ApprovalCard / ApprovalPage** | S-062 / S-063 | Openstaand / vervallen (tijd/drift) / goedgekeurd / geweigerd; R3 in twee stappen | Aftellen volgens T-23; de bevestigingsknop is pas actief na de getypte controle (R3) | P2 |
| C-22 | **Countdown** | T-23 | normaal / bijna verlopen / verlopen | Aankondigen op drempels, niet elke seconde | P0 (codes) |
| C-23 | **ExecutionTimeline** | S-064, T-05 | stap ok / bezig / mislukt / gestopt; abortknop | `role="list"`; live-updates `polite` | P2 |
| C-24 | **ConfirmFlow** | Bevestigingsniveaus | R1 = AlertDialog; R2 = goedkeuring; R3 = typen + aparte stap | Werkwoordlabels; focus op Annuleren bij R3 | P2 |
| C-25 | **AuditTimeline** | Wie / wat / wanneer / bron | Filters; export | Tijden als `<time>` | P0 |
| C-26 | **ActorBadge** | systeem / gebruiker / AI / flow / spraak | — | Tekst | P0 |
| C-27 | **IncidentRow + SeverityBadge + IncidentStatus** | S-050 | T-20 / T-20a; aantal events | Rij als één link; status als tekst | P1 |
| C-28 | **EvidenceList** | "Toon bewijs", citaten | logregel / metriek / event / document; uitklapbaar | Logtekst altijd als geciteerde data (`<blockquote>`/`<pre>`) | P1 |
| C-29 | **HypothesisCard** | De oorzaak met T-24-zekerheid | zeker / waarschijnlijk / onzeker / ik weet het niet | — | P1 |
| C-30 | **Chat-set** | Bericht (gebruiker/AI), citaatchip, plan-stappen, actiechip, tegoedmeter, privacy-indicator | AI denkt / antwoord / fout / harde stop | Nieuwe AI-berichten `aria-live="polite"`; toetsenbord: Enter verstuurt, Shift+Enter nieuwe regel | P2 |
| C-31 | **Voice-set** | Ingedrukt-houden-microfoonknop, transcriptbevestiging, TTS aan/uit, opnamestatus | geen toestemming / luistert / verwerkt / bevestigen | De knop ook via de spatiebalk; **een zichtbare én aangekondigde opnamestatus** | P5 |
| C-32 | **Grafieken** | Lijn/vlak (trends), sparkline, meter (pool, tegoed), segmentbalk (dekking, energieverdeling), gestapelde kolom (energie per dag, gemeten/geschat) | Een gat bij onbekend; verouderd-markering; periodekiezer boven de grafiek; **tabelweergave verplicht**; geen dubbele y-as | `<figure>` + `<figcaption>`; tooltip ook via focus | P1 |
| C-33 | **CoverageMatrix** | Back-updekking, SSO-dekking, meetdekking, compatibiliteitsmatrix | cel: ja / nee / onbekend / n.v.t. (symbool + tekst) | Echte tabel ≥ 768; per-rij-kaarten < 768 | P0 |
| C-34 | **ResponsiveList** | Tabel ≥ 768 px, kaartenlijst < 768 px | sorteren, filteren, cursor-paginering, rijacties | Geen horizontale scroll voor kerninfo (K1) | P0 |
| C-35 | **FilterBar** | Eén rij boven de inhoud | zoeken, chips, periode eerst; mobiel als sheet | Resultaatteller `aria-live` | P0 |
| C-36 | **Wizard / Stepper** | Onboarding, installatie, herstel, bronnen, executor | stap ok / huidig / geblokkeerd / fout; opslaan en later verder | "Stap 2 van 5: …" in de kop | P0 |
| C-37 | **SchemaForm-veldset** | Formulieren uit een JSON-schema | tekst; getal + eenheid; **nullable met "onbekend"**; ja/nee zonder standaard; lijst van strings (chips + toevoegen); lijst van objecten (herhaalbare rijen); verplichte bevestiging (`const: true`) | Labels en hulp via `aria-describedby`; fouten per veld | P0 |
| C-38 | **DatasetPicker** | Een dataset kiezen uit de inventaris | met rol (config / data / media / scratch); verboden paden uitgeschakeld met reden | Boom of lijst met toetsenbord | P2 |
| C-39 | **SecretField / CredentialRow** | Geheimen invoeren en tonen | invoer (nooit vooringevuld) / opgeslagen (••••1a2b + datum) / testen / roteren | `type="password"`; geen tonen-knop voor de opgeslagen waarde | P0 |
| C-40 | **CodeDisplay** | Een koppelcode tonen, uitleg over de setupcode | geldig + aftellen / verlopen / gebruikt | Code in groepen; spellingvriendelijk (geen 0/O/1/I) | P0 |
| C-41 | **ServiceRow** | Het dienstenregister | gekoppeld / niet gekoppeld / mislukt / geen contact sinds … | — | P0 |
| C-42 | **DeepLink** | Een externe app-UI openen | eigen app / app van derden / niet bereikbaar | "Opent <app> in een nieuw tabblad" | P0 |
| C-43 | **RoomCard / DeviceControl** | Huis | aan/uit, doel, offline, verouderd, override, geblokkeerd, readback-fasen | Bediening als knop of slider met tekstwaarde; geen kleur-only voor aan/uit | P3 |
| C-44 | **ClimateZone** | Gree-zone | modus, conflictblokkade, handmatig, niet ondersteund | — | P3 |
| C-45 | **BoilerCard** | Alleen meten | vermogen, kWh, kosten, PolicyLock | **Geen schakelaar-element** in de DOM | P3 |
| C-46 | **EnergyReading** | Waarde + kwaliteit + meterreset/zomertijd-label | gemeten / geschat / onbekend | — | P3 |
| C-47 | **Media-set** | MediaTabs, TitleRow (poster optioneel), WhyMissingPanel (diagnoseketen), DownloadRow | beschikbaar / ontbreekt / bezig / mislukt / gepauzeerd | Posters met een alt-tekst; de keten als geordende lijst | P3 |
| C-48 | **PausedBar** | T-17 | noodstop / pauze | `role="status"` | P2 |
| C-49 | **RoleNotice** | T-16 | kijker / operator / kind | — | P0 |
| C-50 | **ThemeSwitch** | Systeem / Licht / Donker | — | ToggleGroup met tekst | P0 |
| C-51 | **GlobalSearch** | Schermen + zoekindex (P5) | — | Command-patroon | P1 |
| C-52 | **LogViewer** | Geschoonde logs | omloop, zoeken, kopiëren, laden | Monospace; toetsenbord-scroll | P1 |
| C-53 | **FlowCard / NodeRequirementChip** | Automatisering | actief / gepauzeerd / fout; node: R0–R3 / verboden | — | P2 |
| C-54 | **RunLog** | Dry-run- en uitvoeringslog | — | — | P2 |
| C-55 | **StatusPage-sjabloon** (server-HTML) | §6: kop, checklist, koppelformulier, ontkoppelformulier, melding, voet | zie §6 | zie §6.3 | P0 |

### 8.3 Tokenrollen die de ontwerptaal moet leveren (waarden volgen later)

- **Oppervlak en tekst:** achtergrond, oppervlak, verhoogd, verzonken, rand (decoratief en ≥ 3:1 voor velden),
  tekst 1/2/3, focusring.
- **Merk en interactie:** accent, accent-hover, tekst op accent, link.
- **Statusrollen (gereserveerd):** ok, aandacht, fout, onbekend/neutraal, info, plus hun tints.
- **Overige assen:** risico R0–R3, gate/slot, gepauzeerd, validatie, meetkwaliteit (geschat).
- **Domeinrollen** (moeten blijven bestaan, §10): warmte, koeling, boiler, licht-aan, verouderd (my_house); GPU-lane,
  CPU-lane, integriteit (MediaGuard).
- **Grafiekrollen:** de categorische reeks in een vaste volgorde, sequentieel, divergerend, de-nadruk/overig, raster en
  as. Gekozen via de dataviz-procedure + de validator, apart voor licht en donker.
- **Typografie** (familie, schaal, `tabular-nums` voor kolommen), **ruimte**, **radius**, **schaduw**, **beweging**
  (met `prefers-reduced-motion`), **breekpunten** (360 / 390 / 768 / 1024 / 1440) en **z-lagen**.

---

## 9. Toegankelijkheid en responsief gedrag

### 9.1 Normen

**WCAG 2.1 AA** is het minimum. Platformeisen gaan waar nodig verder:

- touch targets ≥ 44 × 44 px (strenger dan 2.1 AA; dat staat in 2.5.5 AAA);
- de P0-tests draaien axe al met WCAG 2.2 A/AA (ADR-0009). Dat blijft zo.

### 9.2 Eisen per WCAG-principe

| # | Eis | WCAG | Toepassing in het platform |
|---|---|---|---|
| A-01 | Alternatieve tekst | 1.1.1 | Iconen `aria-hidden` naast tekst; een icoonknop krijgt een `aria-label` dat bij het zichtbare label past (2.5.3); posters krijgen een titel als alt; grafieken een `figcaption` + tabelweergave |
| A-02 | Structuur | 1.3.1 | Landmarks, één h1 per pagina, kopniveaus zonder sprongen, echte tabellen met `th scope`, lijsten als lijst, formuliergroepen met `fieldset/legend` (ja/nee, rijen) |
| A-03 | Volgorde en oriëntatie | 1.3.2, 1.3.4 | De DOM-volgorde is de leesvolgorde (status vóór kaarten); staand en liggend werken allebei |
| A-04 | Niet alleen kleur | 1.4.1 | Status, risico, diff, aan/uit, grafiekreeksen: altijd met tekst, symbool, vorm of patroon (de dataviz-textuur als optie) |
| A-05 | Contrast | 1.4.3, 1.4.11 | Tekst ≥ 4,5:1 (groot ≥ 3:1); veldranden, focusring, badgerand (als die informatie draagt), grafieklijnen en iconen ≥ 3:1. **Beide thema's berekend** (culori + wcag-contrast) |
| A-06 | Herschalen en reflow | 1.4.4, 1.4.10, 1.4.12 | 200% zoom zonder verlies; reflow op 320 CSS-px zonder horizontale scroll (behalve diffs en logs als 2D-inhoud, met een ScrollArea); extra regelafstand breekt niets |
| A-07 | Inhoud bij hover/focus | 1.4.13 | Tooltips sluitbaar (Esc), aanwijsbaar en blijvend; nooit de enige informatiebron |
| A-08 | Toetsenbord | 2.1.1, 2.1.2 | Alles bedienbaar: tabs (pijltjes), menu's, dialogen (focusval + teruggeven), command palette en grafiekpunten (focusbaar of via de tabelweergave); geen toetsenbordval |
| A-09 | Tijdslimieten | 2.2.1 | De sessie waarschuwt vóór het verlopen, met **Verlengen**. Codes en goedkeuringen hebben een beveiligingslimiet (wezenlijk), maar wel een vooraankondiging, een zichtbare klok en een directe "nieuwe code/voorstel"-weg |
| A-10 | Beweging | 2.2.2, 2.3.3 | Geen automatisch bewegende inhoud zonder pauze; `prefers-reduced-motion` respecteren (aftelklokken en live-grafieken zonder animatie) |
| A-11 | Navigatie | 2.4.1–2.4.7 | Skiplink; een paginatitel per route ("Backups — Hub"); een logische focusvolgorde; linkteksten met context ("Bekijk back-updekking"); een zichtbare focusring (≥ 2 px, ≥ 3:1) |
| A-12 | Aanwijzer | 2.5.1–2.5.3 | Geen vegen-only (snoozen of verwijderen altijd ook met een knop); acties bij `pointerup`; label in naam |
| A-13 | Taal | 3.1.1, 3.1.2 | `lang="nl"`; Engelse vaktermen of code in `<code>` of met `lang="en"` waar de uitspraak ertoe doet |
| A-14 | Voorspelbaar | 3.2.1–3.2.4 | Geen contextwissel bij focus of invoer (filters met een expliciete toepasknop op mobiel); **consistente navigatie en identificatie** over de Hub, de statuspagina's en de bestaande apps (dezelfde iconen en labels voor hetzelfde) |
| A-15 | Invoerhulp | 3.3.1–3.3.4 | Fouten per veld + samenvatting; een suggestie hoe je het oplost; **foutpreventie** bij R2/R3 = preview + bevestiging + omkeerbaarheid (of een expliciete melding dat het niet omkeerbaar is) |
| A-16 | Robuust | 4.1.2, 4.1.3 | Naam, rol en waarde voor alle custom componenten (Radix levert de basis); statusberichten via `aria-live` (gekopieerd, opgeslagen, verbinding hersteld, nieuwe AI-reactie) zonder focusverlies |
| A-17 | Schermlezer en routewissel | 2.4.3 / 4.1.3 | Bij een client-side navigatie gaat de focus naar de h1 en wordt de titel aangekondigd |
| A-18 | Forced colors | (1.4.1/1.4.11) | De Windows-hoogcontrastmodus houdt symbolen en randen; status blijft leesbaar zonder achtergrondkleur |
| A-19 | Kinderprofiel | (3.1.5 AAA als richtlijn) | Eenvoudige taal, geen codes of trace_id's in beeld ("Er ging iets mis. Vraag het aan een volwassene."); de trace_id zit achter "Details" |

**Al gevonden in P0 (moet het nieuwe ontwerp oplossen):**

- K1: de gate-tabel op 390 px (1.4.10 reflow);
- K2/K3: de betekenis van rood en groen (geen WCAG-fout, wel misleidend);
- K4: uitloggen als primaire kopactie.

### 9.3 Responsief gedrag

| Breedte | Schil | Indeling | Bijzonderheden |
|---|---|---|---|
| **360 / 390** (telefoon) | Ondernavigatie 5 items (+ safe area), compacte kopbalk | Eén kolom. Kaarten op volle breedte. Tabellen → kaartenlijst. Tabs scrollbaar. Filters in een sheet. | Goedkeuring en preview als volledige pagina. Primaire actie onderaan, sticky boven de ondernavigatie. Diff onder elkaar. |
| **768** (tablet staand) | Ondernavigatie (ADR-0009: zijbalk vanaf 1024) | Twee kolommen voor kaarten; echte tabellen voor eenvoudige lijsten (≤ 4 kolommen), anders kaarten | Masterlijst + detail als aparte schermen |
| **1024–1279** | Zijbalk (eventueel ingeklapt) + kopbalk | 2–3 kolommen | — |
| **1440** (desktop) | Volledige zijbalk + kopbalk met Zoeken, Problemen, Goedkeuringen, AI en het gebruikersmenu | 3 kolommen voor kaarten; tabellen met alle kolommen; master-detail voor Problemen en Goedkeuringen | Maximale inhoudsbreedte (geen eindeloos brede regels; leestekst ≤ ±75 tekens) |

Algemeen:

- geen horizontale scroll van de pagina;
- touch targets ≥ 44 px met ≥ 8 px tussenruimte;
- de lettergrootte voor invoer is ≥ 16 px (geen iOS-zoom);
- licht en donker zijn getest op elke breedte;
- schermafdrukken op 360/390/768/1440 × licht/donker horen bij elke prototype- en releasestap.

### 9.4 Offline en reconnect (PWA)

- Zonder HTTPS geen service worker en geen clipboard-API (E-34). De UI zegt dat eerlijk (S-169) en heeft een terugval
  voor kopiëren (C-15).
- Offline: T-10. Waarden worden onbekend of verouderd, acties zijn uitgeschakeld, er staat nooit een mutatie in de
  wachtrij. Na het herstel worden alle gegevens opnieuw opgehaald en daarna pas als vers getoond.
- De eventstream krijgt een backoff met een zichtbare aftelling (T-10b). Bij een terugkeer na lange tijd ververst de
  pagina zich volledig.
- Echte tests: een Android-telefoon (wifi uit/aan, VPN) en de vliegtuigmodus.

---

## 10. Bestaande apps: wat "alleen uiterlijk" inhoudt

- **Mag wel:**
  - tokens (kleur, typografie, radius, schaduw, beweging), componentstijl, iconenset (lucide is al in MediaGuard en MSO),
    statuslabels en -symbolen, focusstijl;
  - thema-mechanisme Systeem / Licht / Donker. MediaGuard heeft dit al; my_house nu alleen het systeemthema. Een
    wisselknop toevoegen is een UI-wijziging; zie O-09.
- **Mag niet:** routes, schermstructuur, functies, teksten met domeinbetekenis of de API-koppeling wijzigen. De
  ontwerpdocumenten van MediaGuard (S1–S21, sneltoetsen, integriteitsslotjes) blijven gelden; alleen de visuele laag
  gaat naar de platformtokens.
- **Domeinbetekenis behouden:**
  - my_house: `heat`/`cool` (verwarmen/koelen), `boiler`, `light-on`, `stale`;
  - MediaGuard: `lane-gpu`/`lane-cpu`, integriteit-slot, AV1;
  - MSO: de recharts-grafieken (straks met de dataviz-palet).

  Deze worden **domeinrollen** in de platformtokens, zodat ze niet botsen met de statusrollen.
- **Techniek per app:**
  - MediaGuard en MSO hebben Tailwind 4 + CSS-variabelen. De platformtokens kunnen `--mg-*` vervangen of mappen.
    MediaGuard heeft al een `components.json` (new-york).
  - my_house heeft **geen Tailwind**. De minst ingrijpende weg is de platformtokens als CSS-variabelen toe te passen op
    de bestaande variabelen (`--bg`, `--surface`, …). Een Tailwind-migratie van my_house is een aparte beslissing (O-10).
- **Lettertypen:** MediaGuard en MSO bundelen Inter en JetBrains Mono lokaal, my_house Inter en Space Grotesk, de Hub
  gebruikt een systeemfont. De platformkeuze bepaalt of die bundels blijven of verdwijnen (O-01).
- **Contrast:** het MediaGuard-rapport (82 combinaties AA) is de lat. Na het overzetten wordt het contrast voor alle
  vier de oppervlakken opnieuw berekend.

---

## 11. Open ontwerpbesluiten (in ADR's vast te leggen door de ontwerp-agent)

| # | Besluit | Opties | Voorlopige richting en waarom |
|---|---|---|---|
| O-01 | Lettertype | Systeemfont / lokaal gebundelde Inter (+ mono) | Te kiezen in de tokenstap. Inter is al in 3 apps lokaal aanwezig (consistentie). Systeemfont kost 0 KB en past bij de statuspagina's (die geen font mogen laden). |
| O-02 | Standaardthema | Systeem / donker / licht | **Systeem** voor de Hub, my_house en de statuspagina's. MediaGuard en MSO volgen de platformstandaard, maar de gebruiker kan donker kiezen. |
| O-03 | Verouderde gegevens | Wissen (Hub P0) of "laatst bekend" gedempt tonen | **Laatst bekend + "verouderd" + status onbekend + een gat in de grafiek.** Dit sluit aan bij B06-006 en EX24 ("oude data met stale-markering") en is bruikbaarder dan een leeg vak. Vraagt een aanpassing in de Hub-code. |
| O-04 | Desktop-ingangen voor Apps, Problemen, AI, Goedkeuringen en Zoeken | Kopbalk / zijbalk uitbreiden | **Kopbalk**, zodat de zijbalk exact volgens 08_UI blijft. Apps onder Server (zoals in ADR-0009). |
| O-05 | Rechten van de rol `kind` in de Hub | — | De kleinste set: Home (kind), Media (eigen), Zoeken (`kid_allowed`), Mijn profiel. Bevestigen met de API-bouwer. |
| O-06 | Wie mag R2/R3 goedkeuren | admin / operator | De UI is **server-gestuurd** (de API levert "mag goedkeuren" + "wie wel"). Er wordt niets hardgecodeerd. |
| O-07 | Productnaam in de UI | "AI Server Manager" / "Hub" / "Thuisplatform" | Vraag aan de gebruiker, of beslis in een ADR. "Hub" is kort en past bij de docs. |
| O-08 | Kleur van een dichte gate | rood / neutraal slot | **Slot + aandacht/neutraal.** Rood alleen bij een gemeten falen (K2, T-14a). |
| O-09 | Thema-wisselknop in my_house | toevoegen / alleen systeem | Telt als een kleine UI-toevoeging. Valt binnen "uiterlijk" als de knop de functies niet raakt. Ter bevestiging. |
| O-10 | my_house naar Tailwind | ja / nee (alleen CSS-variabelen) | Eerst CSS-variabelen (de minste impact). Tailwind pas als my_house zelf de componenten gaat delen. |
| O-11 | Een "Terug naar de Hub"-link in de bestaande apps | ja / nee | Een functionele toevoeging: niet zonder akkoord van de gebruiker. |
| O-12 | Validatiestatus in de productie-UI | overal / alleen bij "Over" en hardwaregevoelige functies | **Bij "Over" (S-170) en bij functies waarvan de hardwarevalidatie ontbreekt** (Gree, GPU, OneDrive). Niet op elk scherm (ruis). |
| O-13 | Grafiekbibliotheek | recharts (shadcn chart) / eigen SVG | **recharts via shadcn chart**: MSO gebruikt het al. De dataviz-regels (tabelweergave, gaten, één as) gelden bovenop. |
| O-14 | Verspreiding van de statuspagina-CSS | gedeeld pakket / gekopieerd fragment | Een versie-gepind gekopieerd fragment per repo (de repos blijven zelfstandig), met een controle op afdrijven. |
| O-15 | Statussymbolen | tekstsymbolen (✓ ! ✕ ?) / lucide-iconen | lucide-iconen in de Hub en de apps; inline SVG met dezelfde paden op de statuspagina's. |

---

## 12. Volgende stappen (voor de ontwerp-agent)

1. **Tokens.** Kleurrollen voor licht en donker, met contrast berekend (culori + wcag-contrast) en grafiekpaletten via
   de dataviz-procedure + validator. Daarnaast typografie, ruimte, radius, beweging en breekpunten.
2. **Componentspecificaties.** C-01…C-55 met hun varianten, toestanden en a11y (`design:design-system` *document*).
3. **Prototypes.** Statische HTML met gecompileerde Tailwind en fictieve voorbeelddata die als voorbeeld is gemarkeerd.
   Te maken:
   - Home;
   - de onboarding met gates (de K1-oplossing);
   - de appdetail met tabs;
   - de problemen-inbox en een incident;
   - de actie-preview en een R3-goedkeuring;
   - de backupdekking;
   - Huis met de boiler;
   - de statuspagina van de executor.

   Elk scherm op 360/390/768/1440 in licht en donker, met de toestanden unknown, stale, fout, offline, gate en kind.
4. **Controles.** `design:accessibility-review` en `design:design-critique` op de prototypes; `design:ux-copy` op alle
   toestandsteksten.
5. **Overdracht.** `design:design-handoff` per repo, en ADR's voor O-01…O-15.
