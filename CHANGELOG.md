# Changelog

Alle noemenswaardige wijzigingen. Versies volgen `VERSION`; images krijgen exact deze tag (nooit `latest`).

## [0.1.0] — 2026-11-09 (fase P0, backend en web-UI; niet uitgebracht)

### Toegevoegd — fase P2 deel 1: policy-engine, goedkeuringen en executor (ADR-0030; contract 1.3 §8)
- **Risicoclassificatie (B02-005):** `policy/*.yaml` (acties, apps, blokkades) read-only ingebakken in de Hub- én de
  executor-image, met `policy_hash`; gedeeld pakket `asm_policy` (deterministisch, R0–R3; `risk_claim` wordt bewaard
  en genegeerd). Onbekende, destructieve en shell-achtige acties en elke boilerschakeling worden altijd geweigerd;
  Emby en andere beschermde apps worden herkend op naam, catalogusapp én image; is van een bestaande app niet te zien
  wat erin draait (een gestopte Custom App: TrueNAS toont dan geen image), dan wordt elke actie erop geweigerd.
- **Executor (B02-006):** TrueNAS-sleutel met schrijfrechten op de executorpagina (adres en vingerafdruk tonen en
  bevestigen, daarna live testen en versleuteld opslaan); `POST /api/v1/execute` controleert zelf opnieuw handtekening,
  vervaltijd, nonce (eigen SQLite), allowlist, parameterschema, `policy_hash`, risicoklasse en precondities; TrueNAS
  JSON-RPC met `core.get_methods`, before/after-hash en readback; bij een afwijking stopt de executor en volgt een
  incident. `GET /api/v1/executions/{request_id}` leest het journaal.
- **Voorstellen en goedkeuringen in de Hub (B01-007):** `POST/GET /api/v1/actions`, `…/approve`, `…/reject`,
  `…/execute`, `…/reconcile`, `GET /api/v1/policy` en `GET/PUT /api/v1/actions/noodstop`. Een goedkeuring is gebonden
  aan `preview_hash`, `resource_etag` en `policy_hash`, hooguit 15 minuten geldig, één keer bruikbaar en vervalt bij
  elke wijziging van een gebonden veld. Goedkeuren, afwijzen, uitvoeren en ophelderen vergrendelen het verzoek:
  gelijktijdige aanroepen lopen na elkaar en precies één uitvoering bereikt de executor. Migratie 0012
  (`action_request`, `approval`).
- **Apps via de executor (B01-003):** installeren als standaard Custom App (ix-app-waarden via `app.create`, nooit
  `custom_compose_config`), verwijderen alleen de containers (data blijft), terugzetten met de vorige waarden.
- **Blokkades:** pool DEGRADED of onbekend en een rode back-upgate blokkeren opslagmutaties, ook met goedkeuring;
  anti-flap (afkoeltijd, maximum per uur; ook bij gelijktijdige uitvoering) en een noodstop voor alle uitvoering;
  bijwerken en terugzetten vragen een geverifieerd herstelpunt (app-herstelpunten bestaan nog niet →
  `backup_checkpoint_ontbreekt`).
- **Nog niet gebouwd:** de schermen in de Hub-UI voor voorstellen, preview en goedkeuren (nu via de API), een ingang
  voor voorstellen door diensten, flows of AI, en app-herstelpunten (B12). Alles is Sim-getest tegen een fake TrueNAS;
  NIET GEVALIDEERD (echte NAS).

### Gewijzigd — contract 1.3 toegepast in de Hub en de executor (ADR-0029; punten NU van C1.3-ASM)
- **Enroll (C1.3-ASM-02):** antwoord `schema_version` `"1.3"` met `rotation_sequence` (0: geen sleutelrotatie
  gebouwd); `base_url` alleen op type gecontroleerd, een ongeldige waarde wordt `null` met `base_url_genegeerd` en een
  waarschuwing in de Hub-UI; bij herkoppelen vervallen de oude tokens pas bij het eerste gebruik van het nieuwe, en een
  nieuw token dat 60 min ongebruikt blijft, vervalt. Migratie 0011 (`service.base_url_genegeerd`, `hub_setting`,
  `incident.ernst_bron`).
- **Sleutels (C1.3-ASM-03):** vingerafdruk over alle policy-sleutels (Hub en executor), testvector
  `HN69-2PHK-XV2D-X85W`.
- **Noodlogin (C1.3-ASM-05/06):** `100.64.0.0/10` standaard niet privé; `PUT /api/v1/auth/break-glass/cgnat`
  (beheerder, audit, waarschuwing) en de zelftest toont het; `invalid_totp` en een fout eigen wachtwoord binnen een
  sessie geven 422 (401 alleen voor authenticatie); UI onderscheidt op status.
- **Scopes en momentopname (C1.3-ASM-07/08):** vaste leesscopes per dienst (`inventaris.lezen` voor appstore-en-fork
  en jelly-leon-platform), 403 `scope_ontbreekt`; `backup.self`, outbox en bewijs van de Hub-connector alleen voor
  gebruikers; `GET /api/v1/apps` met `snapshot_id`, `meting_observed_at` en 409 `snapshot_changed`; sorteren op status.
- **Events en incidenten (C1.3-ASM-09/10):** domeinen per eigenaar, vaste werkwoorden, ernst in vijf Peil-woorden met
  bronwaarde in de UI (hoog escaleert niet meer); `sso.access.revoked`/`changed` op (`issuer`, `sub`); filter op app.
