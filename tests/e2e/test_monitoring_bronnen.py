"""Dienst-E2E: monitoringbronnen en healthchecks (B09-002, B09-001/B01-004 deels) tegen fakes (Sim-getest).

- Uptime Kuma: ``/metrics`` met API-key + statuspagina, versie-detectie, automatische en handmatige koppeling aan apps,
  verouderd → unknown, ingetrokken key → direct unknown + event (EX16).
- Beszel: alleen het NAS-systeem (mini-pc uitgesloten), GPU's op naam aan PCI-slot (nooit verwisseld), geen 0 °C.
- Heartbeat en connector-health van eigen diensten: 200 zonder jobs → degraded; grace bij fouten; nooit open.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest
from conftest import enroll_body, idem, login_as, make_user
from fakes.fake_monitoring import FakeBeszel, FakeDienst, FakeUptimeKuma, nas_stats
from fakes.fake_truenas import FakeTrueNAS, _app
from nashelpers import connect, refresh
from sqlalchemy import select

from hub.models import OutboxEvent

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
KEY = "uk1_testkey_abcdef"
BESZEL_PW = "Lees-Alleen-Wachtwoord-1"


@pytest.fixture
def kuma() -> Any:
    k = FakeUptimeKuma(api_keys={KEY}).start()
    yield k
    k.stop()


@pytest.fixture
def beszel() -> Any:
    b = FakeBeszel().start()
    yield b
    b.stop()


def _apps(admin: Any) -> dict[str, dict[str, Any]]:
    return {a["runtime_id"]: a for a in admin.get("/api/v1/apps", params={"limit": 200}).json()["items"]}


def _age_observations(db_url: str, minutes: int) -> None:
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("UPDATE health_observation SET observed_at = observed_at - make_interval(mins => %s)", (minutes,))


def _source(admin: Any, body: dict[str, Any]) -> dict[str, Any]:
    r = admin.post("/api/v1/monitoring/sources", json=body, headers=idem())
    assert r.status_code == 201, r.text
    return dict(r.json())


def test_uptime_kuma_koppelt_monitors_en_wordt_onbekend_bij_veroudering_of_ingetrokken_key(
    admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any, kuma: FakeUptimeKuma, clean_db: str
) -> None:
    fake_nas.data["app.query"].append(
        _app(
            "prowlarr", "RUNNING", "ghcr.io/linuxserver/prowlarr:1.30.0", 30150, 9696, "/mnt/testpool/apps/p", "/config"
        )
    )
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    kuma.add(1, "MediaGuard", url="http://127.0.0.1:30101/api/v1/health")
    kuma.add(2, "Prowlarr", url="http://127.0.0.1:30150/ping", ping=33.0)
    kuma.add(3, "Externe site", url="https://example.org/", status=0)
    kuma.add(4, "Jellyfin", url="http://127.0.0.1:30013/health", status=0)
    kuma.status_pages = {"thuis": [1, 2]}

    src = _source(
        admin,
        {"soort": "uptime_kuma", "naam": "Kuma", "basis_url": kuma.url, "api_key": KEY, "status_paginas": ["thuis"]},
    )
    assert KEY not in str(src) and src["geheim"]["laatste4"] == "cdef"
    r = admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem())
    assert r.status_code == 200, r.text
    # Jellyfin is gestopt: TrueNAS toont dan geen poorten (lege active_workloads), dus die monitor koppelt niet
    # automatisch op hostpoort. Gekoppeld: MediaGuard en Prowlarr.
    assert r.json()["resultaat"] == {"status": "ok", "monitors": 4, "gekoppeld": 2}
    bron = r.json()["bron"]
    assert bron["status"]["status"] == "ok" and bron["status"]["versie"] == "2.5.9"

    apps = _apps(admin)
    # App van derden zonder eigen taken: een verse monitor 'up' maakt hem gezond.
    assert apps["prowlarr"]["gezondheid"]["status"] == "healthy"
    assert apps["prowlarr"]["gezondheid"]["laatst_getest"] is not None
    # MediaGuard is bereikbaar (Kuma), maar de binnenkant (jobs) volgt in P3 → nooit groen.
    mg = admin.get(f"/api/v1/apps/{apps['mediaguard']['id']}").json()
    comps = {c["soort"]: c for c in mg["gezondheid"]["componenten"]}
    assert comps["buitenkant"]["status"] == "healthy" and mg["gezondheid"]["status"] == "unknown"
    assert comps["buitenkant"]["latency_ms"] == 12.0
    assert apps["jellyfin"]["gezondheid"]["status"] == "down"
    detail = admin.get(f"/api/v1/monitoring/sources/{src['id']}").json()
    mons = {m["naam"]: m for m in detail["monitors"]}
    assert mons["Externe site"]["app"] is None and mons["Prowlarr"]["koppeling"] == "automatisch"
    assert mons["MediaGuard"]["details"]["via"] == ["metrics", "status_pagina"]

    # Handmatig: 'Externe site' hoort bij niets ('geen'), Prowlarr-monitor juist niet bij Prowlarr.
    r = admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}",
        json={"koppelingen": {"id:2": "geen", "id:3": apps["mediaguard"]["id"]}},
        headers=idem(),
    )
    assert r.status_code == 200, r.text
    admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
    apps = _apps(admin)
    assert apps["prowlarr"]["gezondheid"]["status"] == "unknown"  # geen bron meer gekoppeld
    assert apps["mediaguard"]["gezondheid"]["status"] == "down"  # handmatig gekoppelde monitor is down
    bad = admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}", json={"koppelingen": {"id:9": "niet-een-uuid"}}, headers=idem()
    )
    assert bad.status_code == 422
    admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}",
        json={"koppelingen": {"id:2": None, "id:3": None}},
        headers=idem(),
    ).raise_for_status()
    admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
    assert _apps(admin)["prowlarr"]["gezondheid"]["status"] == "healthy"

    # Kuma onbereikbaar: waarnemingen verouderen → unknown met laatst bekende status, nooit 'nog gezond'.
    kuma.offline()
    admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
    _age_observations(clean_db, 10)
    p = admin.get(f"/api/v1/apps/{_apps(admin)['prowlarr']['id']}").json()["gezondheid"]
    assert p["status"] == "unknown" and p["reason_code"] == "meting_verouderd"
    buiten = next(c for c in p["componenten"] if c["soort"] == "buitenkant")
    assert buiten["laatste_status"] == "healthy" and buiten["verouderd"] is True
    st = admin.get("/api/v1/monitoring/sources").json()["items"][0]["status"]
    assert st["status"] == "fout" and st["reden"] == "niet_bereikbaar"

    # Key ingetrokken (EX16): direct unknown, event, geen open toegang; nieuwe key → hersteld.
    kuma.online()
    kuma.api_keys = set()
    kuma.status_pages = {}
    admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}", json={"status_paginas": []}, headers=idem()
    ).raise_for_status()
    admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
    srcs = admin.get("/api/v1/monitoring/sources").json()["items"][0]
    assert srcs["status"]["reden"] == "api_key_geweigerd" and "API-key" in srcs["status"]["melding"]
    health = admin.get("/api/v1/monitoring/health", params={"bron_type": "uptime_kuma"}).json()["items"]
    assert health and {h["status"] for h in health} == {"unknown"}
    assert {h["reason_code"] for h in health} == {"bron_credential_geweigerd"}
    kuma.api_keys = {"uk1_nieuwe_key_123"}
    admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}", json={"api_key": "uk1_nieuwe_key_123"}, headers=idem()
    ).raise_for_status()
    admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
    assert _apps(admin)["prowlarr"]["gezondheid"]["status"] == "healthy"
    with app.state.sessionmaker() as db:
        types = [e.event_type for e in db.scalars(select(OutboxEvent).order_by(OutboxEvent.seq))]
    assert "monitoring.source.failed" in types and types[-1] == "monitoring.source.recovered"
    series = admin.get("/api/v1/metrics/series", params={"metriek": "monitor.latentie"}).json()["items"]
    assert any(s["laatst_bekend"]["waarde"] == 33.0 for s in series)
    assert fake_nas.mutations == []


def test_kuma_zonder_monitor_id_en_validatie(admin: Any, kuma: FakeUptimeKuma) -> None:
    kuma.with_ids = False  # oudere Uptime Kuma: sleutel op naam
    kuma.add(1, 'Rare "naam" \\ met tekens', url="http://192.0.2.9:80/")
    src = _source(admin, {"soort": "uptime_kuma", "naam": "Oud", "basis_url": kuma.url, "api_key": KEY})
    admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).raise_for_status()
    mons = admin.get(f"/api/v1/monitoring/sources/{src['id']}").json()["monitors"]
    assert [m["sleutel"] for m in mons] == ['naam:Rare "naam" \\ met tekens']
    for body in (
        {"soort": "uptime_kuma", "naam": "x", "basis_url": kuma.url},  # geen key en geen statuspagina
        {"soort": "uptime_kuma", "naam": "x", "basis_url": kuma.url, "api_key": KEY, "wachtwoord": "abcdefgh"},
        {"soort": "beszel", "naam": "x", "basis_url": kuma.url, "identiteit": "a"},
        {"soort": "uptime_kuma", "naam": "x", "basis_url": "http://u:p@nas:3001", "api_key": KEY},
        {"soort": "uptime_kuma", "naam": "x", "basis_url": kuma.url, "status_paginas": ["Niet Geldig"]},
    ):
        assert admin.post("/api/v1/monitoring/sources", json=body, headers=idem()).status_code == 422, body
    kuma.redirect_to = "http://127.0.0.1:1/elders"
    r = admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).json()
    assert r["resultaat"] == {"status": "fout", "reden": "redirect_niet_gevolgd"}


def test_beszel_alleen_nas_gpu_op_naam_en_geen_nul_graden(
    admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any, beszel: FakeBeszel
) -> None:
    connect(admin, fake_nas)
    refresh(admin, worker_once)  # GPU-identiteit (PCI-slot) uit app.gpu_choices
    src = _source(
        admin,
        {
            "soort": "beszel",
            "naam": "Beszel",
            "basis_url": beszel.url,
            "identiteit": "hub-lezer",
            "wachtwoord": BESZEL_PW,
        },
    )
    assert BESZEL_PW not in str(src)
    r = admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).json()
    assert r["resultaat"]["status"] == "ok", r
    bron = r["bron"]
    assert bron["status"]["versie"] == "0.21.1"
    rollen = {s["naam"]: s["rol"] for s in bron["detail"]["systemen"]}
    assert rollen == {"truenas": "nas", "mini-pc": "uitgesloten"}
    assert bron["detail"]["nas"]["koppeling"].startswith("automatisch")

    def series(**f: Any) -> dict[str, Any]:
        items = admin.get("/api/v1/metrics/series", params={"limit": 200, **f}).json()["items"]
        return {f"{s['onderwerp_type']}|{s['onderwerp_id']}|{s['metriek']}": s for s in items}

    nas = series(onderwerp_type="nas")
    assert nas["nas|nas|cpu.gebruik"]["laatste_waarde"] == 12.5  # nooit de 99 % van de mini-pc
    assert nas["nas|nas|cpu.temperatuur"]["laatste_waarde"] == 48.0  # acpitz 0 °C genegeerd
    assert nas["nas|nas|geheugen.beschikbaar_pct"]["laatste_waarde"] == 75.0
    assert nas["nas|nas|zfs.arc"]["eenheid"] == "B"
    gpu = series(onderwerp_type="gpu")
    assert gpu["gpu|0000:03:00.0|gpu.gebruik"]["laatste_waarde"] == 30.0  # A310
    assert gpu["gpu|0000:00:02.0|gpu.gebruik"]["laatste_waarde"] == 5.0  # UHD 770
    assert not any("temperatuur" in k for k in gpu), "Beszel levert geen GPU-temperatuur: geen meting, geen 0 °C"

    # Na een herstart wisselen de render-nodes/sleutels: de koppeling op naam blijft A310 ↔ 0000:03:00.0.
    st = beszel.stats["nas000000000001"]
    st["stats"] = nas_stats(
        {"card0": {"n": "Intel UHD Graphics 770", "u": 7.0}, "card1": {"n": "Intel Arc A310", "u": 44.0}}
    )
    st["created"] = datetime.now(UTC)
    admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).raise_for_status()
    gpu = series(onderwerp_type="gpu")
    assert gpu["gpu|0000:03:00.0|gpu.gebruik"]["laatste_waarde"] == 44.0
    assert gpu["gpu|0000:00:02.0|gpu.gebruik"]["laatste_waarde"] == 7.0

    # Dubbelzinnige namen: geen toewijzing (en dus geen meting) in plaats van een gok.
    st["stats"] = nas_stats({"card0": {"n": "Intel Graphics", "u": 50.0}})
    st["created"] = datetime.now(UTC)
    r = admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).json()
    assert r["bron"]["detail"]["gpu_niet_toegewezen"][0]["reden"] == "geen_modelnummer_in_naam"
    assert series(onderwerp_type="gpu")["gpu|0000:03:00.0|gpu.gebruik"]["laatste_waarde"] == 44.0

    # Verkeerd wachtwoord → eerlijk 'inloggen mislukt', geen data.
    admin.patch(
        f"/api/v1/monitoring/sources/{src['id']}", json={"wachtwoord": "Fout-Wachtwoord-99"}, headers=idem()
    ).raise_for_status()
    r = admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).json()
    assert r["resultaat"] == {"status": "fout", "reden": "inloggen_mislukt"}
    make_user(admin, "operator1", "operator")
    op = login_as(app, "operator1")
    assert op.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).status_code == 403
    assert op.get("/api/v1/monitoring/sources").status_code == 200


def _enroll(admin: Any, app_id: str) -> tuple[str, str]:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    r = admin.post("/api/v1/services/enroll", json=enroll_body(app_id, token=r.json()["enrollment_token"]))
    assert r.status_code == 200, r.text
    return str(r.json()["service_id"]), str(r.json()["service_token"])


def test_heartbeat_en_connector_health_200_zonder_jobs_is_degraded(
    admin: Any, app: Any, client: Any, fake_nas: FakeTrueNAS, worker_once: Any, kuma: FakeUptimeKuma, clean_db: str
) -> None:
    service_id, token = _enroll(admin, "home-control-hub")
    dienst = FakeDienst(app.state.keyring().jwt_signing.public_key(), "home-control-hub", service_id).start()
    try:
        fake_nas.data["app.query"].append(
            _app(
                "home-control-hub",
                "RUNNING",
                "ghcr.io/lvos04/home-control-hub:0.1.0",
                dienst.port,
                30420,
                "/mnt/x",
                "/appdata",
            )
        )
        connect(admin, fake_nas)
        refresh(admin, worker_once)
        kuma.add(7, "Home Control Hub", url=f"http://127.0.0.1:{dienst.port}/healthz")
        _source(admin, {"soort": "uptime_kuma", "naam": "Kuma", "basis_url": kuma.url, "api_key": KEY})

        hch = _apps(admin)["home-control-hub"]
        assert hch["adaptertype"] == "eigen_dienst"
        bearer = {"Authorization": f"Bearer {token}"}
        now = datetime.now(UTC)

        def beat(**kw: Any) -> Any:
            body = {"status": "healthy", "observed_at": datetime.now(UTC).isoformat(), "verwacht_interval_s": 60, **kw}
            return client.post("/api/v1/monitoring/heartbeat", json=body, headers=bearer)

        # Connector-health eerst: dienst zegt healthy, Kuma zegt up → gezond.
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        assert dienst.rejected == []
        assert _apps(admin)["home-control-hub"]["gezondheid"]["status"] == "healthy"

        # 200 maar de worker-controle faalt (B09-002). Contract 1.3 §6: het totaal is de slechtste check, dus een
        # worker die down is maakt de dienst down; een beperkte jobs-check maakt hem beperkt.
        dienst.health = {"status": "healthy", "checks": [{"name": "worker", "status": "down"}]}
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        g = _apps(admin)["home-control-hub"]["gezondheid"]
        assert g["status"] == "down" and g["reason_code"] == "jobs_staan_stil"
        dienst.health = {"status": "healthy", "checks": [{"name": "jobs", "status": "degraded"}]}
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        g = _apps(admin)["home-control-hub"]["gezondheid"]
        assert g["status"] == "degraded" and g["reason_code"] == "jobs_staan_stil"
        dienst.health = {"status": "healthy", "checks": [{"name": "worker", "status": "healthy"}]}

        # Heartbeat met taken die al lang niet meer afgerond worden → degraded.
        stil = {
            "wachtrij": 5,
            "laatste_job_klaar": (now - timedelta(hours=2)).isoformat(),
            "laatste_hartslag": now.isoformat(),
        }
        r = beat(worker=stil)
        assert r.status_code == 202 and r.json()["beoordeling"] == {"status": "degraded", "reden": "jobs_staan_stil"}
        assert _apps(admin)["home-control-hub"]["gezondheid"]["reason_code"] == "jobs_staan_stil"
        again = client.post(
            "/api/v1/monitoring/heartbeat",
            json={"status": "healthy", "observed_at": datetime.now(UTC).isoformat()},
            headers=bearer,
        )
        assert again.status_code == 429 and again.headers["Retry-After"] == "5"
        # Heartbeat en connector-health blijven uit (10 min): binnenkant verouderd → unknown, nooit 'nog gezond'.
        _age_observations(clean_db, 10)
        g = _apps(admin)["home-control-hub"]["gezondheid"]
        assert g["status"] == "unknown" and g["reason_code"] == "meting_verouderd"

        # Validatie en rechten.
        old = client.post(
            "/api/v1/monitoring/heartbeat",
            json={"status": "healthy", "observed_at": (now - timedelta(hours=1)).isoformat()},
            headers=bearer,
        )
        assert old.status_code == 422
        assert (
            admin.post(
                "/api/v1/monitoring/heartbeat", json={"status": "healthy", "observed_at": now.isoformat()}
            ).status_code
            == 401
        )
        extra = client.post(
            "/api/v1/monitoring/heartbeat",
            json={"status": "healthy", "observed_at": now.isoformat(), "geheim": "x"},
            headers=bearer,
        )
        assert extra.status_code == 422

        # Dienst onbereikbaar: eerste fout = grace (unknown), tweede = down.
        dienst.offline()
        with psycopg.connect(clean_db, autocommit=True) as conn:
            conn.execute("DELETE FROM health_observation WHERE bron_type = 'heartbeat'")
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        conn_obs = admin.get("/api/v1/monitoring/health", params={"bron_type": "connector"}).json()["items"][0]
        assert conn_obs["status"] == "unknown" and conn_obs["reason_code"] == "eerste_fout_grace"
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        g = _apps(admin)["home-control-hub"]["gezondheid"]
        assert g["status"] == "down" and g["reason_code"] == "dienst_onbereikbaar"

        # Dienst weigert de Hub (bv. ontkoppeld): nooit gezond, geen open toegang.
        dienst.online()
        dienst.service_id = "00000000-0000-4000-8000-000000000000"
        admin.post("/api/v1/monitoring/poll", headers=idem()).raise_for_status()
        conn_obs = admin.get("/api/v1/monitoring/health", params={"bron_type": "connector"}).json()["items"][0]
        assert conn_obs["status"] == "unknown" and conn_obs["reason_code"] == "dienst_weigerde"
        assert _apps(admin)["home-control-hub"]["gezondheid"]["status"] == "unknown"
    finally:
        dienst.stop()
    status = admin.get("/api/v1/monitoring/status").json()
    assert {t["naam"] for t in status["taken"]} >= {"bronnen_pollen", "alerts_evalueren", "meldingen_versturen"}
