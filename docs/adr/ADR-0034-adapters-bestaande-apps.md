# ADR-0034 — Leesadapters voor bestaande apps

Status: ontwerp ter review · 2026-11-19 · S-P3-010 · niveau N4.

Contract 1.3 met aanvulling C-12. De Hub projecteert de bestaande API's van MediaGuard, Media Source Optimizer
(MSO) en my_house op het leesmodel van §6. Elke app blijft eigenaar van zijn data, bestaande cliënten en
foutformaat. De ontwerpbesluiten hieronder sturen S-P3-020, S-P3-030, S-P3-040, S-P3-050, S-P3-150 en S-P3-300.

Bronnen: [platformcontract §2.3, §3.10, §6.2 en §8](../platform-v2/PLATFORM_CONTRACTEN.md),
[conformiteit C1.3-ASM-21](../platform-v2/CONTRACT_1.3_CONFORMITEIT.md),
[ADR-0031](ADR-0031-contract-1-3-aanvulling-c12.md) en [ADR-0032](ADR-0032-vertrouwde-appplannen-en-kluisdoorgifte.md)
besluiten 2 en 4. De routekeuze berust op de broncode en OpenAPI-exports van MediaGuard (`97410b9`),
MSO (`73d3a22`) en my_house (`d4cd6f6`). Het energiebesluit gebruikt het energiedomein van
home-control-hub (`ab668cc`). De planning in de delta-matrices beschrijft ook oudere versies.

## 1. Plaats, koppeling en opslag

Maak `apps/api/src/hub/adapters/` met `basis.py` en één module per app: `mediaguard.py`, `mso.py` en
`my_house.py`. De basis biedt ontdekken, gezondheid en items. Kies in S-P3-020 een aparte koppeltabel via een
toevoegende migratie met downgrade. Sla per koppeling het vaste app-ID, de bevestigde doelinstantie, de
gevalideerde basis-URL, de kluisverwijzing, de laatste vier tekens, de invoerdatum en de laatste geprojecteerde
meting met `observed_at` op. Hergebruik het versleutelde kluispatroon van `MonitorSource.geheim_ref` en
`monitoring/sources.py::poll_kuma`. De aparte tabel bindt bestemming, identiteit, rechten en kluisverwijzing
samen. `MonitorSource` heeft vrije opties voor monitoring en mist die binding. `registry.py::service_base_url`
kan een adres leveren voor een geregistreerde dienst. Controleer daarnaast dat de registratie en de
bevestigde runtime-instantie bij het vaste app-ID horen.

Een beheerder maakt, wijzigt, test en verwijdert de koppeling in de Hub-UI. De gebruiker maakt het beperkte
credential in de app en voert de sleutel of eenmalige koppelcode in de Hub-UI in. De Hub-kluis bewaart de
sleutel of het ingewisselde token versleuteld. De verwijzing heeft de tweeledige vorm van §3.10 en is gebonden
aan precies deze app en koppeling. De UI geeft als credentialmetadata alleen de laatste vier tekens en de
invoerdatum terug. De eenmalige koppelcode vervalt na inwisseling. Ontkoppelen wist de kluiswaarde en metingen
in de Hub. Een gewijzigde bestemming of instantie vraagt herbevestiging en nieuwe credentialinvoer.

De adapter controleert route, methode, doelbinding en least privilege vóór gebruik van het credential.
Elk verzoek gebruikt `outbound.validate_base_url` en `outbound.request` met begrensde tijd en antwoordgrootte.
Gebruik voor credentialverkeer HTTPS met geverifieerde serveridentiteit naar de bevestigde bestemming.
Weiger redirects, verboden adressen en een verbinding waarvan het bestemmingsadres niet aantoonbaar binnen
de goedgekeurde binding valt. Controleer dit bij het verbinden, ook bij veranderende DNS-antwoorden.
Een app-antwoord, deeplink of plannerinvoer mag nooit een nieuwe credentialbestemming bepalen. Bij een
ontbrekende doel- of transportcontrole blijft de koppeling onbruikbaar. De executorverbinding uit ADR-0032,
besluit 4, is een afzonderlijk ontwerp. Adaptercredentials blijven in de §3.10-namespace, buiten appplan,
executor, AI, logs, audit, events, foutteksten, verzoekhashes en duurzame verzoekpayloads. `HUB_URL` dient
als teruglink. Bestaande apps hebben geen enrollment in v1.

