# ADR-0006 — Idempotency-Key en endpoints die geheimen teruggeven

Status: aangenomen · 2026-11-09 · fase P0 · **contractpunt gemeld**

## Context
Contract §5: mutaties vereisen `Idempotency-Key`; herhaling geeft hetzelfde antwoord zonder tweede uitvoering. Daarvoor
moet het antwoord worden opgeslagen. Sommige antwoorden bevatten een geheim (sessietoken, enrollment-token,
koppelcode, service-token) en contract §3 staat alleen hashes in tabellen toe.

## Besluit
- Alle overige mutaties eisen een UUID in `Idempotency-Key` (anders `400 idempotency_key_required`); het antwoord wordt
  in dezelfde transactie als de wijziging opgeslagen; hergebruik met een ander verzoek → `422 idempotency_key_reused`;
  replay draagt `Idempotent-Replay: true`. Bewaartermijn 24 uur.
- Uitgezonderd (key optioneel, antwoord niet opgeslagen): `setup/admin`, `auth/login`, `auth/logout`,
  `auth/password`, `auth/service-jwt`, `services/enrollment-tokens`, `services/pairing-codes`, `services/enroll`,
  `services/*/rotate`. Die zijn eenmalig van aard (single-use token) of geven bij elke aanroep bewust een nieuw geheim.
  Gaat een antwoord met een geheim verloren, dan maakt de beheerder een nieuw token/koppelcode.
- `events/inbox`: het `event_id` en `(source_app, source_event_id)` zijn de natuurlijke idempotency-sleutel (dedupe).
