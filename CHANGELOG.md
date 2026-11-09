# Changelog

Alle noemenswaardige wijzigingen. Versies volgen `VERSION`; images krijgen exact deze tag (nooit `latest`).

## [0.1.0] — 2026-11-09 (fase P0, backend; niet uitgebracht)

### Toegevoegd
- Hub-API (`hub`): FastAPI + SQLAlchemy 2 + Alembic + pydantic-settings; processen `api`, `worker`, `ai-runner`
  (stub, aparte gebruiker 569 zonder toegang tot geheimen), `init`, `migrate`, `backup-now`, `export-openapi`.
- First-start-init: ontbrekende geheimen in `/appdata/secrets` (0600, nooit overschrijven; Ed25519 voor identiteit,
  JWT en policy; `vault.key`), eenmalige setupcode in de app-log.
- Aanmelden: setupcode → eerste admin; login/logout (argon2id, rate-limit), sessies met CSRF, rollen
  admin/operator/viewer/kind, sessies intrekken, JWKS en dienst-JWT (EdDSA, exp ≤ 120 s).
- Enrollment: eenmalige enrollment-tokens (60 min) en koppelcodes, service-tokens (alleen hashes), rotatie met
  overgangstijd, intrekken.
- Onboarding-wizard-API voor D01–D18 met getypte waarden, bewijs, metingen via TrueNAS-readback en `GET /api/v1/gates`.
- Alleen-lezen TrueNAS JSON-RPC-adapter (wss, TLS-verificatie of bevestigde vingerafdruk, capability-map per versie,
  reason codes), inventaris met `observed_at`/veroudering, dienstenregister.
- Back-up en herstel: dekking per app/dataset, snapshotbeleid als voorstel, geverifieerde pg_dump van de eigen database,
  hersteltests als bewijsrecord.
- Events-inbox met dedupe, connectorcontract van de Hub, OpenAPI-export.
- Executor (P0): statuspagina "nog niet gekoppeld", allowlist die alles weigert.
- Alles-in-één Hub-image en executor-image (supervisor als PID 1, na de init geen root-proces), Custom App-formulieren,
  manifesten, CI (lint, types, tests met PostgreSQL, migraties, OpenAPI-drift, pip-audit, images + rooktest) en
  release-workflow (GHCR, SBOM, digests).

### Validatie
Sim-getest en tegen een echte PostgreSQL 16 getest; images gebouwd en gestart in Docker. **NIET GEVALIDEERD op een
echte NAS.**
