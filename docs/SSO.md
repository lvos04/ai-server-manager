# SSO-login van de Hub via OIDC (B01-006)

Keuzes en motivering: [ADR-0023](adr/ADR-0023-oidc-sso-hub.md). Getest tegen een in-repo OIDC-fake in de vorm van
Authentik (**Sim-getest**); tegen een echte Authentik **NIET GEVALIDEERD**. Authentik zelf inrichten (provider,
groepen, herstel) hoort bij `home-control-hub` (B13).

KLEIN-107 herstelt bestaande invoer- en sessiegrenzen. De tijdelijke handmatige overdracht blijft volgens
[ADR-0033](adr/ADR-0033-oidc-clientgeheim-naar-de-hubkluis.md) dicht tot ook O1/O2 en hun herstelvoorwaarden zijn bewezen:
het herstelbestendige intrekkingsanker en het verwijderen van de geheime bodyhash zijn hier niet gebouwd.

## Eerst: de noodlogin
Zorg dat de noodlogin werkt (Instellingen → Noodaccount: wachtwoord ≥ 20 tekens + TOTP, bevestigd). Die werkt altijd,
ook als Authentik onbereikbaar is, en alleen vanaf het thuisnetwerk. Zonder werkend noodaccount kan "OIDC verplicht" niet
aan.

Maak een lokale beheerder of een noodaccount aan voordat je voor beheer op SSO vertrouwt. De Hub weigert handmatige
wijzigingen die SSO uitzetten of alle OIDC-sessies intrekken zonder werkende lokale herstelroute. Hetzelfde geldt als
je de laatste werkende lokale herstelroute via gebruikersbeheer uitschakelt. Bij gewijzigde discovery zet de Hub
SSO automatisch uit, ook als er geen lokale herstelroute is. Op Gebruikers en toegang staat dan vooraf een waarschuwing.

## In Authentik (door de beheerder, in de Authentik-web-UI)
1. Een **OAuth2/OpenID-provider** voor de Hub: client type *Confidential*, redirect-URI exact
   `https://<adres van de Hub>/api/v1/auth/oidc/callback`, **signing key** kiezen (RS256; zonder signing key gebruikt Authentik HS256 en dat weigert
   de Hub), scopes `openid profile email` (de standaard-profielmapping geeft `groups`).
2. Een applicatie met die provider en groepen voor de Hub-rollen (bijvoorbeeld beheerders, beheer, kijkers, kinderen).

## In de Hub (admin)
SSO inrichten vereist een vertrouwde HTTPS-route naar de Hub.

1. `PUT /api/v1/auth/oidc`: issuer (exact zoals Authentik hem toont, met slash aan het eind), client-id, clientgeheim
   (alleen schrijven; daarna toont de Hub alleen de laatste 4 tekens), redirect-URI, scopes, groepsclaim (`groups`) en
   de koppelingen groep → rol (`admin`, `operator`, `viewer`, `kind`; `kind` wint altijd).
   Schrijven én wissen van het geheim vereisen HTTPS en een lokale beheerderssessie of noodsessie. Een SSO-beheerder
   krijgt `403 lokale_beheerder_vereist`; HTTP krijgt `403 oidc_geheim_https_vereist`, zonder configuratie- of
   kluiswijziging. De API gebruikt hetzelfde verzoeksschema als Secure-cookies: de echte verbinding of headers die
   uvicorn van een expliciet vertrouwde proxy accepteert. Een door de browser aangeleverde schemaheader is onvoldoende.
   Het geheimveld verschijnt alleen via HTTPS voor lokale beheerders en noodsessies. Een SSO-beheerder kan gewone
   gebruikers en hun lagere rollen blijven beheren. Alleen een lokale beheerder of noodsessie kan een gebruiker met
   rol beheerder aanmaken, een rol naar beheerder wijzigen of het noodaccount aanmaken of wijzigen.
   De invoer staat uitsluitend tijdelijk in het veld en het uitgaande verzoek, niet in React-state of browseropslag.
   Verzenden (ook bij fout), verlaten en pagina-herstel maken het veld leeg. `autocomplete=off` en uitsluitingsattributen
   ontmoedigen wachtwoordmanagers; extern opslag-/synchronisatiegedrag kan de app niet afdwingen.
