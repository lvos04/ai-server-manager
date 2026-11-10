"""Dienst-E2E: alerts en meldingen via Gotify (B09-003, notification.send R0) tegen een fake Gotify (Sim-getest).

Acceptatie B09-003: een Prometheus-achtige testbelasting (veel reeksen, veel metingen, waarden rond de drempel)
veroorzaakt geen meldingenstorm: dedupe per overgang, hysterese, rate-limit per kanaal met één samenvatting.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from conftest import idem, login_as, make_user
from fakes.fake_gotify import FakeGotify
from fakes.fake_truenas import FakeTrueNAS
from nashelpers import connect, refresh
from sqlalchemy import select

from hub.models import AlertInstance, Notification, OutboxEvent
from hub.monitoring import alerts, timeseries
from hub.monitoring.timeseries import Sample
from hub.notify.dispatch import dispatch

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
TOKEN = "AppTokenHub123"


@pytest.fixture
def gotify() -> Any:
    g = FakeGotify(tokens={TOKEN}).start()
    yield g
    g.stop()


def _channel(admin: Any, gotify: FakeGotify, **kw: Any) -> dict[str, Any]:
    body = {"naam": "Telefoon", "basis_url": gotify.url, "token": TOKEN, **kw}
    r = admin.post("/api/v1/notifications/channels", json=body, headers=idem())
    assert r.status_code == 201, r.text
    return dict(r.json())


def test_kanaal_beheren_testmelding_echt_en_token_nooit_terug(admin: Any, app: Any, gotify: FakeGotify) -> None:
    ch = _channel(admin, gotify)
    assert ch["token"]["ingesteld"] and ch["token"]["laatste4"] == "b123"
    listing = admin.get("/api/v1/notifications/channels").text
    assert TOKEN not in listing and TOKEN not in str(ch)

    r = admin.post(f"/api/v1/notifications/channels/{ch['id']}/test", headers=idem())
    assert r.status_code == 200 and r.json()["verzonden"] is True and r.json()["gotify_versie"] == "3.1.1"
    assert gotify.messages[-1]["title"] == "Testmelding van de Hub" and gotify.messages[-1]["priority"] == 2

    # Fout token → eerlijk 'niet verzonden' met reden; nooit gesimuleerd succes.
    gotify.tokens = {"AnderToken999"}
    r = admin.post(f"/api/v1/notifications/channels/{ch['id']}/test", headers=idem())
    assert r.json()["verzonden"] is False and r.json()["reden"] == "token_geweigerd"
    assert r.json()["kanaal"]["status"]["laatste_status"] == "fout"
    r = admin.patch(f"/api/v1/notifications/channels/{ch['id']}", json={"token": "AnderToken999"}, headers=idem())
    assert r.status_code == 200 and r.json()["status"]["laatste_reden"] is None
    assert admin.post(f"/api/v1/notifications/channels/{ch['id']}/test", headers=idem()).json()["verzonden"]

    # Adresregels: geen inloggegevens in de URL, geen link-local.
    bad = admin.post(
        "/api/v1/notifications/channels",
        json={"naam": "x", "basis_url": "http://169.254.169.254", "token": TOKEN},
        headers=idem(),
    )
    assert bad.status_code == 422 and bad.json()["details"]["reden"] == "adres_niet_toegestaan"
    audit = admin.get("/api/v1/audit").json()["items"]
    assert {"notification.channel.created", "notification.channel.tested"} <= {a["actie"] for a in audit}
    assert TOKEN not in str(audit)


def test_notification_send_r0_via_wachtrij_en_rechten(admin: Any, app: Any, settings: Any, gotify: FakeGotify) -> None:
    make_user(admin, "operator1", "operator")
    make_user(admin, "kijker", "viewer")
    op, viewer = login_as(app, "operator1"), login_as(app, "kijker")
    body = {"titel": "Hallo", "bericht": "Testbericht", "ernst": "waarschuwing"}
    r = op.post("/api/v1/notifications", json=body, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "geen_kanaal"  # zonder kanaal niets verstuurd
    _channel(admin, gotify, min_ernst="waarschuwing")
    key = idem()
    r = op.post("/api/v1/notifications", json=body, headers=key)
    assert r.status_code == 202 and r.json()["action_id"] == "notification.send" and r.json()["risico"] == "R0"
    again = op.post("/api/v1/notifications", json=body, headers=key)
    assert again.json() == r.json() and again.headers.get("Idempotent-Replay") == "true"
    info = op.post("/api/v1/notifications", json={**body, "ernst": "info"}, headers=idem())
    assert info.status_code == 409  # onder de minimale ernst van het kanaal
    assert viewer.post("/api/v1/notifications", json=body, headers=idem()).status_code == 403
    assert op.post("/api/v1/notifications", json={**body, "titel": "x" * 121}, headers=idem()).status_code == 422
    with app.state.sessionmaker() as db:
        stats = dispatch(db, settings, app.state.vault())
        db.commit()
    assert stats["verzonden"] == 1 and len(gotify.messages) == 1 and gotify.messages[0]["priority"] == 5
    sent = op.get("/api/v1/notifications", params={"status": "verzonden"}).json()["items"]
    assert len(sent) == 1 and sent[0]["bron"] == "handmatig"


def test_prometheus_achtige_testload_geeft_geen_meldingenstorm(
    admin: Any, app: Any, settings: Any, gotify: FakeGotify
) -> None:
    """200 reeksen met elk 300 metingen (elke 10 s): eerst flapperend rond de drempel (debounce → geen enkel alert),
    dan aanhoudend erboven (precies één 'actief'-melding per alert), dan tussen drempel en herstelgrens (hysterese →
    geen hersteldmelding). Het kanaal verstuurt hooguit 10 berichten per kwartier en daarna één samenvatting."""
    ch = _channel(admin, gotify, max_per_venster=10, venster_s=900)
    rule = admin.post(
        "/api/v1/alerts/rules",
        json={
            "naam": "Test: belasting",
            "metriek": "test.belasting",
            "onderwerp_type": "app",
            "operator": "ge",
            "drempel": 85,
            "herstel_drempel": 70,
            "duur_s": 60,
            "herstel_duur_s": 120,
            "ernst": "waarschuwing",
            "kanalen": [ch["id"]],
        },
        headers=idem(),
    )
    assert rule.status_code == 201, rule.text
    rng = random.Random(42)
    now = datetime.now(UTC).replace(microsecond=0)
    t_a, t_b = now - timedelta(seconds=2400), now - timedelta(seconds=1190)

    def load(t: datetime, n: int, value: Any) -> list[Sample]:
        return [
            Sample("app", f"app-{i:03d}", "test.belasting", "%", "test", t + timedelta(seconds=10 * k), value(k))
            for i in range(200)
            for k in range(n)
        ]

    with app.state.sessionmaker() as db:
        # A: flapperen 84 ↔ 92 → de duur wordt steeds onderbroken.
        assert (
            timeseries.record(db, settings, load(t_a, 120, lambda k: 92.0 if k % 2 else 84.0), now=now).opgeslagen
            == 24_000
        )
        db.commit()
        alerts.evaluate(db, settings, now=t_a + timedelta(seconds=1190))
        db.commit()
        assert not db.scalars(select(AlertInstance).where(AlertInstance.toestand == "firing")).all()
        # B: aanhoudend boven de drempel met ruis.
        timeseries.record(db, settings, load(t_b, 120, lambda k: 86 + rng.random() * 6), now=now)
        db.commit()
        for _ in range(3):  # de worker evalueert elke 30 s: geen dubbele overgangen of meldingen
            alerts.evaluate(db, settings, now=now)
            db.commit()
        assert len(db.scalars(select(AlertInstance).where(AlertInstance.toestand == "firing")).all()) == 200
        # C: tussen herstelgrens en drempel → blijft actief (hysterese), geen hersteldmelding.
        later = now + timedelta(seconds=600)
        timeseries.record(
            db, settings, load(now + timedelta(seconds=10), 60, lambda k: 75 + rng.random() * 9), now=later
        )
        db.commit()
        alerts.evaluate(db, settings, now=later)
        db.commit()
        made = db.scalars(select(Notification).where(Notification.bron == "alert")).all()
        assert len(made) == 200 and {n.soort for n in made} == {"actief"}
        for _ in range(5):
            dispatch(db, settings, app.state.vault(), now=later)
            db.commit()
        assert len(gotify.messages) == 10
        # Kwartier later: één samenvatting; de rest blijft onderdrukt (nooit 190 berichten achter elkaar).
        dispatch(db, settings, app.state.vault(), now=later + timedelta(minutes=16))
        db.commit()
    assert len(gotify.messages) == 11
    assert gotify.messages[-1]["title"] == "190 meldingen onderdrukt"
    counts = admin.get("/api/v1/notifications", params={"status": "onderdrukt", "limit": 200}).json()["items"]
    assert len(counts) == 190 and {n["reden"] for n in counts} == {"rate_limit"}


def test_keten_truenas_naar_gotify_app_down_en_dempen(
    admin: Any,
    app: Any,
    settings: Any,
    fake_nas: FakeTrueNAS,
    worker_once: Any,
    periodic_run: Any,
    gotify: FakeGotify,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake TrueNAS → inventaris → catalogus → gezondheid → reeks app.status → standaardregel 'App onbereikbaar' →
    Gotify. Pool-metingen komen als reeks binnen; dempen onderdrukt de volgende melding."""
    # De test springt ~20 min vooruit; de inventaris moet vers blijven. Contract 1.3 §6.2 begrenst de geldigheid op de
    # standaard max_age (900 s), dus alleen in deze test die grens ruimer.
    from hub import config as hub_config

    monkeypatch.setattr(hub_config, "DEFAULT_MAX_AGE_SECONDS", 7200)
    settings.inventory_ttl_seconds = 7200
    _channel(admin, gotify)
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    series = admin.get("/api/v1/metrics/series", params={"onderwerp_type": "pool"}).json()["items"]
    assert {s["metriek"] for s in series} == {"pool.gebruik", "pool.vrij", "pool.gezond"}
    assert next(s for s in series if s["metriek"] == "pool.gebruik")["laatste_waarde"] == 25.0

    t0 = datetime.now(UTC).replace(microsecond=0)
    periodic_run("gezondheid_vastleggen", "alerts_evalueren", now=t0)
    periodic_run("gezondheid_vastleggen", "alerts_evalueren", "meldingen_versturen", now=t0 + timedelta(seconds=310))
    titles = [m["title"] for m in gotify.messages]
    assert titles == ["App onbereikbaar"], titles  # alleen de gestopte Jellyfin; MediaGuard is 'unknown', niet down
    assert gotify.messages[0]["priority"] == 8 and "app " in gotify.messages[0]["message"]
    rules = {r["standaard_sleutel"]: r for r in admin.get("/api/v1/alerts/rules").json()["items"]}
    assert {"pool-vol", "pool-ongezond", "app-down", "cpu-hoog"} <= set(rules)
    firing = admin.get("/api/v1/alerts", params={"toestand": "firing"}).json()["items"]
    assert len(firing) == 1 and firing[0]["regel"]["naam"] == "App onbereikbaar"

    # Dempen (operator): het alert blijft zichtbaar, een herhaling wordt 'onderdrukt' i.p.v. verstuurd.
    aid = firing[0]["id"]
    r = admin.post(f"/api/v1/alerts/{aid}/snooze", json={"minuten": 60, "reden": "onderhoud"}, headers=idem())
    assert r.status_code == 200 and r.json()["gedempt_tot"]
    rid = rules["app-down"]["id"]
    r = admin.patch(f"/api/v1/alerts/rules/{rid}", json={"herhaal_na_s": 900}, headers=idem())
    assert r.status_code == 200 and r.json()["herhaal_na_s"] == 900
    periodic_run("gezondheid_vastleggen", "alerts_evalueren", "meldingen_versturen", now=t0 + timedelta(seconds=1300))
    assert len(gotify.messages) == 1
    suppressed = admin.get("/api/v1/notifications", params={"status": "onderdrukt"}).json()["items"]
    assert [n["reden"] for n in suppressed] == ["gedempt"] and suppressed[0]["soort"] == "herhaling"

    # Geen verse meting meer (bron stil): het alert blijft actief en wordt nooit door ontbrekende data 'hersteld'.
    periodic_run("alerts_evalueren", "meldingen_versturen", now=t0 + timedelta(seconds=3000))
    still = admin.get("/api/v1/alerts", params={"toestand": "firing"}).json()["items"]
    assert len(still) == 1 and still[0]["gegevens_verouderd"] is True
    assert len(gotify.messages) == 1

    # Hysterese-regel moet kloppen; een If-Match met een oude versie wordt geweigerd.
    bad = admin.patch(f"/api/v1/alerts/rules/{rid}", json={"herstel_drempel": 0.1}, headers=idem())
    assert bad.status_code == 422
    stale = admin.patch(f"/api/v1/alerts/rules/{rid}", json={"naam": "x"}, headers={**idem(), "If-Match": '"1"'})
    assert stale.status_code == 412
    assert fake_nas.mutations == []


