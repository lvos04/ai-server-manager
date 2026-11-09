"""Dienst-E2E: out-of-band melden (B09-005, EX22, EX23) — Sim-getest, NIET GEVALIDEERD op een echte NAS/telefoon.

EX22 "Stop Hub → Uptime Kuma/Gotify blijven melden": hier gesimuleerd als **topologie**: de Hub leest Uptime Kuma alleen
(GET) en heeft geen route die Kuma-meldingen ontvangt; Kuma's eigen Gotify-melding (gesimuleerd naar de Gotify-provider
van Uptime Kuma: ``POST /message?token=…``) komt aan terwijl de Hub-app en de worker gestopt zijn.
EX23 "Volledige NAS offline": de Hub claimt nooit out-of-band dekking zonder externe host; draaien Kuma of Gotify op het
NAS-adres, dan zegt de Hub dat er bij NAS-uitval niets meldt.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from typing import Any

import pytest
from conftest import idem, login_as, make_user
from fakes.fake_gotify import FakeGotify
from fakes.fake_monitoring import FakeUptimeKuma
from fakes.fake_truenas import FakeTrueNAS, _app
from nashelpers import connect, refresh

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
KEY = "uk1_testkey_abcdef"
GOTIFY_KUMA = "KumaEigenToken77"
GOTIFY_HUB = "HubEigenToken88"


def kuma_notify(gotify_url: str, token: str, monitor: str) -> int:
    """Simulatie van de Gotify-melding die Uptime Kuma zelf verstuurt (geen Hub in het pad)."""
    body = json.dumps(
        {"message": f"[{monitor}] [🔴 Down] connect ECONNREFUSED", "priority": 8, "title": "Uptime-Kuma"}
    ).encode()
    req = urllib.request.Request(  # noqa: S310 - lokale fake (http://127.0.0.1)
        f"{gotify_url}/message?token={token}", data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 - lokale fake
        return int(resp.status)


def test_ex22_kuma_meldt_zonder_hub_en_hub_zit_niet_in_het_pad(
    admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any, periodic_run: Any
) -> None:
    fake_nas.data["app.query"].append(
        _app(
            "ai-server-manager",
            "RUNNING",
            "ghcr.io/lvos04/ai-server-manager:0.1.0",
            30400,
            30400,
            "/mnt/testpool/apps/hub",
            "/appdata",
        )
    )
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    kuma = FakeUptimeKuma(api_keys={KEY}).start()
    gotify = FakeGotify(tokens={GOTIFY_KUMA, GOTIFY_HUB}).start()
    try:
        kuma.add(1, "Hub", url="http://127.0.0.1:30400/healthz")
        src = admin.post(
            "/api/v1/monitoring/sources",
            json={"soort": "uptime_kuma", "naam": "Kuma", "basis_url": kuma.url, "api_key": KEY},
            headers=idem(),
        ).json()
        admin.post(f"/api/v1/monitoring/sources/{src['id']}/test", headers=idem()).raise_for_status()
        admin.post(
            "/api/v1/notifications/channels",
            json={"naam": "Telefoon", "basis_url": gotify.url, "token": GOTIFY_HUB},
            headers=idem(),
        ).raise_for_status()
        st = admin.get("/api/v1/monitoring/out-of-band").json()
        assert st["hub_in_meldpad"] is False
        assert st["hub_uitval"]["status"] == "kuma_bewaakt_hub" and st["hub_uitval"]["bewaakt"]["ai-server-manager"]
        assert st["kuma_meldt_via_gotify"] == "onbekend"  # niet uit /metrics te lezen: nooit aangenomen
        # De Hub las Kuma alleen: geen schrijfactie, geen meldingsinstelling, geen webhook naar de Hub.
        assert {r.method for r in kuma.requests} == {"GET"}
        paths = app.openapi()["paths"]
        assert not [p for p in paths if "kuma" in p.lower() or "webhook" in p.lower()]

        # Hub (API) en worker stoppen; Kuma ziet de Hub 'down' en meldt zelf via Gotify.
        seen_before = len(kuma.requests)
        admin.close()
        app.state.engine.dispose()
        kuma.monitors[0]["status"] = 0
        assert kuma_notify(gotify.url, GOTIFY_KUMA, "Hub") == 200
        assert gotify.messages[-1]["title"] == "Uptime-Kuma" and "[Hub]" in gotify.messages[-1]["message"]
        assert len(kuma.requests) == seen_before  # niemand vroeg Kuma iets; de Hub stond uit
    finally:
        kuma.stop()
        gotify.stop()


def test_ex23_geen_claim_zonder_externe_host_en_bevestiging_alleen_handmatig(admin: Any, app: Any) -> None:
    admin.put(
        "/api/v1/decisions/D03/waarde",
        json={"waarde": {"nas_adres": "10.20.30.40", "https_poort": 443}},
        headers=idem(),
    ).raise_for_status()
    st = admin.get("/api/v1/monitoring/out-of-band").json()
    assert st["hub_uitval"]["status"] == "niet_ingericht"
    assert st["volledige_nas_uitval"]["status"] == "niet_gedekt" and st["volledige_nas_uitval"]["gedekt"] is False
    # Kuma op het NAS-adres → bij NAS-uitval meldt niemand iets.
    on_nas = admin.post(
        "/api/v1/monitoring/sources",
        json={"soort": "uptime_kuma", "naam": "Kuma", "basis_url": "http://10.20.30.40:3001", "api_key": KEY},
        headers=idem(),
    ).json()
    st = admin.get("/api/v1/monitoring/out-of-band").json()
    assert st["uptime_kuma"][0]["locatie"] == "op_de_nas"
    assert st["volledige_nas_uitval"]["status"] == "niet_gedekt"
    assert "meldt niemand iets" in st["volledige_nas_uitval"]["tekst"]
    assert st["hub_uitval"]["status"] == "hiaat"  # Kuma bewaakt de Hub (nog) niet
    # Kuma op een ander adres: hooguit 'extern_onbevestigd', nooit 'gedekt'.
    admin.patch(
        f"/api/v1/monitoring/sources/{on_nas['id']}", json={"basis_url": "http://10.99.0.5:3001"}, headers=idem()
    ).raise_for_status()
    st = admin.get("/api/v1/monitoring/out-of-band").json()
    assert (
        st["volledige_nas_uitval"]["status"] == "extern_onbevestigd" and st["volledige_nas_uitval"]["gedekt"] is False
    )
    # Een handmatige test vastleggen: alleen admin, met audit; uitkomst blijft 'handmatig bevestigd'.
    body = {
        "getest_op": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "kuma_meldt_hub_uitval": True,
        "kuma_gotify_test_ontvangen": True,
        "externe_host": True,
        "notitie": "Kuma op de mini-server",
    }
    make_user(admin, "op-ob", "operator")
    assert (
        login_as(app, "op-ob").post("/api/v1/monitoring/out-of-band/bevestiging", json=body, headers=idem()).status_code
        == 403
    )
    r = admin.post("/api/v1/monitoring/out-of-band/bevestiging", json=body, headers=idem())
    assert r.status_code == 201, r.text
    st = r.json()
    assert st["kuma_meldt_via_gotify"] == "handmatig_bevestigd"
    assert st["volledige_nas_uitval"]["status"] == "extern_handmatig_bevestigd"
    assert st["volledige_nas_uitval"]["gedekt"] is False and st["laatste_bevestiging"]["door"] == "beheerder"
    # Hostnaam tegenover een IP-adres: niet te beslissen → onbekend (geen aanname).
    admin.patch(
        f"/api/v1/monitoring/sources/{on_nas['id']}", json={"basis_url": "http://kuma.thuis:3001"}, headers=idem()
    ).raise_for_status()
    st = admin.get("/api/v1/monitoring/out-of-band").json()
    assert st["uptime_kuma"][0]["locatie"] == "onbekend" and st["volledige_nas_uitval"]["status"] == "onbekend"