## 2. Leeslijsten en veldselectie

Elke rij geeft het toegestane HTTP-verzoek, het recht en de maximale veldselectie voor opslag en weergave.
Maak uit de toegestane, getypeerde velden een nieuw object, ook voor geneste objecten. Gebruik alleen begrensde
ID's, enumwaarden, aantallen, eenheden en tijdstempels. Plak bronfouttekst, ruwe antwoorden, diagnosevelden,
paden, adressen en laadgegevens nooit in log, audit, cache, incident, API of UI. Een deeplink gebruikt een
vast schermpad bij de bevestigde app of de expliciete deeplinkregel bij my_house. Valideer statuscode,
antwoordvorm en benodigde velden. Een geslaagde HTML-respons of onherkenbare JSON kan geen health opleveren.

### MediaGuard

Gebruik `X-Api-Key` met de sleutel `hub` en exact rol `viewer`. Controleer die rol en de scopes via
`/api/v1/auth/me` bij het koppelen en vóór hervatting na een credentialwijziging. De leesadapter gebruikt
alleen de leesrechten. De huidige scopetests (`apps/core/tests/test_api_keys.py` in MediaGuard) tonen dat
een viewer afzonderlijk `emergency_stop:on` kan krijgen. Die bevoegdheid behoort tot S-P3-600/S-P3-110.
Daar controleert de Hub expliciet `active: true` en behandelt 403 bij ontbrekende ondersteuning of terugrol
als onbeschikbaar. Noodstop uit is uitgesloten. Herzoek blijft gereserveerd tot BG-05.

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /api/v1/health` | Openbaar, zonder sleutel | `status`, `version` |
| `GET /api/v1/auth/me` | Sleutelcontrole, exact viewer | `role`, `scopes` uitsluitend voor rechtencontrole |
| `GET /api/v1/wanted` | Viewer | `total`, per item `id` als `wanted_id`, `kind`, `reason`, `status`, `updated_at` waar aanwezig. Vaste paginering |
| `GET /api/v1/encoding/jobs` | Viewer | `status`, `created_at`, `updated_at`; totalen per toestand met vermelding als de lijst begrensd is |
| `GET /connector/v1/discover` | Viewer, na bevestiging connectorversie | `app_id`, `source_version`, `schema_version`, leesrecht, `item_types`, `limits.max_age_s`, `timestamp_utc` |
| `GET /connector/v1/items` | Viewer, na bevestiging connectorversie en per type volgens de voorwaarden hieronder | `type`, `status`, `reason_code`, `snapshot_id`, `observed_at`, `total`, `next_cursor`; per item `id`, `observed_at` en de veldselectie hieronder |

#### Uitgesloten routes

Behandel de volgende routes bij bronversie `97410b9` als `capability_unavailable`. De tabel hierboven
is de leeslijst voor die versie. Laat een uitgesloten route of vervangende gegevensbron pas toe bij
positief bewijs voor de vastgestelde versie en configuratie, inclusief de bijbehorende negatieve proef.
Ontbrekende metingen uit een uitgesloten route zijn `unknown`.

| Uitgesloten pad | Reden en voorwaarde voor toelating |
| --- | --- |
| `/api/v1/status`, `/api/v1/attention`, `/connector/v1/health` | Een viewer-verzoek kan een opgeslagen keuze om een melding te verbergen wissen. Beproef elk pad afzonderlijk met een gewijzigde melding. Ook dan blijft de opgeslagen meldingskeuze intact. Voor incidenten geldt bovendien de volledigheidsproef hieronder. |
| `/api/v1/mediaserver/status` | Bij versleutelde gegevens zonder sleutelbestand kan de route een bestand aanmaken. Beproef dat het sleutelbestand na het verzoek afwezig blijft en dat ontbrekende contactmetingen `unknown` worden. |
| `/api/v1/backups` | De route maakt een ontbrekende map aan. Kies een uitlezing waarbij de back-upmap na het verzoek afwezig blijft en de meting dan `unknown` is. Projecteer uitsluitend `created_at` en `verified` van de laatste bruikbare back-up. |
| `/api/v1/downloads/health` | De route kan voor een live diagnose op de downloadclient inloggen, ook bij een beperkte Hub-projectie. Gebruik uitsluitend een bron die de reeds verzamelde statistiek uitleest zonder live diagnose of opslagwijziging. |
| `/api/v1/storage/forecast` | De route kan een nieuwe poolmeting starten en de poolstatus wegschrijven. Gebruik uitsluitend een reeds gemeten resultaat dat zonder die bijwerking kan worden uitgelezen. |

#### Mediaserverstatus

Zodra een veilige uitlezing is bevestigd, is `servers[]` per server leidend, ook bij een lege lijst.
Alleen als `servers` ontbreekt gebruikt de adapter de legacy-velden op het hoogste niveau voor één
server. Projecteer `server_id` indien beschikbaar, `kind`, een geldige weergavenaam als `label`,
`connected` en `hold.active`. Een ongeldige lijst wordt `unknown`. De veldselectie sluit
`sessions`, `hold.reason`, `actions`, `tests` en `last` uit van opslag, logs en weergave.
Kijkgedrag blijft bij de bestaande mediaservers.

Gebruik voor serverhealth uitsluitend een privacyveilige bron met een expliciet contactresultaat en
een geldige brontijd voor dezelfde server, binnen de strengste versheidsgrens uit §3. Ontbrekend
of verlopen contact wordt `unknown`, een verse expliciete contactfout wordt `down` en een vers
expliciet succes wordt `healthy`. Het legacyveld `connected` geeft alleen de verbindingsindicatie.
Zonder bevestigde contactmeting blijft serverhealth `unknown`, bij beide waarden van `connected`.

#### Connectorovergang en gegevensbronnen

S-P3-610 en S-P3-615 bevestigen per type het schema, de viewer-rechten, de neveneffectvrije uitlezing,
de meettijd en eventuele gelijkwaardigheid. Gebruik voor B04-002 dezelfde testinstallatie, meetperiode,
scope, filters en telling. Kies één bron per meetwaarde. Bij vergelijking blijven de testwaarden
gescheiden en telt alleen de gekozen bron mee. Gebruik de volgende veldselectie en toewijzing.

| Dataset | Vergelijking en bronkeuze |
| --- | --- |
| wanted | Vergelijk equivalent open wanted-bereik, het totaal, `wanted_id`, soort en reden bij gelijke filters en dezelfde meetpopulatie. Vergelijk toestand alleen bij aantoonbaar dezelfde betekenis. Schakel dan de hele wanted-meting over naar `items` van type `wanted`. Gebruik vóór die overgang de toegelaten legacy-uitlezing. |
| status | Vergelijk noodstop actief en sinds, aantallen wachtende, actieve en onopgeloste mislukte jobs en ongelezen waarschuwingen en fouten bij dezelfde definities en peildatum. In `97410b9` is alleen het connectoritem `status` kandidaat voor deze waarden. Gebruik een onafhankelijke neveneffectvrije testreferentie voor vergelijking zolang het legacy-pad is uitgesloten. |
| downloads | De historische uitkomsten over 7 en 30 dagen per brontype (`grabs`, `imported`, `failed`, `success_rate`) komen uitsluitend uit een toegelaten uitlezing van verzamelde statistiek en blijven tot die tijd `unknown`. Type `downloads` levert de actuele voortgang, toestand en wachten-op-import per item. Vergelijk actuele waarden alleen met een veilige referentie voor dezelfde wachtrij en peildatum. |
| AV1 | Legacy `/api/v1/encoding/jobs` blijft bron voor jobtotalen per toestand, met vermelding van een begrensde lijst. Type `av1_lanes` levert CPU- en GPU-banen met bezetting, slotlimieten, gewenste plaatsen en pauzestatus. Vergelijk baanmetingen alleen met een veilige referentie met dezelfde baan, eenheid en meettijd. |
| incidenten | Vergelijk bij volledige waarnemingen de incidenten over hetzelfde bronbereik per begrensde bron-ID, eigenaar, bekende oorzaakcode, ernst en aantal. Kies één volledige bron, met `incidents` als connectorbron. Legacy-incidenten zijn uitgesloten zolang de routebijwerking of het ontbreken van volledigheidsbewijs speelt. |

Voor een actuele incidentenlijst is afzonderlijk bewijs van bronvolledigheid nodig, inclusief de encoder
en de overige verwachte deelbronnen. Legacy `/api/v1/attention` kan bij een encoderfout een lege lijst
met nultellers leveren en geeft zelf geen volledigheidssignaal. Een onvolledige incidentenmeting is
`unknown`. Een bevestigde, verse en volledige connectorwaarneming met `status: ok` kan een lege lijst
als nul incidenten tonen. Beproef een falende encoder en een bereikbare encoder met nul incidenten
afzonderlijk. Geef verschillende waarden aan de historische uitkomsten, actuele downloads, jobtotalen
en baanslots in de overgangsproef. Toets behoud en enkelvoudige telling van de beschikbare waarden
en `unknown` voor ontbrekende of onvolledige metingen.

`status: ok` op de openbare probe is alleen liveness. Gebruik connector-health pas na bewijs voor die
route en alleen voor gelijkwaardige checks met `status`, `observed_at`, `reason_code`,
`checks[].name/status/observed_at` en de begrensde jobdetails uit contract §6. Vertaal verse bevestigde
onderdeelfouten naar `degraded` en expliciet offline onderdelen naar `down`. Ontbrekende of onvolledige
metingen worden `unknown`. Geef de noodstop als afzonderlijke beveiligingsstatus uit het toegelaten
statusitem. Zonder verse noodstopmeting blijft de stand onbekend. De leeslijst bevat geen `evidence`
of events. Een 401, 403, time-out, ongeldig schema of onverwacht antwoord leidt tot `unknown` voor
de geraakte gegevens. Een geconfigureerde connector blijft de enige bron na een fout of weigering.

#### Connectorpaginering

Vraag per type hooguit 200 items per pagina met ondoorzichtige, door de bron afgegeven cursors.
Controleer vanaf de eerste pagina het type, de versheid, `snapshot_id`, `observed_at` en het totaal.
Vervolgpagina’s horen bij dezelfde meting en melden dezelfde `snapshot_id`, dezelfde `observed_at`
en hetzelfde totaal. Zonder `snapshot_id` volstaat `observed_at` alleen als de bron daarmee aantoonbaar
eenzelfde momentopname over alle pagina’s garandeert. De uitzondering in contract §5 voor een gewone
tabel met een stabiele sorteersleutel geldt alleen voor tabellen die geen meting voorstellen.
Het gepinde `wanted` gebruikt een stabiele sleutel en de oudste meettijd, zonder momentopnamebinding.
Gebruik die connectorvariant uitsluitend wanneer één verse, volledige pagina het totaal dekt.

Publiceer een verzameling pas na de laatste pagina als het aantal unieke items het totaal dekt.
Bij 409 `snapshot_changed` of verschil in momentopname, meettijd of totaal, verwerp de volledige
deelverzameling en begin opnieuw zonder cursor. Bij uitputting van het retrybudget blijft de meting
`unknown` en is een eerdere waarde uitsluitend laatst bekend. Beproef twee consistente pagina’s,
herstart bij wisseling tussen pagina’s en bevestig dat pagina’s van de vervallen meting wegblijven.

### MSO

#### Openbare probes

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /healthz` | Openbaar, zonder sleutel | `status`, `version`; de router zit bewust buiten de schema-export |
| `GET /api/v1/setup/status` | Openbaar, zonder sleutel | `setup_required`, `completed`, `version` |

