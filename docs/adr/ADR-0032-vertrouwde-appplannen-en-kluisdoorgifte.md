# ADR-0032 — Vertrouwde appplannen, doelbinding en kluisdoorgifte

Status: ontwerp ter review, herstelronde 2 · 2026-11-17 · S-P2-050 deelstap A · niveau N4.
Basis: `e88a290c9ad5fef4acf498d05ad3414395a4fcb5` van `ai-server-manager`; herstel op
`58187e38145fd4628d712888a2829bdeb19fbe60` na de reviews R-VEILIG (bevindingen 1–10) en R-TECH (bevinding 1);
herstelronde 2 op `a03ca73e2ee0d12b0d9aad272529be19ead3dbf1` na de herreview (R-TECH-1 tot en met -3 en twee
kleine punten).
Besluit 8 bevat een besluit van de regisseur namens de afwezige gebruiker; het wordt de gebruiker nog voorgelegd.
Contract: `contracts 1.3` met aanvulling C-12, ADR-0031. Op 2026-11-21 zijn de bron- en doelbinding (M1) en
vertrouwde plannerinvoer (M3) vastgesteld in §8.1 en §8.2. Het eerdere routebesluit staat in §4.4.
Deze ontwerpstap legt bouwgrenzen en toekomstige bewijstests vast. Het contractbesluit levert de afspraken voor
de eigenaarrepos. De uitvoering en de acceptatieproeven van deel D volgen afzonderlijk.

## Context en gelezen bronstand

De generieke Hub/executor-keten bestaat. De volledige vertrouwde keten van catalogus via planner tot uitvoering
ontbreekt. `apps/api/src/hub/catalog/appstore.py::fetch_entries` leest entries, geen lifecycle-plannen.
`apps/api/src/hub/actions/blokkades.py::verified_checkpoint` geeft altijd `None`. Een groen resultaat met een
vervangen checkpointfunctie bewijst daarom geen bruikbare updateketen.

De volgende bronnen bepalen de grenzen, naast het dossier S-P2-050, kop "Omvang, niveau en opsplitsing":

- `docs/platform-v2/PLATFORM_CONTRACTEN.md`, koppen "1. Vaste keuzes", "2.3 Bestaande apps", "3.1
  Uitgangspunten", "3.10 Credentials van andere apps", "8. Risicobeleid, voorstel, goedkeuring en executor",
  "9. Manifeststandaard" en "11. Bewijs en Excel"; `CONTRACT_1.3_CONFORMITEIT.md`, C1.3-ASM-18/-24 en ASF-15.
- `docs/adr/ADR-0030-policy-engine-approvals-executor.md`, besluiten 6–12, 28 en 32 en "Open punten";
  `ADR-0031-contract-1-3-aanvulling-c12.md`, besluiten 3 en 9; `docs/EXECUTION_REQUEST.md`.
- `docs/platform-v2/02_BOUWPLANNEN/B01_HOME_CONTROL_HUB.md`, B01-003; `EXCEL_TAKEN.json`, B01-003;
  `01_ARCHITECTUUR/03_RISICO_AUTONOMIE.md`, "Technische handhaving" en "Speciale blokkades";
  `OVERDRACHT/STATUS.md`, gebruikersbesluiten; `02_BOUWPLANNEN/B03_BESLUITEN.md`, genomen en open besluiten.
- `appstore-en-fork` op `a994c2a51f45b81b2c48c6533b0ccf51ba857f5a` (opnieuw gemeten bij het herstel; het
  eerste ontwerp las `e634cb0`):
  `apps/api/src/appstore/api/catalog.py::get_version`, `version_summary`, `source_out`, `preview`, `_app_id_bound`;
  `catalog/service.py::verify_stored_provenance`, `ensure_bundled_source`; `catalog/sources.py::fetch_http`;
  `manifest/provenance.py::ProvenanceRecord`, `key_id`; `manifest/validator.py::validate_data`;
  `manifest/rules.py::ACCOUNT_WORDS`, `LOGIN_NAMES`, `is_account_name`; `manifest/translate.py::_Resolver.hub_at`;
  `secrets_store.py` (`identity.ed25519`); `hublink.py` (`public_key_jwk`);
  ADR-0015, besluiten 1–5 en "Gevolgen"; ADR-0023, besluiten 1–5.
  `valid` en `provenance_verified` zijn verschillende uitspraken. De laatste controleert opgeslagen bewijs met
  de eigen appstore-identiteit; dat is op zichzelf geen goedkeuring van een uitgever door de Hub.
- `jelly-leon-platform` op `5d314cf6952a1f1875990f89ce3b0a67cab2d182` (`apps/api/src/lifecycle` en ADR-0022
  ongewijzigd ten opzichte van het eerder gelezen `90c192b`):
  `docs/adr/ADR-0022-plannen-installatie-update-terugzetten.md`, "Besluit" en "Open punten";
  `apps/api/src/lifecycle/api_plans.py`, verzoekmodellen, planroutes en `report_step`; `lifecycle/auth.py::WRITE_ROLES`;
  `lifecycle/planner.py::_Bouw.stap`, `plan_update`, `_schaduw` en `meld`. Een los `manifest_yaml` levert daar
  bewust geen vertrouwde geheime vertaling. De ketentest met Hub-/executor-stand-ins is geen volledige Hub-test.
- In deze repo daarnaast: `apps/executor/src/executor/uitvoeren.py` (kop, `_plan`, `_voer_uit`),
  `executor/journal.py::save_values`, `executor/hublink.py`, `apps/policy/src/asm_policy/params.py::_app_update` en
  `_ix_values`, `apps/api/src/hub/vault.py` (`REF_RE`, `last4`, `Vault.put`), `hub/routers/actions.py::propose` en
  `::approve`, `hub/actions/service.py::stel_voor` en `keur_goed`, `hub/routers/events.py` (connectorroutes) en
  `hub/routers/services.py` (enrollment-token).

De onderstaande toetsen zijn **nog te bouwen en te draaien**, tenzij een bron uitdrukkelijk bestaande dekking noemt.
Een toetsnummer in dit ADR is geen bestaande testfunctie of evidence-ID. Per toets moet de bouwer de echte
testnaam, gepinde tegenpartijcommits, uitvoer en de rode mutatie-uitkomst vastleggen. Tests gebruiken tijdelijke
gegevens en de echte code van appstore, planner, Hub en executor; alleen TrueNAS wordt in de integrale proef nagebootst.

## Genummerde besluiten

### 1. Bronvertrouwen is een expliciete Hub-beslissing (C1.3-ASM-24)

**Keuze.** De Hub aanvaardt uitsluitend een exacte catalogusversie uit een door een beheerder goedgekeurde,
onveranderlijk gepinde bron. De vertrouwensselectie staat buiten AI en buiten invoer van een planner of aanvrager.
Zij bindt de actieve ingeschreven appstore-instantie en haar gepinde identiteit aan de bronidentiteit, soort,
repository/locatie, subpad, exacte revisie en toegelaten uitgeverssleutel. Een bewegende branch, alleen een URL,
`enabled: true` of `require_signature` zonder aantoonbaar geslaagde verificatie is onvoldoende. Vereist zijn altijd
beide: een exacte bronpin (een git-commit) én een geldige uitgevershandtekening tegen de vooraf toegelaten sleutel;
er is geen lossere variant. Een ingebouwde bron (`ensure_bundled_source`: geen handtekening, revisie
`bundled:<16 hex>`) en een http-bron (revisie is een ETag, `fetch_http`) voldoen daar nooit aan en blijven dicht.
Als uitgeversbewijs telt de Hub alleen het ondertekende provenance-record (`ProvenanceRecord`, getekend met de
identiteit die de appstore bij de Hub inschrijft: `secrets_store.py` `identity.ed25519` is dezelfde sleutel als
`public_key_jwk` in `hublink.py`; de Hub rekent die handtekening zelf na) of een eigen narekening van de
uitgevershandtekening, nooit het losse statusveld `publisher_signature` uit `version_summary`. Hij vergelijkt de
volledige uitgeverssleutel (de hele publieke sleutel of een volledige SHA-256-vingerafdruk), nooit alleen een
sleutel-ID van 16 hex (`key_id`, `trusted_key_id`, `publisher_key_id`). De appstore levert die volledige sleutel
in de gelezen bronstand alleen als korte sleutel-ID. §8.1 kiest de volledige uitgeversvingerafdruk in het door de
appstore getekende record. Zonder beschikbaar bewijs van die combinatie blijft uitvoering dicht. Een wijziging/intrekking
van deze selectie maakt open voorstellen ongeldig; de planner en een catalogussynchronisatie mogen de selectie
niet verruimen.

De Hub haalt entry, gekozen `version_id`, versiegegevens en bronstatus zelf bij die appstore op. Hij vergelijkt de
vaste `app_id`, entry-versiebinding en bronidentiteit en valideert het gehele manifest opnieuw met de gepinde
standaard, inclusief haar regels na parameterinvulling. De manifesthash is de hash van het canonieke ingelezen
manifestobject volgens `appstore.manifest.canonical`, zoals `validate_data` hem berekent; geen hash van opnieuw
opgemaakte YAML en geen willekeurig model met weggelaten velden/defaults. Ontbreekt het oorspronkelijke object of
de controleerbare herkomst, dan geen autorisatie. `valid=true`, een los manifest, een CLI-vertaling,
`trusted_app_id=True` of een lijst `vault_refs` van de aanvrager telt nooit als bronbewijs.

Een niet-geheime bindingscontext verbindt minimaal: appstore-identiteit, bronpin en goedkeuringsrevisie,
entry/versie, manifesthash, vaste `app_id`, doelinstantie uit besluit 2, image-digests/catalogusversie,
schema-/validatorpin, plannerplan en stap, vertaalde payload met verwijzingen, de exacte verzameling gemarkeerde
`{path, parameter, ref}` en onveranderlijke kluisrevisies uit besluit 4. Dezelfde context telt mee in de
gebonden preview en `action_scope.parameters_sha256`. Contract §8.1 legt die binding vast in `parameters.catalog_binding`.
Geen vrije extra velden in het huidige `ExecutionRequest`.

**Eigen anker van de executor.** Voor de executor is elk veld in de ondertekende context een claim, geen bewijs:
"het veld staat in de ondertekende context" is precies "de Hub heeft het goedgekeurd", en dat volstaat niet. De
bestaande executor kent alleen de gepinde policy-sleutel, het beleid in zijn image en zijn eigen readback
(`uitvoeren.py`, kop, stap 1–9); hij heeft geen catalogus- of bronkennis. Hij vergelijkt de claim daarom met twee
ankers die hij zelf heeft en die de Hub niet kan veranderen:

- **Bron en inhoud:** de witte lijst per app en versie uit besluit 6, als beleidsbestand onder de `policy_hash` in
  het image van Hub én executor (een verschillende lijst geeft dus al een weigering op de policy-hash; de vorm volgt
  in C). Elke regel noemt catalogusapp, trein, exacte versie, manifesthash, image-digests, schema-/ix-app-versie, de
  toegelaten bronidentiteit (soort, locatie, subpad, exacte revisie), de volledige uitgeverssleutel en het veldschema
  met de toegelaten kluisplekken. De executor weigert als bron, revisie, sleutel, `app_id`, versie, manifesthash of
  digest niet precies op één regel past, en toetst de werkelijke payload en de gemarkeerde
  `{path, parameter, ref}` zelf aan het veldschema van die regel. De beheerdersselectie in de Hub kan deze lijst
  alleen versmallen, nooit verruimen. Elke nieuw toegelaten cataloguscombinatie vraagt daarom een gezamenlijke
  release en uitrol van Hub- én executor-image met dezelfde nieuwe lijst; zolang de twee lijsten niet overeenkomen,
  weigert de executor op de policy-hash. Combinaties die nog nodig zijn voor terugzetten blijven in de nieuwe lijst
  staan (besluit 6).
- **Doel:** zijn eigen verse readback via zijn eigen gepinde TrueNAS-verbinding (bestaande stap 5–7: vingerafdruk,
  `app.query`/`app.image.query`, ETag) en zijn eigen instantielijst zonder waarden uit besluit 4. Bij een nieuwe
  installatie moet de runtime-naam afwezig zijn; bij een bestaande instantie moeten naam, catalogusapp/trein,
  image-identiteit en, als er kluisplekken zijn, zijn eigen instantieregistratie passen.

Een registerrevisie, plan-ID of bronselectie van de Hub kan de executor niet zelf nagaan; die vervangen nooit een
van beide ankers.

Hercontrole gebeurt bij voorstel, goedkeuring en vlak vóór uitvoering/ontsluiting. Elke wijziging vraagt een
nieuwe preview en goedkeuring. Alleen een aantoonbaar afwezige catalogusversie geeft `version_unavailable`;
een onbereikbare, onleesbare of verouderde bron geeft onbekend en houdt de gate dicht.

**Alternatieven en reden.** Alleen `valid` vertrouwen of de eigen appstore-handtekening gelijkstellen aan een
uitgeversgoedkeuring is verworpen: beide bewijzen een andere eigenschap. Bronlocatie uit het plan overnemen is
verworpen: dat laat de aanvrager zijn eigen vertrouwensanker kiezen. §8.1 bepaalt hoe de bronpin en het
uitgeversbewijs worden gecontroleerd. De keuze voor een concrete catalogusrelease volgt bij de levering.

**Bewijstest T1.** Een gegenereerde testuitgever, vooraf gepinde bron en echte catalogusversie leveren één
goedgekeurd voorstel op. Vervang afzonderlijk bron, uitgeverssleutel, entry, `version_id`, hash, `app_id`, doel,
payload of `vault_refs`; trek de bron tussen goedkeuring en uitvoering in. Iedere variant weigert vóór
ondertekening/ontsluiting en vóór een TrueNAS-schrijfaanroep. Test ook ontbrekend bewijs, verdwenen versie, een
`bundled`- en een http-bron, een los `publisher_signature: verified` zonder geldig ondertekend record en een andere
uitgeverssleutel met dezelfde 16-hex sleutel-ID.
**Directe executorproeven (T1-direct).** Een met de testsleutel van de Hub correct ondertekend verzoek (geldige
handtekening, nonce, tijden, policy-hash en goedkeuring) gaat rechtstreeks naar de executor, telkens met één
afwijking: een niet-toegelaten bron of revisie, een andere uitgeverssleutel, manifesthash, digest, `app_id` of
versie, een ander doel dan de eigen readback, of een extra, ontbrekende of verplaatste kluismarkering. Elk geval:
weigering met een vaste code, nul kluisopvragen en nul TrueNAS-schrijfaanroepen.
**Mutatie M-T1.** Sla de bronpin-/uitgeverscontrole of één bindingsvergelijking over: de overeenkomstige weigertest
moet rood worden, met aantoonbaar bereik van die controle. Haal de vergelijking met de witte lijst of met de eigen
readback uit de executor (de Hub-controles blijven staan): de betreffende directe executorproef wordt rood, en een
teller toont dat het verzoek de executor werkelijk bereikte.

