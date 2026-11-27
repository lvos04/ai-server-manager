"""De kredietgrens overleeft losse Hub-sessies, herhaling van een taak en gelijktijdige aanvragen."""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import select

from hub import audit
from hub.ai import tegoed
from hub.ai.runner import Triage
from hub.errors import HubError
from hub.models import AuditEvent, Decision
from hub.timeutil import utcnow

pytestmark = pytest.mark.integration


def test_reservering_blijft_binnen_maandbudget_en_bewaart_bestaande_audit(app: Any, settings: Any, admin: Any) -> None:
    settings.ai_enabled = True
    settings.ai_provider_url = "https://krediet.invalid"
    now = utcnow()
    triage = Triage(ernst="info", gebeurtenissen=1, inventaris="unknown", logregels=0)
    with app.state.sessionmaker() as db:
        bestaand = list(db.execute(select(AuditEvent.id, AuditEvent.hash).order_by(AuditEvent.id)))
        assert bestaand
        row = db.get_one(Decision, "D09")
        for waarde, verwacht in (
            ({}, "d09_open"),
            ({"account_gekoppeld": True, "harde_stop": True, "overage_toegestaan": False}, "tegoed_onbekend"),
        ):
            row.status, row.waarde = "Getest", waarde
            db.commit()
            assert tegoed.stand(db, settings, now).status == verwacht
        row.waarde = {
            **row.waarde,
            "tegoedmaand": now.strftime("%Y-%m"),
            "inbegrepen_eenheden": 2,
            "max_eenheden_per_taak": 2,
            "aanbieder": uuid.uuid4().hex,
            "modelkeuze": uuid.uuid4().hex,
        }
        db.commit()
    start = threading.Barrier(2)

    def reserveer(_: int) -> Any:
        with app.state.sessionmaker() as db:
            start.wait(timeout=10)
            return tegoed.reserveer(db, settings, uuid.uuid4(), "operator", triage)

    with ThreadPoolExecutor(max_workers=2) as pool:
        beurten = list(pool.map(reserveer, range(2)))
    assert sorted(status for status, _ in beurten) == ["gereserveerd", "tegoed_op"]
    taak = next(t for _, t in beurten if t is not None)
    with app.state.sessionmaker() as db:
        with pytest.raises(HubError, match="al krediet gereserveerd"):
            tegoed.reserveer(db, settings, taak.taak_id, "operator", triage)
        assert tegoed.stand(db, settings, now).beschikbaar == 0
        assert tegoed.stand(db, settings, now.replace(year=now.year + 1)).status == "tegoed_onbekend"
        assert (
            db.execute(select(AuditEvent.id, AuditEvent.hash).order_by(AuditEvent.id).limit(len(bestaand))).all()
            == bestaand
        )
        assert audit.verify(db)["status"] == "intact"
    assert admin.get("/api/v1/ai/providers").json()["tegoed"]["gereserveerd"] == 2
    pagina = admin.get("/api/v1/ai/audit").json()
    assert [r["actie"] for r in pagina["items"]] == [tegoed.RESERVERING]
