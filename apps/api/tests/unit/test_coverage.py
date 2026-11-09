"""Back-updekking en snapshotbeleid-voorstel (pure logica)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from hub.backup.coverage import CoverageInputs, compute, snapshot_policy_proposal
from hub.timeutil import iso

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def ok(data: Any) -> dict[str, Any]:
    return {"status": "ok", "data": data, "observed_at": iso(NOW), "verouderd": False}


UNKNOWN = {"status": "unknown", "reason_code": "unreachable", "data": None}


def _inputs(**over: Any) -> CoverageInputs:
    base: dict[str, Any] = dict(
        apps=ok(
            [
                {
                    "naam": "mediaguard",
                    "herkend_als": "mediaguard",
                    "opslag": [{"bron": "/mnt/p/apps/mediaguard/config", "doel": "/data"}],
                },
                {
                    "naam": "ai-server-manager",
                    "herkend_als": "ai-server-manager",
                    "opslag": [{"bron": "/mnt/p/apps/hub", "doel": "/appdata"}],
                },
            ]
        ),
        datasets=ok(
            [
                {"naam": "p", "pool": "p", "mountpoint": "/mnt/p"},
                {"naam": "p/apps", "pool": "p", "mountpoint": "/mnt/p/apps"},
                {"naam": "p/apps/mediaguard", "pool": "p", "mountpoint": "/mnt/p/apps/mediaguard"},
                {"naam": "p/apps/hub", "pool": "p", "mountpoint": "/mnt/p/apps/hub"},
                {"naam": "p/photos", "pool": "p", "mountpoint": "/mnt/p/photos"},
            ]
        ),
        pools=ok([{"naam": "p", "gebruik_pct": 85.0}]),
        snapshot_tasks=ok(
            [{"id": 1, "dataset": "p/apps", "recursief": True, "uitgesloten": ["p/apps/hub"], "ingeschakeld": True}]
        ),
        latest_snapshots=ok(
            {"per_dataset": {"p/apps": {"naam": "p/apps@x", "aangemaakt_op": iso(NOW - timedelta(hours=3))}}}
        ),
        cloudsync=ok(
            [
                {
                    "id": 7,
                    "pad": "/mnt/p/photos",
                    "richting": "PUSH",
                    "ingeschakeld": True,
                    "provider": "ONEDRIVE",
                    "is_onedrive": True,
                    "laatste_job": {"staat": "SUCCESS", "beeindigd": iso(NOW - timedelta(hours=5))},
                }
            ]
        ),
        replication=ok([]),
        rpo_rto={
            "mediaguard": {"rpo_uren": 1.0, "rto_uren": 4.0},
            "ai-server-manager": {"rpo_uren": 24.0, "rto_uren": 2.0},
        },
        self_backup={"finished_at": NOW - timedelta(hours=2), "sha256": "ab" * 32, "id": "b1"},
        self_backup_max_age_seconds=26 * 3600,
        restore_tests=[],
        enrolled_apps=set(),
        extra_datasets=["p/photos"],
        now=NOW,
    )
    base.update(over)
    return CoverageInputs(**base)


def test_dekking_per_app_en_dataset() -> None:
    cov = compute(_inputs())
    apps = {a["app"]: a for a in cov["apps"]}
    mg = apps["mediaguard"]
    assert mg["datasets"] == ["p/apps/mediaguard"]
    assert mg["lokaal_snapshot"] == "gedekt"
    assert mg["db_export"]["reason_code"] == "capability_unavailable"
    assert mg["volledige_appbackup"] is False
    assert mg["rpo_rto"]["rpo_status"] == "overschreden"  # 3 uur oud > RPO 1 uur
    assert mg["rpo_rto"]["rto_status"] == "unknown"
    hub = apps["ai-server-manager"]
    assert hub["lokaal_snapshot"] == "niet_gedekt"  # uitgesloten in de taak
    assert hub["db_export"]["status"] == "geverifieerd"
    assert hub["volledige_appbackup"] is False  # geen snapshot of externe kopie van de dataset
    ds = {d["dataset"]: d for d in cov["datasets"]}
    assert ds["p/photos"]["extern"]["status"] == "gedekt" and ds["p/photos"]["extern"]["herstelgarantie"] is False
    assert ds["p/photos"]["extern"]["cloud_sync"][0]["leeftijd_uren"] == 5.0


def test_hersteltest_geeft_herstelgarantie_en_rto() -> None:
    tests = [
        {
            "app_id": "mediaguard",
            "dataset": None,
            "resultaat": "geslaagd",
            "uitgevoerd_op": iso(NOW),
            "duur_minuten": 30,
        },
        {"app_id": None, "dataset": "p/photos", "resultaat": "geslaagd", "uitgevoerd_op": iso(NOW), "duur_minuten": 10},
    ]
    cov = compute(_inputs(restore_tests=tests))
    apps = {a["app"]: a for a in cov["apps"]}
    assert apps["mediaguard"]["rpo_rto"]["rto_status"] == "binnen"
    ds = {d["dataset"]: d for d in cov["datasets"]}
    assert ds["p/photos"]["extern"]["herstelgarantie"] is True


def test_ingeschreven_connector_en_hub_volledig() -> None:
    inp = _inputs(
        enrolled_apps={"mediaguard"},
        snapshot_tasks=ok([{"id": 1, "dataset": "p/apps", "recursief": True, "uitgesloten": [], "ingeschakeld": True}]),
    )
    apps = {a["app"]: a for a in compute(inp)["apps"]}
    assert apps["mediaguard"]["db_export"]["reason_code"] == "connector_not_queried"
    assert apps["ai-server-manager"]["volledige_appbackup"] is True


def test_onbekende_bronnen_zijn_unknown() -> None:
    cov = compute(_inputs(snapshot_tasks=UNKNOWN, cloudsync=UNKNOWN, replication=UNKNOWN))
    apps = {a["app"]: a for a in cov["apps"]}
    assert apps["mediaguard"]["lokaal_snapshot"] == "unknown" and apps["mediaguard"]["extern"] == "unknown"
    assert cov["bronnen"]["cloudsync"]["reason_code"] == "unreachable"


def test_zonder_inventaris_staat_de_hub_er_toch_in() -> None:
    cov = compute(_inputs(apps=UNKNOWN, datasets=UNKNOWN, self_backup=None))
    assert [a["app"] for a in cov["apps"]] == ["ai-server-manager"]
    assert cov["apps"][0]["db_export"]["status"] == "ontbreekt"


def test_verouderde_eigen_backup() -> None:
    inp = _inputs(self_backup={"finished_at": NOW - timedelta(hours=30), "sha256": "x", "id": "b"})
    apps = {a["app"]: a for a in compute(inp)["apps"]}
    assert apps["ai-server-manager"]["db_export"]["status"] == "verouderd"


def test_snapshotvoorstel_met_ruimtewaarschuwing() -> None:
    inp = _inputs()
    prop = snapshot_policy_proposal(inp, compute(inp))
    assert prop["toegepast"] is False and prop["status"] == "voorstel"
    by_ds = {p["dataset"]: p for p in prop["voorstellen"]}
    assert set(by_ds) == {"p/apps/hub", "p/photos"}
    assert by_ds["p/apps/hub"]["voorstel"]["frequentie"] == "dagelijks"
    assert any("85.0% vol" in w for w in prop["waarschuwingen"])