### 2. Vaste app_id en TrueNAS-appnaam blijven afzonderlijke identiteiten

**Keuze.** Een kluisverwijzing gebruikt de vaste manifest-/catalogus-`app_id`. De TrueNAS-appnaam is een runtime-naam.
De bestaande `target.app_id` draagt in de generieke actieketen die runtime-naam; stilzwijgend herinterpreteren mag
niet. Het register bindt de vaste identiteit aan host/NAS-identiteit, unieke doelinstantie, bevestigde runtime-naam,
gemeten image/catalogusidentiteit, registerrevisie en resource-ETag. De bestaande basis is
`apps/api/src/hub/registry.py::app_name_for` en `service_base_url`; die basis is nog geen kluisautorisatie voor alle
catalogusapps. Een afwijkende naam kan uitsluitend via een bevestigde registratie worden gebruikt. Geen afleiding
uit naamgelijkenis, meegegeven `base_url` of een onbevestigde kandidaat.

Voor een nieuwe installatie wordt een unieke registratie in afwachting van readback aan de goedgekeurde runtime-naam
en `expected_version: absent` gebonden. Na uitvoering bevestigt alleen passende readback de registratie en hostpoort.
Een bestaande installatie wordt niet automatisch geadopteerd. Naamhergebruik na verwijderen, registerwijziging,
onherkenbaar doel of tegenstrijdige image-identiteit maakt een oude binding onbruikbaar. Beschermde apps worden ook
op image/catalogusidentiteit herkend; een hernoemde Emby wordt nooit vrijgegeven.

De drie logische delen van `vault://app/<app_id>/<parameter>` zijn exact `app`, de vaste `app_id` en de parameter.
Parseer structureel en begrensd: geen lege of extra delen, `.` of `..` als deel, traversal, query, fragment,
percent-gecodeerde scheidingstekens, Unicode-normalisatie, hoofdletteralias of witruimte. De bestaande tweeledige
credentialreferentie uit §3.10 blijft een andere namespace en is nooit geldig als app-verwijzing. Geen concateneren
naar een bestandspad en geen uitwijken naar `vault://<scope>/<naam>` als een app-ref niet bestaat.

De app-geheimen staan in een eigen opslagruimte. Een app-ref wordt nooit afgebeeld op de tweeledige vorm van
`hub/vault.py::REF_RE` (`<scope>/<naam>`) en nooit opgezocht in de bestaande ruimtes van de Hub (`auth`,
`truenas`, `monitoring`, `meldingen`; `make_ref` in `oidc/service.py`, `truenas/connection.py`,
`routers/monitoring.py`, `routers/notifications.py` en `routers/breakglass.py`). Anders zou een manifest met
`app_id` `truenas` en parameter `readonly-api-key` de eigen TrueNAS-sleutel van de Hub ophalen. Een `app_id` die
gelijk is aan zo'n ruimtenaam krijgt geen andere behandeling dan elke andere `app_id`: de lookup kan die ruimtes
eenvoudig niet bereiken.

Omdat de publieke verwijzing geen instantie bevat, houdt de interne kluislookup óók de bevestigde doelinstantie en
kluisrevisie aan. Er is nooit een app-brede fallback. Meerdere instanties van dezelfde vaste app krijgen geen
toegang tot elkaars geheimen; tot die eenduidige opslagbinding bestaat wordt deze capability geweigerd. Dat geldt
ook voor de schaduwinstallatie uit het updateplan (`planner.py::_schaduw`, stap `schaduw-installeren`: een tweede
instantie op een kloon). Voor een app met kluisgeheimen blijft die stap dicht tot een besluit in deelstap F (eigen
geheimen voor de testkopie of geen schaduwtest); de geheimen van de bron-instantie krijgt zij nooit.

**Alternatieven en reden.** Runtime-naam in het vaultpad zetten breekt de vaste identiteit bij een hernoeming.
Alleen de vaste app-id gebruiken deelt geheimen tussen instanties. Beide zijn verworpen. De precieze
doelbinding naast `target` staat in §8.1. De opslagmigratie voor geheime waarden hoort bij M2.

**Bewijstest T2.** Installeer met een afwijkende runtime-naam en controleer via de echte API dat alleen de juiste
geregistreerde instantie het verwachte testgeheim ontvangt. Test tweede instantie, naamhergebruik, ontbrekende
bevestiging, hostwissel en alle ongeldige verwijzingsvormen; geen kluislookup op een ander doel. Botsingsgevallen:
een vertrouwd testmanifest met `app_id` gelijk aan een bestaande kluisruimte (`truenas`, `auth`, `monitoring`,
`meldingen`) en een parameter gelijk aan een bestaande naam daar (bijvoorbeeld `readonly-api-key`,
`oidc-client-secret`), met de bestaande waarde vooraf gevuld: geen waarde, nul opvragen in de bestaande ruimtes
(teller per ruimte). Schaduwinstallatie van een app met kluisgeheimen: geweigerd, nul kluisopvragen. De
doelgevallen (tweede instantie, naamhergebruik, hostwissel, andere runtime-naam) gaan ook als correct ondertekend
verzoek rechtstreeks naar de executor (zoals T1-direct): weigering op zijn eigen readback en instantielijst, nul
kluisopvragen en nul schrijfaanroepen.
**Mutatie M-T2.** Vervang de registerbinding door naamvergelijking, laat een instantiecriterium weg of laat `..`
door de parser: telkens wordt de betreffende negatieve test rood. Beeld de app-ref af op twee delen
(`<app_id>/<parameter>` in de bestaande opslag): de botsingsproef wordt rood. Haal de doelvergelijking uit de
executor (de Hub-controle blijft): de directe doelproef wordt rood.

### 3. De Hub orkestreert het plan zonder authenticatie te omzeilen

**Keuze.** Een geautoriseerde gebruikerssessie start de Hub-orkestratie met de bestaande rol-, CSRF- en
idempotentiecontroles. De Hub zoekt de actieve planner via het register en gebruikt per uitgaande aanroep een
nieuw kortlevend dienst-JWT met precies de planner als audience en diens `service_id`. Een planner-service-token
heeft op de Hub naast de basisroutes van contract §4.4 (events/inbox, services/self, rotate, heartbeat, logs)
alleen leesscopes; het is geen gebruikerssessie en geen approval. Geen route van de Hub neemt een voorstel,
goedkeuring of stapresultaat van een dienst-token aan; de bestaande connectorroutes `/connector/v1/propose`,
`/apply` en `/rollback` (`routers/events.py`, `ViewerOrService`) blijven voor een dienst-token 501.
`apps/api/src/hub/routers/actions.py` wordt hiervoor niet versoepeld. Tot de partijen de vereisten van §8.1
en §8.2 afdwingen, gaat geen planstap naar uitvoering.

**Alleen een eigen plan.** De Hub werkt alleen met een plan dat hij in deze orkestratie zelf bij de planner
aanmaakte (eigen aanroep van de preview-route onder `/lifecycle/v1/plans`; plan-ID, ETag, manifesthash en
vervaltijd uit dat antwoord), nooit met een plan-ID, ETag of stappenlijst van de aanvrager. Hij houdt per stap
zijn eigen boekhouding bij. Toont de planner een wijziging die de Hub niet zelf meldde (een stapstatus, ETag of
inhoud anders dan zijn boekhouding), dan stopt de orkestratie: geen volgende stap, wel een melding.

**Actiestap en handmatige eigenaarstaak zijn verschillend.** De planner kent stappen van soort `actie` (met
`voorstel`) en `handmatig` (zonder voorstel en zonder `verwacht`; `planner.py::_Bouw.stap`). Voorbeelden van
handmatig zijn `export` (bij `backup.db_export.method` `pg_dump`, `sqlite_backup` of `app_native`) en
`kloon-opruimen`. De planner kan geen van beide nagaan: `meld` vraagt bij een actie alleen een niet-lege
`execution_id` en bij een handmatige stap niets, en `report_step` staat open voor admin, operator en de Hub als
dienst (`lifecycle/auth.py::WRITE_ROLES`; ADR-0022 besluit 7). Daarom is de stand in de planner voor de Hub nooit
bewijs:

- Een voorganger van soort actie telt alleen met een eigen uitgevoerd actieverzoek van de Hub voor precies dat plan
  en die stap: een `request_id` uit de eigen Hub-administratie, uitkomst uitgevoerd en readback die past bij
  `verwacht`, vastgelegd vóór de terugmelding.
- Een handmatige stap telt alleen met een bevestiging in de Hub door een beheerder (levende sessie met rol admin,
  CSRF, gebonden aan plan, stap, plan-ETag en doel). Zo'n bevestiging levert nooit een geverifieerd app-checkpoint
  of exportbewijs op. De Hub meldt de stap aan de planner zonder `execution_id`, met de bevestiging als reden; hij
  verzint nooit een `execution_id`.
- Een melding die iemand anders rechtstreeks bij de planner deed (operator of beheerder) maakt een stap voor de Hub
  niet voltooid; ziet de Hub zo'n stand, dan stopt hij.
- De updatevariant waarvan het plan een handmatige `export` bevat, blijft dicht tot het exportbewijs verifieerbaar
  is: in F een checkpoint dat de Hub zelf verifieert, gebonden aan doel, database/dataset en tijd. Tot dan geen
  `bijwerken` na zo'n plan. `kloon-opruimen` blijft een eigenaarstaak; het platform verwijdert geen kloon of dataset.

**Levende sessie per stap, geen uitvoering op de achtergrond.** Elk voorstel en elke uitvoering van een planstap
vraagt op dat moment een levende sessie met de vereiste rol: voorstel operator of hoger; goedkeuring, R2/R3 en de
bevestiging van een handmatige stap admin. De controles zijn die van `routers/actions.py::propose` en `::approve`
(rol, CSRF, `actor_past_niet`); `service.stel_voor` en `keur_goed` doen zelf geen rolcontrole en worden daarom
alleen vanuit zo'n aanvraag aangeroepen. Er is geen lus die vervolgstappen (ook R0/R1, die zonder goedkeuring
uitvoeren) op naam van de starter uitvoert. Is de sessie ingetrokken, de rol verlaagd of de gebruiker
uitgeschakeld, dan volgt geen voorstel en geen uitvoering.

Elke actiestap doorloopt dezelfde proposalservice, deterministische policy, actuele gates, preview en menselijke
goedkeuring als een rechtstreeks voorstel. De actor blijft herleidbaar tot de echte initiator; de planner kan geen
gebruiker of risico claimen. Een UUID5 van de planner dedupliceert alleen; hij vervangt geen goedkeuring,
vervaltijd of nonce.

De appstore-preview moet voor exact dezelfde versie, parameters en gemeten doelcontext `ready_for_install: true`
én `conflicts.status: ok` geven, naast de Hub-controles. Bij ontbreken, onbekend of veroudering geen vrijgave.
Vóór uitvoering leest de Hub plan en bronnen opnieuw; gewijzigde ETag/inhoud vervalt de goedkeuring. Na uitvoering
meldt hij alleen eigen gecontroleerde execution-ID en gemaskeerde readback terug, met idempotentie en vers JWT,
en leest het plan opnieuw. Onzekere uitvoering wordt niet opnieuw uitgevoerd om de rapportage te herstellen.
Ontbrekend digestbewijs uit `app.image.query` is onbekend, geen succes; afwijkende digest stopt de executor en
wordt een incident. Container-only verwijderen hergebruikt `app.delete` met `remove_ix_volumes: false` en
`remove_images: false`; er is geen gefingeerd uninstall-plan. Post-install-controles blijven een echte gate,
ook als `app.create` zelf slaagde.

**Alternatieven en reden.** Een planner-token door de gebruikersroute laten gaan, een stand-in als productieroute
inbouwen of een plannerstap rechtstreeks naar de executor sturen is verworpen: dat omzeilt bestaande autorisatie.
De stapstatus van de planner als bewijs tellen of vervolgstappen op de achtergrond uitvoeren is verworpen: de
planner kan een melding niet nagaan en een achtergrondlus handelt na intrekking nog op naam van de starter.
De bouw van vertrouwde plannerinvoer bij de tegenpartij volgt §8.2. Een losse YAML-tekst geeft geen
uitvoeringsrecht. Voor plannen met kluisverwijzingen blijven ook de vereisten van besluit 4 gelden.

**Bewijstest T3.** Echte planner, appstore, Hub en executor met fake TrueNAS: installatie, terugmelding en
registratie. Test planner-token op gebruikersroute, ontbrekende gebruikersrol/CSRF/approval, gewijzigde plan-ETag,
geblokkeerde voorganger, `ready_for_install: false`, conflict, ontbrekende digest, replay en verlopen plan.
Controleer datasets en snapshots vóór/na verwijderen en geen tweede schrijfaanroep bij dubbele melding.
Daarnaast, elk met een teller op `stel_voor` en op de executor:
- een operator meldt een stap rechtstreeks bij de echte planner als voltooid, ook met een verzonnen `execution_id`:
  de Hub voert de volgende stap niet uit en stopt de orkestratie;
- een plan-ID van de aanvrager in plaats van een eigen plan: geweigerd;
- sessie ingetrokken, rol verlaagd of gebruiker uitgeschakeld tussen stap 1 en 2: geen voorstel, geen uitvoering;
- een planner-token op `/connector/v1/propose`, `/apply` en `/rollback` blijft 501, en geen route neemt een
  voorstel, goedkeuring of stapresultaat van een dienst-token aan;
- handmatige stap: een `app_native`- en een `pg_dump`-keten (echte planner, vertrouwd testmanifest met die
  `backup.db_export.method`). Zonder bevestiging, met een bevestiging door een operator of met alleen een melding
  bij de planner: geen vervolgstap. Met een beheerdersbevestiging: de stap telt, maar er ontstaat geen geverifieerd
  checkpoint en `bijwerken` blijft dicht tot F; aan de planner gaat geen `execution_id` mee.
**Mutatie M-T3.** Schakel één gate, sessiecontrole, ETag-binding of readbackvergelijking uit: de eigen negatieve
test moet rood worden. Een teller bewijst dat de beoogde stap werkelijk is bereikt. Laat de Hub de stapstatus van
de planner als voorgangerbewijs tellen, of accepteer een beheerdersbevestiging als export- of checkpointbewijs: de
proef met de verzonnen melding respectievelijk de `app_native`/`pg_dump`-proef wordt rood. Voer een vervolgstap uit
zonder hercontrole van de sessie: de proef met de ingetrokken sessie wordt rood.

