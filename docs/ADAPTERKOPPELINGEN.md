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

## MediaGuard

De bronkeuze volgt optie 1 van het regisseursbesluit van 20 november 2026. De adapter gebruikt
uitsluitend bewezen alleen-lezen bronnen. De lijst voor de onderzochte versie is leeg. De
Hub doet daarom voor MediaGuard geen bronverzoeken. De koppeling en het ontkoppelen blijven
beschikbaar in de Hub. Een ingevoerde sleutel blijft ongebruikt in de Hub-kluis. De bronrol en
de geldigheid van de sleutel zijn onbekend.

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
onbekende meting telt wel mee. Bij gelijke toestand krijgt de adapterreden voorrang. Bij
`healthy` geeft het totaal de oudste gebruikte meettijd. Anders geeft het de tijd van de
component die de toestand bepaalt.

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
bestaande statusrij en vermeldt een laatst bekende storing of beperking alleen in de toelichting.

Een my_house-contactproef telt één nieuwe gezondheidsmeting. Drie opeenvolgende metingen met
`unknown` of `down` openen één incident. Een gezonde meting sluit het. Een beperkte meting
onderbreekt een reeks vóór opening. Cataloguslezingen en idempotente herhalingen tellen niet mee.
Migratie `0021` bewaart de reeks per koppeling. Bestaande koppelingen beginnen op nul. Terugrollen
van `0021` verwijdert alleen de teller.
