# ADR-0011 — Contract 1.2: enrollment, Hub-authenticatie, sleutelpinning en Custom App-realiteit

Status: aangenomen · 2026-11-09 · ronde "contract 1.2" · eigenaar contract: `ai-server-manager`
Aangevuld door ADR-0012 (onafhankelijke review, zelfde dag): o.a. `app_id` vast per image, `pending` naast `state`,
rotatie zonder buitensluiten, geen automatische rotatie (R2), ook PID 1 niet als root. De tabel hieronder is de stand
bij het vaststellen; jelly-leon-platform stuurt sinds `8c83aa6` al exact de Hub-velden.
Bron: `docs/platform-v2/OVERDRACHT/STATUS.md` (secties "Contract 1.2" en "Besluiten van de gebruiker"), de
enrollment-code, tests en ADR's van alle nieuwe diensten. Resultaat: `docs/platform-v2/PLATFORM_CONTRACTEN.md` 1.2 en
`docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md`.

## Context

Contract 1.1 noemde enrollment, service-tokens en JWKS, maar niet het exacte verzoek/antwoord, niet hoe de Hub zich bij
een dienst authenticeert en niet hoe Hub-sleutels betrouwbaar bij een dienst komen. Elke dienst koos in P0 iets eigens:

| Dienst | Verzoek naar `POST /api/v1/services/enroll` | Past op de Hub (`extra=forbid`)? |
|---|---|---|
| Hub (`apps/api/src/hub/routers/services.py`) | `{app_id, enrollment_token \| pairing_code, version, base_url, public_key_jwk?}` | — |
| `zoeken-en-persoonlijke-ai` (ADR-0002) | gelijk aan de Hub | ja |
| `home-control-hub` (ADR-0002/0008) | `{app_id, kind, secret, version, base_url, public_key_jwk, api_prefix, connector_prefix}` | **nee** (422) |
| `appstore-en-fork` (ADR-0005) | Hub-velden + `capabilities` | **nee** (422) |
| `jelly-leon-platform` (ADR-0004/0009) | Hub-velden + `kind`, `capabilities`, `schema_version` | **nee** (422) |

Alle vier diensten namen aan dat de Hub hen aanroept met **hun eigen service-token**; de Hub bewaart van dat token
alleen de SHA-256 en kan dat dus niet. Alle vier vertrouwden de JWKS die later via HTTP op het LAN wordt opgehaald
(jelly-leon-platform repareerde in de P0-review al een kritieke auth-bypass via een vreemde "Hub", ADR-0009 daar).
Daarnaast meldde P0 de Custom App-realiteit (ix-app 1.4.8 laat no-new-privileges/cap_drop weg, `app.rollback` werkt
niet voor image-tags, catalogusversies verdwijnen) en nam de gebruiker zeven besluiten.

## Besluiten

1. **Enroll-schema = wat de Hub al bouwde, aangescherpt.** De velden van de Hub (en van zoeken-en-persoonlijke-ai)
   worden het exacte schema; `public_key_jwk` en `version` worden verplicht, `app_id` volgt het TrueNAS-appnaampatroon;
   `extra=forbid` blijft (drift valt direct op als 422 in plaats van stil genegeerd te worden). Het antwoord houdt de
   veldnamen die de Hub al teruggeeft en die alle diensten al lezen (`service_token`, `service_id`, `jwks`,
   `policy_public_key`), plus `schema_version`, `keyset_fingerprint`, `key_rotation_url` en `enrollment_replayed`.
   Eén foutcode `401 invalid_enrollment` voor onbekend/verlopen/gebruikt (geen orakel). *Waarom:* minst nieuw werk
   (één dienst past al; drie passen hun verzoek licht aan: extra velden weg, home-control-hub hernoemt
   `kind`/`secret` naar `enrollment_token`/`pairing_code`) en veilig.
