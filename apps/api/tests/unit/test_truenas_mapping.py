"""Capability-map per versie, normalisatie (whitelist) en key-scope."""

from __future__ import annotations

import pytest

from hub.truenas import normalize as norm
from hub.truenas.capabilities import build_capability_map, parse_version
from hub.truenas.client import (
    READ_ONLY_METHODS,
    build_ws_url,
    display_fingerprint,
    normalize_fingerprint,
    validate_host,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TrueNAS-SCALE-24.10.2.1", (24, 10, 2)),
        ("25.04.1", (25, 4, 1)),
        ("TrueNAS-25.10.0", (25, 10, 0)),
        ("x", None),
        (None, None),
    ],
)
def test_versie_parsen(raw: str | None, expected: tuple[int, int, int] | None) -> None:
    assert parse_version(raw) == expected


def test_capabilities_uit_core_get_methods() -> None:
    m25 = build_capability_map(
        {"pool.snapshot.query", "app.query", "app.gpu_choices", "pool.snapshot.create"}, "25.04.2"
    )
    assert m25.source == "core.get_methods"
    assert m25.method_for("snapshots") == "pool.snapshot.query"
    assert m25.method_for("pools") is None  # niet aangeboden → onbekend, niet aangenomen
    assert m25.write_info["snapshot_create"] == "pool.snapshot.create"
    m24 = build_capability_map({"zfs.snapshot.query", "device.get_info"}, "24.10.2")
    assert m24.method_for("snapshots") == "zfs.snapshot.query"
    assert m24.method_for("gpus") == "device.get_info"


def test_capabilities_terugval_op_versietabel() -> None:
    assert build_capability_map(None, "TrueNAS-25.04.0").method_for("snapshots") == "pool.snapshot.query"
    assert build_capability_map(None, "24.10.1").method_for("snapshots") == "zfs.snapshot.query"
    m = build_capability_map(None, None)
    assert m.source == "geen" and all(v is None for v in m.methods.values())


def test_alleen_leesmethoden_toegestaan() -> None:
    assert all(
        m.endswith(
            (
                ".query",
                ".info",
                ".version",
                ".list",
                ".results",
                ".get_methods",
                ".summary",
                ".gpu_choices",
                ".get_info",
                ".me",
                ".login_with_api_key",
            )
        )
        for m in READ_ONLY_METHODS
    )
    assert not {"app.create", "app.delete", "pool.snapshot.create", "app.redeploy"} & READ_ONLY_METHODS


def test_url_en_adresvalidatie() -> None:
    assert build_ws_url("192.0.2.5", None) == "wss://192.0.2.5/api/current"
    assert build_ws_url("nas.lan", 8443) == "wss://nas.lan:8443/api/current"
    assert build_ws_url("fd00::1", 443) == "wss://[fd00::1]/api/current"
    for bad in ("http://nas", "nas:443", "", "-bad", "a/b"):
        with pytest.raises(ValueError):
            validate_host(bad)


def test_vingerafdruk_normaliseren() -> None:
    fp = "ab" * 32
    assert normalize_fingerprint(display_fingerprint(fp)) == fp
    with pytest.raises(ValueError):
        normalize_fingerprint("abc")


def test_apps_normaliseren_en_herkennen() -> None:
    raw = [
        {
            "name": "mso",
            "state": "RUNNING",
            "version": "1",
            "config": {"env": {"X": "geheim"}},
            "active_workloads": {
                "images": ["ghcr.io/lvos04/media-source-optimizer:1.6.0@sha256:" + "a" * 64],
                "used_ports": [
                    {
                        "container_port": 38081,
                        "protocol": "TCP",
                        "host_ports": [{"host_port": 38081, "host_ip": "0.0.0.0"}],
                    }
                ],
                "volumes": [{"source": "/mnt/p/apps/mso", "destination": "/appdata", "type": "bind"}],
            },
        }
    ]
    a = norm.apps(raw)[0]
    assert a["herkend_als"] == "media-source-optimizer"
    assert a["images"][0]["tag"] == "1.6.0" and a["images"][0]["digest"] == "sha256:" + "a" * 64
    assert a["poorten"] == [{"container_poort": 38081, "host_poort": 38081, "host_ip": "0.0.0.0", "protocol": "tcp"}]
    assert "config" not in a and "geheim" not in str(a)
    assert norm.recognize_app("my-house", []) == "my_house"
    assert norm.recognize_app("onbekend", ["docker.io/x/y:1"]) is None


