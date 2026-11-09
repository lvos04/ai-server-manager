# ADR-0014 — Onafhankelijke review van contract 1.2 in de Hub en de executor

Status: aangenomen · 2026-11-09 · ronde "contract 1.2 toepassen", reviewstap · bij `CONTRACT_1.2_CONFORMITEIT.md` §1
Vult ADR-0013 aan en vervangt daar de laatste zin van punt 8 (geen `jti`-replaycache in de executor).

## Context

Na de bouwstap (ADR-0013) zijn de Hub en de executor opnieuw nagelopen tegen `PLATFORM_CONTRACTEN.md` §1–§13 en de
acceptatiecriteria, met de tests zoals de CI ze draait. De meeste punten klopten en waren met positieve én negatieve
tests afgedekt. Hieronder staan de afwijkingen die gevonden en gerepareerd zijn, en de keuzes die daarbij zijn gemaakt.

## Bevindingen en besluiten

1. **1 MiB-grens zat niet altijd vóór routering en authenticatie (§5).** De Hub telde de body pas als een route hem
   las. Een chunked verzoek van meer dan 1 MiB zonder aanmelding op een route zonder body-parameter gaf daardoor `401`,
   en op een onbekende methode `405`, in plaats van `413`. De 413-body had ook geen `details.max_bytes`. De executor
   keek alleen naar `Content-Length` en had dus geen grens voor chunked verzoeken.
   *Besluit:* in beide apps leest een ASGI-laag (`hub/app.py` `BodyLimit`, `executor/bodylimit.py`) de body vóór alles,
   met hooguit 1 MiB in het geheugen. Komt er meer binnen, dan antwoordt de laag direct met
   `413 {"code":"payload_too_large","details":{"max_bytes":1048576}}`. De app krijgt daarna de gebufferde body. Een
   ongeldige `Content-Length` geeft `400`. Verbreekt de client de verbinding vóór de body compleet is, dan wordt er
   niets uitgevoerd.
   *Afweging:* elk verzoek wordt eerst volledig gelezen. Dat kost per gelijktijdig verzoek hooguit 1 MiB geheugen. De
   apps hebben geen uploads of streams boven die grens (gecontroleerd). Een hogere grens per route vraagt volgens §5 een
   eigen ADR.
2. **De executor had geen `jti`-replaycache (§4.6).** `POST /connector/v1/hub-link/unlink` is een mutatie die Hub-JWT's
   accepteert. ADR-0013 vond een cache nog niet nodig, omdat de route altijd `501` geeft. Maar §4.6 eist de controle per
   mutatie, en de route controleerde ook `Idempotency-Key` en de rol `admin` niet (§3.8, §6).
   *Besluit:* een persistente replaycache in `/appdata/executor.sqlite3` (0600, WAL, `BEGIN IMMEDIATE`; buiten
   `secrets/`, er staan geen geheimen in), sleutel `(iss, jti)`, bewaard tot `exp` + 30 s.
   - Volgorde op de mutatie: auth (§4.7) → rol → `Idempotency-Key` (UUID, verplicht) → replaycontrole → handeling.
   - Exacte herhaling (zelfde `jti`, methode, pad en key): het opgeslagen antwoord met `Idempotent-Replay: true`.
   - Zelfde `jti` met een andere key, methode of pad: `401 token_replayed`.
   - Exacte herhaling terwijl het eerste verzoek nog loopt: `409 idempotency_in_progress` (zelfde code als de Hub). Het
     contract regelt dit geval niet; dit is de veiligste lezing.
   - Cache onbruikbaar: `503 replay_check_unavailable` (fail-closed). Lezen (GET) gaat niet langs de cache.
   De nonce-controle van `ExecutionRequest` (§8, P2) kan dezelfde SQLite-database gebruiken.
3. **De rol `kind` won niet altijd (§4.2).** Op de executor gaf een gebruikers-JWT met `roles: ["kind","admin"]` toegang
   tot `GET /connector/v1/hub-link`. *Besluit:* `user_rank` geeft `kind` (rang 0) zodra `kind` voorkomt; onbekende rollen
   tellen niet. `unlink` vraagt rang `admin` (of een dienst-JWT).
4. **`iat` in de toekomst werd geaccepteerd (§4.7 `invalid_token`).** *Besluit:* `iat` of `nbf` later dan nu + 30 s,
   `exp` vóór `iat`, of een `bool` als tijd → `invalid_token`.
5. **De CI-controle na een downgrade deed niets.** `! python -m hub migrate --check` in `ci.yml` zet `errexit` uit
   (actionlint/shellcheck SC2251). Daardoor faalde de stap nooit, ook niet als `--check` ten onrechte "actueel" meldde.
   *Besluit:* een expliciete `if …; then exit 1; fi`.
6. **Via de webpoort werd een vroeg 413-antwoord vaak een 502.** De Node-doorgang (`apps/web/server/hub-server.mjs`)
   stuurde de body door naar de API. Zodra de API met 413 antwoordde en de verbinding sloot, kreeg het schrijven een
   fout en maakte de doorgang er `502 api_unavailable` van ("Hub-API niet bereikbaar"). Gemeten tegen de image: bij een
   chunked upload van 3 MB was dat 18 van de 25 keer zo. Rechtstreeks op uvicorn gebeurde het niet.
   *Besluit:* de doorgang telt zelf mee (`bodyCounter`, `declaredTooLarge` in `proxy.mjs`). Boven 1 MiB antwoordt hij
   met dezelfde 413-body als de API, breekt de verbinding naar de API af en gooit de rest van de body weg, zodat de
   client het antwoord gewoon leest. Na de reparatie: 50 van de 50 keer `413` (3 MB en 20 MB). De grens in de API blijft
   staan als tweede laag.
7. **Testgaten gedicht.** Toegevoegd zijn tests voor:
   - de 413-grens vóór aanmelding en routering (Hub en executor, chunked en met `Content-Length`, grenswaarde precies
     1 MiB), in vitest voor de doorgang, en in de rooktest (5× 3 MB via de webpoort en op de executor);
   - een hergebruikte `jti`, ook na een herstart;
   - een gewisselde Hub-sleutel op de mutatie;
   - koppelen na de eerste koppeling met een geldige formuliercode van vóór die koppeling, ook na intrekken (`409`, en
     geen verzoek naar de Hub);
   - een verlopen executor-koppelcode.

## Gevolgen

- Gedrag voor geldige verzoeken is ongewijzigd; alleen te grote verzoeken krijgen eerder en consequenter `413`.
- De executor maakt bij de eerste muterende aanroep `/appdata/executor.sqlite3` aan (eigenaar 568, 0600).
- Alles blijft **Sim-getest**: echte PostgreSQL, de echte Hub-API en de executor via uvicorn en in de images; niets is
  op een echte NAS getest.
