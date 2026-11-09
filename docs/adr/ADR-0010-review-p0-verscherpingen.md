# ADR-0010 — Verscherpingen uit de onafhankelijke review van fase P0

Status: aangenomen · 2026-11-09 · fase P0 (review) · **contractpunten gemeld**

## Context
De onafhankelijke review van P0 (backend + web-UI + images) vond een paar plekken waar het gedrag niet de veiligste
interpretatie van het contract volgde of waar een acceptatiecriterium niet door een test werd afgedekt.

## Besluiten
1. **Setupcode echt eenmalig, ook bij gelijktijdige verzoeken.** `POST /api/v1/setup/admin` neemt een
   `pg_advisory_xact_lock` en controleert pas daarna of er al een beheerder is. Twee gelijktijdige verzoeken met dezelfde
   geldige code gaven eerder twee beheerders. Bestaat er al een beheerder maar ontbreekt `secrets/setup-completed`
   (bv. stroomuitval tussen commit en markering), dan herstelt de Hub die markering, zodat `hub init` nooit meer een
   onbruikbare setupcode in de log zet.
2. **1 MiB per verzoek, ook zonder `Content-Length`.** Een ASGI-laag telt de body tijdens het lezen en breekt af met
   `413 payload_too_large`; eerder werd alleen de header gecontroleerd en kon een chunked verzoek onbeperkt groot zijn.
3. **Rate-limit op `POST /api/v1/auth/password`.** Het huidige wachtwoord valt onder dezelfde grens als inloggen, zodat
   het met een overgenomen sessie niet te raden is.
4. **`no-new-privileges` in de images zelf.** Contract §10 vraagt `no-new-privileges`; het standaard Custom
   App-formulier kan die vlag (volgens de overdrachtsnotities) niet zetten. De bewaker van de Hub en het entrypoint van
   de executor zetten daarom `prctl(PR_SET_NO_NEW_PRIVS)` direct na de gebruikerswissel; alle processen erven het. De
   rooktest controleert `NoNewPrivs: 1` per proces (processen van `docker exec`/healthcheck zelf tellen niet mee).
5. **Rooktest = herstart zonder dataverlies.** `deploy/smoke.sh` (ook in CI) maakt nu via de setupcode uit de log de
   eerste beheerder aan, controleert dat de code eenmalig is, herstart en kill-t beide containers hard en controleert
   daarna: setup blijft afgerond, inloggen werkt, geen nieuwe setupcode, executor-identiteit ongewijzigd, oude
   `postmaster.pid` opgeruimd.
6. **Rechtenmatrix over alle routes.** `apps/api/tests/integration/test_route_authz.py` legt per route de minimale rol
   vast (bron: het OpenAPI-schema). Een nieuwe route zonder expliciete keuze laat de test falen. Zonder aanmelding
   → 401 op elke niet-publieke route; te lage rol → 403; service-token op een gebruikersroute → 403.
7. **CI slaat nooit stil over.** Zonder bereikbare PostgreSQL faalt de integratiefixture in CI (`CI`/`HUB_TEST_REQUIRE_PG`)
   in plaats van alle integratie- en E2E-tests over te slaan.

## Gevolgen
- Geen API-vorm gewijzigd (OpenAPI ongewijzigd); alleen strenger gedrag.
- Contractpunt (open): `GET /connector/v1/items?type=decision` geeft elke ingeschreven dienst alle besluiten (o.a. het
  NAS-adres uit D03). Het contract noemt "scopes gerespecteerd" maar definieert geen scopes; tot contract 1.2 dat doet,
  blijft het lezen voor ingeschreven diensten zoals het is (geen geheimen; credentials staan alleen in de vault).
