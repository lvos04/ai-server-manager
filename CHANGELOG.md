# Changelog

Alle noemenswaardige wijzigingen. Versies volgen `VERSION`; images krijgen exact deze tag (nooit `latest`).

## [0.1.0] — 2026-11-09 (fase P0, backend en web-UI; niet uitgebracht)

### Toegevoegd — Acties via de eigenaar-connector (S-P2-080)

- `sso.sessions.revoke` en `sso.oidc.hub.register` lopen nu als ondertekend `ExecutionRequest` naar
  `POST /connector/v1/apply` van home-control-hub. De Hub vraagt eerst `POST /connector/v1/propose` bij de eigenaar;
  diens `preview_hash` en `resource_etag` binden de goedkeuring. Een ontbrekende route bij de eigenaar geeft
  `501 capability_unavailable`; een antwoord zonder volledig bewijs telt nooit als uitgevoerd.
- `sso.oidc.hub.register` vraagt een back-up. Zonder B12-bewijs van de Authentik-database blijft het geblokkeerd
  (`backup_checkpoint_ontbreekt`). De AI kan geen van beide voorstellen; `mediaguard.*` blijft gereserveerd.
- Fake eigenaar `tests/fakes/fake_eigenaar.py` en E2E `tests/e2e/test_eigenaar_acties.py`. Die toetst ook dat de
  eigenaar een verzoek met een ongeldige of ontbrekende handtekening weigert. Sim-getest; NIET GEVALIDEERD (echte
  NAS); de echte proef volgt in S-P2-340.

### Toegevoegd — Geheimen van catalogusapps via de vault (S-P2-070)

- De preview van een installatie toont per kluisverwijzing `{"verwijzing": "vault://app/<app_id>/<parameter>",
  "waarde": "geheim, niet getoond"}`; de waarde vult pas de executor in (contract 1.3 §8.3).
- Een niet-bestaand kluispad weigert vóór ondertekening: een verwijzing buiten de regel geeft geen voorstel, en een
  gebonden revisie die bij het uitvoeren niet (meer) als die verwijzing van die instantie bestaat geeft
  `409 kluiswaarde_ontbreekt` zonder ondertekend verzoek, afgifte of schrijfaanroep.
- De lekzoektocht na een volledige installatie-run loopt nu ook over de preview, het antwoord van elke route van Hub
  en executor en de hexvorm in binaire kolommen. De tegenproef zet de versleuteling van de app-opslag uit en maakt de
  zoektocht rood (V-003); zonder de hexvorm bleef die zoektocht groen. Sim-getest; NIET GEVALIDEERD (echte NAS).

### Toegevoegd — Dynamische blokkades en gates: pool, back-up, boiler (S-P2-060)

- Een eigen back-up die te oud wordt voor de back-upgate geeft nu een kritiek incident `backup.verouderd` (event
  `backup.freshness.stale`, de worker-taak `incidenten_bijwerken`). Het incident sluit zodra er weer een verse,
  geverifieerde export is (`backup.freshness.recovered`). De grens is dezelfde als die van de gate, dus R2/R3 blijft
  dicht met `backup_gate_rood` (EX12).
- Nieuwe negatieve tests: per gate (`r2_r3_acties`, `data_mutatie`, `deployment`, `bestaande_app_updates`) een
  goedgekeurde actie die bij een dichte gate niet wordt ondertekend. Een beheerder kan een gate niet wegklikken.
  Elke opslagmutatie loopt via de poolgate (EX11). De boiler wordt geweigerd voor elke soort actor (EX27).
  Sim-geslaagd; NIET GEVALIDEERD (echte NAS, hardware).

### Toegevoegd — Volledige keten appstore → planner → Hub → executor (S-P2-050g, deel G)

- `tests/interop/test_keten_echt.py` en de CI-job `keten` draaien de gepinde appstore-en-fork en jelly-leon-platform,
  elk met een eigen database en koppeling, met de echte Hub en executor tegen de nagebootste TrueNAS. De keten
  installeert, werkt bij met een geverifieerd checkpoint, zet terug en verwijdert. Daarnaast de negatieve rijen en
  negen mutatieproeven. Sim-getest; NIET GEVALIDEERD (echte NAS).
- Hersteld: de Hub weigerde elke vertrouwde Custom App-installatie, omdat de vertaling altijd `command: []` en
  `entrypoint: []` zet. Precies de lege lijst telt nu niet als eigen opdracht.
- Een planner die zonder stap blokkeert, geeft `409 plan_geblokkeerd` met zijn vaste codes (bijvoorbeeld
  `version_unavailable`).

### Toegevoegd — Geverifieerde app-checkpoints en pre-update-gate (S-P2-050f, deel F)

- Een geslaagde, teruggelezen `zfs.snapshot.create` is een checkpoint: de executor legt dataset, snapshot,
  `createtxg` en recursief vast in zijn journaal. De Hub kiest bij `app.update`/`app.rollback` zelf zijn eigen
  snapshotverzoek van het laatste uur, van na de laatste wijziging van de app, dat de opslag uit de inventaris
  dekt; anders `backup_checkpoint_ontbreekt` met de reden. De executor controleert vóór de schrijfaanroep opnieuw:
  `checkpoint_ontbreekt`, `checkpoint_verlopen`, `checkpoint_afwijkend` (snapshot weg of andere `createtxg`) of
  `checkpoint_dekt_niet` (dekking uit `app.config`). Fail-closed; geen nieuwe externe dienst.
- EX15 met optie 3 (ADR-0032 besluit 8): `app.update` kent het optionele veld `upgrade` (`migrations`,
  `tag_only_rollback_safe`). De executor legt bij elke bijwerking en terugzetting de herkomst verzegeld vast
  (`buiten_keten`) en bij de eerste start eenmalig de bestaande recepten als `oud`. Na een gemelde migratie weigeren
  Hub en executor terugzetten op alleen de image (`database_herstel_vereist`); een herstelpunt zonder eigen herkomst
  geeft `herkomst_onbekend`. Sim-getest tegen contractconforme fakes; NIET GEVALIDEERD (echte NAS).
