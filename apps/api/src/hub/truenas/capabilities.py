"""Capability-map per TrueNAS-versie.

Methodenamen verschillen per versie (bv. ``pool.snapshot.query`` sinds 25.04 vs ``zfs.snapshot.query`` ervoor). De Hub
kiest per capability de eerste kandidaat die de NAS echt aanbiedt volgens ``core.get_methods``. Lukt methode-ontdekking
niet, dan valt de map terug op een vaste versietabel en wordt dat als ``capability_source = "versietabel"`` vastgelegd.
Schrijfmethoden staan hier alleen ter informatie voor de executor (P2); de Hub roept ze nooit aan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# capability -> kandidaten in voorkeursvolgorde: (methode, standaardparameters)
READ_CAPABILITIES: dict[str, list[tuple[str, list[Any]]]] = {
    "system_version": [("system.version", [])],
    "system_info": [("system.info", [])],
    "pools": [("pool.query", [])],
    "datasets": [("pool.dataset.query", [[], {"extra": {"flat": True, "retrieve_children": True}}])],
    "apps": [("app.query", [])],  # nooit retrieve_config: de configuratie kan geheimen bevatten
    "images": [("app.image.query", [])],  # alleen tags/digests voor de digest-readback van de catalogus
    "disks": [("disk.query", [])],
    "smart": [("smart.test.results", [])],
    "gpus": [("app.gpu_choices", []), ("device.get_info", [{"type": "GPU"}])],
    "snapshot_tasks": [("pool.snapshottask.query", [])],
    "snapshots": [("pool.snapshot.query", []), ("zfs.snapshot.query", [])],
    "cloudsync": [("cloudsync.query", [])],
    "replication": [("replication.query", [])],
    "alerts": [("alert.list", [])],
    "network": [("network.general.summary", []), ("interface.query", [])],
    "key_scope": [("auth.me", [])],
    # Live metingen: event source reporting.realtime via core.subscribe (rol REPORTING_READ).
    "realtime": [("core.subscribe", [])],
}

# Alleen ter informatie (fase P2, executor): welke schrijfmethode deze versie aanbiedt.
WRITE_CAPABILITIES_INFO: dict[str, list[str]] = {
    "snapshot_create": ["pool.snapshot.create", "zfs.snapshot.create"],
    "snapshot_clone": ["pool.snapshot.clone", "zfs.snapshot.clone"],
    "app_restart": ["app.redeploy"],
    "app_create": ["app.create"],
}

# Terugvaltabel als core.get_methods niet beschikbaar is (bv. ontbrekende rechten).
_VERSION_TABLE: list[tuple[tuple[int, int], dict[str, str]]] = [
    ((25, 4), {"snapshots": "pool.snapshot.query", "gpus": "app.gpu_choices"}),
    ((24, 10), {"snapshots": "zfs.snapshot.query", "gpus": "app.gpu_choices"}),
]

_VERSION_RE = re.compile(r"(\d{2})\.(\d{1,2})(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(raw: str | None) -> tuple[int, int, int] | None:
    """``TrueNAS-SCALE-24.10.2.1`` → (24, 10, 2); ``25.04.1`` → (25, 4, 1). Onbekend → None."""
    if not raw:
        return None
    m = _VERSION_RE.search(raw)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


@dataclass
class CapabilityMap:
    source: str  # core.get_methods | versietabel | geen
    version: str | None
    methods: dict[str, str | None] = field(default_factory=dict)  # capability -> methode (None = niet beschikbaar)
    params: dict[str, list[Any]] = field(default_factory=dict)
    write_info: dict[str, str | None] = field(default_factory=dict)

    def method_for(self, capability: str) -> str | None:
        return self.methods.get(capability)

    def as_dict(self) -> dict[str, Any]:
        return {
            "bron": self.source,
            "nas_versie": self.version,
            "lezen": dict(self.methods),
            "schrijven_alleen_info_executor": dict(self.write_info),
        }


def build_capability_map(available: set[str] | None, version: str | None) -> CapabilityMap:
    if available is not None:
        cmap = CapabilityMap(source="core.get_methods", version=version)
        for cap, candidates in READ_CAPABILITIES.items():
            chosen = next(((m, p) for m, p in candidates if m in available), None)
            cmap.methods[cap] = chosen[0] if chosen else None
            if chosen:
                cmap.params[cap] = chosen[1]
        for cap, wcands in WRITE_CAPABILITIES_INFO.items():
            cmap.write_info[cap] = next((m for m in wcands if m in available), None)
        return cmap

    parsed = parse_version(version)
    cmap = CapabilityMap(source="versietabel" if parsed else "geen", version=version)
    overrides: dict[str, str] = {}
    if parsed:
        for minimum, table in _VERSION_TABLE:
            if parsed[:2] >= minimum:
                overrides = table
                break
    for cap, candidates in READ_CAPABILITIES.items():
        if not parsed:
            cmap.methods[cap] = None
            continue
        wanted = overrides.get(cap, candidates[0][0])
        chosen = next(((m, p) for m, p in candidates if m == wanted), candidates[0])
        cmap.methods[cap] = chosen[0]
        cmap.params[cap] = chosen[1]
    for cap in WRITE_CAPABILITIES_INFO:
        cmap.write_info[cap] = None
    return cmap
