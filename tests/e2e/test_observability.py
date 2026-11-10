"""Dienst-E2E: observability van de NAS (B01-004) en meetdekking (B09-001) tegen de fake TrueNAS en fake Beszel.

Acceptatie B01-004: een bron ouder dan de TTL is ``unknown``; GPU-wisseling van render-node verwisselt A310 en iGPU
niet (identiteit = PCI-slot). B09-001: A310 en UHD 770 juist onderscheiden; ontbrekende GPU-temperatuur nooit 0 °C.
Sim-getest; NIET GEVALIDEERD op een echte NAS.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from conftest import idem, login_as, make_user
from fakes.fake_monitoring import FakeBeszel
from fakes.fake_truenas import FakeTrueNAS, KeyProfile
from nashelpers import READONLY_KEY, connect, refresh

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
GIB = 1024**3


def _view(admin: Any) -> dict[str, Any]:
    r = admin.get("/api/v1/observability/nas")
    assert r.status_code == 200, r.text
    return dict(r.json())


def test_zonder_koppeling_alles_onbekend(admin: Any, periodic_run: Any) -> None:
    out = periodic_run("nas_meten")["nas_meten"]
    assert out["meting"] == "unknown" and out["reden"] == "not_configured"
    v = _view(admin)
    assert v["cpu"]["gebruik"] == {
        "waarde": None,
        "eenheid": "%",
        "bron": None,
        "observed_at": None,
        "status": "unknown",
        "reden": "geen_bron",
        "reason_code": "geen_bron",
        "laatst_bekend": None,
    }
    assert v["gpus"] == [] and v["alleen_truenas"] is True
    cov = admin.get("/api/v1/monitoring/coverage").json()
    assert cov["bronnen"]["truenas"]["gekoppeld"] is False
    cpu = next(r for r in cov["metrieken"] if r["metriek"] == "cpu.gebruik")
    assert cpu["gedekt"] is False and {b["reden"] for b in cpu["bronnen"]} == {"bron_niet_gekoppeld"}


def test_live_metingen_uit_truenas_met_bron_en_tijd(
    admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any, periodic_run: Any, clean_db: str
) -> None:
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    out = periodic_run("nas_meten")["nas_meten"]
    assert out["meting"] == "ok" and out["threads"] == 4, out
    assert fake_nas.subscriptions and fake_nas.unsubscribed == fake_nas.subscriptions  # abonnement netjes opgezegd
    v = _view(admin)
    cpu = v["cpu"]["gebruik"]
    assert cpu["waarde"] == 23.5 and cpu["eenheid"] == "%" and cpu["bron"] == "TrueNAS (reporting.realtime)"
    assert cpu["observed_at"] and cpu["status"] == "ok"
    assert v["cpu"]["temperatuur"]["waarde"] == 51.0 and v["cpu"]["threads"] == 4
    g = v["geheugen"]
    assert (g["totaal"]["waarde"], g["gebruikt"]["waarde"], g["beschikbaar_pct"]["waarde"]) == (32 * GIB, 8 * GIB, 75.0)
    assert g["zfs_arc"]["waarde"] == 6 * GIB and g["zfs_arc_treffers"]["waarde"] == 97
    assert v["schijven"]["lezen"]["waarde"] == 4096 and v["schijven"]["bezet"]["waarde"] == 3.5
    ifaces = {i["naam"]: i for i in v["netwerk"]["interfaces"]}
    assert ifaces["eth0"]["link"]["waarde"] == 1 and ifaces["eth0"]["ontvangen"]["waarde"] == 1250
    assert ifaces["eth1"]["link"]["waarde"] == 0 and ifaces["eth1"]["ontvangen"]["status"] == "unknown"
    assert v["netwerk"]["totaal"]["ontvangen"]["waarde"] == 1250  # precies één actieve interface
    pools = {p["naam"]: p for p in v["pools"]}
    assert pools["testpool"]["gebruik"]["waarde"] == 25.0 and pools["testpool"]["gezond"] is True
    gpus = {x["pci_slot"]: x for x in v["gpus"]}
    assert {s: x["herkend_als"] for s, x in gpus.items()} == {"0000:03:00.0": "a310", "0000:00:02.0": "uhd770"}
    for x in gpus.values():
        assert x["temperatuur"]["waarde"] is None and x["temperatuur"]["reden"] == "niet_geleverd"
        assert x["gebruik"]["status"] == "unknown"  # TrueNAS levert geen GPU-belasting
    assert fake_nas.mutations == []

    # NAS weg: geen nieuwe meting; na de TTL alles unknown met de laatst bekende waarde en tijd.
    fake_nas.offline()
    out = periodic_run("nas_meten")["nas_meten"]
    assert out["meting"] == "unknown" and out["reden"] == "unreachable"
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE metric_series SET laatste_op = laatste_op - interval '10 minutes'")
    v = _view(admin)
    cpu = v["cpu"]["gebruik"]
    assert cpu["status"] == "unknown" and cpu["waarde"] is None and cpu["reden"] == "verouderd"
    assert cpu["laatst_bekend"]["waarde"] == 23.5 and v["realtime"]["reden"] == "unreachable"


def test_beszel_als_tweede_bron_gpu_op_pci_slot_en_mini_pc_uitgesloten(
    admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any, periodic_run: Any
) -> None:
    beszel = FakeBeszel().start()
    try:
        connect(admin, fake_nas)
        refresh(admin, worker_once)
        r = admin.post(
            "/api/v1/monitoring/sources",
            json={
                "soort": "beszel",
                "naam": "Beszel",
                "basis_url": beszel.url,
                "identiteit": "hub-lezer",
                "wachtwoord": "Lees-Alleen-Wachtwoord-1",
            },
            headers=idem(),
        )
        assert r.status_code == 201, r.text
        periodic_run("nas_meten", "bronnen_pollen")
        v = _view(admin)
        assert v["cpu"]["gebruik"]["bron"] == "TrueNAS (reporting.realtime)"  # TrueNAS gaat voor
        assert v["cpu"]["gebruik"]["alternatieven"] == ["Beszel (Beszel)"]
        gpus = {x["pci_slot"]: x for x in v["gpus"]}
        assert (
            gpus["0000:03:00.0"]["gebruik"]["waarde"] == 30.0
            and gpus["0000:03:00.0"]["gebruik"]["bron"] == "Beszel (Beszel)"
        )
        assert gpus["0000:00:02.0"]["gebruik"]["waarde"] == 5.0
        assert gpus["0000:03:00.0"]["vermogen"]["waarde"] == 9.5
        assert [s["naam"] for s in v["uitgesloten_systemen"]] == ["mini-pc"]

        cov = admin.get("/api/v1/monitoring/coverage").json()
        rows = {(m["metriek"], m["onderwerp_id"]): m for m in cov["metrieken"]}
        cpu = rows[("cpu.gebruik", "nas")]
        assert cpu["gedekt"] and {b["bron"]: b["levert"] for b in cpu["bronnen"]} == {
            "truenas_realtime": True,
            "beszel": True,
        }
        assert rows[("gpu.gebruik", "0000:03:00.0")]["gedekt"] is True
        temp = rows[("gpu.temperatuur", "0000:03:00.0")]
        assert temp["gedekt"] is False and "bewust niet gebouwd" in temp["hiaat"]
        assert all(b["kan_leveren"] == "nee" for b in temp["bronnen"])
        assert rows[("schijf.temperatuur", "nas")]["gedekt"] is False
        assert "GPU-temperatuur — a310 (0000:03:00.0)" in cov["hiaten"]
        assert rows[("pool.gebruik", "testpool")]["gedekt"] is True
        assert cov["apps"]["totaal"] == 4 and cov["apps"]["met_buitenkant"] == 0
        assert {a["naam"] for a in cov["apps"]["hiaten"]} == {
            "mediaguard",
            "media-source-optimizer",
            "my-house",
            "jellyfin",
        }
    finally:
        beszel.stop()


def test_realtime_zonder_leesrecht_of_zonder_antwoord_is_onbekend(
    admin: Any, app: Any, settings: Any, periodic_run: Any
) -> None:
    nas = FakeTrueNAS(keys={READONLY_KEY: KeyProfile(deny={"reporting.realtime"})}).start()
    try:
        connect(admin, nas)
        out = periodic_run("nas_meten")["nas_meten"]
        assert out["meting"] == "unknown" and out["reden"] == "permission_denied"
        cov = admin.get("/api/v1/monitoring/coverage").json()
        assert cov["bronnen"]["truenas"]["realtime_reden"] == "permission_denied"
        nas.keys = {READONLY_KEY: KeyProfile()}
        nas.realtime_silent = True
        settings.truenas_read_timeout = 1
        out = periodic_run("nas_meten")["nas_meten"]
        assert out["meting"] == "unknown" and out["reden"] == "timeout"
        assert nas.unsubscribed, "ook na een time-out wordt het abonnement opgezegd"
        assert _view(admin)["cpu"]["gebruik"]["status"] == "unknown"
        assert nas.mutations == []
    finally:
        nas.stop()
    make_user(admin, "kleintje", "kind")
    assert login_as(app, "kleintje").get("/api/v1/observability/nas").status_code == 403
