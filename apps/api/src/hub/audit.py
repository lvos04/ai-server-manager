"""Globaal auditspoor (alle muterende handelingen)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from hub.models import AuditEvent
from hub.redact import redact


def record(
    db: Session,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    details: dict[str, Any] | None = None,
    trace_id: str = "",
) -> AuditEvent:
    ev = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=redact(details or {}),
        trace_id=trace_id,
    )
    db.add(ev)
    return ev