#### Pas na bewezen sleutelrechten

Een koppeling gebruikt een rolvrije machine-sleutel via `X-Api-Key`. Vóór de eerste beschermde uitlezing
verifieert de Hub een door MSO ondertekende rechtenverklaring met de effectieve scopes exact `{read}`
en een geldigheidsduur. De verklaring moet verifieerbaar gebonden zijn aan de aangeboden sleutel en
de bevestigde doelinstantie. Controleer sleutelbinding en handtekening lokaal tegen een vooraf voor
die instantie bevestigde verificatiesleutel. Accepteer alleen een verklaring waarvan de rechten voor
de sleutel onveranderlijk zijn gedurende de geldigheidsduur of waarvan de actuele rechten via een
afzonderlijke, vertrouwde bevestiging kunnen worden vastgesteld vóór de beschermde uitlezing. Bij
gewijzigde sleutel, rechten, bestemming, versie of verlopen bewijs vervalt de toelating tot
herbevestiging. Weiger sleutels met extra of onbekende rechten zonder beschermde uitlezing. Een
gebruikerssessie, CSRF-token of gebruikerswachtwoord wordt geweigerd.

Discovery geeft geen bewijs van de effectieve scopes. Zowel een sleutel met `read`
als een sleutel met `read` en `changes:approve` krijgt in `73d3a22` dezelfde `permissions: [read]`.
Sleutelbeheer en `/api/v1/auth/me` zijn voor deze machine-identiteit ontoegankelijk. Gebruik bij deze
versie alleen de openbare probes totdat MSO het benodigde bewijs levert. De beschermde datasets blijven
`capability_unavailable` en hun metingen `unknown`. Een geslaagd leesverzoek of een door de Hub-gebruiker
ingevulde scopenaam kan de vereiste MSO-bevestiging niet vervangen.

