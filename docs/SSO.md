# SSO-login van de Hub via OIDC (B01-006)

Keuzes en motivering: [ADR-0023](adr/ADR-0023-oidc-sso-hub.md). Getest tegen een in-repo OIDC-fake in de vorm van
Authentik (**Sim-getest**); tegen een echte Authentik **NIET GEVALIDEERD**. Authentik zelf inrichten (provider,
groepen, herstel) hoort bij `home-control-hub` (B13).

## Eerst: de noodlogin
Zorg dat de noodlogin werkt (Instellingen → Noodaccount: wachtwoord ≥ 20 tekens + TOTP, bevestigd). Die werkt altijd,
ook als Authentik onbereikbaar is, en alleen vanaf het thuisnetwerk. Zonder werkend noodaccount kan "OIDC verplicht" niet
aan.

## In Authentik (door de beheerder, in de Authentik-web-UI)
1. Een **OAuth2/OpenID-provider** voor de Hub: client type *Confidential*, redirect-URI exact
   `https://<adres van de Hub>/api/v1/auth/oidc/callback` (zonder HTTPS-route kan het tijdelijk `http://` zijn; de Hub
   toont dan een waarschuwing), **signing key** kiezen (RS256; zonder signing key gebruikt Authentik HS256 en dat weigert
   de Hub), scopes `openid profile email` (de standaard-profielmapping geeft `groups`).
2. Een applicatie met die provider en groepen voor de Hub-rollen (bijvoorbeeld beheerders, beheer, kijkers, kinderen).

## In de Hub (admin)
1. `PUT /api/v1/auth/oidc`: issuer (exact zoals Authentik hem toont, met slash aan het eind), client-id, clientgeheim
   (alleen schrijven; daarna toont de Hub alleen de laatste 4 tekens), redirect-URI, scopes, groepsclaim (`groups`) en
   de koppelingen groep → rol (`admin`, `operator`, `viewer`, `kind`; `kind` wint altijd).
2. `POST /api/v1/auth/oidc/discover`: de Hub controleert de issuer (https, exacte issuer, endpoints op dezelfde oorsprong,
   PKCE S256, asymmetrische handtekening) en haalt de sleutels op.
3. `POST /api/v1/auth/oidc/test`: open de teruggegeven URL in dezelfde browser en log in bij Authentik. De Hub toont of
   het ID-token geldig is en welke rol je zou krijgen; er wordt geen sessie gemaakt.
4. Leg het resultaat vast als bewijs voor **D17** (onboarding) zodat gate *Authentik/OIDC* opengaat.
5. `POST /api/v1/auth/oidc/inschakelen` met `ingeschakeld: true` (en eventueel `verplicht: true`).

Inloggen gaat daarna via `GET /api/v1/auth/oidc/login`; fouten komen terug als `/inloggen?sso_fout=<reden>`.

## Sessies
- Uitloggen en intrekken werken direct. Een beheerder ziet alle actieve sessies (`GET /api/v1/sessions`) en kan alle
  sessies van een gebruiker intrekken (`POST /api/v1/users/{id}/sessions/revoke`).
- SSO uitzetten of issuer, client, redirect, groepsclaim of koppelingen wijzigen trekt alle SSO-sessies in (en vraagt een
  nieuwe testlogin).
- Haalt Authentik iemands toegang weg, dan stuurt `home-control-hub` `sso.access.revoked`; bij een wijziging
  `sso.access.changed`. De Hub koppelt op (`issuer`, `sub`) en alleen zonder `sub` (overgang) op de gebruikersnaam, en
  trekt de SSO-sessies van die gebruiker in; zo'n event geeft nooit rechten (contract 1.3 §7). Een gebruiker zonder
  gekoppelde groep kan niet meer inloggen.
- `GET /api/v1/sso/status` (admin) toont het advies van `home-control-hub`: de rechten van zijn Authentik-token
  (`deels_gecontroleerd` = waarschuwing, nooit groen) en of de rechtenkaart verouderd is.
