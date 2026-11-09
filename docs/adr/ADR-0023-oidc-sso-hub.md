# ADR-0023 — SSO-login van de Hub via OIDC (Authorization Code + PKCE)

Status: aanvaard · Datum: 2026-11-09 · Fase: P1 "Ogen en toegang", backend deel 2
Excel: B01-006 (Hub-kant van B13-002/B13-004); bouwt op de noodlogin van ADR-0013/0014 (contract 1.2 §4.1)

## Context
B01-006 vraagt OIDC-login voor de Hub tegen Authentik, rollen admin/operator/viewer (+ kind), korte sessies, veilige
cookies/CSRF en intrekken van sessies; acceptatie: een kijker kan nooit update/stop of geheimen ophalen en uitloggen of
intrekken werkt direct. Authentik zelf inrichten is van `home-control-hub` (B13); daar is de Hub "register en adviseur,
nooit poortwachter". De noodlogin bestaat al in de Hub en moet blijven werken als OIDC faalt.

## Besluiten
1. **Flow:** Authorization Code + PKCE (S256, verplicht), confidential client (`client_secret_basic`, anders
   `client_secret_post`; zonder geheim: publieke client met PKCE). Het clientgeheim staat alleen in de vault en komt nooit
   terug (alleen `ingesteld` + laatste 4).
2. **Issuer en discovery:** alleen `https://` (D17 "HTTPS"); `http://` uitsluitend naar loopback met de ontwikkelvlag
   (tests). Het `issuer`-veld van de discovery moet exact gelijk zijn (Authentik gebruikt een slash aan het eind); alle
   endpoints op dezelfde oorsprong als de issuer; redirects nooit volgen; geen proxy. Discovery wordt bij inloggen
   hooguit een dag hergebruikt; verandert hij, dan gaat SSO uit tot een nieuwe testlogin (break-glass blijft).
3. **ID-token:** alleen asymmetrische algoritmen (RS/PS/ES/EdDSA). `none` en HS* worden geweigerd: Authentik gebruikt
   HS256 met het clientgeheim als er geen signing key is gekozen; dat staat de Hub niet toe (de beheerder kiest in
   Authentik een signing key). `kid` uit de JWKS; een onbekende `kid` haalt de JWKS hooguit eens per minuut opnieuw op
   (geen versterker voor aanvallers). `iss`, `aud` (meerdere → `azp`), `exp`/`iat`/`nbf` met 30 s speling, `iat` ≤ 10 min
   oud, `nonce` gelijk aan de transactie, `sub` verplicht.
4. **Transactie:** `state`, `nonce` en PKCE-verifier per aanmelding, eenmalig, 10 minuten, gebonden aan de browser via een
   eigen HttpOnly-cookie (`SameSite=Lax`, pad `/api/v1/auth/oidc`) waarvan alleen de SHA-256 in de database staat. Een
   tweede callback (replay) of een callback in een andere browser faalt; ook een mislukte poging maakt de state waardeloos.
   Het starten is per bron-IP begrensd (30 per 15 min).
5. **Sessiecookie en doorsturen:** de sessie blijft `SameSite=Strict`. Omdat de callback een cross-site navigatie is,
   antwoordt de Hub met een kleine HTML-pagina (geen JavaScript, CSP `default-src 'none'`) die met een meta-refresh naar
   het (gecontroleerde, eigen) terugkeerpad gaat; die volgende navigatie is same-site en de cookie gaat mee.
6. **Accounts en rollen:** eigen SSO-account per (issuer, `sub`); **nooit** automatisch koppelen aan een bestaand lokaal
   account op naam of e-mail (overname-risico). Gebruikersnaam uit `preferred_username` (bij botsing `-sso`). Geen
   bruikbaar wachtwoord; wachtwoord wijzigen → `409 sso_account`. **Groep → rol** stelt de beheerder in de Hub in:
   `kind` wint altijd (contract §4.2), anders de hoogste rol; geen gekoppelde groep → geen toegang (geen standaardrol) en
   lopende SSO-sessies van die gebruiker vervallen. Groepen uit het ID-token, anders uit userinfo (`sub` moet gelijk
   zijn). De rol wordt bij elke login opnieuw bepaald; een rolwijziging trekt oudere SSO-sessies in.