S-P3-040 en S-P3-230 toetsen dat een bewezen sleutel met uitsluitend `read` wordt aanvaard en een
sleutel met extra rechten vóór de eerste beschermde uitlezing wordt geweigerd. De volgende routes
komen pas in aanmerking na die controle en bevestiging van de versie, routebevoegdheid en antwoordvorm
volgens `mso/machine_keys.py::READ_ROUTES` en de OpenAPI-export.

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /api/v1/system/info` | Machine `read` | `version`, `schema_version`, `mode`, `paused` |
| `GET /api/v1/system/health` | Machine `read` | `status`, `components[].name/status`; geen `message`, `label` of `disk` |
| `GET /api/v1/overview` | Machine `read` | `mode`, `paused`, `health.status`, `generated_at`, `connectors.items[].id/configured/status/last_checked_at`; geen `recent_audit` of kosten |
| `GET /api/v1/usenet/failure-reasons` | Machine `read` | `items[].key` voor een lokaal bekende oorzaakcode |
| `GET /api/v1/mediaguard/compat` | Machine `read` | `checked_at` en `routes[].id/live` voor bekende capability-ID's |
| `GET /api/v1/changes?status=preview` | Machine `read` | `items[].id/status`; uitsluitend previews en een vaste link naar MSO |
| `GET /connector/v1/discover` | Machine `read`, na bevestiging connectorversie | `app_id`, `source_version`, `schema_version`, leesrecht, `limits.max_age_s`, `timestamp_utc` |
| `GET /connector/v1/health` | Machine `read`, na bevestiging connectorversie | `status`, `observed_at`, `reason_code`, `checks[].name/status/observed_at`, bekende `checks[].detail.reason_code` |
| `GET /connector/v1/items` | Machine `read`, na bevestiging connectorversie | `next_cursor`, per `connector` of `change_set`: `id`, `type`, `status`, `observed_at`, `reason_code`; toon alleen previews bij changes |

**Overgang S-P3-230.** Stap over op connector-discovery, health en de beschikbare itemtypen nadat de
installatie, schema's, rechten en versheid zijn bevestigd. De actuele connector biedt `connector` en
`change_set`. Behoud de toegestane bestaande routes voor aanvullende datasets. Gebruik per dataset één
pad en laat een connectorweigering niet door legacy overschrijven. `/api/v1/usenet/categories/diagnosis`,
`/api/v1/system/maintenance` en `/api/v1/costs/summary` bestaan, maar staan in de gelezen bron buiten
`READ_ROUTES` en hebben geen gelijkwaardig connectoritem. Zet ze op `capability_unavailable`. De
MSO-route-eigenaar moet een expliciet toegestane, neveneffectvrije leesroute leveren voordat S-P3-040
of S-P3-150 die dataset aanzet. Gebruik geen `refresh` en leid readiness nooit af uit HTTP 200 alleen.
De actuele bron bevat `/readyz`; compatibiliteit met oudere distribueerbare versies vereist apart bewijs.

Gebruik één geautoriseerde bron per check. Houd voor de contactcheck van een geconfigureerde
MSO-connector de legacy-uitlezing uit `/api/v1/overview` aan zolang connector-health of het
connectoritem `connector` het onderscheid tussen verse `auth_failed` en generieke `degraded`
verliest. Gebruik daarvoor alleen bekende ID’s van geconfigureerde connectoren, hun `status` en de
bijbehorende brontijd `connectors.items[].last_checked_at`. Bij ontbrekende bewezen sleutelrechten is ook
de legacy-uitlezing onbeschikbaar en de check `unknown`. Voorkom dat een samenvattende
connectorstatus de afzonderlijk gekozen contactcheck vervangt of dubbel meetelt.

Vertaal verse `offline` naar `down` en verse `auth_failed` naar `degraded` met
`reason_code: auth_failed`. Een verse generieke `degraded` blijft `degraded` zonder deze
redencode. Vers `healthy` blijft `healthy`. Een onbekende toestand, een verouderde meting of
ontbrekende meettijd geeft `unknown` volgens §3. Leg de overgang van deze check pas vast nadat de
gekozen connectorvorm dezelfde code en meettijd aantoonbaar behoudt. Beproef verse `auth_failed`,
generieke `degraded` en een verouderde meting via legacy, connector-health en het connectoritem.
Gebruik bij een fout alleen
`correlation_id` na vormcontrole en een bekende foutcode. Bij 401 of 403 meldt de Hub dat de
koppeling of het leesrecht onbruikbaar is en worden de geraakte gegevens `unknown`.

### my_house

Gebruik een door de gebruiker gemaakte eenmalige koppelcode met rol viewer. Inwisseling via
`POST /api/v1/pairing/redeem` met `code` en `device_name` en vernieuwing via
`POST /api/v1/clients/self/refresh` zijn credentialbeheer buiten de leeslijst. Controleer de
`client.role` uit het koppelantwoord vóór bewaren en verifieer de doelinstantie van het antwoord.
Bewaar alleen een geldig viewer-token, stuur het als Bearer-token en vernieuw het ruim vóór de
vervaldatum. Een verlopen of ingetrokken token of mislukte vernieuwing geeft een incident en `unknown`.

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /api/v1/health` | Openbaar, zonder token | `status`, `version`; dit is de databaseprobe |
| `GET /api/v1/system/status` | Viewer-token | `version`, `checks[].key/state`; geen vrije details |
| `GET /api/v1/homes` | Viewer-token | `id`, `name`, `timezone`, `active` |
| `GET /api/v1/homes/{home_id}/zones` | Viewer-token | `id`, `name`, `unit_status`, `online`, `mode`, `temperature.value/unit/quality/at/stale`, dezelfde selectie voor `humidity` |
| `GET /api/v1/homes/{home_id}/lights` | Viewer-token | Per groep/lamp `id`, `name`, `on`, `brightness`, `reachable`; per scène `id`, `active`, `group_id` |
| `GET /api/v1/homes/{home_id}/alerts` | Viewer-token | `id`, `severity`, `created_at` indien beschikbaar, aantal open meldingen |
| `GET /api/v1/homes/{home_id}/devices` | Viewer-token | `id`, `kind`, `online`, `last_seen`, `compatibility`, `lifecycle` |
| `GET /api/v1/system/settings` | Viewer-token | `lan_url`, `remote_url` alleen als kandidaat voor een gevalideerde gebruikerslink; `safe_mode`, `maintenance` |

