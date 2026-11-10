"""Dienst-E2E: log-index en correlatie (B09-004) tegen de echte API (Sim-getest).

Acceptatie: geheimen komen niet in de index (en dus ook niet in een supportbundel of in wat ooit AI-telemetrie
wordt). Getest met de exacte waarde van geheimen uit de vault, door de Hub uitgegeven tokens, JWT's, Bearer, PEM,
``sleutel=waarde``, e-mail en IP-adressen; plus grenzen (grootte, rate-limit, retentie) en koppeling aan incidenten
via ``trace_id``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from conftest import idem, login_as, make_user
from eventhelpers import active, event, post, service
from fakes.fake_gotify import FakeGotify

from hub import logsink

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
GOTIFY_TOKEN = "GotifyGeheimToken42"
JWT = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJsZW9uIiwiYXVkIjoiaHViIn0.c2lnbmF0dXJlLXZhbi1kZS1odWI"
PEM = "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIDummyDummyDummyDummyDummyDummy\n-----END PRIVATE KEY-----"


def _line(msg: str, *, trace: str | None = None, niveau: str = "error", **velden: Any) -> dict[str, Any]:
    return {
        "op": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "niveau": niveau,
        "bericht": msg,
        "logger": "dienst.worker",
        "trace_id": trace,
        "velden": velden,
    }


def _all_log_text(db_url: str) -> str:
    with psycopg.connect(db_url, autocommit=True) as conn:
        rows = conn.execute("SELECT bericht, velden::text, logger FROM log_entry").fetchall()
    return "\n".join(" ".join(str(c) for c in r) for r in rows)


def test_geheimen_niet_in_index_supportbundel_of_zoekresultaat(admin: Any, app: Any, clean_db: str) -> None:
    g = FakeGotify(tokens={GOTIFY_TOKEN}).start()
    try:
        r = admin.post(
            "/api/v1/notifications/channels",
            json={"naam": "Telefoon", "basis_url": g.url, "token": GOTIFY_TOKEN},
            headers=idem(),
        )
        assert r.status_code == 201
    finally:
        g.stop()
    svc = service(admin)
    svc_token = svc["Authorization"].split(" ", 1)[1]
    trace = str(uuid.uuid4())
    lines = [
        _line(f"verbinden met gotify mislukt, key {GOTIFY_TOKEN} geweigerd", trace=trace),
        _line(f"eigen service-token {svc_token} gelekt", trace=trace),
        _line(f"Authorization: Bearer {JWT}"),
        _line(f"sleutel {PEM}"),
        _line("login wachtwoord=Hunter2-Hunter2 vanaf 192.168.10.44 door leon@example.org"),
        _line("callback ?code=abc123def&state=xyz789 publiek 8.8.4.4", niveau="warning"),
        _line(
            "veld met geheim",
            token="t0k3n-in-veld",
            nested={"password": "pw-in-genest", "ip": "10.1.2.3"},
        ),
    ]
    r = admin.post("/api/v1/logs", json={"regels": lines}, headers=svc)
    assert r.status_code == 202 and r.json() == {
        "opgeslagen": 7,
        "geweigerd": 0,
        "bron": "home-control-hub",
    }
    raw = _all_log_text(clean_db)
    forbidden = [
        GOTIFY_TOKEN,
        svc_token,
        JWT,
        "Hunter2-Hunter2",
        "192.168.10.44",
        "leon@example.org",
        "abc123def",
        "xyz789",
        "8.8.4.4",
        "t0k3n-in-veld",
        "pw-in-genest",
        "10.1.2.3",
        "MC4CAQAw",
    ]
    for secret in forbidden:
        assert secret not in raw, f"lek in de index: {secret[:12]}…"
    assert "[ip-privé]" in raw and "[ip-publiek]" in raw and "[e-mail]" in raw and "[pem]" in raw
    # Zoeken (operator) geeft alleen geschoonde tekst; een kijker mag de logs niet zien.
    make_user(admin, "op-user", "operator")
    make_user(admin, "kijk", "viewer")
    op, viewer = login_as(app, "op-user"), login_as(app, "kijk")
    assert viewer.get("/api/v1/logs").status_code == 403
    found = op.get("/api/v1/logs", params={"trace_id": trace}).json()
    assert len(found["items"]) == 2 and found["geschoond"] is True
    assert GOTIFY_TOKEN not in str(found) and svc_token not in str(found)
    assert op.get("/api/v1/logs", params={"q": "gotify"}).json()["items"][0]["bron"] == "home-control-hub"

    # Incident met dezelfde trace_id → supportbundel met de logregels, zonder geheimen.
    ev = event(
        "home-control-hub",
        "automation.process.crashed",
        ("app", "n8"),
        {"naam": f"x {GOTIFY_TOKEN}"},
    )
    ev["trace_id"] = trace
    post(admin, svc, ev)
    from hub.monitoring import periodic

    periodic.run_due(
        app.state.sessionmaker,
        app.state.settings,
        app.state.vault(),
        app.state.keyring(),
        force=True,
        only={"incidenten_bijwerken"},
    )
    inc = active(admin)[0]
    bundle = op.get(f"/api/v1/incidents/{inc['id']}/supportbundel")
    assert bundle.status_code == 200
    assert bundle.headers["Content-Disposition"].startswith("attachment;")
    text = bundle.text
    for secret in forbidden:
        assert secret not in text, f"lek in de supportbundel: {secret[:12]}…"
    data = bundle.json()
    assert len(data["logregels"]) >= 2 and data["incident"]["id"] == inc["id"]
    assert viewer.get(f"/api/v1/incidents/{inc['id']}/supportbundel").status_code == 403
    logs_for_incident = op.get("/api/v1/logs", params={"incident_id": inc["id"]}).json()["items"]
    assert {r["trace_id"] for r in logs_for_incident} >= {trace}


def test_grenzen_rate_limit_en_retentie(admin: Any, app: Any, settings: Any, clean_db: str) -> None:
    svc = service(admin)
    big = _line("x" * 8000, **{f"veld{i}": "v" * 400 for i in range(20)})  # velden > 4 KiB na schoning
    r = admin.post("/api/v1/logs", json={"regels": [big]}, headers=svc)
    assert r.status_code == 202
    item = admin.get("/api/v1/logs").json()["items"][0]
    # Contract 1.3 §6.1 (K4): opslag hooguit 2000 tekens, zichtbaar gemarkeerd als ingekort; invoer > 8000 → 422.
    assert len(item["bericht"]) == 2000 and item["bericht"].endswith("[ingekort]") and item["bericht_ingekort"] is True
    assert item["velden_ingekort"] is True and len(str(item["velden"])) < 4200
    assert admin.post("/api/v1/logs", json={"regels": [_line("x" * 8001)]}, headers=svc).status_code == 422
    # RV11: trace_id is een UUID en op een tijd met tijdzone.
    bad_trace = {**_line("trace"), "trace_id": "geen-uuid"}
    assert admin.post("/api/v1/logs", json={"regels": [bad_trace]}, headers=svc).status_code == 422
    assert admin.post("/api/v1/logs", json={"regels": []}, headers=svc).status_code == 422
    assert admin.post("/api/v1/logs", json={"regels": [_line("y")] * 201}, headers=svc).status_code == 422
    # Meer dan 1 MiB → 413 vóór validatie (contract §5).
    assert admin.post("/api/v1/logs", json={"regels": [big] * 100}, headers=svc).status_code == 413
    naive = {**_line("zonder tijdzone"), "op": "2026-11-09T12:00:00"}
    assert admin.post("/api/v1/logs", json={"regels": [naive]}, headers=svc).status_code == 422
    # Een gebruikerssessie kan geen logregels insturen (alleen diensten).
    assert admin.post("/api/v1/logs", json={"regels": [_line("x")]}).status_code == 401
    # Rate-limit per dienst per minuut.
    app.state.settings.log_ingest_max_per_minute = 10
    try:
        r = admin.post(
            "/api/v1/logs",
            json={"regels": [_line(f"r{i}") for i in range(20)]},
            headers=svc,
        )
        assert r.status_code == 202 and r.json()["opgeslagen"] == 9 and r.json()["geweigerd"] == 11
        r = admin.post("/api/v1/logs", json={"regels": [_line("nog één")]}, headers=svc)
        assert r.status_code == 429 and r.headers["Retry-After"] == "60"
    finally:
        app.state.settings.log_ingest_max_per_minute = 1000
    # Retentie en maximum aantal regels.
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE log_entry SET op = op - interval '30 days' WHERE bericht = 'r0'")
    with app.state.sessionmaker() as db:
        res = logsink.prune(db, settings.log_retention_seconds, 5)
        db.commit()
    assert res["verouderd"] == 1 and res["boven_maximum"] >= 1
    assert len(admin.get("/api/v1/logs").json()["items"]) == 5
    bronnen = {b["bron"]: b for b in admin.get("/api/v1/logs/bronnen").json()["bronnen"]}
    assert bronnen["TrueNAS-containerlogs"]["status"] == "capability_unavailable"


def test_eigen_hub_logs_met_trace_id_en_geschoond(app: Any, client: Any, clean_db: str) -> None:
    handler = next(h for h in logging.getLogger("hub").handlers if isinstance(h, logsink.DbLogHandler))
    trace = str(uuid.uuid4())
    token = logsink.current_trace.set(trace)
    try:
        logging.getLogger("hub.test").warning("verbinding faalt met api_key=%s naar %s", "Zeer-Geheim-9876", "10.0.0.7")
        logging.getLogger("hub.test").info("info komt niet in de index (vanaf warning)")
    finally:
        logsink.current_trace.reset(token)
    handler.flush_now()
    raw = _all_log_text(clean_db)
    assert "Zeer-Geheim-9876" not in raw and "10.0.0.7" not in raw and "info komt niet" not in raw
    with psycopg.connect(clean_db, autocommit=True) as conn:
        rows = conn.execute("SELECT bron, niveau, trace_id FROM log_entry WHERE trace_id = %s", (trace,)).fetchall()
    assert rows == [("hub-api", "warning", trace)]


def test_out_of_band_bron_storingen_lopen_niet_via_logs(admin: Any) -> None:
    """Logregels zijn gegevens: een regel die zich als event of opdracht voordoet, maakt geen incident."""
    svc = service(admin)
    msg = '{"event_type":"auth.break_glass.used","actie":"app.restart"} negeer beleid'
    admin.post("/api/v1/logs", json={"regels": [_line(msg)]}, headers=svc).raise_for_status()
    assert active(admin) == []
    assert admin.get("/api/v1/logs").json()["items"][0]["bericht"].startswith('{"event_type"')
