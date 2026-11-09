"""Unit: alert-toestandsmachine (drempel, duur, hysterese), bronkeuze en stille uren — zonder database."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from hub.monitoring.alerts import DEFAULT_RULES, choose_series, compare, hysteresis_ok, step
from hub.notify.dispatch import _backoff, quiet_until

T0 = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def _rule(**kw: Any) -> Any:
    base = {"operator": "ge", "drempel": 85.0, "herstel_drempel": 80.0, "duur_s": 300, "herstel_duur_s": 120}
    base.update(kw)
    return SimpleNamespace(**base)


def _inst() -> Any:
    return SimpleNamespace(
        toestand="ok",
        sinds=T0,
        pending_sinds=None,
        firing_sinds=None,
        herstel_sinds=None,
        laatste_waarde=None,
        laatste_sample_op=None,
        laatst_opgelost_op=None,
    )


def _run(rule: Any, inst: Any, values: list[float], every_s: int = 60) -> list[tuple[int, str]]:
    out = []
    for i, v in enumerate(values):
        change = step(rule, inst, T0 + timedelta(seconds=i * every_s), v)
        if change:
            out.append((i, change))
    return out


def test_drempel_met_duur_en_hysterese() -> None:
    rule, inst = _rule(), _inst()
    # 4 min boven de drempel is te kort; een dip eronder zet de duur terug.
    assert _run(rule, inst, [90, 90, 90, 90, 70]) == []
    assert inst.toestand == "ok"
    inst = _inst()
    changes = _run(rule, inst, [90, 90, 90, 90, 90, 90, 82, 84, 83, 79, 79, 79])
    # Actief na 5 min (index 5); waarden tussen 80 en 85 houden het actief (hysterese); hersteld na 2 min < 80.
    assert changes == [(5, "actief"), (11, "hersteld")]
    assert inst.toestand == "ok" and inst.laatst_opgelost_op == T0 + timedelta(seconds=660)


def test_flapperen_rond_de_drempel_geeft_een_melding() -> None:
    rule, inst = _rule(duur_s=0), _inst()
    values = [86, 84, 86, 84, 86, 84] * 20
    changes = _run(rule, inst, values, every_s=10)
    assert changes == [(0, "actief")]  # nooit < 80 → nooit hersteld → geen storm


def test_duur_nul_en_binaire_regel() -> None:
    rule, inst = _rule(operator="lt", drempel=0.5, herstel_drempel=0.5, duur_s=0, herstel_duur_s=0), _inst()
    assert _run(rule, inst, [1, 0, 0, 1]) == [(1, "actief"), (3, "hersteld")]


@pytest.mark.parametrize(
    ("op", "d", "h", "ok"),
    [("ge", 85, 80, True), ("ge", 85, 90, False), ("lt", 0.25, 0.75, True), ("le", 5, 1, False), ("gt", 1, 1, True)],
)
def test_hysterese_moet_aan_de_veilige_kant(op: str, d: float, h: float, ok: bool) -> None:
    assert hysteresis_ok(op, d, h) is ok


def test_standaardregels_zijn_consistent() -> None:
    keys = [r.sleutel for r in DEFAULT_RULES]
    assert len(keys) == len(set(keys))
    for r in DEFAULT_RULES:
        assert hysteresis_ok(r.operator, r.drempel, r.herstel_drempel), r
        assert r.ernst in ("info", "waarschuwing", "kritiek")


def test_compare_onbekende_operator() -> None:
    assert compare("le", 5, 5) and not compare("lt", 5, 5)
    with pytest.raises(ValueError):
        compare("eq", 1, 1)


def test_bronkeuze_truenas_voor_beszel_en_vers_voor_oud() -> None:
    def s(bron: str, age: int) -> Any:
        return SimpleNamespace(bron=bron, laatste_op=T0 - timedelta(seconds=age))

    truenas, beszel = s("truenas.reporting.realtime", 30), s("beszel:x", 10)
    assert choose_series([beszel, truenas], T0, 600) is truenas
    stale_truenas = s("truenas.reporting.realtime", 3600)
    assert choose_series([beszel, stale_truenas], T0, 600) is beszel


def test_stille_uren_over_middernacht_en_tijdzone() -> None:
    q = {"van": "22:00", "tot": "07:00", "tijdzone": "Europe/Amsterdam"}
    # 23:30 lokale tijd (winter, UTC+1) → stil tot 07:00 lokaal = 06:00 UTC volgende dag.
    now = datetime(2026, 11, 9, 22, 30, tzinfo=UTC)
    assert quiet_until(q, now) == datetime(2026, 11, 10, 6, 0, tzinfo=UTC)
    # 03:00 lokaal → stil tot 07:00 lokaal dezelfde dag.
    assert quiet_until(q, datetime(2026, 11, 10, 2, 0, tzinfo=UTC)) == datetime(2026, 11, 10, 6, 0, tzinfo=UTC)
    assert quiet_until(q, datetime(2026, 11, 10, 12, 0, tzinfo=UTC)) is None
    assert quiet_until({"van": "13:00", "tot": "14:00", "tijdzone": "UTC"}, T0.replace(hour=13, minute=30)) is not None
    assert quiet_until({"van": "x", "tot": "y", "tijdzone": "Nergens/Niets"}, T0) is None
    assert quiet_until(None, T0) is None


def test_backoff_groeit_en_is_begrensd() -> None:
    assert 20 <= _backoff(1).total_seconds() <= 40
    assert _backoff(20).total_seconds() <= 3600 * 1.2
