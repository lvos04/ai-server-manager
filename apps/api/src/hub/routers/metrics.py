"""Tijdreeksen lezen (B09-003): reeksen met bron, eenheid en veroudering; punten ruw, per 5 min of per uur."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from hub.deps import DB, Cursor, Limit, SettingsDep, Viewer, decode_cursor, encode_cursor
from hub.errors import HubError
from hub.models import MetricSeries
from hub.monitoring.timeseries import query, series_dict
from hub.timeutil import iso, utcnow

router = APIRouter(prefix="/api/v1/metrics", tags=["tijdreeksen"])


@router.get("/series", summary="Reeksen (onderwerp × metriek × bron) met laatste waarde, bron en veroudering")
def list_series(
    db: DB,
    settings: SettingsDep,
    _: Viewer,
    limit: Limit = 100,
    cursor: Cursor = None,
    onderwerp_type: str | None = Query(default=None, max_length=16),
    onderwerp_id: str | None = Query(default=None, max_length=128),
    metriek: str | None = Query(default=None, max_length=64),
    bron: str | None = Query(default=None, max_length=96),
) -> dict[str, Any]:
    after = decode_cursor(cursor) or 0
    q = select(MetricSeries).where(MetricSeries.id > after)
    if onderwerp_type:
        q = q.where(MetricSeries.onderwerp_type == onderwerp_type)
    if onderwerp_id:
        q = q.where(MetricSeries.onderwerp_id == onderwerp_id)
    if metriek:
        q = q.where(MetricSeries.metriek == metriek)
    if bron:
        q = q.where(MetricSeries.bron == bron)
    rows = list(db.scalars(q.order_by(MetricSeries.id).limit(limit + 1)))
    now = utcnow()
    return {
        "items": [series_dict(s, stale_seconds=settings.alert_stale_seconds, now=now) for s in rows[:limit]],
        "next_cursor": encode_cursor(rows[limit - 1].id) if len(rows) > limit else None,
        "observed_at": iso(now),
    }


@router.get("/query", summary="Punten van één reeks (auto: ≤ 6 u ruw, ≤ 7 d per 5 min, anders per uur)")
def query_series(
    db: DB,
    settings: SettingsDep,
    _: Viewer,
    series: int = Query(ge=1, description="Reeks-id uit /api/v1/metrics/series."),
    van: datetime | None = None,
    tot: datetime | None = None,
    resolutie: Literal["auto", "ruw", "5m", "1u"] = "auto",
    max_punten: int = Query(default=500, ge=10, le=2000),
) -> dict[str, Any]:
    s = db.get(MetricSeries, series)
    if s is None:
        raise HubError(404, "not_found", "Reeks niet gevonden.")
    now = utcnow()
    tot = tot or now
    van = van or tot - timedelta(hours=6)
    if van.tzinfo is None or tot.tzinfo is None:
        raise HubError(422, "validation_error", "Tijden moeten een tijdzone hebben (UTC, eindigend op Z).")
    if van >= tot:
        raise HubError(422, "validation_error", "'van' moet vóór 'tot' liggen.")
    if tot - van > timedelta(days=400):
        raise HubError(422, "validation_error", "Hooguit 400 dagen per opvraging.")
    data = query(db, s, van=van, tot=tot, resolutie=resolutie, max_punten=max_punten)
    return {
        "reeks": series_dict(s, stale_seconds=settings.alert_stale_seconds, now=now),
        "van": iso(van),
        "tot": iso(tot),
        **data,
    }
