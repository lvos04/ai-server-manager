"""Tijdreeksen in de eigen PostgreSQL (B09-003): begrensd, genormaliseerd, retentie per reeks, ruw → 5 min → 1 uur.

- Een reeks = onderwerp (``nas``, ``pool``, ``app``, ``gpu``, ``interface``, ``monitor``) × metriek × bron. Dezelfde
  metriek uit twee bronnen (TrueNAS en Beszel) blijft twee reeksen; de weergave kiest per metriek een verse bron.
- Eenheden zijn genormaliseerd: ``%``, ``B``, ``B/s``, ``°C``, ``ms``, ``W``, ``status`` (1 gezond, 0.5 verminderd,
  0 down). Ontbrekende waarden worden **niet** opgeslagen (geen 0 voor onbekend).
- Grenzen: maximaal ``metrics_max_series`` reeksen; waarden moeten eindig zijn; tijden met tijdzone en niet meer dan
  5 min in de toekomst. Wat buiten de grenzen valt wordt geweigerd en geteld, nooit stil opgeslagen.
- Aggregatie met ``date_bin`` (PostgreSQL ≥ 14), idempotent (``ON CONFLICT … DO UPDATE``). Geen extensie nodig, zodat de
  alles-in-één image de standaard PostgreSQL 16 houdt.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import MetricRollup, MetricSample, MetricSeries
from hub.timeutil import iso, utcnow

EENHEDEN: tuple[str, ...] = ("%", "B", "B/s", "°C", "ms", "W", "status", "aantal", "Mb/s", "dagen")
ONDERWERPEN: tuple[str, ...] = ("nas", "pool", "app", "gpu", "interface", "monitor")
ORIGIN = "2000-01-01 00:00:00+00"
DAY = 24 * 3600
INSERT_BATCH = 5000  # 3 parameters per meting; ruim onder de PostgreSQL-grens van 65 535 parameters

# Retentie-uitzonderingen per metriek (ruw, 5 min, 1 uur) in seconden; anders de instellingen.
RETENTIE: dict[str, tuple[int, int, int]] = {
    "app.status": (7 * DAY, 90 * DAY, 400 * DAY),
    "app.latentie": (2 * DAY, 30 * DAY, 180 * DAY),
}


@dataclass(frozen=True)
class Sample:
    onderwerp_type: str
    onderwerp_id: str
    metriek: str
    eenheid: str
    bron: str
    ts: datetime
    waarde: float
    labels: dict[str, Any] = field(default_factory=dict)

    @property
    def sleutel(self) -> str:
        return f"{self.onderwerp_type}|{self.onderwerp_id}|{self.metriek}|{self.bron}"[:255]


@dataclass
class RecordResult:
    opgeslagen: int = 0
    afgewezen: int = 0
    nieuwe_reeksen: int = 0
    redenen: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.afgewezen += 1
        self.redenen[reason] = self.redenen.get(reason, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "opgeslagen": self.opgeslagen,
            "afgewezen": self.afgewezen,
            "nieuwe_reeksen": self.nieuwe_reeksen,
            "redenen": self.redenen,
        }


def _retention(metriek: str, settings: Settings) -> tuple[int, int, int]:
    return RETENTIE.get(
        metriek,
        (
            settings.metrics_raw_retention_seconds,
            settings.metrics_5m_retention_seconds,
            settings.metrics_1h_retention_seconds,
        ),
    )


def record(db: Session, settings: Settings, samples: Iterable[Sample], *, now: datetime | None = None) -> RecordResult:
    now = now or utcnow()
    res = RecordResult()
    wanted = list(samples)
    if not wanted:
        return res
    keys = {s.sleutel for s in wanted}
    existing = {r.sleutel: r for r in db.scalars(select(MetricSeries).where(MetricSeries.sleutel.in_(keys)))}
    count = db.scalar(select(func.count()).select_from(MetricSeries)) or 0
    rows: list[dict[str, Any]] = []
    for s in wanted:
        if s.onderwerp_type not in ONDERWERPEN or s.eenheid not in EENHEDEN:
            res.reject("onbekend_onderwerp_of_eenheid")
            continue
        if not isinstance(s.waarde, int | float) or isinstance(s.waarde, bool) or not math.isfinite(s.waarde):
            res.reject("geen_eindige_waarde")
            continue
        if s.ts.tzinfo is None or s.ts > now + timedelta(minutes=5):
            res.reject("ongeldige_tijd")
            continue
        series = existing.get(s.sleutel)
        if series is None:
            if count >= settings.metrics_max_series:
                res.reject("max_reeksen_bereikt")
                continue
            ruw, vijf, uur = _retention(s.metriek, settings)
            series = MetricSeries(
                sleutel=s.sleutel,
                onderwerp_type=s.onderwerp_type,
                onderwerp_id=s.onderwerp_id[:128],
                metriek=s.metriek,
                eenheid=s.eenheid,
                bron=s.bron[:96],
                labels=s.labels,
                retentie_ruw_s=ruw,
                retentie_5m_s=vijf,
                retentie_1u_s=uur,
                aangemaakt_op=now,
            )
            db.add(series)
            db.flush()
            existing[s.sleutel] = series
            count += 1
            res.nieuwe_reeksen += 1
        elif s.labels and series.labels != s.labels:
            series.labels = s.labels
        if series.laatste_op is None or s.ts >= series.laatste_op:
            series.laatste_op, series.laatste_waarde = s.ts, float(s.waarde)
        rows.append({"series_id": series.id, "ts": s.ts, "waarde": float(s.waarde)})
    for start in range(0, len(rows), INSERT_BATCH):
        stmt = (
            insert(MetricSample)
            .values(rows[start : start + INSERT_BATCH])
            .on_conflict_do_nothing(index_elements=["series_id", "ts"])
            .returning(MetricSample.series_id)
        )
        res.opgeslagen += len(db.execute(stmt).all())
    db.flush()
    return res


_ROLLUP_5M = text(
    """
    INSERT INTO metric_rollup (series_id, resolutie, bucket, n, min, max, som, laatste)
    SELECT s.series_id, 300, date_bin('300 seconds', s.ts, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS b,
           count(*), min(s.waarde), max(s.waarde), sum(s.waarde), (array_agg(s.waarde ORDER BY s.ts DESC))[1]
    FROM metric_sample s
    WHERE s.ts >= date_bin('300 seconds', CAST(:since AS timestamptz), TIMESTAMPTZ '2000-01-01 00:00:00+00')
    GROUP BY s.series_id, b
    ON CONFLICT (series_id, resolutie, bucket) DO UPDATE
      SET n = EXCLUDED.n, min = EXCLUDED.min, max = EXCLUDED.max, som = EXCLUDED.som, laatste = EXCLUDED.laatste
    """
)
_ROLLUP_1H = text(
    """
    INSERT INTO metric_rollup (series_id, resolutie, bucket, n, min, max, som, laatste)
    SELECT r.series_id, 3600, date_bin('3600 seconds', r.bucket, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS b,
           sum(r.n), min(r.min), max(r.max), sum(r.som), (array_agg(r.laatste ORDER BY r.bucket DESC))[1]
    FROM metric_rollup r
    WHERE r.resolutie = 300
      AND r.bucket >= date_bin('3600 seconds', CAST(:since AS timestamptz), TIMESTAMPTZ '2000-01-01 00:00:00+00')
    GROUP BY r.series_id, b
    ON CONFLICT (series_id, resolutie, bucket) DO UPDATE
      SET n = EXCLUDED.n, min = EXCLUDED.min, max = EXCLUDED.max, som = EXCLUDED.som, laatste = EXCLUDED.laatste
    """
)


def rollup(db: Session, *, since: datetime) -> dict[str, int]:
    """Herbereken de 5-minuten- en uur-aggregaten vanaf ``since`` (afgerond naar het begin van het blok)."""
    r5 = db.execute(_ROLLUP_5M, {"since": since})
    r1 = db.execute(_ROLLUP_1H, {"since": since})
    db.flush()
    return {"vijf_minuten": int(getattr(r5, "rowcount", 0) or 0), "uur": int(getattr(r1, "rowcount", 0) or 0)}


def prune(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Retentie per reeks: ruwe metingen, 5-minuten- en uuraggregaten; reeksen zonder enige meting binnen de
    uurretentie verdwijnen helemaal."""
    now = now or utcnow()
    p = {"now": now}
    raw = db.execute(
        text(
            "DELETE FROM metric_sample s USING metric_series m WHERE s.series_id = m.id "
            "AND s.ts < CAST(:now AS timestamptz) - make_interval(secs => m.retentie_ruw_s)"
        ),
        p,
    )
    five = db.execute(
        text(
            "DELETE FROM metric_rollup r USING metric_series m WHERE r.series_id = m.id AND r.resolutie = 300 "
            "AND r.bucket < CAST(:now AS timestamptz) - make_interval(secs => m.retentie_5m_s)"
        ),
        p,
    )
    hour = db.execute(
        text(
            "DELETE FROM metric_rollup r USING metric_series m WHERE r.series_id = m.id AND r.resolutie = 3600 "
            "AND r.bucket < CAST(:now AS timestamptz) - make_interval(secs => m.retentie_1u_s)"
        ),
        p,
    )
    series = db.execute(
        text(
            "DELETE FROM metric_series m WHERE (m.laatste_op IS NULL OR m.laatste_op < "
            "CAST(:now AS timestamptz) - make_interval(secs => m.retentie_1u_s)) "
            "AND NOT EXISTS (SELECT 1 FROM metric_sample s WHERE s.series_id = m.id) "
            "AND NOT EXISTS (SELECT 1 FROM metric_rollup r WHERE r.series_id = m.id) "
            "AND NOT EXISTS (SELECT 1 FROM alert_instance a WHERE a.series_id = m.id)"
        ),
        p,
    )
    db.flush()
    return {
        "ruw": int(getattr(raw, "rowcount", 0) or 0),
        "vijf_minuten": int(getattr(five, "rowcount", 0) or 0),
        "uur": int(getattr(hour, "rowcount", 0) or 0),
        "reeksen": int(getattr(series, "rowcount", 0) or 0),
    }


RESOLUTIES = {"ruw": 0, "5m": 300, "1u": 3600}


def choose_resolution(span: timedelta, requested: str) -> str:
    if requested != "auto":
        return requested
    if span <= timedelta(hours=6):
        return "ruw"
    if span <= timedelta(days=7):
        return "5m"
    return "1u"


def query(
    db: Session, series: MetricSeries, *, van: datetime, tot: datetime, resolutie: str, max_punten: int
) -> dict[str, Any]:
    gekozen = choose_resolution(tot - van, resolutie)
    punten: list[dict[str, Any]] = []
    if gekozen == "ruw":
        rows = db.execute(
            select(MetricSample.ts, MetricSample.waarde)
            .where(MetricSample.series_id == series.id, MetricSample.ts >= van, MetricSample.ts <= tot)
            .order_by(MetricSample.ts)
            .limit(max_punten + 1)
        ).all()
        if len(rows) > max_punten and resolutie == "auto":
            return query(db, series, van=van, tot=tot, resolutie="5m", max_punten=max_punten)
        punten = [{"ts": iso(r.ts), "waarde": r.waarde} for r in rows[:max_punten]]
    else:
        res = RESOLUTIES[gekozen]
        rrows = list(
            db.scalars(
                select(MetricRollup)
                .where(
                    MetricRollup.series_id == series.id,
                    MetricRollup.resolutie == res,
                    MetricRollup.bucket >= van,
                    MetricRollup.bucket <= tot,
                )
                .order_by(MetricRollup.bucket)
                .limit(max_punten + 1)
            )
        )
        if len(rrows) > max_punten and resolutie == "auto" and gekozen == "5m":
            return query(db, series, van=van, tot=tot, resolutie="1u", max_punten=max_punten)
        punten = [
            {
                "ts": iso(r.bucket),
                "gemiddelde": r.som / r.n if r.n else None,
                "min": r.min,
                "max": r.max,
                "laatste": r.laatste,
                "n": r.n,
            }
            for r in rrows[:max_punten]
        ]
    return {"resolutie": gekozen, "punten": punten, "afgekapt": len(punten) >= max_punten}


def series_dict(s: MetricSeries, *, stale_seconds: int, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    stale = s.laatste_op is None or (now - s.laatste_op).total_seconds() > stale_seconds
    return {
        "id": s.id,
        "onderwerp_type": s.onderwerp_type,
        "onderwerp_id": s.onderwerp_id,
        "metriek": s.metriek,
        "eenheid": s.eenheid,
        "bron": s.bron,
        "labels": s.labels,
        "laatste_waarde": None if stale else s.laatste_waarde,
        "laatst_bekend": {"waarde": s.laatste_waarde, "observed_at": iso(s.laatste_op)},
        "observed_at": iso(s.laatste_op),
        "status": "unknown" if stale else "ok",
        "verouderd": stale,
        "retentie": {"ruw_s": s.retentie_ruw_s, "vijf_minuten_s": s.retentie_5m_s, "uur_s": s.retentie_1u_s},
    }
