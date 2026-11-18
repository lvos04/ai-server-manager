"""De gepinde planner leest een echte Hub. Alleen de TrueNAS-bron is een simulator."""

from __future__ import annotations

import os
import subprocess
import tarfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import enroll_body
from nashelpers import connect

PLANNER_PIN = "26746920e643cdbb5f9dc31b90cbcc29b65c1f1e"
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def planner_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = Path(os.environ["JLP_SOURCE"]).resolve()
    work = tmp_path_factory.mktemp("planner-m3")
    archive = work / "planner.tar"
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "archive",
            "-o",
            str(archive),
            PLANNER_PIN,
            "apps/api/src",
            "install/manifests",
        ],
        check=True,
    )
    with tarfile.open(archive) as f:
        f.extractall(work, filter="data")
    return work


@pytest.mark.parametrize(
    ("manifest_name", "train", "app_name", "pin", "replacement"),
    [
        ("gotify", "stable", "ix-app", "1.4.8", "1.4.9"),
        ("authentik", "community", "authentik", "1.3.64", "1.3.65"),
    ],
)
def test_verdwenen_versie_blokkeert_planner_zolang_de_nee_vers_is(
    admin: Any,
    fake_nas: Any,
    worker_once: Any,
    planner_source: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest_name: str,
    train: str,
    app_name: str,
    pin: str,
    replacement: str,
) -> None:
    monkeypatch.syspath_prepend(str(planner_source / "apps/api/src"))
    from lifecycle import planner
    from lifecycle.hubread import HubLezer

    from hub.catalog import availability

    now = datetime.now(UTC)
    monkeypatch.setattr(availability, "utcnow", lambda: now)
    connect(admin, fake_nas)
    grant = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "jelly-leon-platform"})
    assert grant.status_code == 201
    enrolled = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body("jelly-leon-platform", token=grant.json()["enrollment_token"]),
    )
    assert enrolled.status_code == 200
    reader = HubLezer(admin, str(admin.base_url), enrolled.json()["service_token"])
    worker_once(schedule=True)
    first = reader.beschikbaarheid(train, app_name, pin)
    assert first.beschikbaar == "ja" and first.gemeten_op
    inventory = reader.inventaris()
    assert inventory.status == "ok"

    index = fake_nas.data["catalog.apps"][train][app_name]
    index["latest_version"] = replacement
    fake_nas.data["catalog.get_app_details"][train][app_name] = {
        **index,
        "versions": {replacement: {"version": replacement}},
    }
    now += timedelta(seconds=300)
    worker_once(schedule=True)
    second = reader.beschikbaarheid(train, app_name, pin)
    assert second.beschikbaar == "nee" and second.gemeten_op > first.gemeten_op
    assert reader.beschikbaarheid(train, app_name, replacement).beschikbaar == "ja"

    manifest = (planner_source / "install/manifests" / f"{manifest_name}.manifest.yaml").read_text(encoding="utf-8")

    def plan() -> dict[str, Any]:
        return planner.plan_installatie(
            plan_id=uuid.uuid4(),
            manifest_yaml=manifest,
            parameters={},
            app_name=None,
            doel=planner.Doel(truenas_version=fake_nas.version, ix_app_version="1.4.8"),
            inventaris=inventory,
            beschikbaar=reader.beschikbaarheid,
            now=now,
        )

    blocked = plan()
    missing = next(b for b in blocked["blokkades"] if b["code"] == "version_unavailable")
    assert missing["details"]["pinned_version"] == pin
    assert blocked["stappen"] == []
    now += timedelta(seconds=901)
    assert reader.beschikbaarheid(train, app_name, pin).beschikbaar == "onbekend"
    codes = {b["code"] for b in plan()["blokkades"]}
    assert "version_availability_unknown" in codes and "version_unavailable" not in codes
    assert not fake_nas.mutations