- Herstelronde (harde eis appgegevens): de dekking telt ook de schrijfbare koppelingen van de draaiende werklast en
  aangekoppelde kinddatasets; zonder positief bewijs van opslag geen dekking. Een recursief checkpoint telt alleen de
  per dataset teruggelezen leden met dezelfde `createtxg`, gebonden aan de eigen voltooide snapshotactie. De
  executor controleert vlak vóór de schrijfaanroep nogmaals (`doel_gewijzigd` of de bestaande codes). Terugzetten
  vraagt ook dekking van de opslag waar het recept naar schrijft. EX15 geldt ook voor `app.update` terug naar een
  image of catalogusversie van vóór een gemelde migratie. Een anker per app in de geheimenmap ziet een teruggezet
  ouder journaal (`herkomst_onbekend`).

### Vastgelegd — Afzonderlijke geheime overdracht (S-P2-050e, M2)

- Platformcontract 1.3 §8.3 legt de overdracht van appgeheimen en het enrollment-token vast. Het ondertekende
  verzoek bevat alleen verwijzingen. De executor haalt de waarden na zijn eigen controles eenmalig bij de Hub op,
  versleuteld (HPKE) en ondertekend met de bij het koppelen gepinde sleutels. De executor vult `HUB_*` in, niet de
  vertaling (§3.2). Een instantie met ingevulde plekken krijgt geen bijwerking of terugzetting via `app.config` tot
  het recept met alleen verwijzingen bestaat. ADR-0032 legt M2 vast.
- Correctie bij de bouw van 050e: de HPKE-afgifte bindt `claim_sha256` in de info (`asm-kluis-afgifte-v1:` plus de
  hash), omdat de enkelvoudige HPKE-API geen aad kent; een appgeheim dat met `-` of `_` begint, maakt de Hub opnieuw
  (dat volgt al uit de vorm).

### Toegevoegd — Catalogusinstallatie via een eigen plannerplan (S-P2-050d, deel D)

- De Hub verifieert het catalogusbewijs zelf bij de appstore (handtekening, manifesthash, Git-pin, uitgever) en
  maakt het installatieplan zelf bij de planner met `catalog_request_sha256` (contract 1.3 §8.1/§8.2). Nieuwe
  routes onder `/api/v1/catalog/plans`; migratie 0022 voegt `catalog_plan` toe.
- Hub en executor toetsen `catalog_binding` aan de witte lijst in `policy/catalogus.yaml`; de executor eist na
  installatie een passende digest uit `app.image.query`. De productielijst blijft leeg, dus er wordt nog niets
  vrijgegeven. Sim-getest tegen contractconforme fakes; NIET GEVALIDEERD (echte NAS).

### Vastgelegd — Bron en doel van uitvoerbare appplannen (S-P2-050d)

- Platformcontract 1.3 §8.1 bindt catalogusitem, versie, manifesthash, Git-pin en uitgeversbewijs aan één
  doelinstantie. §8.2 bindt de geverifieerde plannerinvoer aan de bestaande Hub-dienst-JWT en het eigen plan.
  ADR-0032 wijst de aanvullingen toe aan appstore, planner, Hub en executor. Uitvoering blijft gesloten tot de
  vereiste controles zijn gebouwd en beproefd.

### Aangescherpt — Installatiebeleid en preview (S-P2-050c)
- De Hub en executor toetsen installatiewaarden met de gepinde C-12-eigenaarsregels. Aanmeldgegevens worden
  geweigerd, ook als kluisverwijzing. Variant B vereist voor een kluisverwijzing in een omgevingsvariabele van
  de standaard Custom App een toegestane geheimnaam. Het invullen uit de kluis blijft gesloten.
- Installatiewaarden die host-netwerk of `privileged` inschakelen worden geweigerd. NFS en SMB blijven dicht.
  De witte lijst voor catalogusinstallaties is leeg. `policy/catalogus.yaml` legt de validatorpin voor beide
  images en manifest-CI vast.
- Previews maskeren padvormige geheimen, geheime UUID- en hex-sleutels, omgevingswaarden en geheimen in URL-query's
  en webhookvelden. Expliciete padvelden en getypte openbare waarden blijven zichtbaar.

### Vastgelegd — Leesadapters voor bestaande apps (S-P3-010)
- [ADR-0034](docs/adr/ADR-0034-adapters-bestaande-apps.md) legt voor MediaGuard, MSO en my_house de
  leesroutes, veldselectie, kluiskoppeling en versheid vast. MediaGuard-leesroutes met bijwerkingen
  blijven uitgesloten. De connectorovergang bewaakt bronvolledigheid, vergelijkbare meetwaarden en
  paginering per momentopname. MSO vereist vooraf bewijs van uitsluitend leesrechten en behoudt de
  specifieke authenticatiefout bij de overgang. Het energiedomein van home-control-hub leest als
  enige de energiecijfers van my_house en levert ze aan B01-011.

### Gerepareerd — Hub: lokale aanmelding bij ontbrekende nood-TOTP (KLEIN-110)
- Bij een ontbrekende of onleesbare nood-TOTP-kluisrij meldt de Hub dat het noodaccount niet werkt. "OIDC verplicht"
  geldt tijdelijk niet, zodat bestaande lokale beheerders kunnen inloggen. SSO blijft beschikbaar met een leesbaar
  clientgeheim. De openbare SSO-status en het inlogscherm verwijzen bij die terugval naar Instellingen → Noodaccount
  om het wachtwoord en de TOTP te vernieuwen. De eerste start die de kluisfout aantreft voegt één auditregel toe met
  een vaste redencode.
