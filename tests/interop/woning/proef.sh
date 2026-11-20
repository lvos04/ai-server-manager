#!/usr/bin/env bash
# Draai met de testomgeving van elke app en een lokale PostgreSQL-testserver.
set -euo pipefail
hub=$(git rev-parse --show-toplevel)
huis=$(realpath "${MY_HOUSE_SOURCE:?pad naar de my_house-werkkopie}")
proeven="$hub/tests/interop/woning"
werk=$(mktemp -d)
trap 'rm -rf -- "$werk"' EXIT
hub_python=${HUB_PYTHON:-"$hub/.venv/bin/python"}
huis_python=${MY_HOUSE_PYTHON:-"$huis/.venv/bin/python"}
export HUB_TEST_REQUIRE_PG=1
mkdir -p "$werk"/{hub,huis,oud,nieuw,tests}
git -C "$hub" archive 63e2b136fdda77dd6809cc19b1beb3bb4114c58a | tar -x -C "$werk/hub"
git -C "$huis" archive c296859a5a99d550b97367f93ac56d0db9cf9c89 apps/api integrations | tar -x -C "$werk/huis"
cp "$proeven"/{bron,kijkroute}.py "$werk/tests/"
cd "$werk/tests"
for versie in oud nieuw; do
    bron="$huis"
    if [[ $versie == oud ]]; then bron="$werk/huis"; fi
    WONING_ANTWOORDEN="$werk/$versie" PYTHONPATH="$bron/apps/api/tests:$bron/apps/api/src:$bron/integrations/src" \
        "$huis_python" -m pytest -q -p no:cacheprovider -p conftest -c "$bron/apps/api/pyproject.toml" bron.py
done
resultaat=0
for versie in oud nieuw; do
    bron="$hub"
    if [[ $versie == oud ]]; then bron="$werk/hub"; fi
    WONING_HUB="$versie" WONING_ANTWOORDEN="$werk" \
        PYTHONPATH="$bron:$bron/tests:$bron/apps/api/tests/integration:$bron/apps/api/src:$bron/apps/policy/src:$bron/apps/executor/src" \
        "$hub_python" -m pytest -v -p conftest -p test_adapterkoppelingen -c "$bron/pytest.ini" kijkroute.py || resultaat=1
done
exit "$resultaat"