def test_gotify_storingen_herhalen_dead_letter_en_token_fail_closed(
    admin: Any, app: Any, settings: Any, gotify: FakeGotify
) -> None:
    ch = _channel(admin, gotify, stille_uren=None)
    r = admin.post("/api/v1/notifications", json={"titel": "A", "bericht": "B", "ernst": "kritiek"}, headers=idem())
    assert r.status_code == 202
    now = datetime.now(UTC) + timedelta(seconds=1)  # ná het aanmaken, dus de melding is aan de beurt
    gotify.force_status = 503
    with app.state.sessionmaker() as db:
        t = now
        for _ in range(settings.notify_max_attempts):
            dispatch(db, settings, app.state.vault(), now=t)
            db.commit()
            t += timedelta(hours=2)  # ruim na elke backoff
        n = db.scalars(select(Notification).where(Notification.bron == "handmatig")).one()
        assert n.status == "mislukt" and n.pogingen == settings.notify_max_attempts and n.reden == "http_503"
        assert db.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "notification.delivery.failed")).first()
    assert gotify.messages == []

    # Token ingetrokken in Gotify → kanaal 'fout', geen herhaalde pogingen; na een nieuw token gaat het weer.
    gotify.force_status = None
    gotify.tokens = set()
    admin.post("/api/v1/notifications", json={"titel": "C", "bericht": "D", "ernst": "kritiek"}, headers=idem())
    with app.state.sessionmaker() as db:
        dispatch(db, settings, app.state.vault())
        db.commit()
        before = len(gotify.requests)
        dispatch(db, settings, app.state.vault())
        db.commit()
        assert len(gotify.requests) == before, "geen nieuwe pogingen zolang het token geweigerd is"
    chan = admin.get("/api/v1/notifications/channels").json()["items"][0]
    assert chan["status"]["laatste_reden"] == "token_geweigerd" and "vervang" in chan["status"]["melding"]
    gotify.tokens = {"NieuwToken12345"}
    admin.patch(f"/api/v1/notifications/channels/{ch['id']}", json={"token": "NieuwToken12345"}, headers=idem())
    with app.state.sessionmaker() as db:
        dispatch(db, settings, app.state.vault())
        db.commit()
    assert [m["title"] for m in gotify.messages] == ["C"]