- Verplichte OIDC vereist ook een gewone lokale beheerder. Gebruikersbeheer beschermt de laatste gewone lokale
  beheerder zolang verplichting is ingesteld. Bij een oudere installatie zonder gewone lokale beheerder biedt de
  Hub-console een herstelcommando voor een ontbrekende of onleesbare nood-TOTP-kluisrij. De Hub toont de beschikbare
  herstelstap en blokkeert gewone lokale aanmeldingen weer zodra de nood-TOTP is bevestigd en SSO beschikbaar is.
- Ook een onbruikbare wachtwoordhash van het noodaccount blokkeert verplichte OIDC. De zelftest noemt de oorzaak.
  Zonder gewone lokale beheerder biedt de console eenmalig herstel met audit. Een lokale aanmelding vereist een
  volledige Argon2id-verifier met een digest van 32 bytes. Oudere ondersteunde verifiers kunnen na aanmelding
  automatisch worden vernieuwd.

### Gerepareerd — Hub: OIDC-invoer, sessiegrenzen en lokale noodbediening (KLEIN-107)
- Upgradenotitie KLEIN-107: vanaf databaseversie 0012 vervallen alle bestaande OIDC-sessies. SSO zonder leesbaar
  clientgeheim is onbeschikbaar. Inloggen en de SSO-instellingen tonen de reden en lokale aanmelding blijft mogelijk,
  ook als "OIDC verplicht" is ingesteld. Richt SSO opnieuw in via een vertrouwde HTTPS-route.
- Alleen lokale beheerders en noodsessies mogen beheerdersrechten toekennen, het noodaccount wijzigen en de laatste
  vier tekens van het clientgeheim zien. SSO-beheerders kunnen gewone gebruikers en lagere rollen blijven beheren.
- Een nieuwe issuer of client-ID krijgt een eigen clientgeheim. Zonder nieuw geheim bij de wijziging verwijdert de Hub
  de oude kluisrij en zet SSO uit. Handmatige intrekking van SSO vereist een werkende lokale herstelroute.
- Schrijven/wissen van het OIDC-clientgeheim alleen via vertrouwde HTTPS door een lokale beheerder of noodsessie;
  HTTP en SSO-beheerders krijgen een vaste 403 zonder configuratie- of kluiswijziging. UI-veld alleen via HTTPS,
  zonder React-state, browseropslag of `new-password`; leeg bij verzenden, fout en verlaten.
- OIDC-sessies per verzoek gebonden aan SSO aan en de actuele configuratie (toevoegende migratie 0013);
  uitzetten, gewijzigde discovery en vervangen/wissen trekken uitsluitend OIDC-sessies in, ook bij SSO al uit.
  Lokale sessies, noodsessies, bestaand TOTP en de gedeelde kluissleutel blijven behouden.
- Zonder actief leesbaar clientgeheim geen testlogin, callback-tokenaanvraag of inschakelen; wissen verwijdert
  de oude ciphertext. OIDC-idempotentieantwoorden zonder laatste vier, inclusief oude cache-antwoorden (migratie 0014).
- De noodlogin met het nieuwe wachtwoord en een geldige nieuwe TOTP-code bevestigt een openstaande rotatie.
  Verlies van de nieuwe gegevens kan de enige noodroute onbruikbaar maken. Alleen lokale beheerders en noodsessies
  mogen noodsessies intrekken.
- Bij de eerste start vervangt de Hub oude uitleg met het algoritme uit het ID-token door de vaste foutcode in de
  SSO-configuratie en OIDC-idempotentieantwoorden. Eén auditregel telt de aangepaste velden. Historische verzegelde
  auditregels blijven intact, inclusief de tekst die daarin al stond.
- CGNAT-beheer alleen via lokale beheerder of noodsessie; setting, standaard uit en noodlogin blijven gelijk.
- O1 (herstelbestendig intrekkingsanker), O2 (geheime bodyhash in verzoek-idempotentie) en O3 (beleid uitsluitend LAN)
  blijven open. De tijdelijke overdracht blijft dicht volgens ADR-0033. Contract 1.3, policy en ADR-0033 zijn ongewijzigd.

### Gerepareerd — Contract 1.3: aanvulling C-12 na de review van de bron (S-P2-C12, deel A, A-HERSTEL; blijft `contracts 1.3`)
- §3.1, tweede uitzondering: een manifest bevat nooit een kluisverwijzing (`vault_ref_not_allowed`); alleen de Hub en,
  bij het uitvoeren, de executor vullen een kluisverwijzing in, alleen voor de `app_id` van het doel van de ondertekende
  actie, nooit voor een andere app en nooit onder een accountnaam; verzoekhash en idempotentie-opslag staan in de lijst
  van plekken zonder waarde (R-VEILIG-1).
- §9: een kluisverwijzing of geheim van de Hub onder een accountnaam is een fout, nooit een waarschuwing; de woordenlijst
  van de standaard krijgt `INIT`, `LOGIN`, `BASIC_AUTH` en de aanmeldnamen van een app (`*_INIT_PASSWORD`,
  `*_BASIC_AUTH_PASSWORD`, `JUPYTER_TOKEN`, de kale naam `PASSWORD`); bouw in appstore-en-fork (C1.3-ASF-15), opnieuw
  toetsen in de Hub (S-P2-050) (R-VEILIG-2). De 32 tekens gelden ook in de vorm `gebruiker:wachtwoord` (R-VEILIG-3).
- §11: de statusregel volgt het besluit van de gebruiker van 2026-11-11 (rest alleen de NAS-test: `Bezig`, met
  `alleen NAS-test nodig`; `Geblokkeerd` alleen als het werk niet verder kan worden gebouwd) (C12-7).
- Conformiteitslijst: nieuw C1.3-ASM-24 (Hub- en executorkant van de tweede uitzondering, P2) (R-MANIFEST-1); C1.3-ASF-15
  en C1.3-HCH-16 aangevuld.
