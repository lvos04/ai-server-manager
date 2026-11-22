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
GEZOND = {"status": "ok", "data": [{"naam": "p", "status": "ONLINE", "gezond": True}]}
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


GOEDE_RIJ = {"name": "p", "status": "ONLINE", "healthy": True}


@pytest.mark.parametrize(
    ("rijen", "open_verwacht"),
    [
        pytest.param([GOEDE_RIJ], True, id="gezond"),
        pytest.param([{**GOEDE_RIJ, "status": "DEGRADED"}], False, id="tegenstrijdig"),
        pytest.param([{**GOEDE_RIJ, "healthy": False}], False, id="online-maar-ongezond"),
        pytest.param([{"name": "p", "healthy": True}], False, id="status-ontbreekt"),
        pytest.param([{"name": "p", "status": "ONLINE"}], False, id="gezondheidsvlag-ontbreekt"),
        pytest.param([{**GOEDE_RIJ, "healthy": "true"}], False, id="gezondheidsvlag-geen-boolean"),
        pytest.param([{"status": "ONLINE", "healthy": True}], False, id="naam-ontbreekt"),
        pytest.param([GOEDE_RIJ, None], False, id="onleesbare-tweede-pool"),
        pytest.param([GOEDE_RIJ, "ONLINE"], False, id="tekst-in-plaats-van-rij"),
    ],
)
def test_elke_poolrij_moet_aantoonbaar_gezond_zijn(rijen: list[Any], open_verwacht: bool) -> None:
    """R-VEILIG-1 (positieve witte lijst): Hub (normalize + gate) en executor geven per rij hetzelfde oordeel. Alleen
    een benoemde pool die ONLINE is en expliciet healthy=true meldt, opent de poolgate."""
    from executor.uitvoeren import pools_gezond

    from hub.truenas.normalize import pools as normaliseer

    uit = _uitkomst(pools={"status": "ok", "data": normaliseer(rijen)})
    verwacht = set() if open_verwacht else {"pool_niet_gezond"}
    assert _codes(uit, ["data_mutatie"]) == verwacht
    assert _codes(uit, ["r2_r3_acties"]) == verwacht
    assert pools_gezond(rijen)[0] is open_verwacht


@pytest.mark.parametrize(
    "rij",
    [
        {"naam": "p", "status": "DEGRADED", "gezond": True},  # tegenstrijdig opgeslagen
        {"naam": "p", "gezond": True},  # status ontbreekt
        {"naam": None, "status": "ONLINE", "gezond": True},  # naamloos
        None,  # onleesbaar
    ],
)
def test_gate_vertrouwt_een_opgeslagen_gezond_vlag_niet_alleen(rij: Any) -> None:
    """R-VEILIG-1: ook een eerder opgeslagen meting met een tegenstrijdige of onvolledige rij houdt de gate dicht."""
    uit = _uitkomst(pools={"status": "ok", "data": [{"naam": "q", "status": "ONLINE", "gezond": True}, rij]})
    assert _codes(uit, ["data_mutatie"]) == {"pool_niet_gezond"}


@pytest.mark.parametrize(
    ("backup_uur", "open_verwacht"),
    [(-24, False), (-0.1, False), (-0.01, True), (0, True), (25.9, True), (26.1, False)],
)
def test_backuptijd_heeft_twee_grenzen(backup_uur: float, open_verwacht: bool) -> None:
    """R-VEILIG-3: niet ouder dan de grens (26 uur hier) en niet verder in de toekomst dan de klokmarge (60 s)."""
    codes = _codes(_uitkomst(backup_uur=backup_uur), ["r2_r3_acties"])
    assert codes == (set() if open_verwacht else {"backup_gate_rood"})


def test_binnen_venster() -> None:
    from hub.timeutil import KLOKMARGE_SECONDEN, binnen_venster

    nu = datetime.now(UTC)
    assert binnen_venster(nu, nu, 60) and binnen_venster(nu - timedelta(seconds=60), nu, 60)
    assert binnen_venster(nu + timedelta(seconds=KLOKMARGE_SECONDEN), nu, 60)
    assert not binnen_venster(nu + timedelta(seconds=KLOKMARGE_SECONDEN + 1), nu, 60)
    assert not binnen_venster(nu - timedelta(seconds=61), nu, 60)
    assert not binnen_venster(None, nu, 60)
    assert binnen_venster((nu - timedelta(seconds=5)).replace(tzinfo=None), nu, 60)  # naïeve tijd = UTC


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


def test_elke_opslagmutatie_vraagt_de_poolgate_en_riskante_media_acties_bestaan_niet() -> None:
    """EX11 (S-P2-060 bouwpunt 2): elke toegestane actie met ``opslagmutatie`` loopt via ``data_mutatie`` (en dus via
    de poolmeting); een riskante media-actie (wissen, opschonen) staat niet op de allowlist en wordt altijd
    geweigerd, ook als de pool gezond is."""
    opslag = [a for a in POLICY.acties.values() if a.opslagmutatie]
    assert opslag, "geen opslagmutaties in het beleid"
    for a in opslag:
        cls = classify(POLICY, action_id=a.action_id, target={"host_id": HOST}, parameters={}, actor_type="user")
        assert "data_mutatie" in nodige_gates(a, cls), a.action_id
    uit = _uitkomst(pools={"status": "ok", "data": [{"naam": "p", "gezond": False, "status": "DEGRADED"}]})
    assert _codes(uit, ["data_mutatie"]) == {"pool_niet_gezond"}
    for aid in ("media.purge", "mediaguard.purge.start", "jellyfin.media.delete", "downloads.wipe"):
        c = classify(POLICY, action_id=aid, target={"host_id": HOST}, parameters={}, actor_type="user")
        assert c.geweigerd and POLICY.actie(aid) is None, aid
