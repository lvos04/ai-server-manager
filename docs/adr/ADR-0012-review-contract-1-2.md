# ADR-0012 — Onafhankelijke review van contract 1.2: correcties vóór verspreiding

Status: aangenomen · 2026-11-09 · ronde "contract 1.2" · eigenaar contract: `ai-server-manager`
Bij: `docs/platform-v2/PLATFORM_CONTRACTEN.md` (`contracts 1.2`, sectie "Correcties uit de onafhankelijke review"),
`docs/platform-v2/CONTRACT_1.2_CONFORMITEIT.md`, ADR-0011.

## Context

Na het vaststellen van 1.2 (ADR-0011) is het contract door een aparte reviewer tegen STATUS.md, de besluiten van de
gebruiker, `01_ARCHITECTUUR` (02, 03, 04, 07, 08) en de **echte code** van alle andere repos gehouden (alleen lezen,
stand per repo in de conformiteitslijst). Doel: het contract proberen te weerleggen vóórdat het naar de andere repos
wordt gekopieerd. Het contract was nog nergens gekopieerd of gebouwd; de correcties horen daarom bij 1.2 zelf (geen
1.3). Niets hiervan is op een echte NAS getest.

## Wat standhield

- Alle punten uit STATUS.md "Contract 1.2" en besluiten 1–7 + D10 zijn verwerkt (§1.1, §2.1–§2.3, §3, §4, §9, §12,
  §13). Besluit 2 (12.x) en 6 (tags) staan uitdrukkelijk buiten deze ronde.
- De testvectoren van §4.5 zijn met een eigen, los geschreven berekening (andere bit-extractie, zonder de Hub-code)
  opnieuw berekend: `MEGG-8GFG-2E4Y-K2RQ` en `CYRC-JS8C-14AN-JR17` kloppen, ook bij een andere volgorde van `jwks.keys`.
- De keuze dienst-JWT (Hub → dienst) i.p.v. het service-token in beide richtingen, pinning bij enrollment en opslag in
  `hub-link.json` zijn veiliger dan de alternatieven en uitvoerbaar met wat de diensten al hebben.
- Elke in de conformiteitslijst genoemde bestandsnaam bestaat in de betreffende repo.

## Wat niet standhield en hoe het is opgelost

1. **`app_id` = "TrueNAS-appnaam" was niet uitvoerbaar.** Een dienst kent zijn TrueNAS-appnaam niet; alle vier hebben
   een constante `APP_ID`. Kiest de gebruiker een andere naam, dan zou enrollment met 401 falen. → `app_id` is de
   vaste naam uit §2; de Hub houdt de werkelijke appnaam apart bij (gemeten, bevestigd). Eén instantie per `app_id`.
2. **`state: bezig` sprak §3.8 tegen** ("mislukt het, dan blijft een bestaande koppeling ongewijzigd"): bij opnieuw
   koppelen zou een gekoppelde dienst tijdelijk niet-gekoppeld zijn, en na een crash was onduidelijk wat geldt.
   Ook ontbrak wat een dienst doet als hij met een koppelcode herstart (het geheim is dan weg). → `pending` staat
   náást de stabiele `state`; stappen voor definitief mislukken en elke herstartvariant zijn vastgelegd;
   `previous_pins` en `last_error {code, at}` staan in het schema.
3. **JWK-regels waren half.** "`kid` = thumbprint" stond in het voorbeeld maar niet als regel; home-control-hub en
   appstore-en-fork sturen `use`/`alg` mee (appstore ook een andere `kid`), terwijl de Hub die nu stil weglaat en het
   contract ze met 422 weigert. jelly-leon-platform had dat na 1.2 al strikt gebouwd (ook in zijn Hub-simulator).
   → strikt gehouden (gelijk aan wat al gebouwd is, drift valt op): alleen `{kty, crv, x, kid}`, `kid` = thumbprint;
   HC1/AS1/H1 aangevuld. Een koppelcode die na normalisatie geen 12 Crockford-tekens is → 422.
4. **Rate-limit ±1.** "> 10 mislukte pogingen" terwijl de Hub bij 10 al weigert. → precies omschreven zoals gebouwd.
   Toegevoegd: diensten op één NAS delen bij de Hub mogelijk één bron-IP (NIET GEVALIDEERD).
5. **Rotatie kon een dienst buitensluiten.** Oude tokens vervielen vast 10 min na de rotatie; crasht een dienst
   tussen het ophalen en opslaan van het nieuwe token en is hij > 10 min weg, dan krijgt hij 401 → `ingetrokken`.
   → oud token geldig tot 10 min na het **eerste gebruik** van het nieuwe (max. 24 uur); de Hub vraagt opnieuw
   rotatie als een ouder token wordt gebruikt terwijl het nieuwste ongebruikt is.
6. **Automatische rotatie na 180 dagen botste met 03_RISICO_AUTONOMIE** ("secrets roteren" = R2, expliciete
   goedkeuring). → alleen een melding met knop; de Hub roteert nooit op eigen initiatief. Koppelen, ontkoppelen,
   intrekken, token- en sleutelrotatie en het noodaccount zijn uitdrukkelijk geen `action_id`'s (03: geen wijziging
   van beveiligingsbeleid of privileges door de AI).
