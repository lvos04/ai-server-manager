"""Leesgrenzen van de my_house-adapter."""

import ast
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from hub.adapters import my_house


@pytest.mark.parametrize(
    ("veld", "verwacht"),
    [
        ({}, None),
        ({"on": None}, None),
        ({"on": "false"}, None),
        ({"on": 0}, None),
        ({"on": False}, False),
        ({"on": True}, True),
    ],
)
def test_lichtstand_is_alleen_een_expliciete_boolean(veld: dict[str, Any], verwacht: bool | None) -> None:
    light = my_house.Light.model_validate({"id": str(uuid4()), "name": "Proeflicht", **veld}, strict=True)
    assert light.on is verwacht


@pytest.mark.parametrize("temperatuur", [None, {}, {"value": 0, "at": "ongeldig"}])
def test_ongeldige_sensor_laat_andere_zonemetingen_staan(temperatuur: Any) -> None:
    nu = datetime.now(UTC)
    zone = my_house.Zone.model_validate(
        {
            "id": str(uuid4()),
            "name": "Proefzone",
            "unit_status": "online",
            "online": True,
            "mode": "heat",
            "temperature": temperatuur,
            "humidity": {
                "value": 42,
                "unit": "%",
                "quality": "measured",
                "at": nu.isoformat(),
                "stale": False,
            },
            "target_c": 21,
            "target_at": nu.isoformat(),
        },
        strict=True,
    )
    assert zone.temperature.value is None and zone.temperature.quality == "missing"
    assert zone.humidity.value == 42 and zone.target_at == nu


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
    worker = {"key": "worker", "state": "ok", "age_s": 0}
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
    _, readings = my_house._system_readings({"version": "1.0.0", "checks": checks}, now, now)
    assert my_house.health(readings, now).status == "healthy"
    expired = my_house.health(readings, now + timedelta(seconds=seconds))
    assert (expired.status, expired.reason_code) == ("unknown", "meting_verouderd")
    if bron == "zigbee":
        assert [check.project(now + timedelta(seconds=seconds)).state for check in readings[-2:]] == [
            "unknown",
            "unknown",
        ]


@pytest.mark.parametrize(
    ("state", "age_s"),
    [("ok", age_s) for age_s in (None, True, "118", 118.0, -1, 120, 2**64)]
    + [("error", age_s) for age_s in (None, True, "120", 120.0, -1, 119, 2**64)],
)
def test_ongeldige_workerleeftijd_is_onbekend(state: str, age_s: Any) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    checks = [{"key": "database", "state": "ok"}, {"key": "worker", "state": state, "age_s": age_s}]
    _, readings = my_house._system_readings({"version": "1.0.0", "checks": checks}, now, now)
    assert readings[1].project(now).state == "unknown"
    health = my_house.health(readings, now)
    assert (health.status, health.reason_code) == ("unknown", "meettijd_onbekend")


def test_worker_118_seconden_is_nog_een_seconde_vers_vanaf_verzoekstart() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    grens = now + timedelta(seconds=1)
    checks = [{"key": "database", "state": "ok"}, {"key": "worker", "state": "ok", "age_s": 118}]
    _, readings = my_house._system_readings({"version": "1.0.0", "checks": checks}, now, grens)
    assert readings[1].project(grens).state == "ok"
    health = my_house.health(readings, grens + timedelta(microseconds=1))
    assert (health.status, health.reason_code) == ("unknown", "meting_verouderd")
    assert health.observed_at == now - timedelta(seconds=119)


def test_workeruitval_bewaart_hartslag_en_foutmeting_apart() -> None:
    verzoek = datetime(2026, 1, 1, tzinfo=UTC)
    ontvangst = verzoek + timedelta(seconds=2)
    checks = [{"key": "database", "state": "ok"}, {"key": "worker", "state": "error", "age_s": 241}]
    _, readings = my_house._system_readings({"version": "1.0.0", "checks": checks}, verzoek, ontvangst)
    fout = readings[1]
    assert fout.worker_observed_at == verzoek - timedelta(seconds=242)
    assert fout.worker_error_observed_at == verzoek
    assert fout.measurement(ontvangst).status == "down"
    assert fout.measurement(ontvangst).observed_at == verzoek


def test_opgeslagen_workercheck_zonder_bronmeettijd_is_onbekend() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    readings = my_house.CheckReadings.validate_python(
        [
            {"key": "database", "state": "ok", "observed_at": now, "max_age_s": 900},
            {"key": "worker", "state": "ok", "observed_at": now, "max_age_s": 120},
        ]
    )
    assert readings[0].project(now).state == "ok"
    assert readings[1].project(now).state == "unknown"
    health = my_house.health(readings, now)
    assert (health.status, health.reason_code) == ("unknown", "meettijd_onbekend")


def test_oude_workeruitval_zonder_foutmeettijd_is_onbekend() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    readings = my_house.CheckReadings.validate_python(
        [
            {"key": "database", "state": "ok", "observed_at": now, "max_age_s": 900},
            {
                "key": "worker",
                "state": "error",
                "observed_at": now,
                "worker_observed_at": now - timedelta(seconds=121),
                "max_age_s": 120,
            },
        ]
    )
    assert readings[1].project(now).state == "unknown"
    health = my_house.health(readings, now)
    assert (health.status, health.reason_code) == ("unknown", "meettijd_onbekend")
