# Koppelingen met bestaande apps

S-P3-020 levert de Hub-API en opslag voor de koppelingen uit ADR-0034. S-P3-040 voegt de openbare
MSO-probes toe. De koppelcode voor my_house vereist eerst de
inwisseling uit S-P3-050. Tot die tijd antwoordt de Hub met `capability_unavailable` op die koppeling.

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
  gebruikt alleen de openbare leesprobes voor de gekozen app. Het verbonden adres moet binnen de
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