- **Connector, versheid en log-sink (C1.3-ASM-11/12/13):** totaal = slechtste check, vaste checknamen (ook `jobs`),
  `limits.max_age_s` in `discover`, `max_age` van de bron overgenomen en nooit soepeler dan 900 s (ook de
  inventaris-TTL), `meting_verouderd`; log-opslag zichtbaar ingekort.
- **Koppelstatus in de Hub-UI (C1.3-ASM-16):** `GET /api/v1/services/{id}/koppelstatus` leest de witte lijst en de
  NL-melding bij de dienst zelf; onleesbaar = storing; scopes en genegeerde `base_url` per dienst zichtbaar.
- **Executor als dienst (C1.3-ASM-04/14):** adresregels (canonieke IP-vormen, controle na DNS-resolutie per
  verbinding), onleesbaar koppelbestand fail-closed, `hub_incompatibel`, exacte `Origin` met het schema van het
  verzoek, `Sec-Fetch-Site`, `Host`-beperking (`host_niet_toegestaan`), elke POST een poging (ook `al_gekoppeld`),
  409 `koppelen_bezig`, invoer niet afkappen, één logregel per poging, Gereed = `/readyz` + gekoppeld + bevestigd;
  JWT-regels van §4.7 (`aud` één string, geen `kid` → `unknown_key`, `jti` bij elke POST verbruikt, authenticatie vóór
  rol, `Idempotency-Key` en body); `/api/v1/execute` vraagt eerst een dienst-JWT; statische Idempotency-Key-test;
  browsertest met de negatieve gevallen.
- **Images (C1.3-ASM-01):** bounding set leeg na de eigenaarschapsstap; healthchecks wisselen als eerste handeling naar
  568 met no_new_privs; rooktest controleert CapPrm/CapAmb/CapBnd en de healthcheck apart, en de executor als Custom
  User 568.
- **Peil 1.1.1:** gepinde sjabloonkopie en renderer in één doorgang voor de executor; tokenkopie, ondernavigatie op
  labelbreedte zonder vet actief item, statuspil-radius en "verzonden" in de Hub-UI.
- **Overig:** uitgaande beheerdersadressen volgen de canonieke vormen van §3.2; contract-pin op bron-commit 02b119c
  (C1.3-ALG-01); werkopdrachten noemen contract 1.3 en leggen de KWALITEIT van Python-diensten niet meer op aan
  jelly-leon-web en jelly-leon-clients (C1.3-ASM-23); eigen manifesten met kop "platformcontract 1.3".
- **Eigen manifesten (C1.3-ASM-17, onafhankelijke review):** nu de validator van appstore-en-fork ze kent
  (C1.3-ASF-08): `healthcheck.monitor` op `/readyz` (200, 10 s, 60 s), `accepted_findings: digest_pending_release`
  tot de eerste release en `provenance.license: GPL-3.0`; `--strict` geldig. Nieuwe test `test_eigen_manifesten.py`
  en CI-job `manifest` (validator op een vaste commit). Docs (CUSTOM_APP, README, rooktest) verwijzen naar contract
  1.3.

### Gerepareerd — onafhankelijke review van contract 1.3 (ADR-0028; blijft `contracts 1.3`)
- Dertien correcties RV1–RV13 in het wijzigingslog van het contract, telkens de veiligste lezing: de bestaande
  Emby-koppeling van MediaGuard (bibliotheek bijwerken, afspeeltest) blijft, de rest van het platform schrijft nooit in
  Emby; de HARDE EIS geldt ook voor upgrades die de database van een mediaserver migreren (10.11 → 12.x); geen
  kijkgedrag via de MediaGuard-adapter in de Hub; een `service_id` voor de Jelly Leon-plugin (§4.3); `HUB_URL` bij
  my_house via de vertaling; onleesbaar koppelbestand vervangen vóór het verzoek; ook een POST op een al gekoppelde
  dienst telt als poging; geplakte sleutelsets tellen mee bij een sleutelrotatie; rol en `Idempotency-Key` na de
  authenticatie; formulier-POST's van statuspagina's met reden uitgezonderd van `Idempotency-Key`; types in de
  log-sink; niet gekoppeld = niet pushen, en de eigenaar van een event is (`source_app`, domein); de overstap van
  MediaGuard naar de nieuwe publieke repo is gemeten uitgevoerd (GHCR-koppeling blijft open).
- Conformiteitslijst: C1.3-JLP-02/-03 gecorrigeerd (de gemeten stand klopte niet), de gevolgen van RV1–RV13 per repo
  met regelnummers, Δ-HUB-2 als repowerk en het nieuwe punt C1.3-MH-07 (nu 121 punten).
- `test_contract_13.py` bewaakt het reviewblok en de kernzin van elke correctie in de juiste paragraaf.
- EVIDENCE volgens §11 van 1.3 (C1.3-ASM-15): `test_evidence_contract.py` kent `Intel-iGPU-getest (ontwikkelmachine)`
  en `Niet getest`, eist dat een NIET GEVALIDEERD uit `blokkade` ook in `validatie` staat en controleert `C1.x-…`- en
  `REVIEW-…`-ID's; `tools/excel/update_excel.py` meldt zulke regels in het overzicht `contractpunten_en_reviews`.
  B01-001 en I23-23-08 rechtgezet; nieuwe regels `REVIEW-ai-server-manager-contract-1.3` en `C1.3-ASM-15`.