### 4. Kluisdoorgifte gebeurt afzonderlijk, eenmalig en pas na hercontrole

**Keuze.** De ondertekende envelope, alle verzoek-/parameter-/before-/after-hashes, idempotentie-opslag, audit,
journaal, events, connector-items, AI en logs bevatten nooit de ontsloten geheime waarde of een waarde-afgeleide
hash. Ook geen ciphertext met de nieuwe waarden in de envelope of het journaal. Zij bevatten hooguit de gebonden
verwijzingen, niet-geheime kluisrevisies en context. De vault zelf bewaart de waarden versleuteld.
Een kluisrevisie is een ondoorzichtige onveranderlijke identiteit, geen hash van het geheim. Rotatie maakt een
nieuwe revisie en vraagt een nieuwe preview/goedkeuring; een ref kan na goedkeuring niet stil van waarde wisselen.

Het gekozen transportontwerp is een **afzonderlijke ophaalverbinding van executor naar Hub met TLS 1.3,
wederzijdse certificaatcontrole en vooraf gepinde transportidentiteiten**. Geen HTTP-terugval, redirects,
TLS-early-data of doorgifte door de gewone webproxy. Het bestaande HTTP-dienstkanaal alleen is daarvoor onvoldoende.
De executor krijgt geen Hub-database, kluisbestand of vault-hoofdsleutel. De transportidentiteit is afzonderlijk
van de Ed25519-policyondertekeningssleutel; die sleutel wordt niet als encryptiesleutel hergebruikt.
Elke partij maakt haar eigen transportprivésleutel lokaal; alleen het publieke certificaat/de publieke pin wordt
uitgewisseld via een door een beheerder bevestigde koppeling. Privésleutels blijven onder de bestaande
geheimenmaprechten, buiten de AI-runner. Intrekken/ontkoppelen blokkeert de ophaalverbinding onmiddellijk;
een gewijzigde pin wordt nooit via dezelfde onbevestigde verbinding vertrouwd. Geen trust-on-first-use.
Het exacte koppel-/rotatieprotocol, het strikte berichtschema en de endpointvorm moeten vóór E als M2 worden
vastgesteld en interoperabel getest. M2 is vastgelegd in contract §8.3; de transportvorm daar vervangt de TLS-verbinding hierboven
(zie 'Open contractmeldingen en tekstvoorstellen'). Dit ADR verzint daarvoor geen reeds bestaand endpoint of extra envelopeveld.

De verplichte volgorde voor de latere implementatie:

1. De Hub maakt gegenereerde niet-accountgeheimen (type appgeheim hieronder) uitsluitend in de vault en bindt
   revisies en alle gemarkeerde plekken aan de preview. Parameteropslag en antwoorden bevatten alleen
   verwijzingen. Iedere ontbrekende, dubbele of extra markering weigert; een ref op een andere plek of als
   deeltekst wordt nooit opgelost.
   Er zijn precies twee gebonden typen, elk met een eigen vaste vorm en eigen opslag- en hashregels:
   - **appgeheim** (contract §3.1 a en de tweede uitzondering, C-12), op een toegelaten kluisplek van de eigen
     witte-lijstregel (besluit 6). Vorm `^[A-Za-z0-9][A-Za-z0-9_-]{42}$`: 43 tekens, 32 willekeurige bytes als
     base64url zonder opvulling; een waarde die met `-` of `_` begint wordt verworpen en opnieuw gemaakt. Opslag
     versleuteld in de eigen app-opslag van besluit 2, op te halen met ref en revisie. Die opslag bewaart geen
     `last4` of ander deel of afgeleide van de waarde (anders dan `Vault.put`, dat `last4` vult), alleen
     "gegenereerd" met datum en revisie (contract §3.1 a); nergens staat een hash van de waarde.
   - **enrollment-token**, uitsluitend op de plek `HUB_ENROLLMENT_TOKEN` van een koppelbare eigen dienst met
     volledige koppeling (koppelvelden hieronder; my_house krijgt alleen `HUB_URL` en heeft geen tokenplek). Vorm:
     het bestaande formaat, ongewijzigd: `^enr_[A-Za-z0-9_-]{43}$`, dus `enr_` plus 43 tekens, 47 in totaal
     (contract §3.2–§3.4; `hub/security.py::new_token`, `hub/routers/services.py` `ENROLLMENT_TOKEN`). Nooit in de
     kluis of de app-opslag en nooit terugleesbaar; de Hub bewaart alleen de SHA-256 in zijn bestaande
     enrollment-opslag (contract §3.1 en §3.4), nergens anders een hash of deel.

   Het type van elke plek volgt uitsluitend uit de eigen witte-lijstregel (de toegelaten kluisplekken zijn
   appgeheimen; de koppelbare eigen dienst geeft de ene tokenplek); Hub en executor bepalen het elk zelf. Geen veld
   van de aanvrager, het voorstel, het manifest, de planner of het ophaalantwoord kiest of verandert type of
   patroon. Een app die voor een appgeheim een andere vorm vraagt, wordt niet ondersteund.
2. De executor ontvangt eerst uitsluitend het normale ondertekende verzoek met de vastgelegde niet-geheime
   context. Hij controleert zelf handtekening, tijden, nonce, allowlist, schema, C-12, bron-/doelbinding,
   policy-hash, eigen risicoklasse, approval, checkpoints en verse precondities, vóór enige kluisopvraag.
3. Op de gepinde ophaalverbinding vraagt uitsluitend die executor precies de toegelaten referenties/revisies op
   (en, bij een gekoppelde eigen dienst, het token voor de ene tokenplek), gebonden aan de hash van het
   **ref-only** ondertekende verzoek, request-ID, approval/nonce, doelinstantie, uitvoerderidentiteit en vervaltijd.
   De Hub controleert opnieuw de actuele autorisatie, intrekking en context.
   Een opvraag met een andere of extra ref of revisie dan aan het verzoek gebonden is, wordt in zijn geheel
   geweigerd: geen gedeeltelijke afgifte.
   Een vrijgave vervalt uiterlijk bij de eerst aflopende verzoek-/approvaltijd, met maximaal 60 seconden
   ophaaltijd; zij is nooit overdraagbaar aan een andere executor of een volgend verzoek. De laatste lokale
   preconditiecontrole gebeurt na ontvangst, direct vóór de RPC; bij een gewijzigd doel wordt niet geschreven.
4. Een atomaire claim verhindert twee ontvangers. Bewaarde claimgegevens bevatten geen waarden of ophaalbaar
   antwoord. Transportreplay of herstart levert geen nieuwe waardeafgifte; bij onzekerheid nieuwe autorisatie,
   nooit blind herhalen. Vervallen approval of onbereikbare Hub betekent geen waarde en geen uitvoering.
5. Alleen direct voor de goedgekeurde `app.create`/`app.update` vervangt de executor de exacte gemarkeerde
   tekstplekken in een tijdelijke kopie. De opgehaalde waarde valt buiten de handtekening, de goedgekeurde preview
   en de parametercontrole (die liep in stap 2 over de verwijzing). Daarom toetst de executor elke opgehaalde
   waarde vóór het invullen aan de vaste vorm van het type dat zijn eigen witte-lijstregel aan die plek geeft
   (stap 1) en aan de gevraagde ref en revisie (bij het token: aan de gevraagde plek en het verzoek). Een waarde
   van het andere type past nooit. Past één waarde niet, dan weigert hij het hele verzoek met een vaste code,
   zonder schrijfaanroep en zonder de waarde te loggen.
   Het oorspronkelijke verzoek blijft ref-only. De uitvoer-adapter mag dit object niet via generieke
   request-/exceptionlogging laten lopen; ook het TrueNAS-clientpad is afgeschermd.
   Een capability voor een andere methode, bestemming of accountplek blijft geweigerd.
6. Bij succes, weigering, fout en time-out worden tijdelijke kopieën en transportbuffers zo snel mogelijk
   losgelaten en nooit gedumpt. Dit is geen bewijs dat alle geheugenkopieën in de runtime fysiek gewist zijn.
   Geen bodies, traceback-locals, ruwe TrueNAS-foutteksten of request-objecten in diagnostiek. Alleen vaste codes
   en aantallen naar het bestaande afgeschermde resultaatpad; bij onbekende uitkomst de bestaande stop/incidentweg.

**Terugzetrecept van een instantie met kluisplekken.** Het bestaande versleutelde terugzetrecept uit ADR-0030
besluit 8 wordt niet verwijderd. Het bewaart bij elke `app.update`/`app.rollback` van een ix-app de hele
`app.config` (`uitvoeren.py::_voer_uit`, `journal.py::save_values`), en een gewone image-update draagt geen
markering (`params.py::_app_update`: alleen `image`, `catalog_version`, `image_digest`, `manifest_sha256`). Een
geheim dat de executor in E invulde, komt zo bij de eerstvolgende gewone update alsnog (versleuteld) in het recept.
Daarom weigeren Hub én executor vanaf deelstap E elke `app.update` en `app.rollback` die een recept maakt of
gebruikt (het `app.config`-pad) op een instantie met gebonden kluisplekken, ook de gewone image-update, tot het
recept met alleen verwijzingen en revisies (M2) bestaat en met T4 bewezen is. Het catalogus-pad (`app.upgrade`,
`app.rollback` met `catalog_version`) maakt geen executorrecept en blijft onder besluit 8 en de gates van F.

De executor kent die plekken uit zijn eigen instantielijst. Bij elke geslaagde invulling legt hij in zijn journaal
vast, zonder waarde of waarde-afgeleide hash, welke instantie (vingerafdruk van zijn gepinde TrueNAS-verbinding,
runtime-naam, catalogusapp/trein, `request_id` van de installatie) welke gemarkeerde plekken met welke refs en
revisies kreeg. Alleen de executor vult in, dus alleen hij heeft deze lijst volledig. De Hub houdt dezelfde
markering in zijn register en zet haar in de ondertekende context van elk update- en terugzetverzoek. Onbekend is
weigeren: is de lijst niet leesbaar, verschillen lijst en ondertekende markering, of is de instantie niet eenduidig
vast te stellen, dan weigert de executor met een vaste code vóórdat hij `app.config` leest. Andere bestaande
recepten (zonder kluisplekken) blijven onder het bestaande beleid; dit ADR claimt geen opschoning daarvan.

**Koppelvelden `HUB_*`.** De Hub voegt ze alleen toe als hij de betrokken eigen dienst koppelt, en zo:

- Nooit uit parameters van de aanvrager. De bestaande weigering `reserved_env` (`params.py::_ix_values`, in Hub én
  executor) blijft voor elke parameter van een voorstel; er komt geen uitzondering in de parametercontrole.
- In het voorstel staat alleen een ondertekend, niet-geheim contextveld "de Hub koppelt deze vaste `app_id`", met
  de soort (volledig, of alleen `HUB_URL` voor my_house). De aanvrager kan het niet zetten; de Hub zet het alleen
  voor een eigen dienst die op de witte lijst van besluit 6 als koppelbaar staat.
- De executor zet `HUB_URL` en `HUB_KEY_FINGERPRINT` zelf uit zijn eigen gepinde koppeling met de Hub
  (`executor/hublink.py`, `hub_url` en `keyset_fingerprint`). Noemt de context een ander adres of een andere
  vingerafdruk, dan weigert hij zonder schrijfaanroep.
- `HUB_ENROLLMENT_TOKEN` wordt pas bij de claim uit stap 3–4 gemaakt, niet bij voorstel of goedkeuring (een
  voorstel kan tot 24 uur open staan, `ProposalIn.expires_in_seconds`; het token leeft 60 minuten). Het is gebonden
  aan de vaste `app_id`, het verzoek en de doelinstantie, reist alleen over de afzonderlijke ophaalverbinding en is
  nooit terugleesbaar: de Hub bewaart alleen de hash (contract §3.1), nooit in de kluis, een tabel, het journaal,
  een recept of een antwoord. Het heeft het type enrollment-token uit stap 1 met het bestaande formaat; de
  executor toetst het in stap 5 aan dat formaat, nooit aan de vorm van een appgeheim. De plek van het token telt
  in de instantielijst als gebonden kluisplek, zodat ook hier de receptweigering hierboven geldt (gevolgen
  hieronder). Opslag en moment van uitgifte worden in M2 vastgelegd.
- De preview toont de koppeling: "koppelt met de Hub", met adres en vingerafdruk van de eigen koppeling; nooit
  het token.
- my_house krijgt alleen `HUB_URL`; bestaande adapters krijgen geen automatische enrollment. Bij een onzekere
  uitvoering geen nieuw token op hetzelfde oude akkoord en geen automatische tweede installatie; eerst toestand
  vaststellen, zo nodig het oude token intrekken en een nieuwe gebonden handeling.

**Gevolgen van de tokenmarkering (vastgesteld vóór E).** Voor een eigen dienst waarvan de executor zelf het token
invulde, geldt vanaf E:

- Een gewone image-update en een `app.rollback` met `herstel_van` lopen over het `app.config`-pad en worden door
  Hub én executor geweigerd tot het ref-only recept (M2) bestaat en de fase na M2 van T4 bewezen is. Tot dan kan
  het platform zo'n dienst langs die weg niet bijwerken of terugzetten.
- Een verlopen of gebruikt token heft de markering niet op: de waarde kan in de TrueNAS-configuratie blijven staan
  (hoe TrueNAS haar bewaart is NIET GEVALIDEERD, contract §3.1) en zou anders bij de volgende update in het
  recept komen. Er is geen vrijgave na alleen tijd of gebruik.
- Hoe het ref-only recept de tokenplek vastlegt (alleen plek en type, nooit waarde of hash) en wat een terugzetting
  daar invult, legt M2 vast; tot dan geldt de weigering.
- Alleen wat de executor zelf invulde, wordt gemarkeerd. Bestaande adapters (MediaGuard, MSO, Jellyfin/Jelly
  Leon, Emby: geen enrollment, contract §2.3 regel 2), de plugin die met een publieke sleutelset koppelt (regel 9),
  my_house (alleen `HUB_URL`, niet geheim), een eigen dienst die vóór E of met de hand is gekoppeld (koppelcode, of
  een token dat de beheerder zelf in het formulier zette, contract §3.2 punt 2) en elke andere instantie zonder
  eigen invulling krijgen geen markering. Hun gewone updates en hun bestaande terugval blijven onder het bestaande
  beleid, met hun bestaande blokkades (zoals de Emby-bescherming).

De acceptatie van E toont dit aan (T4, tokenmarkering); zonder dat bewijs geen vrijgave van E.

