"""Events-inbox (dedupe), connectorcontract, besluiten-API (statusovergangen, ETag, idempotency)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest
from conftest import idem, login_as, make_user

pytestmark = pytest.mark.integration


def _service(admin: Any, app: Any, app_id: str = "home-control-hub") -> tuple[Any, dict[str, str]]:
    from fastapi.testclient import TestClient

    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id}).json()["enrollment_token"]
    anon = TestClient(app, base_url="https://testserver")
    svc = anon.post("/api/v1/services/enroll", json={"app_id": app_id, "enrollment_token": tok}).json()
    return anon, {"Authorization": f"Bearer {svc['service_token']}"}


def _event(source: str = "home-control-hub", **over: Any) -> dict[str, Any]:
    ev = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "source_app": source,
        "source_event_id": "bron-1",
        "event_type": "app.health.changed",
        "entity": {"type": "app", "id": "beszel"},
        "timestamp_utc": "2026-11-09T04:00:00Z",
        "trace_id": str(uuid.uuid4()),
        "correlation_id": None,
        "actor": {"type": "system", "id": "home-control-hub"},
        "classification": "internal",
        "payload": {"status": "down", "api_key": "mag-niet-bewaard"},
        "payload_ref": None,
    }
    ev.update(over)
    return ev


def test_inbox_dedupe_en_redactie(admin: Any, app: Any) -> None:
    svc, hdr = _service(admin, app)
    ev = _event()
    r = svc.post("/api/v1/events/inbox", json=ev, headers=hdr)
    assert r.status_code == 202 and r.json()["status"] == "accepted"
    assert svc.post("/api/v1/events/inbox", json=ev, headers=hdr).json()["status"] == "duplicate"
    same_source = _event(event_id=str(uuid.uuid4()))  # zelfde (source_app, source_event_id)
    r = svc.post("/api/v1/events/inbox", json=same_source, headers=hdr)
    assert r.status_code == 200 and r.json()["status"] == "duplicate"
    items = admin.get("/api/v1/events").json()["items"]
    assert len(items) == 1 and items[0]["payload"]["api_key"] == "***"


def test_inbox_weigert_vervalste_bron_en_ongeldige_envelope(admin: Any, app: Any) -> None:
    svc, hdr = _service(admin, app)
    r = svc.post("/api/v1/events/inbox", json=_event(source="mediaguard"), headers=hdr)
    assert r.status_code == 403 and r.json()["code"] == "source_mismatch"
    assert svc.post("/api/v1/events/inbox", json=_event()).status_code == 401
    bad = _event(event_type="GeenPunten", timestamp_utc="2026-11-09T04:00:00")
    r = svc.post("/api/v1/events/inbox", json=bad, headers=hdr)
    assert r.status_code == 422 and {f["veld"] for f in r.json()["details"]["fouten"]} >= {
        "body.event_type",
        "body.timestamp_utc",
    }
    # gebruikerssessie mag niet in de inbox schrijven
    assert admin.post("/api/v1/events/inbox", json=_event()).status_code == 401


def test_gevoelige_payload_verborgen_voor_viewer_en_paginering(admin: Any, app: Any) -> None:
    svc, hdr = _service(admin, app)
    for i in range(3):
        svc.post("/api/v1/events/inbox", json=_event(source_event_id=f"s{i}", classification="sensitive"), headers=hdr)
    make_user(admin, "kijker", "viewer")
    viewer = login_as(app, "kijker")
    page1 = viewer.get("/api/v1/events?limit=2").json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    assert all(i["payload"] is None and i["payload_verborgen"] for i in page1["items"])
    page2 = viewer.get(f"/api/v1/events?limit=2&cursor={page1['next_cursor']}").json()
    assert len(page2["items"]) == 1 and page2["next_cursor"] is None
    assert admin.get("/api/v1/events").json()["items"][0]["payload"] is not None


def test_connectorcontract_van_de_hub(admin: Any, app: Any) -> None:
    svc, hdr = _service(admin, app)
    d = svc.get("/connector/v1/discover", headers=hdr).json()
    assert d["app_id"] == "ai-server-manager" and d["schema_version"] == "1.0" and d["capabilities"] == ["read"]
    h = svc.get("/connector/v1/health", headers=hdr).json()
    assert h["status"] in ("degraded", "unknown") and {c["name"] for c in h["checks"]} == {
        "database",
        "worker",
        "eigen_backup",
    }
    items = svc.get("/connector/v1/items?type=decision&limit=5", headers=hdr).json()
    assert len(items["items"]) == 5 and items["next_cursor"]
    for path in ("propose", "apply", "rollback"):
        r = svc.post(f"/connector/v1/{path}", headers=hdr)
        assert r.status_code == 501 and r.json()["code"] == "capability_unavailable"
    admin.put(
        "/api/v1/decisions/D16/waarde",
        json={"waarde": {"per_app": [{"app_id": "mediaguard", "rpo_uren": 24, "rto_uren": 4}]}},
        headers=idem(),
    )
    ev = svc.get("/connector/v1/events", headers=hdr).json()
    assert (
        ev["items"][0]["event_type"] == "onboarding.decision.changed"
        and ev["items"][0]["source_app"] == "ai-server-manager"
    )
    assert svc.get("/connector/v1/evidence/onzin", headers=hdr).status_code == 404


def test_besluit_statusovergangen(admin: Any) -> None:
    r = admin.get("/api/v1/decisions/D03")
    etag = r.headers["ETag"]
    assert r.json()["status"] == "Open" and "schema" in r.json()
    bad = admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "http://nas"}}, headers=idem())
    assert bad.status_code == 422 and bad.json()["details"]["fouten"]
    ok = admin.put(
        "/api/v1/decisions/D03/waarde",
        json={"waarde": {"nas_adres": "192.0.2.20"}},
        headers={**idem(), "If-Match": etag},
    )
    assert ok.status_code == 200 and ok.json()["status"] == "Ingevuld" and ok.json()["waarde_bron"] == "gebruiker"
    stale = admin.put(
        "/api/v1/decisions/D03/waarde",
        json={"waarde": {"nas_adres": "192.0.2.21"}},
        headers={**idem(), "If-Match": etag},
    )
    assert stale.status_code == 412
    ev = {
        "soort": "handmatige_test",
        "omschrijving": "Adres gecontroleerd in TrueNAS Network",
        "resultaat": "geslaagd",
        "uitgevoerd_op": str(date(2026, 11, 9)),
    }
    r = admin.post("/api/v1/decisions/D03/bewijs", json=ev, headers=idem())
    assert r.json()["status"] == "Getest" and r.json()["bewijs"][0]["bron"] == "gebruiker"
    r = admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.22"}}, headers=idem())
    assert r.json()["status"] == "Ingevuld" and r.json()["getest_op"] is None
    r = admin.post(
        "/api/v1/decisions/D01/status", json={"status": "N.v.t.", "reden": "niet van toepassing"}, headers=idem()
    )
    assert r.status_code == 409
    r = admin.post(
        "/api/v1/decisions/D18/status", json={"status": "N.v.t.", "reden": "Geen muziekwensen"}, headers=idem()
    )
    assert r.json()["status"] == "N.v.t."
    r = admin.post("/api/v1/decisions/D12/status", json={"status": "Getest", "reden": ""}, headers=idem())
    assert r.status_code == 422
    assert admin.put("/api/v1/decisions/D10/waarde", json={"waarde": {}}, headers=idem()).status_code == 409
    assert admin.post("/api/v1/decisions/D04/meting", headers=idem()).status_code == 422
    assert admin.post("/api/v1/decisions/D04/bewijs", json=ev, headers=idem()).json()["code"] == "decision_not_filled"


def test_idempotency_replay_voert_niet_twee_keer_uit(admin: Any) -> None:
    key = idem()
    body = {"waarde": {"nas_adres": "192.0.2.30"}}
    r1 = admin.put("/api/v1/decisions/D03/waarde", json=body, headers=key)
    r2 = admin.put("/api/v1/decisions/D03/waarde", json=body, headers=key)
    assert r1.json() == r2.json() and r2.headers["Idempotent-Replay"] == "true"
    assert admin.get("/api/v1/decisions/D03").json()["version"] == r1.json()["version"]
    r3 = admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.31"}}, headers=key)
    assert r3.status_code == 422 and r3.json()["code"] == "idempotency_key_reused"
    assert (
        admin.put("/api/v1/decisions/D03/waarde", json=body, headers={"Idempotency-Key": "geen-uuid"}).status_code
        == 400
    )


def test_d05_getest_vereist_hersteltests(admin: Any) -> None:
    val = {
        "foto_hersteld": True,
        "db_export_hersteld": True,
        "omgeving": "Geïsoleerde testmap",
        "uitgevoerd_op": "2026-11-08",
        "referentie": "proefherstel 1",
    }
    admin.put("/api/v1/decisions/D05/waarde", json={"waarde": val}, headers=idem()).raise_for_status()
    ev = {
        "soort": "hersteltest",
        "omschrijving": "Foto en database teruggezet",
        "resultaat": "geslaagd",
        "uitgevoerd_op": "2026-11-08",
    }
    r = admin.post("/api/v1/decisions/D05/bewijs", json=ev, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "restore_evidence_missing"
    for soort in ("foto", "database"):
        rt = {
            "app_id": "mediaguard",
            "soort": soort,
            "resultaat": "geslaagd",
            "omgeving": "geïsoleerde testmap",
            "omschrijving": f"{soort} teruggezet en geopend",
            "uitgevoerd_op": "2026-11-08T10:00:00Z",
            "duur_minuten": 20,
        }
        assert admin.post("/api/v1/backups/restore-tests", json=rt, headers=idem()).status_code == 201
    r = admin.post("/api/v1/decisions/D05/bewijs", json=ev, headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "Getest"
    gate = admin.get("/api/v1/gates/backup_gate").json()
    assert gate["status"] == "geblokkeerd"  # D04, D16 en eigen back-up ontbreken nog
    ids = {r["id"] for r in gate["redenen"]}
    assert {"D04", "D16", "eigen_backup"} <= ids and "D05" not in ids


def test_audit_spoor(admin: Any) -> None:
    admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.40"}}, headers=idem())
    items = admin.get("/api/v1/audit").json()["items"]
    actions = [i["actie"] for i in items]
    assert "decision.value_set" in actions and "setup.admin_created" in actions