Gebruik alleen bevestigde huis-ID's uit de huizenlijst. Geef alleen een deeplink terug nadat het adres
met `validate_base_url` is gevalideerd en de appbestemming is bevestigd. Voor het huisoverzicht
combineert de Hub de bovenstaande leesgegevens. Laat `/api/v1/homes/{home_id}/overview` buiten de
leeslijst omdat `routers/homes.py::overview` via `sync_worker_alert` bij een actief huis meldingen kan
aanmaken of sluiten en dat commit. Meld dit aan S-P3-050. De bron kan intern de gebruiktijd van het
viewer-token bijwerken als onderdeel van authenticatie. De adapter biedt geen bedien-, audit-,
diagnose-, back-up- of gebruikersroute aan.

my_house gebruikt de bestaande GET-routes. De leesconnector P3-03 vervalt. De aparte routes uit
P3-05 voor ondertekende acties en bewijs, en het terugkeerpad uit C1.3-MH-05, blijven buiten de
leesadapter. Zie de my_house-delta-matrix §11.6. Health: `ok` wordt `healthy`, `warn` wordt
`degraded`, `error` wordt `down` voor het onderdeel en ontbrekende of onbekende toestanden worden
`unknown`. Vertaal bij fouten alleen bekende `detail.code`-waarden naar vaste Hub-redencodes.

