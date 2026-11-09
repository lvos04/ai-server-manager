# ADR-0006 — Idempotency-Key en endpoints die geheimen teruggeven

Status: aangenomen · 2026-11-09 · fase P0 · **contractpunt gemeld** · bijgewerkt voor contract 1.2 (ADR-0013)

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
  `services/self/rotate` en (contract 1.2) `auth/break-glass/setup`, `auth/break-glass/rotate`,
  `auth/break-glass/confirm`, `auth/break-glass/login`. Die zijn eenmalig van aard (single-use token, TOTP-code) of
  geven bij elke aanroep bewust een nieuw geheim. Gaat een antwoord met een geheim verloren, dan maakt de beheerder een
  nieuw token/koppelcode. `auth/break-glass/selftest` muteert niets en heeft daarom geen key nodig.
- **Contract 1.2 — `POST /services/{id}/rotate` (admin)** geeft geen geheim meer terug: het **vraagt** rotatie aan
  (`202`) en eist daarom nu een `Idempotency-Key` (zoals `revoke`, `unlink` en `truenas-app`).
- **Contract 1.2 — herhaling van `services/enroll` (§3.6)** loopt niet via `Idempotency-Key` (die wordt genegeerd) maar
  via de grant zelf: zelfde token/koppelcode, `app_id` en sleutel-thumbprint, binnen 60 min, en het via die grant
  uitgegeven token is nog nooit gebruikt (`first_used_at`/`last_used_at` leeg). Dan trekt de Hub het ongebruikte token
  in en geeft een nieuw uit (`enrollment_replayed: true`); de grant-rij wordt daarbij vergrendeld (`FOR UPDATE`), zodat
  twee gelijktijdige pogingen na elkaar worden beoordeeld. Zodra de dienst zijn token gebruikt
  (`GET /services/self`), is de herhaling dicht.
- `events/inbox`: het `event_id` en `(source_app, source_event_id)` zijn de natuurlijke idempotency-sleutel (dedupe).
