# AI Server Manager — ontwikkeltaken. Zwaar werk met beperkt parallelisme (gedeelde bouwomgeving).
PY ?= python3.12
VENV ?= .venv
BIN ?= $(abspath $(VENV)/bin)
NICE := nice -n 10
API := apps/api
EXE := apps/executor
CA_SECRET := $(if $(wildcard /root/.ccr/ca-bundle.crt),--secret id=ca_bundle,src=/root/.ccr/ca-bundle.crt,)
PROXY_ARGS := $(if $(HTTPS_PROXY),--network host --build-arg HTTPS_PROXY=$(HTTPS_PROXY),)

.PHONY: venv lint format type test test-unit test-integration test-e2e migrate-check openapi openapi-check audit \
        image-hub image-executor images smoke lock clean

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

clean:
	find . -name __pycache__ -not -path './$(VENV)/*' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache $(API)/.mypy_cache $(EXE)/.mypy_cache
	docker image prune -f
