# ADR-0013 — Contract 1.2 in de Hub en de executor: bouwkeuzes

Status: aangenomen · 2026-11-09 · ronde "contract 1.2 toepassen" · bij `CONTRACT_1.2_CONFORMITEIT.md` §1 (H1–H14)
Bouwt op ADR-0011 (keuzes contract 1.2) en ADR-0012 (review). Werkt ADR-0006 bij (idempotency) en vult ADR-0010 aan.

## Context

Contract 1.2 legt enrollment, Hub → dienst-authenticatie, pinning, rotatie en de noodlogin exact vast. De Hub is als
eerste aan de beurt (volgorde 1 van de conformiteitslijst), zodat de vier nieuwe diensten tegen de echte Hub kunnen
testen. Een aantal punten laat het contract open of hangt af van latere fasen; die keuzes staan hieronder.

## Besluiten

1. **Executor koppelt alleen met een koppelcode.** `POST /services/enrollment-tokens` voor
   `ai-server-manager-executor` → `422 executor_requires_pairing_code`; de koppelcode voor de executor is 30 min geldig
   (`purpose: executor`). *Waarom:* §3.9 noemt alleen de koppelcode + vingerafdruk op de executorpagina; de executor is
   de tweede handmatige Custom App en wordt nooit via de API geïnstalleerd. Geen enrollment-token = geen geheim in het
   formulier van de app met schrijfrechten.
2. **Herhaling na herstart (§3.6):** de grant-rij wordt met `SELECT … FOR UPDATE` vergrendeld; herhaling mag alleen als
   de thumbprint gelijk is aan `used_with_key_thumbprint`, de grant niet verlopen is, het nieuwste token van die grant
   niet ingetrokken is (beheerder of herinschrijving met een andere grant sluit de herhaling), geen enkel token van de
   grant ooit gebruikt is en de dienst `active` is. Een herhaling wist een aangevraagde rotatie.
3. **Rotatie zonder buitensluiten (§3.8):** `self/rotate` zet op alle nog geldige, ooit gebruikte tokens
   `superseded_at` en een bovengrens van 24 uur (nooit verlengd door een volgende rotatie); nooit gebruikte eerder
   uitgegeven tokens worden ingetrokken. Bij het **eerste gebruik** van een token gaan vervangen oudere tokens naar
   `min(bovengrens, nu + 10 min)`. `Hub-Token-Rotation: required` zet de afhankelijkheid via `request.state`; de
   HTTP-middleware zet de header, ook als het eindpunt zelf een `JSONResponse` teruggeeft. Na 180 dagen alleen
   `rotatie.aanbevolen: true` in het register (geen automatische rotatie, R2).
4. **Hub → dienst met `http.client`** (`hub/servicecalls.py`), geen nieuwe afhankelijkheid: volgt nooit redirects en
   leest nooit proxy-omgevingsvariabelen; alleen `http://` naar het **gemeten** registeradres (D03 + hostpoort uit
   `app.query` van de app die de eigen image draait). `base_url` uit het enroll-verzoek wordt nooit gebruikt. Zonder
   gemeten adres → `409 service_address_unknown` (de beheerder kan alleen intrekken).
5. **Ontkoppelen = eerst de dienst, dan de Hub.** `POST /services/{id}/unlink` (admin, `Idempotency-Key`, die ook naar
   de dienst gaat) stuurt een nieuwe dienst-JWT; alleen 2xx of `401 not_linked` (herhaling) telt als geslaagd, daarna
   trekt de Hub de registratie in. Elk ander antwoord, een redirect of een netwerkfout → `502` en er wordt niets
   ingetrokken (fail-closed: liever een zichtbare storing dan een half ontkoppelde dienst).
6. **TrueNAS-appnaam (H14):** `PUT /services/{id}/truenas-app` (admin) accepteert alleen een naam die de laatste verse
   inventaris als app met de eigen image (`ghcr.io/lvos04/<app_id>`) heeft gemeten; anders `422` met de gemeten
   kandidaten. De `app_id` blijft de vaste constante. Gebruik voor `app.update` volgt in P2.
