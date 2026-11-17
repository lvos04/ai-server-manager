# ADR-0032 — Vertrouwde appplannen, doelbinding en kluisdoorgifte

Status: ontwerp ter review · 2026-11-17 · S-P2-050 deelstap A · niveau N4.
Basis: `e88a290c9ad5fef4acf498d05ad3414395a4fcb5` van `ai-server-manager`.
Contract: `contracts 1.3` met aanvulling C-12, ADR-0031.
Dit document legt bouwgrenzen en toekomstige bewijstests vast; het levert geen uitvoerende code of nieuwe
bevoegdheid. De contractmeldingen onderaan zijn tekstvoorstellen, geen aangenomen transportcontract.
Geen wijziging van `policy/*.yaml`, contracttekst, EVIDENCE of andere repos. B01-003, EX15 en EX47 worden in
deelstap A niet aangemaakt. Niets hiervan is op een echte NAS, met Emby of met echte accounts gevalideerd.

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
- `appstore-en-fork` op `e634cb0c8c8c752acf1082323fb127914fea7fb8`:
  `apps/api/src/appstore/api/catalog.py::get_version`, `preview`, `_app_id_bound`;
  `catalog/service.py::verify_stored_provenance`; `manifest/validator.py::validate_data`;
  `manifest/rules.py::ACCOUNT_WORDS`, `is_account_name`; ADR-0015, besluiten 1–5 en "Gevolgen".
  `valid` en `provenance_verified` zijn verschillende uitspraken. De laatste controleert opgeslagen bewijs met
  de eigen appstore-identiteit; dat is op zichzelf geen goedkeuring van een uitgever door de Hub.
- `jelly-leon-platform` op `90c192bad5590bf964ec8cada1bbffe6d297211d`:
  `docs/adr/ADR-0022-plannen-installatie-update-terugzetten.md`, "Besluit" en "Open punten";
  `apps/api/src/lifecycle/api_plans.py`, verzoekmodellen en planroutes. Een los `manifest_yaml` levert daar
  bewust geen vertrouwde geheime vertaling. De ketentest met Hub-/executor-stand-ins is geen volledige Hub-test.

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
`enabled: true` of `require_signature` zonder aantoonbaar geslaagde verificatie is onvoldoende. De strenge variant
vraagt zowel een exacte bronpin als een geldige uitgevershandtekening tegen de vooraf toegelaten sleutel.
Zonder beschikbaar bewijs van die combinatie blijft uitvoering dicht. Een wijziging/intrekking van deze selectie
maakt open voorstellen ongeldig; de planner en een catalogussynchronisatie mogen de selectie niet verruimen.

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
gebonden preview en `action_scope.parameters_sha256`; daarvoor is eerst de schemavastlegging van M1 nodig.
Geen vrije extra velden in het huidige `ExecutionRequest`. De executor verifieert deze ondertekende context zelf,
zijn eigen toegelaten bron-/schemabewijs en zijn verse doelmeting; alleen "de Hub heeft het goedgekeurd" volstaat niet.
Hercontrole gebeurt bij voorstel, goedkeuring en vlak vóór uitvoering/ontsluiting. Elke wijziging vraagt een
nieuwe preview en goedkeuring. Alleen een aantoonbaar afwezige catalogusversie geeft `version_unavailable`;
een onbereikbare, onleesbare of verouderde bron geeft onbekend en houdt de gate dicht.

**Alternatieven en reden.** Alleen `valid` vertrouwen of de eigen appstore-handtekening gelijkstellen aan een
uitgeversgoedkeuring is verworpen: beide bewijzen een andere eigenschap. Bronlocatie uit het plan overnemen is
verworpen: dat laat de aanvrager zijn eigen vertrouwensanker kiezen. De concrete bronconfiguratie en het
controleerbare uitgeversbewijs zijn open (M1); er wordt geen echte bron of sleutel verondersteld.

