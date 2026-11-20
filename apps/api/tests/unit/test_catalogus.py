"""Unit: appcatalogus (B01-002) en gezondheidsmodel (B09-002) zonder database of netwerk."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from hub.adapters.health import stored_health
from hub.catalog.discovery import deep_link, image_info, install_method, readback_digests, storage
from hub.catalog.profiles import ADAPTER_TYPES, PROFILES, SOORTEN, profile_for
from hub.models import AdapterLink
from hub.monitoring.health import Component, evaluate, freshen, status_value
from hub.outbound import OutboundError, validate_base_url
from hub.truenas import normalize as norm

REPO = Path(__file__).resolve().parents[4]
NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


# ------------------------------------------------------------------ herkenning en normalisatie
@pytest.mark.parametrize(
    ("name", "image", "expected"),
    [
        ("ai-server-manager-executor", "ghcr.io/lvos04/ai-server-manager-executor:0.1.0", "ai-server-manager-executor"),
        ("ai-server-manager", "ghcr.io/lvos04/ai-server-manager:0.1.0", "ai-server-manager"),
        ("jelly-leon-platform", "ghcr.io/lvos04/jelly-leon-platform:0.1.0", "jelly-leon-platform"),
        ("jelly-leon", "ghcr.io/lvos04/jelly-leon:10.11.11", "jelly-leon"),
        ("mijn-hub", "ghcr.io/lvos04/home-control-hub:0.1.0", "home-control-hub"),
        ("mediaguard", "ghcr.io/lvos04/mediaguard-core:1.2.2-aio", "mediaguard"),
        ("iets", "docker.io/library/nginx:1.27", None),
    ],
)
def test_herkenning_exact_voor_voorvoegsel(name: str, image: str, expected: str | None) -> None:
    assert norm.recognize_app(name, [image]) == expected


def test_portals_nemen_host_nooit_over() -> None:
    out = norm.portals({"Web UI": "http://0.0.0.0:30080/ui", "kapot": "ftp://x", "zonder": 5})
    assert out == [{"naam": "Web UI", "schema": "http", "poort": 30080, "pad": "/ui"}]


def test_images_alleen_tags_en_digests() -> None:
    raw = [{"id": "sha256:1", "repo_tags": ["a:1"], "repo_digests": ["a@sha256:" + "b" * 64], "author": "x"}]
    assert norm.images(raw) == [{"id": "sha256:1", "repo_tags": ["a:1"], "repo_digests": ["a@sha256:" + "b" * 64]}]


# ------------------------------------------------------------------ installatiewijze, image en opslag
@pytest.mark.parametrize(
    ("app", "expected"),
    [
        ({"custom_app": False, "catalogus_app": "ix-app"}, "custom_app"),
        ({"custom_app": False, "catalogus_app": "jellyfin"}, "catalog_app"),
        ({"custom_app": True, "catalogus_app": None}, "custom_compose"),
        ({"custom_app": None}, "onbekend"),
        ({"custom_app": False, "catalogus_app": None}, "onbekend"),
    ],
)
def test_installatiewijze(app: dict[str, Any], expected: str) -> None:
    assert install_method(app) == expected


DIGEST = "sha256:" + "c" * 64


def test_digest_readback_klopt_wijkt_af_of_onbekend() -> None:
    app = {"images": [{"repository": "ghcr.io/lvos04/mediaguard", "tag": "1.2.2", "digest": None}]}
    imgs = [{"repo_tags": ["ghcr.io/lvos04/mediaguard:1.2.2"], "repo_digests": [f"ghcr.io/lvos04/mediaguard@{DIGEST}"]}]
    ok = image_info(app, "mediaguard", imgs)
    assert ok["digest"] == DIGEST and ok["digest_bron"] == "app.image.query" and ok["readback"]["status"] == "ok"
    tag_digest = "sha256:" + "d" * 64
    pinned = {"images": [{"repository": "ghcr.io/lvos04/mediaguard", "tag": "1.2.2", "digest": tag_digest}]}
    off = image_info(pinned, "mediaguard", imgs)
    assert off["digest"] == tag_digest and off["readback"]["status"] == "afwijking"
    assert image_info(app, "mediaguard", None)["readback"]["status"] == "unknown"
    assert image_info(app, "mediaguard", [])["digest"] is None
    # Alleen digests met dezelfde repository tellen (geen verwarring met een andere image).
    other = [{"repo_tags": ["ghcr.io/lvos04/mediaguard:1.2.2"], "repo_digests": [f"ghcr.io/x/y@{DIGEST}"]}]
    assert readback_digests("ghcr.io/lvos04/mediaguard", "1.2.2", None, other) == []


def test_opslag_naar_dataset_en_ixvolume() -> None:
    datasets = [
        {"naam": "p", "mountpoint": "/mnt/p"},
        {"naam": "p/apps", "mountpoint": "/mnt/p/apps"},
    ]
    app = {
        "opslag": [
            {"bron": "/mnt/p/apps/mg/config", "doel": "/config", "type": "bind"},
            {"bron": "/mnt/.ix-apps/app_mounts/x/data", "doel": "/data", "type": "bind"},
            {"bron": "/var/run/x", "doel": "/x", "type": "bind"},
        ]
    }
    out = storage(app, datasets)
    assert [o["dataset"] for o in out] == ["p/apps", None, None]
    assert [o["soort"] for o in out] == ["hostpad", "ixvolume", "overig"]


def _row(**kw: Any) -> Any:
    base = {"portals": [], "poorten": [], "app_id": None}
    base.update(kw)
    return SimpleNamespace(**base)


def test_deep_link_alleen_met_d03_en_uit_portal_of_hostpoort() -> None:
    row = _row(portals=[{"naam": "Web UI", "schema": "http", "poort": 30101, "pad": "/"}])
    assert deep_link(row, None) == {"url": None, "reden": "nas_adres_onbekend"}
    assert deep_link(row, "192.0.2.10")["url"] == "http://192.0.2.10:30101/"
    ports = [
        {"container_poort": 38989, "host_poort": 38989, "protocol": "tcp"},
        {"container_poort": 30080, "host_poort": 31080, "protocol": "tcp"},
    ]
    assert deep_link(_row(app_id="mediaguard", poorten=ports), "nas.lan")["url"] == "http://nas.lan:31080/"
    assert deep_link(_row(poorten=[]), "nas.lan")["reden"] == "geen_tcp_hostpoort"
    assert deep_link(_row(poorten=ports), "2001:db8::1")["url"] == "http://[2001:db8::1]:38989/"


def test_profielen_hebben_geldige_typen_en_bestaande_documentatie() -> None:
    for p in PROFILES.values():
        assert p.adapter in ADAPTER_TYPES and p.soort in SOORTEN
        if p.documentatie:
            assert (REPO / p.documentatie).is_file(), p.documentatie
    assert profile_for("bestaat-niet").adapter == "onbekend"
    assert profile_for(None).soort == "onbekend"
    # Bestaande apps met eigen taken worden nooit groen zonder binnenkant-controle.
    for key in ("mediaguard", "media-source-optimizer", "my_house", "home-control-hub", "ai-server-manager"):
        assert PROFILES[key].binnenkant_vereist


# ------------------------------------------------------------------ gezondheidsmodel
def C(soort: str, status: str, age_s: float = 0, reason: str | None = None) -> Component:
    return Component(
        soort,
        f"test:{soort}",
        status,
        reason,
        NOW - timedelta(seconds=age_s),
        geldig_tot=NOW + timedelta(seconds=30),
        bevestigd_op=NOW - timedelta(seconds=age_s),
    )


def _ev(comps: list[Component], vereist: bool = False, bron: str | None = None, aanwezig: bool = True) -> Any:
    return evaluate(comps, aanwezig=aanwezig, binnenkant_vereist=vereist, binnenkant_bron=bron, now=NOW)


def test_truenas_running_alleen_is_nooit_gezond() -> None:
    r = _ev([C("truenas", "healthy")])
    assert r["status"] == "unknown" and r["reason_code"] == "geen_gezondheidsbron"


def test_buitenkant_gezond_is_gezond_zonder_binnenkant_eis() -> None:
    assert _ev([C("truenas", "healthy"), C("buitenkant", "healthy")])["status"] == "healthy"


def test_200_zonder_jobs_is_degraded_en_zonder_binnenkant_onbekend() -> None:
    """B09-002: app die 200 geeft maar geen jobs uitvoert → degraded; zonder binnenkant-controle nooit groen."""
    stil = C("binnenkant", "degraded", reason="jobs_staan_stil")
    r = _ev([C("truenas", "healthy"), C("buitenkant", "healthy"), stil])
    assert r["status"] == "degraded" and r["reason_code"] == "jobs_staan_stil"
    r = _ev([C("truenas", "healthy"), C("buitenkant", "healthy")], vereist=True, bron="heartbeat_of_connector")
    assert r["status"] == "unknown" and r["reason_code"] == "binnenkant_ontbreekt"
    r = _ev([C("truenas", "healthy"), C("buitenkant", "healthy")], vereist=True, bron="adapter_p3")
    assert r["status"] == "unknown" and r["reason_code"] == "adapter_niet_gekoppeld"
    ok = [C("truenas", "healthy"), C("buitenkant", "healthy"), C("binnenkant", "healthy")]
    assert _ev(ok, vereist=True, bron="heartbeat_of_connector")["status"] == "healthy"


def test_down_wint_en_verdwenen_is_onbekend() -> None:
    r = _ev([C("truenas", "down", reason="app_gestopt"), C("buitenkant", "healthy")])
    assert r["status"] == "down" and r["oorzaak"] == "test:truenas"
    assert _ev([C("buitenkant", "healthy")], aanwezig=False)["reason_code"] == "niet_meer_in_inventaris"


def test_verouderde_component_is_onbekend_nooit_laatst_bekend() -> None:
    old = freshen(C("buitenkant", "healthy", age_s=600), ttl_seconds=300, now=NOW)
    # Contract 1.3 §6.2: verouderd = unknown met reason_code meting_verouderd; de oude waarde alleen "laatst bekend".
    assert (old.status, old.reason_code, old.extra["laatste_status"]) == ("unknown", "meting_verouderd", "healthy")
    fresh = freshen(C("buitenkant", "healthy", age_s=10), ttl_seconds=300, now=NOW)
    assert fresh.status == "healthy"
    r = _ev([C("truenas", "healthy"), old])
    assert r["status"] == "unknown" and r["reason_code"] == "meting_verouderd"
    # Elke gekoppelde bron moet vers zijn, ook als een tweede monitor nog gezond is.
    assert _ev([C("truenas", "healthy"), old, C("buitenkant", "healthy")])["status"] == "unknown"


@pytest.mark.parametrize("grens", [None, NOW - timedelta(microseconds=1), NOW.replace(tzinfo=None)])
def test_ontbrekende_of_ongeldige_bronvervalgrens(grens: datetime | None) -> None:
    monitor = Component("buitenkant", "monitor", "healthy", None, NOW, geldig_tot=grens)
    resultaat = _ev([C("truenas", "healthy"), monitor])
    assert resultaat["status"] == "unknown"
    assert resultaat["componenten"][1]["laatste_status"] == "healthy"


@pytest.mark.parametrize(
    ("buitenstatus", "adapterstatus", "verwacht"),
    [
        (None, "healthy", "healthy"),
        ("healthy", "healthy", "healthy"),
        ("healthy", "unknown", "unknown"),
        ("unknown", "healthy", "unknown"),
        ("degraded", "unknown", "degraded"),
        ("down", "degraded", "down"),
    ],
)
def test_samenstelling_adapterprofiel(buitenstatus: str | None, adapterstatus: str, verwacht: str) -> None:
    adapter = Component(
        "binnenkant",
        "adapter_p3",
        adapterstatus,
        None,
        NOW - timedelta(seconds=30),
        geldig_tot=NOW + timedelta(seconds=20),
        bevestigd_op=NOW,
    )
    comps = [C("truenas", "healthy", age_s=10), adapter]
    if buitenstatus is not None:
        comps.append(C("buitenkant", buitenstatus, age_s=20))
    assert _ev(comps, vereist=True, bron="adapter_p3")["status"] == verwacht
    if verwacht == "healthy":
        assert _ev(comps, vereist=True, bron="adapter_p3")["observed_at"] == "2026-11-09T11:59:30Z"


def test_onbekende_adapter_wint_van_andere_binnenkant_en_behoudt_meettijd() -> None:
    adapter = Component("binnenkant", "adapter_p3", "unknown", "meting_verouderd", NOW - timedelta(seconds=901))
    r = _ev([C("truenas", "healthy"), C("binnenkant", "healthy"), adapter], vereist=True, bron="adapter_p3")
    assert (r["status"], r["reason_code"], r["observed_at"]) == ("unknown", "meting_verouderd", "2026-11-09T11:44:59Z")


def test_gewijzigde_serveridentiteit_blokkeert_toeschrijving_van_crash() -> None:
    adapter = Component("binnenkant", "adapter_p3", "unknown", "bron_identiteit_gewijzigd", NOW)
    r = _ev([C("truenas", "down", reason="app_gecrasht"), C("buitenkant", "healthy"), adapter], True, "adapter_p3")
    assert (r["status"], r["reason_code"]) == ("unknown", "bron_identiteit_gewijzigd")
    assert all(c["status"] == "unknown" for c in r["componenten"])


def test_adapter_zonder_meettijd_behoudt_bij_offline_inventaris_de_laatst_bekende_inventaristijd() -> None:
    inventory = C("truenas", "unknown", age_s=900, reason="inventaris_verouderd")
    adapter = Component("binnenkant", "adapter_p3", "unknown", "adapter_niet_gekoppeld", None)
    r = _ev([inventory, adapter], vereist=True, bron="adapter_p3")
    assert (r["status"], r["reason_code"], r["observed_at"]) == (
        "unknown",
        "adapter_niet_gekoppeld",
        "2026-11-09T11:45:00Z",
    )
    assert r["componenten"][1]["observed_at"] is None


@pytest.mark.parametrize(
    ("stamp", "status", "reason"),
    [
        (NOW.isoformat(), "healthy", None),
        ((NOW - timedelta(seconds=301)).isoformat(), "unknown", "meting_verouderd"),
        ((NOW + timedelta(seconds=1)).isoformat(), "unknown", "meettijd_onbekend"),
        (None, "unknown", "meettijd_onbekend"),
        (NOW.replace(tzinfo=None).isoformat(), "unknown", "meettijd_onbekend"),
        ("geen tijdstip", "unknown", "meting_onbekend"),
    ],
)
def test_versheid_van_opgeslagen_adaptermeting(stamp: str | None, status: str, reason: str | None) -> None:
    link = AdapterLink(
        app_id="my_house",
        my_house_checks=[
            {"key": "database", "state": "ok", "observed_at": stamp, "max_age_s": 300},
            {
                "key": "worker",
                "state": "ok",
                "observed_at": NOW.isoformat(),
                "worker_observed_at": NOW.isoformat(),
                "max_age_s": 300,
            },
        ],
    )
    reading = stored_health(link, NOW, bound=True)
    assert (reading.status, reading.reason_code) == (status, reason)
    if reason == "meting_verouderd":
        assert reading.observed_at == NOW - timedelta(seconds=301)
        assert reading.laatste_status == "healthy"


def test_oudste_bronmeettijd_en_eerste_vervalgrens_zijn_onafhankelijk() -> None:
    oud = NOW - timedelta(seconds=60)
    link = AdapterLink(
        app_id="my_house",
        my_house_checks=[
            {"key": "database", "state": "ok", "observed_at": oud.isoformat(), "max_age_s": 900},
            {
                "key": "worker",
                "state": "ok",
                "observed_at": NOW.isoformat(),
                "worker_observed_at": NOW.isoformat(),
                "max_age_s": 120,
            },
        ],
    )
    meting = stored_health(link, NOW, bound=True)
    assert (meting.status, meting.observed_at, meting.geldig_tot) == ("healthy", oud, NOW + timedelta(seconds=120))
    link.my_house_expires_at = NOW + timedelta(seconds=10)
    assert stored_health(link, NOW, bound=True).geldig_tot == link.my_house_expires_at
    assert stored_health(link, link.my_house_expires_at, bound=True).status == "unknown"


@pytest.mark.parametrize("tijd", [None, NOW + timedelta(seconds=1), NOW.replace(tzinfo=None)])
def test_ongeldige_brontijd_geeft_geen_actuele_meting(tijd: datetime | None) -> None:
    meting = freshen(Component("buitenkant", "test", "healthy", None, tijd), ttl_seconds=300, now=NOW)
    assert (meting.status, meting.observed_at, meting.geldig_tot) == ("unknown", None, None)


@pytest.mark.parametrize(
    ("app_id", "reason"),
    [("mediaguard", "geen_alleen_lezen_bron"), ("media-source-optimizer", "capability_unavailable")],
)
def test_openbare_bereikbaarheid_is_geen_binnenkantmeting(app_id: str, reason: str) -> None:
    link = AdapterLink(app_id=app_id, laatste_status="healthy", observed_at=NOW)
    reading = stored_health(link, NOW, bound=True)
    assert (reading.status, reading.reason_code, reading.observed_at) == ("unknown", reason, None)


def test_statuswaarde_voor_tijdreeks() -> None:
    assert [status_value(s) for s in ("healthy", "degraded", "down", "unknown")] == [1.0, 0.5, 0.0, None]


# ------------------------------------------------------------------ uitgaande adressen
@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("ftp://nas:21", "adres_ongeldig"),
        ("http://user:pw@nas:3001", "adres_ongeldig"),
        ("http://nas:3001/?x=1", "adres_ongeldig"),
        ("http://127.0.0.1:3001", "adres_niet_toegestaan"),
        ("http://localhost:3001", "adres_niet_toegestaan"),
        ("http://169.254.169.254", "adres_niet_toegestaan"),
        ("http://[fe80::1]:80", "adres_niet_toegestaan"),
        ("http://0.0.0.0:80", "adres_niet_toegestaan"),
        # Contract 1.3 §3.2: alleen canonieke IP-vormen; IPv6 alleen tussen [].
        ("http://127.1:3001", "adres_ongeldig"),
        ("http://2130706433", "adres_ongeldig"),
        ("http://0x7f000001", "adres_ongeldig"),
        ("http://010.0.0.1", "adres_ongeldig"),
        ("http://0", "adres_ongeldig"),
        ("http://localhost.:3001", "adres_niet_toegestaan"),
        ("http://[::ffff:127.0.0.1]:80", "adres_niet_toegestaan"),
        ("http://[fe80::1%25eth0]", "adres_ongeldig"),
    ],
)
def test_uitgaande_adressen_streng(url: str, reason: str) -> None:
    with pytest.raises(OutboundError) as e:
        validate_base_url(url)
    assert e.value.reason == reason


def test_uitgaand_adres_toegestaan_en_loopback_alleen_met_vlag() -> None:
    assert validate_base_url("http://192.0.2.10:3001/") == "http://192.0.2.10:3001"
    assert validate_base_url("https://kuma.lan/status") == "https://kuma.lan/status"
    assert validate_base_url("http://127.0.0.1:3001", allow_loopback=True) == "http://127.0.0.1:3001"
