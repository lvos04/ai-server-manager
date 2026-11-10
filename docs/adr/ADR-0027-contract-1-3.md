# ADR-0027 — Contract 1.3 vastgesteld: besluiten van de gebruiker, Emby en twee mediaservers, strengere koppelregels

Status: aangenomen · 2026-11-10 · ronde "contract 1.3" · eigenaar contract: `ai-server-manager`
Bouwt op: ADR-0011 en ADR-0012 (contract 1.2), ADR-0016…0020 (B03), ADR-0021…0023 (P1-uitbreidingen van de Hub),
ADR-0025/0026 (reviews).
Invoer: `docs/platform-v2/CONTRACT_1.3_KANDIDATEN.md` (74 groepen; alle 36 groepen van klasse a).
Resultaat: `docs/platform-v2/PLATFORM_CONTRACTEN.md` (`contracts 1.3`) en `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`
(per repo, alle 11, met bestanden en moment).

## Context

Sinds contract 1.2 meldden de bouwers en reviewers van ronde 2 samen 151 contractpunten. Daarnaast lagen er
contractdelta's uit het B03-plan (hoofdstuk 18, ADR-0016…0020), nieuwe besluiten van de gebruiker (Emby is de huidige
mediaserver, MediaGuard volgt Emby én Jelly Leon, HARDE EIS voor kijkgeschiedenis en MediaGuard-voortgang, alle repos
publiek met GPL-3.0, MediaGuard in een nieuwe repo), de validatiewaarde "Intel-iGPU-getest (ontwikkelmachine)", en routes
die de Hub in P1 bouwde zonder dat het contract ze kende (heartbeat, log-sink, eventgrenzen, `max_age`, eigenaar-connector
voor `sso.*`, back-upbevestiging, catalogusbeschikbaarheid, `client_secret`). De inventaris ontdubbelde dat tot 74 groepen;
36 vragen een contractwijziging, elk met een tekstvoorstel.

Bij het lezen van de code van alle repos (2026-11-10) bleek bovendien dat de diensten op sommige punten elk iets anders
deden, omdat 1.2 het niet vastlegde: de `Referrer-Policy` en de omgang met `Origin: null`, de vingerafdruk bij twee
policy-sleutels, de namen van de koppel-events, of een healthcheck als root mag draaien.

## Besluiten

1. **Alle 36 groepen (a) zijn overgenomen** zoals de inventaris ze voorstelt, met de preciseringen hieronder. Het
   wijzigingslog bovenaan het contract noemt per punt de groep; `apps/api/tests/unit/test_contract_13.py` controleert dat
   elke groep A01–A36 in het wijzigingslog en in de conformiteitslijst staat.
