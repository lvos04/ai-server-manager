# Koppelingen met bestaande apps

S-P3-020 levert de Hub-API en opslag voor de koppelingen uit ADR-0034. De appmodules voor beschermde
uitlezing volgen in S-P3-030, S-P3-040 en S-P3-050. De koppelcode voor my_house vereist eerst de
inwisseling uit S-P3-050. Tot die tijd antwoordt de Hub met `capability_unavailable` op die koppeling.

- De beheerder maakt een koppeling onder `/api/v1/adapterkoppelingen` en bevestigt het HTTPS-basisadres
  en de bijbehorende instantie uit de Hub-catalogus. De app-ID moet overeenkomen met die registratie.
- De beheerder levert het credential aan via de invoerheader `X-Adapter-Credential`. De JSON-body
  bevat de bestemming. Hierdoor kan de gewone idempotentieregel de JSON-body vergelijken zonder
  het credential in de verzoekhash op te nemen. Gebruik voor iedere nieuwe invoer een nieuwe
  `Idempotency-Key`. Herhaling met dezelfde sleutel en body retourneert het oorspronkelijke antwoord.
  Bewaar het credential buiten verzoeklogs. De API geeft alleen de laatste vier tekens en de
  invoerdatum als credentialmetadata terug.
- Wijzig een koppeling via `PATCH /api/v1/adapterkoppelingen/{link_id}`. Een nieuwe bestemming,
  instantie of adresbinding vereist doelbevestiging en een nieuw credential. De Hub verwijdert dan
  de vorige contactmeting. Een ingelogde gebruiker kan de lijst en het detail lezen.
- De beheerder voert de contactproef uit via `POST /api/v1/adapterkoppelingen/{link_id}/test`. De Hub
  gebruikt alleen de openbare leesprobe voor de gekozen app. Het verbonden adres moet binnen de
  bevestigde adresbinding vallen en het TLS-certificaat moet bij de ingestelde hostnaam passen.
  Doorverwijzingen worden geweigerd. Bij uitval is de contacttoestand onbekend. Een contactmeting
  ouder dan 900 seconden wordt `unknown` met `meting_verouderd`. Een openbare probe stelt alleen
  contact vast. De appgezondheid blijft `unknown` met `capability_unavailable` tot een appmodule
  de benodigde leescontrole levert. Lees het resultaat via `GET /api/v1/adapterkoppelingen/{link_id}`.
  Herhaalbare schrijfbevestigingen bevatten geen contactmetingen of credentialmetadata.
- De beheerder ontkoppelt via `DELETE /api/v1/adapterkoppelingen/{link_id}`. De Hub wist de
  kluiswaarde en contactmeting in dezelfde transactie. Deze route stuurt geen verzoek naar de app.

Migratie `0017` voegt de tabel `adapter_link` toe. De downgrade wist de gekoppelde kluiswaarden
en de nieuwe tabel. De bestaande Hub-gegevens blijven behouden.