**Bewijstest T1.** Een gegenereerde testuitgever, vooraf gepinde bron en echte catalogusversie leveren één
goedgekeurd voorstel op. Vervang afzonderlijk bron, uitgeverssleutel, entry, `version_id`, hash, `app_id`, doel,
payload of `vault_refs`; trek de bron tussen goedkeuring en uitvoering in. Iedere variant weigert vóór
ondertekening/ontsluiting en vóór een TrueNAS-schrijfaanroep. Test ook ontbrekend bewijs en verdwenen versie.
**Mutatie M-T1.** Sla de bronpin-/uitgeverscontrole of één bindingsvergelijking over: de overeenkomstige weigertest
moet rood worden, met aantoonbaar bereik van die controle.

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

Omdat de publieke verwijzing geen instantie bevat, houdt de interne kluislookup óók de bevestigde doelinstantie en
kluisrevisie aan. Er is nooit een app-brede fallback. Meerdere instanties van dezelfde vaste app krijgen geen
toegang tot elkaars geheimen; tot die eenduidige opslagbinding bestaat wordt deze capability geweigerd.

**Alternatieven en reden.** Runtime-naam in het vaultpad zetten breekt de vaste identiteit bij een hernoeming.
Alleen de vaste app-id gebruiken deelt geheimen tussen instanties. Beide zijn verworpen. De precieze
representatie naast de huidige `target` en de opslagmigratie zijn open in M1/M2.

**Bewijstest T2.** Installeer met een afwijkende runtime-naam en controleer via de echte API dat alleen de juiste
geregistreerde instantie het verwachte testgeheim ontvangt. Test tweede instantie, naamhergebruik, ontbrekende
bevestiging, hostwissel en alle ongeldige verwijzingsvormen; geen kluislookup op een ander doel.
**Mutatie M-T2.** Vervang de registerbinding door naamvergelijking, laat een instantiecriterium weg of laat `..`
door de parser: telkens wordt de betreffende negatieve test rood.

### 3. De Hub orkestreert het plan zonder authenticatie te omzeilen

**Keuze.** Een geautoriseerde gebruikerssessie start de Hub-orkestratie met de bestaande rol-, CSRF- en
idempotentiecontroles. De Hub zoekt de actieve planner via het register en gebruikt per uitgaande aanroep een
nieuw kortlevend dienst-JWT met precies de planner als audience en diens `service_id`. Planner-service-tokens
geven uitsluitend de daarvoor vastgelegde leesscopes op de Hub; zij zijn geen gebruikerssessie en geen approval.
`apps/api/src/hub/routers/actions.py` wordt hiervoor niet versoepeld.

De Hub roept de bestaande preview-, lees- en resultaatroutes onder `/lifecycle/v1/plans` aan. Hij bewaart plan-ID,
ETag, manifesthash, vervaltijd en stapbinding en accepteert alleen vrijgegeven DAG-stappen waarvan voorgangers
met gecontroleerde readback zijn bevestigd. Elke stap doorloopt intern dezelfde proposalservice,
deterministische policy, actuele gates, preview en menselijke goedkeuring als een rechtstreeks voorstel.
De actor blijft herleidbaar tot de echte initiator; de planner kan geen gebruiker of risico claimen.
Een UUID5 van de planner dedupliceert alleen; hij vervangt geen goedkeuring, vervaltijd of nonce.

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
Voor plannen met geheimen ontbreekt nog een vertrouwde plannerinvoer in de tegenpartij; een door de Hub
meegegeven YAML-tekst maakt die ingang niet vanzelf vertrouwd (M3). Tot afstemming blijft deze planvorm dicht.

**Bewijstest T3.** Echte planner, appstore, Hub en executor met fake TrueNAS: installatie, terugmelding en
registratie. Test planner-token op gebruikersroute, ontbrekende gebruikersrol/CSRF/approval, gewijzigde plan-ETag,
geblokkeerde voorganger, `ready_for_install: false`, conflict, ontbrekende digest, replay en verlopen plan.
Controleer datasets en snapshots vóór/na verwijderen en geen tweede schrijfaanroep bij dubbele melding.
**Mutatie M-T3.** Schakel één gate, sessiecontrole, ETag-binding of readbackvergelijking uit: de eigen negatieve
test moet rood worden. Een teller bewijst dat de beoogde stap werkelijk is bereikt.

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
vastgesteld en interoperabel getest. Dit ADR verzint daarvoor geen reeds bestaand endpoint of extra envelopeveld.