def test_cloudsync_zonder_credentials_en_onedrive_detectie() -> None:
    raw = [
        {
            "id": 1,
            "path": "/mnt/p/photos",
            "direction": "PUSH",
            "enabled": True,
            "credentials": {"provider": {"type": "ONEDRIVE", "client_secret": "S3CRET", "token": "T0KEN"}},
            "job": {
                "state": "FAILED",
                "error": "Bearer abcdefghijklmnop expired",
                "time_finished": {"$date": 1700000000000},
            },
        },
        {"id": 2, "path": "/mnt/p/x", "direction": "PUSH", "credentials": {"provider": "S3"}},
    ]
    out = norm.cloudsync(raw)
    assert out[0]["is_onedrive"] is True and out[1]["is_onedrive"] is False and out[1]["provider"] == "S3"
    text = str(out)
    assert "S3CRET" not in text and "T0KEN" not in text and "abcdefghijklmnop" not in text
    assert out[0]["laatste_job"]["beeindigd"] == "2023-11-14T22:13:20Z"


def test_gpu_identiteit_is_pci_slot() -> None:
    out = norm.gpus(
        {
            "0000:03:00.0": {"description": "Intel DG2 [Arc A310]", "vendor": "INTEL"},
            "0000:00:02.0": {"description": "UHD Graphics 770"},
        }
    )
    assert [(g["pci_slot"], g["herkend_als"]) for g in out] == [("0000:00:02.0", "uhd770"), ("0000:03:00.0", "a310")]
    assert all(g["render_node"] is None for g in out)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"$date": 1700000000000}, "2023-11-14T22:13:20Z"),
        (1700000000, "2023-11-14T22:13:20Z"),
        ("1700000000", "2023-11-14T22:13:20Z"),
        ("2023-11-14T22:13:20Z", "2023-11-14T22:13:20Z"),
        ({"parsed": {"$date": 1700000000000}}, "2023-11-14T22:13:20Z"),
        (None, None),
        ("onzin", None),
        (True, None),
    ],
)
def test_tijden_parsen(value: object, expected: str | None) -> None:
    assert norm.parse_ts(value) == expected


@pytest.mark.parametrize(
    ("roles", "scope"),
    [
        (["READONLY_ADMIN"], "alleen_lezen"),
        (["APPS_READ", "POOL_READ"], "alleen_lezen"),
        (["FULL_ADMIN"], "schrijfrechten"),
        (["READONLY_ADMIN", "APPS_WRITE"], "schrijfrechten"),
        ([], "onbekend"),
    ],
)
def test_key_scope(roles: list[str], scope: str) -> None:
    assert norm.key_scope({"privilege": {"roles": {"$set": roles}}}) == scope
    assert norm.key_scope(None) == "onbekend"


def test_pools_en_datasets() -> None:
    p = norm.pools(
        [
            {
                "name": "p",
                "status": "DEGRADED",
                "healthy": False,
                "size": 100,
                "allocated": 85,
                "free": 15,
                "scan": {"state": "FINISHED", "errors": 2},
            }
        ]
    )[0]
    assert p["gezond"] is False and p["gebruik_pct"] == 85.0 and p["scrub"]["fouten"] == 2
    ds = norm.datasets([{"name": "p", "mountpoint": "/mnt/p", "children": [{"name": "p/a", "mountpoint": "/mnt/p/a"}]}])
    assert [d["naam"] for d in ds] == ["p", "p/a"]