OIDC-`client_secret`-overdracht blijft afzonderlijk in
[ADR-0033](ADR-0033-oidc-clientgeheim-naar-de-hubkluis.md) (070, ontwerp): een door Authentik gemaakte
credential voor de Hub, geen appgeheim of enrollment-token op dit ophaalkanaal. De eigen OIDC-ruimte uit
ADR-0033 (niet de gedeelde `auth`-ruimte) blijft gescheiden van de app-opslag van besluit 2;
de open OIDC-contractmeldingen sluiten M2 hier niet.

**Alternatieven en reden.** Geheim vóór ondertekenen in `parameters` zetten, de vault delen, een algemeen
`get_secret(ref)` aanbieden of plaintext via het gewone HTTP-kanaal sturen is verworpen: de eerste twee lekken
naar duurzame opslag/bevoegdheden, de laatste twee missen de noodzakelijke doel- en verzoekbinding. Alleen
maskeren bij loguitvoer is onvoldoende. Tot M1/M2 en de bewijstests zijn afgerond blijft `501 capability_unavailable`
voor deze kluiscapability gelden; de vermelding "oplossen bij samenstellen ExecutionRequest" uit 070 geeft geen uitzondering.

**Bewijstest T4.** Een per test willekeurig gemaakt geheim bereikt uitsluitend de juiste fake-TrueNAS-waarde bij
`app.create`/`app.update`. Onderzoek niet-lege vastgelegde requests, canonieke hashinvoer, signatures,
Hub-tabellen inclusief idempotentie, executorjournaal en recepten, routeantwoorden, events en logs. De recepten
worden daarbij ontsleuteld (`Journal.load_values`): in de ruwe journaalbytes staat een versleutelde waarde nooit
letterlijk, dus een zoektocht daarin kan niet falen. Gezocht wordt op de hele waarde, op haar base64-, URL- en
JSON-vorm, op haar SHA-256 en, in de kluistabel buiten de ciphertext, op elk venster van vier of meer tekens.
Nul treffers zijn vereist. Herhaal bij rotatie, fout vóór/na RPC, timeout, herstart, dubbele claim,
foutcertificaat/pin, HTTP-downgrade, verkeerde executor, ontbrekende ref, een opvraag met een andere of extra ref
of revisie dan gebonden, en ingetrokken approval. Voor afwijzingen vóór ontsluiting is ook het aantal
kluisopvragen nul. Daarnaast:
- recept, fase vóór de vrijgave van M2 (vanaf E): installatie met geheim, daarna een gewone image-update en een
  `app.rollback` met `herstel_van` op die instantie: Hub én executor weigeren vóór `app.config`, nul
  schrijfaanroepen en nul aanroepen van de receptopslag (teller op `save_values`/`load_values` of hun opvolger);
  hetzelfde met een onleesbare instantielijst en met een ondertekende markering die afwijkt van de eigen lijst.
  Deze fase bewijst de weigering, niet de receptschrijver;
- recept, fase na de vrijgave van M2: op een gemarkeerde instantie een echte gewone image-update en daarna een
  `app.rollback` met `herstel_van` naar het daarbij gemaakte recept, via de productieschrijver (`_voer_uit` en de
  receptopslag; een teller toont dat de schrijver werkelijk is bereikt). Het ontsleutelde recept is niet leeg en
  bevat op de gemarkeerde plekken uitsluitend de juiste refs en revisies uit de eigen instantielijst (geen
  ontbrekende, extra of andere); na de rollback staan in de nagebootste TrueNAS exact de vorige waarden (de
  geheime plek opnieuw ingevuld uit de gebonden ref en revisie volgens stap 2–5) en de vorige digest; de
  zoektocht hierboven geeft nul treffers op de waarde en haar afgeleide vormen;
- vorm, voor beide typen: de test-Hub levert een padtekst, een vlag (een waarde die met `-` begint), een waarde
  met een regeleinde, een te korte en een te lange waarde en de waarde van een andere ref; voor het token ook een
  waarde zonder `enr_` en een met 42 of 44 tekens na `enr_`: weigering, nul schrijfaanroepen, de waarde in geen
  enkele log;
- kruisverwisseling: de test-Hub levert op de tokenplek een waarde in de vorm van een appgeheim en op een
  appgeheimplek een geldig `enr_`-token, telkens met het bijpassende (verkeerde) type in zijn antwoord; en een
  voorstel of manifest dat zelf een type of patroon noemt: weigering van het hele verzoek met een vaste code, nul
  schrijfaanroepen, de waarde in geen enkele log;
- koppelvelden: `HUB_*` als parameter van de aanvrager geweigerd in Hub en executor; een ander adres of andere
  vingerafdruk in de context dan de eigen koppeling: nul schrijfaanroepen; het enrollment-token in geen tabel,
  journaal, recept of antwoord (alleen de hash), en de preview toont adres en vingerafdruk;
- koppelketen (positief): echte Hub, echte executor, nagebootste TrueNAS en een koppelbare eigen dienst op een
  gepinde commit. Na goedkeuring en claim ontvangt de nagebootste TrueNAS `HUB_URL` en `HUB_KEY_FINGERPRINT` uit
  de eigen koppeling en op `HUB_ENROLLMENT_TOKEN` een token van 47 tekens dat past op `^enr_[A-Za-z0-9_-]{43}$`.
  De dienst wordt in de test gestart met precies die omgevingswaarden, meldt zich aan met
  `POST /api/v1/services/enroll` (contract §3.3) en bevestigt met `GET /api/v1/services/self`; de Hub toont hem
  als gekoppeld. Daarna staat het token alleen als SHA-256 in de enrollment-opslag van de Hub, in geen andere
  tabel, journaal, recept, antwoord of log, en na de bevestiging geeft hetzelfde token 401 `invalid_enrollment`;
- tokenmarkering (acceptatie E): voor de dienst uit de koppelketen worden een gewone image-update en een
  `app.rollback` met `herstel_van` vóór `app.config` geweigerd, ook nadat het token verlopen en gebruikt is.
  In dezelfde testopzet, vergeleken met de build van vóór E: instanties van MediaGuard, MSO, Jelly Leon en Emby
  (bestaande adapters), my_house met alleen `HUB_URL` en een met de hand of vóór E gekoppelde eigen dienst hebben
  geen regel in de instantielijst, en een gewone image-update en een `app.rollback` met `herstel_van` met een
  bestaand recept hebben dezelfde uitkomst en dezelfde weigercode als vóór E (een bestaande blokkade zoals de
  Emby-bescherming blijft de reden, nooit de tokenmarkering); waar er vóór E geen blokkade was, worden precies
  dezelfde waarden teruggezet.
Geen geheimwaarde in test-/CI-uitvoer.
**Mutatie M-T4.** Verplaats ontsluiting vóór de signature/hash, laat de adapter een requestbody loggen, laat de
receptweigering vallen, haal de vormcontrole weg, sta een extra ref in de opvraag toe, vul `last4` in de nieuwe
opslag of neem `HUB_*` uit de parameters over. Elke variant maakt de betreffende test rood; de lektest bewijst haar
werking met opzettelijk gevulde opvang, nooit met lege tabellen. Zonder receptweigering wordt de fase vóór M2 rood
(de teller op de receptopslag is dan niet nul). Verander alleen de receptschrijver zodat hij opgeloste waarden
bewaart, terwijl alle andere controles blijven staan: de fase na M2 wordt rood, omdat zij het ontsleutelde recept
van de bereikte schrijver doorzoekt; de fase vóór M2 blijft weigeren. Pas de vorm van het appgeheim (43 tekens) ook
op het enrollment-token toe: de koppelketen wordt rood. Neem het type van een plek uit het ophaalantwoord, het
voorstel of het manifest in plaats van uit de eigen witte-lijstregel: de kruisverwisseling wordt rood. Markeer
elke instantie met een `HUB_*`-variabele of een token in haar configuratie, in plaats van alleen eigen invulling:
de proef met de bestaande adapters en de met de hand gekoppelde dienst wordt rood. Hef de markering op na verval of
gebruik van het token: de proef met het verlopen token wordt rood.

### 5. C-12-accountgegevens worden in elke vorm geweigerd

**Keuze.** Hub en executor gebruiken dezelfde gepinde woordenlijst en dezelfde accountcontextregels als de
manifeststandaard van appstore-en-fork, eigenaar ASF-15. Geen eigen aanvullende of versmalde Hub-lijst. De
C-12-uitbreiding van ADR-0031 staat sinds `a994c2a` in die bron (ADR-0023): het veld `accounts`; `INIT`, `LOGIN`
en `BASIC_AUTH` in `ACCOUNT_WORDS`; de aanmeldnamen `JUPYTER_TOKEN` en `PASSWORD` alleen als hele naam
(`LOGIN_NAMES`); en variant B: een geheim van de Hub in een omgevingsvariabele van een Custom App alleen onder een
geheimnaam die geen accountnaam is (anders `account_gegevens_verboden` of `secret_in_form`). De validatorpin van
deze repo (`ASF_COMMIT` in `.github/workflows/ci.yml`) wijst nog naar een oudere commit. In deelstap C nemen Hub
en executor dezelfde gepinde toets over als de validator in de CI: één pin, vóór gebruik opnieuw gemeten in de
bron, met een driftcontrole. Alleen een oudere validator importeren of alleen naar de direct omliggende sleutel
kijken voldoet dus niet. Variant B geldt ook voor de gemarkeerde kluisplekken van besluit 4.

Weigering geldt op het gehele oorspronkelijke manifest, na parameterinvulling, op de werkelijke vertaalde
payload en opnieuw vóór kluisontsluiting. Het betreft letterlijke gegevens, gewone parameters, `value_from`,
gegenereerde geheimen, kluisrefs, naam/waarde-paren, hashes, gebruikerslijsten en geneste/overgeërfde
accountcontext, inclusief tekstvormen die de standaard interpreteert. Een naamloos of onbekend vrij veld wordt
niet als veilig behandeld; besluit 6 weigert het. Een toegelaten transportvorm van een geheim maakt de accountplek
niet toegelaten. Een accountweigering is nooit een accepteerbare waarschuwing. Het beschrijvende `accounts`-veld
levert alleen eigenaarstaken; het wordt niet aan het kleine policy-metadata-object toegevoegd en geeft geen values.

**Alternatieven en reden.** Alleen `ADMIN_*` zoeken, alleen het manifest toetsen of generated secrets onder
accountnamen toestaan is verworpen: gewone parameters en geneste context omzeilen dat. Verschillende lijsten
per laag laten beleid uiteenlopen. Het leverings-/pinmechanisme voor dezelfde regels blijft M4.

**Bewijstest T5.** Eén gedeelde gepinde matrix van de eigenaar door validator, Hub-API en directe executor:
alle bovenstaande invoervormen en de C-12-regressies uit ADR-0031 worden geweigerd met
`account_gegevens_verboden`, zonder secretlookup/RPC. Daarbij horen de gevallen van ADR-0023: `INIT`, `LOGIN`,
`BASIC_AUTH`, `JUPYTER_TOKEN` en `PASSWORD` als hele naam, en een kluisplek in een Custom App-omgevingsvariabele
onder een accountnaam; onder een naam die geen geheimnaam is weigert dezelfde matrix met `secret_in_form`
(variant B). Een toegelaten niet-accountgeheim en gewone openbare instelling blijven als positieve controles
aanwezig. Ontbrekende/verouderde regelset of een pin die afwijkt van die van de validator geeft geen vrijgave.
**Mutatie M-T5.** Sla de hercontrole na invullen over, laat oudercontext weg of vervang de regelset door de oude
lijst (zonder ADR-0023): minimaal de daarbij horende concrete accountcase moet rood worden. Laat Hub of executor
een andere pin gebruiken dan de validator: de driftcontrole wordt rood.

### 6. Opslag en preview krijgen een witte lijst per app én versie

**Keuze.** Er bestaat alleen ondersteuning voor expliciet beoordeelde combinaties van catalogusapp, trein,
exacte versie, manifesthash/image-digests en TrueNAS-/ix-app-schemaversie. De latere C-stap stelt de eerste
concrete ondersteunde combinaties vast uit gepinde fixtures; dit ADR noemt geen ongecontroleerde versie als
ondersteund. Een onbekende versie of onbekend veld betekent **geen toestemming**, ook met `null`, `{}` of een
onschuldig lijkende naam. Geen generieke recursieve verbodslijst als vervanging van zo'n schema. Dezelfde lijst
is het eigen anker van de executor uit besluit 1: zij staat als beleidsbestand onder de `policy_hash` in beide
images en noemt per regel ook de toegelaten bronidentiteit, de volledige uitgeverssleutel, de toegelaten
kluisplekken en of de app een koppelbare eigen dienst is (`HUB_*`, besluit 4).
Een nieuwe toegelaten combinatie komt er alleen bij via een gezamenlijke release en uitrol van Hub- en
executor-image met dezelfde nieuwe lijst; zolang de twee niet overeenkomen, blijft uitvoering geweigerd
(policy-hash). Een nieuwe lijst voegt toe en behoudt de historische combinaties die nog nodig zijn voor terugzetten
(de vorige versie van een geïnstalleerde instantie, of een bewaard recept of checkpoint verwijst ernaar); zo'n
combinatie verdwijnt niet als bijwerking van een nieuwe release.

De witte lijst beschrijft typen, grenzen, betekenis, toegelaten opslagconfiguraties en één previewregel voor
ieder gezet veld. Bestaande ix-app-lijsten, hostpad-/datasetnaam-/ACL-weigeringen, verboden mounts en GPU-grenzen
blijven gelden. Voor catalogusapps dezelfde expliciete opslagbeoordeling, geen ruimere doorvoer via vrije values.
NFS en SMB blijven geweigerd, ook met kluisrefs, een exportpad zonder slash of verborgen configuraties.
Voor opening daarvan is een afzonderlijk ontwerp/besluit nodig met doelbinding, traversal, komma-injectie en
mountopties; E of de aanwezigheid van geheimtransport opent deze typen niet. `tmpfs_config.size` blijft een
strikt geheel getal van minstens 1; de bewuste keuze zonder bovengrens blijft behouden.

Preview en alle API-vormen gebruiken dezelfde toonfunctie. Elk gezet veld staat erin met getypte openbare
waarde of expliciete maskering; onbekend betekent weigeren, niet weglaten. Omgevingswaarden blijven altijd
verborgen. Geheime waarden worden niet in bewaarde parameters/preview/idempotentieresultaten opgenomen;
eigen cataloguswaarden worden na afloop volgens hun schema gewist. `command`/`entrypoint` blijven 501 tot het
ontworpen installatiescherm in 170/180 bestaat. Deze open punten uit S-P2-040 zijn verplicht in C en G:

| Punt | Besluit voor schema/toonfunctie | Bewijs in T6 |
|---|---|---|
| V1 | Een pad onder een geheime naam alleen openbaar bij expliciet toegelaten file/path/dir- of tls/ssl/cert-context. | Echt configuratiepad zichtbaar; padvormig geheim gemaskeerd. |
| V2 | UUID/hex met streepjes onder geheime context blijft geheim, ook als sleutel. | API-detail, lijst en opgeslagen eindtoestand maskeren dezelfde invoer. |
| V3 | `public` is alleen als eerste naamdeel een mogelijke openbare schemaregel. | `publication_token` blijft geheim; expliciet openbaar veld zichtbaar. |
| V4 | `envconfig`, `variables`, `vars`, `extra_vars` zijn omgevingscontext. | Alleen namen; geen waarde via object, lijst of paar. |
| V5 | URL-querygeheimen en webhookvelden maskeren volgens bestaande redactieregels. | Niet-geheime instelling zichtbaar naast de verborgen query-/webhookwaarde. |
| V6 | `seed_ratio` is uitsluitend als getypte openbare instelling toegestaan; geen algemene uitzondering voor `seed`. | Ratio zichtbaar, seed-geheim verborgen; paden met spatie/hexdeel alleen in bedoelde context. |
| V7 | Alle gevallen gebruiken echte gepinde manifest-/catalogusvormen en de echte API. | Dezelfde matrix via voorstel, lijst, detail, resultaat en duurzame opslag. |

**Alternatieven en reden.** Naamheuristiek met een algemene paduitzondering of alleen de recursieve denylist
is verworpen: beide kennen de betekenis van een vrij catalogusveld niet. Alles maskeren zou de gebonden diff
onbruikbaar maken. De witte lijst staat veilige getypte informatie toe en weigert de onbekende rest.

**Bewijstest T6.** Per daadwerkelijk ondersteunde combinatie één volledige geldige fixture; varieer elk veldtype
en voeg op elke toegelaten objectplek één onbekend veld toe. Onbekende versie, NFS/SMB en ACL blijven dicht;
bekende geldige opslag en grote geldige tmpfs blijven regressiecontroles. V1–V7 via echte API en opslag, niet
alleen `_toon`. Weigering en maskering worden afzonderlijk aangetoond.
Releaseproef: een Hub met een nieuwe combinatie in zijn lijst tegen een executor met de vorige lijst (twee
beleidskopieën): weigering op de policy-hash, nul kluisopvragen en nul schrijfaanroepen; na de gezamenlijke uitrol
slaagt de nieuwe combinatie en blijft de terugzetting naar de vorige combinatie toegelaten.
**Mutatie M-T6.** Laat onbekende velden/versies door, open NFS/SMB of zet de betreffende V1–V6-maskering uit:
iedere gerichte test wordt rood. Een kunstmatige bovengrens voor tmpfs maakt de positieve regressietest rood.
Laat de nieuwe lijst de vorige combinatie weg: de terugzetting in de releaseproef wordt rood.

### 7. Padtekst bewijst geen veilige grens voor symlinks in een image

**Keuze.** De bestaande weigeringen, waaronder `/var/run/secrets`, blijven staan. Een executor die alleen
TrueNAS-API-readback heeft, kan daarmee niet elk onderdeel van een containerpad tegen de image-rootfs
verifiëren. `realpath` op de ontwikkelhost zegt niets over dat pad in een NAS-image. Er komt hiervoor geen shell,
Docker-socket, extra hostmount of generieke uitvoeractie bij.

Voor nieuwe catalogusopslag wordt geen pad toegestaan op grond van alleen een tekstuele prefix of een
image-digest. Vereist bewijs is gebonden aan exact die digest(s), alle padcomponenten en de uiteindelijke
mounttopologie, inclusief ouder-symlinks, laagoverschrijvingen en veranderingen vóór mounten. Een offline analyse
van gepinde imagelagen kan ondersteunend bewijs leveren, maar bewijst op zichzelf geen onveranderlijkheid van
runtime-paden. Ontbreekt een controleerbare garantie voor de concrete mount, dan blijft die verruiming geweigerd.
De huidige API levert die algemene garantie niet; dat blijft een open capability, geen heimelijk geslaagde
preflight. De bestaande generieke controles blijven bestaan zonder claim van volledige symlinkveiligheid.

**Alternatieven en reden.** Alleen bekende symlinknamen blokkeren is onvolledig; alleen de laatste component
controleren mist een symlink in een oudermap. Zelf een NAS-shell of hostbestand raadplegen overschrijdt de grens.
Een algemeen bruikbaar runtime-bewijsmechanisme is open (M5); twijfel geeft geen ruimere opslagtoestemming.

**Bewijstest T7.** Lokale gepinde imagefixtures met een directe symlink, ouder-symlink, extra laag en
runtime-vervanging; het veilige geval heeft aantoonbaar alle vereiste bewijsvoorwaarden. Zonder die laatste
garantie weigert ook een normaal uitziend pad. Controleer nul NAS-schrijfaanroepen en nul nieuwe host-/shelltoegang.
**Mutatie M-T7.** Vervang de bewijsvoorwaarde door alleen prefixvergelijking of inspectie van de laatste component:
de respectieve ontsnappingsproef moet rood worden. Alleen fixtures inspecteren telt niet als NAS-validatie.

### 8. EX15 blokkeert image-only herstel na een migratie

**Keuze.** Manifest-/upgradecontext en het werkelijk uitgevoerde updateverleden worden onveranderlijk aan het
recept, doel en checkpoint gebonden. Hub én executor weigeren image-only `app.rollback` na een migratie, bij
`tag_only_rollback_safe: false` of bij een onbekende herstelbron. Bij een recept zonder (geldige) migratiecontext
geldt het besluit hieronder. Dit geldt ook voor een rechtstreeks ingediend voorstel dat de planner overslaat en
voor een catalogusrollback.

**Besluit over recepten zonder migratiecontext.** Het gebruikersbesluit van 2026-11-14 (KLEIN-85; VOORTGANG.md:
"terugzetten gaat altijd door; HARDE EIS bestaande apps terug te zetten") en EX15 botsen bij een recept zonder
migratiecontext. Geen bestaand recept en geen update buiten een plan draagt die context: `_app_update` kent het veld
niet en de journaaltabel `app_values` bewaart alleen `request_id`, app, versleuteld vak en tijd.

| Optie | Regel | Gevolg |
|---|---|---|
| 1 | Weigeren bij elke ontbrekende context. | Na F is geen bestaand recept en geen update buiten de keten meer via het platform terug te zetten; dat breekt KLEIN-85 voor bestaande apps. |
| 2 | Alleen weigeren als de context aantoonbaar een migratie of `tag_only_rollback_safe: false` noemt; ontbrekende context gaat door met een melding. | KLEIN-85 blijft heel, maar EX15 hangt af van de aanwezigheid van de context: een keten-update van ná F waarvan de context verloren of weggelaten is, gaat door. |
| 3 | Recepten van vóór deelstap F en van updates buiten de vertrouwde keten gaan door met een duidelijke melding. Recepten van updates die ná F via de vertrouwde keten liepen, dragen altijd migratiecontext en worden geweigerd als die ontbreekt, tegenstrijdig is of een migratie zonder veilige tag-terugval noemt (EX15). | KLEIN-85 blijft heel voor bestaande apps en voor updates buiten de keten; elke update via de keten is beschermd. Restrisico: een migratie bij een update buiten de keten wordt alleen gemeld. |

**BESLOTEN door regisseur (gebruiker afwezig), wordt de gebruiker voorgelegd in het eindoverzicht: optie 3.**
Het onderscheid komt nooit uit een veld van het terugzetverzoek. "Oud" en "buiten de keten" zijn een positief
vastgestelde herkomst, nooit de afwezigheid van een vastlegging. Elk recept heeft precies één van drie herkomsten:

- `oud`: het recept bestond bij de ingebruikname van deelstap F en staat in de eenmalige vastlegging hieronder;
- `keten`: de update liep via de vertrouwde keten (ondertekende context aanwezig en tegen het anker uit besluit 1
  gecontroleerd), met de migratiecontext;
- `buiten_keten`: een update ná F zonder die context.

Bij het bewaren van elk nieuw recept na F legt de executor zelf uitdrukkelijk `keten` (met migratiecontext) of
`buiten_keten` vast, in hetzelfde versleutelde vak, gebonden aan het `request_id`; een terugzetverzoek kan het niet
veranderen. De Hub legt voor zijn eigen updateverzoek in zijn eigen administratie dezelfde herkomst vast. Bij een
terugzetting beslissen Hub en executor elk uit hun eigen registratie, met dezelfde volgorde:

1. Een recept met zelfstandig geldige eigen herkomst `keten` of `buiten_keten`, vastgelegd bij dat recept zelf,
   is niet afhankelijk van de oud-verzameling. Zij controleren de verzegeling en de binding aan recept, app,
   instantie en oorspronkelijke update; `buiten_keten` gaat door met de melding, `keten` alleen met geldige
   migratiecontext (EX15). Verlies, onleesbaarheid of verschil tussen de exemplaren van de oud-verzameling
   verandert die eigen herkomst niet en blokkeert deze route niet, ook niet voor `app.update` met zo'n recept.
   Noemt de geldige, onderling gelijke oud-verzameling hetzelfde recept óók `oud`, dan is dat tegenstrijdig met
   die eigen herkomst: weigering. Een onleesbare of tegenstrijdige eigen herkomst wordt nooit alsnog `oud`.
2. Alleen een recept zonder eigen herkomst heeft de geldige oud-vastlegging hieronder nodig. Past zijn binding
   daar precies op, dan gaat het als `oud` door met de melding. Ontbreekt de vastlegging of is zij onbruikbaar,
   dan volgt eerst herstel; zonder herstel is uitsluitend de hieronder gebonden beheerdersbevestiging mogelijk
   voor een aantoonbaar recept van vóór F. Afwezigheid alleen bewijst nooit `oud` of `buiten_keten`.

Overige ontbrekende, onleesbare of tegenstrijdige herkomst is ONBEKEND: weigering met een vaste code, geen
rollback-RPC. Een ketenrecept van ná F waarvan de hele herkomstregistratie ontbreekt blijft geweigerd, ook met
een beheerdersbevestiging. De melding is een vaste waarschuwing in het antwoord, het journaal en één logregel,
zonder waarden, zoals de KLEIN-85-melding.

**Eenmalige vastlegging van bestaande recepten bij de ingebruikname van F.** De executor legt bij zijn eerste start
met de F-code, vóór hij een `app.update` of `app.rollback` over het `app.config`-pad uitvoert, alle dan bestaande
recepten eenmalig en duurzaam als `oud` vast:

- Geen wijziging van bestaande recepten: hij leest per recept alleen `request_id`, app en tijd uit `app_values`,
  gebonden aan de eigen instantieadministratie; hij ontsleutelt, herschrijft, verplaatst of verwijdert geen recept
  (vak, app en tijd blijven byte-gelijk). De vastlegging staat afzonderlijk en is met zijn eigen vault-sleutel
  verzegeld: de verzameling `request_id`'s met
  hun tijd, app en instantie, het aantal, de inhoudsvingerafdruk en het tijdstip van ingebruikname van F. Een
  recept waarvan een binding niet precies op de vastlegging past, is niet `oud`.
- De executor legt het tijdstip van ingebruikname van F zelf eenmalig en duurzaam vast, vóór enige F-uitvoering,
  afzonderlijk van de oud-verzameling en verzegeld gebonden aan zijn identiteit en de instantie. Dit tijdanker
  blijft bij verlies van de verzameling bestaan; de Hub bewaart een geauthenticeerde kopie. Een verzoek, herstart
  of beheerdersbevestiging kan dit tijdstip niet verschuiven. Een ontbrekend of ongeldig tijdanker moet uit de
  oorspronkelijke back-up worden hersteld; het huidige tijdstip of de huidige voorraad geldt nooit als vervanging.
- Fail-closed bij de eerste ingebruikname: verzameling en lokale markering "voltooid" worden in één transactie
  geschreven, met een consistente journaalgrens en zonder gelijktijdige update-/rollbackschrijvers. Tot deze
  eerste vastlegging en de vergelijking met de Hub voltooid zijn, begint geen F-uitvoering met recept. Een
  onderbroken transactie laat geen gedeeltelijke verzameling achter; alleen aantoonbaar nog onvoltooide eerste
  ingebruikname mag vanaf hetzelfde tijdanker en dezelfde oorspronkelijke journaalgrens worden hervat, vóór enige
  F-uitvoering. Een onderbreking na lokale voltooiing hervat uitsluitend de kopie en vergelijking met de Hub.
- Herhaalbaar na voltooiing: de verzameling blijft onveranderlijk; geen nieuwe inventarisatie bij een herstart
  of bij verlies, ook niet als er geen recepten met eigen herkomst meer over zijn. Een recept van na de
  oorspronkelijke grens komt er nooit in. Verlies raakt alleen recepten zonder eigen herkomst; recepten met
  zelfstandig geldige eigen herkomst volgen hun eigen regel. Nieuwe F-updates blijven hun herkomst atomair bij
  het nieuwe recept bewaren en omzeilen geen bestaande gate.
- Twee bewaarplekken: de executor bewaart de vastlegging en de Hub bewaart dezelfde verzameling als administratie,
  gekoppeld aan zijn eigen vóór F ondertekende update-/rollbackverzoeken ongeacht hun uitkomst. Bestaande
  administratie wordt niet herschreven. Beide kanten verzegelen hun exemplaar met hun eigen sleutel; geen
  vault-sleutel delen. Vóór gebruik controleren zij elk hun eigen zegel en vergelijken via de bestaande gepinde,
  geauthenticeerde verbinding de inhoudsvingerafdruk, het aantal, het tijdanker en alle recept-/doelbindingen van
  beide exemplaren. Verschil betekent: geen van beide geldt als waar zonder herstel; niet de nieuwste, de Hub of
  de executor automatisch laten winnen. Ontbreken van een exemplaar is een herstelbare storing, geen bewijs van
  een lege verzameling. De zelfstandige-herkomstroute blijft in beide gevallen beschikbaar.
- Beide exemplaren, hun voltooiingsgegevens, het afzonderlijke tijdanker, de bijbehorende Hub-administratie en
  de voor verificatie benodigde eigen sleutelmaterialen horen consistent bij dezelfde versleutelde back-upset,
  met gescheiden sleutelbewaring. Alleen een Hub-database-export dekt de executorvastlegging niet. Een back-up
  telt hiervoor pas na verificatie van de set, de zegels en een proefherstel met exacte bindingvergelijking.