### Gewijzigd — contract 1.3 vastgesteld (`docs/platform-v2/PLATFORM_CONTRACTEN.md`, ADR-0027)
- `PLATFORM_CONTRACTEN.md` is nu `contracts 1.3`: alle 36 contractgroepen uit de inventaris verwerkt, met een
  wijzigingslog 1.2 → 1.3 bovenaan (één punt per groep) en de keuzes bij het vaststellen (K1–K9). Onder meer: Emby als
  bestaande mediaserver en de HARDE EIS (kijkgeschiedenis en MediaGuard-voortgang), MediaGuard volgt twee servers
  (`servers[]` naast de bestaande velden), gereserveerde MediaGuard-acties tot BG-05, Jelly Leon-conventies en JL4,
  model-apps, healthcheck als 568 en bounding set, strengere herkomst- en `Host`-regels voor statuspagina's,
  onleesbaar koppelbestand fail-closed, vingerafdruk over alle policy-sleutels (testvector `HN69-2PHK-XV2D-X85W`),
  scopes dienst → Hub, heartbeat en log-sink, foutcatalogus, versheid (`max_age`), eventregels en ernst, SSO-regels,
  eigenaar-connector en back-upbevestiging, manifest (`accepted_findings`, `checklist`, `post_install_checks`,
  adoptie, monitorplan), EVIDENCE-waarden `Intel-iGPU-getest (ontwikkelmachine)` en `Niet getest`, GPL-3.0.
- Nieuw `CONTRACT_1.3_CONFORMITEIT.md`: per repo (alle 11) de concrete wijzigingen met bestanden en moment (NU of
  P2/P3/P4-0/P4/P5), ID's `C1.3-<REPO>-<nn>`, gemeten tegen de code van elke repo (alleen gelezen).
- Nieuwe test `apps/api/tests/unit/test_contract_13.py`: kop, wijzigingslog en conformiteitslijst dekken elke groep,
  geen relatieve links (kopieën), een hoofdstuk per repo, unieke ID's met geldig moment, testvectoren onafhankelijk
  nagerekend, nieuwe validatiewaarden in §11.
- De inventaris, README, `docs/platform-v2/README.md` en `OVERDRACHT/STATUS.md` (met de gebouwde client-ID's en hun
  bron) wijzen naar 1.3. De code van de Hub volgt nog 1.2; wat hier nog moet, staat in hoofdstuk 1 van de lijst.

### Toegevoegd — inventaris voor contract 1.3 (`docs/platform-v2/CONTRACT_1.3_KANDIDATEN.md`)
- Alle 151 contractmeldingen uit ronde 2, de contractpunten uit de ADR's en EVIDENCE van alle repos sinds 1.2, de
  B03-delta's (hoofdstuk 18, ADR-0016…0020), de besluiten van de gebruiker (Emby, MediaGuard volgt twee servers,
  HARDE EIS, publiek + GPL-3.0), de P1-uitbreidingen van de Hub en de Peil-reviews: ontdubbeld in 74 groepen en
  geclassificeerd (36 contractwijziging met tekstvoorstel, 8 al opgelost, 12 repowerk, 2 afgewezen, 16 voor Peil).
- Bron byte-gelijk in `CONTRACT_1.3_MELDINGEN_RONDE2.json`; `tests/unit/test_contract_13_kandidaten.py` bewaakt dat
  elke melding precies één keer in een bestaande groep staat en dat elke contractgroep een tekstvoorstel heeft.
- Contract 1.2 blijft bindend tot 1.3 is vastgesteld; er is geen contracttekst gewijzigd.

### Gerepareerd — onafhankelijke QA-review van P1 en de contract 1.2-schermen (ADR-0026)
- **Executor koppelen in een echte browser (N-01):** de statuspagina stuurde `Referrer-Policy: no-referrer`, waardoor
  elke browser `Origin: null` meestuurde en `POST /koppelen` altijd weigerde. Nu `same-origin`; de exacte
  `Origin`-controle blijft (fail-closed). De web-E2E start de echte executor en verstuurt het formulier in Chromium.
- **Open redirect na inloggen:** `?terug=/%09/ander.domein` werd in de browser `//ander.domein` (na SSO via de
  meta-refresh, na lokaal inloggen via de router). Hub en web-UI accepteren nu alleen zichtbare ASCII zonder spatie.
- **Auditspoor:** ook `TRUNCATE` wordt geweigerd (migratie 0010, statement-trigger).
- **Gebruikers:** gelijktijdig dezelfde naam aanmaken geeft 409 `username_taken` in plaats van 500 (N-06).
- **Eerlijkheid en Peil:** de executor logt bij de start de echte koppelstatus; overlays `bg-black/50` (ONTWERPTAAL §1).

### Gewijzigd — ontwerpreview van de gebouwde Hub-UI (ADR-0025, `docs/ontwerp/PEIL_REVIEW.md`)
- **Meetgereedschap** `apps/web/review` + `make web-review`. Het meet alle schermen (beheerder, kijker, kind,
  publiek, executor-statuspagina, NAS offline en browser offline) op 320–1440 in licht en donker: axe, gerenderd
  contrast, Tab-doorloop, doelen, overloop, Peil-semantiek en woordenlijst. Draait ook in CI. Na herstel: 59
  schermen, 700 metingen, 0 harde bevindingen, axe 0 (Sim-getest).
- **Grafieken:** het querypad was bij elke weergave anders (eindeloos ophalen) en elke grafiek zei ten onrechte
  "Geen meting". Nu is het pad stabiel en werkt de grafiek volgens C-32: toetsenbord-draadkruis met voorlezen,
  eindpunt met label, gat-arcering, bronregel en kleine waarden nooit als 0.