7. **Noodlogin (§4.1):**
   - Eén noodaccount, alleen via `/api/v1/auth/break-glass/*`; de gewone `/auth/login` weigert het (anders kan TOTP
     worden overgeslagen); het account blijft `admin` en wijzigt zijn wachtwoord alleen via *roteren*.
   - Instellen en roteren vragen het **eigen wachtwoord** van de beheerder (een overgenomen sessie alleen is niet
     genoeg) en geven het TOTP-geheim één keer terug (`no-store`); daarom, net als `auth/password`, zonder
     `Idempotency-Key` (ADR-0006). Het geheim staat AES-GCM-versleuteld in de vault (`vault://auth/break-glass-totp-…`).
   - TOTP volgens RFC 6238 (SHA-1, 30 s, 6 cijfers, ±1 stap); een gebruikte tijdstap wordt nooit opnieuw geaccepteerd
     (ook niet tussen bevestigen en inloggen).
   - Privé-bereiken RFC 1918, 100.64.0.0/10 en fc00::/7 (IPv4-mapped IPv6 meegerekend); loopback en link-local tellen
     **niet**. Het bron-IP is het TCP-adres dat de webserver (`proxy.mjs`) als enige `X-Forwarded-For` doorgeeft.
     Restrisico achter Docker-NAT: NIET GEVALIDEERD; de zelftest toont het adres en waarschuwt bij een adres dat op een
     Docker-gateway lijkt (`172.16.0.0/12`, eindigend op `.1`).
   - Elke noodlogin: audit `auth.break_glass.used`, outbox-event `auth.break_glass.used` (classificatie `sensitive`) en
     rotatieplicht. De Hub heeft nog geen incidenten-inbox (B01-005) en geen meldkanaal (Gotify); het event is daarom
     de eerlijke vorm van "incident + melding" tot die er zijn.
   - "OIDC verplicht" bestaat nog niet (B13/D17); `breakglass.assert_oidc_required_allowed` is de bewaking die die
     schakelaar straks moet aanroepen, en de status toont `oidc_verplicht_mogelijk`.
   - Een cache van het beleid van home-control-hub is **niet** gebouwd: zonder cache gelden de standaardwaarden
     (contract §4.1); er is nog geen bron (HC10).
8. **Executor-koppelen (H7, deel P0/P1):** statuspagina-formulier met CSRF + Origin-controle en throttle 5/15 min per
   bron-IP + 20/15 min totaal (één API-proces: teller in het geheugen mag, §3.7); opslag en pinning in
   `/appdata/secrets/hub-link.json`; inkomende Hub-JWT's op `GET /connector/v1/hub-link` met de controlevolgorde en
   redenen van §4.7 (zonder PyJWT, met `cryptography`). `POST /connector/v1/hub-link/unlink` → `501
   capability_unavailable` en geen koppelformulier na de eerste koppeling: §3.9 staat ontkoppelen op de executor alleen
   toe na een live geverifieerde TrueNAS-schrijfkey, en die bestaat pas in P2. Een `jti`-replaycache is nog niet nodig
   (de executor heeft geen muterende route die Hub-JWT's accepteert); die komt mee met de uitvoerroute in P2.
9. **UI wacht op de ontwerpstap.** De schermen "Diensten" (H5) en "Noodaccount" (H6) zijn niet gebouwd: contract §13
   vraagt vooraf een ontwerpstap van de design-agent, en `docs/platform-v2/ONTWERPTAAL.md` + `design/ontwerptaal/`
   staan nog niet in deze repo. Tot dan zijn alle functies via de API (en `/api/docs`) bereikbaar, en zegt
   `deploy/truenas/CUSTOM_APP.md` dat eerlijk. H12 (ombouw) start om dezelfde reden niet.
10. **Niet in deze ronde** (fase-gebonden in de conformiteitslijst): H10 (terugzetrecept + digest-readback, P2, samen
    met jelly-leon-platform), H11 (adapters bestaande apps, P3), H13 (open punt voor een volgende contractversie).
11. **Manifesten (H8)** pas aangepast nadat de validator van appstore-en-fork M1–M6 had (volgorde 3, commit `837fa61`
    daar): `joins_platform_network` en `custom_app.ports` zijn weg, kop "platformcontract 1.2". Gecontroleerd met
    `jl-manifest validate --strict` uit die commit (alleen-lezen uitgepakt in een tijdelijke map): 0 fouten, alleen
    `digest_pending_release` blijft — de digest vult de release-CI, en taggen is niet in deze ronde (besluit 6).

## Gevolgen

- De echte Hub volgt §3.3 exact; diensten met extra velden (home-control-hub, appstore-en-fork) of `use`/`alg` in hun
  JWK krijgen nu `422` tot hun HC1/AS1 klaar is.
- Migratie `0002` (up/down getest) voegt kolommen toe; bestaande tokens krijgen `first_used_at = last_used_at`.
- Alles is Sim-getest (echte PostgreSQL, echte Hub-API, nep-dienst en echte executor via uvicorn); niets is op een
  echte NAS getest.