**Verlies en herstel voor de eigenaar, zonder terminal.** De bestaande back-up- en herstelvoorziening uit
`docs/platform-v2/03_INSTALLATIE/I02_BACKUP_EN_RESTORE.md` (controle back-upbestand, geïsoleerd proefherstel,
app-consistente export en gescheiden sleutelbewaring) wordt hergebruikt; geen tweede back-upstelsel of nieuwe
generieke database-restoreactie. De vereiste bediening is onderdeel van de vrijgave van F/G, met UI-uitwerking in
de bestaande schermstappen. De huidige Hub-back-updekking en hersteltestregistratie zijn nog geen uitvoerbare
herstelknop voor deze nieuwe metadata; dit ADR claimt dat niet.

1. De Hub toont bij het betrokken recept "Herkomstadministratie ontbreekt" of "Herkomstadministratie verschilt",
   welke kopie ontbreekt/faalt, bron en meettijd, en de vervolgstap "Herkomstadministratie herstellen" bij Backups.
   De executorpagina toont dezelfde lokale storing en het eigen oordeel. Geldige eigen herkomst blijft bruikbaar;
   de UI toont dat per recept, zonder geheime waarden.
2. De eigenaar kiest in die herstelbediening een geverifieerde back-upset van dezelfde executor/Hub en instantie.
   Eerst worden de twee exemplaren, de oorspronkelijke voltooiingsgegevens, het tijdanker en de bijbehorende
   administratie geïsoleerd uit die set gelezen en met de eigen sleutelmaterialen geverifieerd. Beide kanten
   vergelijken de volledige oorspronkelijke bindingen, zegels en inhoud; de UI toont datum, bron, aantal,
   overeenkomst of concrete afwijking en wat zal worden teruggezet. Eén intact overgebleven exemplaar wordt
   alleen vanuit zo'n geverifieerde oorspronkelijke set hersteld, nooit blind tot waarheid verheven.
3. Na een gebonden beheerdersgoedkeuring via de bestaande herstelvoorziening wordt uitsluitend de ontbrekende
   herkomstadministratie hersteld, bij verschil worden beide exemplaren door de geverifieerde oorspronkelijke
   exemplaren vervangen. Geen nieuwe `oud`-leden, geen nieuwe tijden; geen appwaarden, journaalrecepten, nonces,
   latere eigen herkomstregistraties of appdatabases overschrijven. De activering van beide exemplaren is pas
   bruikbaar na duurzame opslag en onderlinge herverificatie; bij onderbreking blijft deze route in herstelstand.
   De UI toont daarna "Herkomstadministratie hersteld" met verificatietijd en auditverwijzing. Een aparte nieuwe
   goedkeuring voor het terugzetten van de app blijft nodig. Zo worden de oorspronkelijke bindingen exact terug
   beschikbaar en blijven bestaande recepten en hun vorige waarden/digest intact.
4. Een ontbrekende, onleesbare, verkeerde of onvolledige back-up geeft geen herstelbewijs. De UI toont de reden en
   biedt voor uitsluitend het onderstaande geval de per recept gebonden bevestiging; anders blijft het recept
   geweigerd met de concrete ontbrekende voorwaarde. Geen stil eindpunt zonder hersteluitleg.

**Alleen zonder herstel: gebonden beheerdersbevestiging voor een recept van vóór F.** Voor een leesbaar recept
zonder eigen herkomst waarvoor de oud-vastlegging niet te herstellen is, tonen Hub én executor wat zij zelf
kunnen vaststellen: recept-ID, receptvingerafdruk, app en instantie, het oorspronkelijke tijdstip uit hun eigen
journaal/actieadministratie tegenover het door de executor zelf vastgelegde tijdanker van F, en de ontbrekende
bewijsstukken. Geen tijd of herkomst uit het terugzetverzoek aannemen. Alleen als beide hun bindingen onafhankelijk
kunnen verifiëren, de tijdstippen overeenstemmen en het recept aantoonbaar strikt vóór F is gemaakt, verschijnt in
de Hub "Dit ene oude recept terugzetten met waarschuwing". Bij ná F, een gelijke of onbepaalbare tijd, een
ontbrekend tijdanker, tegenstrijdigheid of onleesbaar recept blijft deze mogelijkheid gesloten. Een ketenrecept
van ná F zonder registratie blijft dus geweigerd; ook een beheerder kan dat niet langs deze route vrijgeven.

Dit vraagt een uitdrukkelijke bevestiging door een beheerder in een levende beheerderssessie, als hoogste
risicoklasse R3 met menselijke goedkeuring van precies die diff. De bevestiging bindt uitsluitend dit recept en
zijn vingerafdruk, app, instantie, oorspronkelijke tijden, F-tijdanker, huidige doelversie/ETag, checkpoint,
policy-hash en de waarschuwing. Zij vervalt bij wijziging van een binding, verlopen sessie/goedkeuring of hergebruik;
de bestaande vervaltijd en eenmalige nonce blijven gelden. De Hub legt vóór uitvoering een auditregel vast met
beheerder, bindingen, verliesreden en bevestiging zonder waarden. De executor controleert zelf opnieuw de
ondertekende gebonden goedkeuring, de levende sessie volgens besluit 3, het eigen recept en tijdanker en alle
bestaande gates; zijn journaal koppelt uitkomst en waarschuwing aan dezelfde auditverwijzing. Zonder duurzame audit
en journaal geen uitvoering. AI, planner, dienst-token of algemene instelling kan deze bevestiging niet geven.

Na bevestiging wordt precies dat ene recept teruggezet volgens optie 3, met dezelfde vaste melding en exact de
vorige waarden en digest plus readback. De bevestiging maakt het recept niet blijvend `oud`, vult de verloren
verzameling niet opnieuw en geeft geen ander recept of volgende uitvoering vrij. Zij ontsluit uitsluitend dit
herkomstgeval; migratie-, checkpoint-, doel-, Emby- en geheimtransportgates blijven verplicht. Dit is een ontwerp
voor gebonden autorisatie bij de bestaande terugzetroute, geen nieuwe vrije R3-actie of algemene vrijgave.

**Aan de gebruiker voor te leggen bij optie 3.** Bij verlies eerst de verzegelde herkomstadministratie uit de
bestaande back-upvoorziening herstellen. Lukt dat niet, dan mag alleen een aantoonbaar recept van vóór F zonder
eigen herkomst na bovenstaande R3-beheerdersbevestiging van precies dat recept met waarschuwing worden teruggezet;
een recept van ná F zonder herkomst blijft geweigerd. Zelfstandig geldige eigen herkomst blijft onafhankelijk
bruikbaar. Dit hoort bij het bestaande regisseursbesluit en wordt niet als reeds door de gebruiker goedgekeurd
gepresenteerd.

Zo blijven bestaande recepten terug te zetten met de melding (HARDE EIS, KLEIN-85); optie 3 zelf verandert niet.

Een beheerder kan een weigering door de migratiegate niet wegklikken, ook niet met de bovenstaande
herkomstbevestiging. Die uitkomst verwijst naar `eigenaar_herstel`: de eigenaar moet
image en bijbehorende data/database als één herstelroute behandelen. Er wordt geen nieuwe R3-actie, database-
schrijfroute, snapshot-rollback of automatische data-overschrijving verzonnen. Tot die eigenaarsroute beschikbaar
en geverifieerd is blijft herstel geblokkeerd; R3 in de risicotabel is op zichzelf geen uitvoerbare capability.

Zonder migratie gaat de bestaande rollback alleen met passende geverifieerde checkpointdekking (`requires_backup`
in `policy/acties.yaml`) en nieuwe gebonden goedkeuring; bij een keten-recept van ná F bovendien met aantoonbaar
veilige context. Hij gebruikt precies de vorige waarden en controleert
vorige digest/versie en readback. Het besluit KLEIN-85 blijft gelden: de hercontrole van historische waarden
meldt overtredingen en blokkeert op zichzelf het terugzetten niet, en recepten van vóór F of buiten de keten
blijven terug te zetten (optie 3). Deze meldregel is geen vrijstelling van de aparte migratie-, doel-, checkpoint-
of geheimtransportgates (zoals de receptweigering van besluit 4); er wordt geen verborgen wijziging van die
meldregel gedaan.

Emby blijft onder alle namen beschermd, ook met approval. MediaGuard en de mediaservers blijven onder hun
bestaande strenge blokkades totdat de daarvoor bedoelde eigenaarsbesluiten en het upgradebewijs beschikbaar
zijn. Alle kijkgeschiedenis (gezien, hervatpunten, favorieten, beoordelingen, spoorkeuzes, gebruikers en rechten)
en MediaGuard-voortgang blijven beschikbaar; geen overstap zonder vóór/na-rapport per gebruiker en diens
uitdrukkelijk akkoord op verschillen. De oude installatie blijft terugval, de gebruiker verwijdert Emby zelf.

**Alternatieven en reden.** Alleen de planner laten weigeren is verworpen: een directe Hub-actie omzeilt dat.
Oude image starten en "hersteld" melden is verworpen: een gemigreerde database kan onverenigbaar zijn.
Een fictieve R3-restore lost geen ontbrekende eigenaarsroute op.

**Bewijstest T8.** Volledige keten én directe Hub/executor-verzoeken voor migratie waar/onbekend/tegenstrijdig,
onveilig tagherstel, checkpoint van ander doel, ontbrekende database of verlopen RPO: geen rollback-RPC.
Een veilige niet-migrerende testapp zet werkelijk de vorige waarden en digest terug. Bestaande KLEIN-85-proeven
voor overtreding, geen overtreding en hercontrolefout blijven aanwezig. Emby stop/update/uninstall worden ook
hernoemd en met approval geweigerd. Een gevulde checkpointfixture maakt ontbrekende database aantoonbaar.
Voor optie 3: een recept van vóór F (bewaard door de huidige code, zonder context; na de eenmalige vastlegging
`oud`) en een recept van een update buiten de keten na F (vastgelegd als `buiten_keten`) worden teruggezet met
precies dezelfde waarden en de vaste melding; vak, app en tijd van elk bestaand recept zijn vóór en na de
eenmalige vastlegging byte-gelijk. Een recept van een keten-update na F zonder context, met tegenstrijdige context
of met een migratie zonder veilige tag-terugval wordt geweigerd: geen rollback-RPC. Ook ONBEKEND en geweigerd, geen
rollback-RPC: een ketenrecept dat via de echte updateroute van Hub en executor is gemaakt en waarvan de test daarna
de hele herkomstregistratie verwijdert (bij de executor, bij de Hub en bij beide), een onleesbare herkomst, en een
recept met eigen herkomst dat ook in de geldige, onderling gelijke oud-vastlegging staat. Eenmalige vastlegging:
een onderbroken eerste transactie laat geen gedeeltelijk `oud` achter en tot voltooiing en vergelijking begint
geen F-uitvoering met recept; hervatten bewaart tijdanker en oorspronkelijke grens. Een herhaalde start na
voltooiing verandert de verzameling niet; een recept van na die grens is nooit `oud`. Verwijdering leidt nooit
tot herinventarisatie, ook niet als alle recepten met eigen herkomst inmiddels weg zijn. Een terugzetverzoek dat
zelf "buiten de keten", "oud" of een context meestuurt, verandert daar niets aan.

Verlies- en herstelproef via de echte Hub/executor-updateroute, samen groen met alle bovenstaande T8-negatieven:

- Verwijder alleen de oud-verzameling bij de executor, bij de Hub en bij beide; laat recepten, journaal en sleutels
  intact. Geldige eigen herkomst `keten` en `buiten_keten` volgt steeds haar eigen regel: veilige ketencontext
  herstelt, onveilige/ontbrekende migratiecontext weigert, buiten de keten herstelt met melding. Ook een update met
  zelfstandig geldige eigen herkomst blijft mogelijk, met alle bestaande gates. Verwijdering mag nooit in een
  algemene stop veranderen of een nieuwe oud-inventarisatie starten.
- Eén ontbrekend exemplaar, een ongeldig zegel, twee geldig verzegelde maar verschillende exemplaren en een
  afgebroken kopie-/herstelactivering geven geen automatische winnaar of `oud`. Geldige eigen herkomst blijft
  onafhankelijk; een werkelijk tegenstrijdig recept bij een geldige gelijke verzameling blijft geweigerd.
- Herstel via de beschreven eigenaarsbediening uit dezelfde geverifieerde back-upset maakt de oorspronkelijke
  bindingen exact terug beschikbaar: identieke leden, tijden, app-/instantie-/requestbindingen, aantal,
  inhoudsvingerafdruk, voltooiing en F-tijdanker in beide exemplaren. Vergelijk tevens oude én latere recepten,
  hun versleutelde vak, app en tijd vóór/na byte-gelijk; zet daarna de oude waarden en digest werkelijk terug met
  melding. Verkeerde instantie, gewijzigde bindingen, kapot zegel of ontbrekend onderdeel van de set weigert.
- Zonder herstel: een intact recept van vóór F zonder eigen herkomst weigert zonder de gebonden
  beheerdersbevestiging, en zet na precies die R3-bevestiging in een levende sessie dezelfde vorige waarden en
  digest terug met melding, auditregel en readback. Dezelfde bevestiging voor een ander recept, een gewijzigde
  receptvingerafdruk/app/instantie/diff, replay, verlopen sessie/goedkeuring, ontbrekende audit, ontbrekend tijdanker
  of een gelijke/onbekende recepttijd: geen rollback-RPC. Test de Hub- én de eigen executorcontrole afzonderlijk.
- Een ketenrecept van ná F zonder herkomstregistratie blijft geweigerd bij verwijdering bij de executor, de Hub
  en beide, ook zonder oud-verzameling en mét een beheerdersbevestiging; geen rollback-RPC. De UI biedt voor dit
  recept geen bevestigingsmogelijkheid en toont waarom. Na een bevestigde oude terugzetting blijft een tweede
  recept zonder nieuwe eigen bevestiging geweigerd. Geen algemene instelling of meegegeven tijd verandert dat.
**Mutatie M-T8.** Verwijder de zelfstandige migratiegate of vervang checkpointverificatie door "ID bestaat":
de betreffende directe weigertest moet rood worden. Verander één oude waarde/digest: de positieve hersteltest faalt.
Lees de herkomst van het recept uit het terugzetverzoek in plaats van uit het eigen vak, of behandel een
keten-recept zonder context als van vóór F: de weigerproef wordt rood. Weiger elk recept zonder context (optie 1):
de proef met het recept van vóór F wordt rood. Behandel een recept zonder herkomstregistratie als `oud` of
`buiten_keten` (de oude regel "zonder vastlegging = van vóór F of buiten de keten"): de proef met het ketenrecept
zonder registratie wordt rood. Laat de registratie bij het bewaren weg: de positieve terugzetting van het recept
buiten de keten wordt rood (ONBEKEND), zonder dat optie 3 verandert. Maak de eenmalige vastlegging bij elke start
of bij verlies opnieuw, verschuif het F-tijdanker of neem recepten van na de oorspronkelijke grens op: de
herstart-/verlies-/ná-F-proef wordt rood. Laat de vastlegging of haar herstel een bestaand of later recept
herschrijven: de byte-vergelijking wordt rood.
Verliesmutaties: "neem bij verlies alles als oud aan" maakt de ná-F-weigerproef rood; "weiger bij verlies alles"
maakt de positieve proef met zelfstandige eigen herkomst en de bevestigde vóór-F-terugzetting rood;
"bevestiging geldt voor een ander recept of voor een recept van na F" maakt de betreffende gebonden weigertest
rood. Laat een ongeldig/afwijkend exemplaar winnen, herstel andere oorspronkelijke bindingen of sla vergelijking
van beide exemplaren over: de verlies-/herstelproef wordt rood. Sla R3-goedkeuring, levende sessie, verval,
eenmaligheid of duurzame audit over, of laat de herkomstbevestiging een migratiegate opheffen: de betreffende
negatieve proef wordt rood. Deze mutaties worden pas in F/G uitgevoerd; hier zijn het ontwerpcriteria.

