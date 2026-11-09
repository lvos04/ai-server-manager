"""Tijden altijd ISO-8601 UTC met ``Z`` (contract §5)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S") + (
        f".{dt.microsecond // 1000:03d}Z" if dt.microsecond else "Z"
    )


def age_seconds(dt: datetime | None, now: datetime | None = None) -> float | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return ((now or utcnow()) - dt).total_seconds()


UtcDateTime = Annotated[datetime, PlainSerializer(lambda d: iso(d), return_type=str)]
