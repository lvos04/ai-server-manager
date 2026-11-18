# SSO-login van de Hub via OIDC (B01-006)

Keuzes en motivering: [ADR-0023](adr/ADR-0023-oidc-sso-hub.md). Getest tegen een in-repo OIDC-fake in de vorm van
Authentik (**Sim-getest**); tegen een echte Authentik **NIET GEVALIDEERD**. Authentik zelf inrichten (provider,
groepen, herstel) hoort bij `home-control-hub` (B13).

KLEIN-107 herstelt bestaande invoer- en sessiegrenzen. De tijdelijke handmatige overdracht blijft volgens
[ADR-0033](adr/ADR-0033-oidc-clientgeheim-naar-de-hubkluis.md) dicht tot ook O1/O2 en hun herstelvoorwaarden zijn bewezen:
het herstelbestendige intrekkingsanker en het verwijderen van de geheime bodyhash zijn hier niet gebouwd.

## Eerst: de noodlogin
Stel de noodlogin in via Instellingen → Noodaccount met een wachtwoord van minimaal 20 tekens en bevestig het TOTP.
De noodlogin werkt vanaf een toegestaan privéadres, ook als Authentik onbereikbaar is. Voor "OIDC verplicht" zijn
een werkend noodaccount én een actief gewoon lokaal beheerdersaccount met een wachtwoord vereist. De Hub beschermt
dan de laatste gewone lokale beheerder tegen uitschakelen of degraderen. Zolang SSO beschikbaar is en het
noodaccount werkt, weigert de Hub gewone lokale aanmeldingen.

Maak een lokale beheerder of een noodaccount aan voordat je voor beheer op SSO vertrouwt. De Hub weigert handmatige
wijzigingen die SSO uitzetten of alle OIDC-sessies intrekken zonder werkende lokale herstelroute. Hetzelfde geldt als
je de laatste werkende lokale herstelroute via gebruikersbeheer uitschakelt. Bij gewijzigde discovery zet de Hub
SSO automatisch uit, ook als er geen lokale herstelroute is. Op Gebruikers en toegang staat dan vooraf een waarschuwing.

Bewaar bij een rotatie het nieuwe wachtwoord en het nieuwe TOTP offline voordat je de beheersessie sluit. Als die
sessie eindigt vóór de bevestiging, kies je op het inlogscherm **Noodlogin**. Meld je vanaf het thuisnetwerk aan met
het nieuwe wachtwoord en een geldige code uit de nieuwe authenticator. De Hub bevestigt daarmee het nieuwe TOTP en
markeert de noodlogin zoals gebruikelijk voor rotatie. Vanuit die noodsessie kun je een lokale beheerder aanmaken of
heractiveren en de SSO-instellingen herstellen.

De Hub controleert voor lokale accounts en het noodaccount of de opgeslagen wachtwoordhash een volledig
gecodeerde Argon2id-verifier met een digest van 32 bytes is. Ondersteunde oudere Argon2id-verifiers blijven
bruikbaar. Na een geslaagde gewone aanmelding vernieuwt de Hub zo nodig de hash. Bij een afgekeurd profiel
weigert de Hub de aanmelding en blijft de opgeslagen hash behouden.

Bij een onbruikbare wachtwoordhash van het noodaccount of een ontbrekende of onleesbare nood-TOTP-kluisrij
geeft de zelftest aan welke controle faalt. De Hub weigert het inschakelen van verplichte OIDC. Een eerder
ingestelde verplichting vervalt tijdelijk. De openbare SSO-status en de schermen voor inloggen en SSO-beheer
tonen de oorzaak en de beschikbare herstelstap. Log in met een bestaand lokaal beheerdersaccount.
Vernieuw onder Instellingen → Noodaccount het noodwachtwoord en de TOTP en bevestig de nieuwe code. SSO blijft beschikbaar
zolang het clientgeheim leesbaar is. Na bevestiging geldt "OIDC verplicht" weer als die instelling aanstaat en SSO
beschikbaar is. Bij de eerste start die de kluisfout aantreft, schrijft de Hub één auditregel
`auth.break_glass.totp_kluisrij_ontbreekt` met een vaste redencode.

### Bestaande installatie zonder bruikbare lokale beheerder

Werkt de noodlogin nog, maak dan vanuit een noodsessie een gewone lokale beheerder aan of activeer die opnieuw.
Bij een onbruikbare wachtwoordhash van het noodaccount of een ontbrekende of onleesbare nood-TOTP-kluisrij kan
de beheerder van de installatie via de Hub-console
een lokaal beheerdersaccount aanmaken. Open een interactieve terminal in de draaiende Hub-container als de
gebruiker waaronder de Hub draait. Gebruik bij een losse installatie de terminal met de gebruikelijke
Hub-configuratie. Voer het commando uit met een nieuwe, vrije gebruikersnaam.

```sh
python -m hub herstel-lokale-beheerder <nieuwe-gebruikersnaam>
```

Vervang de plaatsaanduiding door de gebruikersnaam. Voer het nieuwe wachtwoord twee keer in bij de afgeschermde
prompt. Het commando controleert de storing en weigert een tweede herstel zodra er een bruikbare gewone lokale
beheerder is. Het aanmaken en de reden komen samen in het auditspoor. Meld je daarna aan met het nieuwe lokale account en herstel
het noodaccount via Instellingen → Noodaccount. Bewaar het lokale account voor een volgende storing.

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
   rol beheerder aanmaken, een rol naar beheerder wijzigen, een lokaal beheeraccount opnieuw activeren of het
   noodaccount aanmaken of wijzigen.
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

Bij de eerste start na dit herstel vervangt de Hub de oude fouttekst met het algoritme uit het ID-token door de
vaste code `alg_niet_toegestaan` in het laatste SSO-testresultaat en de opgeslagen OIDC-idempotentieantwoorden.
Als velden zijn aangepast, krijgt het auditspoor één nieuwe regel met alleen het aantal. Volgens het bewaarbeleid
blijven bestaande verzegelde auditregels intact. Daarin kan de historische tekst nog staan.

## Sessies
- Uitloggen en intrekken werken direct. Gebruikers kunnen hun eigen sessies intrekken via
  `POST /api/v1/auth/sessions/{session_id}/revoke`. Een beheerder ziet alle actieve sessies (`GET /api/v1/sessions`)
  en kan sessies afzonderlijk of per gebruiker intrekken (`POST /api/v1/users/{user_id}/sessions/revoke`). Alleen een
  lokale beheerder of noodsessie mag een noodsessie afzonderlijk of alle sessies van het noodaccount intrekken.
  Een SSO-beheerder krijgt daarbij op beide routes 403.
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