### 9. De afhankelijkheidslus wordt door begrensde leveringen doorbroken

**Keuze.** S-P2-050 → 060 → 070 → 080 → 090 is geen reden om ongebouwde garanties te simuleren. De door de
regisseur gekozen deelketens A–G krijgen ieder een concrete basis- en eindcommit, passende poorten, push,
CI op die eindcommit en onafhankelijke reviews. H0 is de genoemde basis; HA–HG zijn symbolische eindgrenzen,
geen bestaande hashes. De regisseur legt elke volle eindhash vast vóór de volgende deelopdracht en plant
geen andere schrijver in hetzelfde bereik. Het planbestand wordt in deze ontwerpstap niet gewijzigd.

| Deel en bereik | Naar voren gehaald en eigen resultaat | Blijft elders / vrijgavegrens |
|---|---|---|
| A, H0..HA | Dit ontwerp met besluiten 1–9, test-/mutatiematrix en contractmeldingen. | Geen code of statusverhoging; R-TECH en R-VEILIG, herstel/herreview waar nodig, daarna R-EERLIJK vóór B. |
| B, HA..HB | Uit 080 uitsluitend `catalogus.lezen`: scopehandhaving, gemeten ja/nee/onbekend, versheid en verdwenen versie; interop met echte `HubLezer`. Begrensd: trein, app en versie alleen in vaste patronen, geen vrije filters of zoektekst naar TrueNAS, een grens op metingen per dienst en tijd, en antwoorden uit een eigen gemeten voorraad met versheid in plaats van een TrueNAS-meting per aanvraag. | Route/schema eerst als M3 vastleggen; eigenaar-connector, unlink en algemene 080-acceptatie blijven bij 080. |
| C, HB..HC | Per app/versie schema voor opslag en preview (tevens het executoranker van besluit 1), V1–V7, parser/doelgrenzen en C-12-accountweigering. De aangevulde eigenaarsvalidator (in de bron sinds `a994c2a`) opnieuw meten; één pin voor validator-CI, Hub en executor (M4). | Geen kluisontsluiting; NFS/SMB en onbekende schema's blijven dicht. Symlinkbewijs is een harde capabilitygrens. |
| D, HC..HD | Echte plannerclient met alleen een eigen plan, actiestap en handmatige stap gescheiden, levende sessie per stap (besluit 3), bronvertrouwen met het eigen executoranker, manifest-/appstore-preview, installatie zonder nieuwe geheimcapability, container-only verwijderen, readback/incident en registerbinding. Uit 080 de voor deze installatie vereiste post-install-gate. | M1 en M3 zijn vastgelegd in §8.1–8.2. De implementaties, de bestaande gates en de hercontrole moeten bij installatie samenwerken. Bij ontbrekend bewijs blijft uitvoering dicht. |
| E, HD..HE | Uit 070 de volledige relevante keten voor gegenereerde appgeheimen en `HUB_*` volgens besluit 4 (koppelvelden), samen met ASM-24, doelbinding, de twee gebonden typen (appgeheim en enrollment-token) met hun vaste vorm, instantielijst, wisgedrag en afzonderlijk transport. Vanaf E weigeren Hub en executor elke update/rollback met recept op een instantie met kluisplekken. De acceptatie toont de gevolgen van de tokenmarkering: bestaande adapters en bestaande terugval worden niet gemarkeerd of afgesloten (besluit 4, T4). | Eerst M1–M4 oplossen; OIDC-client_secret-overdracht en eigen ADR blijven bij 070, geen automatische accountvoorziening. |
| F, HE..HF | Uit 090 geverifieerde app-checkpoints, duurzame registratie/verificatie, RPO en database-/snapshotdekking, `Approval.backup_checkpoint_id` en pre-update-gate voor update/rollback; EX15 met optie 3 van besluit 8. Noodzakelijke 060-gatehercontrole sluit aan op deze echte data. Besluit over de schaduwinstallatie van een app met kluisgeheimen (besluit 2) en, als het exportbewijs verifieerbaar is, opening van de updatevariant met handmatige export (besluit 3). | Geen vervanging van `verified_checkpoint` door een teststub. Ref-only recept (M2) vóór update/rollback met recept op een instantie met kluisplekken. Overige pool-/boiler-/back-upblokkades en bewijs van 060 blijven daar; externe uploadverificatie, echte accountproef en overige 090-acceptatie blijven bij 090. |
| G, HF..HG | Appstore → planner → echte Hub → echte executor → fake TrueNAS en terug. Positief/negatief T1–T8, V7, alle oorspronkelijke verplichte 050-tests, mutaties, volledige toepasselijke poorten en CI op HG. | Pas dan beoordeling van heel 050; resterende lokale bouwgaten nooit als alleen NAS-resttest presenteren. UI blijft bij 160/170/180 met ontwerp/review. |

Voor B betreft interop met de echte `HubLezer` de echte broncode van de planner, niet een eigen kopie van zijn
verwachtingen. De voor catalogus, scopes, transport of vertrouwensbewijzen benodigde tegenpartijwijzigingen
worden apart in de eigenaarrepo geleverd en gepind; een ontbrekende levering houdt alleen die capability dicht.
070/080/090 nemen bewezen deelresultaten over zonder dubbelbouw, maar behouden hun resterende taken en
eigen acceptatie. Nieuwe grenzen zijn geen afvinking van hun gehele werkpakketten.

Voor iedere bouwdeelstap blijven volledige ketens gelden: A-VERKEN → A-BOUW → R-TECH + R-VEILIG en waar
geraakt R-HARDE-EIS/R-MANIFEST → A-HERSTEL/herreview → R-EERLIJK. Deelstap A volgt de hierboven genoemde
ontwerpketen. Dat reviews nog volgen, blijft zichtbaar; dit ADR is nog niet aangenomen.
Een groene CI bewijst bestaande codecontroles, geen nog ongebouwde capability. Ontwerp is geen Sim-bouwbewijs.
Pas bij volledige bouw-/Sim-acceptatie en uitsluitend resterende echte NAS/account/hardwareproef wordt bewijs
`Bezig`, met `alleen NAS-test nodig` en de passende `NIET GEVALIDEERD (…)`. In A verandert geen evidence-status.

**Alternatieven en reden.** Wachten met alle benodigde bouwstenen tot ná 050 laat de lus bestaan.
Een altijd-groen checkpoint, namaak-Hub of kleinere acceptatie maskeert het probleem. Beide routes zijn verworpen;
de verplaatsing van concrete bouwstenen behoudt dezelfde volledige eindacceptatie.

**Bewijstest T9.** De regisseur/reviewer vergelijkt per deelbereik diff, echte tests, mutatie-uitvoer, pins en CI.
G vereist een positieve update met werkelijk via de productieroute gemaakt en geverifieerd app-checkpoint en
dezelfde update negatief zonder dat checkpoint; de verificatiefunctie en autorisatie worden niet vervangen.
G herhaalt de handmatige-stapketen van T3 (`app_native` en `pg_dump`): een beheerdersbevestiging of een
plannermelding alleen geeft geen checkpoint en geen `bijwerken`; alleen het door de Hub geverifieerde
exportcheckpoint uit F opent die variant.
Alle oorspronkelijke 050-negatieven blijven: EX47, data behouden bij uninstall, EX15, Emby en verdwenen versie.
**Mutatie M-T9.** Vervang in een tijdelijke tegenproef de checkpointverificatie door altijd geldig, de echte
Hub door een stand-in of verwijder een vereiste ketenschakel/negatief scenario. De negatieve integratietest of
expliciete controles op geladen productiecomponenten en verplichte scenario's moeten rood worden. Accepteer een
beheerdersbevestiging van `export` als checkpointbewijs: de negatieve `app_native`/`pg_dump`-update wordt rood.

## Uitvoering deel D (S-P2-050d, 2026-11-21, niveau N5)

Status: gebouwd en Sim-getest tegen contractconforme fakes. NIET GEVALIDEERD (echte NAS). De echte keten blijft
dicht zolang appstore en planner de §8.1/§8.2-aanvullingen niet leveren (zie meldingen hieronder).

- **Gedeelde controle.** `apps/policy/src/asm_policy/catalogbinding.py` leest de witte lijst `installaties` in
  `policy/catalogus.yaml` streng (onbekend veld, `..`, korte commit, lege digests of kluisplekken: geen beleid) en
  toetst `parameters.catalog_binding` van `app.install`: precies één regel voor bron, uitgever, app, versie,
  manifesthash, schema en validator; release, payload, digest en instantie moeten erbij passen; `vault_refs` leeg.
  Hub en executor gebruiken dezelfde toets; de executor ankert op zijn eigen `policy_hash`. Na uitvoering eist de
  executor een digest uit `app.image.query` (`repo_digests`) die in de release staat, anders een afwijking.
  De productielijst blijft leeg; de `policy_hash` verandert niet.
- **Hub.** `hub/catalog/plannen.py` verifieert zelf versie, item en bron bij de appstore en de recordhandtekening
  met de gepinde appstoresleutel, rekent de manifesthash na en zoekt de regel. Daarna maakt de Hub zelf het plan
  bij de planner met `catalog_request_sha256` en registreert plan-ID, ETag, binding en vervaltijd (tabel
  `catalog_plan`, migratie 0022). Routes: `POST /api/v1/catalog/plans/install`, `GET /api/v1/catalog/plans/{id}`
  en `POST /api/v1/catalog/plans/{id}/steps/{step}/propose`, alleen voor gebruikerssessies. Vóór voorstel,
  goedkeuring en uitvoering controleert de Hub plan en bewijs opnieuw. `POST /api/v1/actions` weigert een eigen
  `catalog_binding`. Na uitvoering meldt de Hub het stapresultaat met de eigen readback en registreert naam en
  digest; de status is `geinstalleerd_controles_open`, nooit gezond.
- **Herstel na R-VEILIG (S-P2-050d).** De Hub valideert het oorspronkelijke manifest zelf met een kopie van het
  gepinde schema (`hub/catalog/manifest-v1.schema.json`, `schema_sha256` van ASF_COMMIT; een regel met een ander
  schema geeft geen plan) en toetst de ingevulde parameters vóór de planneraanroep: alleen gedeclareerde
  `wizard`-/`dataset_picker`-parameters met het juiste type en zonder geheim (C-12). De regel noemt ook de bron-ID
  en het veldschema (`formuliervelden`); item, versie, record en actieve bron (`trusted_key_id`) moeten dezelfde
  bron en uitgeverssleutel noemen. De controles na installatie moeten gelijk zijn aan die uit het geverifieerde
  manifest. Bij aanmaak bewaart de Hub de canonieke stapinhoud; vóór voorstel, goedkeuring en uitvoering vergelijkt
  hij die, de vervaltijd, de planstatus en de voorgangers (een stap met voorganger blijft dicht tot er een eigen
  bevestiging is). Een tegenstrijdige image-readback is een afwijking. Terug naar 0021 bewaart een gevulde
  `catalog_plan` als `catalog_plan_bewaard`; opnieuw 0022 zet haar ongewijzigd terug.
- **Herstel na de tweede R-VEILIG-ronde (S-P2-050d).** De Hub draait nu de gepinde validator zelf: een letterlijke
  kopie van `appstore/manifest` op ASF_COMMIT in `hub/catalog/asf` (bytegelijkheid bewaakt via `BRON.json`). Het
  oorspronkelijke manifest moet nul fouten geven (schema én regels, zoals hostnetwerk zonder reden); elke ingevulde
  parameterwaarde gaat vóór de planneraanroep door de parametercontrole van die validator (bijvoorbeeld geen relatief
  pad). De vertaalde stap moet zelf de manifesthash van het record noemen; ontbreken is een weigering. Bij de
  readback is elke imagerij zonder digest en een actieve imagereferentie met een andere digest een afwijking.
  Antwoorden (lezen en idempotente herhaling) tonen van de controles alleen `id`, `soort` en `beschrijving_nl`.
  Migratie 0023 maakt databases uit de oorspronkelijke 0022 (zonder `stap_sha256`) weer leesbaar, laat registraties
  staan en zet oude open plannen op `opnieuw_voorvertonen`.
- **VERSIE 2.** Een aparte beheerdersselectie van bron en uitgever met eigen revisie (nu: de witte lijst onder de
  `policy_hash`). Een veldschema dieper dan het eerste niveau. Een eigen
  bevestigingsroute voor handmatige voorgangers. Een appstore-previewaanroep naast de planner. Kommagetallen in manifest of parameters (nu
  geweigerd door de canonieke JSON). Hostpoort in de registratie uit de volgende inventaris (nu `null` met reden).
  Bevestigingsroute voor de controles na installatie. Koppeling van latere acties aan de registratie (F/G).

## Uitvoering deel F (S-P2-050f, 2026-11-22, niveau N5)

Status: gebouwd en Sim-getest tegen contractconforme fakes. NIET GEVALIDEERD (echte NAS). Versie 1: de kern
(geverifieerd checkpoint, fail-closed pre-update-gate, EX15 met optie 3); de rest staat onder VERSIE 2.

- **Checkpoint.** Alleen een snapshot die het platform zelf maakte via de bestaande actie `zfs.snapshot.create`
  (adapters en gesimuleerde TrueNAS; geen OneDrive of andere externe dienst, die horen bij 090/100). Na een
  geslaagde readback legt de executor `request_id`, dataset, snapshot, `createtxg`, recursief en de journaalgrens
  vast (tabel `checkpoint`); zonder `createtxg` of bij een journaalfout blijft de snapshot staan, met waarschuwing
  `checkpoint_niet_vastgelegd`, en telt hij niet. De gedeelde regels staan in `asm_policy/checkpoint.py`
  (`CHECKPOINT_MAX_SECONDEN` = 3600, dekking per dataset, opslag uit `app.config`).