- **Toegankelijkheid:** focusring op datumvelden; kindschil zonder focus achter de ondernavigatie; gebruikersmenu
  niet-modaal (axe); zijbalkring niet afgesneden; losse links 44 px; geen overloop op 1024; koppen zonder sprong.
- **Peil-woorden en iconen:** iconen volgens §7 (Huis = sofa), geen badge "Gemeten" bij een verse waarde, echte
  meervouden, geen ruwe Engelse statuswoorden, sessies in kindertaal op Ik, intrekken en verwijderen geen rode knop.
- **Niet gerepareerd (overgedragen):** koppelen via de executor-statuspagina mislukt in een echte browser
  (`Origin: null` door `Referrer-Policy: no-referrer`).

### Toegevoegd — fase P1 webstap: Hub-UI in Peil en de P1-schermen (ADR-0024; contract 1.2 H5/H6/H12)
- **Peil (H12):** Tailwind 4 + shadcn/ui-componenten (Button, Tabs, AlertDialog, Sheet, DropdownMenu, met de
  Peil-codemod) + lucide-react 1.66.0; tokens als versie-gepinde kopie `src/app/peil/ontwerptaal.css` (sha256-test);
  themascript zet altijd het opgeloste thema (ook bij Systeem); de P0-klassen `.btn`/`.badge`/`.tone-*`/`.notice`/`.choice`
  en `Icon.tsx` zijn weg. Productnaam **TrueNAS Home Platform** (merk, titels, PWA-manifest en -iconen).
- **Statussen in Peil:** groen alleen voor gemeten en goed; Gekoppeld/Draait/Geslaagd/Aan/Ingesteld zijn neutraal,
  open besluiten en dichte gates geen storing (slot), totaal Storing > Beperkt > Deels onbekend > Alles gezond.
- **O-03:** bij een fout blijft de laatst bekende waarde staan, gedempt ("Laatst bekend · 10:12") met status Onbekend /
  Verouderd — nooit gewist, nooit als actueel (vervangt ADR-0009 punt 3).
- **Nieuwe schermen:** Apps-catalogus (filter met aantallen, slechtste status eerst) en appdetail met tabs in de URL
  (Status · Metrieken · Logs · Versies · Acties; acties `aria-disabled` "Volgt in fase P2", geen RisicoBadge);
  Problemen-inbox (master-detail ≥ 1280) en incidentdetail (hypothese als woord, Toon bewijs, Onderzoek, alleen-lezen
  herstelvoorstel, erkennen/uitstellen/oplossen met `nog_actief`, veilige modus, supportbundel, tijdlijn); Server →
  Metrieken (nu-tegels, CPU-grafiek, GPU's als small multiples met temperatuur altijd Onbekend, opslagmeters, netwerk),
  Meetdekking en Logs; Home met P1-bronnen (catalogus, incidenten, monitoring, meldingen, gates).
- **Instellingen** als index + subpagina's: Account (thema, wachtwoord, sessies), Gebruikers en toegang (rollen incl.
  kind, alle sessies, SSO met gate D17, issuercontrole en testlogin), **Noodaccount (H6)** (instellen/vernieuwen met TOTP
  één keer tonen + bevestigen, zelftest met bron-IP), **Diensten (H5)** (vingerafdruk + publieke sleutelset, koppelcode
  met aftellen of enrollment-token met `HUB_URL`/`HUB_ENROLLMENT_TOKEN`/`HUB_KEY_FINGERPRINT`, register, rotatie,
  ontkoppelen met eerlijke fout, intrekken met getypte app-id), Monitoring en meldingen (bronnen met "Opslaan en testen",
  alertregels, Gotify-testmelding, out-of-band, meldingenlogboek), Apparaat, Auditspoor (ketting controleren) en Over.
- **Noodlogin-pagina** `/inloggen/nood`, SSO-knop en `sso_fout`-meldingen op `/inloggen`; **kindschil** Home · Kijken ·
  Zoeken · Ik met kindvriendelijke 403; onboarding-stap executor met koppelcode (30 min).
- **Executor-statuspagina** in het Peil-sjabloon (C-55, versie-gepinde kopie + driftest), velden per contract 1.2,
  veldfouten met skiplink; "Gekoppeld" neutraal. TOTP-issuer van het noodaccount is nu "TrueNAS Home Platform".
- **Tests:** vitest (Peil-statussen, Home-afleiding, componenten, tokenkopie, 401-afhandeling); Playwright tegen de
  echte API met simulators (TrueNAS, Uptime Kuma, Beszel, Gotify, OIDC-issuer, simulator-dienst): alle schermen op
  360/390/768/1440 in licht én donker met axe, plus P1-gedrag (catalogus, bronnen, diensten, 100 events → één incident,
  noodaccount, SSO-testlogin, kind, intrekken). Schermafdrukken in `docs/screenshots/p1/`.

### Toegevoegd — fase P1 deel 2 (backend): incidenten, logs, runbooks, out-of-band, SSO en auditketting (ADR-0022/0023)
- **Incidenten-inbox (B01-005):** `/api/v1/incidents…` met inbox per prioriteit, samenvatting en groepen per oorzaak,
  detail (ETag), gebeurtenissen, bewijs, erkennen (met verval), snoozen (kritiek ≤ 24 uur), oplossen alleen als de
  readback het niet tegenspreekt (`409 nog_actief`), notities en een geschoonde supportbundel. Dedupe en correlatie per
  vingerafdruk (100 identieke crashes → één incident), herstel sluit alleen het eigen incident en nooit met een ouder
  herstel, heropenen binnen een uur, escalatie, één melding per opening en een hersteldmelding; alert-incidenten melden
  niet dubbel. Hypothese met zekerheid en bewijs of "Ik weet het niet". Nieuwe outbox-events
  `alert.instance.fired|resolved`, `notification.channel.failed|recovered` en `audit.chain.broken`; SSO-events van
  home-control-hub (ADR-0009 daar) worden incidenten.
