"""B12-004/EX12 (S-P2-090): verificatie van de externe (OneDrive-)back-up. De Hub leest de uploadtaak via de nagebootste
TrueNAS (``cloudsync.query``, alleen-lezen); een verouderde upload of verlopen aanmelding geeft een incident met hoge
prioriteit en houdt de back-upgate (en daarmee R2/R3) dicht. Nooit een echt OneDrive-account (Sim-getest)."""

from __future__ import annotations

import json
import logging
import uuid
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import idem
from fakes.fake_truenas import _app, _ms
from nashelpers import READONLY_KEY, connect, refresh
from sqlalchemy import func, select

pytestmark = pytest.mark.integration
SOORT = "backup.extern"
D04 = {
    "methode": "truenas_cloud_sync",
    "taken": ["Foto's naar OneDrive"],
    "versleuteld": False,
    "scope": ["testpool/photos"],
    "retentie": "30 dagen",
    "herstel_credentials_locatie": "Wachtwoordkluis van de beheerder",
}


def _incidenten(admin: Any) -> list[dict[str, Any]]:
    r = admin.get("/api/v1/incidents", params={"soort": SOORT, "status": "alle"})
    assert r.status_code == 200, r.text
    return list(r.json()["items"])


def _events(app: Any) -> int:
    from hub.models import OutboxEvent

    with app.state.sessionmaker() as db:
        return int(db.scalar(select(func.count()).where(OutboxEvent.event_type == "backup.offsite.stale")) or 0)


def _extern_reden(admin: Any) -> dict[str, Any] | None:
    gate = admin.get("/api/v1/gates/backup_gate").json()
    return next((r for r in gate["redenen"] if r["id"] == "extern_backup"), None)


def _r2_r3_codes(app: Any, settings: Any) -> set[str]:
    from asm_policy import load_policy

    from hub.actions import blokkades
    from hub.onboarding import gates

    with app.state.sessionmaker() as db:
        uit = gates.evaluate(blokkades.gate_inputs(db, settings))
        return {b["code"] for b in blokkades.uit_gates(load_policy(), uit, ["r2_r3_acties"])}


def _ronde(admin: Any, worker_once: Any, periodic_run: Any) -> str:
    refresh(admin, worker_once)
    return str(periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["extern_backup"])


def test_verouderde_upload_en_verlopen_aanmelding_geven_incident_en_gate_dicht(
    admin: Any, app: Any, settings: Any, worker_once: Any, periodic_run: Any, fake_nas: Any
) -> None:
    connect(admin, fake_nas)
    # Zonder D04 is de externe back-up onbekend: gate dicht, maar geen incident (er is niets gemeten dat faalt).
    assert _ronde(admin, worker_once, periodic_run) == "unknown"
    assert _extern_reden(admin)["status"] == "unknown" and _incidenten(admin) == []
    r = admin.put("/api/v1/decisions/D04/waarde", json={"waarde": D04}, headers=idem())
    assert r.status_code == 200, r.text

    # Vers en geslaagd (upload van 4 uur geleden): geen incident en geen reden voor de dichte back-upgate.
    assert _ronde(admin, worker_once, periodic_run) == "ok"
    assert _incidenten(admin) == [] and _extern_reden(admin) is None
    uit = admin.get("/api/v1/backups/extern").json()
    assert uit["status"] == "ok" and uit["taken"][0]["laatste_job_staat"] == "SUCCESS"
    assert "GEHEIM" not in str(uit)  # nooit credential-attributen (V-085)

    # Verouderde upload → kritiek incident; de gate blijft dicht met backup_gate_rood.
    job = fake_nas.data["cloudsync.query"][0]["job"]
    job["time_started"], job["time_finished"] = _ms(hours_ago=31), _ms(hours_ago=30)
    assert _ronde(admin, worker_once, periodic_run) == "verouderd"
    [inc] = _incidenten(admin)
    assert inc["status"] == "open" and inc["ernst"] == "kritiek" and inc["bron"] == "hub:backup", inc
    assert _extern_reden(admin)["status"] == "geblokkeerd"
    assert "backup_gate_rood" in _r2_r3_codes(app, settings)
    # Nog steeds een probleem (nu een verlopen aanmelding): hetzelfde incident, geen nieuw event per ronde.
    job.update(state="FAILED", time_finished=_ms(hours_ago=1), error="invalid_grant: AADSTS70008 token expired")
    assert _ronde(admin, worker_once, periodic_run) == "aanmelding_verlopen"
    assert len(_incidenten(admin)) == 1 and _events(app) == 1
    assert "backup_gate_rood" in _r2_r3_codes(app, settings)

    # Onbekend (TrueNAS weigert cloudsync.query) sluit het incident niet: alleen positief bewijs sluit.
    fake_nas.keys[READONLY_KEY].deny = {"cloudsync.query"}
    assert _ronde(admin, worker_once, periodic_run) == "unknown"
    assert _incidenten(admin)[0]["status"] == "open" and _extern_reden(admin)["status"] == "unknown"
    fake_nas.keys[READONLY_KEY].deny = set()

    # Weer een verse, geslaagde upload: het incident sluit en de gate heeft deze reden niet meer.
    job.update(state="SUCCESS", time_finished=_ms(hours_ago=1), error=None)
    assert _ronde(admin, worker_once, periodic_run) == "ok"
    [inc] = _incidenten(admin)
    assert inc["status"] == "opgelost", inc
    assert _extern_reden(admin) is None