7. **Elke 401 → `ingetrokken` was te bros** (een verkeerde `HUB_URL` of storing zou een dienst blijvend afsluiten).
   → eerst `GET /api/v1/services/self`; netwerkfouten, 5xx en 429 zijn nooit een intrekking. Een herhaalde `unlink`
   (401 `not_linked`) telt voor de Hub als geslaagd.
8. **Sleutelrotatie was niet ondertekenbaar zoals beschreven:** één statement met zowel jwt- als policy-wijzigingen
   kan niet door "een sleutel van hetzelfde doel" worden ondertekend. → één doel per statement (`purpose`), `typ` in de
   JWS-header, `sequence` zonder gaten, endpoint zonder authenticatie (ook voor bestaande apps met een geplakte
   sleutelset), en de Hub gebruikt een nieuwe sleutel pas als elke actieve dienst de rotatie meldt. Onbekende `kid`
   wacht niet op een poll (geen latentie of DoS in het verzoekpad). Nog niet gebouwd: het endpoint blijft een lege lijst.
9. **`reason`-waarden zonder betekenis.** → tabel per `reason` met controlevolgorde, zodat de vier diensten hetzelfde
   antwoorden.
10. **"Alles als 568" was niet waar in de images.** `dumb-init` (vier dienstimages, MSO) en `tini` (MediaGuard)
    blijven als root PID 1 met de Docker-standaardcapabilities; de rooktests slaan PID 1 over. Het contract eiste
    "daarna alles als 568" maar de rooktestregel zei "per dienstproces". → expliciet ook PID 1, rooktest op elk proces.
    De eigen rooktest van de Hub controleerde `CapEff` niet (wel Uid en NoNewPrivs): toegevoegd in `deploy/smoke.sh`.
11. **Executor-uitzondering (§3.9) was te omzeilen:** "een live geverifieerde schrijfkey" zonder vast NAS-adres laat
    iemand een eigen nep-TrueNAS opgeven. → verifiëren tegen het bij de eerste koppeling vastgelegde NAS-adres en
    TLS-certificaat (zoals ADR-0010 voor de Hub).
12. **Uitspraken over TrueNAS lazen als feiten.** "Catalogustreinen houden alleen de nieuwste versie" is in de bron
    een waarneming op één commit (onzeker); `use_all_gpus` "kan niet per GPU" komt uit de appstore-docs. → §2.2 begint
    met de bron en NIET GEVALIDEERD (echte NAS); ook de `ix-app`-versie zelf kan verdwijnen → `version_unavailable`
    (anders zou elke eigen installatie stil op een ongeteste `ix-app`-versie terechtkomen). Het bron-IP voor de
    noodlogin achter Docker-portpublicatie is NIET GEVALIDEERD; de zelftest toont het gemeten adres.
13. **Kleine onduidelijkheden:** `HUB_ENROLLMENT_TOKEN` heette "niet-geheim" (spreekt §3.1 tegen); Hub-adres op de
    statuspagina had geen regels (SSRF-achtig: willekeurig LAN-adres) → zelfde regels als `HUB_URL`, geen
    link-local, nooit redirects volgen; `/appdata/secrets` offsite alleen versleuteld (04_GEGEVENS_EN_STORAGE);
    besluit 1 noemde `app_search_suggest_intent_data` en de back-upregels niet (jelly-leon-clients ADR-0004 wel);
    `schema_version` in het enroll-antwoord nu "major 1" i.p.v. exact `"1.2"` (geen lockstep-upgrade).

## Conformiteitslijst

Bijgewerkt naar de echte stand per repo (commit genoemd). Ná het vaststellen van 1.2 waren al gebouwd:
jelly-leon-platform enroll-verzoek exact (`8c83aa6`) en 1 MiB-grens (`d5fda8a`); zoeken-en-persoonlijke-ai
`no_new_privs` + rooktest zoals het formulier (`72d3714`); jelly-leon CI groen (`d71439da0`); jelly-leon-clients
Android/Android TV lokaal gebouwd (`5ee6d91`). Nieuw gevonden: root-PID 1 (A6), `use`/`alg` in de JWK (HC1, AS1),
`details.max` i.p.v. `max_bytes` (ZA4), `portal.port` tegen `custom_app.ports` (M2), Hub-rooktest zonder `CapEff`.

## Gevolgen

- Geen nieuw versienummer; de kopie naar de andere repos (volgende stap) neemt deze tekst mee.
- Open blijven (ongewijzigd): scopes per dienst op de Hub-connector, pinning voor de Jelly Leon-plugin (P4), HTTPS op
  het LAN, `JL_SYNC_PUSH_TOKEN` (besluit 4), per-GPU-toewijzing via `privileges.devices` (B03/P4).
- Restrisico blijft: vóór de eerste koppeling kan iemand op het LAN een dienst via de statuspagina aan een eigen "Hub"
  koppelen (ADR-0011 punt 6).
