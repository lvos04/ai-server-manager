# Koppelingen met bestaande apps

S-P3-020 levert de Hub-API en opslag voor de koppelingen uit ADR-0034. S-P3-040 voegt de openbare
MSO-probes toe. S-P3-050 voegt de leeskoppeling met my_house toe. S-P3-030 toont welke
MediaGuard-metingen ontbreken zolang de onderzochte bronnen bijwerkingen hebben.

- De beheerder maakt een koppeling onder `/api/v1/adapterkoppelingen` en bevestigt het HTTPS-basisadres
  en de bijbehorende instantie uit de Hub-catalogus. De app-ID moet overeenkomen met die registratie.
- Voor koppelingen met een credential levert de beheerder dit aan via `X-Adapter-Credential`. De JSON-body
  bevat de bestemming. Hierdoor kan de gewone idempotentieregel de JSON-body vergelijken zonder
  het credential in de verzoekhash op te nemen. Gebruik voor iedere nieuwe invoer een nieuwe
  `Idempotency-Key`. Herhaling met dezelfde sleutel en body retourneert het oorspronkelijke antwoord.
  Bewaar het credential buiten verzoeklogs. De API geeft alleen de laatste vier tekens en de
  invoerdatum als credentialmetadata terug.
- Wijzig een koppeling via `PATCH /api/v1/adapterkoppelingen/{link_id}`. Een nieuwe bestemming,
  instantie of adresbinding vereist doelbevestiging. Voor een koppeling met een credential is ook
  nieuwe credentialinvoer vereist. De Hub verwijdert dan de vorige contactmeting. Een ingelogde
  gebruiker kan de lijst en het detail lezen.
- De beheerder voert de contactproef uit via `POST /api/v1/adapterkoppelingen/{link_id}/test`. De Hub
  gebruikt de vastgelegde leesroutes voor de gekozen app. Het verbonden adres moet binnen de
  bevestigde adresbinding vallen en het TLS-certificaat moet bij de ingestelde hostnaam passen.
  Doorverwijzingen worden geweigerd. Bij uitval is de contacttoestand onbekend. Een contactmeting
  ouder dan 900 seconden wordt `unknown` met `meting_verouderd`. Een openbare probe stelt alleen
  contact vast. De appgezondheid blijft `unknown` met `capability_unavailable` tot een appmodule
  de benodigde leescontrole levert. Lees de contactmeting via `GET /api/v1/adapterkoppelingen/{link_id}`.
- De beheerder ontkoppelt via `DELETE /api/v1/adapterkoppelingen/{link_id}`. De Hub wist de
  kluiswaarde en contactmeting in dezelfde transactie. Deze route stuurt geen verzoek naar de app.

Migratie `0017` voegt de tabel `adapter_link` toe. De downgrade wist de gekoppelde kluiswaarden
en de nieuwe tabel. De bestaande Hub-gegevens blijven behouden.

## Koppelen in de Hub

Open **Instellingen → Diensten → Bestaande apps**. De kaart vermeldt de installatienaam uit
de catalogus. Als beheerder controleer je het HTTPS-adres en de poort voordat je de bestemming
bevestigt en **Opslaan** kiest. Ontbreekt de installatie, vernieuw dan eerst de inventaris en
werk de appcatalogus bij. Een kijker of operator kan de koppelstatus en de laatste contactmeting lezen.

| App | Wat je in de app doet | Wat de Hub bewaart |
| --- | --- | --- |
| MediaGuard | Open als beheerder **Instellingen → API-sleutels**. Maak een kijker-sleutel zonder extra rechten. | De sleutel in de kluis. De geldigheid en de rol blijven onbekend zolang een veilige leescontrole ontbreekt. |
| Media Source Optimizer (MSO) | Het sleutelbeheer staat voor beheerders onder **Instellingen → Gebruikers**. Een machinesleutel voor de Hub mag uitsluitend het recht `read` hebben. | Alleen de bestemming voor de openbare verbindingstest. Sleutelinvoer is uitgeschakeld zolang de Hub het leesrecht niet kan verifiëren. |
| my_house | Open als beheerder de API-documentatie in de app onder `/api/v1/docs`. Kies bij de koppelcodes **POST /api/v1/pairing/codes**, zet de rol op `viewer` en het doel op `hub`. Neem de eenmalige code en de server-ID samen over. | Het kijker-token uit de inwisseling. De laatste vier tekens en de datum horen bij dat token. |

