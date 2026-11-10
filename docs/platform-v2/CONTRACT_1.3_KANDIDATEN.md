# Contract 1.3 — kandidaten (inventaris van alle meldingen sinds contract 1.2)

Status: **inventaris, geen contract — verwerkt in contract 1.3** (2026-11-10, `ai-server-manager:docs/adr/ADR-0027-contract-1-3.md`)
· Peildatum 2026-11-10 · Eigenaar `lvos04/ai-server-manager` · Invoer voor de volgende stappen: contract 1.3 (alle
groepen **(a)**, nu in [`PLATFORM_CONTRACTEN.md`](PLATFORM_CONTRACTEN.md) `contracts 1.3` en
[`CONTRACT_1.3_CONFORMITEIT.md`](CONTRACT_1.3_CONFORMITEIT.md)), Peil 1.1.1 (alle groepen **(e)**) en het werk per repo
(groepen **(c)**, ook per repo in de conformiteitslijst). Waar het contract een voorstel hieronder preciseert of
strenger maakt, wint het contract (keuzes K1–K9 in het wijzigingslog). Dit document wijzigt geen code in andere repos.

## 0. Werkwijze

**Bronnen** (gelezen of doorzocht op 2026-11-10, branch `ccr-c133d7a0-kuz1cv` van elke repo):

1. `contract-issues-ronde2.json` (lokaal in de werkmap, niet in git) — de 151 `contract_issues` uit de eindrapporten
   van ronde 2 (8 repos). Een byte-gelijke kopie (sha256 `ad9d5e05…cb3d87`) staat naast dit document:
   [`CONTRACT_1.3_MELDINGEN_RONDE2.json`](CONTRACT_1.3_MELDINGEN_RONDE2.json).
   **ID `R2-nnn` = positie nnn (vanaf 1) in die lijst.**
2. Contractpunten in de ADR's van `home-control-hub` (ADR-0008 t/m ADR-0013) en in de ADR's, reviews en `EVIDENCE.json`
   van alle repos sinds contract 1.2 → ID's `X-nn` (alleen wat niet letterlijk al in de 151 staat, of wat extra bewijs
   geeft).
3. Contractdelta's uit het B03-plan (`02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` hoofdstuk 18) en ADR-0016…0020 van
   deze repo → ID's `Δ-…` en `ADR-00nn`.
4. Feiten en besluiten van de gebruiker (`OVERDRACHT/STATUS.md`, `02_BOUWPLANNEN/B03_BESLUITEN.md`) → ID's `U-nn`.
5. De validatiewaarde "Intel-iGPU-getest (ontwikkelmachine)" voor §11 → `U-07`.
6. Hub-uitbreidingen uit P1 die nog niet in het contract staan → ID's `P-nn`.
7. Peil-verbeterpunten uit de ontwerpreviews (`docs/ontwerp/PEIL_REVIEW.md` in my_house, media-source-optimizer,
   media-guard-ultimate, ai-server-manager en de vier statuspagina-reviews) → in de groepen (e), met ID's `X-nn` waar
   ze niet al in de 151 staan.

**Klassen:**

| Klasse | Betekenis | Wat er met de groep gebeurt |
|---|---|---|
| **(a)** | contractwijziging nodig | tekstvoorstel hieronder; de stap "contract 1.3" verwerkt elke (a)-groep |
| **(b)** | al opgelost in code of contract | bewijs genoemd; geen contractwerk (hooguit een verduidelijkende zin) |
| **(c)** | repo-bug of repo-keuze, geen contractzaak | repo genoemd; gaat naar de backlog van die repo |
| **(d)** | afwijzen | reden genoemd |
| **(e)** | Peil-ontwerpzaak | voorstel voor Peil 1.1.1 (ontwerp-agent; `ONTWERPTAAL.md` + `design/ontwerptaal/`) |

**Ontdubbelen:** meldingen over hetzelfde onderwerp vormen één groep. Elke melding staat in precies één groep
(kolom *Groep*); raakt ze ook een andere groep, dan staat die onder *Ook in*. De volledige tabellen staan in §10
(151 meldingen) en §11 (overige bronnen). `apps/api/tests/unit/test_contract_13_kandidaten.py` controleert dat elke
melding precies één keer in een bestaande groep staat en dat elke (a)-groep een tekstvoorstel en geraakte repos heeft.

**Eerlijkheid:** uitspraken als "gemeten in de code" zijn gelezen of gezocht in de broncode op de peildatum (grep, geen
uitvoering), tenzij er een test bij staat. Niets in dit document is op een echte NAS, met echte accounts of op echte
hardware gevalideerd.

**Afkortingen repos:** ASM = ai-server-manager (Hub + executor) · HCH = home-control-hub · ASF = appstore-en-fork ·
JLP = jelly-leon-platform · ZPA = zoeken-en-persoonlijke-ai · JL = jelly-leon · JLW = jelly-leon-web ·
JLC = jelly-leon-clients · MGU = media-guard-ultimate · MSO = media-source-optimizer · MH = my_house.

## 1. Telling

| Klasse | Betekenis | Groepen | Meldingen ronde 2 | Overige bronnen |
|---|---|---|---|---|
| (a) | contractwijziging | 36 | 78 | 50 |
| (b) | al opgelost | 8 | 11 | 2 |
| (c) | repo | 12 | 17 | 10 |
| (d) | afwijzen | 2 | 2 | 1 |
| (e) | Peil | 16 | 43 | 13 |
| | **totaal** | **74** | **151** | **76** |

Herhalingen in de bron (meestal bouwer + reviewer van dezelfde repo): R2-043/019, R2-044/018, R2-047/002, R2-048/027,
R2-049/029, R2-086/062/005, R2-107/085/025/014, R2-138/129, R2-139/130, R2-141/132, R2-142/135, R2-149/145.

## 2. Overzicht van de groepen