De verplichte volgorde voor de latere implementatie:

1. De Hub maakt gegenereerde niet-accountgeheimen uitsluitend in de vault en bindt revisies en alle gemarkeerde
   plekken aan de preview. Parameteropslag en antwoorden bevatten alleen verwijzingen. Iedere ontbrekende,
   dubbele of extra markering weigert; een ref op een andere plek of als deeltekst wordt nooit opgelost.
2. De executor ontvangt eerst uitsluitend het normale ondertekende verzoek met de vastgelegde niet-geheime
   context. Hij controleert zelf handtekening, tijden, nonce, allowlist, schema, C-12, bron-/doelbinding,
   policy-hash, eigen risicoklasse, approval, checkpoints en verse precondities, vóór enige kluisopvraag.
3. Op de gepinde ophaalverbinding vraagt uitsluitend die executor precies de toegelaten referenties/revisies op,
   gebonden aan de hash van het **ref-only** ondertekende verzoek, request-ID, approval/nonce, doelinstantie,
   uitvoerderidentiteit en vervaltijd. De Hub controleert opnieuw de actuele autorisatie, intrekking en context.
   Een vrijgave vervalt uiterlijk bij de eerst aflopende verzoek-/approvaltijd, met maximaal 60 seconden
   ophaaltijd; zij is nooit overdraagbaar aan een andere executor of een volgend verzoek. De laatste lokale
   preconditiecontrole gebeurt na ontvangst, direct vóór de RPC; bij een gewijzigd doel wordt niet geschreven.
4. Een atomaire claim verhindert twee ontvangers. Bewaarde claimgegevens bevatten geen waarden of ophaalbaar
   antwoord. Transportreplay of herstart levert geen nieuwe waardeafgifte; bij onzekerheid nieuwe autorisatie,
   nooit blind herhalen. Vervallen approval of onbereikbare Hub betekent geen waarde en geen uitvoering.
5. Alleen direct voor de goedgekeurde `app.create`/`app.update` vervangt de executor de exacte gemarkeerde
   tekstplekken in een tijdelijke kopie. Het oorspronkelijke verzoek blijft ref-only. De uitvoer-adapter mag
   dit object niet via generieke request-/exceptionlogging laten lopen; ook het TrueNAS-clientpad is afgeschermd.
   Een capability voor een andere methode, bestemming of accountplek blijft geweigerd.
6. Bij succes, weigering, fout en time-out worden tijdelijke kopieën en transportbuffers zo snel mogelijk
   losgelaten en nooit gedumpt. Dit is geen bewijs dat alle geheugenkopieën in de runtime fysiek gewist zijn.
   Geen bodies, traceback-locals, ruwe TrueNAS-foutteksten of request-objecten in diagnostiek. Alleen vaste codes
   en aantallen naar het bestaande afgeschermde resultaatpad; bij onbekende uitkomst de bestaande stop/incidentweg.

Het bestaande versleutelde terugzetrecept uit ADR-0030 besluit 8 wordt niet verwijderd. Voor deze nieuwe
capability mogen opgeloste appgeheimen ook niet via `app.config` alsnog in dat recept of een configuratiehash
terechtkomen: bekende geheimplekken moeten vóór opslag/hashing terug naar gebonden referenties en revisies.
Zonder verliesloos en veilig recept wordt de update met deze capability geweigerd. Andere bestaande recepten
blijven onder het bestaande beleid; dit ADR claimt geen opschoning daarvan. Een rollback die deze nieuwe
geheimdoorgifte nodig heeft blijft dicht totdat ook zijn gebonden `app.update`-herstelpad aantoonbaar veilig is.

