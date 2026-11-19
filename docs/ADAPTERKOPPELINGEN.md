# Koppelingen met bestaande apps

S-P3-020 levert de Hub-API en opslag voor de koppelingen uit ADR-0034. S-P3-040 voegt de openbare
MSO-probes toe. S-P3-050 voegt de leeskoppeling met my_house toe.

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