Na opslaan is het invoerveld leeg. **Testen** haalt de contactmeting op. **Ingesteld** betekent
dat de bestemming is bewaard. **Gekoppeld** vereist bevestigd contact met een bruikbare meettijd.
Bij een verlopen meting zie je **Verouderd** en de oorspronkelijke meettijd. Bij een weigering
of storing staat er een herstelactie bij de kaart. Een openbare MSO-test toont bereikbaarheid.

Met **Ontkoppelen** kun je eerst de gevolgen lezen en annuleren. Na bevestigen wist de Hub de
koppeling en de kluiswaarde. Trek bij MediaGuard de sleutel ook in de app zelf in. Trek bij
my_house de toegang van de Hub in de lijst met gekoppelde clients in.

## MediaGuard

Het besluit van 20 november 2026 geldt voor de algemene contactproef en de metingen
hieronder. De sleutel blijft in de Hub-kluis. Koppelen en contact testen
vergen voor deze metingen geen bronverzoek. De incidentketen controleert de bronrol bij het uitlezen,
volgens het aanvullende besluit van 21 november.

Lijst en detail tonen onder `mediaguard` de datasets `wanted`, `status`, `downloads`, `av1`
en `incidenten`, en de metingen `mediaservers`, `noodstop`, `opslagprognose` en `backups`.
Elk veld heeft status `unknown`, zonder meettijd, met reden `geen alleen-lezen bron`
(`geen_alleen_lezen_bron`). De contactproef geeft de gebruikelijke bevestiging. De
contacttoestand en gezondheid zijn `unknown`. Een oude contactmeting uit een eerdere Hub-versie
verschijnt uitsluitend als laatst bekende status met de oude meettijd. Een weggevallen
doelbinding geeft voor het contact de reden `doelbinding`.

Broninspectie van MediaGuard-commit `e1c121d4a29bff7228f56bd6ede5f9548ac00ae5`:

| Pad | Bijwerking in de bron |
| --- | --- |
| `/api/v1/health`, `/healthz`, `/readyz` | `app.py::SchemaRecovery` roept vóór de routes `db.py::Database.check_schema` aan. `schema.py::applied_versions` kan bij een aanwezige WAL het ontbrekende SQLite-hulpbestand aanmaken. Een lokale proef op een tijdelijke database bevestigt dit. |
| `/api/v1/auth/me`, `/api/v1/wanted`, `/api/v1/encoding/jobs`, `/connector/v1/discover`, `/connector/v1/health`, `/connector/v1/items` | `auth.py::principal_from_request` gebruikt `apikeys.py::authenticate`. `_touch` werkt de gebruiktijd bij en `_reject` schrijft een auditregel bij een ongeldige of ingetrokken sleutel. |
| `/api/v1/status`, `/api/v1/attention` | `attention.py::_hidden` kan via `forget` een eerder opgeslagen meldingskeuze wissen. |
| `/api/v1/mediaserver/status` | `mediaserver/api.py::status` gebruikt `_top` en `server_entry`. Het pad via `secrets_store.py::SecretStore._cipher` kan een ontbrekend sleutelbestand aanmaken. |
| `/api/v1/downloads/health` | `downloads/failures.py::downloads_health` gebruikt `downloads/failure_lookup.py::recent_client_errors`, dat bij qBittorrent kan inloggen. |
| `/api/v1/storage/forecast` | `storage_forecast.py::storage_forecast` kan via `_measure_pool` een poolmeting starten en opslaan. |
| `/api/v1/backups` | `maintenance/api.py::list_backups` gebruikt `_backup_dir`, dat een ontbrekende map aanmaakt. |

## MSO

Bevestig bij aanmaken of herbevestigen de catalogusinstantie en laat `X-Adapter-Credential` weg.
Credentialinvoer, gebruikersgegevens en een opgegeven scope worden geweigerd. Een oudere koppeling kan
de openbare contactproef gebruiken. Herbevestigen of ontkoppelen wist een eventueel oud kluisrecord.
Voor een openbare koppeling toont het detail een lege `laatste4` en `ingevoerd_op: null`.

De contactproef vraagt `GET /healthz` en `GET /api/v1/setup/status` aan zonder sleutel.
De bevestiging van `/test` bevat onder `probes`
`healthz` met `status` en `version`, en `setup` met `setup_required`, `completed` en `version`.
Een mislukte probe geeft voor dat onderdeel `null` en maakt de contactmeting `unknown`. Het incident
bevat een vaste Hub-redencode en, bij een bekende bronfoutcode, de vormgecontroleerde broncorrelatie.
De beschermde datasets blijven `capability_unavailable` en hun metingen `unknown`. Hiervoor is een
afzonderlijke stap nodig met de verifieerbare rechtenverklaring uit ADR-0034.