`HUB_*` wordt uitsluitend intern toegevoegd als de Hub de betrokken eigen dienst koppelt. my_house krijgt alleen
`HUB_URL`, bestaande adapters krijgen geen automatische enrollment. De korte levensduur en eenmaligheid van een
enrollment-token blijven gelden; het token volgt dezelfde afscherming. Bij een onzekere uitvoering geen nieuw
token op hetzelfde oude akkoord en geen automatische tweede installatie; eerst toestand vaststellen, zo nodig
oude token intrekken en een nieuwe gebonden handeling. OIDC-`client_secret`-overdracht blijft een eigen ADR in 070.

**Alternatieven en reden.** Geheim vóór ondertekenen in `parameters` zetten, de vault delen, een algemeen
`get_secret(ref)` aanbieden of plaintext via het gewone HTTP-kanaal sturen is verworpen: de eerste twee lekken
naar duurzame opslag/bevoegdheden, de laatste twee missen de noodzakelijke doel- en verzoekbinding. Alleen
maskeren bij loguitvoer is onvoldoende. Tot M1/M2 en de bewijstests zijn afgerond blijft `501 capability_unavailable`
voor deze kluiscapability gelden; de vermelding "oplossen bij samenstellen ExecutionRequest" uit 070 geeft geen uitzondering.

**Bewijstest T4.** Een per test willekeurig gemaakt geheim bereikt uitsluitend de juiste fake-TrueNAS-waarde bij
`app.create`/`app.update`. Onderzoek niet-lege vastgelegde requests, canonieke hashinvoer, signatures,
Hub-tabellen inclusief idempotentie, executorjournaal/recepten, routeantwoorden, events en logs. Nul treffers voor
de waarde en geen waarde-afgeleide hash zijn vereist. Herhaal bij rotatie, fout vóór/na RPC, timeout, herstart,
dubbele claim, foutcertificaat/pin, HTTP-downgrade, verkeerde executor, ontbrekende ref en ingetrokken approval. Voor afwijzingen
vóór ontsluiting is ook het aantal kluisopvragen nul. Geen geheimwaarde in test-/CI-uitvoer.
**Mutatie M-T4.** Verplaats ontsluiting vóór de signature/hash, laat de adapter een requestbody loggen, bewaar
een opgelost recept of verwijder de doel-/eenmaligheidscontrole. Elke variant maakt de betreffende test rood;
de lektest bewijst haar werking met opzettelijk gevulde opvang, nooit met lege tabellen.

### 5. C-12-accountgegevens worden in elke vorm geweigerd

**Keuze.** Hub en executor gebruiken dezelfde gepinde woordenlijst en dezelfde accountcontextregels als de
manifeststandaard van appstore-en-fork, eigenaar ASF-15. Geen eigen aanvullende of versmalde Hub-lijst. De
C-12-uitbreiding van ADR-0031 moet daar eerst gepusht, gecontroleerd en gepind zijn; de gelezen `ACCOUNT_WORDS`
bevat die uitbreiding nog niet. Alleen een oudere validator importeren of alleen naar de direct omliggende
sleutel kijken voldoet dus niet.

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
`account_gegevens_verboden`, zonder secretlookup/RPC. Een toegelaten niet-accountgeheim en gewone openbare
instelling blijven als positieve controles aanwezig. Ontbrekende/verouderde regelset geeft geen vrijgave.
**Mutatie M-T5.** Sla de hercontrole na invullen over, laat oudercontext weg of vervang de regelset door de oude
lijst: minimaal de daarbij horende concrete accountcase moet rood worden.

### 6. Opslag en preview krijgen een witte lijst per app én versie

