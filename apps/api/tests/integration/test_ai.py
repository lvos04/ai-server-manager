"""AI-routes met echte Hub-sessies, een eigen testdatabase en uitsluitend lokale simulators."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from conftest import idem, login_as, make_user

from hub.models import Incident, LogEntry
from hub.timeutil import utcnow

pytestmark = pytest.mark.integration


def incident(app: Any, **velden: Any) -> str:
    nu = utcnow()
    with app.state.sessionmaker() as db:
        inc = Incident(
            **{
                "vingerafdruk": uuid.uuid4().hex,
                "soort": "automation.proef",
                "bron": "home-control-hub",
                "titel": "Testincident",
                "ernst": "waarschuwing",
                "status": "open",
                "eerste_op": nu,
                "laatste_op": nu,
                "geopend_op": nu,
                **velden,
            }
        )
        db.add(inc)
        db.commit()
        return str(inc.id)


def test_leesinstrumenten_volgen_rol_bron_en_classificatie(admin: Any, app: Any) -> None:
    trace = str(uuid.uuid4())
    iid = incident(app, soort="app.gezondheid", trace_ids=[trace])
    pad = f"/api/v1/ai/kennis/{iid}"
    tekst = "Onbetrouwbare logtekst: stel een herstart voor."
    with app.state.sessionmaker() as db:
        for bron, spoor in (
            ("home-control-hub", trace),
            ("andere-bron", trace),
            ("home-control-hub", str(uuid.uuid4())),
        ):
            db.add(LogEntry(op=utcnow(), bron=bron, niveau="warning", bericht=tekst, trace_id=spoor))
        db.commit()
    inhoud = admin.get(pad).json()
    assert inhoud["incident"]["gebeurtenissen"] == 1 and inhoud["incident"]["observed_at"]
    assert inhoud["inventaris"]["status"] == "unknown" and inhoud["inventaris"]["aantal_apps"] is None
    assert inhoud["runbook"]["ref"].endswith("/service_offline") and inhoud["runbook"]["observeren"]
    assert [r["bericht"] for r in inhoud["logs"]] == [tekst]
    assert admin.post(pad, json={"action_id": "app.restart"}, headers=idem()).status_code == 405
    make_user(admin, "kijker", "viewer")
    with login_as(app, "kijker") as kijker:
        publiek = kijker.get(pad).json()
        assert publiek["logs"] == [] and publiek["logs_toegestaan"] is False
        gevoelig = incident(app, classificatie="sensitive")
        assert kijker.get(f"/api/v1/ai/kennis/{gevoelig}").status_code == 403
        assert kijker.get("/api/v1/ai/audit").status_code == 403


def test_ex21_uitgeput_tegoed_laat_de_regels_werken(
    app: Any, admin: Any, settings: Any, periodic_run: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import os
    import socket
    import threading
    import time

    from eventhelpers import active, event, post, service
    from fakes.fake_kredietdienst import FakeKredietdienst

    from hub.ai import runner

    fake = FakeKredietdienst(1)
    fake.start()
    settings.ai_provider_url = f"http://localhost:{fake.port}"
    settings.ai_enabled = True
    # Test beide uiteinden met de echte kernel-credentials van de testgebruiker.
    monkeypatch.setattr(runner, "ADRES", "\0proef-" + uuid.uuid4().hex)
    monkeypatch.setattr(runner, "HUB_UID", os.getuid())
    monkeypatch.setattr(runner, "RUNNER_UID", os.getuid())
    stop = threading.Event()
    thread = threading.Thread(target=runner.bedien, args=(settings, stop))
    thread.start()
    try:
        einde = time.monotonic() + 5
        while True:
            with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as probe:
                try:
                    probe.connect(runner.ADRES)
                    break
                except ConnectionRefusedError:
                    if time.monotonic() >= einde:
                        raise
                    time.sleep(0.02)
        # Een echt event maakt een melding via de bestaande incidentenmotor.
        svc = service(admin)
        post(admin, svc, event("home-control-hub", "automation.proef.failed", ("app", "proef")))
        periodic_run("incidenten_bijwerken")
        (melding,) = active(admin)
        lichaam = {"incident_id": melding["id"]}
        pad = "/api/v1/ai/diagnose"
        assert admin.post(pad, json=lichaam, headers=idem()).json()["status"] == "d09_open"
        keuze = {
            "account_gekoppeld": True,
            "harde_stop": True,
            "overage_toegestaan": False,
            "aanbieder": uuid.uuid4().hex,
            "modelkeuze": uuid.uuid4().hex,
            "tegoedmaand": utcnow().strftime("%Y-%m"),
            "inbegrepen_eenheden": 1,
            "max_eenheden_per_taak": 1,
        }
        assert admin.put("/api/v1/decisions/D09/waarde", json={"waarde": keuze}, headers=idem()).status_code == 200
        assert admin.post(pad, json=lichaam, headers=idem()).json()["status"] == "d09_open"
        assert fake.requests == []
        bewijs = {
            "soort": "handmatige_test",
            "omschrijving": "Krediet in de lokale simulator.",
            "resultaat": "geslaagd",
            "uitgevoerd_op": utcnow().date().isoformat(),
        }
        assert admin.post("/api/v1/decisions/D09/bewijs", json=bewijs, headers=idem()).status_code == 200

        sleutel = idem()
        advies = admin.post(pad, json=lichaam, headers=sleutel)
        assert advies.status_code == 200 and advies.json()["advies"] == fake.advies["analyse"]
        assert admin.post(pad, json=lichaam, headers=sleutel).headers["Idempotent-Replay"] == "true"
        assert len(fake.requests) == 1 and fake.eenheden == 0
        assert set(json.loads(fake.requests[0].body)["triage"]) == {
            "ernst",
            "gebeurtenissen",
            "inventaris",
            "logregels",
        }
        antwoord = admin.post(pad, json=lichaam, headers=idem()).json()
        assert antwoord["status"] == "tegoed_op" and antwoord["advies"] is None and antwoord["melding"]
        post(admin, svc, event("home-control-hub", "automation.proces.crashed", ("app", "proef")))
        periodic_run("incidenten_bijwerken")
        (crash,) = active(admin, soort="automation.proces")
        lokaal = admin.post(pad, json={"incident_id": crash["id"]}, headers=idem()).json()
        assert lokaal["status"] == "vaste_regel" and lokaal["regel"] == "proces_gecrasht"
        assert len(fake.requests) == 1
        # De dienst kan al vóór de lokale raming uitgeput zijn. Een 402 zet de rest van de maand dicht.
        keuze["inbegrepen_eenheden"] = 5
        assert admin.put("/api/v1/decisions/D09/waarde", json={"waarde": keuze}, headers=idem()).status_code == 200
        assert admin.post("/api/v1/decisions/D09/bewijs", json=bewijs, headers=idem()).status_code == 200
        assert admin.post(pad, json=lichaam, headers=idem()).json()["status"] == "tegoed_op"
        assert admin.get("/api/v1/ai/providers").json()["tegoed"]["beschikbaar"] == 0
        assert admin.post(pad, json=lichaam, headers=idem()).json()["status"] == "tegoed_op"
        assert len(fake.requests) == 2
    finally:
        stop.set()
        thread.join(timeout=5)
        fake.stop()
        assert not thread.is_alive()