2. **Herhaling na herstart halverwege** zonder `Idempotency-Key`: dezelfde grant + `app_id` + dezelfde
   identiteitssleutel (thumbprint), binnen de 60 min en zolang het eerder uitgegeven token **nooit gebruikt** is → nieuw
   token, oud ingetrokken. De dienst bevestigt direct met `GET /api/v1/services/self`, waarmee de herhaling dicht gaat.
   *Afgewogen:* een door de dienst gegenereerd token (alleen hash naar de Hub) is eleganter maar vraagt meer
   herbouw aan beide kanten; een handtekening als bewijs van sleutelbezit voegt op HTTP-LAN niets toe, want wie het
   verzoek afluistert, ziet ook het antwoord met het token.
3. **Hub → dienst = door de Hub ondertekende dienst-JWT** (`token_use: "hub_service"`, `sub: "hub"`,
   `roles: ["service"]`, `service_id`, `jti`, ≤ 120 s), **niet** het service-token in beide richtingen. *Waarom:*
   (a) het service-token gaat bij elke event-push over het LAN; wie het afluistert mag niet als de Hub optreden;
   (b) de Hub houdt "alleen hashes" (contract §3, ADR-0006) en hoeft geen terugleesbare tokens te bewaren;
   (c) hergebruikt wat al gebouwd is: elke dienst verifieert al Hub-JWT's (EdDSA, `iss`, `aud`, `exp`), en de
   gepinde sleutel, `jti`-replaycache en 120 s-grens gelden dan ook voor de Hub-aanroepen. Kosten: per dienst een
   kleine afbeelding `token_use → principal` en het weigeren van het inkomende service-token. Gebruikers-JWT's krijgen
   `token_use: "user"` zodat de twee soorten nooit te verwarren zijn.
4. **Pinning bij enrollment + menselijke vingerafdruk.** De dienst pint `jwks` en `policy_public_key` uit het
   enroll-antwoord (kid + `x` + RFC 7638-thumbprint) en vertrouwt daarna nooit een via HTTP opgehaalde JWKS. Om de
   pinning zelf tegen een MITM op het LAN te beschermen, controleert de dienst een **sleutelset-vingerafdruk** (80 bit,
   16 tekens Crockford-base32) die de Hub-UI naast de koppelcode toont en die de Hub bij installatie via de API als
   `HUB_KEY_FINGERPRINT` meegeeft. Nieuwe sleutels alleen via opnieuw koppelen of een met een gepinde sleutel
   ondertekende rotatie (`/api/v1/auth/key-rotations`; in de Hub nog niet gebouwd → lege lijst, geen rotatie).
   *Afgewogen:* HTTPS op het LAN vraagt certificaatbeheer dat pas met B10/B13 komt; JWKS ondertekend door de
   policy-sleutel verschuift alleen het TOFU-probleem.
5. **Opslag in `/appdata/secrets/hub-link.json`** (0600, 568, atomair, met vergrendeling) in plaats van de
   database-vault. *Waarom:* een database-herstel (B12) mag geen oude koppeling, oude pins of een ingetrokken token
   terugbrengen; DB-exports bevatten dan geen credentials; "ooit gekoppeld" overleeft elke DB-wissel. Het token staat er
   onversleuteld in, net als `vault.key` en de identiteitssleutel in dezelfde map (versleutelen met een sleutel uit
   dezelfde map voegt niets toe). Bestaande koppelingen worden eenmalig overgezet.
6. **Statuspagina-koppelen alleen vóór de eerste koppeling**, met vingerafdruk, 5/15 min per bron-IP + 20/15 min per
   dienst. Geen lokale ontkoppelcode meer op de statuspagina (zoals home-control-hub en zoeken-en-persoonlijke-ai nu
   hebben): herkoppelen gaat via de Hub of via een nieuw `HUB_ENROLLMENT_TOKEN` in het TrueNAS-formulier (wie dat kan,
   is TrueNAS-beheerder). Uitzondering: de executor mag ontkoppelen/roteren na een live geverifieerde TrueNAS-schrijfkey.
   *Restrisico:* vóór de eerste koppeling kan iemand op het LAN de dienst aan een eigen "Hub" koppelen; de vingerafdruk
   helpt daar niet (de aanvaller kiest alle invoer). Beperking: env-enrollment is de aanbevolen weg, de dienst heeft dan
   nog geen data of rechten, en opnieuw koppelen via de Hub herstelt het.