**Keuze.** Er bestaat alleen ondersteuning voor expliciet beoordeelde combinaties van catalogusapp, trein,
exacte versie, manifesthash/image-digests en TrueNAS-/ix-app-schemaversie. De latere C-stap stelt de eerste
concrete ondersteunde combinaties vast uit gepinde fixtures; dit ADR noemt geen ongecontroleerde versie als
ondersteund. Een onbekende versie of onbekend veld betekent **geen toestemming**, ook met `null`, `{}` of een
onschuldig lijkende naam. Geen generieke recursieve verbodslijst als vervanging van zo'n schema.

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
**Mutatie M-T6.** Laat onbekende velden/versies door, open NFS/SMB of zet de betreffende V1–V6-maskering uit:
iedere gerichte test wordt rood. Een kunstmatige bovengrens voor tmpfs maakt de positieve regressietest rood.

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
`tag_only_rollback_safe: false`, ontbrekende/tegenstrijdige migratiecontext of onbekende herstelbron. Dit geldt ook
voor een rechtstreeks ingediend voorstel dat de planner overslaat en voor een catalogusrollback.
Een beheerder kan de weigering niet wegklikken. De uitkomst verwijst naar `eigenaar_herstel`: de eigenaar moet
image en bijbehorende data/database als één herstelroute behandelen. Er wordt geen nieuwe R3-actie, database-
schrijfroute, snapshot-rollback of automatische data-overschrijving verzonnen. Tot die eigenaarsroute beschikbaar
en geverifieerd is blijft herstel geblokkeerd; R3 in de risicotabel is op zichzelf geen uitvoerbare capability.

Zonder migratie kan de bestaande rollback alleen met aantoonbaar veilige context, passende geverifieerde
checkpointdekking en nieuwe gebonden goedkeuring. Hij gebruikt precies de vorige waarden en controleert
vorige digest/versie en readback. Het besluit KLEIN-85 blijft gelden: de hercontrole van historische waarden
meldt overtredingen en blokkeert op zichzelf het terugzetten niet. Deze meldregel is geen vrijstelling van de
aparte migratie-, doel-, checkpoint- of geheimtransportgates; er wordt geen verborgen wijziging van die meldregel gedaan.

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
**Mutatie M-T8.** Verwijder de zelfstandige migratiegate of vervang checkpointverificatie door "ID bestaat":
de betreffende directe weigertest moet rood worden. Verander één oude waarde/digest: de positieve hersteltest faalt.

### 9. De afhankelijkheidslus wordt door begrensde leveringen doorbroken

**Keuze.** S-P2-050 → 060 → 070 → 080 → 090 is geen reden om ongebouwde garanties te simuleren. De door de
regisseur gekozen deelketens A–G krijgen ieder een concrete basis- en eindcommit, passende poorten, push,
CI op die eindcommit en onafhankelijke reviews. H0 is de genoemde basis; HA–HG zijn symbolische eindgrenzen,
geen bestaande hashes. De regisseur legt elke volle eindhash vast vóór de volgende deelopdracht en plant
geen andere schrijver in hetzelfde bereik. Het planbestand wordt in deze ontwerpstap niet gewijzigd.

