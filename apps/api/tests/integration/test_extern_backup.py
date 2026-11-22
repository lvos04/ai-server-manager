"""B12-004/EX12 (S-P2-090): verificatie van de externe (OneDrive-)back-up. De Hub leest de uploadtaak via de nagebootste
TrueNAS (``cloudsync.query``, alleen-lezen); een verouderde upload of verlopen aanmelding geeft een incident met hoge
prioriteit en houdt de back-upgate (en daarmee R2/R3) dicht. Nooit een echt OneDrive-account (Sim-getest)."""

from __future__ import annotations

from typing import Any

import pytest
from conftest import idem
from fakes.fake_truenas import _ms
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
