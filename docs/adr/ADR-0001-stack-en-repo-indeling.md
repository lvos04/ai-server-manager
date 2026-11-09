# ADR-0001 — Stack, repo-indeling en vastgezette afhankelijkheden

Status: aangenomen · 2026-11-09 · fase P0

## Context
Platformcontract 1.1 §1/§10 legt de stack (Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16) en de
repo-indeling vast. Er werken meerdere bouwers tegelijk; reproduceerbare builds zijn verplicht (geen `latest`).

## Besluit
- `apps/api` bevat pakket `hub` (`src/hub`), migraties in `apps/api/alembic` (in de wheel meegenomen als
  `hub/_alembic`, zodat de image migreert zonder broncode), tests in `apps/api/tests/{unit,integration}`.
- `apps/executor` is een eigen pakket en eigen image (contract §2); `tests/e2e` + `tests/fakes` bevatten de dienst-E2E
  met de fake TrueNAS. `apps/web` (PWA) volgt; de Dockerfile heeft er een gemarkeerde plek voor.
- Afhankelijkheden staan exact in `pyproject.toml`; `requirements.lock` (runtime, incl. transitieve pakketten,
  gegenereerd in een schone venv) en `requirements-dev.lock` (CI-gereedschap). De images installeren met `--no-deps`
  uit het lockbestand en controleren met `pip check` (dat ving een ontbrekende transitieve afhankelijkheid).
- Base-images op exacte versie én `@sha256`-digest (`python:3.12.16-slim-bookworm`, `postgres:16.15-bookworm`);
  GitHub Actions op commit-SHA.
- Eén Alembic-migratie per schemawijziging; CI controleert upgrade → downgrade → upgrade en `alembic check`
  (modellen = migraties).

## Gevolgen
Versie-updates gaan bewust: lock opnieuw maken, `pip-audit`, CI. Tests importeren in `importlib`-modus omdat er twee
testmappen naast elkaar staan.
