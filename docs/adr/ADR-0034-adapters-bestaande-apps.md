# ADR-0034 — Leesadapters voor bestaande apps

Status: ontwerp ter review · 2026-11-19 · S-P3-010 · niveau N3.

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
| `GET /api/v1/status` | Viewer | `version`, `time`, `emergency_stop.active`, `emergency_stop.since`, `jobs.queued`, `jobs.running`, `jobs.failed`, `unread_notifications`, `attention.count/errors/warnings`, `health.complete`, `health.encoder` |
| `GET /api/v1/mediaserver/status` | Viewer | Per `servers[]`: `server_id`, `kind`, `label`, `connected`, `hold.active` |
| `GET /api/v1/attention` | Viewer | `count`, `errors`, per incident `items[].key/severity/count`, oorzaakcode uit de bekende broncodes |
| `GET /api/v1/wanted` | Viewer | `total`, per item `id` als `wanted_id`, `kind`, `reason`, `status`, `updated_at` waar aanwezig. Vaste paginering |
| `GET /api/v1/downloads/health` | Viewer | Per tijdvak uit `sources_7d` en `sources_30d`: `grabs`, `imported`, `failed` en `success_rate`, uitgesplitst naar brontype. Uit `causes` alleen `count` en uit `paused_items` hooguit het aantal |
| `GET /api/v1/encoding/jobs` | Viewer | `status`, `created_at`, `updated_at`; totalen per toestand met vermelding als de lijst begrensd is |
| `GET /api/v1/backups` | Viewer | `created_at`, `verified`; datum en integriteitsstatus van het laatste bruikbare resultaat |
| `GET /connector/v1/discover` | Viewer, na bevestiging connectorversie | `app_id`, `source_version`, `schema_version`, leesrecht, `item_types`, `limits.max_age_s`, `timestamp_utc` |
| `GET /connector/v1/health` | Viewer, na bevestiging connectorversie | `status`, `observed_at`, `reason_code`, `checks[].name/status/observed_at` en de begrensde jobdetails uit §6 |
| `GET /connector/v1/items` | Viewer, na bevestiging connectorversie | `type`, `status`, `reason_code`, `observed_at`, `total`, `next_cursor`; per item `id`, `observed_at` en de veldselectie hieronder |

Per server is de lijst `servers` leidend, ook bij een lege lijst. Alleen als `servers` ontbreekt gebruikt
de adapter `kind`, `label`, `connected` en `hold.active` op het hoogste niveau als één legacy-server.
Een ongeldige lijst wordt `unknown`. Gebruik alleen een geldige weergavenaam voor `label`. Buiten de
projectie blijven onder meer `sessions`, `hold.reason`, `actions`, `tests` en `last`. De Hub slaat die
velden nooit op, logt ze nooit en toont ze nooit. Kijkgedrag blijft bij de bestaande mediaservers.

**Overgang S-P3-610 en S-P3-615.** Gebruik de bestaande routes bij een bevestigde legacy-versie. Voor een
bevestigde connectorversie neemt `health` de gelijkwaardige gezondheidschecks over. Na verificatie van
schema, rechten, versheid en overeenstemming van de vijf datasets leest de adapter `items` voor
`wanted` (type, reden, toestand), `status` (noodstopstatus/tijd, job- en meldingaantallen), `downloads`
(toestand, voortgang, wacht op import), `av1_lanes` (cpu/gpu, bezetting, beschikbare en gewenste
plaatsen, pauzestatus) en `incidents` (eigenaar, oorzaak, ernst, aantal). Dit volgt de afgebakende
itemvormen in `connector/items.py`. Gebruik hooguit 200 items per pagina, vaste types en ondoorzichtige
cursors. Gebruik per dataset één pad en tel vergelijkingsresultaten nooit dubbel. Op de bestaande
mediaserverroute blijven de per-serverstatus en de veldenwitte lijst van toepassing. Houd de bestaande
back-upmetadata en noodstoplezing waar de connector iets mist. `evidence` en events worden hier niet
gepold. Een 401, 403, timeout, ongeldig schema of onverwacht antwoord leidt tot `unknown` voor de
geraakte gegevens. Gebruik geen legacy-terugval om een fout of weigering op een geconfigureerde
connector te omzeilen.

Opslagprognose blijft voorlopig `capability_unavailable`. De in S-P3-030 genoemde
`/api/v1/storage/forecast` vraagt een actuele poolmeting aan en schrijft de poolstatus terug
(`storage_forecast.py::storage_forecast` en `record_pool`). Voor een Hub-lezer is een uitleesbaar,
reeds gemeten resultaat zonder die bijwerking nodig.

Health: `status: ok` op de openbare probe is alleen liveness. Vertaal verse bevestigde
onderdeelfouten naar `degraded`, expliciet offline onderdelen naar `down`, en ontbrekende of
onvolledige metingen naar `unknown`. `connected: false` is `down` voor die mediaserver. Een actieve
noodstop is een afzonderlijke beveiligingsstatus. Zonder verse noodstopmeting blijft deze onbekend.

### MSO

Gebruik een rolvrije machine-sleutel met uitsluitend scope `read` via `X-Api-Key`. De actuele
`mso/machine_keys.py::READ_ROUTES` en OpenAPI-export bepalen welke bestaande routes deze sleutel
toelaten. Een oudere installatie zonder deze voorziening levert alleen openbare probes. Een gewone
MSO-sessie, CSRF-token of gebruikerswachtwoord wordt geweigerd als koppelmethode.

| Route | Recht | Toegestane velden |
| --- | --- | --- |
| `GET /healthz` | Openbaar, zonder sleutel | `status`, `version`; de router zit bewust buiten de schema-export |
| `GET /api/v1/setup/status` | Openbaar, zonder sleutel | `setup_required`, `completed`, `version` |
| `GET /api/v1/system/info` | Machine `read` | `version`, `schema_version`, `mode`, `paused` |
| `GET /api/v1/system/health` | Machine `read` | `status`, `components[].name/status`; geen `message`, `label` of `disk` |
| `GET /api/v1/overview` | Machine `read` | `mode`, `paused`, `health.status`, `generated_at`; geen `recent_audit` of kosten |
| `GET /api/v1/usenet/failure-reasons` | Machine `read` | `items[].key` voor een lokaal bekende oorzaakcode |
| `GET /api/v1/mediaguard/compat` | Machine `read` | `checked_at` en `routes[].id/live` voor bekende capability-ID's |
| `GET /api/v1/changes?status=preview` | Machine `read` | `items[].id/status`; uitsluitend previews en een vaste link naar MSO |
| `GET /connector/v1/discover` | Machine `read`, na bevestiging connectorversie | `app_id`, `source_version`, `schema_version`, leesrecht, `limits.max_age_s`, `timestamp_utc` |
| `GET /connector/v1/health` | Machine `read`, na bevestiging connectorversie | `status`, `observed_at`, `reason_code`, `checks[].name/status/observed_at` |
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

Health: `offline` wordt `down`, `auth_failed` wordt `degraded` met `reason_code: auth_failed`.
Onbekende toestanden en ontbrekende metingen worden `unknown`. Gebruik bij een fout alleen
`correlation_id` na vormcontrole en een bekende foutcode. Bij 401 of 403 meldt de Hub dat de
koppeling of het leesrecht niet bruikbaar is en worden de geraakte gegevens `unknown`.

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
