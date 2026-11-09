"""De web-UI test haar schemaformulier tegen een kopie van de besluitschema's; die kopie mag niet afdrijven."""

from __future__ import annotations

import json
from pathlib import Path

from hub.onboarding.catalog import DECISIONS, schema_json

FIXTURE = Path(__file__).resolve().parents[3] / "web" / "tests" / "unit" / "fixtures" / "decision-schemas.json"


def test_web_fixture_gelijk_aan_catalogus() -> None:
    actual = {d.id: schema_json(d.id) for d in DECISIONS}
    stored = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert stored == actual, (
        "apps/web/tests/unit/fixtures/decision-schemas.json is verouderd; maak hem opnieuw "
        "(zie apps/web/README.md, 'Schemafixture')."
    )