7. **Inschakelen:** alleen een beheerder; vraagt een geslaagde **testlogin** met de huidige instellingen
   (`config_versie`) en gate `authentik` (D17 Getest; de testlogin kan het bewijs voor D17 zijn). Wijzigen van issuer,
   client, redirect, groepsclaim of koppelingen verhoogt `config_versie`, zet SSO uit en trekt SSO-sessies in.
8. **"OIDC verplicht":** alleen met een werkend noodaccount (`assert_oidc_required_allowed`, al aanwezig) en geldt alleen
   zolang dat noodaccount werkt (`verplicht_effectief`); anders kan lokaal inloggen weer (geen SSO-only lock-out). Met
   "verplicht" weigert `/auth/login` gewone lokale accounts met `403 oidc_verplicht`, zonder wachtwoordcontrole (geen
   orakel). De noodlogin (`/auth/break-glass/login`) doet geen enkele netwerkaanroep en blijft werken bij uitval van de
   issuer.
9. **Intrekken:** uitloggen en intrekken werken direct (de sessie wordt per verzoek gecontroleerd); de beheerder kan alle
   sessies van een gebruiker intrekken en alle actieve sessies zien (`/api/v1/sessions`). `sso.access.revoked` van
   `home-control-hub` (alleen die dienst, via de inbox met service-token) trekt de SSO-sessies van die Authentik-gebruiker
   in: alleen intrekken, een event kan nooit rechten geven.
10. **Advies van home-control-hub:** `GET /api/v1/sso/status` leest (dienst-JWT; voor de rechtenkaart een kortlevende
    gebruikers-JWT van de beheerder) de tokenrechten en de versheid van de rechtenkaart. `least_privilege`
    `deels_gecontroleerd` → weergave `waarschuwing`, `te_ruim` → `fout`, al het andere (ook `ok`, dat daar niet bestaat)
    → `onbekend`; rechten `verouderd` → `verouderd`. Nooit groen op aannames; de rechtenkaart zelf wordt niet doorgegeven.
11. Instellen/testen/inschakelen en sessiebeheer zijn **geen** `action_id`'s (contract §8): de AI kan ze niet voorstellen.
    Starten van een (test)login en de callback vallen, net als inloggen, buiten `Idempotency-Key` (ADR-0006).

## Gevolgen
- Migratie 0008 (`oidc_config`, `oidc_transaction`, `oidc_identity`, `auth_bron` op gebruiker en sessie).
- De login-knop, het SSO-instellingenscherm en de sessielijst volgen in de P1-webstap (`/inloggen?sso_fout=<code>` toont
  dan de reden).
- Getest tegen een in-repo OIDC-fake in de vorm van Authentik en een fake `home-control-hub`; tegen een echte Authentik
  NIET GEVALIDEERD (account/instantie ontbreekt).

## Open punten voor het contract
1. §4.1 noemt OIDC "optioneel zodra B13 actief is" maar niet wie de groep→rol-koppeling beheert. Gekozen: de Hub (eigen
   tabel); `home-control-hub` toont zijn koppelingen als advies. Voorstel 1.3: vastleggen.
2. §4.1 zegt niets over de duur van SSO-sessies; gekozen: instelbaar 15–720 min (standaard 8 uur), nooit langer dan de
   lokale sessieduur, met dezelfde inactiviteitsgrens.
3. D17 vraagt "HTTPS"; zonder TLS-route (B10/B13) kan de Hub-redirect zelf nog `http://` zijn. Gekozen: issuer altijd
   https; redirect_uri mag http (de code is door PKCE en het browsercookie beschermd), de status toont
   `redirect_uri_https: false` als waarschuwing.