- **Log-index (B09-004):** `POST /api/v1/logs` (diensten), `GET /api/v1/logs` en `/logs/bronnen` (operator); eigen
  WARNING-logs met `trace_id`; schonen vóór opslag (geheimen, tokens, JWT, PEM, hex/base64, e-mail, IP-adressen en de
  exacte waarde van vault-geheimen en Hub-tokens), grenzen, rate-limit en retentie.
- **Out-of-band (B09-005, EX22/EX23):** `GET /api/v1/monitoring/out-of-band` en `…/bevestiging`; de Hub zit niet in het
  meldpad van Uptime Kuma en noemt volledige NAS-uitval nooit "gedekt".
- **Runbooks (B09-006):** acht getypeerde runbooks (`/api/v1/runbooks`, `docs/RUNBOOKS.md` gegenereerd met drift-check),
  "Onderzoek", "Herstel voorstellen" (alleen een `ActionProposal`, niet uitvoerbaar tot P2) en de veilige modus na
  herhaald falen (geen eindeloze herstarts).
- **SSO-login (B01-006):** OIDC Authorization Code + PKCE tegen een instelbare issuer (Authentik), groep→rol (kind wint),
  testlogin + gate D17 vóór inschakelen, "OIDC verplicht" alleen met werkend noodaccount, sessie-intrekking (admin,
  uitzetten, `sso.access.revoked`, rolwijziging), `/api/v1/sessions` en het advies `GET /api/v1/sso/status` (nooit
  groen). De bestaande noodlogin is hergebruikt en blijft werken als de issuer uitvalt.
- **Auditspoor:** append-only met hash-ketting (`ketting_nr`, `prev_hash`, `hash`), trigger tegen wijzigen/verwijderen,
  `GET /api/v1/audit/verify`, anker in `/appdata/audit/anker.jsonl`, dagelijkse controle.
- Migraties 0006–0009 (0009: partiële index voor het verzegelen; verzegelen kiest de rijen in de database, ook na een
  teruggedraaid savepoint); worker-taken `incidenten_bijwerken`, `logs_onderhoud`, `audit_verankeren`, `audit_controleren`;
  OpenAPI, `.env.example`, `docs/INCIDENTEN.md`, `docs/SSO.md`; de rooktest controleert de nieuwe routes en het anker.
- Tests: unit (regels, schoning, runbooks, OIDC, audit), integratie (auditketting incl. manipulatie en gelijktijdige
  schrijvers) en dienst-E2E met fakes (OIDC in de vorm van Authentik, home-control-hub, Uptime Kuma, Gotify, TrueNAS).

### Toegevoegd — fase P1 deel 1 (backend): catalogus, monitoring, alerts en meldingen (ADR-0021)
- **Appcatalogus (B01-002):** `GET /api/v1/apps` (zoeken/filteren op status, adaptertype, soort), `GET /api/v1/apps/{id}`
  (ETag, acties per rol) en `POST /api/v1/apps/discover`. Identiteit = TrueNAS-app-id (stabiel over een NAS-herstart);
  idempotente discovery alleen uit een verse inventaris, nooit verwijderen (`aanwezig=false` + `verdwenen_sinds`);
  installatiewijze (`ix-app` = standaard Custom App, `custom_app: true` = compose/YAML, anders catalogusapp);
  image/tag/digest met readback via `app.image.query` en geschiedenis; opslag → dataset; deep-link uit D03 + poort;
  resourcegrenzen eerlijk `unknown` (app-configuratie wordt nooit gelezen); appstore-koppeling via het
  dienstenregister en een dienst-JWT, anders `unknown`.
- **Gezondheidsmodel (B09-002):** componenten TrueNAS-staat, buitenkant (Uptime Kuma) en binnenkant (heartbeat,
  connector-health, worker van de Hub); verouderd = `unknown`; `RUNNING` alleen is nooit gezond; apps met eigen taken pas
  gezond met een verse binnenkant (MediaGuard/MSO/my_house: binnenkant volgt in P3 → `unknown`).
- **Bronnen (B09-002):** `/api/v1/monitoring/sources` (Uptime Kuma: `/metrics` met API-key en/of statuspagina,
  versie-detectie, automatische en handmatige koppeling; Beszel: readonly-gebruiker, alleen het NAS-systeem, mini-pc
  uitgesloten), `/poll`, `/health`, `/status` en de dienstroute `POST /api/v1/monitoring/heartbeat` (Hub-uitbreiding).
  Connector-health (§6) van eigen diensten met dienst-JWT en grace. Ingetrokken key → direct `unknown` + event (EX16).
- **Tijdreeksen en alerts (B09-003):** reeksen in de eigen PostgreSQL met grenzen, aggregatie ruw → 5 min → 1 uur en
  retentie per reeks (`/api/v1/metrics/series`, `/query`); alertregels met drempel, duur en hysterese, standaardregels,
  dempen per alert en per regel (`/api/v1/alerts…`); verouderde data geeft geen overgang.