- `test_contract_13.py`: een eigen test per kernzin van §3.1, §8, §9 en §11, zodat een afzwakking ook na een nieuwe pin
  rood is (R-TECH-1); nieuwe pin in `test_contract_pin.py`; ADR-0031 besluit 3 en 9.

### Gewijzigd — Contract 1.3: aanvulling C-12 (S-P2-C12, deel A; ADR-0031; blijft `contracts 1.3`)
- `docs/platform-v2/PLATFORM_CONTRACTEN.md`: wijzigingslogblok "Aanvulling C-12" (C12-1 tot en met C12-6). §9: het
  optionele veld `accounts` met de aanmaakwijzen `eerste_gebruik` en `door_beheerder`, de weigering
  `account_gegevens_verboden`, de 32-tekens-eis voor een dienstaccount en "één weg per document" (geen controlelijst
  naast een installeerbaar manifest); EX47 noemt de accountgegevens. §3.1: tweede uitzondering voor een geheim van de
  Hub als vault-verwijzing in een omgevingsvariabele van een Custom App (besluit gebruiker 2026-11-11, S-P2-500), nooit
  voor een beheerder of dienstaccount; §3.2 en §8 volgen. §8: wat een preview minimaal toont. §11: validatiewaarde
  `NIET GEVALIDEERD (echte Hub)`. De versieregel blijft letterlijk gelijk.
- `docs/platform-v2/CONTRACT_1.3_CONFORMITEIT.md`: C1.3-ASF-15, C1.3-JLP-15 en C1.3-HCH-16 (P3).
- Nieuwe pin in `apps/api/tests/unit/test_contract_pin.py`; tests voor de aanvulling in `test_contract_13.py`; de vaste
  validatielijst van `test_evidence_contract.py` volgt de tabel van §11.
- `docs/platform-v2/03_INSTALLATIE/I10_NODE_RED.md` en `02_BOUWPLANNEN/B12_BACKUP_HERSTEL.md` volgen ADR-0016 van
  appstore-en-fork (Node-RED maakt zijn sleutel zelf, geen beheerder tot de gebruiker een weg kiest; een kopie van een
  dataset met sleutel en versleutelde gegevens geldt als geheim).
- De kopieën in de andere tien repos volgen in een eigen stap per repo (deel B).

### Gerepareerd — Hub: toonregels van de preview bijgesteld (S-P2-040 herstelronde 6)
- Omgevingscontext ook bij een deel dat op `env`/`envs`/`environment(s)` eindigt en bij `environ`/`dotenv` (niet `venv`); namen op `keys` en `oauth`, `jwt`, `otp`, `mnemonic`, `salt`, `seed` geheim-achtig; onder een geheim-achtige naam blijft de vorm staan (sleutels, ja/nee, leeg), een absoluut pad en `public_*` blijven zichtbaar (R-VEILIG-18 t/m 20; ADR-0030 besluit 32).

### Gerepareerd — Hub: scherpere toonregels voor de preview (S-P2-040 herstelronde 5)
- Geheim-achtige namen ook genormaliseerd en op `key`/`pwd`/`auth`, URL met alleen een wachtwoord, omgevingscontext alleen bij een heel deel `env`, onder een omgevingssleutel alleen korte niet-willekeurige namen, ook `huidig` door de toonfunctie (R-VEILIG-14 t/m 17; ADR-0030 besluit 32).

### Gerepareerd — Hub: elk veld van de preview door één toonfunctie (S-P2-040 herstelronde 4)
- Geen rauw veld meer in `preview.wijziging` (ook `resources`); onder elke sleutel met `env` (genormaliseerd) alleen namen, paren `key`/`name`/`value` in elke schrijfwijze, overige tekst en sleutels via `redact_text`; bewakingstest per veld (R-VEILIG-9 t/m 13; ADR-0030 besluit 32).

### Gerepareerd — Hub: omgevingsvariabelen in andere vormen alleen met naam in de preview (S-P2-040 herstelronde 3)
- Onder `environment`/`env`/`envs` van een catalogusapp, als `NAAM=waarde`, als `Name`/`Value` of als paar direct onder `values` staat alleen de naam in de preview; tests voor labels met een geheime `key` en niet-tekstgeheimen (R-VEILIG-8; ADR-0030 besluit 32).

### Gerepareerd — Hub: geheimen in de preview van een catalogusapp en herhaalde noodstop (S-P2-040 herstelronde 2)
- Een geheim-achtige sleutel direct onder de waarden van een catalogusapp staat in de preview als `***`; van elk paar
  `name` + `value` (zoals `additional_envs`) staat alleen de naam erin, de waarde als `***` (R-VEILIG-5 en -6;
  ADR-0030 besluit 28 en 32).
- Een herhaald uit-verzoek op `PUT /api/v1/actions/noodstop` met dezelfde `Idempotency-Key` wijzigt niets en geeft de
  werkelijke stand terug; een herhaald aan-verzoek zet de noodstop nog steeds echt aan (R-VEILIG-7).
- Tests in `apps/api/tests/integration/test_acties.py`.

### Gerepareerd — Hub: preview, bewijs en witte lijst bij acties (S-P2-040 herstel; ADR-0030 besluit 32)
- De preview van `app.install` toont elk gezet veld van `app_create.values` met zijn waarde (hostname, DNS, run_as,
  tty, stdin, labels, healthcheck en de rest; van `envs` alleen de namen, een geheim als `***`), ook de eigen waarden
  van een catalogusapp. Een voorstel met `command` of `entrypoint` geeft `501 capability_unavailable`
  (`eigen_opdracht`) tot er een installatiescherm is; een open voorstel van daarvoor wordt bij goedkeuren geweigerd.
  Na afloop verdwijnen `labels` en `notes` ook uit de bewaarde preview (R-VEILIG-1).
