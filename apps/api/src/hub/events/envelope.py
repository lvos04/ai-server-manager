"""Event-envelope (contract §7), inbox met dedupe en eigen outbox."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hub.models import InboxEvent, OutboxEvent
from hub.redact import redact
from hub.timeutil import iso, utcnow

MAX_PAYLOAD_BYTES = 16 * 1024
APP_ID_PATTERN = r"^[a-z0-9][a-z0-9_.-]{0,63}$"
EVENT_TYPE_PATTERN = r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$"


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["system", "user", "ai", "flow"]
    id: str = Field(min_length=1, max_length=128)


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    id: str = Field(min_length=1, max_length=200)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    event_id: uuid.UUID
    source_app: str = Field(pattern=APP_ID_PATTERN)
    source_event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(max_length=128, pattern=EVENT_TYPE_PATTERN)
    entity: Entity
    timestamp_utc: datetime
    trace_id: uuid.UUID
    correlation_id: uuid.UUID | None = None
    actor: Actor
    classification: Literal["public", "internal", "sensitive"]
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_ref: str | None = Field(default=None, max_length=512)

    @field_validator("timestamp_utc")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp_utc moet een tijdzone hebben (UTC, eindigend op Z)")
        return v

    @field_validator("payload")
    @classmethod
    def _size(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(v, default=str).encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload groter dan {MAX_PAYLOAD_BYTES} bytes; gebruik payload_ref")
        return v


def accept(db: Session, env: EventEnvelope, *, service_id: uuid.UUID | None) -> tuple[str, InboxEvent]:
    """Sla op of herken een duplicaat (op ``event_id`` óf ``(source_app, source_event_id)``)."""
    existing = db.scalars(
        select(InboxEvent).where(
            or_(
                InboxEvent.event_id == env.event_id,
                (InboxEvent.source_app == env.source_app) & (InboxEvent.source_event_id == env.source_event_id),
            )
        )
    ).first()
    if existing is not None:
        return "duplicate", existing
    row = InboxEvent(
        event_id=env.event_id,
        source_app=env.source_app,
        source_event_id=env.source_event_id,
        event_type=env.event_type,
        entity_type=env.entity.type,
        entity_id=env.entity.id,
        timestamp_utc=env.timestamp_utc,
        trace_id=env.trace_id,
        correlation_id=env.correlation_id,
        actor=env.actor.model_dump(),
        classification=env.classification,
        payload=redact(env.payload),
        payload_ref=env.payload_ref,
        received_at=utcnow(),
        received_from_service=service_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # gelijktijdige levering van hetzelfde event
        dup = db.scalars(
            select(InboxEvent).where(
                or_(
                    InboxEvent.event_id == env.event_id,
                    (InboxEvent.source_app == env.source_app) & (InboxEvent.source_event_id == env.source_event_id),
                )
            )
        ).first()
        if dup is None:
            raise
        return "duplicate", dup
    return "accepted", row


def inbox_to_dict(row: InboxEvent, *, show_sensitive: bool) -> dict[str, Any]:
    hidden = row.classification == "sensitive" and not show_sensitive
    return {
        "seq": row.seq,
        "schema_version": "1.0",
        "event_id": str(row.event_id),
        "source_app": row.source_app,
        "source_event_id": row.source_event_id,
        "event_type": row.event_type,
        "entity": {"type": row.entity_type, "id": row.entity_id},
        "timestamp_utc": iso(row.timestamp_utc),
        "trace_id": str(row.trace_id),
        "correlation_id": str(row.correlation_id) if row.correlation_id else None,
        "actor": row.actor,
        "classification": row.classification,
        "payload": None if hidden else row.payload,
        "payload_verborgen": hidden,
        "payload_ref": row.payload_ref,
        "received_at": iso(row.received_at),
    }


def emit(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    *,
    classification: str = "internal",
    trace_id: uuid.UUID | None = None,
) -> OutboxEvent:
    ev = OutboxEvent(
        event_id=uuid.uuid4(),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_utc=utcnow(),
        trace_id=trace_id or uuid.uuid4(),
        classification=classification,
        payload=redact(payload),
    )
    db.add(ev)
    return ev


def outbox_to_envelope(row: OutboxEvent, app_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "event_id": str(row.event_id),
        "source_app": app_id,
        "source_event_id": str(row.seq),
        "event_type": row.event_type,
        "entity": {"type": row.entity_type, "id": row.entity_id},
        "timestamp_utc": iso(row.timestamp_utc),
        "trace_id": str(row.trace_id),
        "correlation_id": None,
        "actor": {"type": "system", "id": app_id},
        "classification": row.classification,
        "payload": row.payload,
        "payload_ref": None,
    }
