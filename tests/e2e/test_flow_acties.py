"""Dienst-E2E: een flow vraagt een actie aan via een nagebootste home-control-hub (B01-008; EX46 Hub-deel).

De **echte** Hub-API maakt van ``flow.action.requested`` een voorstel, ondertekent het ``ExecutionRequest`` en roept de
**echte** executor-app aan, die naar de fake TrueNAS schrijft. Sim-getest: geen echte Node-RED en geen echte NAS.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import Stack, app_target, bouw_stack, haal, schrijfaanroepen, voer_uit
from executorhelpers import write_nas
from fakes.fake_truenas import FakeTrueNAS
from flowhelpers import flow_audit, flow_event, flow_request_id, koppel_hch

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(
    admin: Any,
    app: Any,
    nas: FakeTrueNAS,
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Stack]:
    s = bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    yield s
    s.stop()


def test_vijf_keer_afgeleverd_geeft_een_voorstel_en_een_uitvoering(
    stack: Stack,
) -> None:
    hch = koppel_hch(stack.admin, stack.app)
    ev = flow_event("app.restart", app_target("my-house"))
    statussen = [hch.post("/api/v1/events/inbox", json=ev).json()["status"] for _ in range(5)]
    assert statussen == ["accepted"] + ["duplicate"] * 4
    # Een herhaalde push uit de outbox van home-control-hub met een nieuw event_id: nog steeds één voorstel.
    r = hch.post(
        "/api/v1/events/inbox",
        json={**ev, "event_id": str(uuid.uuid4()), "source_event_id": "2"},
    )
    assert r.json()["status"] == "accepted"
    rid = flow_request_id(ev)
    v = haal(stack.admin, rid)
    assert (v["status"], v["actor"]["type"]) == ("klaar", "flow")

    r = voer_uit(stack.admin, rid)
    assert r.status_code == 200, r.text
    assert haal(stack.admin, rid)["status"] == "uitgevoerd"
    assert schrijfaanroepen(stack.nas) == ["app.redeploy"]
    # Nog een keer uitvoeren of opnieuw afleveren geeft geen tweede uitvoering.
    assert voer_uit(stack.admin, rid).status_code >= 400
    assert hch.post("/api/v1/events/inbox", json=ev).json()["status"] == "duplicate"
    assert schrijfaanroepen(stack.nas) == ["app.redeploy"]
    acties = [a["action"] for a in flow_audit(stack.app)]
    assert acties.count("action.proposal.created") == 1


def test_dataset_verwijderen_via_flow_bereikt_de_executor_nooit(stack: Stack) -> None:
    hch = koppel_hch(stack.admin, stack.app)
    ev = flow_event("pool.dataset.delete", {"host_id": "nas-primary", "dataset": "tank/media"})
    assert hch.post("/api/v1/events/inbox", json=ev).status_code == 202
    rid = flow_request_id(ev)
    assert haal(stack.admin, rid)["status"] == "geweigerd"
    assert voer_uit(stack.admin, rid).status_code >= 400
    assert schrijfaanroepen(stack.nas) == []
    assert "action.proposal.refused" in [a["action"] for a in flow_audit(stack.app)]