2. **Bij tegenstrijdige bronnen is de veiligste lezing gekozen:**
   - `GET /api/v1/mediaserver/status` "als lijst per server" (bron) tegenover "bestaande clients mogen niet breken"
     (§2.3 regel 1): een **extra** veld `servers[]`; de velden op het hoogste niveau blijven en beschrijven de eerste
     server.
   - Δ-CONTRACT-MG (B03-plan: de Hub mag MediaGuard laten zoeken en herstellen) tegenover het open besluit BG-05:
     de acties staan in het contract als **gereserveerd, niet toegestaan** tot BG-05 én sleutelscopes in MediaGuard
     (P3-02). Tot dan alleen een deeplink (`handmatig_in_mediaguard`).
   - `Origin: null` (home-control-hub en zoeken accepteerden hem, appstore, jelly-leon-platform en de executor niet):
     de **strengste** regel voor iedereen — `Referrer-Policy: same-origin`, exacte `Origin`, `Sec-Fetch-Site` — omdat een
     andere app op hetzelfde NAS-adres dezelfde *site* is en SameSite-cookies dan meegaan.
   - Vingerafdruk met twee policy-sleutels (home-control-hub en appstore sorteren alle thumbprints, zoeken nam de laatst
     gepinde): **sorteren over alle sleutels**. Met één policy-sleutel is de uitkomst gelijk aan 1.2, dus de bestaande
     testvectoren blijven. Nieuwe testvector `HN69-2PHK-XV2D-X85W`, onafhankelijk nagerekend in de contracttest.
   - GPU-modellen uit het B03-plan zijn door D08 niet gemeten: het contract noemt alleen **rollen** ("de GPU die
     D08/BG-27 toewijst"), geen hardware als feit.
   - Android-ID's: de regel wordt "nooit een ID, accounttype, authority, permissie, `app_search_suggest_*` of
     sharedpref-naam gelijk aan die van een officiële app" (wat de regel beschermt, en wat CI al bewaakt) in plaats van
     "nooit `org.jellyfin.*`"; de gekozen ID's staan erbij met de bron (alleen de bouwopdracht) en de vraag om
     bevestiging. Niet verspreiden en geen Apple-registratie vóór die bevestiging.
3. **DNS-rebinding: de `Host`-beperking is aangenomen** (de inventaris liet dit aan de contractreview). Een POST op een
   koppel- of sleutelformulier mag alleen als de `Host`-header een IP-adres, een naam zonder punt of een naam onder
   `.local`, `.lan`, `.internal` of `.home.arpa` is. *Waarom:* zonder deze regel kan een website die iemand op het LAN
   bezoekt via rebinding dezelfde oorsprong krijgen (dan helpen `Origin` en `Sec-Fetch-Site` niet) en een nog nooit
   gekoppelde dienst aan een eigen "Hub" koppelen. Rebinding vraagt een publieke domeinnaam, en die valt nu buiten de
   lijst. *Kosten:* wie een statuspagina via een eigen domeinnaam opent, kan daar niet koppelen; env-enrollment (de
   aanbevolen weg) en koppelen via de Hub blijven werken, en de pagina zegt dat de gebruiker het IP-adres moet gebruiken.
4. **Bounding set bij een start als root: verplicht** (het voorstel zei "aanbevolen"). Het kost per image een paar regels
   (`PR_CAPBSET_DROP` vóór de wissel, zoals home-control-hub en appstore-en-fork al doen) en sluit een terugweg naar
   capabilities via een later `execve` dubbel af. Bij "Custom User 568" kan het niet; dan blijven `CapEff`, `CapPrm`,
   `CapAmb` 0 en `NoNewPrivs 1` de eis.
5. **Log-sink: twee vaste grenzen** in plaats van "één grens": invoer `bericht` ≤ 8000 tekens (langer → 422, zoals de Hub
   nu doet) en opslag na schoning ≤ 2000 tekens, zichtbaar ingekort. De regel "invoer nooit eerst afkappen" (§5) gaat
   over controleren; inkorten bij opslag ná de controle is iets anders. Eén grens van 2000 op de invoer zou een dienst
   met een lange stacktrace een hele batch laten verliezen.
6. **Paginering met momentopname** geldt voor lijsten die uit een meting komen (inventaris, catalogus,
   zoekresultaat), niet voor elke tabel: een gewone tabel met een stabiele sorteersleutel heeft geen momentopname.
7. **Scopes dienst → Hub:** `inventaris.lezen` voor appstore-en-fork en jelly-leon-platform; `catalogus.lezen` (route in
   P2) voor home-control-hub en jelly-leon-platform; `besluiten.lezen` standaard aan **geen** dienst (gemeten: geen
   dienst leest nu besluiten van de Hub); het connector-itemtype `backup.self` van de Hub alleen voor gebruikers. Een
   403 `scope_ontbreekt` is nooit een intrekking.
8. **Enroll-antwoord `schema_version: "1.3"`** met het nieuwe veld `rotation_sequence`. Gemeten: home-control-hub,
   appstore-en-fork, jelly-leon-platform, zoeken-en-persoonlijke-ai en de executor controleren alleen major 1 en negeren
   onbekende velden; een 1.3-Hub breekt dus geen 1.2-dienst. Een 1.2-Hub stuurt geen `rotation_sequence`: dan 0.
9. **Oude tokens pas intrekken bij het eerste gebruik van het nieuwe** bij een nieuwe enrollment van een bestaande
   registratie; zo breekt een mislukte herkoppeling (bv. verkeerde vingerafdruk) de bestaande koppeling niet, zoals §3.8
   al beloofde. Intrekken door een beheerder blijft direct.
10. **Foutcatalogus:** de codes van de Hub (ADR-0016) worden de platformtabel. 423 `item_in_playback` (Jelly Leon) is de
    enige eigen statuscode buiten de tabel; verder `details.reason` of een eigen code onder 409. `invalid_totp` wordt
    422: 401 betekent alleen "niet (meer) aangemeld".
11. **Ontwerpreview:** het contract neemt de testmatrix en normen van ONTWERPTAAL §12 letterlijk over (320–1440, WCAG 2.2
    AA). De controles mogen in een apart reviewgereedschap draaien zolang ze in CI draaien (zoals `apps/web/review`).
    Peil-zaken uit de inventaris (E01–E16) wijzigen het contract niet en gaan naar Peil 1.1.1.
12. **EVIDENCE-ID's voor contractpunten:** `C1.3-<REPO>-<nn>` uit de conformiteitslijst, `C1.2-<code>` voor 1.2 en
    `REVIEW-<repo>-<onderwerp>`. `update_excel.py` moet ze apart melden (C1.3-ASM-15); tot dat gebouwd is, schrijft deze
    repo zulke regels nog niet in zijn eigen `EVIDENCE.json`.
13. **Kopieën:** byte-gelijk met drifttest; verwijzingen naar deze repo als tekst `ai-server-manager:<pad>`. Daarom
    bevatten het contract en de conformiteitslijst geen enkele relatieve link (ook geen link naar een bestand in dezelfde
    map); de contracttest bewaakt dat.

## Alternatieven

- *Alleen de groepen met een NU-moment opnemen en de rest in 1.4:* verworpen. De (a)-groepen met een later moment
  (P2/P3/P4) leggen grenzen vast die nu al gelden (bv. "gereserveerd tot BG-05", "Emby nooit schrijven"); zonder tekst
  bouwt een repo er ongemerkt omheen.
- *De `Host`-beperking alleen aanbevelen:* verworpen; een aanbeveling geeft bij vijf diensten vijf keuzes, terwijl het
  restrisico (koppelen aan een vreemde Hub vóór de eerste koppeling) juist de zwakste plek van §3.7 is.
- *`servers[]` als vervanging van de bestaande velden (letterlijk "lijst per server"):* verworpen; bestaande clients
  (web, Android, MSO) zouden breken (§2.3 regel 1).
- *`Origin: null` accepteren met alleen de double-submit-cookie:* verworpen; een andere app op hetzelfde NAS-adres kan
  dan met de cookie meeliften.

## Gevolgen

- Elke repo heeft werk; de lijst per repo staat in `CONTRACT_1.3_CONFORMITEIT.md` met per punt NU of de fase (P2, P3,
  P4-0, P4, P5). De volgorde: kopieën, dan de Hub (enroll, scopes, momentopname, inbox), dan de validator van
  appstore-en-fork, dan de diensten; de bestaande apps in P3.
- Contract 1.2 blijft als historie in het wijzigingslog; `CONTRACT_1.2_CONFORMITEIT.md` blijft staan.
- Open besluiten van de gebruiker staan in contract §1.2, elk met wat tot dan geldt: BG-05, BG-04, BG-06/BG-18,
  `100.64.0.0/10` voor de noodlogin, bevestiging van de Android-ID's en de Swiftfin-bundle-id, het GHCR-pakket van de
  nieuwe MediaGuard-repo, `JL_SYNC_PUSH_TOKEN`.
- Restrisico's die blijven: koppelen aan een vreemde Hub vóór de eerste koppeling via het IP-adres (kleiner, niet weg);
  het korte root-venster van een healthcheck vóór de wissel; de 1 MiB-grens pas na authenticatie in het Jellyfin-proces
  tot de spike slaagt; LAN-verkeer over HTTP tot B10/B13.
- Niets hiervan is op een echte NAS, met echte accounts of op echte hardware gevalideerd.

## Verificatie

- `apps/api/tests/unit/test_contract_13.py`: kop `contracts 1.3`; elke groep A01–A36 in het wijzigingslog en in de
  conformiteitslijst; geen relatieve links in beide documenten; alle 11 repos met een eigen hoofdstuk; elke regel in de
  conformiteitslijst met een unieke ID en een geldig moment; de drie testvectoren onafhankelijk nagerekend en letterlijk
  in het contract; de nieuwe validatiewaarden in §11.
- `apps/api/tests/unit/test_keyset_fingerprint.py` en `test_contract_13_kandidaten.py` blijven groen.