- `uitgevoerd` alleen met volledig bewijs van de executor (`methode`, `before_hash`, `after_hash`, `uitgevoerd_op`,
  `policy_hash` gelijk aan het eigen beleid), ook bij ophelderen via het journaal; anders `502 uitkomst_onbekend` en
  het incident `actie.afwijking` blijft open (R-VEILIG-2).
- Resultaat, audit, event en foutantwoord nemen van de executor alleen velden uit een vaste lijst over, met vaste vorm
  en grootte; eigen velden van de Hub zijn niet te overschrijven, `reden` is altijd een code (anders
  `onbekende_reden`; een NUL-teken gaf eerder HTTP 500) en `gestopt` alleen een echte ja/nee (R-VEILIG-3).
- `PUT /api/v1/actions/noodstop` zet de stand ook bij een herhaalde `Idempotency-Key` echt en geeft de werkelijke
  stand terug (R-VEILIG-4). De titel van `actie.afwijking` zegt "executor gestopt" alleen als de executor dat meldt.
- Tests: `tests/e2e/test_acties.py` (onder meer het event van `502 uitvoering_mislukt` en `gestopt` false bij
  ophelderen, R-TECH-1 en R-TECH-2), `apps/api/tests/integration/test_acties.py` (een bewakingstest per veld van de
  standaard Custom App) en `apps/api/tests/unit/test_incident_regels.py`.

### Gerepareerd — Hub: reden en stop van de executor in event en incident (S-P2-040; ADR-0030 besluit 26, 30 en 31)
- Antwoordt de executor na de schrijfaanroep `409 afwijking` (bv. `journaal_niet_beschikbaar` of
  `uitkomst_onbekend` na een onbekende jobstatus), dan neemt het event `action.run.failed` nu `reden` én `gestopt`
  over; het incident `actie.afwijking` toont ze. Hetzelfde bij ophelderen (`reconcile`) van een journaalrij die
  achteraf `afwijking` of `mislukt` blijkt: tot nu toe ging daar geen `reden` en geen `gestopt` mee in het event.
  `gestopt` komt alleen mee als de executor het zelf meldt.
- Tests in `tests/e2e/test_acties.py`: executor-409 bij een weggevallen journaal en bij een onbekende jobstatus;
  ophelderen van een journaalrij die achteraf `afwijking` (`staat_verschilt`, `uitkomst_onbekend`) of `mislukt` is;
  de vaste veldenset van elk actieantwoord (V-046: geen parameterwaarden en geen nonce).
- ADR-0030: besluit 30 (de 15 minuten gelden voor de goedkeuring; de preview wordt bij goedkeuren en uitvoeren
  opnieuw berekend), besluit 31 (onbekend `action_id` blijft `403`) en een open punt voor R-VEILIG-11
  (`ready_for_install`/`conflicts.status`, doorgeschoven naar S-P2-050/S-P2-080).

### Gerepareerd — executor: geen valse stop door statusopvragen (S-P2-030 herstelronde 2; ADR-0030 besluit 14)
- Een onaangemelde statusopvraag (`GET /api/v1/status` of de executorpagina) tijdens het begin van een uitvoering kon
  de executor ten onrechte op gestopt zetten (`uitkomst_onbekend`), terwijl de actie slaagde. Nu worden de lopende
  uitvoeringen binnen de schrijftransactie gelezen, en de statusopvragen lezen alleen: ze leggen nooit een stop vast
  (R-VEILIG-H1).
- Valt het journaal weg vóór de schrijfaanroep, dan krijgt de rij het einde `mislukt` zodra het journaal terug is, in
  plaats van later een stop met "uitkomst onbekend" (R-VEILIG-H2).

### Gerepareerd — executor: onbekende uitkomst na de schrijfaanroep en een duurzame stop (S-P2-030 herstel; ADR-0030 besluit 14)
- Faalt het opvragen van de jobstatus nadat TrueNAS de schrijfaanroep heeft aangenomen (er is een job), dan is de
  uitkomst onbekend: `409 afwijking` met `uitkomst_onbekend` en de executor stopt (`job_status_onbekend`), in plaats
  van `502` met "TrueNAS heeft de actie niet uitgevoerd". `502 uitvoering_mislukt` blijft alleen voor een aanroep die
  TrueNAS zelf weigert of een job die `FAILED`/`ABORTED` meldt (R-TECH-1).
- De stop is duurzaam: stop en einde van de journaalrij in één transactie; lukt vastleggen niet, dan blijft de stop in
  het geheugen tot het journaal weer werkt. Bij het starten en vóór elke uitvoering telt een rij `gestart` zonder
  einde (proces weggevallen na de schrijfaanroep) of een `afwijking` zonder vrijgave als stop. Elke onverwachte fout
  ná de schrijfaanroep is een onbekende uitkomst (stop), geen `500` (R-VEILIG-1, R-VEILIG-2). Een stop raakt nooit een
  app; vrijgeven blijft "Sleutel vervangen" met een leeg veld "Nieuwe sleutel". Een al vrijgegeven `afwijking` uit
  een eerder journaal geeft bij de eerste start met deze versie één keer opnieuw een stop.
- Te diep geneste JSON op `/api/v1/execute` geeft `422 validation_error` in plaats van `500` (R-VEILIG-3).
- Het journaal (ook `GET /api/v1/executions/{request_id}`) bewaart van een fout van TrueNAS alleen de code en de
  foutnaam of jobstatus (bv. `job_mislukt [FAILED]`), nooit de vrije fouttekst; die kan waarden uit de aanroep
  bevatten (R-VEILIG-4).
- Tests: `apps/executor/tests/test_stop_duurzaam.py` (de proeven van de review als vaste tests) en een aangepaste
  test in `apps/executor/tests/test_uitvoeren.py` (een fout bij het opvragen van de jobstatus geeft nooit meer `502`).

