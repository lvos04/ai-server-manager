"""Integratie: tijdreeksen in PostgreSQL (B09-003) — grenzen, aggregatie ruw → 5 min → 1 uur, retentie en API."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from conftest import login_as, make_user

from hub.models import MetricRollup, MetricSample, MetricSeries
from hub.monitoring import timeseries
from hub.monitoring.timeseries import Sample

pytestmark = pytest.mark.integration

T0 = datetime(2026, 11, 9, 10, 0, tzinfo=UTC)


def S(v: float, ts: datetime, oid: str = "nas", metriek: str = "cpu.gebruik", bron: str = "test") -> Sample:
    return Sample("nas" if oid == "nas" else "app", oid, metriek, "%", bron, ts, v)


def test_grenzen_en_dedupe(app: Any, settings: Any) -> None:
    settings.metrics_max_series = 3
    with app.state.sessionmaker() as db:
        res = timeseries.record(
            db,
            settings,
            [
                S(10, T0),
                S(10, T0),  # dubbel → één meting
                S(math.nan, T0 + timedelta(seconds=1)),
                S(math.inf, T0 + timedelta(seconds=2)),
                Sample("nas", "nas", "cpu.gebruik", "%", "test", T0.replace(tzinfo=None), 1),
                S(1, T0 + timedelta(hours=1), metriek="x.toekomst"),
                Sample("raar", "x", "a.b", "%", "test", T0, 1),
                Sample("nas", "nas", "a.b", "furlong", "test", T0, 1),
                S(1, T0, oid="a1"),
                S(1, T0, oid="a2"),
                S(1, T0, oid="a3"),  # 4e reeks → geweigerd (max 3)
            ],
            now=T0,
        )
        db.commit()
        assert res.opgeslagen == 3 and res.nieuwe_reeksen == 3
        assert res.redenen == {
            "geen_eindige_waarde": 2,
            "ongeldige_tijd": 2,
            "onbekend_onderwerp_of_eenheid": 2,
            "max_reeksen_bereikt": 1,
        }
        assert db.query(MetricSeries).count() == 3


def test_aggregatie_en_retentie(app: Any, settings: Any) -> None:
    with app.state.sessionmaker() as db:
        samples = [S(float(i % 10), T0 + timedelta(seconds=30 * i)) for i in range(240)]  # 2 uur, elke 30 s
        timeseries.record(db, settings, samples, now=T0 + timedelta(hours=2))
        out = timeseries.rollup(db, since=T0)
        db.commit()
        assert out["vijf_minuten"] == 24 and out["uur"] == 2
        five = db.query(MetricRollup).filter_by(resolutie=300).order_by(MetricRollup.bucket).all()
        assert len(five) == 24 and five[0].n == 10 and five[0].min == 0 and five[0].max == 9
        assert five[0].som == 45 and five[0].laatste == 9
        hour = db.query(MetricRollup).filter_by(resolutie=3600).order_by(MetricRollup.bucket).all()
        assert [h.n for h in hour] == [120, 120] and hour[0].som == 12 * 45
        # Idempotent: opnieuw aggregeren verandert niets.
        timeseries.rollup(db, since=T0)
        db.commit()
        assert db.query(MetricRollup).filter_by(resolutie=300).count() == 24

        # Retentie per reeks: ruw 48 u → na 3 dagen zijn de ruwe metingen weg, de aggregaten blijven.
        res = timeseries.prune(db, now=T0 + timedelta(days=3))
        db.commit()
        assert res["ruw"] == 240 and db.query(MetricSample).count() == 0
        assert db.query(MetricRollup).count() == 26
        # Na 31 dagen ook de 5-minutenaggregaten; na 401 dagen alles inclusief de reeks.
        timeseries.prune(db, now=T0 + timedelta(days=31))
        assert db.query(MetricRollup).filter_by(resolutie=300).count() == 0
        res = timeseries.prune(db, now=T0 + timedelta(days=401))
        db.commit()
        assert res["reeksen"] == 1 and db.query(MetricSeries).count() == 0


def test_api_reeksen_en_punten(admin: Any, app: Any, settings: Any) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    with app.state.sessionmaker() as db:
        timeseries.record(db, settings, [S(float(i), now - timedelta(minutes=60 - i)) for i in range(60)], now=now)
        timeseries.record(db, settings, [S(1.0, now - timedelta(hours=2), metriek="cpu.oud")], now=now)
        timeseries.rollup(db, since=now - timedelta(hours=3))
        db.commit()
    make_user(admin, "kijker", "viewer")
    viewer = login_as(app, "kijker")
    r = viewer.get("/api/v1/metrics/series", params={"onderwerp_type": "nas"})
    assert r.status_code == 200, r.text
    items = {s["metriek"]: s for s in r.json()["items"]}
    assert items["cpu.gebruik"]["status"] == "ok" and items["cpu.gebruik"]["laatste_waarde"] == 59
    # Verouderd: geen waarde (unknown), wel de laatst bekende met tijd.
    old = items["cpu.oud"]
    assert old["status"] == "unknown" and old["laatste_waarde"] is None and old["laatst_bekend"]["waarde"] == 1
    sid = items["cpu.gebruik"]["id"]
    r = viewer.get("/api/v1/metrics/query", params={"series": sid})
    body = r.json()
    assert r.status_code == 200 and body["resolutie"] == "ruw" and len(body["punten"]) == 60
    r = viewer.get("/api/v1/metrics/query", params={"series": sid, "resolutie": "5m"})
    assert r.json()["resolutie"] == "5m" and all("gemiddelde" in p for p in r.json()["punten"])
    van = (now - timedelta(days=10)).isoformat()
    r = viewer.get("/api/v1/metrics/query", params={"series": sid, "van": van})
    assert r.json()["resolutie"] == "1u"
    assert viewer.get("/api/v1/metrics/query", params={"series": 999999}).status_code == 404
    bad = viewer.get("/api/v1/metrics/query", params={"series": sid, "van": now.isoformat(), "tot": van})
    assert bad.status_code == 422
    make_user(admin, "kleintje", "kind")
    assert login_as(app, "kleintje").get("/api/v1/metrics/series").status_code == 403