- **Hub.** `blokkades.verified_checkpoint` kiest het nieuwste eigen uitgevoerde snapshotverzoek met readback
  `aanwezig` en `createtxg`, hooguit een uur oud, ná het einde van de laatste eigen bijwerking/terugzetting van de
  app, waarvan de dataset (met recursief) alle datasets van de app uit de verse inventaris dekt. Anders
  `backup_checkpoint_ontbreekt` met reden (`dekking_onbekend`, `geen_passend_checkpoint`). `Approval.backup_checkpoint_id`
  bindt het id; een nieuwer checkpoint bij de uitvoering laat de goedkeuring vervallen (bestaand).
- **Executor (pre-update-gate).** Vóór de eenmalige goedkeuringsnonce en vóór elke schrijfaanroep, voor alle
  varianten van `app.update` en `app.rollback`: `checkpoint_ontbreekt` (niet in het eigen journaal),
  `checkpoint_verlopen` (ouder dan een uur of de app is daarna bijgewerkt), `checkpoint_afwijkend` (snapshot weg of
  andere `createtxg`) en `checkpoint_dekt_niet` (hostpad, ix-volume of `ix-apps/app_mounts/<app>` buiten de
  snapshot; andere opslagsoorten zoals NFS/SMB of een onbekend pad geven nooit dekking).
- **EX15, optie 3.** `parameters.upgrade` (`migrations`, `tag_only_rollback_safe`) volgt het manifest (§9) en maakt
  alleen strenger. De executor bewaart bij elke bijwerking en terugzetting in dezelfde transactie als het recept een
  verzegelde herkomst (`buiten_keten`, migratievlag, vertrekversie, checkpoint; tabel `recept_herkomst`). Bij de
  eerste start legt hij eenmalig de bestaande recepten als `oud` vast (verzegeld, met tijdanker en een anker in de
  geheimenmap; verlies leidt nooit tot opnieuw inventariseren). Terugzetten: een gemelde migratie vanaf het
  herstelpunt geeft `database_herstel_vereist` (geen rollback-RPC, geen snapshot-rollback); geen eigen herkomst en
  niet `oud`, of allebei, geeft `herkomst_onbekend`; `oud` en `buiten_keten` gaan door met `herkomst` in het
  antwoord en één logregel. De Hub weigert uit zijn eigen administratie hetzelfde (`database_herstel_vereist`,
  `herkomst_onbekend` als het herstelpunt geen eigen uitgevoerde wijziging van dit doel is).
- **Kluismarkering (050e)** blijft: een gemarkeerde instantie vraagt een recept met alleen verwijzingen.
- **Herstelronde (R-HARDE-EIS-1 t/m 6).** Dekking: `app.config`, de te herstellen waarden en de schrijfbare
  bind-koppelingen van de draaiende werklast, plus elke dataset die onder een gekoppeld pad is aangekoppeld; een
  lege lijst telt alleen bij een draaiende werklast zonder schrijfbare koppelingen, een onbekende koppelsoort nooit.
  Een recursief checkpoint legt per dataset de teruggelezen snapshot vast (tabel `checkpoint_lid`, alleen leden met
  de `createtxg` van de eigen snapshot, want ZFS maakt een recursieve snapshot in één txg) en telt alleen als de
  eigen `zfs.snapshot.create`-journaalrij van dat verzoek is uitgevoerd. Vlak vóór de schrijfaanroep leest de
  executor config, datasets en snapshots opnieuw; elke afwijking weigert zonder schrijven. Er is geen hold: het
  venster tussen die laatste lezing en de aanroep zelf blijft (VERSIE 2: ZFS-hold op het checkpoint). Terugzetten
  vraagt dekking van de recept-bestemmingen (Hub uit de readback `herstel_datasets`; recepten van vóór deze ronde
  alleen bij de executor). EX15 geldt voor elke imagewijziging: een doel-image of -catalogusversie die vóór een
  gemelde migratie draaide, geeft `database_herstel_vereist`. De executor schrijft na elke herkomst een anker
  (laatste `request_id`) in `secrets_dir/herkomst/`; ontbreekt die herkomst in het journaal, dan `herkomst_onbekend`.
- **VERSIE 2.** Herkomst `keten` met ondertekende migratiecontext uit de vertrouwde keten (050g); tot dan is elke
  update `buiten_keten` en wordt een migratie alleen geweigerd als de update haar zelf meldt (restrisico van optie
  3). Hub-kopie van de oud-vastlegging met vergelijking, herstelbediening en de R3-beheerdersbevestiging. Een RPO
  korter dan een uur uit het manifest; dekking van een database-export (alleen ZFS-snapshot nu); een checkpoint
  over meer datasets; symlinks in hostpaden (M5). Vertrekversie per verzoek bij de Hub voor een preciezere
  catalogusrollback (nu weigert de Hub na elke gemelde migratie van dit doel). De schaduwinstallatie van besluit 2
  en de updatevariant met handmatige export (besluit 3) blijven dicht.

## Open contractmeldingen en tekstvoorstellen

De regisseur laat de eigenaar de open meldingen in eigen opdrachten vaststellen en waar nodig de contractkopieën
bijwerken. Tot een open melding aantoonbaar is opgelost blijft de betrokken capability dicht. Onafhankelijke
deelstappen kunnen verder.

**M3 catalogusbeschikbaarheid · 2026-11-18 · BESLOTEN door regisseur.**
[Platformcontract §4.4](../platform-v2/PLATFORM_CONTRACTEN.md#catalogusbeschikbaarheid-m3) legt het bestaande
`GET /api/v1/catalog/availability` van de planner en zijn simulator vast, inclusief scope, velden, fouten en
meetgrenzen. De bouw van de Hub-route en de interopproef met de echte `HubLezer` horen bij S-P2-050b.

**M1 en M3 vertrouwde plannerinvoer · 2026-11-21 · BESLOTEN door regisseur.**
[§8.1 Bron- en doelbinding](../platform-v2/PLATFORM_CONTRACTEN.md#81-bron--en-doelbinding-van-appplannen-m1)
en [§8.2 Vertrouwde plannerinvoer](../platform-v2/PLATFORM_CONTRACTEN.md#82-vertrouwde-plannerinvoer-m3)
leggen de keuze voor de kleinste werkende vorm vast. Bronstand bij het besluit:

- `appstore-en-fork@5ece4a3`, `api/catalog.py::get_version` geeft het oorspronkelijke manifestobject,
  rapport en getekende record terug. `catalog/service.py::record_manifest` controleert de uitgevershandtekening
  en legt de entry-relatie na het tekenen vast. Voor uitvoerbaar bewijs voegt de appstore de entry- en versie-ID,
  het bronsubpad en de volledige uitgeversvingerafdruk aan hetzelfde record toe. Oude records zonder dit bewijs
  blijven onbruikbaar voor uitvoering.
- `jelly-leon-platform@1623cf9`, `lifecycle/api_plans.py::_bewaar`, `plan_view` en `lifecycle/planner.py::_vertaal`
  leggen manifesthash, plan en voortgang vast. De planneraanvraag heeft nog geen authenticeerbare catalogusbinding.
  §8.2 voegt een verzoekhash toe aan het bestaande Hub-dienst-JWT. De planner controleert die hash, valideert het
  manifest en koppelt de gecontroleerde bron en het doel aan het plan. De Hub controleert het geretourneerde plan
  tegen zijn eigen gegevens. Acceptatie volgt met T1–T3 en de directe executorproeven.

**M2 afzonderlijke geheime overdracht · 2026-11-21 · BESLOTEN door regisseur.**
[§8.3 Afzonderlijke geheime overdracht](../platform-v2/PLATFORM_CONTRACTEN.md#83-afzonderlijke-geheime-overdracht-m2)
neemt het tekstvoorstel letterlijk over en legt afgifte, sleutels, claim/crash, markering en ref-only recept vast.
De kleinste werkende vorm zonder nieuwe cryptografie of PKI vervangt de TLS-1.3-verbinding met wederzijdse
certificaten uit besluit 4. Die vroeg om nieuwe transportsleutels, certificaten en een eigen koppel- en
rotatieprotocol. De eigenschappen uit besluit 4 blijven gelden. Beide kanten zijn wederzijds geauthenticeerd met de
identiteiten die bij het koppelen door een beheerder zijn bevestigd: de executoridentiteit (§3.9) ondertekent de
opvraag, de gepinde JWT-sleutel van de Hub (§4.5) ondertekent de afgifte. Er is geen trust on first use en de
policy-sleutel wordt niet gebruikt. De waarden zijn versleuteld met HPKE (RFC 9180) uit de al gepinde
`cryptography`-bibliotheek, naar een sleutel die alleen voor die ene opvraag bestaat. Een HTTP-drager of proxy ziet
dus nooit klare tekst. Ontkoppelen of intrekken sluit de afgifte meteen. Bronstand bij het besluit:

- `ai-server-manager@267f5b2`, `hub/vault.py::Vault` (AES-256-GCM, vult `last4`; daarom een eigen app-opslag
  zonder `last4`), `hub/security.py::new_token` en `models.py::EnrollmentGrant` (alleen SHA-256),
  `executor/firststart.py` (identiteit) en `executor/hublink.py::verify_hub_jwt` (gepinde Hub-sleutels).
- `appstore-en-fork`: `manifest/translate.py` zet alleen `vault://app/<app_id>/<parameter>` en voegt nooit `HUB_*`
  toe; manifest en `accounts` blijven geheimvrij (C-12). Daar is geen wijziging voor nodig.

| Melding | Eigenaar en bron | Tekstvoorstel / benodigde vastlegging | Blokkeert |
|---|---|---|---|
| M1 bron- en identiteitsbinding | ai-server-manager en appstore-en-fork | Vastgelegd in §8.1. De appstore levert het complete catalogusbewijs. Hub en executor vergelijken bron, autorisatie en doel met hun eigen ankers. | D vereist de implementatie en de bewijstests. |
| M2 afzonderlijke geheime overdracht | ai-server-manager; contract §3.1, §3.2 en §8 | Vastgelegd in §8.3 (hieronder). Twee gebonden typen, afgifte na eigen verificatie, markering en ref-only recept. §3.1 en §3.2 zijn afgestemd: de executor vult `HUB_*` in, niet de vertaling. | E vereist de implementatie en de bewijstests. Het recept met alleen verwijzingen en de geheim-afhankelijke update/rollback horen bij F. |
| M3 vertrouwde plannerinvoer | ai-server-manager en jelly-leon-platform | Vastgelegd in §8.2. De Hub authenticeert de bron en de aanvraag. De planner bewaart de gecontroleerde binding bij het eigen plan. §4.4 bepaalt de catalogusbeschikbaarheid. | D vereist de implementatie en de bewijstests. De afzonderlijke kluisdoorgifte hoort bij E. |
| M4 eigenaarsregels C-12 | appstore-en-fork; contract §9/ASF-15; `manifest/rules.py::ACCOUNT_WORDS` en ADR-0016 W2/W3. | "De uitgebreide woordenlijst en contextregels uit ADR-0031 zijn één gepinde bron voor validator, Hub en executor. Accountgegevens worden vóór en na invulling in alle vormen geweigerd, ook via generated, value_from en vault_refs; ontbrekende of verouderde regels geven geen vrijgave." Lever reproduceerbare gedeelde testmatrix en regelset; leg pin-/driftcontrole vast. Geen eigen Hub-woordenlijst. Bronstand: de regels staan sinds `a994c2a` in de bron (ADR-0023, besluit 5 hierboven); `ASF_COMMIT` in `ci.yml` wijst nog naar een oudere commit. Hub en executor nemen in C dezelfde gepinde toets over als de validator in de CI en meten de bron dan opnieuw. | C en daarmee E/G. |
| M5 bewijsgrens imagepaden | ai-server-manager, afstemmen met manifeststandaardeigenaar; ADR-0030 besluit 6 en "Engine-regels buiten de policy_hash". | "Een toegelaten padtekst of gepinde image bewijst geen afwezigheid van symlinks. Nieuwe opslagtoestemming vereist controleerbaar digest- en mountgebonden bewijs voor elk padonderdeel en runtime-mutatie; ontbreekt dat, dan capability niet beschikbaar. Geen shell of Docker-socket als omweg." Het algemeen bruikbare bewijsmechanisme is ONBEKEND; eerst bronnen/capabilities vaststellen met `rg -n 'symlink|rootfs|mount_path' apps/executor/src apps/policy/src` in de repo en beoordeling van gepinde imagefixtures. | Verruiming van catalogusmounts in C/D; geen algemene veiligheidsclaim in G. |

Overige open grenzen: toegelaten echte bronconfiguratie, exacte eerste ondersteunde app-/versiecombinaties,
checkpointverificatie/RPO per ondersteunde app en de uitvoerbare eigenaarsroute voor migratieherstel worden in
B–F vastgesteld; niets wordt als gemeten NAS-waarde ingevuld. Engine-/schemaregels buiten de yaml-hash blijven
het bestaande restrisico uit ADR-0030: gelijke `policy_hash` bewijst geen gelijke uitvoercode. Voor uitrol zijn
bijpassende geteste Hub-/executor-images op digest vereist; geen nieuw engineveld zonder contractbesluit.

## Verificatie van deze ontwerpstap

Alleen dit ADR en verwijzingen in ADR-0030 en `docs/EXECUTION_REQUEST.md` horen bij de repo-diff, ook in de
herstelronde. De herstelronde voegt geen genummerd besluit toe maar werkt besluit 1–6, 8 (met het besluit van de
regisseur) en 9, de toetsen T1–T5, T8 en T9 en de meldingen M1–M4 bij; de toetsen blijven toekomstige acceptatie.
Herstelronde 2 werkt alleen bij: besluit 1 en 6 met T6/M-T6 (gezamenlijke uitrol van beide images), besluit 4 met
T4/M-T4 (receptproef in twee fasen rond M2, twee gebonden typen, gevolgen van de tokenmarkering), besluit 8 met
T8/M-T8 (positief vastgestelde herkomst en eenmalige vastlegging bij F; optie 3 ongewijzigd) en rij E van besluit 9.
Controleer relatieve links, besluiten 1–9 met alternatief/reden en test/mutatie, scope en ongewijzigde contract-,
policy- en evidencebestanden. Draai de bestaande contract-/manifest-/evidencecontroles uit P-ai-server-manager
voor het geraakte documentatiedeel en P-GIT; P-VEILIG, P-HARDE-EIS en P-INSTALLATIE zijn ontwerpchecklijsten.
De volledige code-/migratie-/image-/UI-poorten worden door de ongewijzigde CI herhaald op de gepushte ontwerpcommit.
T1–T9 zijn toekomstige acceptatie, geen in A uitgevoerde tests of grond voor nieuwe evidence.