### Toegevoegd — executor: na een schrijfaanroep nooit "er is niets uitgevoerd" (S-P2-030; ADR-0030)
- Tests leggen vast dat een fout ná de schrijfaanroep naar TrueNAS (ook een geweigerde `app.update` nadat
  `app.config` lukte) nooit `503` met "er is niets uitgevoerd" geeft, maar `502 uitvoering_mislukt` of `409 afwijking`
  (`apps/executor/tests/test_uitvoeren.py`). ADR-0030 "Open punten": stand van de open punten uit de ruwe lijst
  (sleutelrotatie van de policy-sleutel in de executor nog open) en het besluit over de engine-regels buiten de
  `policy_hash` (geen contractveld; executor-image op digest, vervangen bij de uitrol in P6).

### Gerepareerd — herstelronde van de executor: schrijfsleutel, beheer en log (S-P2-020; ADR-0030 besluit 13)
- Beheer (`/beheer`: ontkoppelen, vervangen, vrijgeven) neemt als bewijs alleen de huidige opgeslagen sleutel: eerst
  een vergelijking in constante tijd met de ontsleutelde sleutel, daarna de live test. Een andere sleutel, ook een
  geldige schrijfsleutel, geeft `sleutel_niet_huidig` en gaat nergens heen; een onleesbare opslag of `vault.key` geeft
  `sleutelopslag_onleesbaar`. Een in TrueNAS ingetrokken sleutel vraagt een nieuwe datamap (R-VEILIG-2).
- Een schrijfsleutel moet de app- én snapshotacties dekken (`FULL_ADMIN`, of `APPS_WRITE` met `SNAPSHOT_WRITE`);
  anders `schrijfrechten_onvolledig`. De nep-TrueNAS dwingt de rechten per methode af (R-TECH-1).
- Status en pagina openen de opgeslagen sleutel echt: past `vault.key` er niet bij, dan `sleutelopslag_onleesbaar`,
  nooit "Gezond" (R-TECH-2). Uitvoeren met een onleesbare sleutelopslag geeft `503 schrijfsleutel_onleesbaar`
  (R-TECH-3).
- Een schijf- of rechtenfout bij het opslaan geeft `sleutelopslag_niet_schrijfbaar` (503) in plaats van een kale 500;
  een wedloop tussen twee tabbladen geeft `sleutel_al_ingesteld` (409) (R-TECH-4, R-TECH-9).
- `python -m executor api` logt elke afgehandelde poging (code en trace-ID) in de app-log; de verbinding met TrueNAS
  logt via een eigen logger vast op INFO, zodat websockets-frames met de sleutel nooit in een log komen
  (R-VEILIG-3, R-VEILIG-4).
- De web-E2E verstuurt nu ook het sleutelformulier (twee stappen) en "Sleutel vervangen" in Chromium (R-VEILIG-5).
- Een databasefout zet geen parameterwaarden meer in de fout of de app-log (`hide_parameters=True`; KLEIN-25, V-094).
- Een onverwachte databasefout zet de DETAIL-regel van PostgreSQL (sleutelwaarde of hele rij) niet meer in de app-log: de algemene foutafhandeling van API en worker logt alleen soort, sqlstate, constraint en tabel, en een logfilter haalt DETAIL ook elders weg (KLEIN-33).
- Log-schoning (KLEIN-89, V-094): een lange reeks met cijfers, hoofd- en kleine letters en hoge entropie wordt `[geheim?]`, ook met veel `_`/`-` (een willekeurig base64url-token bleef zo in ~0,18 % van de gevallen staan); bewuste gedragswijziging: een bestandsnaam of identifier van die vorm (bv. `TrueNAS_V2_Uitvoering_en_Afvinken_2026`) wordt nu ook geschoond.
- Teksten (KLEIN-60): de executormelding bij `ingetrokken_door_hub` wijst naar 'Ontkoppelen van de Hub' op de eigen pagina (met de schrijfsleutel) in plaats van "via de Hub"; `docs/RUNBOOKS.md` heet nu "Stappenplannen" en zegt "lijst met toegestane acties" (Peil §11.1).
- Nog open (wacht op een besluit over het Peil-sjabloon): opnieuw koppelen na ontkoppelen met sleutelbewijs
  (R-VEILIG-1) en een eigen knop "Vrijgeven" (R-TECH-5).

### Gerepareerd — herstelronde 3 van het policy-pakket: één tabel van verboden sleutels (S-P2-010; ADR-0030)
- De EX47-controle gebruikt één genormaliseerde tabel van verboden sleutels (kleine letters, alleen letters en
  cijfers), gelijk voor een sleutel in een object, een losse tekst in een lijst en de vlagvorm, in de Hub én de
  executor. `privileged` en `host_network` worden geweigerd met elke waarde behalve afwezig, `null` of `false` (ook
  `1` en `"true"`), ook in een andere schrijfwijze (`Privileged`, `hostNetwork`, `host-network`) en in een onderdeel
  van de standaard Custom App. "compose" in een sleutel en `services` zijn altijd verboden.
- Nieuwe weigering `catalogus_waarde_verboden`: Docker-/compose-namen met een niet-lege waarde (`network_mode` en
  `net` met `host` of `container:…`, `pid_mode`, `ipc_mode`, `uts`, `userns`, `cgroupns`, `security_opt`, `seccomp`,
  `apparmor`, `sysctls`, `volumes_from`, `runtime`, `device_cgroup_rules`, `allowPrivilegeEscalation`; bij een
  catalogusapp ook `command` en `entrypoint`), dezelfde namen als vlag (`"--network=host"`, `"--security-opt=…"`),
  en "unconfined" in een tekst. `device` en `--device` geven `devices_verboden`.
- In de waarden van een catalogusapp krijgt een tekstwaarde in een object dezelfde controle als een losse tekst in
  een lijst (`{"extra_args": "--privileged"}`, `{"volume": "/:/host"}`), en tellen `source`, `src`, `hostpath` en
  `path` met een waarde die met "/" begint als hostpad. Vrije tekst blijft toegestaan: de waarde naast `name` of
  `key` in een paar (`envs[].value`, `labels[].value`), `notes` en `description`.