def _taakbesluit(admin: Any, taken: list[str]) -> None:
    r = admin.put("/api/v1/decisions/D04/waarde", json={"waarde": {**D04, "taken": taken}}, headers=idem())
    assert r.status_code == 200, r.text


def test_dubbele_omschrijving_houdt_gate_dicht_en_incident_open(
    admin: Any, fake_nas: Any, worker_once: Any, periodic_run: Any
) -> None:
    """R-HARDE-EIS-3: een gezonde taak met dezelfde omschrijving verbergt de mislukte niet (elke volgorde)."""
    connect(admin, fake_nas)
    taken = fake_nas.data["cloudsync.query"]
    gezond = deepcopy(taken[0])
    gezond["id"] += 100
    taken[0]["job"].update(state="FAILED", error="teststoring")
    _taakbesluit(admin, [gezond["description"]])
    assert _ronde(admin, worker_once, periodic_run) == "mislukt"
    for plek in (0, len(taken)):
        taken.insert(plek, gezond)
        assert _ronde(admin, worker_once, periodic_run) == "ontbreekt"
        assert _extern_reden(admin) is not None and _incidenten(admin)[0]["status"] == "open"
        taken.remove(gezond)


def test_oudere_upload_heft_latere_storing_niet_op(
    admin: Any, fake_nas: Any, worker_once: Any, periodic_run: Any
) -> None:
    """R-HARDE-EIS-5: na een storing telt alleen een LATERE geslaagde upload als herstel."""
    connect(admin, fake_nas)
    taak = fake_nas.data["cloudsync.query"][0]
    _taakbesluit(admin, [str(taak["id"])])
    eerdere_upload = deepcopy(taak["job"])  # geslaagd, vier uur geleden
    taak["job"].update(state="FAILED", time_started=_ms(hours_ago=2), time_finished=_ms(hours_ago=1), error="x")
    assert _ronde(admin, worker_once, periodic_run) == "mislukt"
    taak["job"] = eerdere_upload
    assert _ronde(admin, worker_once, periodic_run) == "mislukt"
    assert _extern_reden(admin) is not None and _incidenten(admin)[0]["status"] == "open"
    taak["job"] = {**eerdere_upload, "time_started": _ms(hours_ago=0.5), "time_finished": _ms(hours_ago=0.25)}
    assert _ronde(admin, worker_once, periodic_run) == "ok"
    assert _incidenten(admin)[0]["status"] == "opgelost"