2. `POST /api/v1/auth/oidc/discover`: de Hub controleert de issuer (https, exacte issuer, endpoints op dezelfde oorsprong,
   PKCE S256, asymmetrische handtekening) en haalt de sleutels op.
3. `POST /api/v1/auth/oidc/test`: open de teruggegeven URL in dezelfde browser en log in bij Authentik. De Hub toont of
   het ID-token geldig is en welke rol je zou krijgen; er wordt geen sessie gemaakt.
4. Leg het resultaat vast als bewijs voor **D17** (onboarding) zodat gate *Authentik/OIDC* opengaat.
5. `POST /api/v1/auth/oidc/inschakelen` met `ingeschakeld: true` (en eventueel `verplicht: true`).

Inloggen gaat daarna via `GET /api/v1/auth/oidc/login`; fouten komen terug als `/inloggen?sso_fout=<reden>`.
Zonder actief leesbaar clientgeheim toont Inloggen de reden, verdwijnt de SSO-knop en kun je lokaal inloggen,
ook als "OIDC verplicht" is ingesteld. Testlogin en inschakelen weigeren met `oidc_clientgeheim_ontbreekt` (409).
Ook de callback stopt vóór de tokenaanvraag. Stel het clientgeheim opnieuw in via HTTPS.
Wissen en een wijziging van issuer of client-ID zonder nieuw geheim verwijderen de oude kluisrij, zetten SSO uit
en trekken OIDC-sessies in. Het nood-TOTP en de gedeelde kluissleutel blijven behouden.
Alleen de beheer-GET voor een lokale beheerder of noodsessie toont de laatste vier tekens. Opgeslagen antwoorden van opslaan, discovery en
inschakelen bevatten die niet. Migratie 0014 schoont bestaande OIDC-antwoorden; andere routes en verzoekhashes blijven gelijk.

## Upgraden

Bij upgrade vanaf databaseversie 0012 vervallen alle bestaande OIDC-sessies. Gebruik een lokale beheerderssessie
of de noodlogin om SSO zonder leesbaar geheim opnieuw in te richten. De instelling blijft zichtbaar met de oorzaak
van de onbeschikbaarheid. De Hub legt die toestand bij de eerste start vast in het auditspoor. Lokale en noodsessies
blijven geldig.

## Sessies
- Uitloggen en intrekken werken direct. Een beheerder ziet alle actieve sessies (`GET /api/v1/sessions`) en kan alle
  sessies van een gebruiker intrekken (`POST /api/v1/users/{id}/sessions/revoke`).
- Elke OIDC-sessie geldt alleen met SSO aan en dezelfde configuratieversie. Migratie 0013 voegt die binding toe;
  oudere OIDC-sessies zonder binding moeten opnieuw aanmelden. Lokale sessies en noodsessies blijven geldig.
- SSO uitzetten (ook als het al uit staat), gewijzigde discovery, issuer, client, redirect, scopes, sessieduur,
  groepsclaim, koppelingen en vervangen/wissen van het geheim trekken OIDC-sessies in. Automatisch verversen van
  gewijzigde discovery zet SSO ook uit. Opnieuw inschakelen laat ingetrokken sessies niet herleven; een nieuwe testlogin is nodig.
- Dit is geen herstelbestendige intrekkingsgrens: een volledige oude database terugzetten vraagt het nog open O1-anker.
- De bestaande CGNAT-instelling van de noodlogin blijft standaard uit. Alleen een lokale beheerder of noodsessie mag
  haar wijzigen; een SSO-beheerder krijgt 403. Dit verandert de netwerksetting of noodlogin niet en geeft geen
  vrijgave voor netwerkverruiming bij het gebruikersbesluit alleen LAN (O3).
- Haalt Authentik iemands toegang weg, dan stuurt `home-control-hub` `sso.access.revoked`; bij een wijziging
  `sso.access.changed`. De Hub koppelt op (`issuer`, `sub`) en alleen zonder `sub` (overgang) op de gebruikersnaam, en
  trekt de SSO-sessies van die gebruiker in; zo'n event geeft nooit rechten (contract 1.3 §7). Een gebruiker zonder
  gekoppelde groep kan niet meer inloggen.
- `GET /api/v1/sso/status` (admin) toont het advies van `home-control-hub`: de rechten van zijn Authentik-token
  (`deels_gecontroleerd` = waarschuwing, nooit groen) en of de rechtenkaart verouderd is.