| Deel en bereik | Naar voren gehaald en eigen resultaat | Blijft elders / vrijgavegrens |
|---|---|---|
| A, H0..HA | Dit ontwerp met besluiten 1–9, test-/mutatiematrix en contractmeldingen. | Geen code of statusverhoging; R-TECH en R-VEILIG, herstel/herreview waar nodig, daarna R-EERLIJK vóór B. |
| B, HA..HB | Uit 080 uitsluitend `catalogus.lezen`: scopehandhaving, gemeten ja/nee/onbekend, versheid en verdwenen versie; interop met echte `HubLezer`. | Route/schema eerst als M3 vastleggen; eigenaar-connector, unlink en algemene 080-acceptatie blijven bij 080. |
| C, HB..HC | Per app/versie schema voor opslag en preview, V1–V7, parser/doelgrenzen en C-12-accountweigering. De aangevulde eigenaarsvalidator eerst gepusht en gepind. | Geen kluisontsluiting; NFS/SMB en onbekende schema's blijven dicht. Symlinkbewijs is een harde capabilitygrens. |
| D, HC..HD | Echte plannerclient, bronvertrouwen, manifest-/appstore-preview, installatie zonder nieuwe geheimcapability, container-only verwijderen, readback/incident en registerbinding. Uit 080 de voor deze installatie vereiste post-install-gate. | Bestaande echte gates blijven verplicht; noodzakelijke hercontrole wordt met de installatie getest, geen testoverride. Geheimplan zonder vertrouwde plannerinvoer blijft dicht; geen totaalafvinking. |
| E, HD..HE | Uit 070 de volledige relevante keten voor gegenereerde appgeheimen en intern toegevoegde `HUB_*`, samen met ASM-24, doelbinding, wisgedrag en afzonderlijk transport uit besluit 4. | Eerst M1–M4 oplossen; OIDC-client_secret-overdracht en eigen ADR blijven bij 070, geen automatische accountvoorziening. |
| F, HE..HF | Uit 090 geverifieerde app-checkpoints, duurzame registratie/verificatie, RPO en database-/snapshotdekking, `Approval.backup_checkpoint_id` en pre-update-gate voor update/rollback; EX15. Noodzakelijke 060-gatehercontrole sluit aan op deze echte data. | Geen vervanging van `verified_checkpoint` door een teststub. Overige pool-/boiler-/back-upblokkades en bewijs van 060 blijven daar; externe uploadverificatie, echte accountproef en overige 090-acceptatie blijven bij 090. |
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
Alle oorspronkelijke 050-negatieven blijven: EX47, data behouden bij uninstall, EX15, Emby en verdwenen versie.
**Mutatie M-T9.** Vervang in een tijdelijke tegenproef de checkpointverificatie door altijd geldig, de echte
Hub door een stand-in of verwijder een vereiste ketenschakel/negatief scenario. De negatieve integratietest of
expliciete controles op geladen productiecomponenten en verplichte scenario's moeten rood worden.

## Open contractmeldingen en tekstvoorstellen

Deze meldingen zijn **open**. De regisseur laat de eigenaar ze in eigen opdrachten vaststellen en waar nodig
de contractkopieën geregisseerd bijwerken. Dit document wijzigt contract 1.3 niet. Tot een melding aantoonbaar
is opgelost blijft de betrokken capability dicht; andere onafhankelijke deelstappen kunnen wel verder.

