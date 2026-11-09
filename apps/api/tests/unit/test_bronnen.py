"""Unit: parsers en beoordeling van monitoringbronnen (Prometheus-tekst, Uptime Kuma, Beszel, heartbeat, connector)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from hub.monitoring import beszel, heartbeat, kuma, prometheus
from hub.monitoring.sources import judge_connector_health

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
GPUS = [
    {"pci_slot": "0000:03:00.0", "beschrijving": "Intel Corporation DG2 [Arc A310]"},
    {"pci_slot": "0000:00:02.0", "beschrijving": "Intel Corporation Raptor Lake-S GT1 [UHD Graphics 770]"},
]


def test_prometheus_tekst_met_escapes_en_onleesbare_regels() -> None:
    text = (
        "# HELP x y\n"
        'monitor_status{monitor_id="1",monitor_name="A \\"b\\" \\\\ c",monitor_url="null"} 1\n'
        "kapot{zonder einde 1\n"
        'monitor_response_time{monitor_id="1"} 12.5 1700000000000\n'
        "nan_waarde NaN\n"
        "geen_labels 3\n"
    )
    res = prometheus.parse(text)
    assert res.onleesbaar == 1
    assert res.by_name("monitor_status")[0].labels["monitor_name"] == 'A "b" \\ c'
    assert res.by_name("monitor_response_time")[0].waarde == 12.5
    assert res.by_name("geen_labels")[0].labels == {} and not res.by_name("nan_waarde")


def test_kuma_metrics_naar_status_en_versie() -> None:
    text = (
        'app_version{version="2.5.9",major="2",minor="5",patch="9"} 1\n'
        'monitor_status{monitor_id="1",monitor_name="Up",monitor_type="http",monitor_url="http://u:p@nas:30101/x?token=1",'
        'monitor_hostname="null",monitor_port="null"} 1\n'
        'monitor_status{monitor_id="2",monitor_name="Down",monitor_type="port",monitor_url="null",'
        'monitor_hostname="nas.lan",monitor_port="8096"} 0\n'
        'monitor_status{monitor_id="3",monitor_name="Pending"} 2\n'
        'monitor_status{monitor_id="4",monitor_name="Onderhoud"} 3\n'
        'monitor_response_time{monitor_id="1",monitor_name="Up"} 15\n'
        'monitor_uptime_ratio{monitor_id="1",monitor_name="Up",window="1d"} 0.98\n'
        'monitor_uptime_ratio{monitor_id="1",monitor_name="Up",window="30d"} 0.5\n'
    )
    mons, version, bad = kuma.parse_metrics(text, NOW)
    assert version == "2.5.9" and bad == 0
    assert {k: (m.status, m.reason_code) for k, m in mons.items()} == {
        "id:1": ("healthy", None),
        "id:2": ("down", "monitor_down"),
        "id:3": ("degraded", "monitor_wacht"),
        "id:4": ("unknown", "onderhoud"),
    }
    up = mons["id:1"]
    assert up.url == "http://nas:30101/x"  # inloggegevens en query verwijderd
    assert up.latency_ms == 15 and up.uptime_24u == 0.98 and up.observed_at == NOW
    assert mons["id:2"].hostname == "nas.lan" and mons["id:2"].port == 8096


def test_kuma_statuspagina_geeft_echte_tijd() -> None:
    page = {"publicGroupList": [{"monitorList": [{"id": 5, "name": "Hub", "type": "http"}]}]}
    beats = {
        "heartbeatList": {"5": [{"status": 1, "time": "2026-11-09 11:58:00.000", "ping": 9}]},
        "uptimeList": {"5_24": 1},
    }
    mons = kuma.merge_status_page({}, page, beats)
    m = mons["id:5"]
    assert m.status == "healthy" and m.observed_at == datetime(2026, 11, 9, 11, 58, tzinfo=UTC)
    assert m.latency_ms == 9 and m.uptime_24u == 1 and m.bronnen == ["status_pagina"]


@pytest.mark.parametrize(
    ("name", "slot", "reason"),
    [
        ("Intel Arc A310", "0000:03:00.0", "naam_eenduidig"),
        ("Intel(R) UHD Graphics 770", "0000:00:02.0", "naam_eenduidig"),
        ("Intel Graphics", None, "geen_modelnummer_in_naam"),
        ("NVIDIA RTX 4090", None, "geen_gpu_met_deze_naam"),
    ],
)
def test_gpu_alleen_eenduidig_op_naam(name: str, slot: str | None, reason: str) -> None:
    assert beszel.match_gpu(name, GPUS) == (slot, reason)


def test_gpu_dubbelzinnig_wordt_niet_gekoppeld() -> None:
    twins = [{"pci_slot": "a", "beschrijving": "Arc A310"}, {"pci_slot": "b", "beschrijving": "Arc A310"}]
    assert beszel.match_gpu("A310", twins) == (None, "geen_eenduidige_gpu")


def test_beszel_stats_eenheden_en_geen_nul_graden() -> None:
    stats = {
        "cpu": 10,
        "m": 16.0,
        "mu": 4.0,
        "mz": 2.0,
        "dr": 1.0,
        "dw": 2.0,
        "t": {"coretemp_package_id_0": 0, "cpu_thermal": 200},
        "g": {"x": {"n": "Arc A310", "u": 0}},
    }
    samples, unassigned = beszel.nas_samples(stats, NOW, "beszel:x", GPUS)
    by = {(s.onderwerp_type, s.metriek): s.waarde for s in samples}
    assert by[("nas", "geheugen.totaal")] == 16 * 1024**3 and by[("nas", "geheugen.beschikbaar_pct")] == 75.0
    assert by[("nas", "schijf.lezen")] == 1024**2
    assert ("nas", "cpu.temperatuur") not in by  # 0 °C en 200 °C zijn ongeldig: onbekend, nooit 0
    assert by[("gpu", "gpu.gebruik")] == 0 and ("gpu", "gpu.vermogen") not in by and unassigned == []
    assert beszel.valid_temp(-5) is None and beszel.valid_temp(55.5) == 55.5 and beszel.valid_temp(True) is None


def _hb(**kw: Any) -> heartbeat.HeartbeatIn:
    return heartbeat.HeartbeatIn.model_validate({"status": "healthy", "observed_at": NOW.isoformat(), **kw})


def test_heartbeat_beoordeling() -> None:
    assert heartbeat.judge(_hb(), NOW) == ("healthy", None)
    assert heartbeat.judge(_hb(status="down"), NOW) == ("down", "dienst_meldt_down")
    stale = {"laatste_hartslag": (NOW - timedelta(minutes=10)).isoformat()}
    assert heartbeat.judge(_hb(worker=stale), NOW) == ("degraded", "worker_staat_stil")
    stuck = {"wachtrij": 3, "laatste_job_klaar": (NOW - timedelta(minutes=20)).isoformat()}
    assert heartbeat.judge(_hb(worker=stuck), NOW) == ("degraded", "jobs_staan_stil")
    idle = {"wachtrij": 0, "laatste_job_klaar": (NOW - timedelta(days=2)).isoformat()}
    assert heartbeat.judge(_hb(worker=idle), NOW) == ("healthy", None)  # niets te doen is geen storing
    assert heartbeat.judge(_hb(checks=[{"name": "db", "status": "down"}]), NOW) == ("degraded", "controle_faalt")
    with pytest.raises(ValueError):
        _hb(observed_at="2026-11-09T12:00:00")  # zonder tijdzone


def test_connector_health_beoordeling() -> None:
    ok = {"status": "healthy", "observed_at": "2026-11-09T11:59:30Z", "reason_code": None, "checks": []}
    assert judge_connector_health(ok, NOW)[:3] == ("healthy", None, datetime(2026, 11, 9, 11, 59, 30, tzinfo=UTC))
    stalled = {**ok, "checks": [{"name": "Worker", "status": "down"}]}
    assert judge_connector_health(stalled, NOW)[:2] == ("degraded", "jobs_staan_stil")
    far = {**ok, "observed_at": "2020-01-01T00:00:00Z"}
    assert judge_connector_health(far, NOW)[2] == NOW  # klok van de dienst niet vertrouwen bij grote afwijking
    assert judge_connector_health({"status": "groen"}, NOW)[:2] == ("unknown", "antwoord_ongeldig")
    assert judge_connector_health(None, NOW)[:2] == ("unknown", "antwoord_ongeldig")
