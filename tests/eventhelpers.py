"""Gedeelde hulpfuncties voor dienst-E2E met events (contract §7) en de incidenten-inbox."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from conftest import enroll_body


def service(admin: Any, app_id: str = "home-control-hub") -> dict[str, str]:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body(app_id, token=r.json()["enrollment_token"]),
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['service_token']}"}


def event(
    source: str,
    event_type: str,
    entity: tuple[str, str],
    payload: dict[str, Any] | None = None,
    *,
    at: datetime | None = None,
    event_id: str | None = None,
    source_event_id: str | None = None,
    classification: str = "internal",
    correlation_id: str | None = None,
) -> dict[str, Any]:
    eid = event_id or str(uuid.uuid4())
    return {
        "schema_version": "1.0",
        "event_id": eid,
        "source_app": source,
        "source_event_id": source_event_id or eid,
        "event_type": event_type,
        "entity": {"type": entity[0], "id": entity[1]},
        "timestamp_utc": (at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "trace_id": str(uuid.uuid4()),
        "correlation_id": correlation_id,
        "actor": {"type": "system", "id": source},
        "classification": classification,
        "payload": payload or {},
    }


def post(client: Any, headers: dict[str, str], ev: dict[str, Any]) -> None:
    r = client.post("/api/v1/events/inbox", json=ev, headers=headers)
    assert r.status_code in (200, 202), r.text


def active(admin: Any, **params: Any) -> list[dict[str, Any]]:
    r = admin.get("/api/v1/incidents", params={"limit": 200, **params})
    assert r.status_code == 200, r.text
    return list(r.json()["items"])