| Groep | Klasse | Onderwerp | Plek | Meldingen ronde 2 | Overige bronnen | Geraakte repos |
|---|---|---|---|---|---|---|
| [A01](#a01) | (a) | Besluiten van de gebruiker sinds 1.2: publiek, GPL-3.0, nieuwe MediaGuard-repo | §1.1, §2.1, §10 | — | U-05, U-06, U-08 | alle 11 |
| [A02](#a02) | (a) | Eigen applicationId/bundle-id: regel 'nooit een officiële ID' en de gekozen ID's | §1.1 besluit 1, §2.3 regel 6 | 027, 028, 029, 030, 048, 049 | — | JLC, ASM |
| [A03](#a03) | (a) | Emby als bestaande app, MediaGuard volgt Emby én Jelly Leon, HARDE EIS | §2.3 (nieuw: regel 7–8) | — | U-01, U-02, U-03, U-04, Δ-MG-AUTH, Δ-MG-DUAL, ADR-0020 | ASM, MGU, JL, ASF |
| [A04](#a04) | (a) | Jelly Leon: upstream-conventies, Hub-koppeling JL4, 12.x-auth, 1 MiB per route | §2.3, §5 | 003, 046 | ADR-0017 | JL, ASM |
| [A05](#a05) | (a) | MediaGuard-acties via de Hub (Δ-CONTRACT-MG) gereserveerd; Jelly Leon als viewerclient | §2.3 regel 2–3, §8 | — | Δ-CONTRACT-MG, Δ-HUB-1, ADR-0018 | ASM, MGU, JL |
| [A06](#a06) | (a) | Optionele model-apps: app `mt`, één producent per soort, GPU-rol | §1, §2 | — | Δ-CONTRACT-MT, Δ-CONTRACT-MODEL, ADR-0019 | ASM, JL, ZPA, ASF |
| [A07](#a07) | (a) | 100.64.0.0/10 niet meer standaard privé | §4.1 | — | Δ-CONTRACT-NET | ASM, HCH, JL |
| [A08](#a08) | (a) | Healthcheckproces en bounding set bij start als 568 | §2.2, §10 | 001, 002, 034, 045, 047 | — | ASM, ASF, MSO, MGU, MH, JL, HCH, JLP, ZPA |
| [A09](#a09) | (a) | Term `custom_app` en catalogusapp voor apps met één container | §1, §2, §9 | 053, 079 | — | ASM, ASF, JLP |
| [A10](#a10) | (a) | Geheimen die een app niet zelf maakt: catalogus-values en OIDC-clientgeheim | §3.1, §4.4, §9 | — | P-07, X-17 | ASM, HCH, JLP, ASF |
| [A11](#a11) | (a) | Adresregels (IP-vorm), `base_url` en `HUB_*` buiten het manifest | §3.2, §3.3, §9 | 038, 040, 121 | — | HCH, ASF, JLP, ZPA, ASM |
| [A12](#a12) | (a) | `hub-link.json`: onleesbaar bestand, open codelijst, extra velden | §3.5, §3.8 | 036, 119 | X-03, X-05 | HCH, ASF, JLP, ZPA, ASM |
| [A13](#a13) | (a) | Herkomstcontrole koppelformulier: Referrer-Policy, Origin, Sec-Fetch-Site, browsertest | §3.7, §3.9 | 083, 095, 096, 145, 149 | X-41 | HCH, ZPA, ASF, JLP, ASM |
| [A14](#a14) | (a) | Overige regels koppelformulier: pogingen, koppelen bezig, meldingen, log, DNS-rebinding | §3.7 | 035, 125 | X-12, X-14 | HCH, ASF, JLP, ZPA, ASM |
| [A15](#a15) | (a) | 'Gereed' op de statuspagina tegenover `/readyz` | §3.7, §5, §13 | 006, 075 | — | HCH, ASF, JLP, ZPA, ASM |
| [A16](#a16) | (a) | JWT-controles: `aud`, reason-tabel, `jti` per POST, auth vóór bodyvalidatie | §4.2, §4.3, §4.6, §4.7 | 033, 037, 120 | X-04, X-06, X-10 | HCH, ASF, JLP, ZPA, ASM, JL |
| [A17](#a17) | (a) | Sleutelpinning en rotatie: meerdere policy-sleutels, `rotation_sequence`, oude tokens | §3.3, §3.6, §4.5 | 032 | X-07, X-08, X-09, X-11 | ASM, HCH, ASF, JLP, ZPA |
| [A18](#a18) | (a) | Dienst → Hub: alleen-lezen routes en scopes (inventaris, catalogusbeschikbaarheid) | §4.4, H13 | 063 | P-06, P-09 | ASM, ASF, HCH, JLP |
| [A19](#a19) | (a) | Hub-uitbreidingen heartbeat en log-sink | §4.4, §6 (nieuw §6.1) | 050, 111 | P-01, P-08 | ASM, HCH, ASF, JLP, ZPA |
| [A20](#a20) | (a) | Uitzonderingen op `Idempotency-Key` | §5 | 051, 117, 150 | — | ASM, HCH, ASF, JLP, ZPA |
| [A21](#a21) | (a) | Foutcatalogus, 401-betekenis, paginering met snapshot, invoer niet afkappen | §5 | 124, 137 | ADR-0016, X-13 | alle diensten, JL, ASM |
| [A22](#a22) | (a) | Connector-health: vaste checknamen en totaal = slechtste | §6 | 052, 123 | — | ASM, HCH, ASF, JLP, ZPA, JL |
| [A23](#a23) | (a) | Versheid: `observed_at` en `max_age` per capability | §1, §6 | 070, 087, 122 | P-03 | ASM, HCH, ASF, JLP, ZPA |
| [A24](#a24) | (a) | Events: envelopegrenzen, werkwoorden, domeinen per eigenaar, vaste `service.*`-namen | §7 | 109, 118 | B03-§10.10, P-02, X-01, X-40 | ASM, HCH, ASF, JLP, ZPA, JL |
| [A25](#a25) | (a) | Ernst: vijf Peil-woorden, optioneel in de payload, vaste afbeelding | §7 | 110, 129, 138 | — | ASM, alle eventbronnen |
| [A26](#a26) | (a) | `sso.access.revoked` met OIDC-`sub` | §7 | 112 | — | HCH, ASM |
| [A27](#a27) | (a) | SSO in de Hub: groep→rol, sessieduur, https, terugkeerpad | §4.1 | 113, 114, 115, 151 | — | ASM, HCH, MGU, MSO, MH |
| [A28](#a28) | (a) | Eigenaar-connector-acties (sso.*) en back-upbevestiging per app | §6, §8 | — | P-04, P-05 | ASM, HCH, MH, MSO, MGU |
| [A29](#a29) | (a) | TrueNAS alleen-lezen: `core.subscribe` voor `reporting.realtime` | §8 | 055 | — | ASM |
| [A30](#a30) | (a) | Manifeststandaard: geaccepteerde bevindingen, checklist, controles na installatie, poorten | §9 | 077, 078, 081, 082, 128 | — | ASF, JLP, alle repos met manifest |
| [A31](#a31) | (a) | Adoptie van bestaande apps: `kind: adoption`, eigenaar, statuswoorden | §9, 02_DATA_EIGENAARSCHAP | 065, 066, 067 | — | ASF, ASM |
| [A32](#a32) | (a) | Monitorplan per app (endpoint, verwachte status, time-out) | §9, B09 | 127 | — | ASM, JLP, ASF |
| [A33](#a33) | (a) | EVIDENCE (§11): nieuwe validatiewaarden, ID's buiten de Excel, consistentieregels | §11 | 005, 042, 062, 084, 086, 136, 146 | U-07, Δ-ASM-EXCEL, X-15, X-42 | alle 11 |
| [A34](#a34) | (a) | Ontwerpreview: breedtes 320–1440 en WCAG 2.2 AA | §13, §10 | 093, 144 | — | ASM, HCH, ASF, JLP, ZPA, MGU, MSO, MH |
| [A35](#a35) | (a) | Contractkopie: byte-gelijk en zonder kapotte relatieve links | kop, §13 | 017, 018, 044 | — | alle 11 |
| [A36](#a36) | (a) | Hub-adres voor 'Terug naar de Hub' in bestaande apps | §2.3 regel 5, §3.2 | — | X-19 | MGU, MSO, MH |
| [B01](#b01) | (b) | Formuliernamen `hub_adres`/`koppelcode`/`hub_vingerafdruk` | Peil-sjabloon | 011, 015, 143 | — | — |
| [B02](#b02) | (b) | otpauth-issuer 'TrueNAS Home Platform' | ADR-0024 punt 11 | 133 | — | — |
| [B03](#b03) | (b) | §10-kwaliteitseisen gelden niet voor webclient en apparaat-apps | §2, §10 | 019, 031, 043 | — | — |
| [B04](#b04) | (b) | Koppelstatus na ontkoppelen alleen via de 401-reason | §3.8 (R5), §4.7 | 039 | — | — |
| [B05](#b05) | (b) | Scan vóór publiek maken (programmabreed uitgevoerd) | §1.1 besluit 3 | 020 | — | — |
| [B06](#b06) | (b) | Eén specifieke render-node: al open punt in §9 | §9 | 004 | — | — |
| [B07](#b07) | (b) | 44 px voor losse links: recept `.losse-link` (C-63) | COMPONENTEN §28 | 148 | — | — |
| [B08](#b08) | (b) | Adviezen van home-control-hub en adapterroutes van my_house: al conform | §2.3, §6 | — | X-02, X-34 | — |
| [C01](#c01) | (c) | Hub-API-gemak: sorteren, filteren, poolstatus, open koppelcodes | — | 132, 134, 135, 140, 141, 142 | — | ASM |
| [C02](#c02) | (c) | Hub-catalogus: readback aan de verkeerde image, fake-imagenaam MediaGuard | — | 068, 069 | — | ASM |
| [C03](#c03) | (c) | Hub-keuzes die al binnen het contract passen | — | 054, 056, 116, 131 | — | ASM |
| [C04](#c04) | (c) | Testgat: ontkoppelen via de Hub-route niet end-to-end | — | 041 | — | ASM |
| [C05](#c05) | (c) | ADR-nummering tussen gelijktijdige bouwers | — | 057 | — | ASM |
| [C06](#c06) | (c) | Appstore-keuzes bij herkenning en inventaris | — | 064, 071 | X-16 | ASF |
| [C07](#c07) | (c) | Bouwplan B03 en jelly-leon-web: namen van haken en registers | — | — | X-18 | ASM (bouwplan), JLW |
| [C08](#c08) | (c) | I01 stap 3 schrijft shellopdrachten voor | — | 080 | — | ASM (pakket), JLP |
| [C09](#c09) | (c) | MediaGuard en my_house: functionele vervolgpunten uit de Peil-review | — | — | X-20, X-24, X-33 | MGU, MH |
| [C10](#c10) | (c) | MSO: functionele vervolgpunten uit de Peil-review | — | — | X-25 | MSO |
| [C11](#c11) | (c) | Hub-UI: vervolgpunten uit de Peil-review | — | — | X-35 | ASM |
| [C12](#c12) | (c) | B03-deltaverzoeken die repowerk zijn (geen contracttekst) | B03 h18 | — | Δ-MG-1…8, Δ-MG-DV, Δ-HUB-2, Δ-HUB-3, Δ-HUB-JL, Δ-ZK-1, Δ-ZK-2 | ASM, MGU, ZPA |
| [D01](#d01) | (d) | Witte lijst van §3.5 als verplichting lezen | §3.5 | 026, 076 | — | — |
| [D02](#d02) | (d) | Forced colors: rand ook op de Gezond-pil | Peil | — | X-39 | — |
| [E01](#e01) | (e) | Sjabloon: blok voor een onleesbare koppelstatus | ONTWERPTAAL §13.2 | 007, 012, 021, 058, 072, 092, 100 | — | Peil → 5 statuspagina's |
| [E02](#e02) | (e) | Sjabloon: aparte weergave 'Koppelen bezig' | ONTWERPTAAL §13.2 | 073 | — | Peil → 5 statuspagina's |
| [E03](#e03) | (e) | Sjabloon: tonen en iconen per rij (nog niet, niet beschikbaar, beleid, verouderd, feit) | ONTWERPTAAL §4.3, §7 | 008, 059, 089, 097, 102, 108 | X-37 | Peil → 5 statuspagina's |
| [E04](#e04) | (e) | 'Niet gekoppeld' in de controles: één icoon per betekenis | ONTWERPTAAL §7, COMPONENTEN §4/§25 | 088, 098, 106 | — | Peil |
| [E05](#e05) | (e) | Rol van de melding (alert/status/geen) | COMPONENTEN C-14 | 060, 090, 103 | — | Peil → 5 statuspagina's |
| [E06](#e06) | (e) | Codes en lange woorden in meldingen en redenen | ONTWERPTAAL §5, §11.2 | 013, 022, 061, 091, 099, 104 | — | Peil → 5 statuspagina's |
| [E07](#e07) | (e) | Referentie-renderer: één doorgang | ONTWERPTAAL §13.2 | 014, 025, 085, 107 | — | Peil + 5 renderers |
| [E08](#e08) | (e) | Drift- en pinregel van de kopieën | ONTWERPTAAL §13.2, §14 | 010, 016, 023, 024, 074 | — | Peil + alle kopieën |
| [E09](#e09) | (e) | Overige sjabloonpunten: novalidate, (verplicht), skiplink, knop, rijopbouw, bron | ONTWERPTAAL §9, §12, §13.2 | 009, 101, 105 | X-36, X-38 | Peil → 5 statuspagina's |
| [E10](#e10) | (e) | Totaalstatus van een statuspagina: wat telt mee | ONTWERPTAAL §4.3, §13.2 | 094, 126 | — | Peil, HCH, ASF |
| [E11](#e11) | (e) | Zekerheid als woord met vaste drempels | ONTWERPTAAL §4 (T-24) | 130, 139 | X-26 | Peil, ASM, MSO |
| [E12](#e12) | (e) | Reflow testen met het lettertype van de CI-runner | ONTWERPTAAL §12 | 147 | — | Peil |
| [E13](#e13) | (e) | Woorden: 'Niet beschikbaar' (aflevering) en 'Verzonden' | ONTWERPTAAL §11 | — | X-23, X-27 | Peil, MGU, MH |
| [E14](#e14) | (e) | Aliaslaag en tokens: focusring, scroll-padding, randen, -soft-vlakken | ONTWERPTAAL §13.3–§13.5, §14 | — | X-22, X-29, X-30, X-32 | Peil, MGU, MSO, MH |
| [E15](#e15) | (e) | Verouderd: regel voor statuspillen en bediening | ONTWERPTAAL §9 (O-03) | — | X-21, X-31 | Peil, MGU, MH |
| [E16](#e16) | (e) | Ondernavigatie op 320 px | ONTWERPTAAL §6 | — | X-28 | Peil, MH |

## 3. Groepen (a): contractwijziging nodig

Per groep: de meldingen, het probleem, een **tekstvoorstel** (zo dicht mogelijk bij de definitieve contracttekst),
de **geraakte repos** en wanneer het gebouwd moet worden. "NU" = in de conformiteitsronde van 1.3; anders de fase.

<a id="a01"></a>
### A01 — Besluiten van de gebruiker sinds 1.2: publiek, GPL-3.0, nieuwe MediaGuard-repo

- **Bronnen:** U-05, U-06, U-08.
- **Probleem:** 1.2 §1.1 beschrijft besluit 3 nog als voornemen, §10 zegt "geen licentie toevoegen zonder vraag aan de
  gebruiker" en besluit 5 staat op de oude stand. Gemeten in de repos: een GPL-3.0-`LICENSE` staat al in ASM, HCH, ASF,
  JLP, ZPA, MGU, MSO en MH; JL en JLW houden GPL-2.0 (upstream), JLC heeft per subtree de upstream-licentie.
- **Tekstvoorstel:**
  - §1.1 besluit 3 (vervangen): "Uitgevoerd op 2026-11-09, na de scan van de volledige historie: tien repos zijn
    publiek (de zichtbaarheid van elk GHCR-pakket wordt per pakket gecontroleerd; `STATUS.md` noemt alleen de repos).
    `media-guard-ultimate` niet: de huidige repo wordt `media-guard-ultimate-archief`
    (privé, ongewijzigd bewaard) en een nieuwe publieke `lvos04/media-guard-ultimate` met schone historie volgt na de
    Peil-ronde. Tot die repo en haar images gepubliceerd zijn, is installeren van MediaGuard zonder registry-login
    NIET GEVALIDEERD."
  - §1.1 nieuw besluit 8: "Licentie van de eigen repos: **GPL-3.0** (volledige tekst in `LICENSE`). Forks houden hun
    upstream-licentie (jelly-leon en jelly-leon-web GPL-2.0, jelly-leon-clients per subtree); upstream-credits blijven."
  - §1.1 besluit 5: "Uitgevoerd: my_house 0.2.0 is gepubliceerd." Besluit 4 blijft open (geen tokens in repos).
  - §10, laatste regel van het blok: "`LICENSE` (GPL-3.0)" in plaats van "geen licentie toevoegen zonder vraag aan de
    gebruiker".
  - §2.3, rij MediaGuard: repo "`media-guard-ultimate` (nieuwe publieke repo; oude historie in
    `media-guard-ultimate-archief`, privé)"; de imagenaam `ghcr.io/lvos04/mediaguard-core:<versie>-aio` blijft. Open punt:
    het GHCR-pakket moet aan de nieuwe repo gekoppeld worden; tot dan geen nieuwe MediaGuard-release (zie ook de HARDE
    EIS in A03, die ook voor de eerste release uit de nieuwe repo geldt).
- **Geraakte repos:** alle 11 (kopie van het contract, `LICENSE` controleren); MGU (repo-overgang); ASM (contract en
  `OVERDRACHT/STATUS.md`).
- **Uitvoering:** tekst NU; de nieuwe MediaGuard-repo zelf is een aparte stap van de gebruiker en de orkestratie.

<a id="a02"></a>
### A02 — Eigen applicationId/bundle-id: regel "nooit een officiële ID" en de gekozen ID's

- **Bronnen:** R2-027, R2-028, R2-029, R2-030, R2-048, R2-049.
- **Probleem:** §1.1 besluit 1 en JC1 zeggen "nooit `org.jellyfin.*` als ID van de fork". De bouwopdracht van ronde 2
  (`.lokaal/workflows/ronde-2.js`, JC1) gaf `org.jellyfin.mobile.jellyleon` en `org.jellyfin.androidtv.jellyleon` als
  "het voorbeeld uit ADR-0004 dat de gebruiker in het keuzemenu koos"; die ID's staan nergens in ai-server-manager. Wat de
  regel beschermt (naast de officiële app installeerbaar, geen botsing van accounttype/authority/permissie/sharedprefs)
  bewaakt jelly-leon-clients al in CI. JC2 noemt alleen `Shared.xcconfig`, maar het doel "Swiftfin iOS" zet in Release
  zelf `PRODUCT_BUNDLE_IDENTIFIER`, en die doelinstelling wint.
- **Tekstvoorstel:**
  - §1.1 besluit 1, de zin "Nooit `org.jellyfin.*` als ID van de fork" vervangen door: "Nooit een ID die gelijk is aan
    die van een officiële app (upstream of store), en geen accounttype, authority, permissie, `app_search_suggest_*`-waarde
    of sharedpref-naam die gelijk is aan die van de officiële app; CI bewaakt dit. Android-ID's (volgens de bouwopdracht
    van 2026-11-09 gekozen door de gebruiker; bevestiging gevraagd): android `org.jellyfin.mobile.jellyleon`, androidtv
    `org.jellyfin.androidtv.jellyleon`. iOS/tvOS (Swiftfin): voorstel `org.jellyfin.swiftfin.jellyleon`, **te bevestigen
    door de gebruiker vóór de eerste Apple-registratie** (NIET GEVALIDEERD (Mac/Xcode)). Na de eerste verspreiding
    verandert een ID niet meer."
  - §2.3 regel 6 en conformiteit JC2: "iOS: de bundle-id staat in `swiftfin/XcodeConfig/Shared.xcconfig` **én** in
    `project.pbxproj` (doel 'Swiftfin iOS', configuratie Release); de patch wijzigt beide en CI controleert de effectieve
    build-instelling."
  - `OVERDRACHT/STATUS.md` besluit 1: de concrete ID's toevoegen met de bron.
- **Geraakte repos:** JLC (alleen controleren; al zo gebouwd, ADR-0004/ADR-0010), ASM (contract, STATUS).
- **Uitvoering:** tekst NU; bevestiging van de ID's is een open besluit (§8).

<a id="a03"></a>
### A03 — Emby als bestaande app, MediaGuard volgt Emby én Jelly Leon, HARDE EIS

- **Bronnen:** U-01…U-04, Δ-MG-AUTH, Δ-MG-DUAL, ADR-0020 (en ADR-0018 aanvulling 7–8).
- **Probleem:** 1.2 kent Emby niet: §2.3 noemt MediaGuard, MSO, my_house en Jellyfin/Jelly Leon, en de regel "een
  stock-Jellyfin blijft ongemoeid" dekt Emby niet. MediaGuard volgt in de code één mediaserver: `GET
  /api/v1/mediaserver/status` geeft één object (`kind`, `url`, `connected`, `sessions`, `hold`, …; gemeten in
  `media-guard-ultimate/apps/core/mediaguard/mediaserver/api.py`). De HARDE EIS van de gebruiker staat alleen in het
  B03-plan en ADR-0020, niet in het contract.
- **Tekstvoorstel (§2.3):**
  - Nieuwe rij in de tabel: "**Emby** (bestaande mediaserver van de gebruiker; geen platform-repo) · installatiewijze,
    versie, poort en datasets onbekend tot D07 ze meet · eigen database (kijkgeschiedenis) · eigen UI · Emby-API".
    Regels: "Het platform schrijft nooit in Emby, stopt, update of verwijdert Emby nooit. Alleen-lezen toegang met een
    API-sleutel (alleen GET; elke andere methode wordt vóór het netwerk geweigerd) voor D07 en de overname (B03-015).
    Emby blijft de terugval tot de gebruiker hem zelf verwijdert na de controlelijst 'Emby verwijderen' (B03 §10.9.2);
    app stoppen en data verwijderen blijven aparte stappen (APP-02/A4)."
  - Nieuwe regel 7, **HARDE EIS (besluit van de gebruiker)**: "Alle kijkgeschiedenis (gezien-status, hervatpunten,
    favorieten, beoordelingen, onthouden spoorkeuzes, gebruikers, rechten) en de MediaGuard-voortgang blijven altijd
    beschikbaar. (a) Geen overstap van mediaserver zonder vóór/na-rapport per gebruiker en uitdrukkelijk akkoord van de
    gebruiker op elk verschil, ook op verschillen door upstream-migraties; de bestaande installatie blijft ongewijzigd
    als terugval. (b) Elke MediaGuard-release, ook de eerste uit de nieuwe publieke repo, bewijst een upgrade op een
    gevulde database van de vorige versie zonder gegevensverlies; UI-rondes wijzigen geen datamodel. Zonder dat bewijs
    geen release en geen update op de NAS. (c) Geen platformactie, ook niet met goedkeuring, schrijft rechtstreeks in de
    database van Emby, Jelly Leon of MediaGuard."
  - Regel 2, MediaGuard aanvullen (Δ-MG-DUAL, Δ-MG-AUTH): "MediaGuard volgt elke ingestelde mediaserver tegelijk (Emby
    én Jelly Leon): kijkpauze als iemand op één van beide kijkt, afspeeltest en NL-ondertitels per server. Authenticatie
    per server: Emby `X-Emby-Token`; Jelly Leon 12.x `Authorization: MediaBrowser Token=…` (legacy-auth blijft uit,
    BG-01). De Emby-koppeling wordt op geen enkel moment onderbroken; pas na de controlelijst laat MediaGuard Emby los.
    `GET /api/v1/mediaserver/status` krijgt **erbij** een lijst `servers: [{server_id, kind, label, connected,
    hold: {active}, …}]` per server; de bestaande velden op het hoogste niveau blijven bestaan voor bestaande clients
    (regel 1) en beschrijven de eerste server. Voor de viewerclient van Jelly Leon geldt de veldenwitte lijst van B03
    §10.5 (nooit `sessions`, `hold.reason`, `actions`, `tests`, `last`)."
  - Regel 8 (B12): "Het blijvende JSON-exportarchief van de Emby-kijkgegevens (met sha256) is een B12-dekkingsitem
    (Δ-HUB-3). Zonder bevestigde dekking geen 'Emby verwijderen'."
- **Geraakte repos:** MGU (Δ-MG-DUAL/Δ-MG-AUTH, upgradetest per release), ASM (Hub-adapter MediaGuard per server,
  B12-dekking, register), JL (overname B03-015, controle "MediaGuard hangt ook aan deze Jelly Leon"), ASF (Emby als
  adoptie-item, A31).
- **Uitvoering:** tekst NU; Δ-MG-AUTH/Δ-MG-DUAL zijn exitcriterium van P4-0; de upgradetest geldt vanaf de eerste
  release uit de nieuwe MediaGuard-repo.

<a id="a04"></a>
### A04 — Jelly Leon: upstream-conventies, Hub-koppeling JL4, 12.x-auth, 1 MiB per route

- **Bronnen:** R2-003, R2-046, ADR-0017 (ook ADR-0016 deel 1 MiB, U-03).
- **Probleem:** §2/§10 noemen `/appdata` en `/healthz`/`/readyz` "op elke dienst"; §2.3 erkent `/config` voor Jelly
  Leon, `/health` niet. De Hub-koppeling van de plugin (JL4) en wat de Hub mag zien, staan alleen in ADR-0017. Een plugin
  in het Jellyfin-proces kan de 1 MiB-grens niet vóór authenticatie garanderen.
- **Tekstvoorstel (§2.3 regels 1–2, §5):**
  - "Jelly Leon volgt de upstream-conventies: data in `/config` en `/cache` (geen `/appdata`), gezondheid op `/health`
    en `/System/Info/Public`; `/healthz` en `/readyz` zijn voor Jelly Leon niet verplicht. Nieuwe routes van de plugin
    (`/media/v1/*`, `/connector/v1/*`) volgen §5."
  - "1 MiB in het Jellyfin-proces: per route `RequestSizeLimit(1048576)` plus een `Content-Length`-controle; de afwijking
    'na authenticatie' is erkend (ADR-0016) tot de `IStartupFilter`-spike (B03-017) slaagt. Hogere grenzen alleen per
    route met ADR en eigen bovengrens."
  - "Hub-koppeling (JL4, ADR-0017): geen enrollment. De beheerder plakt de publieke Hub-sleutelset in het
    Jellyfin-dashboard en vergelijkt de vingerafdruk (§4.5); daarna gelden §4.5–§4.7 (persistente `jti`-cache, `kind`
    wint). Zonder pin 401 `not_linked`. De Hub pollt `GET /connector/v1/events` (geen push: Jelly Leon heeft geen
    service-token). Naar de Hub gaan alleen aantallen en ondoorzichtige ID's: geen titels, bestandsnamen, paden,
    item-ID's, gebruikers- of apparaatnamen of IP-adressen. `propose`/`apply`/`rollback` geven in v1 501."
  - "De Hub-adapter leest Jelly Leon 12.x met een eigen **niet-admin**-gebruiker via `Authorization: MediaBrowser
    Token=…`; `EnableLegacyAuthorization` blijft uit (BG-01)."
- **Geraakte repos:** JL (plugin), ASM (Hub-adapter, Δ-HUB-JL).
- **Uitvoering:** tekst NU; bouw in P4-0/P4.

<a id="a05"></a>
### A05 — MediaGuard-acties via de Hub (Δ-CONTRACT-MG) gereserveerd; Jelly Leon als viewerclient

- **Bronnen:** Δ-CONTRACT-MG, Δ-HUB-1, ADR-0018.
- **Probleem:** B03 F3/F4 willen MediaGuard laten zoeken of herstellen; 1.2 §2.3 staat bij MediaGuard alleen "noodstop
  aan" toe. Besluit **BG-05 is open** (advies: ja, maar pas na P2/P3). Jelly Leon als tweede MediaGuard-client staat niet
  in het contract (BG-04 open).
- **Tekstvoorstel:**
  - §2.3 regel 3 aanvullen: "Gereserveerde MediaGuard-acties (Δ-CONTRACT-MG) — **niet toegestaan tot besluit BG-05 van
    de gebruiker én tot MediaGuard sleutelscopes heeft (P3-02)**: `mediaguard.wanted.search`,
    `mediaguard.quarantine.release_check`, `mediaguard.file.reacquire`, `mediaguard.quality.report` en
    `mediaguard.subtitles.search`, elk minimaal R2 met goedkeuring per actie, uitgevoerd door MediaGuard zelf via een
    gescopete route (eigenaar-connector, A28). `mediaguard.quarantine.restore` is R3 en wordt nooit door AI voorgesteld.
    Tot het besluit antwoorden Hub en Jelly Leon met `handmatig_in_mediaguard` en een deeplink — nooit gesimuleerd
    succes." (In B03 heten de acties zonder voorvoegsel; het voorvoegsel voorkomt botsingen in de allowlist, Δ-HUB-1.)
  - §2.3 regel 2 aanvullen: "Naast de Hub mag Jelly Leon een eigen MediaGuard-sleutel met rol **viewer** hebben
    (invoer in Jelly Leon zelf, BG-04): rol gecontroleerd met `GET /api/v1/auth/me` bij elke start en elk uur, een andere
    rol → sleutel niet opslaan en niet gebruiken; routewitte lijst (GET + het niet-muterende `POST /api/v1/audio/inspect`)
    en veldenwitte lijst; ruwe antwoorden nooit loggen of bewaren."
- **Geraakte repos:** ASM (policy en allowlist, pas na BG-05), MGU (scopes P3-02, gescopete routes), JL (viewerclient,
  verzoekroute).
- **Uitvoering:** tekst NU als *gereserveerd*; in werking pas na BG-05 (vóór golf 3).

<a id="a06"></a>
### A06 — Optionele model-apps: app `mt`, één producent per soort, GPU-rol

- **Bronnen:** Δ-CONTRACT-MT, Δ-CONTRACT-MODEL, ADR-0019 (ook Δ-ZK-2).
- **Probleem:** §1 noemt lokale modellen als optionele apps, maar niet welke app wat levert; spraakherkenning is dubbel
  gepland (B03-008 en B07-004) en embeddings ook (zoeken maakt ze al van de bron "jellyfin"); `mt` ontbreekt in de
  apptabel. Het B03-plan noemt de A310 en de UHD 770 als GPU's van de NAS; dat is nog niet door D08 gemeten.
- **Tekstvoorstel (§1 en §2):**
  - Rij in de apptabel: "optioneel (standaard uit) · `mt` (vertaalmotor, OPUS-MT via CTranslate2) · eigen gepinde image;
    het model wordt eenmalig buiten de NAS omgezet, met herkomst (revisie, converterversie, commando) en sha256 · poort:
    voorstel bij installatie · repo: open (BG-06/BG-18)".
  - "Eén producent per soort: één spraakherkenning voor B03-008, B07-004, F4 (taal) en F6 (transcripten); één
    embeddingproducent. Tot besluit BG-06 blijft de bestaande producent de enige (zoeken maakt embeddings; Jelly Leon
    niet) en komt er geen tweede."
  - "Model-apps draaien standaard zonder GPU. Een GPU alleen na een D08-meting van de render-node, en nooit op de GPU
    die D08/BG-27 toewijst aan MediaGuard-AV1 of live-transcodes. Geen torch, transformers of ctranslate2 in de
    jelly-leon-image."
  - "Adressen van model-apps: alleen loopback, RFC 1918 of ULA (niet `100.64.0.0/10`), IP-controle per verbinding, geen
    redirects; het geheim van de app staat in de geheimenmap van de afnemer. Zonder model-app: klassieke terugval en
    `503 engine_unavailable` of `capability_unavailable`, nooit gesimuleerd succes."
- **Geraakte repos:** ASM (contract, manifesten van optionele apps via ASF), JL, ZPA, ASF.
- **Uitvoering:** tekst NU; producent en repo van `mt` na BG-06/BG-18 (vóór P5).

<a id="a07"></a>
### A07 — 100.64.0.0/10 niet meer standaard privé

- **Bronnen:** Δ-CONTRACT-NET.
- **Probleem:** §4.1 rekent `100.64.0.0/10` (CGNAT, ook Tailscale) als privé voor de noodlogin. Met Tailscale-delen
  kunnen gasten in dat bereik zitten; Jelly Leon (F1/F2) en ADR-0019 rekenen het al als "niet privé".
- **Tekstvoorstel (§4.1, tweede streepje):** "alleen vanaf RFC 1918 en `fc00::/7` (echte bron-IP …). `100.64.0.0/10`
  telt standaard **niet** als privé. Een beheerder kan het in de Hub-UI toestaan (audit, waarschuwing 'alleen als je
  Tailscale niet met anderen deelt'); de cache van home-control-hub mag dit alleen verscherpen. Dezelfde standaard geldt
  voor elke andere 'privé'-controle in het platform."
- **Geraakte repos:** ASM (noodlogin, standaardwaarde en instelling), HCH (bereiken in het beleid/register), JL.
- **Uitvoering:** NU; of 100.64/10 aan moet, is een besluit van de gebruiker (§8).

<a id="a08"></a>
### A08 — Healthcheckproces en bounding set bij start als 568

- **Bronnen:** R2-001, R2-002, R2-034, R2-045, R2-047.
- **Probleem:** Docker start `HEALTHCHECK`- en `docker exec`-processen buiten de procesboom van PID 1 (PPid 0) als de
  gebruiker van de image: zonder Custom User als root, met de standaard-capabilities en zonder `no_new_privs`. §2.2 zegt
  "geen enkel proces meer als root". Bij "Custom User 568" kan een niet-root-proces de bounding set niet legen.
  Stand (gemeten in de code): de healthcheck wisselt zelf naar 568 met no-new-privileges in HCH, JLP en ZPA
  (`deploy/allinone/healthcheck.py`) en in JL (`setpriv`, ADR-0014); **niet** in ASM (`deploy/allinone/healthcheck.py`,
  `deploy/executor/healthcheck.py`) en ASF (`deploy/allinone/healthcheck.py`). MSO, MGU en MH zijn bestaande apps (A6/P3).
- **Tekstvoorstel (§2.2, na de rooktestzin; §10 verwijst ernaar):** "Docker start `HEALTHCHECK`- en `docker exec`-processen
  als de gebruiker van de image, buiten de procesboom van PID 1. Daarom: (1) het healthcheckcommando staat in exec-vorm
  (geen `sh -c`) en is een klein programma dat als **eerste** handeling `setgroups([])`, `setgid(568)`, `setuid(568)` en
  `prctl(PR_SET_NO_NEW_PRIVS, 1)` uitvoert (of al 568 is) en pas daarna iets controleert; mislukt de wissel → exit 1
  (rood). (2) De rooktest controleert alle processen met PPid ≠ 0 zoals hierboven en de healthcheck apart: hetzelfde
  commando met een controlevlag meldt na de wissel `Uid 568`, `CapEff 0`, `CapPrm 0` en `NoNewPrivs 1`. Het korte
  venster vóór de wissel is een gemeld restrisico. (3) Bounding set: start de container als root, dan laat de bewaker de
  bounding set vallen vóór de wissel (aanbevolen, zoals home-control-hub). Start hij als 'Custom User 568', dan kan dat
  niet; dan gelden `CapEff`, `CapPrm` en `CapAmb` 0 en `NoNewPrivs 1`, en mag `CapBnd` de Docker-standaardset zijn."
- **Geraakte repos:** ASM (Hub en executor), ASF (nu nog root); HCH, JLP, ZPA, JL (alleen de controlevlag/rooktest
  nalopen); MSO, MGU, MH bij hun alles-in-één-stap (P3).
- **Uitvoering:** NU voor ASM en ASF; P3 voor de bestaande apps.

<a id="a09"></a>
### A09 — Term `custom_app` en catalogusapp voor apps met één container

- **Bronnen:** R2-053, R2-079.
- **Probleem:** in TrueNAS `app.query` betekent `custom_app: true` een compose-app (*Install via YAML*); het standaard
  Custom App-formulier is de catalogusapp `ix-app` met `custom_app: false`. Het contract gebruikt "custom_app" voor het
  formulier. §1 ("meerdere containers via de catalogusapp; anders een standaard Custom App") is dubbelzinnig voor apps met
  één container waarvoor ook een catalogusapp bestaat (op de peildatum verdwenen authentik 1.3.63 en immich 1.14.62 al
  uit de trein).
- **Tekstvoorstel:**
  - §2 "Installatie via de API" en §9: "Begrippen: *standaard Custom App* = het formulier van TrueNAS, technisch de
    catalogusapp `ix-app` (`app.query`: `custom_app: false`). Het TrueNAS-veld `custom_app: true` betekent een compose-app
    (*Install via YAML*) en valt altijd buiten het beleid (de Hub toont `custom_compose`). `install.method: custom_app` in
    het manifest betekent uitsluitend het formulier (`ix-app`)."
  - §1: "Apps van derden met één container: standaard een Custom App met één gepinde image (digest), als 568:568 waar de
    image dat toestaat, ook als er een catalogusapp bestaat (geen afhankelijkheid van verdwijnende catalogusversies). Een
    catalogusapp voor apps met meerdere containers, of met een reden in het manifest (`install.reason`). Restrisico,
    vermeld in het manifest: zonder no-new-privileges in het formulier kan een setuid-programma in een upstream-image
    binnen de container root worden."
- **Geraakte repos:** ASM (Hub-herkenning is al zo, ADR-0021), ASF (validator: `install.reason`), JLP
  (`TRUENAS_APP_API.md`, manifesten).
- **Uitvoering:** NU.

<a id="a10"></a>
### A10 — Geheimen die een app niet zelf maakt: catalogus-values en OIDC-clientgeheim

- **Bronnen:** X-17, P-07 (ook R2-077 voor `secret_in_form`).
- **Probleem:** §3.1 "geen geheimen in het formulier" botst met catalogusapps die verplichte geheime waarden hebben
  (Authentik `db_password`/`secret_key`); jelly-leon-platform laat de Hub ze genereren en de executor (P2) ze vullen,
  zonder contractregel. Het OIDC-`client_secret` dat home-control-hub in P2 bij Authentik aanmaakt, moet in de vault van
  de Hub komen, terwijl §4.4 "geen geheimen via die routes" zegt.
- **Tekstvoorstel (§3.1, nieuw punt):**
  - "(a) Catalogusapps met verplichte geheime waarden in hun `values`: bij installatie via de API genereert de Hub ze
    (CSPRNG, ≥ 256 bit), bewaart ze versleuteld in zijn vault (`vault://app/<app_id>/<parameter>`) en geeft de executor
    ze alleen in de `values` van `app.create`/`app.update` mee (onderdeel van de R2-actie). Ze staan nooit in een
    manifest, preview-diff, auditdetail, log of evidence (alleen 'gegenereerd' met datum). Het manifest markeert zo'n
    parameter met `source: generated` en `secret: true`; de validator meldt dan geen `secret_in_form`. Bij een handmatige
    installatie vult de gebruiker ze zelf in TrueNAS in (een geheim van de gebruiker, zoals de registry-token van §2.1).
    De Hub leest de app-configuratie nooit terug (ADR-0021)."
  - "(b) Geheimen die een dienst voor de Hub aanmaakt (OIDC-`client_secret` van de Hub-client, B13-002): §4.4 blijft
    gelden — geen geheimen via Hub-connector, items of events. Tot een eigen ADR in P2 een eenmalige, versleutelde
    overdracht vastlegt, kopieert de beheerder het geheim zelf uit Authentik naar de Hub-UI (vault; alleen de laatste
    4 tekens zichtbaar)."
- **Geraakte repos:** ASM (vault, executor in P2), JLP (manifest Authentik), ASF (validator), HCH (apply van
  `sso.oidc.hub.register` in P2).
- **Uitvoering:** tekst NU; bouw P2.

<a id="a11"></a>
### A11 — Adresregels (IP-vorm), `base_url` en `HUB_*` buiten het manifest

- **Bronnen:** R2-038, R2-040, R2-121 (ook X-06).
- **Probleem:** §3.2 zegt niet in welke vorm een IP-adres mag staan: `127.1`, `2130706433`, `0x7f000001`, `010.0.0.1`,
  `0` en `localhost.` omzeilden de loopback-/link-local-/`0.0.0.0`-regels (home-control-hub ADR-0013 punt 4). Een
  ongeldige optionele `base_url` laat de Hub met 422 weigeren; de dienst behandelt 422 als definitief en het eenmalige
  token is verbrand. `HUB_*` zijn geen geldige manifestparameters (lowercase), maar dat staat nergens.
- **Tekstvoorstel:**
  - §3.2, adresregel aanvullen: "Een IPv4-adres alleen als `a.b.c.d` (vier decimale delen 0–255, zonder voorloopnul); een
    host van alleen cijfers, punten en hex-delen die daar niet aan voldoet, is ongeldig; IPv6 alleen tussen `[]`; één punt
    aan het eind van een naam telt niet mee (`localhost.` = `localhost`). Bij een hostnaam gelden de verboden bereiken
    ook voor het opgeloste adres, bij elke verbinding."
  - §3.3, rij `base_url`: "De dienst stuurt `base_url` alleen als die aan de regels voldoet, anders `null`. De Hub
    weigert een enroll-verzoek nooit om `base_url`: een ongeldige waarde bewaart hij als `null`, met een waarschuwing in de
    Hub-UI."
  - §9 en §3.2: "`HUB_URL`, `HUB_ENROLLMENT_TOKEN` en `HUB_KEY_FINGERPRINT` zijn geen manifestparameters en staan niet in
    `custom_app.env`; de vertaling voegt ze bij `app.install`/`app.update` toe als de Hub koppelt (§8). Een manifest met
    een parameter- of env-naam die met `HUB_` begint → fout `reserved_env`."
- **Geraakte repos:** HCH (al zo), ASF, JLP, ZPA, ASM-executor (IP-vorm nalopen), ASM-Hub (`base_url` tolerant,
  vertaling `HUB_*`), ASF (validator `reserved_env`).
- **Uitvoering:** NU.

<a id="a12"></a>
### A12 — `hub-link.json`: onleesbaar bestand, open codelijst, extra velden

- **Bronnen:** R2-036, R2-119 (ook R2-022, X-03, X-05).
- **Probleem:** §3.5 zegt niet wat een dienst met een onleesbaar `hub-link.json` doet. In home-control-hub zette een
  gewone schrijfactie zo'n bestand stil terug naar "nooit gekoppeld", waarna het koppelformulier terugkwam (open bij fout;
  ADR-0013 punt 1). De lijst `last_error`-codes is "o.a."; diensten voegden eigen codes en velden toe.
- **Tekstvoorstel (§3.5):**
  - "**Onleesbaar** (geen geldige JSON, andere major van `schema_version`, ontbrekende verplichte velden, verkeerde
    eigenaar of rechten): fail-closed. De dienst vertrouwt geen Hub-JWT (401 `not_linked`), toont geen koppelformulier
    (onbekend telt als 'al eens gekoppeld') en meldt in `/readyz` en de witte lijst `last_error.code =
    koppelstatus_onleesbaar`. Moet de dienst het bestand vervangen, dan bewaart hij het origineel als
    `hub-link.json.onleesbaar-<UTC-tijd>` (0600) en zet hij `unreadable_replaced_at`; zolang `first_linked_at` daarna leeg
    is, blijft de toestand 'onleesbaar'. Herstel alleen met een nieuw env-token via de Hub (§3.8)."
  - "De codelijst van `last_error` is open (snake_case, met een vaste NL-melding van de dienst). Vaste aanvullingen:
    `hub_incompatibel` (413/422 van de Hub), `token_ongeldig` (env-token past niet in het patroon),
    `vingerafdruk_ongeldig` (`HUB_KEY_FINGERPRINT` onleesbaar), `hub_adres_ongeldig` (`HUB_URL` breekt §3.2),
    `overzetten_onvolledig` (eenmalige overzetting uit de database onvolledig) en `koppelstatus_onleesbaar`. Bij
    `vingerafdruk_ongeldig` en `hub_adres_ongeldig` spreekt de dienst de Hub niet aan en markeert hij het token niet als
    afgehandeld. De Hub-UI toont de meegeleverde NL-melding en hardcodeert geen codes."
  - "Extra velden mogen; oudere lezers negeren ze: `unreadable_replaced_at`, `token_rotation_requested_at` (een
    aangevraagde rotatie overleeft een herstart) en `key_rotation_blocked_sequence` (een geweigerde sleutelrotatie blijft
    zichtbaar). Ze komen niet in de witte lijst. `last_error` krijgt geen trace-ID (zie E06 voor de weergave)."
- **Geraakte repos:** HCH (gebouwd), ASF, JLP, ZPA, ASM-executor (toepassen), ASM-Hub (UI toont de melding).
- **Uitvoering:** NU.

<a id="a13"></a>
### A13 — Herkomstcontrole koppelformulier: Referrer-Policy, Origin, Sec-Fetch-Site, browsertest

- **Bronnen:** R2-083, R2-095, R2-096, R2-145, R2-149 (ook X-41).
- **Probleem:** §3.7 eist een `Origin`-controle maar zegt niets over de `Referrer-Policy`. Met `no-referrer` stuurt elke
  browser bij de formulier-POST `Origin: null`; een strenge controle weigert dan elke echte poging (appstore-en-fork en de
  executor waren daardoor in een echte browser onbruikbaar), een soepele accepteert `null` en leunt alleen op de
  double-submit-cookie — terwijl een andere app op hetzelfde NAS-adres dezelfde *site* is (SameSite-cookies gaan mee).
  Stand (gemeten in de code): `same-origin` + `Origin: null` geweigerd in ASF (`api/status_page.py`), JLP
  (`statuspage.py`) en de executor (`app.py`); `no-referrer` + `Origin: null` geaccepteerd in HCH (`status_page.py`) en
  ZPA (`status_page.py`, met `Sec-Fetch-Site`). Alleen ZPA controleert `Sec-Fetch-Site`.
- **Tekstvoorstel (§3.7, de CSRF-zin vervangen; geldt ook voor §3.9):** "Herkomst van elke formulier-POST op een
  statuspagina, naast de double-submit-cookie (`SameSite=Strict`, HttpOnly) met formuliertoken:
  1. De pagina's sturen `Referrer-Policy: same-origin` (nooit `no-referrer`).
  2. `Origin` moet exact gelijk zijn aan `<schema>://<Host-header>` van het verzoek; ontbreekt `Origin` of is hij `null`
     → 403 met de vaste melding (fail-closed).
  3. Stuurt de browser `Sec-Fetch-Site`, dan alleen `same-origin` of `none`; `same-site` (een andere app op hetzelfde
     NAS-adres) en `cross-site` → 403.
  4. Een geweigerd verzoek gaat niet naar de Hub en verandert niets.
  5. Elke repo met een koppel- of sleutelformulier heeft een browsertest (Chromium) die het echte formulier tegen de
     echte dienst verstuurt, plus negatieve tests: `Origin: null`, vreemde `Origin`, `Sec-Fetch-Site: same-site` en
     `cross-site`, geen cookie."
- **Geraakte repos:** HCH en ZPA (omzetten naar `same-origin` en exacte `Origin`); ASF, JLP en ASM-executor
  (`Sec-Fetch-Site` toevoegen, browsertest nalopen).
- **Uitvoering:** NU.

<a id="a14"></a>
### A14 — Overige regels koppelformulier: pogingen, koppelen bezig, meldingen, log, DNS-rebinding

- **Bronnen:** R2-035, R2-125 (ook R2-073, X-12, X-13, X-14).
- **Probleem:** niet geregeld: of ongeldige invoer als poging telt; wat een POST doet terwijl er al een koppelpoging loopt;
  of een melding uit de URL mag komen (zoeken toonde "al eens gekoppeld" naast het formulier via `?melding=`); of invoer
  eerst afgekapt mag worden (een te lange koppelcode met een geldig begin ging naar de Hub); waar de trace-ID van een
  poging terechtkomt. DNS-rebinding vergroot het restrisico van §3.7.
- **Tekstvoorstel (§3.7, aanvullingen):**
  - "**Pogingen:** elke formulier-POST die de herkomstcontrole doorstaat, telt mee voor beide limieten (per bron-IP en
    per dienst), ook bij ongeldige invoer, een lopende poging of een onleesbaar koppelbestand."
  - "**Koppelen bezig** (`pending ≠ null`): de dienst stuurt niets naar de Hub en antwoordt met de vaste melding
    `koppelen_bezig` (HTTP 409). De enige voorwaarde voor het formulier blijft 'nog nooit gekoppeld'; de weergave van een
    lopende poging is een Peil-zaak (E02)."
  - "**Onleesbaar koppelbestand:** geen formulier; een POST uit een oud tabblad gaat niet naar de Hub en krijgt
    `koppelstatus_onleesbaar` (A12)."
  - "**Meldingen** horen bij een echte, recente poging van deze browser (sleutel in het geheugen, hooguit 15 min geldig),
    nooit bij alleen een query-parameter; een melding spreekt de koppelstatus nooit tegen."
  - "**Invoer** als geheel controleren, nooit eerst afkappen: koppelcode ≤ 32, vingerafdruk ≤ 64, Hub-adres ≤ 512 tekens;
    langer → veldfout."
  - "**Log:** elke afgehandelde poging geeft één regel in de app-log met code en Trace-ID, zonder het ingevulde Hub-adres
    van een mislukte poging."
  - "**Restrisico DNS-rebinding** (aanvulling): een website die iemand op het LAN bezoekt, kan via DNS-rebinding dezelfde
    oorsprong krijgen (Origin = Host) en een nooit gekoppelde dienst aan een eigen 'Hub' koppelen. Beperking (voorstel):
    `POST /koppelen` alleen als de `Host`-header een IP-adres in §3.2-vorm is, een naam zonder punt, of een naam onder
    `.local`, `.lan`, `.internal` of `.home.arpa`; anders 403 `host_niet_toegestaan` (rebinding gebruikt een publieke
    domeinnaam). Wie de statuspagina via een eigen domeinnaam opent, koppelt met env-enrollment (aanbevolen) of via de
    Hub-UI."
- **Geraakte repos:** HCH, ASF, JLP, ZPA, ASM-executor.
- **Uitvoering:** NU (de Host-beperking: de contractreview beslist, §9).

<a id="a15"></a>
### A15 — "Gereed" op de statuspagina tegenover `/readyz`

- **Bronnen:** R2-006, R2-075.
- **Probleem:** het contract definieert "gereed" voor de statuspagina niet. ONTWERPTAAL §13.2 noemt een niet-gekoppelde
  dienst "Niet gereed", terwijl `/readyz` dan 200 geeft (zodat TrueNAS hem niet herstart). HCH en ZPA kozen allebei:
  `/readyz` 200, pagina "Niet gereed" met uitleg.
- **Tekstvoorstel:**
  - §5: "`GET /readyz` = de dienst kan verkeer aannemen (database, schema, geheimen, eigen worker waar nodig). De
    koppeling met de Hub telt **niet** mee: een niet-gekoppelde, ontkoppelde of ingetrokken dienst is ready."
  - §3.7/§13: "Op de statuspagina betekent **Gereed**: `/readyz` in orde **én** `state: gekoppeld` met `confirmed_at`.
    Anders 'Niet gereed' met de reden (wacht op koppeling, ontkoppeld, ingetrokken, koppelstatus onleesbaar); de pagina
    legt het verschil met `/readyz` uit. Het totaal is nooit groen zonder Gereed (ONTWERPTAAL §13.2)."
- **Geraakte repos:** HCH, ASF, JLP, ZPA, ASM-executor (nalopen; HCH en ZPA zijn al zo).
- **Uitvoering:** NU.

<a id="a16"></a>
### A16 — JWT-controles: `aud`, reason-tabel, `jti` per POST, auth vóór bodyvalidatie

- **Bronnen:** R2-033, R2-037, R2-120 (ook X-04, X-06, X-10).
- **Probleem:** PyJWT accepteert standaard een lijst-`aud` waarin de eigen `app_id` staat; zo'n JWT werkt bij meerdere
  diensten, elk met een eigen replaycache. De reason-tabel van §4.7 dekt een ontbrekende header en een JWT zonder `kid`
  niet (HCH en ZPA kozen allebei `invalid_token`/`unknown_key`). Ook een "lees-achtige" POST zonder `Idempotency-Key`
  verbruikt de `jti`. In zoeken gaf een onleesbare body zonder auth 422 in plaats van 401 (opgelost in ZPA ADR-0012).
- **Tekstvoorstel:**
  - §4.2 en §4.3: "`aud` is precies één string, gelijk aan de eigen `app_id`; een lijst (ook met de eigen `app_id`
    erin) → 401 `invalid_token`."
  - §4.7, tabel aanvullen: "`invalid_token` ook bij: geen `Authorization`-header, een ander schema dan `Bearer`, een lege
    waarde, of een gepinde `kid` waarvan de handtekening niet klopt. `unknown_key` ook bij een JWS-header zonder `kid`."
  - §4.6: "'Mutatie' = **elke** POST/PUT/PATCH/DELETE, ook zonder `Idempotency-Key` en ook als de route niets wijzigt
    (bv. `…/evaluate`, `…/verify`); zonder `Idempotency-Key` bestaat geen exacte herhaling. De Hub haalt per zo'n verzoek
    een nieuwe JWT."
  - §4.7, volgorde: "eerst de 1 MiB-laag (§5), dan authenticatie, dan schemavalidatie van de body: zonder geldige
    authenticatie altijd 401, ook bij een onleesbare of ongeldige body."
- **Geraakte repos:** HCH (al zo), ZPA (deels), ASF, JLP, ASM-executor, JL (plugin, JL4); ASM-Hub als afnemer (per POST
  een nieuwe JWT).
- **Uitvoering:** NU.

<a id="a17"></a>
### A17 — Sleutelpinning en rotatie: meerdere policy-sleutels, `rotation_sequence`, oude tokens

- **Bronnen:** R2-032 (ook X-07, X-08, X-09, X-11).
- **Probleem:** de formule van de sleutelset-vingerafdruk gaat uit van één policy-sleutel. Bij een policy-rotatie zijn
  er tijdelijk twee, en de diensten verschillen: HCH en ASF nemen alle thumbprints gesorteerd met komma's, ZPA "de laatst
  gepinde telt" — dezelfde sleutelset geeft dan een andere vingerafdruk. Het enroll-antwoord mist de huidige
  `rotation_sequence`: een dienst die na een rotatie koppelt, begint op 0 en kan oude statements (ondertekend met
  ingetrokken sleutels) niet controleren. "Nooit de laatste sleutel intrekken" is dubbelzinnig. Bij een nieuwe
  enrollment van een bestaande registratie trekt de Hub alle oude tokens direct in, ook als de dienst het antwoord daarna
  weigert (verkeerde vingerafdruk) — dan vervalt de bestaande koppeling toch, tegen §3.8 in.
- **Tekstvoorstel:**
  - §4.5, formule: "`"jl-hub-keyset-v1\njwt:" + join(",", thumbprints van alle jwt-sleutels) + "\npolicy:" + join(",",
    thumbprints van alle policy-sleutels)`, beide lijsten gesorteerd op bytewaarde. Met één policy-sleutel is dat gelijk
    aan 1.2 (de testvectoren blijven). Nieuwe testvector: jwt `11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo` + policy
    `A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg` én `Kay64UG8yvCyLhqU000LxzYeUm0L_hLIl5S8kyKWbdc` →
    **`HN69-2PHK-XV2D-X85W`**." (Berekend met deze formule, die ook de twee bestaande vectoren geeft; dezelfde uitkomst als
    `home-control-hub` `integrations/security/hubkeys.py` `keyset_fingerprint`, uitgevoerd op 2026-11-10.)
  - §3.3, antwoord: "nieuw veld `rotation_sequence` (integer ≥ 0, huidige reeks van de Hub). De dienst zet
    `pins.rotation_sequence` daarop en vraagt alleen `key-rotations?after=<waarde>`. Ontbreekt het (Hub 1.2), dan 0.
    `schema_version` wordt `"1.3"` (major 1 blijft geldig)."
  - §4.5: "'Nooit de laatste sleutel van een doel intrekken' = na het toepassen heeft het doel minstens één sleutel;
    vervangen (`add` + `retire`) in één statement mag."
  - §3.6, Hub: "Bij een nieuwe geslaagde enrollment van een bestaande registratie trekt de Hub de oude tokens pas in bij
    het eerste gebruik van het nieuwe token (`GET /api/v1/services/self`). Wordt het nieuwe token niet binnen 60 min
    gebruikt, dan trekt de Hub het nieuwe in en blijven de oude geldig. Intrekken door de beheerder (§3.8) blijft
    direct."
- **Geraakte repos:** ASM (Hub: veld, intrekmoment; de sleutelrotatie zelf is nog niet gebouwd), ZPA (formule),
  HCH, ASF, JLP, ASM-executor (veld lezen, formule nalopen).
- **Uitvoering:** NU (formule en veld); de Hub-sleutelrotatie volgt later.

<a id="a18"></a>
### A18 — Dienst → Hub: alleen-lezen routes en scopes (inventaris, catalogusbeschikbaarheid)

- **Bronnen:** R2-063, P-06, P-09 (ook R2-124).
- **Probleem:** §4.4 noemt "Hub-connector-lezen" maar geen inventarisroute. `GET /api/v1/apps` en `/api/v1/apps/{id}`
  vragen een gebruikerssessie (`Viewer`; gemeten in `apps/api/src/hub/routers/catalog.py`), dus de import van ASF geeft
  op een echte installatie altijd `capability_unavailable`. Scopes per dienst waren in 1.2 een open punt (H13: nu leest
  elke ingeschreven dienst alle besluiten). De Authentik-upgradegate van HCH kan niet weten of een doelversie nog in de
  catalogus staat ("catalogusversie onbekend", `domains/sso/backup.py`).
- **Tekstvoorstel (§4.4):** "Dienst → Hub, met service-token, alleen lezen, met een vaste scope per dienst (in de Hub
  vastgelegd, niet door de dienst te kiezen); zonder scope 403 `scope_ontbreekt`, waarop de dienst eerlijk
  `capability_unavailable` meldt. Nooit geheimen via deze routes.

  | Scope | Routes | Diensten (v1) |
  |---|---|---|
  | `inventaris.lezen` | `GET /api/v1/apps`, `GET /api/v1/apps/{id}` | appstore-en-fork, jelly-leon-platform |
  | `catalogus.lezen` | nieuwe route voor catalogusbeschikbaarheid: `{train, app, version}` → `{beschikbaar: ja/nee/onbekend, gemeten_op}` (gemeten met de alleen-lezen TrueNAS-sleutel; zonder meting `onbekend`) | home-control-hub, jelly-leon-platform |
  | `besluiten.lezen` | `GET /connector/v1/items?type=decision` van de Hub (H13) | alleen diensten die het besluit nodig hebben (lijst per besluittype) |
  "
- **Geraakte repos:** ASM (scopes, route), ASF (import), HCH (upgradegate), JLP (plannen).
- **Uitvoering:** `inventaris.lezen` en `besluiten.lezen` NU; catalogusbeschikbaarheid P2.

<a id="a19"></a>
### A19 — Hub-uitbreidingen heartbeat en log-sink

- **Bronnen:** R2-050, R2-111, P-01, P-08.
- **Probleem:** de Hub heeft in P1 twee routes voor diensten gebouwd die niet in 1.2 staan (ADR-0021 §3, ADR-0022 §4).
- **Tekstvoorstel (nieuw §6.1 "Optionele Hub-uitbreidingen voor eigen diensten", service-token):**
  - "`POST /api/v1/monitoring/heartbeat`: `{status: healthy|degraded|down, observed_at, verwacht_interval_s (10–3600,
    standaard 60), checks: [≤ 20 × {name ^[a-z0-9_.-]{1,64}$, status (+unknown), detail ≤ 200}], worker: {laatste_hartslag,
    wachtrij, bezig, laatste_job_klaar, jobs_stil_na_s (60–86400)}}`; onbekende velden → 422; `observed_at` hooguit 5 min
    van de Hub-klok (anders 422). Antwoord 202 `accepted` of 200 `duplicate` (dedupe op `(dienst, observed_at)`); hooguit
    één per 5 s (429 + `Retry-After: 5`). Uitblijven: na 3 × `verwacht_interval_s` wordt de binnenkant `unknown`."
  - "`POST /api/v1/logs`: `{regels: [1–200 × {op, niveau: debug|info|warning|error|critical, bericht, logger ≤ 96,
    trace_id?, velden {}}]}`; opgeslagen bericht ≤ 2000 tekens, velden ≤ 4 KiB; per dienst ≤ 1000 regels per minuut
    (429 + `Retry-After: 60`); retentie 14 dagen en hooguit 50 000 regels; de Hub schoont vóór opslag; de sink voert nooit
    iets uit." (Gemeten: het invoerschema staat nu 8000 tekens toe en de opslag kort in tot 2000; 1.3 legt één grens vast.)
  - "Beide zijn optioneel: zonder heartbeat geldt de connector-health (§6), zonder log-sink alleen de eigen logs."
- **Geraakte repos:** ASM (bestaat); HCH, ASF, JLP, ZPA (mogen gebruiken).
- **Uitvoering:** tekst NU.

<a id="a20"></a>
### A20 — Uitzonderingen op `Idempotency-Key`

- **Bronnen:** R2-051, R2-117, R2-150 (ook R2-037, R2-111).
- **Probleem:** de code kent meer uitzonderingen dan §5 noemt; de statische test van de Hub
  (`apps/api/tests/unit/test_idempotency_routes.py`) somt ze op met als bron "contract_issue voor 1.3".
- **Tekstvoorstel (§5, uitzonderingenlijst aanvullen):** "Daarnaast uitgezonderd (eigen deduplicatie of geen
  bijwerking): `POST /api/v1/events/inbox` (dedupe op `event_id` en `(source_app, source_event_id)`, §7);
  `POST /api/v1/monitoring/heartbeat` (dedupe op `observed_at`); `POST /api/v1/logs` (dubbele levering aanvaard); het
  starten van een OIDC-(test)login en de OIDC-callback (inloggen); noodaccount instellen, roteren en bevestigen (geeft
  een geheim één keer terug of bevestigt een eenmalige TOTP); POST-routes zonder bijwerking behalve audit en tellers
  (`…/selftest`, `…/evaluate`, `…/verify`); `propose`/`apply`/`rollback` **alleen zolang** ze 501
  `capability_unavailable` geven. Elke repo heeft een statische test die faalt op een muterende route zonder
  `Idempotency-Key` die niet met reden in een uitzonderingslijst staat. Let op §4.6: ook zonder `Idempotency-Key`
  verbruikt een POST de `jti`."
- **Geraakte repos:** ASM (al zo); HCH, ASF, JLP, ZPA (statische test toevoegen of nalopen).
- **Uitvoering:** NU.

<a id="a21"></a>
### A21 — Foutcatalogus, 401-betekenis, paginering met snapshot, invoer niet afkappen

- **Bronnen:** R2-124, R2-137, ADR-0016 (ook X-13).
- **Probleem:** §5 legt de foutvorm vast, maar niet welke code bij welke situatie hoort; B03 trok de codes gelijk met
  de referentie van de Hub (ADR-0016). De Hub gebruikt 401 voor een niet-aangemelde sessie én voor een foute TOTP-code
  (`invalid_totp`, `routers/breakglass.py`), waardoor de UI op code moet onderscheiden. De Hub-catalogus pagineert met
  een offset over de laatste meting zonder te zeggen welke meting het is. Zoeken kortte invoer af vóór de controle.
- **Tekstvoorstel (§5):**
  - "**Foutcatalogus** (één code per situatie, alle nieuwe routes): 401 `unauthorized` (+`details.reason`, §4.7) ·
    403 `forbidden` (+`reason`) · 404 `not_found` (ook bij 'niet zichtbaar': geen orakel) · 400
    `idempotency_key_required` · 400 `idempotency_key_invalid` · 422 `idempotency_key_reused` · 409
    `idempotency_in_progress` · herhaling met dezelfde sleutel en body → het oorspronkelijke antwoord met header
    `Idempotent-Replay: true` · 422 `validation_error` (`details.fouten[]`) · 428 `precondition_required` · 412
    `precondition_failed` (`details.huidige_etag`) · 409 `conflict` of een eigen code met `reason` · 413
    `payload_too_large` · 429 `rate_limited` + `Retry-After` · 501 `capability_unavailable` · 503
    `<afhankelijkheid>_unavailable` (generiek `dependency_unavailable`) + `Retry-After`. Eigen situaties gebruiken
    `details.reason` of een eigen code onder 409; nooit een tweede code voor een gedeelde situatie."
  - "**401 alleen voor authenticatie:** geen of ongeldige aanmelding, sessie of token. Foute invoer binnen een geldige
    sessie (bv. een verkeerde TOTP-code bij `break-glass/confirm`) → 422 met een eigen code. Inloggen zelf blijft 401 bij
    foute gegevens."
  - "**Paginering:** een cursor hoort bij één momentopname. Elke pagina noemt `snapshot_id` (of de `observed_at` van de
    meting) en hetzelfde totaal; is die momentopname niet meer beschikbaar → 409 `snapshot_changed` (opnieuw beginnen)."
  - "**Invoer** als geheel controleren, nooit eerst afkappen; te lang → 422."
- **Geraakte repos:** ASM (`invalid_totp` → 422, snapshot in de catalogus), alle diensten (foutcatalogus nalopen; de
  `Idempotent-Replay`-header zit al in HCH, ASF, JLP, ZPA en de Hub), JL (plugin), ASF (client).
- **Uitvoering:** NU.

<a id="a22"></a>
### A22 — Connector-health: vaste checknamen en totaal = slechtste

- **Bronnen:** R2-052, R2-123.
- **Probleem:** §6 zegt niet hoe `status` uit de checks volgt en kent geen vaste checknamen. De Hub herkent "200 maar
  geen jobs" nu aan namen als `worker`, `jobs`, `queue` of `wachtrij` (ADR-0021).
- **Tekstvoorstel (§6, rij health):** "(1) `status` = het slechtste van alle checks in de volgorde `healthy` < `unknown`
  < `degraded` < `down` (zoals het Peil-totaal; 'onbekend nooit groen'); een check zonder verse meting telt als
  `unknown`. (2) Elke check heeft `name` (`^[a-z0-9_.-]{1,64}$`), `status`, `observed_at` en `detail`. (3) Vaste namen
  waar van toepassing: `database`, `worker` (`observed_at` = laatste hartslag), `jobs` (`detail.wachtrij`,
  `detail.bezig`, `detail.laatste_job_klaar`; een wachtrij die niet afneemt → `degraded`) en `hub_link`. Eigen namen mogen
  erbij. Na één overgangsrelease herkent de Hub 'werkt niet maar geeft 200' alleen nog aan `worker` en `jobs`."
- **Geraakte repos:** ASM (beoordeling), HCH, ASF, JLP, ZPA, JL (plugin).
- **Uitvoering:** NU.

<a id="a23"></a>
### A23 — Versheid: `observed_at` en `max_age` per capability

- **Bronnen:** R2-070, R2-087, R2-122, P-03.
- **Probleem:** het contract noemt geen leeftijdsgrens voor metingen. Iedereen koos 15 min (HCH `sources.PROBE_MAX_AGE`,
  ASF `hubinventory.MAX_AGE`, standaard `inventory_ttl_seconds` van de Hub), maar de Hub-TTL is instelbaar (30 s – 24 u,
  `config.py`) en dan zegt de appstore `unknown` terwijl de Hub `ok` zegt.
- **Tekstvoorstel (§1 en §6):** "Elke meting die een dienst doorgeeft (connector-health, items, statuspagina) heeft
  `observed_at`. Een meting ouder dan haar `max_age` is `unknown` met `reason_code: meting_verouderd` en de tijd van de
  laatste meting; de oude waarde wordt nooit als actueel doorgegeven. Standaard `max_age` = 900 s. Een bron mag per
  capability of itemtype een andere waarde opgeven in `GET /connector/v1/discover` → `limits.max_age_s: {"<naam>": s}`.
  Een afnemer mag strenger zijn (eerder `unknown`, nooit groen), nooit soepeler dan de bron."
- **Geraakte repos:** ASM (eigen discover, beoordeling), HCH, ASF, JLP, ZPA.
- **Uitvoering:** NU.

<a id="a24"></a>
### A24 — Events: envelopegrenzen, werkwoorden, domeinen per eigenaar, vaste `service.*`-namen

- **Bronnen:** R2-109, R2-118, P-02, X-01, X-40, B03-§10.10 (ook R2-110).
- **Probleem:** §7 noemt alleen "drie segmenten". De echte grenzen staan in de Hub-inbox
  (`apps/api/src/hub/events/envelope.py`, `routers/events.py`) en de diensten ontdekten ze pas toen events als
  dead-letter eindigden (HCH ADR-0009 punt 5). Probleem en herstel hebben geen vaste vorm. Een dienst kan
  `event_type`'s van een ander domein sturen. De eigen koppel-events heten per dienst anders (gemeten in de code):
  koppeling gelukt = `service.hub_link.linked` (HCH), `service.enrollment.completed` (ASF, JLP) of
  `service.hub_link.paired` (ZPA); geweigerde sleutelrotatie = `service.key_rotation.rejected` (HCH, ASF) of
  `service.hub_key.rotation_rejected` (ZPA).
- **Tekstvoorstel (§7):**
  - "**Grenzen** (zoals de Hub-inbox ze afdwingt): onbekende velden → 422; `event_type` ≤ 128 tekens en
    `^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$`; `source_app` = de `app_id` van het service-token (anders 403
    `source_mismatch`); `source_event_id` 1–200 tekens; `entity.type` `^[a-z0-9_.-]{1,64}$`; `entity.id` 1–200;
    `actor.id` 1–128; `payload` ≤ 16 KiB als JSON (groter: inkorten met `_ingekort: true` of `payload_ref` ≤ 512);
    `timestamp_utc` met tijdzone. Antwoord 202 `accepted` of 200 `duplicate`. Een bron valideert vóór verzending tegen
    dezelfde regels."
  - "**Werkwoorden** (derde segment): probleem = `failed`, `crashed`, `down`, `degraded`, `stalled`, `blocked`,
    `rejected`, `saturated`, `conflict`; herstel = `recovered`, `succeeded`, `resolved`, `restored`; de rest is
    informatie. `entity` is het stabiele onderwerp (de taak, de app, de bron — niet de run), zodat probleem en herstel
    dezelfde vingerafdruk (soort × bron × onderwerp) krijgen. `app.health.changed` draagt `payload.status ∈
    healthy|degraded|down|unknown`; `unknown` is nooit een herstel."
  - "**Domeinen per eigenaar:** Hub `auth`, `alert`, `audit`, `backup`, `inventory`, `monitoring`, `notification`,
    `onboarding`, `action`; home-control-hub `sso`, `energy`, `network`, `automation`, `flow`; appstore-en-fork `catalog`;
    jelly-leon-platform `lifecycle`; zoeken-en-persoonlijke-ai `search`, `voice`; jelly-leon `media` (B03 §10.10);
    gedeeld: `app` (alleen `app.health.changed` over de eigen app) en `service` (alleen de vaste lijst hieronder). Een
    event buiten het eigen domein verwerkt de Hub alleen als algemene informatie, nooit met de regels van de eigenaar."
    (Gemeten in de code op 2026-11-10: Hub `auth`, `alert`, `audit`, `backup`, `inventory`, `monitoring`,
    `notification`, `onboarding`; HCH `sso`, `energy`, `network`, `automation`; ASF `catalog`; ZPA `search`, `voice`.
    `action` en `flow` komen uit de voorbeelden van §7; `lifecycle` is een voorstel, JLP stuurt nu alleen `service.*`.)
  - "**Vaste `service.*`-events** van elke eigen dienst: `service.hub_link.linked` (payload `{via: token|koppelcode}`),
    `service.hub_link.unlinked`, `service.hub_link.revoked`, `service.token.rotated`, `service.key_rotation.applied`,
    `service.key_rotation.rejected`. De oude namen `service.enrollment.completed`, `service.hub_link.paired` en
    `service.hub_key.rotation_rejected` vervallen (één release beide sturen mag)."
- **Geraakte repos:** ASM (inbox, regels), HCH, ASF, JLP, ZPA (namen), JL (media-events).
- **Uitvoering:** NU.

<a id="a25"></a>
### A25 — Ernst: vijf Peil-woorden, optioneel in de payload, vaste afbeelding

- **Bronnen:** R2-110, R2-129, R2-138.
- **Probleem:** §7 kent geen ernst; de Hub leest `payload.ernst` of `payload.severity` als hint. De Hub-API kent drie
  niveaus (`kritiek`, `waarschuwing`, `info`), Peil vijf woorden (Kritiek, Hoog, Middel, Laag, Info); de UI koos OB-05.
- **Tekstvoorstel (§7 en §1):** "Ernst kent platformbreed de vijf Peil-woorden `kritiek`, `hoog`, `middel`, `laag`,
  `info`. Een event mag `payload.ernst` met één van deze waarden meegeven (optioneel; zonder ernst bepaalt de Hub-regel
  het; `severity` als sleutel vervalt). De Hub mag intern drie niveaus houden met deze vaste afbeelding: `kritiek` →
  kritiek; `hoog` en `middel` → waarschuwing; `laag` en `info` → info. De UI toont de bronwaarde als die er is, anders
  kritiek → Kritiek, waarschuwing → Middel, info → Info (OB-05). Alleen kritiek escaleert."
- **Geraakte repos:** ASM (inbox, UI); alle eventbronnen (HCH, ASF, JLP, ZPA, JL) mogen `ernst` meesturen.
- **Uitvoering:** NU.

<a id="a26"></a>
### A26 — `sso.access.revoked` met OIDC-`sub`

- **Bronnen:** R2-112.
- **Probleem:** HCH stuurt `sso.access.revoked` met `entity: {type: "authentik_user", id: <gebruikersnaam>}`
  (`domains/sso/authaudit.py`); de Hub koppelt daarom op `preferred_username` en trekt alleen sessies in. Een
  gebruikersnaam kan in Authentik wijzigen; de stabiele sleutel van de Hub is `(issuer, sub)` (ADR-0023 punt 6).
- **Tekstvoorstel (§7, vast schema):** "`sso.access.revoked` en `sso.access.changed` (bron alleen `home-control-hub`,
  via de inbox): `entity: {type: "authentik_user", id: <gebruikersnaam>}`, `payload` met verplicht `issuer`, `sub` (de
  OIDC-`sub` die de Hub-client krijgt; bij `sub_mode=hashed_user_id` de gehashte gebruikers-ID — te verifiëren tegen de
  broncode van Authentik) en `preferred_username`. De Hub koppelt op `(issuer, sub)`; alleen als `sub` ontbreekt
  (overgang) op `preferred_username`. Een event trekt alleen sessies in en geeft nooit rechten."
- **Geraakte repos:** HCH (payload), ASM (koppeling).
- **Uitvoering:** NU.

<a id="a27"></a>
### A27 — SSO in de Hub: groep→rol, sessieduur, https, terugkeerpad

- **Bronnen:** R2-113, R2-114, R2-115, R2-151 (ook R2-117, R2-112).
- **Probleem:** §4.1 noemt OIDC "optioneel zodra B13 actief is", maar niet wie de groep→rol-koppeling beheert, hoe lang
  een SSO-sessie duurt, hoe D17 "HTTPS" zich verhoudt tot een Hub zonder TLS-route, en welke terugkeerpaden na inloggen
  mogen (`/<tab>/ander.domein` gaf een open redirect; ADR-0026 punt 2).
- **Tekstvoorstel (§4.1, nieuw punt "SSO via OIDC"):**
  - "Groep → rol stelt een beheerder in de Hub in (eigen tabel, audit); `home-control-hub` toont zijn koppelingen alleen
    als advies. Geen gekoppelde groep → geen toegang (geen standaardrol); `kind` wint."
  - "SSO-sessieduur instelbaar 15–720 min (standaard 480), nooit langer dan de lokale sessieduur, met dezelfde
    inactiviteitsgrens."
  - "Issuer en discovery alleen `https://` (D17). `redirect_uri` mag `http://` zolang er geen TLS-route is (B10/B13): de
    code is beschermd door PKCE (S256) en het transactiecookie; de status toont dan de waarschuwing
    `redirect_uri_https: false`."
  - "Terugkeerpad na inloggen (Hub én elke dienst of bestaande app met een eigen login): alleen een pad dat voldoet aan
    `^/(?![/\\])[!-~]*$`, hooguit 256 tekens, zonder `://` en zonder backslash; anders `/`. Nooit een volledige URL."
- **Geraakte repos:** ASM (gebouwd), HCH (advies), MGU, MSO, MH (eigen login: terugkeerpad nalopen in P3).
- **Uitvoering:** tekst NU; bestaande apps P3.

<a id="a28"></a>
### A28 — Eigenaar-connector-acties (sso.*) en back-upbevestiging per app

- **Bronnen:** P-04, P-05.
- **Probleem:** §8 noemt "de executor-app of de eigenaar-connector voert uit", maar alleen de executor heeft een
  allowlist. HCH bouwde `sso.oidc.hub.register` en `sso.sessions.revoke` als R2-voorstel (propose; apply in P2). De
  Authentik-upgradegate van HCH eist een back-upcheckpoint "door de Hub bevestigd"; de dienst telt het nu als bevestigd
  als het met een dienst-JWT binnenkomt (`authentik_router.py`), maar het contract zegt niet hoe de Hub een checkpoint
  bevestigt.
- **Tekstvoorstel (§8, nieuwe tabel "Acties via de eigenaar-connector", naast de executor-allowlist):**

  | `action_id` | eigenaar | klasse (min.) | `requires_backup` | AI mag voorstellen |
  |---|---|---|---|---|
  | `sso.oidc.hub.register` | home-control-hub | R2 | ja (Authentik-database) | nee (wijzigt toegang) |
  | `sso.sessions.revoke` | home-control-hub | R2 | nee | nee |
  | `mediaguard.*` (gereserveerd, A05) | media-guard-ultimate | R2 (`quarantine.restore` R3) | per actie | `quarantine.restore` nooit |
  | my_house `propose`/`apply`, MSO change sets | eigen lijst in hun DELTA_MATRIX (P3) | ≥ R1 | per actie | volgens beleid |

  "De eigenaar voert alleen uit met een door de Hub ondertekend `ExecutionRequest` (gepinde policy-sleutel,
  `preview_hash`, `resource_etag`, nonce, vervaltijd) en controleert zelf opnieuw, net als de executor. **Back-up:**
  `requires_backup: true` ⇒ de Hub bindt in de `Approval` een `backup_checkpoint_id` van een B12-back-up van die app met
  status `geverifieerd` (niet ouder dan het RPO uit het manifest). Een checkpoint dat een gebruiker opgeeft, is nooit
  bewijs. Een dienst die vóór de goedkeuring een back-upgate toont (bv. B13-005), vertrouwt een checkpoint alleen als het
  met een dienst-JWT van de Hub binnenkomt; anders blijft de gate `onbekend`."
- **Geraakte repos:** ASM (policy, P2), HCH (apply, P2), MH, MSO, MGU (P3).
- **Uitvoering:** tekst NU; bouw P2/P3.

<a id="a29"></a>
### A29 — TrueNAS alleen-lezen: `core.subscribe` voor `reporting.realtime`

- **Bronnen:** R2-055.
- **Probleem:** §8 noemt alleen methoden; `reporting.realtime` is in TrueNAS 25.10 een event source (rol
  `REPORTING_READ`), geen methode.
- **Tekstvoorstel (§8, laatste alinea):** "De alleen-lezen-sleutel van de Hub gebruikt leesmethoden plus
  `core.subscribe`/`core.unsubscribe` voor een vaste lijst event sources (nu alleen `reporting.realtime`): abonneren, één
  bericht lezen, opzeggen (ook na een time-out). Een andere event source vraagt een contractwijziging. Bronwaarneming
  (broncode TS-25.10.8); NIET GEVALIDEERD (echte NAS)."
- **Geraakte repos:** ASM (al zo gebouwd, ADR-0021 §5).
- **Uitvoering:** tekst NU.

<a id="a30"></a>
### A30 — Manifeststandaard: geaccepteerde bevindingen, checklist, controles na installatie, poorten

- **Bronnen:** R2-077, R2-078, R2-081, R2-082, R2-128.
- **Probleem:** `--strict` kan nooit schoon zijn voor SQLite-apps zonder export (`backup_db_export_none`), catalogusapps
  met verplichte privé-waarden (`secret_in_form`) en eigen images vóór de release (`digest_pending_release`); JLP hield
  daarom een eigen uitzonderingenlijst bij. Er is geen documentsoort voor I-documenten zonder installatie (I01/I02).
  Upstream-apps hebben een open eerste-gebruik-venster (Gotify `admin/admin`, Beszel first-run, setup van Uptime Kuma en
  Authentik) en runtime-kenmerken die pas bij starten blijken (Beszel-agent: niet-schrijfbare `/tmp` als 568). Bij de
  Authentik-catalogusapp luistert de container op het gekozen hostpoortnummer zelf.
- **Tekstvoorstel (§9, eigenaar validator: appstore-en-fork):**
  - "`accepted_findings: [{code, reden_nl}]` — alleen voor waarschuwingen uit een vaste lijst: `backup_db_export_none`,
    `secret_in_form` (alleen bij een parameter met `source: generated`, A10) en `digest_pending_release` (alleen vóór de
    eerste release). `--strict` faalt op elke andere waarschuwing én op een geaccepteerde code die niet (meer) optreedt.
    Fouten zijn nooit te accepteren."
  - "`backup.db_export` krijgt de waarde `stopped_snapshot` (app stoppen + ZFS-snapshot van de dataset) voor apps zonder
    exportfunctie; de stilstand telt mee in `rto`."
  - "Nieuwe documentsoort `kind: checklist` (`install.method: none`) voor I-documenten zonder installatie, met eigen JSON
    Schema; de validator van manifest v1 weigert hem als installatie."
  - "`post_install_checks: [{id, soort: http|handmatig, beschrijving_nl}]` voor open eerste-gebruik-vensters en
    runtime-kenmerken; de Hub toont ze na installatie als taak voor de beheerder, en tot de bevestiging is de app niet
    'gezond' (gate)."
  - "`network.ports[].container_port` mag `same_as_host` zijn voor catalogusapps waarvan de container op de gekozen
    hostpoort luistert."
- **Geraakte repos:** ASF (validator, schema), JLP (manifesten, checklists), alle repos met een manifest.
- **Uitvoering:** NU.

<a id="a31"></a>
### A31 — Adoptie van bestaande apps: `kind: adoption`, eigenaar, statuswoorden

- **Bronnen:** R2-065, R2-066, R2-067.
- **Probleem:** een manifest v1 voor een bestaande app vraagt velden die niet te meten zijn (healthcheck, RPO/RTO,
  risico, parameters). "Eigenaar" is in het pakket niet gedefinieerd. De statuswoorden verschillen tussen taak, Excel en
  P0-preview.
- **Tekstvoorstel (§9, nieuw blok "Adoptie"):** "Documentsoort `kind: adoption` voor een bestaande, niet door het
  platform geïnstalleerde app: `installable: false`, eigen schema, alleen gemeten of door een beheerder bevestigde velden
  (niets gokken); de validator van manifest v1 weigert hem (`adoption_manifest_not_installable`). `owner: {soort:
  derde|bestaand|eigen_los|eigen, repo (alleen bij eigen repos), bevestigd_door, bevestigd_op}` — 'eigenaar' is wie de
  app beheert, los van de data-eigenaar uit 02_DATA_EIGENAARSCHAP. Status: `onbekend` (in de acceptatie 'unmanaged') ·
  `kandidaat` (herkend, wacht op bevestiging) · `adopted` (`status_nl` 'Geïmporteerd'). Herkenning alleen op de exacte
  catalogusappnaam of de exacte image-repository, nooit op de appnaam; altijd een voorstel dat een beheerder bevestigt.
  Emby (A03) is zo'n item met `owner.soort: derde`."
- **Geraakte repos:** ASF (gebouwd, ADR-0010), ASM (UI 'Geïmporteerd').
- **Uitvoering:** NU (vastleggen).

<a id="a32"></a>
### A32 — Monitorplan per app (endpoint, verwachte status, time-out)

- **Bronnen:** R2-127 (ook R2-128).
- **Probleem:** acceptatie I08-08-03 ("elk endpoint krijgt juiste expected status + timeout") heeft geen eigenaar; de
  Hub gebruikt de Socket.IO-beheer-API van Uptime Kuma niet.
- **Tekstvoorstel (§9 en B09):** "`healthcheck` in het manifest krijgt `monitor: {pad, verwachte_status, timeout_s,
  interval_s}`. De Hub (B09) maakt per app uit het dienstenregister (D03 + hostpoort) en het manifest een monitorplan; hij
  past Uptime Kuma niet zelf aan. De beheerder neemt het plan over in de Uptime Kuma-UI en bevestigt per monitor; dat
  heet 'handmatig bevestigd', nooit 'gevalideerd door de Hub'. Zonder bevestiging blijft I08-08-03 NIET GEVALIDEERD."
- **Geraakte repos:** ASM (B09), ASF (schema), JLP (manifesten).
- **Uitvoering:** tekst NU; bouw P2.

<a id="a33"></a>
### A33 — EVIDENCE (§11): nieuwe validatiewaarden, ID's buiten de Excel, consistentieregels

- **Bronnen:** R2-005, R2-042, R2-062, R2-084, R2-086, R2-136, R2-146, U-07, Δ-ASM-EXCEL, X-15, X-42.
- **Probleem:** §11 staat alleen Excel-ID's toe, dus een statuspagina, een ontwerpreview of een contractpunt (H5, H6,
  H12) kan geen eigen regel krijgen. Er is geen waarde voor een taak die "Niet gestart" is; een lege `validatie` is geen
  lijstwaarde (de test van de Hub, `apps/api/tests/unit/test_evidence_contract.py`, weigert hem). Niets eist dat een
  `NIET GEVALIDEERD (…)` in `blokkade` ook in `validatie` staat. "Intel-iGPU-getest (ontwikkelmachine)" staat in B03-rijen
  alleen in de opmerking, omdat de waarde ontbreekt. Het Excel-gereedschap zelf is al bijgewerkt (Δ-ASM-EXCEL).
- **Tekstvoorstel (§11):**
  1. "Validatiewaarden erbij: `Intel-iGPU-getest (ontwikkelmachine)` (functioneel bewijs en bovengrens op de iGPU van de
     ontwikkelmachine; zegt niets over de GPU's van de NAS, die blijven `NIET GEVALIDEERD (hardware)`) en `Niet getest`
     (alleen bij status `Niet gestart`)."
  2. "Per blad: Testmatrix (`EX..`, `JLT-..`) `Sim-geslaagd`/`Sim-mislukt`; werkpakketten en installatiestappen
     `Sim-getest`/`Unit-getest`/`Intel-iGPU-getest (ontwikkelmachine)`; overal aangevuld met `NIET GEVALIDEERD (…)` waar
     nodig. Een lege `validatie` is nooit toegestaan."
  3. "Elke `NIET GEVALIDEERD (…)` die in `blokkade` staat, staat ook in `validatie`."
  4. "Naast Excel-ID's mogen contractpunten (`C1.2-H5`, `C1.3-…`, met de code uit de conformiteitslijst) en reviews
     (`REVIEW-<repo>-<onderwerp>`) een eigen regel hebben. `update_excel.py` zet die niet in de vier bestaande bladen,
     maar meldt ze in een eigen overzicht (nooit stil weglaten)."
- **Geraakte repos:** alle 11 (EVIDENCE en hun EVIDENCE-test); ASM (`update_excel.py`, `test_evidence_contract.py`).
- **Uitvoering:** NU.

<a id="a34"></a>
### A34 — Ontwerpreview: breedtes 320–1440 en WCAG 2.2 AA

- **Bronnen:** R2-093, R2-144 (ook R2-147).
- **Probleem:** §13 vraagt een ontwerpreview op 360/390/768/1440 volgens WCAG 2.1 AA; ONTWERPTAAL §12 en de
  opdrachten vragen reflow op 320 px en axe met WCAG 2.2 AA. De reviews kozen al de strengste set.
- **Tekstvoorstel (§13 werkwijze, §10 `apps/web`):** "Ontwerpreview op 320, 360, 390, 768, 1024 en 1440 px, licht en
  donker, WCAG 2.2 AA (axe `wcag22aa`), focus nooit bedekt (2.4.11), tekstafstand van 1.4.12 zonder overloop; reflow met
  het systeemlettertype van de CI-runner (E12). De Playwright-matrix van de Hub blijft minimaal 360/390/768/1440; 320 en
  1024 zitten in de review. Gelijk aan ONTWERPTAAL §12."
- **Geraakte repos:** ASM, HCH, ASF, JLP, ZPA, MGU, MSO, MH.
- **Uitvoering:** NU (tekst; de reviews doen dit al).

<a id="a35"></a>
### A35 — Contractkopie: byte-gelijk en zonder kapotte relatieve links

- **Bronnen:** R2-017, R2-018, R2-044.
- **Probleem:** de kopieën zijn byte-gelijk (goed), maar het contract linkt relatief naar `../adr/ADR-0011…` en
  `../adr/ADR-0012…` van ai-server-manager; in andere repos zijn die links kapot. "Niet per repo aanpassen" botste met
  een kopie die de orkestratie liet maken.
- **Tekstvoorstel (kop van het contract):** "Elke repo heeft een **byte-gelijke** kopie in `docs/platform-v2/` met een
  drifttest (sha256 tegen de bron); een repo past de kopie nooit aan, ook niet om links te repareren. Verwijzingen naar
  bestanden in ai-server-manager staan als tekst `ai-server-manager:<pad>` of als absolute GitHub-URL, nooit als relatieve
  link. Hetzelfde geldt voor `CONTRACT_1.3_CONFORMITEIT.md`."
- **Geraakte repos:** alle 11 (kopie + drifttest).
- **Uitvoering:** NU.

<a id="a36"></a>
### A36 — Hub-adres voor "Terug naar de Hub" in bestaande apps

- **Bronnen:** X-19.
- **Probleem:** de link "Terug naar de Hub" (O-11) haalt het adres in elke bestaande app ergens anders vandaan:
  MediaGuard uit de instelling `system.hub_url`, MSO uit `systeem.hub_url`, my_house uit een nieuwe optionele
  omgevingsvariabele `HUB_URL` in het Custom App-formulier (my_house ADR-0008 meldde dat als contractpunt). In nieuwe
  diensten start `HUB_URL` een enrollment.
- **Tekstvoorstel (§2.3 regel 5):** "De link 'Terug naar de Hub' in een bestaande app haalt het Hub-adres uit een
  niet-geheime instelling van die app: het eigen instellingenregister (MediaGuard `system.hub_url`, MSO
  `systeem.hub_url`) of, als de app geen register heeft, de optionele omgevingsvariabele `HUB_URL` (my_house).
  Validatie volgens §3.2; ongeldig of leeg ⇒ geen link. Nooit afleiden uit `Referer`, de URL of andere invoer. In een
  bestaande app start `HUB_URL` **geen** enrollment (regel 2)."
- **Geraakte repos:** MGU, MSO, MH (al zo gebouwd; alleen vastleggen).
- **Uitvoering:** tekst NU.

## 4. Groepen (b): al opgelost in code of contract

<a id="b01"></a>
### B01 — Formuliernamen `hub_adres`/`koppelcode`/`hub_vingerafdruk`

- **Meldingen:** R2-011, R2-015, R2-143.
- **Bewijs:** de nieuwe namen staan in de code van alle vijf statuspagina's: HCH `integrations/status_page.py`, ASF
  `appstore/api/status_page.py`, JLP `lifecycle/statuspage.py`, ZPA `search_ai/status_page.py`, ASM-executor
  `executor/statuspagina.py` (de executor accepteert ook de oude namen, ADR-0024 punt 10). Eventueel noemt §3.7 de
  veldnamen informatief.

<a id="b02"></a>
### B02 — otpauth-issuer "TrueNAS Home Platform"

- **Meldingen:** R2-133.
- **Bewijs:** `apps/api/src/hub/breakglass.py:30` `ISSUER = "TrueNAS Home Platform"` (ADR-0024 punt 11).

<a id="b03"></a>
### B03 — §10-kwaliteitseisen gelden niet voor webclient en apparaat-apps

- **Meldingen:** R2-019, R2-031, R2-043.
- **Bewijs:** §10 heet "Repo-indeling **nieuwe Python-diensten**"; de §2-tabel zet de webclient in de app `jelly-leon`
  ("server incl. web-client"); jelly-leon-web ADR-0008/ADR-0010 en jelly-leon-clients ADR-0008 leggen "geen eigen
  image/Custom App" vast. De spanning zit in de algemene KWALITEIT-tekst van de bouwopdrachten, niet in het contract
  (followup voor de workflowscripts).

<a id="b04"></a>
### B04 — Koppelstatus na ontkoppelen alleen via de 401-reason

- **Meldingen:** R2-039.
- **Bewijs:** zo bedoeld in 1.2: §4.7 geeft `not_linked`/`revoked` als vaste `reason`, en §3.8 (R5) laat een herhaalde
  `unlink` met 401 `not_linked` als geslaagd tellen. Geen wijziging nodig.

<a id="b05"></a>
### B05 — Scan vóór publiek maken (programmabreed uitgevoerd)

- **Meldingen:** R2-020.
- **Bewijs:** `OVERDRACHT/STATUS.md`, "Vervolgbesluiten van de gebruiker": "Openbaarheid (na de scan van alle historie):
  10 repos publiek". De scan in jelly-leon-web was een extra controle achteraf, geen vervanging. (A01 legt de uitvoering
  in §1.1 vast.)

<a id="b06"></a>
### B06 — Eén specifieke render-node: al open punt in §9

- **Meldingen:** R2-004.
- **Bewijs:** contract 1.2 §9 (GPU-alinea): "Eén specifieke render-node via `privileges.devices` is een open punt
  (B03/P4, toegang voor 568 tot de render-groep onbekend)". Blijft open tot D08 (B03 §10.8).

<a id="b07"></a>
### B07 — 44 px voor losse links: recept `.losse-link` (C-63)

- **Meldingen:** R2-148.
- **Bewijs:** `design/ontwerptaal/COMPONENTEN.md` regel C-63 (`.losse-link`) en ADR-0025 punt 3; de reviewmeting van de
  Hub controleert losse links.

<a id="b08"></a>
### B08 — Adviezen van home-control-hub en adapterroutes van my_house: al conform

- **Bronnen:** X-02, X-34.
- **Bewijs:** de Hub toont `least_privilege: deels_gecontroleerd` als waarschuwing, `te_ruim` als fout en al het andere
  als onbekend, en `rights.status: verouderd` nooit groen (ADR-0023 punt 10). my_house bouwt een lees-connector/outbox
  alleen als de delta-matrix of de eigenaar van de Hub-adapter erom vraagt; dat is precies §2.3 regel 1 en de laatste
  alinea van §6.

## 5. Groepen (c): repo-bug of repo-keuze (geen contractzaak)

<a id="c01"></a>
### C01 — Hub-API-gemak: sorteren, filteren, poolstatus, open koppelcodes (ASM)

- **Meldingen:** R2-132, R2-134, R2-135, R2-140, R2-141, R2-142.
- **Repo:** ai-server-manager. Voorstellen voor de Hub-API (geen contract: Hub-intern, alleen de eigen UI gebruikt ze):
  `sorteer=status` op `GET /api/v1/apps` (nu `order_by(naam)`), een filter `onderwerp_id`/`app_id` op
  `GET /api/v1/incidents` (nu alleen `q`), een poolstatusveld (`ONLINE|DEGRADED|FAULTED|…`) naast `pool.gezond` voor
  Peil T-14a, en een lijst van openstaande koppelcodes en enrollment-tokens zonder geheim (aanmaakdatum, `app_id`,
  verloopt, gebruikt ja/nee).

<a id="c02"></a>
### C02 — Hub-catalogus: readback aan de verkeerde image, fake-imagenaam MediaGuard (ASM)

- **Meldingen:** R2-068, R2-069.
- **Repo:** ai-server-manager. Bug: `catalog/discovery.py` (regel ± 170) hangt `digest_bron` en `readback` aan
  `images[0]`, terwijl ze voor de hoofdimage berekend zijn. Testdata: de fake TrueNAS en `tests/unit/test_catalogus.py`
  gebruiken `ghcr.io/lvos04/mediaguard` naast de echte naam `ghcr.io/lvos04/mediaguard-core` (§2.3); gelijktrekken.

<a id="c03"></a>
### C03 — Hub-keuzes die al binnen het contract passen (ASM)

- **Meldingen:** R2-054, R2-056, R2-116, R2-131.
- **Repo:** ai-server-manager. Resourcegrenzen `unknown` tot P2 ze uit het manifest haalt (de app-configuratie lezen kan
  geheimen geven); het Beszel-wachtwoord van een alleen-lezen-gebruiker in de vault (§3.10; restrisico in ADR-0021); de
  getypeerde runbookcatalogus in het Hub-pakket tot de policy-engine er is (P2); geen RisicoBadge op een `risk_claim`
  (§8: de policy bepaalt de klasse). Geen wijziging; bij P2 opnieuw bekijken.

<a id="c04"></a>
### C04 — Testgat: ontkoppelen via de Hub-route niet end-to-end (ASM)

- **Meldingen:** R2-041.
- **Repo:** ai-server-manager (P2): een interop-test met een gemeten dienstadres in de testinventaris, zodat
  `POST /api/v1/services/{id}/unlink` echt de dienst aanroept.

<a id="c05"></a>
### C05 — ADR-nummering tussen gelijktijdige bouwers (ASM)

- **Meldingen:** R2-057.
- **Repo:** ai-server-manager (werkwijze, geen contract): het ADR-nummer pas kiezen na `git pull --rebase`, en bij een
  botsing hernummeren vóór de push.

<a id="c06"></a>
### C06 — Appstore-keuzes bij herkenning en inventaris (ASF)

- **Meldingen:** R2-064, R2-071; X-16.
- **Repo:** appstore-en-fork. De inventaris heeft geen labels of namespace; herkenning alleen op exacte
  catalogusapp-naam of image-repository (de acceptatietekst van B08-002 noemt labels; voorstel: Excel-tekst bijwerken).
  Snapotter/Teeltboek/Uren alleen handmatig koppelen (conform A06 "geen afleiding uit appnaam"). Bug: een 429 van de Hub
  bij het lezen van de inventaris volgt de eigen backoff in plaats van `Retry-After`.

<a id="c07"></a>
### C07 — Bouwplan B03 en jelly-leon-web: namen van haken en registers (ASM-bouwplan, JLW)

- **Bronnen:** X-18.
- **Repo:** ai-server-manager (bouwplan B03): overal "H-ITEMDETAILS" in plaats van "opvolger van JLW-0001" (B03-048,
  B03-057), en `UG-WEB-<n>` naast `UG-<functie>-<n>` in §10.11 opnemen. jelly-leon-web: Node-image op digest in
  `baseline.json` (geen eigen image, ADR-0008) is een repo-keuze.

<a id="c08"></a>
### C08 — I01 stap 3 schrijft shellopdrachten voor (ASM-pakket, JLP)

- **Meldingen:** R2-080.
- **Repo:** ai-server-manager (bron van het pakket, `03_INSTALLATIE/I01…`): stap 3 vervangen door `app.gpu_choices` via
  de alleen-lezen TrueNAS-API plus een bewijsrecord D08, zoals jelly-leon-platform al doet (geen terminal, §1).

<a id="c09"></a>
### C09 — MediaGuard en my_house: functionele vervolgpunten uit de Peil-review (MGU, MH)

- **Bronnen:** X-20, X-24, X-33.
- **Repo:** media-guard-ultimate — Android-app ook en-US (besluit van de gebruiker), servertekst ook in en-US, één
  kleurregel voor "Wat kwam erbij / Waar ging de ruimte heen" op web en Android, Overzicht periodiek verversen,
  SysteemStatusPaneel met rijen per onderdeel. my_house — tabelweergave bij "Laatste 24 uur" (akkoord van de gebruiker
  nodig). Allemaal functioneel; buiten de uiterlijk-ronde.

<a id="c10"></a>
### C10 — MSO: functionele vervolgpunten uit de Peil-review (MSO)

- **Bronnen:** X-25.
- **Repo:** media-source-optimizer — SysteemStatusPaneel bovenaan het Overzicht, bron en tijd per KPI-tegel, Peil-woorden
  (Beperkt/Storing) in de core, fase 2d (inline styles en `mg.css` weg), mock voor de doel-trendlijn, toetsenbordtests
  voor tabs en tabelregio's, echte toestellen.

<a id="c11"></a>
### C11 — Hub-UI: vervolgpunten uit de Peil-review (ASM)

- **Bronnen:** X-35.
- **Repo:** ai-server-manager — Zoeken (C-51) en Live-indicator in de kopbalk (P2/P5, geen schijnknop), iconen op de
  tabs van appdetail, laatste inline styles weg, compacte rijen per onderdeel op mobiel, databasepool meten (N-07,
  vermoeden, niet bewezen).

<a id="c12"></a>
### C12 — B03-deltaverzoeken die repowerk zijn (geen contracttekst)

- **Bronnen:** Δ-MG-1…8 en Δ-MG-DV (MGU), Δ-HUB-2, Δ-HUB-3, Δ-HUB-JL (ASM), Δ-ZK-1, Δ-ZK-2 (ZPA).
- **Repo:** per ID de eigenaar uit B03 hoofdstuk 18. Ze bouwen op contracttekst uit A03 (Emby-archief), A04 (Hub-adapter
  Jelly Leon), A05 (MediaGuard-acties) en A06 (één embeddingproducent), maar zijn zelf werk in de repo.

## 6. Groepen (d): afwijzen

<a id="d01"></a>
### D01 — Witte lijst van §3.5 als verplichting lezen

- **Meldingen:** R2-026, R2-076.
- **Reden:** de witte lijst is een **maximum** ("toont alleen"), geen lijst van verplichte velden. Minder tonen op de
  statuspagina (geen `service_id`, `via`, `service_token_last4`) is toegestaan; `GET /connector/v1/hub-link` geeft ze
  wel. Geen wijziging; geen plek in het sjabloon nodig.

<a id="d02"></a>
### D02 — Forced colors: rand ook op de Gezond-pil

- **Bronnen:** X-39.
- **Reden:** de reviewer meldt het zelf als aanvaardbaar (vorm en woord blijven, Onbekend houdt zijn stippel); geen
  actie.

## 7. Groepen (e): Peil-ontwerpzaken (voor Peil 1.1.1)

Deze groepen zijn voor de ontwerp-agent. Ze wijzigen het sjabloon of de ontwerptaal, niet het contract. Elke
statuspagina en elke kopie krijgt de wijziging pas via een nieuwe Peil-versie (O-14), niet door lokaal te omzeilen.

<a id="e01"></a>
### E01 — Sjabloon: blok voor een onleesbare koppelstatus

- **Meldingen:** R2-007, R2-012, R2-021, R2-058, R2-072, R2-092, R2-100.
- **Voorstel:** blok `<!--ALS:koppelstatus_onleesbaar-->` met pil Storing (of Onbekend) en een vaste tekst: "De
  koppelstatus is onleesbaar; deze dienst vertrouwt niets van de Hub. Opnieuw koppelen gaat via de Hub (nieuw
  koppeltoken)." Geen formulier. Hoort bij A12.

<a id="e02"></a>
### E02 — Sjabloon: aparte weergave "Koppelen bezig"

- **Meldingen:** R2-073 (ook R2-092).
- **Voorstel:** een vlag `koppelen_bezig` die het formulier verbergt en een neutrale pil "Koppelen bezig" (`hourglass`)
  toont, los van "Niet gekoppeld". Tot dan geldt de regel uit A14 (409 `koppelen_bezig`).

<a id="e03"></a>
### E03 — Sjabloon: tonen en iconen per rij

- **Meldingen:** R2-008, R2-059, R2-089, R2-097, R2-102, R2-108 (ook X-37).
- **Voorstel:** de toonlijst `gezond | beperkt | storing | onbekend | gate` uitbreiden met `nog-niet` (hourglass,
  neutraal op `--muted`), `niet-beschikbaar` (circle-slash, stippel; telt als Onbekend), `beleid` (ban, stijl van de gate;
  "Alleen meten" bij de boiler), `verouderd` (clock-alert, stippel + arcering, ≥ 4,5:1 op de donkerste arceerpixel) en
  een neutrale pil voor feiten in het dienstblok; of een optionele plek `{{icoon}}` per rij uit een vaste lijst.

<a id="e04"></a>
### E04 — "Niet gekoppeld" in de controles: één icoon per betekenis

- **Meldingen:** R2-088, R2-098, R2-106.
- **Voorstel:** prototype `statuspagina.html` en COMPONENTEN §4/§25 gelijktrekken: in de controles de pil volgens de
  gezondheid (Onbekend/Storing) met de precieze toestand vooraan in de reden, of `link-2-off` via E03; nooit twee iconen
  voor "Niet gekoppeld" op één pagina.

<a id="e05"></a>
### E05 — Rol van de melding (alert/status/geen)

- **Meldingen:** R2-060, R2-090, R2-103.
- **Voorstel:** plek `{{melding_rol}}` met vaste waarden `alert` (fout van dít verzoek), `status` (info) of leeg (een
  toestand die bij het laden al bestond); C-14 "geen alert-spam", WCAG 4.1.3.

<a id="e06"></a>
### E06 — Codes en lange woorden in meldingen en redenen

- **Meldingen:** R2-013, R2-022, R2-061, R2-091, R2-099, R2-104.
- **Voorstel:** `melding_code` los van `trace_id` (blijvende toestanden hebben geen trace-ID; een opgeslagen fout toont
  de trace-ID van het paginaverzoek); optionele `{{reden_code}}` als `<code>`; een mono-plek voor paden en namen in
  meldingen (`<code>` met `<wbr>` na `/`); `overflow-wrap: anywhere` op `.melding p`, `.checks .reden` en `.feiten dd`.

<a id="e07"></a>
### E07 — Referentie-renderer: één doorgang

- **Meldingen:** R2-014, R2-025, R2-085, R2-107.
- **Voorstel:** `bouw/sjabloon.mjs` vult alles in één doorgang (of escapet `{` in waarden), zodat een waarde met
  `{{x}}` nooit opnieuw wordt ingevuld (een bronnaam `{{csrf_token}}` zou anders de CSRF-waarde tonen). Daarna de
  Python-renderers van de vijf diensten gelijktrekken; byte-gelijke uitvoer voor de prototypes blijft de test.

<a id="e08"></a>
### E08 — Drift- en pinregel van de kopieën

- **Meldingen:** R2-010, R2-016, R2-023, R2-024, R2-074.
- **Voorstel:** ONTWERPTAAL §13.2/§14: de kopie pint versie **en** commit-SHA van de bron (Peil staat alleen op de
  werkbranch, niet op `main`); CI faalt bij een afwijking van de gepinde inhoud of bij dezelfde versie met andere inhoud;
  een nieuwere bronversie geeft alleen een waarschuwing (bijwerken met `tools/peil_kopie.py bijwerken` + tests). Dat is
  wat HCH, ASF en ZPA al doen; JLP faalt nu bij elke nieuwe versie (bewust) en wordt gelijkgetrokken.

<a id="e09"></a>
### E09 — Overige sjabloonpunten: novalidate, (verplicht), skiplink, knop, rijopbouw, bron

- **Meldingen:** R2-009, R2-101, R2-105 (ook X-36, X-38).
- **Voorstel:** `novalidate` op alle statuspaginaformulieren (de diensten valideren server-side met NL-teksten; native
  validatie blokkeert nu `192.168.1.10:30400` met een Engelse browsermelding); "(verplicht)" bij de drie velden; de
  skiplink verbergen met `transform`/`clip-path` in plaats van `top:-4rem`; "Hub openen" als losse knop van 44 px; rijen
  in `.checks` als raster (naam + pil op regel 1, tijd + reden op regel 2); een plek `{{bron}}` in plaats van de vaste
  tekst "Bron: /readyz en /healthz"; een scheiding tussen pil en toelichting voor schermlezers.

<a id="e10"></a>
### E10 — Totaalstatus van een statuspagina: wat telt mee

- **Meldingen:** R2-094, R2-126.
- **Voorstel:** regel in ONTWERPTAAL §13.2: een **verse** meting met Storing of Beperkt in "Wat deze dienst doet" maakt het
  totaal hooguit Beperkt; niet ingestelde en verouderde domeinen tellen niet mee. Functies die capability_unavailable
  geven (bv. de import van ASF op een echte installatie) krijgen een rij "Niet beschikbaar" (telt als Onbekend), zodat de
  pagina geen "Alles gezond" toont zonder die functie. Beide vragen een ontwerpstap (§13) en een besluit van de bouwer.

<a id="e11"></a>
### E11 — Zekerheid als woord met vaste drempels

- **Meldingen:** R2-130, R2-139 (ook X-26).
- **Voorstel:** Peil legt de drempels vast (OB-04 van de Hub): ≥ 0,85 Zeker · ≥ 0,6 Waarschijnlijk · lager Onzeker ·
  leeg "Ik weet het niet"; het getal alleen onder "Toon bewijs". MSO gebruikt dezelfde indeling zodra zijn API een
  zekerheid levert.

<a id="e12"></a>
### E12 — Reflow testen met het lettertype van de CI-runner

- **Meldingen:** R2-147.
- **Voorstel:** ONTWERPTAAL §12: reflow en overloop worden getest met het systeemlettertype van de CI-runner (DejaVu Sans,
  breder dan Noto Sans); lokaal na te doen met een vlag zoals `PEIL_REVIEW_LETTER`. Peil gebruikt bewust het
  systeemfont, dus elk gangbaar systeemfont moet passen.

<a id="e13"></a>
### E13 — Woorden: "Niet beschikbaar" (aflevering) en "Verzonden"

- **Bronnen:** X-23, X-27.
- **Voorstel:** een ander woord voor "indexers vinden niets" in MediaGuard (bv. "Niet te vinden"), zodat "Niet
  beschikbaar" alleen de capability-betekenis heeft; het readback-woord "Verzonden — wacht op bevestiging" (my_house)
  overnemen in plaats van "Verstuurd".

<a id="e14"></a>
### E14 — Aliaslaag en tokens: focusring, scroll-padding, randen, -soft-vlakken

- **Bronnen:** X-22, X-29, X-30, X-32.
- **Voorstel:** in de generator van de aliaslagen de focusring en `scroll-padding` zo zetten dat ze niet verliezen van
  ongelaagde app-CSS (`mg.css`); een rand-token voor gekozen domeinknoppen; `domain-*-soft` als tekstvlak met een paar van
  ≥ 7:1 (of tekst op `-bg`); de aliaslaag-correcties uit PEIL_MIGRATIE §8.1 (my_house) in de generator in plaats van per
  app.

<a id="e15"></a>
### E15 — Verouderd: regel voor statuspillen en bediening

- **Bronnen:** X-21, X-31.
- **Voorstel:** één regel voor offline/verouderd: een laatst bekende Gezond wordt Verouderd; Beperkt en Storing blijven
  staan (ADR-0011 my_house). "Bediening uit bij verouderde gegevens" (PEIL_MIGRATIE §10.3) geldt voor de Hub; in
  bestaande apps alleen in een functionele ronde (het is gedrag, geen uiterlijk; MediaGuard ADR-0018 punt 8).

<a id="e16"></a>
### E16 — Ondernavigatie op 320 px

- **Bronnen:** X-28.
- **Voorstel:** regel voor 320 px: actief zonder extra gewicht (alleen de balk), of een kortere vaste set labels; het
  vette actieve label is nu 2 px breder dan zijn kolom van 64 px.

## 8. Open besluiten voor de gebruiker (uit deze inventaris)

| Besluit | Groep | Tot het besluit geldt |
|---|---|---|
| BG-05: mag de Hub MediaGuard laten zoeken/herstellen (met goedkeuring per actie)? | A05 | alleen deeplinks (`handmatig_in_mediaguard`) |
| BG-04: MediaGuard-sleutel van Jelly Leon in Jelly Leon zelf (viewer)? | A05 | geen sleutel, status `onbekend` |
| BG-06/BG-18: welke app levert spraak en embeddings, en in welke repo komt `mt`? | A06 | geen tweede producent, `mt` niet gebouwd |
| 100.64.0.0/10 (Tailscale) toestaan voor de noodlogin? | A07 | niet toegestaan |
| Android-ID's bevestigen (bron: alleen de bouwopdracht) en Swiftfin-bundle-id `org.jellyfin.swiftfin.jellyleon` | A02 | ID's gebouwd, niet verspreid; geen Apple-registratie |
| GHCR-pakket van MediaGuard koppelen aan de nieuwe publieke repo | A01 | geen nieuwe MediaGuard-release |
| `JL_SYNC_PUSH_TOKEN` (besluit 4) | A01 | sync-push uit |
| MediaGuard-Android ook in en-US? Tabelweergave in my_house? | C09 | geen wijziging |

## 9. Tegenstrijdigheden tussen bronnen en de gekozen lezing

1. **`/api/v1/mediaserver/status` "als lijst per server"** (bron 4) tegenover §2.3 regel 1 ("bestaande clients mogen niet
   breken"): gekozen is een **extra** veld `servers[]` naast de bestaande velden (A03), geen vervanging.
2. **Δ-CONTRACT-MG** (B03-plan) tegenover het open besluit BG-05: gekozen is "gereserveerd, niet toegestaan" (A05).
3. **Vingerafdruk met twee policy-sleutels**: HCH en ASF sorteren alle thumbprints, ZPA neemt de laatst gepinde. Gekozen:
   sorteren (A17); ZPA moet om.
4. **`Origin: null`**: HCH en ZPA accepteren hem, ASF/JLP/executor niet. Gekozen: de strengste (`same-origin` + exacte
   `Origin` + `Sec-Fetch-Site`, A13); HCH en ZPA moeten om.
5. **GPU-namen**: het B03-plan noemt A310 en UHD 770 als NAS-GPU's, D08 heeft niets gemeten. Gekozen: rollen in de
   contracttekst, geen hardware als feit (A06).
6. **DNS-rebinding-beperking op de `Host`-header** (A14): veiliger, maar wie de statuspagina via een eigen domeinnaam
   opent, kan daar niet meer koppelen (env-enrollment of de Hub-UI kan wel). Voorgesteld; de contractreview beslist.
7. **Ernst**: drie API-niveaus tegenover vijf Peil-woorden. Gekozen: vijf woorden in events, vaste afbeelding naar de
   drie Hub-niveaus (A25), geen API-breuk.

## 10. Tabel melding → groep (alle 151 meldingen uit ronde 2)

`R2-nnn` = positie in [`CONTRACT_1.3_MELDINGEN_RONDE2.json`](CONTRACT_1.3_MELDINGEN_RONDE2.json) (vanaf 1). De kolom
*Kern* is een samenvatting; de volledige tekst staat in de JSON.

| Melding | Repo | Kern van de melding | Groep | Klasse | Ook in |
|---|---|---|---|---|---|
| R2-001 | jelly-leon | HEALTHCHECK draait als containergebruiker (root) in alle images | A08 | (a) | — |
| R2-002 | jelly-leon | Custom User 568: bounding set niet te legen | A08 | (a) | — |
| R2-003 | jelly-leon | Jelly Leon houdt /config, /cache en /health | A04 | (a) | — |
| R2-004 | jelly-leon | Eén specifieke render-node kiezen is open (B03/P4) | B06 | (b) | — |
| R2-005 | zoeken-en-persoonlijke-ai | Geen Excel-ID voor ZA9 en de statuspagina | A33 | (a) | — |
| R2-006 | zoeken-en-persoonlijke-ai | 'Niet gereed' op de pagina terwijl /readyz 200 geeft | A15 | (a) | — |
| R2-007 | zoeken-en-persoonlijke-ai | Sjabloon mist toestand onleesbaar koppelbestand | E01 | (e) | — |
| R2-008 | zoeken-en-persoonlijke-ai | Geen hourglass voor 'Nog niet beschikbaar' | E03 | (e) | — |
| R2-009 | zoeken-en-persoonlijke-ai | Vaste tekst 'Bron: /readyz en /healthz' te smal | E09 | (e) | — |
| R2-010 | zoeken-en-persoonlijke-ai | Peil alleen op de werkbranch; kopie op SHA gepind | E08 | (e) | — |
| R2-011 | zoeken-en-persoonlijke-ai | Formuliervelden hub_adres/koppelcode/hub_vingerafdruk overgenomen | B01 | (b) | — |
| R2-012 | jelly-leon-platform | Geen koppelblok bij onleesbaar bestand (koppeling_onbekend) | E01 | (e) | — |
| R2-013 | jelly-leon-platform | Foutcode alleen samen met trace-ID | E06 | (e) | — |
| R2-014 | jelly-leon-platform | Referentie-renderer vervangt {{x}} twee keer | E07 | (e) | — |
| R2-015 | jelly-leon-platform | Formuliernamen: andere diensten moeten volgen | B01 | (b) | — |
| R2-016 | jelly-leon-platform | CI vergelijkt met de werkbranch, niet main | E08 | (e) | — |
| R2-017 | jelly-leon-web | 'Niet per repo aanpassen' tegenover kopie door orkestratie | A35 | (a) | — |
| R2-018 | jelly-leon-web | Kopie bevat kapotte relatieve ADR-links | A35 | (a) | — |
| R2-019 | jelly-leon-web | Kwaliteitseisen passen niet op de webclient | B03 | (b) | — |
| R2-020 | jelly-leon-web | Repo-scan pas na het publiek maken | B05 | (b) | — |
| R2-021 | appstore-en-fork | Geen blok voor onleesbaar hub-link.json | E01 | (e) | — |
| R2-022 | appstore-en-fork | last_error zonder trace-ID tegenover §13.2 | E06 | (e) | A12 |
| R2-023 | appstore-en-fork | 'CI faalt bij drift' botst met versie-pinnen | E08 | (e) | — |
| R2-024 | appstore-en-fork | Peil 1.1.0 alleen op de werkbranch (172ee87) | E08 | (e) | — |
| R2-025 | appstore-en-fork | Renderer vult '{{csrf_token}}' in een waarde in | E07 | (e) | — |
| R2-026 | appstore-en-fork | service_token_last4 heeft geen plek in het sjabloon | D01 | (d) | — |
| R2-027 | jelly-leon-clients | 'Nooit org.jellyfin.*' tegenover gekozen applicationId's | A02 | (a) | — |
| R2-028 | jelly-leon-clients | Gekozen ID's niet in ai-server-manager vastgelegd | A02 | (a) | — |
| R2-029 | jelly-leon-clients | JC2: ook project.pbxproj zet de bundle-id | A02 | (a) | — |
| R2-030 | jelly-leon-clients | Swiftfin-bundle-id: bevestiging gebruiker nodig | A02 | (a) | — |
| R2-031 | jelly-leon-clients | Kwaliteitseisen N.v.t. voor apparaat-apps | B03 | (b) | — |
| R2-032 | home-control-hub | Vingerafdruk bij twee policy-sleutels | A17 | (a) | — |
| R2-033 | home-control-hub | Geen reason voor ontbrekende header of JWT zonder kid | A16 | (a) | — |
| R2-034 | home-control-hub | HEALTHCHECK als root tegenover 'geen proces als root' | A08 | (a) | — |
| R2-035 | home-control-hub | Telt ongeldige invoer als poging? | A14 | (a) | — |
| R2-036 | home-control-hub | last_error-codes niet uitputtend; eigen codes | A12 | (a) | — |
| R2-037 | home-control-hub | Elke POST verbruikt de jti, ook zonder Idempotency-Key | A16 | (a) | A20 |
| R2-038 | home-control-hub | Ongeldige base_url → 422 verbrandt het token | A11 | (a) | — |
| R2-039 | home-control-hub | Na ontkoppelen is GET hub-link onbereikbaar | B04 | (b) | — |
| R2-040 | home-control-hub | HUB_* zijn geen manifestparameters | A11 | (a) | — |
| R2-041 | home-control-hub | Ontkoppelen via de Hub-route niet end-to-end getest | C04 | (c) | — |
| R2-042 | jelly-leon-web | Geen consistentie blokkade ↔ validatie | A33 | (a) | — |
| R2-043 | jelly-leon-web | Kwaliteitseisen webclient (herhaling) | B03 | (b) | — |
| R2-044 | jelly-leon-web | Kapotte relatieve links (herhaling) | A35 | (a) | — |
| R2-045 | jelly-leon | Healthcheck: kort root vóór de wissel; platformbesluit | A08 | (a) | — |
| R2-046 | jelly-leon | /healthz,/readyz botst met Jellyfin-conventies | A04 | (a) | — |
| R2-047 | jelly-leon | CapBnd blijft bij Custom User (herhaling) | A08 | (a) | — |
| R2-048 | jelly-leon-clients | applicationId-regel en besluit vastleggen (review) | A02 | (a) | — |
| R2-049 | jelly-leon-clients | JC2 moet de pbxproj-regel noemen (review) | A02 | (a) | — |
| R2-050 | ai-server-manager | Heartbeat-route niet in contract 1.2 | A19 | (a) | — |
| R2-051 | ai-server-manager | Heartbeat-dedupe hoort bij de §5-uitzonderingen | A20 | (a) | A19 |
| R2-052 | ai-server-manager | Geen vaste checknamen in connector-health | A22 | (a) | — |
| R2-053 | ai-server-manager | custom_app in app.query betekent compose-app | A09 | (a) | — |
| R2-054 | ai-server-manager | Resourcegrenzen alleen via app-config → unknown | C03 | (c) | — |
| R2-055 | ai-server-manager | reporting.realtime is een event source | A29 | (a) | — |
| R2-056 | ai-server-manager | Beszel kent geen API-tokens: wachtwoord in vault | C03 | (c) | — |
| R2-057 | ai-server-manager | ADR-nummering tussen bouwers | C05 | (c) | — |
| R2-058 | zoeken-en-persoonlijke-ai | Geen koppelblok bij onleesbare koppelstatus | E01 | (e) | — |
| R2-059 | zoeken-en-persoonlijke-ai | Tonen 'Nog niet beschikbaar'/'Niet beschikbaar' ontbreken | E03 | (e) | — |
| R2-060 | zoeken-en-persoonlijke-ai | role="alert" vast op elke melding | E05 | (e) | — |
| R2-061 | zoeken-en-persoonlijke-ai | 'reden' is alleen tekst: codes niet in mono | E06 | (e) | — |
| R2-062 | zoeken-en-persoonlijke-ai | Geen Excel-ID voor de ontwerpreview | A33 | (a) | — |
| R2-063 | appstore-en-fork | Hub-appcatalogus niet leesbaar voor diensten | A18 | (a) | — |
| R2-064 | appstore-en-fork | Inventaris zonder labels/namespace (B08-002) | C06 | (c) | — |
| R2-065 | appstore-en-fork | Adoptie als eigen documentsoort kind: adoption | A31 | (a) | — |
| R2-066 | appstore-en-fork | 'Eigenaar' niet gedefinieerd | A31 | (a) | — |
| R2-067 | appstore-en-fork | Statuswoorden onbekend/kandidaat/adopted | A31 | (a) | — |
| R2-068 | appstore-en-fork | Fake TrueNAS gebruikt andere MediaGuard-imagenaam | C02 | (c) | — |
| R2-069 | appstore-en-fork | Readback hangt aan images[0] | C02 | (c) | — |
| R2-070 | appstore-en-fork | Appstore eist ≤ 15 min, Hub-TTL instelbaar | A23 | (a) | C06 |
| R2-071 | appstore-en-fork | Snapotter: geen automatische herkenning | C06 | (c) | — |
| R2-072 | home-control-hub | Geen toestand voor onleesbaar koppelbestand | E01 | (e) | — |
| R2-073 | home-control-hub | Koppelen bezig: formulier niet apart te verbergen | E02 | (e) | A14 |
| R2-074 | home-control-hub | Is een nieuwere bronversie drift? | E08 | (e) | — |
| R2-075 | home-control-hub | 'Gereed' voor de statuspagina niet gedefinieerd | A15 | (a) | — |
| R2-076 | home-control-hub | service_id, via en last4 niet meer op de pagina | D01 | (d) | — |
| R2-077 | jelly-leon-platform | Geen geaccepteerde waarschuwingen per manifest | A30 | (a) | A10 |
| R2-078 | jelly-leon-platform | Geen I-document zonder installatie (checklist) | A30 | (a) | — |
| R2-079 | jelly-leon-platform | Eén container met catalogusapp: dubbelzinnig | A09 | (a) | — |
| R2-080 | jelly-leon-platform | I01 stap 3 schrijft shellopdrachten voor | C08 | (c) | — |
| R2-081 | jelly-leon-platform | Open eerste-gebruik-venster; post_install_checks | A30 | (a) | — |
| R2-082 | jelly-leon-platform | container_port bij de Authentik-catalogusapp | A30 | (a) | — |
| R2-083 | zoeken-en-persoonlijke-ai | no-referrer geeft Origin null; Sec-Fetch-Site | A13 | (a) | — |
| R2-084 | zoeken-en-persoonlijke-ai | Geen validatiewaarde voor 'Niet gestart' | A33 | (a) | — |
| R2-085 | zoeken-en-persoonlijke-ai | Renderer dubbele vervanging; Python doet hetzelfde | E07 | (e) | — |
| R2-086 | zoeken-en-persoonlijke-ai | Geen Excel-ID statuspagina/QA (herhaling) | A33 | (a) | — |
| R2-087 | home-control-hub | Geen TTL voor bronmetingen op de statuspagina | A23 | (a) | — |
| R2-088 | home-control-hub | Prototype: '(?) Niet gekoppeld' met circle-help | E04 | (e) | — |
| R2-089 | home-control-hub | Geen symbool ban voor beleid | E03 | (e) | — |
| R2-090 | home-control-hub | role="alert" vast (home-control-hub) | E05 | (e) | — |
| R2-091 | home-control-hub | Lopende tekst in meldingen breekt niet | E06 | (e) | — |
| R2-092 | home-control-hub | Geen blok onleesbaar, geen weergave koppelen bezig | E01 | (e) | E02 |
| R2-093 | home-control-hub | §13-breedtes en WCAG-versie wijken af | A34 | (a) | — |
| R2-094 | home-control-hub | Prototype: beperkte bron maakt totaal Beperkt | E10 | (e) | — |
| R2-095 | appstore-en-fork | no-referrer maakte elke POST 403 (gerepareerd) | A13 | (a) | — |
| R2-096 | appstore-en-fork | Referrer-Policy/Origin verschilt per dienst | A13 | (a) | — |
| R2-097 | appstore-en-fork | Geen neutrale pil voor feiten | E03 | (e) | — |
| R2-098 | appstore-en-fork | 'Niet gekoppeld' krijgt circle-help | E04 | (e) | E03 |
| R2-099 | appstore-en-fork | Geen mono-plek voor paden in meldingen | E06 | (e) | — |
| R2-100 | appstore-en-fork | Leeg koppelblok bij onleesbaar bestand (review) | E01 | (e) | — |
| R2-101 | jelly-leon-platform | Native browservalidatie vóór de NL-veldfout | E09 | (e) | — |
| R2-102 | jelly-leon-platform | Controlerij kan alleen het icoon van zijn toon | E03 | (e) | E04 |
| R2-103 | jelly-leon-platform | role="alert" ook bij blijvende toestand | E05 | (e) | — |
| R2-104 | jelly-leon-platform | melding_code los van trace_id | E06 | (e) | — |
| R2-105 | jelly-leon-platform | Skiplink met top:-4rem steekt uit | E09 | (e) | — |
| R2-106 | jelly-leon-platform | Prototype: 'Niet gekoppeld' met twee iconen | E04 | (e) | — |
| R2-107 | jelly-leon-platform | sjabloon.mjs vervangt twee keer (herhaling) | E07 | (e) | — |
| R2-108 | jelly-leon-platform | 'Nog niet beschikbaar' met slot i.p.v. hourglass | E03 | (e) | — |
| R2-109 | ai-server-manager | Geen vaste vorm voor crash en herstel | A24 | (a) | — |
| R2-110 | ai-server-manager | Geen ernst in de payload | A25 | (a) | A24 |
| R2-111 | ai-server-manager | Log-sink niet in het contract | A19 | (a) | A20 |
| R2-112 | ai-server-manager | sso.access.revoked zonder OIDC-sub | A26 | (a) | — |
| R2-113 | ai-server-manager | Wie beheert groep→rol | A27 | (a) | — |
| R2-114 | ai-server-manager | Geen duur voor SSO-sessies | A27 | (a) | — |
| R2-115 | ai-server-manager | D17 https tegenover http-redirect | A27 | (a) | — |
| R2-116 | ai-server-manager | Runbook-catalogus vóór de policy-engine | C03 | (c) | — |
| R2-117 | ai-server-manager | OIDC-start en callback zonder Idempotency-Key | A20 | (a) | A27 |
| R2-118 | ai-server-manager | Domeinen van event_types per eigenaar | A24 | (a) | — |
| R2-119 | home-control-hub | Onleesbaar hub-link.json: wat te doen | A12 | (a) | — |
| R2-120 | home-control-hub | aud als lijst niet expliciet ongeldig | A16 | (a) | — |
| R2-121 | home-control-hub | IP-vorm in HUB_URL niet vastgelegd | A11 | (a) | — |
| R2-122 | home-control-hub | TTL van bronmetingen in de API | A23 | (a) | — |
| R2-123 | appstore-en-fork | Totaal van connector-health uit de checks | A22 | (a) | — |
| R2-124 | appstore-en-fork | Paginering zonder snapshot-ID | A21 | (a) | A18 |
| R2-125 | appstore-en-fork | DNS-rebinding vergroot het restrisico van §3.7 | A14 | (a) | — |
| R2-126 | appstore-en-fork | Importstatus ontbreekt; pagina kan 'Alles gezond' tonen | E10 | (e) | — |
| R2-127 | jelly-leon-platform | Monitorplan (I08-08-03) zonder eigenaar | A32 | (a) | — |
| R2-128 | jelly-leon-platform | Runtime-kenmerken van upstream-images | A30 | (a) | A32 |
| R2-129 | ai-server-manager | Ernst: 3 API-niveaus, 5 Peil-woorden | A25 | (a) | — |
| R2-130 | ai-server-manager | Zekerheid als getal tegenover Peil-woorden | E11 | (e) | — |
| R2-131 | ai-server-manager | P1: alleen risk_claim, geen RisicoBadge | C03 | (c) | — |
| R2-132 | ai-server-manager | Geen lijst van open koppelcodes/tokens | C01 | (c) | — |
| R2-133 | ai-server-manager | otpauth-issuer moet de productnaam zijn | B02 | (b) | — |
| R2-134 | ai-server-manager | Alleen pool.gezond, geen DEGRADED/FAULTED | C01 | (c) | — |
| R2-135 | ai-server-manager | GET /api/v1/apps sorteert op naam | C01 | (c) | — |
| R2-136 | ai-server-manager | §11 alleen Excel-ID's: H5/H6/H12 | A33 | (a) | — |
| R2-137 | ai-server-manager | 401 voor sessie én foute TOTP-code | A21 | (a) | — |
| R2-138 | ai-server-manager | Ernst-afbeelding (herhaling) | A25 | (a) | — |
| R2-139 | ai-server-manager | Zekerheid-drempels (herhaling) | E11 | (e) | — |
| R2-140 | ai-server-manager | Incidenten niet per app te filteren | C01 | (c) | — |
| R2-141 | ai-server-manager | Geen lijst open koppelcodes (herhaling) | C01 | (c) | — |
| R2-142 | ai-server-manager | sorteer=status (herhaling) | C01 | (c) | — |
| R2-143 | ai-server-manager | Executor accepteert oude en nieuwe veldnamen | B01 | (b) | — |
| R2-144 | ai-server-manager | §13 gelijktrekken met ONTWERPTAAL §12 | A34 | (a) | — |
| R2-145 | ai-server-manager | CSRF zonder JavaScript: Origin null of exact | A13 | (a) | — |
| R2-146 | ai-server-manager | Geen Excel-ID voor de ontwerpreview (Hub) | A33 | (a) | — |
| R2-147 | ai-server-manager | Lettertype voor reflow niet vastgelegd | E12 | (e) | A34 |
| R2-148 | ai-server-manager | 44 px voor losse links | B07 | (b) | — |
| R2-149 | ai-server-manager | same-origin + exacte Origin voor alle pagina's | A13 | (a) | — |
| R2-150 | ai-server-manager | Uitzonderingen uit de code in §5 opnemen | A20 | (a) | — |
| R2-151 | ai-server-manager | Regel voor het terugkeerpad na inloggen | A27 | (a) | — |

## 11. Overige bronnen → groep

| ID | Bron | Kern | Groep | Klasse | Ook in |
|---|---|---|---|---|---|
| U-01 | B03_BESLUITEN §1 (Emby), STATUS.md | Gebruiker gebruikt nu Emby; blijft als terugval tot de gebruiker hem verwijdert | A03 | (a) | A31 |
| U-02 | B03_BESLUITEN §1, ADR-0018 aanvulling | MediaGuard volgt Emby én Jelly Leon; /api/v1/mediaserver/status per server | A03 | (a) | — |
| U-03 | BG-01, B03 h18 | Δ-MG-AUTH per server (Emby X-Emby-Token, Jelly Leon 12.x MediaBrowser Token) | A03 | (a) | A04 |
| U-04 | ADR-0020, B03 h18 | HARDE EIS: kijkgeschiedenis en MediaGuard-voortgang altijd beschikbaar | A03 | (a) | — |
| U-05 | STATUS.md (vervolgbesluiten) | Alle eigen repos publiek met GPL-3.0; §10 'geen licentie' vervalt | A01 | (a) | — |
| U-06 | STATUS.md (vervolgbesluiten) | MediaGuard in een nieuwe publieke repo met schone historie | A01 | (a) | A03 |
| U-07 | B03 §10.17, Δ-ASM-EXCEL | §11 krijgt de validatiewaarde 'Intel-iGPU-getest (ontwikkelmachine)' | A33 | (a) | — |
| U-08 | STATUS.md | my_house 0.2.0 gepubliceerd; JL_SYNC_PUSH_TOKEN nog open | A01 | (a) | — |
| Δ-CONTRACT-MG | B03 h18 | Hub mag met goedkeuring MediaGuard-acties laten uitvoeren; quarantine.restore R3 | A05 | (a) | — |
| Δ-CONTRACT-MT | B03 h18, ADR-0019 | Optionele app mt in de apptabel | A06 | (a) | — |
| Δ-CONTRACT-MODEL | B03 h18, ADR-0019 | Eén producent per modelsoort; GPU-rol model-apps | A06 | (a) | — |
| Δ-CONTRACT-NET | B03 h18 | 100.64.0.0/10 niet als privé voor de noodlogin | A07 | (a) | — |
| Δ-MG-AUTH | B03 h18 | Authenticatie per server in MediaGuard | A03 | (a) | — |
| Δ-MG-DUAL | B03 h18 | MediaGuard volgt meerdere mediaservers tegelijk | A03 | (a) | — |
| Δ-MG-1…8, Δ-MG-DV | B03 h18 | MediaGuard-uitbreidingen (bevindingen, opnieuw binnenhalen, scopes, kijkpauze …) | C12 | (c) | A05 |
| Δ-HUB-1 | B03 h18 | action_id's voor Δ-CONTRACT-MG, pas na de contractwijziging | A05 | (a) | — |
| Δ-HUB-2, Δ-HUB-3, Δ-HUB-JL | B03 h18 | Hub-kaarten, B12-dekking (Emby-archief), Hub-adapter Jelly Leon | C12 | (c) | A03 |
| Δ-ASM-EXCEL | B03 h18 | Excel-bijwerker opgeleverd; §11-waarde nog open | A33 | (a) | — |
| Δ-ZK-1, Δ-ZK-2 | B03 h18 | machine_translation in B07; één embeddingproducent | C12 | (c) | A06 |
| ADR-0016 | ai-server-manager | Eén foutcatalogus; 1 MiB per route als erkende afwijking | A21 | (a) | A04 |
| ADR-0017 | ai-server-manager | Hub-koppeling JL4; geen titels naar de Hub | A04 | (a) | — |
| ADR-0018 | ai-server-manager | MediaGuard: één viewerclient, geen mutaties tot contractwijziging | A05 | (a) | A03 |
| ADR-0019 | ai-server-manager | Optionele model-apps buiten de image, één producent | A06 | (a) | — |
| ADR-0020 | ai-server-manager | Kijkgeschiedenis altijd beschikbaar; overname vanuit Emby | A03 | (a) | — |
| B03-§10.10 | B03 §10.10 | media.*-eventtypes van Jelly Leon | A24 | (a) | — |
| P-01 | ADR-0021 §3, monitoring/heartbeat.py | POST /api/v1/monitoring/heartbeat | A19 | (a) | A20 |
| P-02 | events/envelope.py, home-control-hub ADR-0009 | Eventregex en -grenzen van de Hub-inbox | A24 | (a) | — |
| P-03 | ADR-0021 §2, home-control-hub sources.py, appstore hubinventory.py | max_age per capability/bron | A23 | (a) | — |
| P-04 | home-control-hub ADR-0007 punt 5/8 | Eigenaar-connector voor sso.*-acties (sso.oidc.hub.register, sso.sessions.revoke) | A28 | (a) | — |
| P-05 | home-control-hub ADR-0007 punt 8, domains/sso/backup.py | Back-upbevestiging per app door de Hub | A28 | (a) | — |
| P-06 | home-control-hub domains/sso/backup.py ('catalogusversie') | Catalogusbeschikbaarheid van een versie | A18 | (a) | — |
| P-07 | home-control-hub ADR-0007 Gevolgen | Overdracht van het OIDC-client_secret naar de Hub-vault | A10 | (a) | — |
| P-08 | ADR-0022 §4, routers/logs.py | POST /api/v1/logs (log-sink) | A19 | (a) | A20 |
| P-09 | CONTRACT_1.2_CONFORMITEIT H13, contract §4.4 | Scopes per dienst op de Hub-connector (open punt 1.2) | A18 | (a) | — |
| X-01 | home-control-hub ADR-0009 punt 5 | Eventnamen met vier segmenten hernoemd; grenzen entity/actor/payload | A24 | (a) | — |
| X-02 | home-control-hub ADR-0009 punt 1–3 | least_privilege nooit ok; rechtenkaart 'verouderd' nooit groen | B08 | (b) | — |
| X-03 | home-control-hub ADR-0010 punt 4 | Extra velden token_rotation_requested_at, key_rotation_blocked_sequence | A12 | (a) | — |
| X-04 | home-control-hub ADR-0010 punt 11 | Reason ontbrekende header/zonder kid (= R2-033) | A16 | (a) | — |
| X-05 | home-control-hub ADR-0013 punt 1 | unreadable_replaced_at, origineel bewaren (= R2-119) | A12 | (a) | — |
| X-06 | home-control-hub ADR-0013 punt 3–4 | aud als lijst en afwijkende IPv4-vormen (= R2-120/121) | A16 | (a) | A11 |
| X-07 | zoeken-en-persoonlijke-ai ADR-0011 | Enroll-antwoord mist rotation_sequence | A17 | (a) | — |
| X-08 | zoeken-en-persoonlijke-ai ADR-0011 | Twee policy-sleutels: 'laatst gepinde telt' (botst met home-control-hub/appstore) | A17 | (a) | — |
| X-09 | zoeken-en-persoonlijke-ai ADR-0011 | 'Nooit de laatste sleutel intrekken': lezing | A17 | (a) | — |
| X-10 | zoeken-en-persoonlijke-ai ADR-0011/0012 | Onleesbare body zonder auth gaf 422 i.p.v. 401 (opgelost) | A16 | (a) | — |
| X-11 | zoeken-en-persoonlijke-ai ADR-0012 | Hub trekt oude tokens in vóór gebruik van het nieuwe | A17 | (a) | — |
| X-12 | zoeken-en-persoonlijke-ai ADR-0015 Q-01 | Foutmelding uit de URL zonder echte poging | A14 | (a) | — |
| X-13 | zoeken-en-persoonlijke-ai ADR-0015 Q-02 | Invoer afgekapt vóór de controle | A21 | (a) | A14 |
| X-14 | zoeken-en-persoonlijke-ai ADR-0015 Q-06 | Trace-ID van een poging in de app-log | A14 | (a) | — |
| X-15 | zoeken-en-persoonlijke-ai ADR-0015 Q-07 | Validatie per Excel-blad; lege validatie | A33 | (a) | — |
| X-16 | appstore-en-fork ADR-0012 | 429 van de Hub-inventaris zonder Retry-After | C06 | (c) | — |
| X-17 | jelly-leon-platform EVIDENCE I09-09-01 | Geheimen van de Authentik-catalogusapp door de Hub; executor vult in P2 | A10 | (a) | A30 |
| X-18 | jelly-leon-web ADR-0011 'Gemelde contractpunten' 1–3 | Webhaak-namen, UG-WEB-nummering, Node-image op digest | C07 | (c) | — |
| X-19 | media-guard-ultimate ADR-0016 p1, media-source-optimizer ADR-0006, my_house ADR-0008 p3 | Hub-adres voor 'Terug naar de Hub' verschilt per app | A36 | (a) | — |
| X-20 | media-guard-ultimate ADR-0016 p4 | Android-app ook en-US? (besluit) | C09 | (c) | — |
| X-21 | media-guard-ultimate ADR-0018 p8 | Bediening uit bij verouderd = gedragswijziging | E15 | (e) | — |
| X-22 | media-guard-ultimate ADR-0016, media-source-optimizer ADR-0006 p6 | Peil-focusring/scroll-padding in @layer base verliezen van mg.css | E14 | (e) | — |
| X-23 | media-guard-ultimate PEIL_REVIEW §7.2, §10 | 'Niet beschikbaar' (aflevering) botst met capability-term | E13 | (e) | — |
| X-24 | media-guard-ultimate PEIL_REVIEW §10 | en-US-servertekst, kleurregel grafiek, verversen, SysteemStatusPaneel | C09 | (c) | — |
| X-25 | media-source-optimizer PEIL_REVIEW §4, §9 (A-1, A-2, O-1…O-6, O-8…O-10) | SysteemStatusPaneel, KPI-bron, core-woorden, fase 2d | C10 | (c) | — |
| X-26 | media-source-optimizer PEIL_REVIEW A-3/O-7 | Zekerheid als getal + balk; indeling nodig | E11 | (e) | — |
| X-27 | my_house PEIL_REVIEW §8.1 | Readback-woord 'Verzonden' i.p.v. 'Verstuurd' | E13 | (e) | — |
| X-28 | my_house PEIL_REVIEW §8.2 | Ondernavigatie op 320 px | E16 | (e) | — |
| X-29 | my_house PEIL_REVIEW §8.3 | domain-*-soft draagt tekst: contrast | E14 | (e) | — |
| X-30 | my_house PEIL_REVIEW §8.4, ADR-0010 p5 | Rand-token voor gekozen domeinknoppen | E14 | (e) | — |
| X-31 | my_house PEIL_REVIEW §8.5, ADR-0011 | Offline/verouderd-regel voor statuspillen | E15 | (e) | — |
| X-32 | my_house PEIL_REVIEW §8.6 | Aliaslaag-correcties uit PEIL_MIGRATIE §8.1 in de generator | E14 | (e) | — |
| X-33 | my_house PEIL_REVIEW §6 | Tabelweergave bij 'Laatste 24 uur' (akkoord gebruiker) | C09 | (c) | — |
| X-34 | my_house EVIDENCE B06-006 | Lees-connector/outbox alleen op verzoek van de adapter-eigenaar | B08 | (b) | — |
| X-35 | ai-server-manager PEIL_REVIEW N-02…N-05, N-07 | Zoeken/Live in kopbalk, tab-iconen, inline styles, compacte rijen, databasepool | C11 | (c) | — |
| X-36 | home-control-hub PEIL_REVIEW §6 S-5…S-7, §7 V-2 | (verplicht), rijopbouw, 'Hub openen', schermlezerscheiding | E09 | (e) | — |
| X-37 | home-control-hub PEIL_REVIEW §6 S-2 | Verouderd-variant met clock-alert | E03 | (e) | — |
| X-38 | zoeken-en-persoonlijke-ai PEIL_REVIEW §6 S-03, S-07 | Rijen in .checks, 'Hub openen' 22 px | E09 | (e) | — |
| X-39 | zoeken-en-persoonlijke-ai PEIL_REVIEW §6 S-08 | Forced colors: rand ook op Gezond | D02 | (d) | — |
| X-40 | code van HCH/ASF/JLP/ZPA (gemeten 2026-11-10) | service.*-eventnamen verschillen per dienst | A24 | (a) | — |
| X-41 | appstore-en-fork PEIL_REVIEW §7.4 | Origin en Referrer-Policy in de sjabloonbeschrijving (= R2-096) | A13 | (a) | — |
| X-42 | jelly-leon ADR-0026 | Intel-iGPU-getest staat in de opmerking (waarde ontbreekt in §11) | A33 | (a) | — |