## Waarom ontbreekt een aflevering?

Een ingelogde kijker kan de vijf schakels opvragen via
`GET /api/v1/incidents/downloadketen/{wanted_id}`. Bij meerdere koppelingen van dezelfde app
kiest de aanroeper de instantie met `mediaguard_link_id` of `mso_link_id`. Een optionele
`mso_change_id` is een meegegeven verwijzing. De route legt geen verband tussen die wijziging
en de oorzaak. Dezelfde lees-URL kan opnieuw worden geopend.

Elke schakel vermeldt de eigenaar, de oorzaakcode en meettijd voor zover bekend, de reden
bij `onbekend` en een schermlink. De link gaat naar de bevestigde eigenaar. Bij een ontbrekende
of vervallen koppeling verwijst hij naar **Instellingen → Diensten**. Een storing bij de ene
eigenaar laat de beschikbare schakels van de andere eigenaar zichtbaar. De respons heeft
`Cache-Control: no-store`. De aanroeper kan een UUID meegeven in `X-Correlation-Id`. Zonder
die kop geeft de Hub een nieuwe UUID uit. De UUID staat ook in het antwoord.

MediaGuard levert de laatst opgeslagen diagnose. Een oude diagnose houdt haar oorspronkelijke
meettijd en krijgt de reden `meting verouderd`. Downloadgroepen en MSO-woordenlijsten
bevatten geen vastgestelde oorzaak voor een individuele aflevering. MSO heeft voor de
categorieën een eigen scherm. De bronrechten en de bekende sleutelboekhouding staan in
[ADR-0034, Incident- en downloadketen](adr/ADR-0034-adapters-bestaande-apps.md#incident--en-downloadketen-s-p3-075-versie-1).

## my_house

1. Maak als beheerder in my_house een koppelcode met rol `viewer` en doel `hub`. De huidige
   my_house-versie geeft deze code uit via de beheer-API `POST /api/v1/pairing/codes`. Gebruik de
   `server_id` uit het uitgifteantwoord om de instantie in de Hub te bevestigen.
2. Voeg in de Hub bij het aanmaken `server_id` toe aan de gebruikelijke JSON-body en stuur de
   code via `X-Adapter-Credential`. De Hub controleert de server-ID via de openbare identiteitsroute.
   Na inwisseling controleert de Hub opnieuw de server-ID, de rol, het doel en de eindige
   vervaltijd. De kluis bewaart alleen het uitgegeven token. De bevestiging bevat het
   koppelings-ID en de versie.
3. Test de koppeling via `POST /api/v1/adapterkoppelingen/{link_id}/test`. De Hub toetst de
   doelbinding vóór elk uitgaand verzoek en gebruikt het serverbewijs van my_house vóór
   tokengebruik. Het veld `my_house` bevat de databaseprobe, systeemchecks, instellingen
   en per woning de zones, verlichting, open meldingen en apparaten. Het overzicht wordt
   samengesteld uit deze leesroutes. Het aantal meldingen is begrensd zodra de bronlimiet
   van honderd is bereikt. Sensorwaarden zonder verse meting zijn leeg. De gebruikerslink
   verschijnt alleen als een LAN- of extern adres uit de instellingen overeenkomt met het
   bevestigde HTTPS-basisadres. Een herhaalde idempotente bevestiging behoudt de oorspronkelijke
   meettijd en doet geen nieuw bronverzoek. De detailroute beoordeelt de versheid per check op
   basis van de bronmeettijd en de geldigheidsgrens. Bij een verlopen check geeft de Hub
   `unknown` met `meting_verouderd` als die check de gezondheid bepaalt. Het afzonderlijk gemeten
   contact kan dan nog vers zijn.
4. De worker controleert elk uur of een token binnen dertig dagen verloopt. Een mislukte
   vernieuwing of geweigerd token maakt de status `unknown` en opent een incident. Een
   geslaagde leesproef bevestigt het herstel en sluit het incident. Bij een verlopen of ingetrokken
   koppeling of een aanhoudend mislukte vernieuwing maak je in my_house een nieuwe koppelcode met
   rol `viewer` en doel `hub`. Voer die via `PATCH` in en test de koppeling daarna opnieuw. Gebruik
   deze route ook als de bron het token heeft vernieuwd en het antwoord de Hub niet heeft bereikt.
   Bij een gewijzigde instantie bevestig je ook de nieuwe `server_id` en bestemming. Intrekken van
   de koppeling in my_house gebeurt vanuit my_house.

De adapter beperkt de woninggegevens tot de leeslijst van ADR-0034. De boiler wordt uitsluitend
gemeten en het energiedomein blijft bij home-control-hub. Ontkoppelen wist de kluiswaarde en alle
meetinhoud van de koppeling. Migratie `0020` scheidt de metingen van de bevestigingen en wist de
meetinhoud uit eerder opgeslagen bevestigingen. Terugrollen van `0020` wist de metingen. Terugrollen
van `0019` verwijdert ook de daarmee gemaakte my_house-koppelingen en kluiswaarden. Na ontkoppelen of
terugrollen levert een herhaalde testbevestiging `my_house: null`.

## Gezondheid van de binnenkant in de catalogus (S-P3-060)

De lijst en het detail lezen de opgeslagen adaptermeting voor de gekoppelde catalogusinstantie.
Ze gebruiken de bronmeettijd, de toestand en de redencode. Ze sturen hiervoor geen verzoek naar
de app. Zonder koppeling is de binnenkant onbekend. De toelichting verwijst naar Instellingen →
Diensten. MediaGuard heeft nog geen bewezen alleen-lezen gezondheidsbron. De openbare
MSO-probes meten bereikbaarheid. Voor beide adapters blijft de binnenkant onbekend.

De catalogus gebruikt de slechtste toestand in de volgorde `down`, `degraded`, `unknown`,
`healthy`. Een ontbrekende buitenkantmonitor telt niet mee. Een gekoppelde monitor met een
onbekende meting telt wel mee. Een gemeten stop of crash bepaalt de totaalstatus. Bij
andere gelijke toestanden krijgt de adapterreden voorrang. Bij
`healthy` geeft het totaal de oudste gebruikte meettijd. Anders geeft het de tijd van de
component die de toestand bepaalt. Bij een inventaris die niet beschikbaar is, blijft de laatst
bekende inventaristijd zichtbaar als de bepalende component zelf geen meettijd heeft.

| Buitenkant | Binnenkantmeting | Totaal bij draaiende app | Geval in `test_samenstelling_adapterprofiel` |
| --- | --- | --- | --- |
| Geen monitor | `healthy` | `healthy` | `None-healthy-healthy` |
| `healthy` | `healthy` | `healthy` | `healthy-healthy-healthy` |
| `healthy` | `unknown` | `unknown` | `healthy-unknown-unknown` |
| `unknown` | `healthy` | `unknown` | `unknown-healthy-unknown` |
| `degraded` | `unknown` | `degraded` | `degraded-unknown-degraded` |
| `down` | `degraded` | `down` | `down-degraded-down` |

Een ontbrekende, ongeldige of toekomstige meettijd geeft `unknown`. Een meting ouder dan haar
`max_age` geeft `unknown` met `meting_verouderd` en behoudt haar meettijd. Appdetail gebruikt de
bestaande statusrij en vermeldt een laatst bekende storing of beperking in de toelichting.

De catalogus leest de runtime-toestand en de meettijd uit dezelfde opgeslagen inventarismeting.
De instantie moet op dezelfde NAS precies één keer voorkomen met hetzelfde runtime-ID en
hetzelfde app-profiel. Bij een gewijzigde bestemming moeten de controles opnieuw meten.
De bron met de kortste resterende geldigheid bepaalt wanneer een gezonde status verloopt.
Lijstfilters, tellingen en detail gebruiken die grens ook tussen twee ophaalacties.

De API beslist in `hub.monitoring.health.evaluate` over de catalogusstatus. De tabel hieronder
geldt voor een draaiende app met gezonde meetwaarden. De drie voorwaarden gelden voor elke
gekoppelde bron. Alle rijen worden op lijst en detail getoetst door `test_groen_vereist_drie_bewijzen`.

| Laatste poging gelukt | Bronvervalgrens geldig | Instantie bevestigd | Catalogusstatus |
| --- | --- | --- | --- |
| Nee | Nee | Nee | Onbekend |
| Nee | Nee | Ja | Onbekend |
| Nee | Ja | Nee | Onbekend |
| Nee | Ja | Ja | Onbekend |
| Ja | Nee | Nee | Onbekend |
| Ja | Nee | Ja | Onbekend |
| Ja | Ja | Nee | Onbekend |
| Ja | Ja | Ja | Gezond |

De inventaris legt een onderbreking vast in dezelfde transactie als de momentopname.
Na afwezigheid of een bestemmingswijziging is een nieuwe broncontrole nodig. Bij my_house
bevestigt de adapter de identiteit van de gekoppelde server. Ook bij een verse bereikbaarheidsmeting
blijft een crash onbekend totdat de adapter de server kan bevestigen. Oudere catalogusrijen krijgen
bij de eerstvolgende inventaris een nieuwe grens voor die bevestiging. Een monitorfout na
gedeeltelijke opslag laat de oude bronmeettijd intact. Het scherm neemt de status uit het
API-antwoord over en trekt groen in bij een ophaalfout of een ontbrekende of verlopen `geldig_tot`.

| Laatste meting of ophaalpoging | Lijst, detail en onderdelen | Vaste regressieproef |
| --- | --- | --- |
| Dezelfde draaiende instantie, vereiste controles vers en gezond | Gezond met de oudste gebruikte bronmeettijd | `test_catalogus_toestandstabel[vers-emby]`, `test_samenstelling_adapterprofiel` |
| De bronvervalgrens is verstreken | Onbekend of Laatst bekend met de oorspronkelijke meettijd, ook op een open scherm | `test_catalogus_toestandstabel[verlopen-emby]`, `10-catalogus-gezondheid.spec.ts` |
| De laatste inventaris- of monitorpoging is mislukt | Onbekend, de vorige meting houdt haar tijd | `test_catalogus_toestandstabel[verversing_mislukt-emby]`, `test_uptime_kuma_koppelt_monitors_en_wordt_onbekend_bij_veroudering_of_ingetrokken_key` |
| Testkluis onbeschikbaar of fout na gedeeltelijke monitoropslag | Onbekend tot een geslaagde nieuwe poging | `test_mislukte_laatste_monitorpoging`, `test_kluisfout_na_gezonde_adapter_of_inventaris` |
| Instantie terug op hetzelfde adres na onderbreking, met of zonder catalogusupdate | Onbekend tot de bron de instantie opnieuw bevestigt | `test_terugkeer_andere_instantie` |
| Een oudere inventarismeting komt binnen na een vastgelegde afwezigheid | De oude meting kan een eerdere bevestiging niet herstellen | `test_vertraagde_inventaris_herstelt_geen_oude_bevestiging` |
| Gewijzigde gevulde poort of portal bij een draaiende of gecrashte app | Onbekend wanneer de bestemming strijdig is met de catalogus | `test_gewijzigde_bestemming_voor_catalogusupdate` |
| Een vereiste bron levert geen geldigheidsgrens, of een oud API-antwoord mist deze grens | Vanaf ontvangst Onbekend of Laatst bekend | `test_ontbrekende_of_ongeldige_bronvervalgrens`, `catalogus-gezondheid.test.tsx` |
| De schermverversing is mislukt, met gegevens in het geheugen | Laatst bekend vanaf de bronmeettijd. De apps tellen als onbekend | `catalogus-gezondheid.test.tsx` (503 bij een verse en een verlopen meting) |
| De eerste schermophaling loopt of mislukt | Laadtoestand of fout met een knop om opnieuw te proberen | `catalogus-gezondheid.test.tsx` (laden en initiële fout) |
| De nieuwste inventaris bevat een crash | Storing vanaf de crashmeting, ook vóór catalogusvernieuwing. Eerdere broncontroles zijn historisch | `test_crash_gaat_meteen_voor_op_eerdere_meting` |
| De instantie ontbreekt, heeft een dubbel runtime-ID of hoort bij een ander doel | Onbekend. De meting van de andere instantie telt nergens mee | `test_catalogus_toestandstabel` (verdwenen, dubbel, ander profiel en andere instantie) |
| De bronmeettijd ontbreekt, is ongeldig of ligt in de toekomst | Onbekend | `test_versheid_van_opgeslagen_adaptermeting`, `test_ongeldige_brontijd_geeft_geen_actuele_meting` |
| Een storing is verlopen | De laatst bekende storing en haar meettijd blijven zichtbaar | `test_verlopen_storing_behoudt_bronmeettijd_zonder_bronverkeer`, `catalogus-gezondheid.test.tsx` |

Een my_house-contactproef telt één nieuwe gezondheidsmeting. Drie opeenvolgende metingen met
`unknown` of `down` openen één incident. Een gezonde meting sluit het. Een beperkte meting
onderbreekt een reeks vóór opening. Cataloguslezingen en idempotente herhalingen tellen niet mee.
Migratie `0021` bewaart de reeks per koppeling. Bestaande koppelingen beginnen op nul. Terugrollen
van `0021` verwijdert alleen de teller.
Na herkoppeling zoekt de Hub het open probleem voor dezelfde catalogusinstantie op.
Dat omvat ook een storing die de incidentenworker nog moet verwerken. De eerste verse
gezonde meting sluit dat incident. De regressieproef is
`test_eerste_gezonde_meting_na_herkoppeling_sluit_incident`.
