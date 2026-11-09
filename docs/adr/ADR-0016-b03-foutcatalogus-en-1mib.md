# ADR-0016 — Eén foutcatalogus; 1 MiB per route als erkende afwijking (B03)

Status: aangenomen · 2026-11-09 · overgenomen uit ADR-B03-05 van het goedgekeurde B03 2.0-plan (`docs/platform-v2/02_BOUWPLANNEN/B03_UNIVERSELE_MEDIASERVER.md` §10.3) · de foutcodes zijn die van de platformreferentie in deze repo (`apps/api/src/hub/deps.py`, `errors.py`); uitvoering in jelly-leon (B03-017).
Contractwijzigingen die hieruit volgen (Δ-…, hoofdstuk 18 van het bouwplan) zijn nog niet in `PLATFORM_CONTRACTEN.md`
doorgevoerd; dat gebeurt als eigen stap met review.
Herkomst: Jurypunten J-COMPAT A-4/A-5, J-BESCH A12/A13, J-TEST H-ALG-10.

- **Werkpakket:** B03-017; test JLT-68.

## Context

- Contract §5 legt de foutvorm vast (`{code, message, details, trace_id}`), `Idempotency-Key` op mutaties en een grens van
  1 MiB **vóór routering en authenticatie**.
- De plandelen gebruikten verschillende codes voor dezelfde situatie: een hergebruikte sleutel gaf 409
  `idempotency_conflict` (F1, F3, F5, F6) of 422 `idempotency_key_reused` (F2, F4); een ontbrekende sleutel 422 of 400.
- De referentie-implementatie van het platform (`ai-server-manager/apps/api/src/hub/deps.py:195-235`, `errors.py`; ook in
  jelly-leon-platform) gebruikt 400 `idempotency_key_required`, 400 `idempotency_key_invalid`, 422
  `idempotency_key_reused`, 409 `idempotency_in_progress`, 422 `validation_error`, 412 `precondition_failed`.
- Een plugin in het Jellyfin-proces kan geen laag vóór routering en authenticatie garanderen zonder een
  `IStartupFilter`; of dat vanuit een plugin werkt, is niet geverifieerd.

## Besluit

1. Alle modules gebruiken **de codes van de platformreferentie** (tabel in §10.3 van het bouwplan), aangevuld met 428
   `precondition_required`, 423 `item_in_playback`, 413 `payload_too_large`, 429 `rate_limited`, 501
   `capability_unavailable` en 503 `<afhankelijkheid>_unavailable` (generiek `dependency_unavailable`). Module-eigen
   situaties gebruiken `details.reason` of een eigen code onder 409; nooit een tweede code voor een gedeelde situatie.
2. Een herhaling met dezelfde sleutel en body geeft het oorspronkelijke antwoord met `Idempotent-Replay: true`.
3. **1 MiB:** `RequestSizeLimit(1048576)` per route plus een `Content-Length`-controle; de afwijking "na authenticatie" is
   erkend tot de gezamenlijke `IStartupFilter`-spike slaagt; dan geldt "vóór auth". Hogere grenzen alleen per route met
   een eigen bovengrens in deze ADR (F6-import: 32 MiB).
4. Eén OpenAPI-bestand `docs/openapi/jelly-leon-plugin.openapi.json` met driftcontrole in CI (ADR-0010).
5. De functiehoofdstukken in het bouwplan zijn hierop mechanisch gelijkgetrokken (Bijlage B, B3/B4).

## Alternatieven

- *409 `idempotency_conflict` (meerderheid van de plandelen):* gangbaar, maar wijkt af van de bestaande platformcode; de Hub
  en de diensten zouden dan twee betekenissen kennen. Verworpen.

## Gevolgen

- Eén contracttestsuite voor alle modules; clients (Hub, webplugins) hoeven maar één tabel te kennen.
- Een aanvaller kan een groot verzoek naar een plugin-route sturen dat pas na de authenticatie wordt afgekapt; de
  Kestrel-limiet van Jellyfin blijft daarvoor de grens. Dit restrisico staat in de ADR tot de spike.

## Verificatie

JLT-68 (zelfde code voor dezelfde situatie in elke module; 413 per route), contracttests per module.
