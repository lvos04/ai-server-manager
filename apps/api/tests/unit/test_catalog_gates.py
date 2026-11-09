"""Besluitenschema's (geen voorbeeldwaarden) en gate-afleiding."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from hub.onboarding.catalog import BY_ID, D10_VAST, DECISIONS, validate_value
from hub.onboarding.gates import GateInputs, evaluate


def test_achttien_besluiten_conform_excel() -> None:
    assert [d.id for d in DECISIONS] == [f"D{i:02d}" for i in range(1, 19)]
    assert [d.id for d in DECISIONS if d.vast] == ["D10"]
    assert {d.id for d in DECISIONS if d.meetbaar} == {"D01", "D02", "D03", "D06", "D07"}


@pytest.mark.parametrize("did", [d.id for d in DECISIONS])
def test_lege_waarde_wordt_geweigerd(did: str) -> None:
    """Er zijn geen standaard-/voorbeeldwaarden: een leeg object is nooit geldig."""
    with pytest.raises(ValidationError):
        validate_value(did, {})


@pytest.mark.parametrize("value", ["<POOL>", "TODO", "x.x.x.x", "voorbeeld", "nas.example.com"])
def test_plaatshouders_geweigerd(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_value("D03", {"nas_adres": value})


def test_d02_datasets_moeten_bij_pool_horen() -> None:
    ok = validate_value("D02", {"pools": ["p1"], "appdata_datasets": ["p1/apps"]})
    assert ok["media_datasets"] == []
    with pytest.raises(ValidationError):
        validate_value("D02", {"pools": ["p1"], "appdata_datasets": ["p2/apps"]})
    with pytest.raises(ValidationError):
        validate_value("D02", {"pools": ["p1"], "appdata_datasets": ["/mnt/p1/apps"]})


def test_veiligheidsbesluiten_kunnen_niet_onveilig() -> None:
    with pytest.raises(ValidationError):
        validate_value("D09", {"account_gekoppeld": True, "harde_stop": True, "overage_toegestaan": True})
    with pytest.raises(ValidationError):
        validate_value("D14", {"p1_meter": True, "energy_socket_boiler_alleen_meten": False})
    assert validate_value("D10", D10_VAST)["mini_pc_uitgesloten"] is True
    with pytest.raises(ValidationError):
        validate_value("D10", {"mini_pc_uitgesloten": False, "doel": "anders"})


def test_d08_render_node_formaat_en_uniek() -> None:
    g = [
        {"rol": "a310", "pci_slot": "0000:03:00.0", "render_node": "/dev/dri/renderD129"},
        {"rol": "uhd770", "pci_slot": "0000:00:02.0", "render_node": "/dev/dri/renderD128"},
    ]
    assert len(validate_value("D08", {"gpus": g})["gpus"]) == 2
    with pytest.raises(ValidationError):
        validate_value("D08", {"gpus": [g[0], {**g[1], "render_node": g[0]["render_node"]}]})
    with pytest.raises(ValidationError):
        validate_value("D08", {"gpus": [{**g[0], "render_node": "/dev/sda"}]})


def _inputs(
    statuses: dict[str, str],
    pools: dict[str, Any] | None = None,
    backup_age_h: float | None = None,
    executor: bool = False,
) -> GateInputs:
    now = datetime.now(UTC)
    dec = {d.id: ("Open", None) for d in DECISIONS}
    dec.update({k: (v, None) for k, v in statuses.items()})
    return GateInputs(
        decisions=dec,
        pools_state=pools or {"status": "unknown", "reason_code": "not_configured"},
        eigen_backup=None if backup_age_h is None else {"finished_at": now - timedelta(hours=backup_age_h)},
        eigen_backup_max_age_seconds=26 * 3600,
        executor_gekoppeld=executor,
        now=now,
    )


def _gates(inp: GateInputs) -> dict[str, dict[str, Any]]:
    return {g["id"]: g for g in evaluate(inp)}


def test_alles_open_alles_dicht() -> None:
    g = _gates(_inputs({}))
    assert not any(x["toegestaan"] for x in g.values())
    assert g["connector_bouw"]["redenen"][0]["tekst"].startswith("D01 is Open")


def test_gate_open_alleen_met_getest() -> None:
    assert _gates(_inputs({"D01": "Ingevuld"}))["connector_bouw"]["status"] == "geblokkeerd"
    assert _gates(_inputs({"D01": "Getest"}))["connector_bouw"]["status"] == "toegestaan"
    assert _gates(_inputs({"D16": "Ingevuld"}))["restore_policy"]["status"] == "toegestaan"


def test_nvt_opent_nooit_een_gate() -> None:
    g = _gates(_inputs({"D12": "N.v.t."}))["gree_aansturing"]
    assert g["status"] == "geblokkeerd" and "N.v.t." in g["redenen"][0]["tekst"]


def test_data_mutatie_pool_onbekend_of_degraded() -> None:
    base = {"D04": "Ingevuld", "D05": "Getest", "D16": "Ingevuld", "D06": "Getest"}
    healthy = {"status": "ok", "data": [{"naam": "p", "gezond": True}]}
    assert _gates(_inputs(base, healthy, backup_age_h=1))["data_mutatie"]["status"] == "toegestaan"
    unk = _gates(_inputs(base, {"status": "unknown", "reason_code": "stale"}, backup_age_h=1))["data_mutatie"]
    assert unk["status"] == "unknown" and unk["toegestaan"] is False
    deg = _gates(_inputs(base, {"status": "ok", "data": [{"naam": "p", "gezond": False}]}, backup_age_h=1))[
        "data_mutatie"
    ]
    assert deg["status"] == "geblokkeerd" and "EX11" in deg["redenen"][0]["tekst"]
    old = _gates(_inputs(base, healthy, backup_age_h=48))["data_mutatie"]
    assert old["status"] == "geblokkeerd" and any(r["id"] == "backup_gate" for r in old["redenen"])


def test_executor_niet_gekoppeld_blokkeert_deploy_en_r2r3() -> None:
    all_ok = {d.id: "Getest" for d in DECISIONS}
    healthy = {"status": "ok", "data": [{"naam": "p", "gezond": True}]}
    g = _gates(_inputs(all_ok, healthy, backup_age_h=1, executor=False))
    assert g["deployment"]["status"] == "geblokkeerd" and g["r2_r3_acties"]["status"] == "geblokkeerd"
    g = _gates(_inputs(all_ok, healthy, backup_age_h=1, executor=True))
    assert all(x["toegestaan"] for x in g.values()), [x for x in g.values() if not x["toegestaan"]]


def test_schema_beschikbaar_voor_ui() -> None:
    schema = BY_ID["D03"].schema.model_json_schema()
    assert "nas_adres" in schema["required"] and "default" not in schema["properties"]["nas_adres"]