- Een losse tekst met een onzichtbaar opmaakteken (Unicode Cf) wordt geweigerd (`stuurteken`); `"-v/:/host"` en
  `"--volume/:/host"` worden als bindvorm herkend.
- Opslag (KLEIN-76): `ix_volume_config.properties` wordt bij elke app geweigerd (nieuwe code `zfs_eigenschappen_verboden`), `mountpoint` met "/" is overal een hostpad, en bij de standaard Custom App geeft een `host_path_config.acl`-blok ook met `acl_enable: false` `acl_verboden` en gaat `acl.path` door de hostpadregel, in een opslagregel van elk type (R-VEILIG-1); een niet-lege config van een ander type dan de regel geeft `opslag_verboden` (ADR-0030 besluit 6).
- Opslag (KLEIN-77): de KLEIN-76-regels staan in de engine, buiten de `policy_hash` (die blijft gelijk); ze werken in de executor pas na een nieuw gebouwd en uitgerold executor-image (ADR-0030, "Engine-regels buiten de `policy_hash`").
- Opslag (KLEIN-78): `ix_volume_config.dataset_name` moet bij elke app een veilige ZFS-naam zijn (geen `/` aan het begin, geen `..`, geen leeg deel, alleen letters, cijfers, `-_.:` en spatie; anders `patroon`), en bij een catalogusapp is `cifs_config.password` alleen als kluisverwijzing toegestaan (nieuwe code `geheim_in_klare_tekst`, met 133c589 vervallen: SMB bij een catalogusapp geeft nu `opslag_verboden`, zie de regel hieronder); `policy_hash` gelijk, werkt in de executor pas na een nieuw executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-78, herstel R-VEILIG-1): bij een catalogusapp geeft SMB-opslag (elke opslagregel van type `cifs` en elke niet-lege `cifs_config`, ook in een andere schrijfwijze en in een lijst) `opslag_verboden`, ook met een kluisverwijzing als wachtwoord, tot de executor kluisverwijzingen invult (S-P2-050/070); dit vervangt `geheim_in_klare_tekst`, dat via `options` en een komma in `username`/`domain` te omzeilen was (ADR-0030 besluit 6).
- Opslag (KLEIN-80): bij de standaard Custom App geldt een witte lijst per opslagregel en per type-config (precies het formulier van ix-app 1.4.8); elke andere sleutel, ook `create_host_path`, `propagation`, `auto_permissions` en tmpfs `exec`/`mode`/`uid`/`gid`, geeft `onbekend_veld` (als sleutel; via `mount_path` waren die tmpfs-opties nog te zetten tot het herstel hieronder), `read_only` moet true of false zijn en `tmpfs_config.size` een geheel getal ≥ 1; `policy_hash` gelijk, werkt in de executor pas na een nieuw executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-80, herstel R-VEILIG-1 en R-VEILIG-2): bij de standaard Custom App is `mount_path` alleen een strikt containerpad (`/` met delen van letters, cijfers en `._@+-`; geen `:`, `,`, `=`, spatie, `.`- of `..`-deel of `/` aan het eind; genormaliseerd geen verboden containerpad), anders `mount_verboden`, zodat tmpfs-opties niet meer via `mount_path` te zetten zijn; in `ix_volume_config` geeft een niet-lege `acl_entries` of `acl_enable` anders dan false `acl_verboden` (KLEIN-75 A4 optie a: geen ACL op een ixVolume via het platform) en een `dataset_name` die er al eerder in staat `dubbel`; `policy_hash` gelijk, werkt in de executor pas na een nieuw executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-81): bij de standaard Custom App geldt een verboden containerpad (`/proc`, `/sys`, `/dev`, de Docker-socket) ook voor alles eronder, per padsegment: `/proc/sys`, `/dev/shm` en `/sys/fs/cgroup` geven nu `mount_verboden`, `/process` en `/devices` blijven geldig; `/` telt alleen exact en hoofdletters tellen mee (`/PROC` is een ander pad); `policy_hash` gelijk, werkt in de executor pas na een nieuw executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-88): bij de standaard Custom App zijn ook `/etc/hosts`, `/etc/hostname`, `/etc/resolv.conf` (door Docker beheerd) en `/run/secrets` verboden containerpaden, met alles eronder (`/run/secrets/x`): `mount_verboden`; `/etc`, `/run`, `/etc/hostsx` en `/run/secretsx` blijven geldig; `policy_hash` gelijk, werkt in de executor pas na een nieuw gebouwd en uitgerold executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-90): bij de standaard Custom App is ook `/var/run/secrets` een verboden containerpad, met alles eronder (`/var/run/secrets/x`): `mount_verboden` (zelfde lijn als de Docker-socket; `/var/run` is in gangbare images een symlink naar `/run`); `/var/run` en `/var/run/secretsx` blijven geldig; `policy_hash` gelijk, werkt in de executor pas na een nieuw gebouwd en uitgerold executor-image (ADR-0030 besluit 6).
- Opslag (KLEIN-83): bij een catalogusapp geeft NFS-opslag (elke opslagregel van type `nfs` en elke niet-lege `nfs_config`, ook in een andere schrijfwijze en in een lijst) bewust `opslag_verboden`, tot S-P2-050 (witte lijst per catalogusapp); het exportpad krijgt niet meer de misleidende `hostpad_verboden` en een exportpad zonder `/` gaat niet meer door; de standaard Custom App is ongewijzigd; `policy_hash` gelijk, werkt in de executor pas na een nieuw executor-image (ADR-0030 besluit 6).
- Terugzetten (KLEIN-85): bij `app.rollback` met `herstel_van` gaan de bewaarde vorige waarden door dezelfde `validate_parameters` als een installatie van de standaard Custom App; een overtreding wordt alleen gemeld (logregel, waarschuwing `herstelwaarden_buiten_beleid`, veld `hercontrole` met codes en aantal, journaal; nooit een waarde) en het terugzetten gaat door met precies dezelfde waarden; geen bovengrens voor `tmpfs_config.size` is een bewuste keuze (ADR-0030); aanvulling 2026-11-14 (KLEIN-86): werkt in de executor pas na een nieuw gebouwd en uitgerold executor-image (ADR-0030 besluit 8).
- Standaard Custom App: `command` en `entrypoint` zijn de opdracht van het proces in de container (zo gebruikt het
  ix-app-sjabloon ze). De vlag- en bindcontrole geldt daar niet meer, zodat gewone opdrachten zoals
  `java -cp /app/lib/*:/app/classes` en `gunicorn --pid /tmp/g.pid` niet meer geweigerd worden. De Docker-socket en
  de kluisregels gelden daar nog wel.

