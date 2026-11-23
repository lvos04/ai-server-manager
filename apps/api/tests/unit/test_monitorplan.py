"""Monitorplan per app (C1.3-ASM-20, contract 1.3 §9): witte lijst van ``healthcheck.monitor`` en hostpoortkeuze."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from hub.monitoring.monitorplan import _hostpoort, normaliseer, uit_manifest

SHA = "sha256:" + "b" * 64
MON = {"pad": "/health", "verwachte_status": 200, "timeout_s": 5, "interval_s": 60}


def _manifest(monitor: Any = MON, port: Any = "web", ports: Any = None) -> dict[str, Any]:
    hc: dict[str, Any] = {"type": "http", "path": "/health", "port": port}
    if monitor is not None:
        hc["monitor"] = monitor
    if ports is None:
        ports = [{"name": "web", "container_port": 8080, "host_port": {"param": "host_port"}, "protocol": "tcp"}]
    return {"healthcheck": hc, "network": {"ports": ports}}


def test_geldig_monitorblok_uit_manifest() -> None:
    blok = uit_manifest(_manifest(), SHA)
    assert blok == {
        "status": "ok",
        "monitor": MON,
        "container_poort": 8080,
        "host_poort": None,
        "manifest_sha256": SHA,
    }
    assert normaliseer(blok) == blok


def test_manifest_zonder_monitor_geeft_ontbreekt() -> None:
    assert uit_manifest(_manifest(monitor=None), SHA)["status"] == "ontbreekt"
    assert uit_manifest({}, SHA)["status"] == "ontbreekt"


@pytest.mark.parametrize(
    "monitor",
    [
        {**MON, "verwachte_status": True},  # een boolean is geen getal
        {**MON, "verwachte_status": "200"},
        {**MON, "timeout_s": 0},
        {**MON, "interval_s": 5.0},
        {**MON, "pad": "health"},
        {**MON, "pad": "/a b"},
        {**MON, "extra": 1},
        {k: v for k, v in MON.items() if k != "pad"},
        "geen-object",
    ],
)
def test_ongeldige_monitor_wordt_geweigerd(monitor: Any) -> None:
    assert uit_manifest(_manifest(monitor=monitor), SHA)["status"] == "ongeldig"


def test_poort_moet_eenduidig_zijn() -> None:
    twee = [
        {"name": "web", "container_port": 8080, "host_port": 30080, "protocol": "tcp"},
        {"name": "api", "container_port": 9090, "host_port": 30090, "protocol": "tcp"},
    ]
    assert uit_manifest(_manifest(port=None, ports=twee), SHA)["status"] == "ongeldig"
    assert uit_manifest(_manifest(port="weg", ports=twee), SHA)["status"] == "ongeldig"
    blok = uit_manifest(_manifest(port="api", ports=twee), SHA)
    assert (blok["container_poort"], blok["host_poort"]) == (9090, 30090)


def test_opgeslagen_blok_wordt_bij_lezen_opnieuw_gecontroleerd() -> None:
    goed = uit_manifest(_manifest(), SHA)
    assert normaliseer({**goed, "monitor": {**MON, "verwachte_status": True}}) is None
    assert normaliseer({**goed, "host_poort": "30080"}) is None
    assert normaliseer({**goed, "status": "ontbreekt"}) is None
    assert normaliseer({**goed, "extra": "genegeerd"}) == goed  # alleen de witte lijst komt terug


@pytest.mark.parametrize("pad", ["/health?weergave=proef", "/health#proef", "/health?", "/health#", "/health\n"])
def test_alleen_monitorpad_bij_inname_en_herlezing(pad: str) -> None:
    monitor = {**MON, "pad": pad}
    assert uit_manifest(_manifest(monitor=monitor), SHA)["status"] == "ongeldig"
    assert normaliseer({**uit_manifest(_manifest(), SHA), "monitor": monitor}) is None


@pytest.mark.parametrize("sha", [None, "", "proef", "sha256:" + "z" * 64])
def test_monitor_zonder_geldige_manifesthash_is_onbruikbaar(sha: str | None) -> None:
    assert normaliseer({**uit_manifest(_manifest(), SHA), "manifest_sha256": sha}) is None


def _row(*poorten: tuple[int | None, int | None, str]) -> Any:
    return SimpleNamespace(poorten=[{"container_poort": c, "host_poort": h, "protocol": p} for c, h, p in poorten])


def test_hostpoort_uit_de_meting() -> None:
    blok = normaliseer(uit_manifest(_manifest(), SHA))
    assert blok is not None
    assert _hostpoort(_row((8080, 30080, "tcp"), (8080, 30080, "udp")), blok) == 30080
    assert _hostpoort(_row((8080, 30080, "tcp"), (8080, 30081, "tcp")), blok) is None  # niet eenduidig
    assert _hostpoort(_row((9090, 30090, "tcp")), blok) is None
    assert _hostpoort(_row(), blok) is None
    vast = {**blok, "host_poort": 30090}
    assert _hostpoort(_row((9090, 30090, "tcp")), vast) == 30090
    zelfde = {**blok, "container_poort": "same_as_host"}
    assert _hostpoort(_row((30100, 30100, "tcp"), (80, 30080, "tcp")), zelfde) == 30100
