"""Leesgrenzen van de my_house-adapter."""

import ast
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from hub.adapters import my_house


def test_module_bevat_uitsluitend_toegelaten_routes() -> None:
    source = Path(my_house.__file__).read_text()
    assert not re.search(r"/(?:command|resume|ack|audit|diagnostics|backups?|users)(?:\b|/)|/lights/groups", source)
    tree = ast.parse(source)
    paths = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/api/")
    }
    assert paths == {
        "/api/v1/health",
        "/api/v1/pairing/identity",
        "/api/v1/pairing/redeem",
        "/api/v1/clients/self/refresh",
        "/api/v1/system/status",
        "/api/v1/homes",
        "/api/v1/homes/{home_id}/zones",
        "/api/v1/homes/{home_id}/lights",
        "/api/v1/homes/{home_id}/alerts",
        "/api/v1/homes/{home_id}/devices",
        "/api/v1/system/settings",
    }


def test_link_vereist_geldig_schema_en_bevestigde_bestemming() -> None:
    base = "https://woning.example"
    assert my_house.user_link(base, "javascript:open()", None) is None
    assert my_house.user_link(base, "https://andere-woning.example", None) is None
    assert my_house.user_link(base, "https://woning.example/?", None) is None
    assert my_house.user_link(base, "javascript:open()", f"{base}/") == base


@pytest.mark.parametrize("bron", ["zigbee", "worker", "backup"])
def test_gezondheid_gebruikt_de_kortere_brongrens(bron: str) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    worker = {"key": "worker", "state": "ok"}
    checks = [{"key": "database", "state": "ok"}, worker]
    if bron == "zigbee":
        integration = f"integration:{uuid4()}"
        checks.extend(
            [
                {
                    "key": integration,
                    "state": "ok",
                    "provider": "zigbee",
                    "details": {"checked_at": (now - timedelta(seconds=175)).isoformat()},
                },
                {"key": f"{integration}:mqtt", "state": "ok"},
            ]
        )
        seconds = 6
    elif bron == "worker":
        worker["age_s"] = 114
        seconds = 6
    else:
        checks.append({"key": "backup", "state": "ok", "age_h": 35.9})
        seconds = 181
    _, readings = my_house._system_readings({"version": "1.0.0", "checks": checks}, now)
    assert my_house.health(readings, now).status == "healthy"
    expired = my_house.health(readings, now + timedelta(seconds=seconds))
    assert (expired.status, expired.reason_code) == ("unknown", "meting_verouderd")
    if bron == "zigbee":
        assert [check.project(now + timedelta(seconds=seconds)).state for check in readings[-2:]] == [
            "unknown",
            "unknown",
        ]
