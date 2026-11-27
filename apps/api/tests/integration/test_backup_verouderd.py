"""EX12 (S-P2-060): een verouderde eigen back-up geeft een kritiek incident en de R2/R3-gate blijft dicht met
``backup_gate_rood``. Echte pg_dump-export, echte worker-taak en echte gate-beoordeling; alleen de leeftijd van de
export wordt teruggezet (Sim-getest)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from conftest import idem
from sqlalchemy import func, select

pytestmark = pytest.mark.integration
SOORT = "backup.verouderd"


def _incidenten(admin: Any) -> list[dict[str, Any]]:
    r = admin.get("/api/v1/incidents", params={"soort": SOORT, "status": "alle"})
    assert r.status_code == 200, r.text
    return list(r.json()["items"])


def _stale_events(app: Any) -> int:
    from hub.models import OutboxEvent

    with app.state.sessionmaker() as db:
        return int(db.scalar(select(func.count()).where(OutboxEvent.event_type == "backup.freshness.stale")) or 0)


def _r2_r3_codes(app: Any, settings: Any) -> set[str]:
    from asm_policy import load_policy

    from hub.actions import blokkades
    from hub.onboarding import gates

    with app.state.sessionmaker() as db:
        uit = gates.evaluate(blokkades.gate_inputs(db, settings))
        return {b["code"] for b in blokkades.uit_gates(load_policy(), uit, ["r2_r3_acties"])}


def _eigen_backup_te_oud(admin: Any) -> bool:
    """Noemt de back-upgate de eigen export als reden? (De besluiten D04/D05/D16 staan hier Open en houden de gate
    los daarvan al dicht; deze test kijkt naar de meting.)"""
    gate = admin.get("/api/v1/gates/backup_gate").json()
    assert gate["status"] != "toegestaan", gate
    return any(r["id"] == "eigen_backup" for r in gate["redenen"])


def test_verouderde_backup_geeft_kritiek_incident_en_houdt_r2_r3_dicht(
    admin: Any, app: Any, settings: Any, worker_once: Any, periodic_run: Any
) -> None:
    from hub.models import SelfBackup

    assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
    assert worker_once()[-1]["status"] == "geslaagd"
    # Vers: geen incident (negatieve rij) en de eigen export is geen reden voor de dichte back-upgate.
    assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"] is False
    assert _incidenten(admin) == [] and not _eigen_backup_te_oud(admin)

    max_leeftijd = settings.self_backup_interval_seconds + 2 * 3600
    with app.state.sessionmaker() as db:
        for b in db.scalars(select(SelfBackup)):
            b.finished_at = b.finished_at - timedelta(seconds=max_leeftijd + 60)
            b.started_at = b.started_at - timedelta(seconds=max_leeftijd + 60)
        db.commit()
    assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"] is True
    [inc] = _incidenten(admin)
    assert inc["status"] == "open" and inc["ernst"] == "kritiek" and inc["bron"] == "hub:backup", inc
    assert _eigen_backup_te_oud(admin) and "backup_gate_rood" in _r2_r3_codes(app, settings)
    # Nog steeds verouderd: hetzelfde incident, geen nieuw event per ronde.
    periodic_run("incidenten_bijwerken")
    assert len(_incidenten(admin)) == 1 and _stale_events(app) == 1

    with app.state.sessionmaker.begin() as db:
        from hub.timeutil import utcnow

        db.scalars(select(SelfBackup)).one().deleted_at = utcnow()
    periodic_run("incidenten_bijwerken")
    assert _incidenten(admin)[0]["status"] == "open"
    assert _eigen_backup_te_oud(admin)

    # Een nieuwe, geverifieerde export: de gate is weer vrij van deze reden en het incident sluit.
    assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
    assert worker_once()[-1]["status"] == "geslaagd"
    assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"] is False
    [inc] = _incidenten(admin)
    assert inc["status"] == "opgelost", inc
    assert not _eigen_backup_te_oud(admin)


def test_volle_wachtrij_houdt_een_verouderingsevent(admin, app, settings, worker_once, periodic_run):
    from hub.events.envelope import emit
    from hub.models import SelfBackup

    assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
    assert worker_once()[-1]["status"] == "geslaagd"
    settings.incident_batch = 10
    with app.state.sessionmaker.begin() as db:
        export = db.scalars(select(SelfBackup)).one()
        leeftijd = timedelta(seconds=settings.self_backup_interval_seconds + 3 * 3600)
        export.started_at -= leeftijd
        export.finished_at -= leeftijd
        for i in range(2 * settings.incident_batch):
            emit(db, "monitoring.sample.observed", "sensor", str(i), {})
    for _ in range(2):
        assert periodic_run("incidenten_bijwerken")["incidenten_bijwerken"]["backup_verouderd"]
    assert _stale_events(app) == 1
