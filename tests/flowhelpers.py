"""Nagebootste home-control-hub voor flowtests (B01-008; Sim-getest).

Gekoppeld met een echt service-token van de Hub en stuurt ``flow.action.requested`` in precies de vorm van
``home-control-hub/apps/api/src/integrations/domains/automation/actions.py`` (``request_action``) en
``integrations/events.py`` (envelope). Alleen testwaarden.
"""

from __future__ import annotations

import uuid
from typing import Any

from conftest import enroll_body

from hub.timeutil import iso, utcnow

HCH = "home-control-hub"


def koppel_hch(admin: Any, app: Any) -> Any:
    """Een client met het service-token van home-control-hub (koppelen zoals bij elke eigen dienst)."""
    from fastapi.testclient import TestClient

    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": HCH}).json()["enrollment_token"]
    c = TestClient(app, base_url="https://testserver")
    svc = c.post("/api/v1/services/enroll", json=enroll_body(HCH, token=tok)).json()
    c.headers["Authorization"] = f"Bearer {svc['service_token']}"
    return c


def flow_event(
    action_id: str,
    target: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    *,
    flow_id: uuid.UUID | None = None,
    action_request_id: uuid.UUID | None = None,
    seq: int = 1,
    **over: Any,
) -> dict[str, Any]:
    fid = flow_id or uuid.uuid4()
    arid = action_request_id or uuid.uuid4()
    actor = f"flow:{fid}"
    trigger = str(uuid.uuid4())
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "source_app": HCH,
        "source_event_id": str(seq),
        "event_type": "flow.action.requested",
        "entity": {"type": "flow", "id": str(fid)},
        "timestamp_utc": iso(utcnow()),
        "trace_id": str(uuid.uuid4()),
        "correlation_id": str(arid),
        "actor": {"type": "flow", "id": actor},
        "classification": "internal",
        "payload": {
            "action_request_id": str(arid),
            "idempotency_key": str(uuid.uuid4()),
            "action_id": action_id,
            "target": target,
            "parameters": parameters or {},
            "reason": "Flow: test",
            "actor": {"type": "flow", "id": actor},
            "expected_version": None,
            "evidence_ids": [trigger],
            "expires_in_seconds": 900,
            "owner": "test-eigenaar",
            "flow": {"id": str(fid), "label": "Testflow", "version": 1},
            "trigger_event_id": trigger,
            "origin_chain": [actor],
            "risk_claim_genegeerd": True,
        },
        "payload_ref": None,
        **over,
    }


def flow_request_id(ev: dict[str, Any]) -> str:
    from hub.actions.flows import request_id_voor

    return str(request_id_voor(ev["source_app"], uuid.UUID(ev["payload"]["action_request_id"])))


def flow_audit(app: Any) -> list[dict[str, Any]]:
    """Auditregels met actor ``flow`` of over een flowverzoek, oudste eerst."""
    from sqlalchemy import select

    from hub.models import AuditEvent

    with app.state.sessionmaker() as db:
        rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id))
        return [
            {
                "action": a.action,
                "actor": f"{a.actor_type}:{a.actor_id}",
                "details": a.details,
                "target": a.target_id,
            }
            for a in rows
            if a.actor_type == "flow" or a.action.startswith("action.flow_request.")
        ]