7. **Rotatie door de dienst zelf.** `POST /api/v1/services/{id}/rotate` (admin) gaf het nieuwe token aan de beheerder,
   die het niet aan de dienst kan geven; in 1.2 vraagt die route rotatie **aan** (202) en signaleert de Hub dat met
   `Hub-Token-Rotation: required`; de dienst roteert via `self/rotate`.
8. **Bestaande apps zonder enrollment in v1**: Hub-adapter in de Hub op bestaande routes met een gescopete sleutel
   (MediaGuard `X-Api-Key` viewer, my_house viewer-koppelcode, MSO nieuwe machine-sleutel in P3, Jellyfin alleen
   openbare routes + niet-admin-gebruiker). Bevestigt my_house ADR-0006 punt 1 en MediaGuard ADR-0013 punt 3–5; wijzigt
   MSO ADR-0002 (dat nog enrollment + Hub-JWT plande).
9. **Custom App-realiteit**: images zetten zelf `PR_SET_NO_NEW_PRIVS` na de eigenaarschapsstap (zoals de Hub al doet,
   ADR-0010 punt 4); rooktests draaien zonder `--security-opt`/`--cap-drop`; digest in het tagveld als
   `versie@sha256:…` met digest-readback (update-detectie NIET GEVALIDEERD); terugzetten van een Custom App =
   `app.update` met bewaarde vorige waarden; verdwenen catalogusversie = blokkade `version_unavailable`.
10. **Manifest**: `joins_platform_network` en `custom_app.ports` vervallen (één bron: `network.ports`), met een
    overgang via `deprecated_field`; GPU wordt een optionele parameter van type `gpu`, begrensd door `privileges.gpu`
    en D08.
11. **Hub-taken**: AI-runner uid 569 (bevestigt ADR-0005); noodlogin met verplichte TOTP, alleen privé-bereiken,
    sessie ≤ 60 min, incident + rotatieplicht, onafhankelijk van Authentik en home-control-hub (sluit aan op
    home-control-hub ADR-0003: "de Hub moet de noodtoegang zelf afdwingen"); D10 Ingevuld.
12. **§12 attributie**: commits eindigen met de attributieregel(s) van de lopende sessie; geen vaste sessielink.
    Het contract noemt zelf geen modelnaam.
13. **§13 ontwerptaal**: alleen reikwijdte en werkwijze; de inhoud komt van de design-agent
    (`docs/platform-v2/ONTWERPTAAL.md`, `design/ontwerptaal/` — bestaan nog niet).

## Gevolgen

- Alle vier nieuwe diensten en de Hub moeten code aanpassen (lijst per repo in `CONTRACT_1.2_CONFORMITEIT.md`). Tot dat
  gebeurd is, werkt enrollment tussen de echte Hub en home-control-hub, appstore-en-fork en jelly-leon-platform niet
  (422), en kan de Hub geen enkele dienst aanroepen. Niets hiervan is op een echte NAS getest.
- Hub-simulatoren in de diensten (`tests/e2e/sim_hub.py`, `tests/fakehub.py`, `e2e/simulators/hub/hub_sim.py`) moeten
  het exacte schema volgen; een gedeelde conformiteitstest (zelfde testvectoren voor de vingerafdruk) voorkomt drift.
- Open (niet in 1.2 besloten): scopes per dienst op de Hub-connector (ADR-0010; nu leest elke ingeschreven dienst alle
  besluiten, zonder geheimen); hoe de Jelly Leon-plugin (P4) Hub-sleutels pint zonder enrollment; HTTPS op het LAN;
  `JL_SYNC_PUSH_TOKEN` (besluit 4).