## 3. Versheid en onbereikbaarheid

De standaard voor elke meting van MediaGuard, MSO en my_house is 900 s. Gebruik de strengste grens
van de afnemer en de bron, per type of check. Respecteer ook bronverklaringen zoals `stale` en
afzonderlijke grenzen voor worker, back-up en sensormetingen. Neem de brontijd als `observed_at`.
Gebruik de ontvangsttijd alleen bij een meting waarvan de bron op dat verzoek de toestand zelf
vaststelt. Een gelezen cache, historisch interval, herhaalde fout of opnieuw getoonde waarde krijgt
geen nieuwe meettijd. Zonder bruikbare meettijd blijft de actualiteit `unknown`.

Bij onbereikbaarheid, ongeldige inhoud of geweigerde authenticatie wordt de geraakte toestand direct
`unknown`. Bij het verstrijken van `max_age` geeft de Hub `unknown`, redencode
`meting_verouderd` en de tijd van de laatste meting. Toon oude waarden uitsluitend als verouderd
en laatst bekend. De slechtste relevante check bepaalt health volgens §6: `healthy` < `unknown`
< `degraded` < `down`. Een expliciet gemeten storing telt mee zolang de meting vers is.

## 4. Energie en kosten

### Energie

Het energiedomein van **home-control-hub (B14)** is de enige directe lezer van de energiecijfers uit
my_house. Dit sluit aan op de bestaande bronconfiguratie `my_house`, `EXPECTED_METER_ROLES` en de
dekkingsmatrix. S-P3-300 bouwt één rechtstreekse client met een eigen viewer-koppeling en kluis. De
koppelreferentie wordt niet gedeeld met ai-server-manager. Bij de broncontrole zijn de vijf energieroutes
in `routers/energy.py` met `Auth` afgeschermd. Gebruik enkel de door die koppeling toegestane data.

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /api/v1/homes/{home_id}/energy/summary` | Viewer-token van B14 | Tijdvak, verbruik/teruglevering per expliciete rol, eenheid, bron, meetkwaliteit |
| `GET /api/v1/homes/{home_id}/energy/live` | Viewer-token van B14 | Actueel vermogen per expliciete rol, eenheid, meettijd, meetkwaliteit |
| `GET /api/v1/homes/{home_id}/energy/export?format=json` | Viewer-token van B14 | Alleen begrensde intervallen met rol, meettijd, meettype, waarde, eenheid en kwaliteit |
| `GET /api/v1/homes/{home_id}/tariffs` | Viewer-token van B14 | Geldig-vanaf, toegestane in-/uitvoertarieven en vaste dagkosten met eenheid |
| `GET /api/v1/energy/limits` | Viewer-token van B14 | Alleen de bronlimieten per bekende rol en eenheid. Een limiet is geen meting |

B14 kent een meterrol alleen toe als de bron die expliciet meldt. Ontbrekende rollen en verouderde
waarnemingen blijven onbekend. Daadwerkelijke meterrollen en dekking vereisen D14 en echte meting.

S-P3-150 bouwt de module `apps/api/src/hub/kosten/`. Voor B01-011 gebruikt deze module B14 als enige
bron voor stroom en de bijbehorende kosten na S-P3-300 en S-P3-310. Voor kosten van externe diensten
is de beoogde bron MSO `/api/v1/costs/summary`, uitsluitend wanneer de app-eigenaar deze met `read`
kan leveren. Bewaar daaruit alleen de periode, bron, categorie, bedrag, valuta en meetkwaliteit.
Tot dan is die post onbekend. Cloudbudget telt alleen mee uit een bestaande bron. Elk cijfer heeft
één bron, een tijdvak en `measurement_quality` (`measured`, `estimated` of `unknown`).
Vermeld de aanname bij een schatting. Tel een dubbele kostenpost uitsluitend bij de aangewezen
bron en log alleen een vaste oorzaakcode. Ontbrekende of verouderde cijfers blijven onbekend.
Leid zonder kalibratie geen wattage af uit CPU-gebruik. De aircometer meet de gedeelde buitenunit.
Verdeel deze kWh niet over binnenunits en verdeel NAS-verbruik niet over apps zonder afzonderlijke
meting. De boiler blijft alleen meten.

## 5. Acceptatie bij de bouwstappen

- Toets de volledige route- en veldprojectie tegen gepinde bronversies en lokale simulatoren,
  inclusief de vijf MediaGuard-datasets. Een schrijf- of bedienroute valt buiten iedere leeslijst.
- Toets op ontbrekende of te ruime rechten, ongeldige antwoorden, uitgezonderde velden, een
  ontbrekende serverlijst, gewijzigde bestemming, redirects en tijdsoverschrijding. Toon aan dat
  oude gegevens nooit actueel worden en dat de sleutel nergens buiten de kluis verschijnt.
- Toets bij overgangen dat weigeringen worden doorgegeven en elke dataset één bron behoudt.
  Bij B14 en B01-011 moeten ontbrekende metingen, veroudering en dubbele posten expliciet worden
  getest. De onafhankelijke veiligheidsreview toetst de leeslijsten en de grenzen van dit besluit.