def test_vrije_taaktekst_blijft_uit_antwoord_events_en_log(
    admin: Any, app: Any, fake_nas: Any, worker_once: Any, periodic_run: Any, caplog: Any
) -> None:
    """R-HARDE-EIS-7: een kijker ziet de taakomschrijving niet; ook niet in gate, incident, events of log."""
    from conftest import login_as, make_user

    from hub.models import OutboxEvent

    connect(admin, fake_nas)
    taak = fake_nas.data["cloudsync.query"][0]
    _taakbesluit(admin, [str(taak["id"])])
    make_user(admin, "lezer", "viewer")
    markering = uuid.uuid4().hex
    taak["description"] = "proef?access_token=" + markering
    caplog.clear()
    with caplog.at_level(logging.INFO), login_as(app, "lezer") as lezer:
        _ronde(admin, worker_once, periodic_run)
        antwoord = lezer.get("/api/v1/backups/extern")
        assert antwoord.status_code == 200, antwoord.text
        sporen = [antwoord.text, admin.get("/api/v1/gates/backup_gate").text, json.dumps(_incidenten(admin))]
        with app.state.sessionmaker() as db:
            sporen.extend(json.dumps(x) for x in db.scalars(select(OutboxEvent.payload)))
        sporen.append(caplog.text)
    assert not any(markering in x for x in sporen)


def test_vertraagd_herstelbericht_sluit_nieuwe_storing_niet(app: Any, settings: Any, monkeypatch: Any) -> None:
    """R-HARDE-EIS-6: een herstelbericht dat pas na een nieuwe storing wordt verwerkt, sluit het incident niet."""
    from hub.events.envelope import emit
    from hub.incidents import engine, rules
    from hub.monitoring import periodic
    from hub.routers import onboarding
    from hub.timeutil import utcnow

    meting = {"status": "mislukt"}
    monkeypatch.setattr(onboarding, "gate_inputs", lambda *a: SimpleNamespace(eigen_backup=None, extern_backup=meting))
    settings.incident_batch = 10
    with app.state.sessionmaker.begin() as db:

        def ronde(status: str) -> None:
            meting["status"] = status
            periodic._task_incidents(db, SimpleNamespace(settings=settings, now=utcnow()))
            db.flush()

        ronde("mislukt")
        for _ in range(settings.incident_batch):  # achterstand: het herstelbericht blijft een ronde liggen
            emit(db, "proef.achterstand.meting", "proef", "proef", {})
        ronde("ok")
        assert engine.active_for(db, rules.OFFSITE_FP) is not None
        ronde("mislukt")
        assert engine.active_for(db, rules.OFFSITE_FP) is not None
        ronde("ok")  # een actuele, goede meting sluit wel
        ronde("ok")
        assert engine.active_for(db, rules.OFFSITE_FP) is None


def test_strengste_rpo_telt_ook_de_catalogusnaam(
    admin: Any, app: Any, fake_nas: Any, worker_once: Any, settings: Any
) -> None:
    """R-HARDE-EIS-2: de strengste RPO over runtime- én catalogusnaam; 30 minuten oud telt dan niet bij 15 min."""
    from asm_policy import load_policy

    from hub.actions import blokkades
    from hub.timeutil import utcnow

    fake_nas.data["app.query"].append(
        _app("proef", "RUNNING", "proef:1", 8044, 8044, "/proef/app", "/config", catalog_app="proefcatalogus")
    )
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    d16 = {
        "per_app": [
            {"app_id": "proef", "rpo_uren": 1, "rto_uren": 1},
            {"app_id": "proefcatalogus", "rpo_uren": 0.25, "rto_uren": 1},
        ]
    }
    r = admin.put("/api/v1/decisions/D16/waarde", json={"waarde": d16}, headers=idem())
    assert r.status_code == 200, r.text
    with app.state.sessionmaker() as db:
        namen = blokkades.herkenningen(db, settings, load_policy(), "proef", SimpleNamespace(herkend_als=None))
        rpo = blokkades.rpo_seconden(db, settings, namen)
    nu = utcnow()
    assert "proefcatalogus" in namen and rpo == 900
    assert not blokkades.beoordeel_herstelpunt(
        namen=namen, db_export=None, gemaakt_op=nu - timedelta(minutes=30), rpo_s=rpo, now=nu
    )[2]
