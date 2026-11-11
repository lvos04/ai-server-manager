"""Blokkades uit de gemeten toestand (contract 1.3 §8; EX11/EX12): de echte gate-beoordeling vertaald naar een
weigering. Zuivere functies; de keten zelf staat in ``tests/e2e/test_acties.py``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from asm_policy import load_policy
from asm_policy.engine import classify

from hub.actions.blokkades import nodige_gates, uit_gates
from hub.onboarding.catalog import DECISIONS
from hub.onboarding.gates import GateInputs, evaluate

POLICY = load_policy()
GEZOND = {"status": "ok", "data": [{"naam": "p", "gezond": True}]}
HOST = "nas-primary"


def _uitkomst(
    *,
    pools: dict[str, Any] | None = None,
    backup_uur: float | None = 1,
    executor: bool = True,
    besluiten: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    dec: dict[str, tuple[str, Any]] = {d.id: ("Getest", None) for d in DECISIONS}
    dec.update({k: (v, None) for k, v in (besluiten or {}).items()})
    return evaluate(
        GateInputs(
            decisions=dec,
            pools_state=GEZOND if pools is None else pools,
            eigen_backup=None if backup_uur is None else {"finished_at": now - timedelta(hours=backup_uur)},
            eigen_backup_max_age_seconds=26 * 3600,
            executor_gekoppeld=executor,
            now=now,
        )
    )


def _gates(action_id: str, target: dict[str, Any], parameters: dict[str, Any] | None = None) -> list[str]:
    actie = POLICY.actie(action_id)
    assert actie is not None
    cls = classify(POLICY, action_id=action_id, target=target, parameters=parameters or {}, actor_type="user")
    return nodige_gates(actie, cls)


def _codes(uitkomst: list[dict[str, Any]], gate_ids: list[str]) -> set[str]:
    return {b["code"] for b in uit_gates(POLICY, uitkomst, gate_ids)}


def test_welke_gates_een_actie_nodig_heeft() -> None:
    app = {"host_id": HOST, "app_id": "demo-app"}
    assert _gates("app.restart", app) == []  # R1 zonder opslag: geen gate
    assert _gates("notification.send", {"host_id": HOST}, {"titel": "a", "tekst": "b"}) == []
    assert _gates("zfs.snapshot.create", {"host_id": HOST, "dataset": "p/x"}, {"naam": "n"}) == ["data_mutatie"]
    assert _gates("app.uninstall", app) == ["r2_r3_acties"]
    assert set(_gates("app.install", app)) == {"r2_r3_acties", "data_mutatie", "deployment"}
    assert set(_gates("app.update", app)) >= {"r2_r3_acties", "bestaande_app_updates"}
    assert set(_gates("app.rollback", app)) >= {"r2_r3_acties", "bestaande_app_updates"}


def test_alles_groen_geen_blokkade() -> None:
    uit = _uitkomst()
    for gates in (["data_mutatie"], ["r2_r3_acties"], ["r2_r3_acties", "data_mutatie", "deployment"]):
        assert uit_gates(POLICY, uit, gates) == []


@pytest.mark.parametrize(
    "pools",
    [
        {"status": "ok", "data": [{"naam": "p", "gezond": False, "status": "DEGRADED"}]},
        {"status": "ok", "data": [{"naam": "p", "gezond": None}]},  # gezondheid onbekend
        {"status": "ok", "data": []},  # geen pools gemeten
        {"status": "unknown", "reason_code": "stale"},  # meting verouderd
        {"status": "unknown", "reason_code": "not_configured"},
        {"status": "error", "reason_code": "auth_failed"},
    ],
)
def test_pool_degraded_of_onbekend_blokkeert_opslagmutaties(pools: dict[str, Any]) -> None:
    """EX11: niet gezond én onbekend tellen allebei als geblokkeerd."""
    uit = _uitkomst(pools=pools)
    assert _codes(uit, ["data_mutatie"]) == {"pool_niet_gezond"}
    blok = uit_gates(POLICY, uit, ["data_mutatie"])[0]
    assert blok["id"] == POLICY.dynamisch["pool"].id and blok["details"]
    # Via de afhankelijke gates komt dezelfde oorzaak boven, niet een vage "gate dicht".
    assert _codes(uit, ["r2_r3_acties"]) == {"pool_niet_gezond"}
    assert "pool_niet_gezond" in _codes(uit, ["r2_r3_acties", "data_mutatie", "deployment"])


@pytest.mark.parametrize("backup_uur", [None, 48])
def test_backupgate_rood_blokkeert_opslagmutaties(backup_uur: float | None) -> None:
    """EX12: geen of een te oude geverifieerde back-up."""
    uit = _uitkomst(backup_uur=backup_uur)
    assert _codes(uit, ["data_mutatie"]) == {"backup_gate_rood"}
    assert _codes(uit, ["r2_r3_acties"]) == {"backup_gate_rood"}


def test_backupbesluiten_niet_getest_is_ook_backupgate_rood() -> None:
    uit = _uitkomst(besluiten={"D05": "Open"})
    assert "backup_gate_rood" in _codes(uit, ["data_mutatie"])


def test_executor_niet_gekoppeld_en_onbekende_gate() -> None:
    uit = _uitkomst(executor=False)
    assert _codes(uit, ["r2_r3_acties"]) == {"executor_niet_gekoppeld"}
    assert _codes(uit, ["deployment"]) == {"executor_niet_gekoppeld"}
    assert _codes(uit, ["data_mutatie"]) == set()  # de pool en de back-up zijn in orde
    # Een gate die niet bestaat, is dicht (onbekend telt nooit als open).
    assert _codes(_uitkomst(), ["bestaat_niet"]) == {"gate_dicht"}
    assert _codes([], ["data_mutatie"]) == {"gate_dicht"}


def test_meerdere_oorzaken_komen_allemaal_boven() -> None:
    uit = _uitkomst(pools={"status": "unknown"}, backup_uur=None, executor=False, besluiten={"D04": "Open"})
    codes = _codes(uit, ["r2_r3_acties", "data_mutatie", "deployment"])
    assert {"pool_niet_gezond", "backup_gate_rood", "executor_niet_gekoppeld"} <= codes