def test_stille_uren_alleen_kritiek_direct(admin: Any, app: Any, settings: Any, gotify: FakeGotify) -> None:
    now = datetime.now(UTC) + timedelta(seconds=5)
    van = (now - timedelta(hours=1)).strftime("%H:%M")
    tot = (now + timedelta(hours=1)).strftime("%H:%M")
    _channel(admin, gotify, stille_uren={"van": van, "tot": tot, "tijdzone": "UTC"})
    admin.post("/api/v1/notifications", json={"titel": "Info", "bericht": "x", "ernst": "info"}, headers=idem())
    admin.post("/api/v1/notifications", json={"titel": "Kritiek", "bericht": "y", "ernst": "kritiek"}, headers=idem())
    with app.state.sessionmaker() as db:
        stats = dispatch(db, settings, app.state.vault(), now=now)
        db.commit()
        assert stats["verzonden"] == 1 and stats["uitgesteld"] == 1
        assert [m["title"] for m in gotify.messages] == ["Kritiek"]
        dispatch(db, settings, app.state.vault(), now=now + timedelta(hours=1, minutes=2))
        db.commit()
    assert [m["title"] for m in gotify.messages] == ["Kritiek", "Info"]
    bad = admin.post(
        "/api/v1/notifications/channels",
        json={
            "naam": "x",
            "basis_url": gotify.url,
            "token": TOKEN,
            "stille_uren": {"van": "22:00", "tot": "07:00", "tijdzone": "Mars/Olympus"},
        },
        headers=idem(),
    )
    assert bad.status_code == 422
    assert uuid.UUID(admin.get("/api/v1/notifications/channels").json()["items"][0]["id"])