| Melding | Eigenaar en bron | Tekstvoorstel / benodigde vastlegging | Blokkeert |
|---|---|---|---|
| M1 bron- en identiteitsbinding | ai-server-manager; contract §3.1, §8, ASM-24; appstore `get_version`, `_app_id_bound` en provenance. | "Een geldige versie is pas uitvoerbaar na eigen Hub-brongoedkeuring en controleerbaar gepinde herkomst. De ondertekende autorisatie bindt entry, versie, manifesthash, bronpin, vaste app_id, bevestigde runtime-doelinstantie, schema, payload en gemarkeerde vault_refs. Wijziging laat goedkeuring vervallen. De executor controleert die binding zelf." Leg de exacte strikte parameters-/bewijsvelden en beschikbaarheid van het oorspronkelijke manifestobject vast; `target.app_id` niet stil herdefiniëren. | D voor volledige vertrouwde uitvoering; E/F voor nieuwe capabilities. |
| M2 afzonderlijke geheime overdracht | ai-server-manager; contract §3.1 en §8; 070 bouwpunt 2; `docs/EXECUTION_REQUEST.md`. | "ExecutionRequest, hashes en duurzame uitvoerregistraties bevatten uitsluitend verwijzingen en onveranderlijke revisies. Na eigen verificatie haalt alleen de bedoelde executor waarden eenmalig op via afzonderlijk wederzijds geauthenticeerd, versleuteld en gepind transport, gebonden aan verzoek, approval, doel, methode en vervaltijd. Geen gedeelde database of hoofdsleutel; geen geheimwaarde in foutpaden, journaal of recept." Leg protocol, sleutellevenscyclus, claim-/crashgedrag en ref-only herstel vast vóór uitvoering. | E en geheim-afhankelijke update/rollback in F. |
| M3 catalogusroute en vertrouwde plannerinvoer | ai-server-manager + jelly-leon-platform, ieder eigen opdracht; contract §4.4, §6.1 en §8; planner ADR-0022 "Open punten" en `api_plans.py`. | "Catalogusbeschikbaarheid is een gescopete verse meting ja/nee/onbekend voor exacte trein/app/versie; alleen nee betekent version_unavailable. De planner bindt vertrouwde catalogusidentiteit en manifesthash aan het plan en mag een losse manifestclaim niet tot geheime vertaling verheffen. Een planner-token is geen gebruikerssessie of approval." Exacte route, velden, fouten en authenticeerbaar bronbewijs door beide eigenaren vastleggen; het voorlopige pad in `hubread` is nog geen contract. | B voor definitieve route; D/E voor geheimhoudende plannen. |
| M4 eigenaarsregels C-12 | appstore-en-fork; contract §9/ASF-15; `manifest/rules.py::ACCOUNT_WORDS` en ADR-0016 W2/W3. | "De uitgebreide woordenlijst en contextregels uit ADR-0031 zijn één gepinde bron voor validator, Hub en executor. Accountgegevens worden vóór en na invulling in alle vormen geweigerd, ook via generated, value_from en vault_refs; ontbrekende of verouderde regels geven geen vrijgave." Lever reproduceerbare gedeelde testmatrix en regelset; leg pin-/driftcontrole vast. Geen eigen Hub-woordenlijst. | C en daarmee E/G. |
| M5 bewijsgrens imagepaden | ai-server-manager, afstemmen met manifeststandaardeigenaar; ADR-0030 besluit 6 en "Engine-regels buiten de policy_hash". | "Een toegelaten padtekst of gepinde image bewijst geen afwezigheid van symlinks. Nieuwe opslagtoestemming vereist controleerbaar digest- en mountgebonden bewijs voor elk padonderdeel en runtime-mutatie; ontbreekt dat, dan capability niet beschikbaar. Geen shell of Docker-socket als omweg." Het algemeen bruikbare bewijsmechanisme is ONBEKEND; eerst bronnen/capabilities vaststellen met `rg -n 'symlink|rootfs|mount_path' apps/executor/src apps/policy/src` in de repo en beoordeling van gepinde imagefixtures. | Verruiming van catalogusmounts in C/D; geen algemene veiligheidsclaim in G. |

Overige open grenzen: toegelaten echte bronconfiguratie, exacte eerste ondersteunde app-/versiecombinaties,
checkpointverificatie/RPO per ondersteunde app en de uitvoerbare eigenaarsroute voor migratieherstel worden in
B–F vastgesteld; niets wordt als gemeten NAS-waarde ingevuld. Engine-/schemaregels buiten de yaml-hash blijven
het bestaande restrisico uit ADR-0030: gelijke `policy_hash` bewijst geen gelijke uitvoercode. Voor uitrol zijn
bijpassende geteste Hub-/executor-images op digest vereist; geen nieuw engineveld zonder contractbesluit.

## Verificatie van deze ontwerpstap

Alleen dit ADR en verwijzingen in ADR-0030 en `docs/EXECUTION_REQUEST.md` horen bij de repo-diff.
Controleer relatieve links, besluiten 1–9 met alternatief/reden en test/mutatie, scope en ongewijzigde contract-,
policy- en evidencebestanden. Draai de bestaande contract-/manifest-/evidencecontroles uit P-ai-server-manager
voor het geraakte documentatiedeel en P-GIT; P-VEILIG, P-HARDE-EIS en P-INSTALLATIE zijn ontwerpchecklijsten.
De volledige code-/migratie-/image-/UI-poorten worden door de ongewijzigde CI herhaald op de gepushte ontwerpcommit.
T1–T9 zijn toekomstige acceptatie, geen in A uitgevoerde tests of grond voor nieuwe evidence.
