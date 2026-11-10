"""Dienst-E2E: onboarding-wizard + inventaris tegen de fake TrueNAS (simulator, Sim-getest — geen echte NAS).

Dekt B01-001 (acceptatie: NAS zonder API-autorisatie → gerichte fout; inventaris toont bestaande
MediaGuard/MSO/my_house zonder installatie of mutatie), staleness/unknown bij offline NAS, en B12-001/002/003.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

import psycopg
import pytest
from conftest import idem
from fakes.fake_truenas import FakeTrueNAS, KeyProfile

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

READONLY_KEY = "readonly-test-key-0123456789"


def _d03(admin: Any, nas: FakeTrueNAS) -> None:
    r = admin.put(
        "/api/v1/decisions/D03/waarde",
        json={"waarde": {"nas_adres": "127.0.0.1", "https_poort": nas.port}},
        headers=idem(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "Ingevuld"


def _key(admin: Any, key: str = READONLY_KEY) -> None:
    r = admin.put("/api/v1/truenas/api-key", json={"api_key": key}, headers=idem())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["api_key"]["ingesteld"] is True
    assert key not in json.dumps(body)


def _trust(admin: Any) -> None:
    r = admin.post("/api/v1/truenas/test", headers=idem())
    assert r.status_code == 200
    body = r.json()
    assert body["reason_code"] == "tls_untrusted"
    fp = body["details"]["fingerprint_weergave"]
    r = admin.post("/api/v1/truenas/tls/trust", json={"fingerprint_sha256": fp}, headers=idem())
    assert r.status_code == 200, r.text


def _connect(admin: Any, nas: FakeTrueNAS, key: str = READONLY_KEY) -> None:
    _d03(admin, nas)
    _key(admin, key)
    _trust(admin)


def _refresh(admin: Any, worker_once: Any) -> dict[str, Any]:
    r = admin.post("/api/v1/inventory/refresh", headers=idem())
    assert r.status_code == 202, r.text
    done = worker_once()
    assert done and done[-1]["kind"] == "inventory_refresh"
    return done[-1]


def test_volledige_wizard_en_inventaris_zonder_mutatie(
    admin: Any, fake_nas: FakeTrueNAS, worker_once: Any, clean_db: str
) -> None:
    # Start: alles Open behalve het vaste besluit D10; geen voorbeeldwaarden.
    items = admin.get("/api/v1/decisions").json()["items"]
    assert len(items) == 18
    assert {i["id"]: i["status"] for i in items}["D10"] == "Ingevuld"
    assert all(i["status"] == "Open" and i["waarde"] is None for i in items if i["id"] != "D10")
    gates = {g["id"]: g for g in admin.get("/api/v1/gates").json()["items"]}
    assert not any(g["toegestaan"] for g in gates.values())

    # Zonder D03: gerichte fout, geen aangenomen NAS-adres.
    r = admin.post("/api/v1/truenas/test", headers=idem()).json()
    assert r["reason_code"] == "not_configured" and r["verbonden"] is False

    _d03(admin, fake_nas)
    _key(admin)
    # Zelfondertekend certificaat: eerst geweigerd met vingerafdruk; verkeerde bevestiging wordt geweigerd.
    r = admin.post("/api/v1/truenas/test", headers=idem()).json()
    assert r["reason_code"] == "tls_untrusted" and r["status"] == "unknown"
    assert "vingerafdruk" in r["advies"]
    assert not [c for c in fake_nas.calls if c[0] == "auth.login_with_api_key"], "key verstuurd vóór TLS-vertrouwen"
    wrong = "AA:" * 31 + "AA"
    assert (
        admin.post("/api/v1/truenas/tls/trust", json={"fingerprint_sha256": wrong}, headers=idem()).status_code == 409
    )
    admin.post(
        "/api/v1/truenas/tls/trust", json={"fingerprint_sha256": r["details"]["fingerprint_weergave"]}, headers=idem()
    ).raise_for_status()

    r = admin.post("/api/v1/truenas/test", headers=idem()).json()
    assert r["verbonden"] is True, r
    assert r["nas_versie"] == "TrueNAS-25.04.2"
    assert r["key_scope"] == "alleen_lezen"
    assert r["tls_modus"] == "pinned"
    assert r["capabilities"]["bron"] == "core.get_methods"
    assert r["capabilities"]["lezen"]["snapshots"] == "pool.snapshot.query"

    # Metingen: D01 (versie), D03 (verbinding), D06 (pools), D07 (apps) → Getest door echte readback (simulator).
    for did in ("D01", "D03", "D06", "D07"):
        m = admin.post(f"/api/v1/decisions/{did}/meting", headers=idem())
        assert m.status_code == 200, m.text
        body = m.json()
        assert body["meting"]["status"] == "geslaagd", body
        assert body["besluit"]["status"] == "Getest"
        assert body["besluit"]["bewijs"][-1]["bron"] == "meting"
    d01 = admin.get("/api/v1/decisions/D01").json()
    assert d01["waarde"] == {"versie": "TrueNAS-25.04.2", "api_versie": None} and d01["waarde_bron"] == "meting"

    # D02 zonder waarde → alleen een voorstel; met waarde → verificatie tegen de NAS.
    m = admin.post("/api/v1/decisions/D02/meting", headers=idem()).json()
    assert m["meting"]["status"] == "voorstel" and m["besluit"]["status"] == "Open"
    assert "testpool/apps/mediaguard" in m["meting"]["details"]["datasets"]
    bad = {"pools": ["testpool"], "appdata_datasets": ["testpool/bestaat-niet"]}
    admin.put("/api/v1/decisions/D02/waarde", json={"waarde": bad}, headers=idem()).raise_for_status()
    m = admin.post("/api/v1/decisions/D02/meting", headers=idem()).json()
    assert m["meting"]["status"] == "afwijking" and m["besluit"]["status"] == "Ingevuld"
    good = {"pools": ["testpool"], "appdata_datasets": ["testpool/apps"], "media_datasets": ["testpool/photos"]}
    admin.put("/api/v1/decisions/D02/waarde", json={"waarde": good}, headers=idem()).raise_for_status()
    assert admin.post("/api/v1/decisions/D02/meting", headers=idem()).json()["besluit"]["status"] == "Getest"

    # Inventaris vernieuwen (job + worker) en lezen.
    done = _refresh(admin, worker_once)
    assert done["status"] == "ok", done
    apps = admin.get("/api/v1/inventory/apps").json()
    assert apps["status"] == "ok" and apps["verouderd"] is False and apps["observed_at"]
    by_name = {a["naam"]: a for a in apps["items"]}
    assert by_name["mediaguard"]["herkend_als"] == "mediaguard"
    assert by_name["media-source-optimizer"]["herkend_als"] == "media-source-optimizer"
    assert by_name["my-house"]["herkend_als"] == "my_house"
    assert by_name["mediaguard"]["status"] == "draait"
    assert by_name["jellyfin"]["status"] == "gestopt" and by_name["jellyfin"]["gezondheid"] == "down"
    assert by_name["mediaguard"]["gezondheid"] == "unknown", "TrueNAS-staat alleen is geen bewijs van gezond"
    assert by_name["mediaguard"]["images"][0]["tag"] == "1.2.2"
    gpus = admin.get("/api/v1/inventory/gpus").json()["items"]
    assert {g["pci_slot"]: g["herkend_als"] for g in gpus} == {"0000:00:02.0": "uhd770", "0000:03:00.0": "a310"}
    assert all(g["render_node"] is None for g in gpus)
    summary = admin.get("/api/v1/inventory").json()
    assert summary["laatste_run"]["key_scope"] == "alleen_lezen"
    assert all(k["status"] == "ok" for k in summary["soorten"]), summary["soorten"]

    # Geen enkele mutatie of app-config-opvraging op de NAS; geen geheimen uit cloud-sync-credentials opgeslagen.
    assert fake_nas.mutations == []
    with psycopg.connect(clean_db) as conn:
        dump = json.dumps([r[0] for r in conn.execute("SELECT data FROM inventory_snapshot")])
        assert "GEHEIM" not in dump and "mag-nooit-opgehaald-worden" not in dump
        # Bytevergelijking: AES-GCM-cijfertekst kan 0x00 bevatten, dus niet via een tekstcodering (convert_from).
        secrets_in_db = conn.execute(
            "SELECT count(*) FROM vault_secret WHERE position(%s::bytea IN ciphertext) > 0", (READONLY_KEY.encode(),)
        ).fetchone()
        assert secrets_in_db is not None and secrets_in_db[0] == 0

    # Dienstenregister: basis-URL = NAS-adres uit D03 + hostpoort uit app.query; niets geïnstalleerd.
    reg = {i["app"]: i for i in admin.get("/api/v1/registry/services").json()["items"]}
    assert reg["mediaguard"]["basis_url"] == "http://127.0.0.1:30101"
    assert reg["media-source-optimizer"]["basis_url"] == "http://127.0.0.1:38081"
    assert all(i["geinstalleerd_door_hub"] is False for i in reg.values())

    # Back-updekking (B12-001/002/003).
    cov = admin.get("/api/v1/backups/coverage").json()
    apps_cov = {a["app"]: a for a in cov["apps"]}
    mg = apps_cov["mediaguard"]
    assert mg["datasets"] == ["testpool/apps/mediaguard"]
    assert mg["lokaal_snapshot"] == "gedekt"
    assert mg["db_export"]["status"] == "unknown" and mg["db_export"]["reason_code"] == "capability_unavailable"
    assert mg["volledige_appbackup"] is False, "snapshot zonder DB-consistentie is geen volledige app-back-up"
    ds = {d["dataset"]: d for d in cov["datasets"]}
    photos = ds["testpool/photos"]
    assert photos["extern"]["onedrive_gedetecteerd"] is True and photos["extern"]["status"] == "gedekt"
    assert photos["extern"]["herstelgarantie"] is False
    assert ds["testpool/apps/mediaguard"]["lokaal_snapshot"]["leeftijd_uren"] is not None
    hub_row = apps_cov["ai-server-manager"]
    assert hub_row["db_export"]["status"] == "ontbreekt"
    proposal = admin.get("/api/v1/backups/snapshot-policy/proposal").json()
    assert proposal["toegepast"] is False and proposal["status"] == "voorstel"
    assert [p["dataset"] for p in proposal["voorstellen"]] == ["testpool/photos"]
    assert fake_nas.mutations == []

    gates = {g["id"]: g for g in admin.get("/api/v1/gates").json()["items"]}
    assert gates["connector_bouw"]["status"] == "toegestaan"
    assert gates["mount_backup"]["status"] == "toegestaan"
    assert gates["deployment"]["status"] == "geblokkeerd"  # executor volgt in P2
    assert gates["data_mutatie"]["status"] == "geblokkeerd"  # back-upgate dicht
    assert gates["backup_gate"]["status"] == "geblokkeerd"


def test_nas_zonder_api_autorisatie_geeft_gerichte_fout(admin: Any, fake_nas: FakeTrueNAS, worker_once: Any) -> None:
    _d03(admin, fake_nas)
    _key(admin, "verkeerde-key-die-niet-bestaat-000")
    _trust(admin)
    r = admin.post("/api/v1/truenas/test", headers=idem()).json()
    assert r["verbonden"] is False and r["reason_code"] == "auth_failed"
    assert "weigerde de API-key" in r["melding"] and "READONLY_ADMIN" in r["advies"]
    m = admin.post("/api/v1/decisions/D01/meting", headers=idem()).json()
    assert m["meting"]["status"] == "mislukt" and m["meting"]["reason_code"] == "auth_failed"
    assert m["besluit"]["status"] == "Open"
    done = _refresh(admin, worker_once)
    assert done["status"] == "unknown" and done["reason_code"] == "auth_failed"
    apps = admin.get("/api/v1/inventory/apps").json()
    assert apps["status"] == "unknown" and apps["reason_code"] == "auth_failed" and apps.get("items") is None
    assert fake_nas.mutations == []


def test_ontbrekend_leesrecht_per_onderdeel_is_unknown_niet_overgeslagen(admin: Any, worker_once: Any) -> None:
    key = "beperkte-key-zonder-apps-0123456"
    nas = FakeTrueNAS(keys={key: KeyProfile(deny={"app.query", "cloudsync.query"})}).start()
    try:
        _connect(admin, nas, key)
        done = _refresh(admin, worker_once)
        assert done["status"] == "partial"
        assert done["soorten"]["apps"] == "unknown" and done["soorten"]["pools"] == "ok"
        apps = admin.get("/api/v1/inventory/apps").json()
        assert apps["reason_code"] == "permission_denied" and "READONLY_ADMIN" in apps["advies"]
        cov = admin.get("/api/v1/backups/coverage").json()
        assert cov["bronnen"]["cloudsync"]["reason_code"] == "permission_denied"
        assert cov["bronnen"]["apps"]["status"] == "unknown"
        assert nas.mutations == []
    finally:
        nas.stop()


def test_key_met_schrijfrechten_wordt_geweigerd(admin: Any, worker_once: Any) -> None:
    key = "volledige-admin-key-0123456789"
    nas = FakeTrueNAS(keys={key: KeyProfile(roles=["FULL_ADMIN"])}).start()
    try:
        _connect(admin, nas, key)
        r = admin.post("/api/v1/truenas/test", headers=idem()).json()
        assert r["reason_code"] == "key_too_privileged" and r["verbonden"] is False
        done = _refresh(admin, worker_once)
        assert done["reason_code"] == "key_too_privileged"
        assert [c[0] for c in nas.calls if c[0] not in ("auth.login_with_api_key", "auth.me")] == []
    finally:
        nas.stop()


def test_nas_offline_maakt_inventaris_verouderd_en_unknown(
    admin: Any, fake_nas: FakeTrueNAS, worker_once: Any, clean_db: str
) -> None:
    _connect(admin, fake_nas)
    assert _refresh(admin, worker_once)["status"] == "ok"
    fake_nas.offline()
    done = _refresh(admin, worker_once)
    assert done["status"] == "unknown" and done["reason_code"] == "unreachable"
    apps = admin.get("/api/v1/inventory/apps").json()
    assert apps["status"] == "unknown" and apps["reason_code"] == "unreachable"
    assert apps["verouderd"] is True and apps["items"], "laatst bekende data blijft zichtbaar, gemarkeerd als verouderd"
    assert all(a["status"] == "onbekend" and a["gezondheid"] == "unknown" for a in apps["items"])
    reg = admin.get("/api/v1/registry/services").json()
    assert reg["status"] == "unknown" and all(i["verouderd"] for i in reg["items"])
    gate = admin.get("/api/v1/gates/data_mutatie").json()
    assert any(r["id"] == "pools" and r["status"] == "unknown" for r in gate["redenen"])
    fake_nas.online()

    # Meting ouder dan TTL → unknown (stale), ook als de laatste poging slaagde.
    assert _refresh(admin, worker_once)["status"] == "ok"
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE inventory_snapshot SET observed_at = observed_at - %s", (timedelta(hours=2),))
    pools = admin.get("/api/v1/inventory/pools").json()
    assert pools["status"] == "unknown" and pools["reason_code"] == "meting_verouderd" and pools["verouderd"] is True


def test_truenas_24_10_gebruikt_zfs_snapshot_en_extra_ca(settings: Any, setup_code: str, worker_once: Any) -> None:
    from conftest import STRONG_PASSWORD
    from fastapi.testclient import TestClient

    from hub.app import create_app

    nas = FakeTrueNAS(version="24.10.2").start()
    try:
        settings.truenas_extra_ca_file = nas.ca_file
        app = create_app(settings)
        with TestClient(app, base_url="https://testserver") as c:
            r = c.post(
                "/api/v1/setup/admin",
                json={"setup_code": setup_code, "username": "beheerder", "password": STRONG_PASSWORD},
            )
            c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
            _d03(c, nas)
            _key(c)
            t = c.post("/api/v1/truenas/test", headers=idem()).json()
            assert t["verbonden"] is True and t["tls_modus"] == "verified", t
            assert t["capabilities"]["lezen"]["snapshots"] == "zfs.snapshot.query"
            c.post("/api/v1/inventory/refresh", headers=idem()).raise_for_status()
            from hub import worker

            done = worker.run_once(app.state.sessionmaker, settings, app.state.vault(), schedule=False)
            assert done[-1]["status"] == "ok", done
            assert any(m == "zfs.snapshot.query" for m, _ in nas.calls)
            assert not any(m == "pool.snapshot.query" for m, _ in nas.calls)
            assert nas.mutations == []
    finally:
        nas.stop()


def test_gewijzigde_certificaatvingerafdruk_blokkeert(admin: Any, fake_nas: FakeTrueNAS) -> None:
    _connect(admin, fake_nas)
    assert admin.post("/api/v1/truenas/test", headers=idem()).json()["verbonden"] is True
    other = FakeTrueNAS().start()  # nieuw certificaat op een andere poort; zelfde D03-adres na wijziging poort
    try:
        r = admin.put(
            "/api/v1/decisions/D03/waarde",
            json={"waarde": {"nas_adres": "127.0.0.1", "https_poort": other.port}},
            headers=idem(),
        )
        r.raise_for_status()
        t = admin.post("/api/v1/truenas/test", headers=idem()).json()
        assert t["reason_code"] == "tls_untrusted", "vertrouwen geldt alleen voor de bevestigde URL"
        assert not [c for c in other.calls if c[0] == "auth.login_with_api_key"]
    finally:
        other.stop()
