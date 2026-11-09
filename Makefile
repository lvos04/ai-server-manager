# AI Server Manager — ontwikkeltaken. Zwaar werk met beperkt parallelisme (gedeelde bouwomgeving).
PY ?= python3.12
VENV ?= .venv
BIN ?= $(abspath $(VENV)/bin)
NICE := nice -n 10
API := apps/api
EXE := apps/executor
comma := ,
CA_SECRET := $(if $(wildcard /root/.ccr/ca-bundle.crt),--secret id=ca_bundle$(comma)src=/root/.ccr/ca-bundle.crt,)
PROXY_ARGS := $(if $(HTTPS_PROXY),--network host --build-arg HTTPS_PROXY=$(HTTPS_PROXY),)

WEB := apps/web
NPM := cd $(WEB) && NEXT_TELEMETRY_DISABLED=1

.PHONY: venv lint format type test test-unit test-integration test-e2e migrate-check openapi openapi-check audit \
        image-hub image-executor images smoke lock clean runbooks \
        web-install web-lint web-test web-build web-e2e web-audit web-schema-fixture

venv:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -q -r $(API)/requirements.lock -r $(API)/requirements-dev.lock
	$(BIN)/pip install -q --no-deps -e $(API) -e $(EXE)

lint:
	cd $(API) && $(BIN)/ruff check src alembic tests ../../tests ../../conftest.py && $(BIN)/ruff format --check src alembic tests ../../tests ../../conftest.py
	cd $(EXE) && $(BIN)/ruff check src tests && $(BIN)/ruff format --check src tests

format:
	cd $(API) && $(BIN)/ruff format src alembic tests ../../tests ../../conftest.py
	cd $(EXE) && $(BIN)/ruff format src tests

type:
	cd $(API) && $(NICE) $(BIN)/mypy
	cd $(EXE) && $(NICE) $(BIN)/mypy

test:
	$(NICE) $(BIN)/pytest

test-unit:
	$(BIN)/pytest $(API)/tests/unit $(EXE)/tests

test-integration:
	$(NICE) $(BIN)/pytest $(API)/tests/integration

test-e2e:
	$(NICE) $(BIN)/pytest tests/e2e

openapi:
	$(BIN)/python -m hub export-openapi --out docs/openapi/hub-api.openapi.json
	$(BIN)/python -m executor export-openapi --out docs/openapi/executor.openapi.json

openapi-check:
	$(BIN)/python -m hub export-openapi --out docs/openapi/hub-api.openapi.json --check
	$(BIN)/python -m executor export-openapi --out docs/openapi/executor.openapi.json --check

runbooks:
	$(BIN)/python -m hub export-runbooks --out docs/RUNBOOKS.md

audit:
	$(BIN)/pip-audit --strict -r $(API)/requirements.lock -r $(EXE)/requirements.lock

image-hub:
	$(NICE) docker buildx build --load $(PROXY_ARGS) $(CA_SECRET) -f deploy/allinone/Dockerfile -t ai-server-manager:dev .

image-executor:
	$(NICE) docker buildx build --load $(PROXY_ARGS) $(CA_SECRET) -f deploy/executor/Dockerfile -t ai-server-manager-executor:dev .

images: image-hub image-executor

smoke:
	bash deploy/smoke.sh ai-server-manager:dev ai-server-manager-executor:dev

lock:
	@echo "Lockbestanden opnieuw maken: schone venv, exacte versies uit pyproject.toml, daarna pip freeze."
	@echo "Zie docs/adr/ADR-0001-stack-en-repo-indeling.md (afhankelijkheden)."

# ------------------------------------------------------------------ web-UI (apps/web)
web-install:
	$(NPM) npm ci --no-audit --no-fund

web-lint:
	$(NPM) npx eslint --max-warnings=0 . && npx tsc --noEmit

web-test:
	$(NPM) npx vitest run

web-build:
	$(NPM) $(NICE) npx next build

# Playwright (360/390/768/1440) tegen de echte API + fake TrueNAS; start zelf de teststack en de productie-build.
web-e2e: web-build
	$(NPM) HUB_E2E_PYTHON=$(BIN)/python $(NICE) npx playwright test

web-audit:
	$(NPM) npm audit --omit=dev --audit-level=high

# Kopie van de besluitschema's voor de unittests van het schemaformulier (test_web_schema_fixture bewaakt drift).
web-schema-fixture:
	$(BIN)/python -c "import json; from hub.onboarding.catalog import DECISIONS, schema_json; \
	print(json.dumps({d.id: schema_json(d.id) for d in DECISIONS}, indent=2, ensure_ascii=False, sort_keys=True))" \
	> $(WEB)/tests/unit/fixtures/decision-schemas.json

clean:
	find . -name __pycache__ -not -path './$(VENV)/*' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache $(API)/.mypy_cache $(EXE)/.mypy_cache
	rm -rf $(WEB)/.next $(WEB)/test-results $(WEB)/playwright-report
	docker image prune -f