- **Meldingen (Gotify, `notification.send` R0):** kanalen met applicatietoken in de vault, echte testmelding,
  rate-limit per kanaal met één samenvatting, stille uren (kritiek altijd), backoff + dead-letter, token geweigerd →
  kanaal stil tot vervanging (`/api/v1/notifications…`).
- **Observability (B01-004) en meetdekking (B09-001):** `GET /api/v1/observability/nas` (live CPU/geheugen/ARC/
  schijven/netwerk uit `reporting.realtime`, GPU's op PCI-slot, bron + `observed_at`, verouderd → `unknown`) en
  `GET /api/v1/monitoring/coverage` (kan leveren volgens de broncode vs. levert nu, hiaten met alternatief).
- Migraties 0003–0005; periodieke worker-taken (`periodic_task`); `.env.example`, OpenAPI, `docs/MONITORING.md`;
  rooktest controleert ook de nieuwe routes en taken in de image.
- Tests: unit, integratie en dienst-E2E met fakes (TrueNAS met `reporting.realtime`, Uptime Kuma, Beszel, Gotify,
  appstore, eigen dienst). Prometheus-achtige testbelasting: 200 reeksen met 60 000 metingen → 10 berichten en één
  samenvatting (de commitboodschap noemde abusievelijk 72 000).

### Gerepareerd — herkenning van apps
- De executor werd als Hub herkend en `jelly-leon-platform` als `jelly-leon` (eerste voorvoegsel won); nu wint een
  exacte naam en anders het langste voorvoegsel. Eigen nieuwe diensten worden herkend.
- **B03 2.0 (goedgekeurd) en Excel-bijwerker (Δ-ASM-EXCEL):**
  - `tools/excel/update_excel.py` voegt werkpakketrijen (`--werkpakketten`, `tasks.json`-formaat; bestaand ID = inhoud
    vervangen met behoud van status en bewijs), testrijen (`--testen`/`--testmeta`, `e2e_cases`-formaat) en faserijen
    (`--fasen`, P4-0 na P3) toe; tabelbereiken, dropdowns, voorwaardelijke opmaak, samengevoegde cellen en formules op
    Dashboard/Appoverzicht lopen mee; formuleresultaten worden herberekend; ongewijzigde onderdelen blijven byte-gelijk;
    idempotent; weigert Gereed/Geslaagd. `JLT-…` gaat naar de Testmatrix, `P4-0` naar Fasen. Pytest (klein test-werkboek
    + de echte Excel in een tijdelijke kopie) in de nieuwe CI-job `excel`.
  - `02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` versie 2.0 met de HARDE EIS van de gebruiker (kijkgeschiedenis en
    MediaGuard-voortgang altijd beschikbaar) en de overname vanuit **Emby** (B03-015, JLT-70…74, P0, golf 0; controlelijst
    "Emby verwijderen"); `B03_FASERING.md`, `B03_BESLUITEN.md`; fase P4-0 en nieuwe gates in `06_FASERING_EN_GATES.md` en
    `OVERDRACHT_PROMPT.md` §4; ADR-0016…0020.
  - Brondata: `08_EXCEL/tasks.json`, `e2e_cases.json`, `EXCEL_TAKEN.json` en `08_EXCEL/b03/`; Excel bijgewerkt
    (66 nieuwe en 6 vervangen B03-rijen, JLT-01…74, rij P4-0, bewijs samengevoegd).
  - Onafhankelijke controle: de HARDE EIS staat nu ook letterlijk vooraan in de **acceptatie** van B03-015 (akkoord van
    de gebruiker op elk verschil, ook door upstream-migraties; de bestaande installatie blijft ongewijzigd als terugval;
    de overname raakt de MediaGuard-database niet en elke MediaGuard-release bewijst een upgrade op een gevulde database
    van de vorige versie) — in het bouwplan, `tasks.json`, `EXCEL_TAKEN.json`, `08_EXCEL/b03/` en de Excel (alleen die
    cel). `B03_BESLUITEN.md`: in het overzicht staat bij BG-38 dat het besluit afwijkt van het advies.
- Ontwerptaal **Peil** 1.1.0 als bron van waarheid: `docs/platform-v2/ONTWERPTAAL.md` + `design/ontwerptaal/` (tokens, CSS voor Tailwind 4 + shadcn/ui, statuspagina-sjabloon, aliaslagen, prototypes, schermafdrukken, contrast- en axe-controle) en ADR-0015 (vervangt ADR-0009 punt 1 deels).

### Gerepareerd — onafhankelijke review van contract 1.2 in Hub en executor (ADR-0014)
- **1 MiB vóór routering en aanmelding (§5):** Hub en executor lezen de body nu vóór alles, met hooguit 1 MiB in het
  geheugen. Een chunked verzoek van meer dan 1 MiB geeft altijd `413` met `details.max_bytes`; vroeger gaf de Hub dan
  401/405 op routes zonder body, en de executor kende helemaal geen grens voor chunked verzoeken.
- **Executor, `unlink` (§4.6, §3.8, §4.2):**
  - Een persistente `jti`-replaycache (`/appdata/executor.sqlite3`): een hergebruikte `jti` geeft `401 token_replayed`,
    ook na een herstart. Een exacte herhaling krijgt het opgeslagen antwoord. Is de cache onbruikbaar, dan `503`.
  - `Idempotency-Key` is verplicht en een gebruikers-JWT moet de rol `admin` hebben.
  - De rol `kind` wint nu altijd.
  - Een JWT met een `iat` in de toekomst wordt geweigerd.
- **CI:** de controle "na een downgrade is de database niet actueel" faalde nooit (`!` zet `errexit` uit). Dat is
  gerepareerd.
- **Webpoort (Node-doorgang):** een chunked upload van meer dan 1 MiB werd vaak `502` ("Hub-API niet bereikbaar")
  in plaats van `413`. De doorgang telt nu zelf en antwoordt met dezelfde 413-body als de API.
- **Rooktest:** controleert nu ook chunked verzoeken van meer dan 1 MiB (tot 3 MB, herhaald), zowel naar de Hub via
  de webpoort als naar de executor.

### Gewijzigd — contract 1.2 toegepast in de Hub en de executor (ADR-0013)
- **Enrollment (H1/H2):** `POST /api/v1/services/enroll` volgt §3.3 exact (strikte JWK, token- en koppelcodeformaat,
  `version`/`base_url`/`public_key_jwk` verplicht); antwoord met `schema_version`, `keyset_fingerprint`,
  `key_rotation_url` en `enrollment_replayed`; toegestane herhaling na een herstart halverwege; nieuw
  `GET /api/v1/services/self`; executor alleen met een koppelcode van 30 min; exacte `Retry-After` bij 429.
- **Rotatie (H3):** oud token vervalt 10 min na het eerste gebruik van het nieuwe (hooguit 24 uur);
  `Hub-Token-Rotation: required`; `POST /services/{id}/rotate` vraagt alleen aan (`202`, `Idempotency-Key`, geen token);
  na 180 dagen alleen een melding.
- **JWT's (H4):** `token_use: "user"` in gebruikers-JWT's; dienst-JWT `token_use: "hub_service"` voor Hub → dienst;
  `GET /api/v1/auth/key-rotations` (lege lijst) en `GET /api/v1/auth/keyset`.
- **Koppelbeheer (H5-backend, H14):** `POST /services/{id}/unlink` (via de dienst, daarna intrekken) en
  `PUT /services/{id}/truenas-app` (gemeten appnaam bevestigen). Het UI-scherm "Diensten" wacht op de ontwerpstap (§13).
- **Noodlogin (H6-backend):** `/api/v1/auth/break-glass` (status, setup, rotate, confirm, login, selftest) met TOTP,
  privé-bereiken, sessie ≤ 60 min, event `auth.break_glass.used` en rotatieplicht. UI wacht op de ontwerpstap.
- **Executor (H7, deel):** koppelen op de statuspagina met koppelcode + vingerafdruk, pinning in `hub-link.json`,
  controle van inkomende Hub-JWT's (`GET /connector/v1/hub-link`); ontkoppelen geeft eerlijk `501` tot P2.
- **Manifesten (H8)** zonder `joins_platform_network`/`custom_app.ports`; **Custom App-instructies (H9)** met tag
  `<versie>@sha256:<digest>`, publieke image en registry-login als terugval.
- Migratie `0002`; OpenAPI bijgewerkt; rooktest controleert ook het enroll-schema, de lege sleutelrotaties en de
  executor-weigering zonder koppeling.

### Gewijzigd — onafhankelijke review van contract 1.2
- `docs/platform-v2/PLATFORM_CONTRACTEN.md` blijft `contracts 1.2`, met correcties R1–R12 (zie
  `docs/adr/ADR-0012-review-contract-1-2.md`): `app_id` vast per image; `pending` naast `state` in `hub-link.json`;
  strikte JWK-regels in het enroll-verzoek; rotatie van service-tokens zonder buitensluiten en alleen op verzoek van
  een beheerder; intrekking pas na `services/self`; sleutelrotatie per doel en zonder authenticatie; vaste
  `reason`-tabel; koppelbeheer is geen `action_id`; TrueNAS-uitspraken als bronwaarneming (NIET GEVALIDEERD); ook
  PID 1 niet als root; executor-bewijs tegen het vastgelegde NAS-adres.
- `docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md` bijgewerkt naar de echte stand per repo (gecontroleerde commits),
  met nieuwe punten A7, AS8, JP12, H14 en root-PID 1 (A6).
- `deploy/smoke.sh`: controleert nu voor elk proces in Hub en executor ook `CapEff 0000000000000000` (naast
  `NoNewPrivs 1`), zoals contract §2.2 vraagt.
- `docs/platform-v2/EVIDENCE.json`: `validatie` van D01–D18 alleen nog met waarden uit de vaste lijst van §11
  (toelichting naar `opmerking`); nieuwe test `apps/api/tests/unit/test_evidence_contract.py` bewaakt dat.

### Gewijzigd — platformcontract 1.2 (alleen documentatie)
- `docs/platform-v2/PLATFORM_CONTRACTEN.md` naar `contracts 1.2` met wijzigingslog: exact enroll-schema, dienst-JWT
  voor Hub → dienst, sleutelpinning met sleutelset-vingerafdruk, `jti`-replaycache, opslag in
  `/appdata/secrets/hub-link.json`, koppelen via de statuspagina alleen vóór de eerste koppeling, Custom App-realiteit,
  manifestwijzigingen, noodlogin in de Hub, besluiten van de gebruiker en nieuw §13 Ontwerptaal.
- Nieuw: `docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md` (wat elke repo moet veranderen) en
  `docs/adr/ADR-0011-contract-1-2.md` (keuzes). De code van de Hub volgt in een volgende stap (H1–H13).
- `apps/api/src/hub/keys.py`: referentie-implementatie van de RFC 7638-thumbprint en de sleutelset-vingerafdruk
  (contract 1.2 §4.5) met de testvectoren uit het contract (`apps/api/tests/unit/test_keyset_fingerprint.py`); nog
  niet gebruikt in het enroll-antwoord.

### Gerepareerd — tests
- `tests/e2e/test_wizard_inventory.py`: de controle op een klare-tekstsleutel in de vault faalde willekeurig als de
  AES-GCM-cijfertekst een 0x00-byte bevatte (`convert_from(…, 'LATIN1')`); nu een bytevergelijking.

### Toegevoegd — web-UI (`apps/web`)
- Next.js 16-PWA (App Router, TypeScript, Nederlands, licht/donker, toetsenbord/screenreader, aanraakdoelen ≥ 44 px):
  eerste start met setupcode, inloggen/uitloggen, onboarding-wizard D01–D18 (uitleg, gate, status, schemaformulier
  zonder voorbeeldwaarden, meten, bewijs), TrueNAS-koppeling (NAS-adres, alleen-lezen-key, verbindingstest,
  vingerafdruk bevestigen), uitleg executor, Server-inventaris, Apps, Backups-dekking, Home-kaarten met bron en
  "laatst bijgewerkt", Instellingen (wachtwoord, sessies, thema, gebruikers, auditspoor, PWA-status).
- Navigatie volgens 08_UI (ondernavigatie < 1024 px, zijbalk ≥ 1024 px); latere fasen eerlijk "nog niet beschikbaar".
- Eigen webserver (`server/hub-server.mjs`) met strikte API-doorgang en echte client-IP (vervalste
  `X-Forwarded-For` genegeerd); service worker alleen voor de app-schil, nooit voor API-gegevens.
- Alles-in-één image: web-stage (Node 22 op digest), web op 30400, API alleen op 127.0.0.1:8400; healthcheck en
  rooktest controleren beide. Makefile-doelen `web-*`, CI-job `web` (eslint, tsc, vitest, npm audit, next build,
  Playwright 360/390/768/1440 met axe).
- Teststack `tests/e2e/web_stack.py` (echte API + worker + fake TrueNAS) en schermafbeeldingen in `docs/screenshots/p0`.

### Gerepareerd
- `Makefile`: de optionele BuildKit-secret `ca_bundle` werd door een komma in `$(if …)` zonder `src=` doorgegeven.

### Gerepareerd — onafhankelijke review P0 (ADR-0010)
- Setupcode: twee gelijktijdige verzoeken met dezelfde geldige code konden twee beheerders opleveren; nu een
  advisory lock + hercontrole. Ontbrekende `setup-completed`-markering naast een bestaande beheerder wordt hersteld.
- 1 MiB-grens per verzoek gold alleen bij een `Content-Length`-header; nu ook voor chunked verzoeken (413).
- `POST /api/v1/auth/password` had geen rate-limit op het huidige wachtwoord.
- Images zetten zelf `no-new-privileges` (prctl) na de gebruikerswissel; rooktest controleert dat per proces.
- Rooktest (ook CI) controleert nu herstart en harde kill zonder dataverlies (beheerder, geen nieuwe setupcode,
  executor-identiteit).
- Nieuwe rechtenmatrix-test over alle routes; integratiefixture faalt in CI zonder PostgreSQL i.p.v. over te slaan.

### Toegevoegd — backend
- Hub-API (`hub`): FastAPI + SQLAlchemy 2 + Alembic + pydantic-settings; processen `api`, `worker`, `ai-runner`
  (stub, aparte gebruiker 569 zonder toegang tot geheimen), `init`, `migrate`, `backup-now`, `export-openapi`.
- First-start-init: ontbrekende geheimen in `/appdata/secrets` (0600, nooit overschrijven; Ed25519 voor identiteit,
  JWT en policy; `vault.key`), eenmalige setupcode in de app-log.
- Aanmelden: setupcode → eerste admin; login/logout (argon2id, rate-limit), sessies met CSRF, rollen
  admin/operator/viewer/kind, sessies intrekken, JWKS en dienst-JWT (EdDSA, exp ≤ 120 s).
- Enrollment: eenmalige enrollment-tokens (60 min) en koppelcodes, service-tokens (alleen hashes), rotatie met
  overgangstijd, intrekken.
- Onboarding-wizard-API voor D01–D18 met getypte waarden, bewijs, metingen via TrueNAS-readback en `GET /api/v1/gates`.
- Alleen-lezen TrueNAS JSON-RPC-adapter (wss, TLS-verificatie of bevestigde vingerafdruk, capability-map per versie,
  reason codes), inventaris met `observed_at`/veroudering, dienstenregister.
- Back-up en herstel: dekking per app/dataset, snapshotbeleid als voorstel, geverifieerde pg_dump van de eigen database,
  hersteltests als bewijsrecord.
- Events-inbox met dedupe, connectorcontract van de Hub, OpenAPI-export.
- Executor (P0): statuspagina "nog niet gekoppeld", allowlist die alles weigert.
- Alles-in-één Hub-image en executor-image (supervisor als PID 1, na de init geen root-proces), Custom App-formulieren,
  manifesten, CI (lint, types, tests met PostgreSQL, migraties, OpenAPI-drift, pip-audit, images + rooktest) en
  release-workflow (GHCR, SBOM, digests).

### Validatie
Sim-getest en tegen een echte PostgreSQL 16 getest; images gebouwd en gestart in Docker; web-UI met Playwright tegen de
echte API en tegen de image (fake TrueNAS). **NIET GEVALIDEERD op een echte NAS, Android-telefoon of tv/speler.**