### Gerepareerd — herstelronde 2 van het policy-pakket: losse teksten in lijsten (S-P2-010; ADR-0030)
- De EX47-controle bekijkt ook een tekst die los in een lijst staat, op elke diepte. Een Docker-socket, een hostpad
  buiten een dataset in bind- of volumevorm (`{"binds": ["/:/host"]}`), een ongeldige kluisverwijzing en een verboden
  sleutel als vlag (`"--privileged"`, `"pid=host"`) geven `422 parameters_ongeldig`, in de Hub én de executor. Een
  geldige kluisverwijzing in een lijst wordt nu gevonden en geeft `501 capability_unavailable`.

### Gerepareerd — herstel na de review van het policy-pakket (S-P2-010; ADR-0030)
- Diep geneste parameters glippen niet meer langs de boiler- en EX47-controle: parameters zijn hooguit 16 niveaus
  diep (`te_diep_genest`), en de doorzoekers kijken tot 32 niveaus en weigeren dieper in plaats van stil te stoppen.
- `app.update` (en `app.rollback` met `herstel_van`) herkent het doel ook op de image ná de actie, in de Hub én de
  executor: een bestaande app omzetten naar een Emby-image wordt geweigerd met de Emby-regel (HARDE EIS).
- Eigen waarden van een catalogusapp: extra capabilities, devices, host-PID/-IPC, gedeeld netwerk en GPU zonder
  `gpu: intel_render` worden op elke diepte geweigerd, net als bij de standaard Custom App.
- `app.stop` zonder herkenning van het doel is R2 (dicht bij twijfel); een hostpad weigert ook Unicode-stuurtekens
  (Cc, Cf, Zl, Zp) en een spatie aan het begin of eind van een mapnaam; een losse surrogaat in de parameters geeft
  `422 parameters_ongeldig` (`niet_canoniek`) in plaats van een 500.
- De rooktest vergelijkt de `policy_hash` van de Hub- en de executor-image met elkaar en met `policy/`; een unittest
  bewaakt dat beide Dockerfiles precies `policy/*.yaml` kopiëren. Runbooktekst: "het platform weigert dit bij een
  gestopte Custom App".

### Gerepareerd — controle van het policy-pakket (S-P2-010; ADR-0030)
- `GET /api/v1/policy` noemt per app-actie ook de klasse voor een Custom App (`risk_class_custom_app`: `app.stop` is
  daar R2) en de twee vaste engine-regels (`engine_regels`: `STOP-EENRICHTING`, `DOEL-ONHERKENBAAR`), uitgerekend met
  de engine zelf. De runbooks noemen bij `app.stop` "Custom App: R2" en bieden na een stop geen terugzetten van een
  Custom App via het platform meer aan zonder de weg via de TrueNAS-web-UI.
- `app.install` van een catalogusapp wordt ook herkend op `app_create.catalog_app`, in de Hub én de executor: een
  tweede Emby onder een andere naam (`catalog_app: "emby"`) valt onder de Emby-regel en wordt geweigerd.
- Een hostpad met een tab, regeleinde of ander stuurteken wordt geweigerd (`hostpad_verboden`).
- `Herkenning.na_stop_herkenbaar` heeft geen standaardwaarde meer (dicht bij twijfel).
- Na afloop van een voorstel wist de Hub ook de vrije tekst in `command`, `entrypoint`, `labels` en `notes` van de
  installatiewaarden, net als de waarden van omgevingsvariabelen (ook na "geweigerd" en "onbekend").
- Tests voor elke verboden blokkade met haar eigen code (BLK-BEVEILIGING, BLK-BETAALD, BLK-DB-DIRECT, BLK-NETWERK
  erbij); `policy/README.md` en de engine noemen voor een onbekende `action_id` nu `403 actie_niet_toegestaan`.

### Toegevoegd — fase P2 deel 1: policy-engine, goedkeuringen en executor (ADR-0030; contract 1.3 §8)
- **Risicoclassificatie (B02-005):** `policy/*.yaml` (acties, apps, blokkades) read-only ingebakken in de Hub- én de
  executor-image, met `policy_hash`; gedeeld pakket `asm_policy` (deterministisch, R0–R3; `risk_claim` wordt bewaard
  en genegeerd). Onbekende, destructieve en shell-achtige acties en elke boilerschakeling worden altijd geweigerd;
  Emby en andere beschermde apps worden herkend op naam, catalogusapp én image; is van een bestaande app niet te zien
  wat erin draait (een gestopte Custom App: TrueNAS toont dan geen image), dan wordt elke actie erop geweigerd.
  Daarom vraagt `app.stop` op een Custom App altijd een goedkeuring van een beheerder (R2) en gebeurt hij nooit
  automatisch; de preview en de runbooks zeggen dat weer starten daarna alleen in de TrueNAS-web-UI kan. Een
  catalogusapp stoppen blijft R1.
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
  `custom_compose_config`), verwijderen alleen de containers (data blijft), terugzetten met de vorige waarden. Waarden
  van omgevingsvariabelen staan na afloop van een voorstel niet meer in de database van de Hub.
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
