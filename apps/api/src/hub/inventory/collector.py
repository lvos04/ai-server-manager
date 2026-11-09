"""Inventaris uitlezen via de alleen-lezen TrueNAS-client.

Elke soort (``kind``) krijgt een eigen resultaat met ``status`` ok/unknown en een ``reason_code``. Een fout in één soort
maakt die soort ``unknown`` en wordt nooit stil overgeslagen; een verbindingsfout maakt alle soorten ``unknown``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hub.timeutil import utcnow
from hub.truenas import normalize as norm
from hub.truenas.capabilities import CapabilityMap, build_capability_map
from hub.truenas.client import TLSSettings, TrueNASClient, TrueNASError
from hub.truenas.messages import message

ALL_KINDS: tuple[str, ...] = (
    "system",
    "pools",
    "datasets",
    "apps",
    "images",
    "disks",
    "smart",
    "gpus",
    "snapshot_tasks",
    "latest_snapshots",
    "cloudsync",
    "replication",
    "alerts",
    "network",
)

_NORMALIZERS: dict[str, Callable[[Any], Any]] = {
    "pools": norm.pools,
    "datasets": norm.datasets,
    "apps": norm.apps,
    "images": norm.images,
    "disks": norm.disks,
    "smart": norm.smart,
    "gpus": norm.gpus,
    "snapshot_tasks": norm.snapshot_tasks,
    "cloudsync": norm.cloudsync,
    "replication": norm.replication,
    "alerts": norm.alerts,
    "network": norm.network,
}


@dataclass
class KindResult:
    kind: str
    status: str  # ok | unknown
    reason_code: str | None
    message: str
    method: str | None
    data: Any
    observed_at: datetime


@dataclass
class CollectResult:
    status: str  # ok | partial | unknown
    reason_code: str | None
    target_url: str
    nas_version: str | None = None
    capabilities: CapabilityMap | None = None
    capability_error: str | None = None
    key_scope: str | None = None
    tls_mode: str | None = None
    server_fingerprint: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    kinds: list[KindResult] = field(default_factory=list)

    def kind(self, name: str) -> KindResult | None:
        return next((k for k in self.kinds if k.kind == name), None)


def _unknown(kind: str, reason: str, detail: str = "", method: str | None = None) -> KindResult:
    return KindResult(kind, "unknown", reason, detail or message(reason), method, None, utcnow())


async def collect(
    url: str,
    api_key: str,
    *,
    tls: TLSSettings,
    connect_timeout: float,
    read_timeout: float,
    kinds: tuple[str, ...] = ALL_KINDS,
) -> CollectResult:
    result = CollectResult(status="unknown", reason_code=None, target_url=url)
    try:
        client = TrueNASClient(url, api_key, tls=tls, connect_timeout=connect_timeout, read_timeout=read_timeout)
        await client.open()
    except TrueNASError as exc:
        result.reason_code = exc.reason_code
        result.error_details = {"detail": exc.detail, **exc.details}
        result.kinds = [_unknown(k, exc.reason_code, exc.detail) for k in kinds]
        return result

    try:
        result.tls_mode = client.tls_mode
        result.server_fingerprint = client.server_fingerprint

        # 1. Rechten van de key: de Hub gebruikt uitsluitend een alleen-lezen-key.
        try:
            result.key_scope = norm.key_scope(await client.call("auth.me"))
        except TrueNASError:
            result.key_scope = "onbekend"
        if result.key_scope == "schrijfrechten":
            result.reason_code = "key_too_privileged"
            result.kinds = [_unknown(k, "key_too_privileged") for k in kinds]
            return result

        # 2. Versie en methode-ontdekking.
        version: str | None = None
        version_error: TrueNASError | None = None
        try:
            raw_version = await client.call("system.version")
            version = str(raw_version) if raw_version is not None else None
        except TrueNASError as exc:
            version_error = exc
        available: set[str] | None = None
        try:
            methods = await client.call("core.get_methods")
            if isinstance(methods, dict | list):
                available = {str(m) for m in methods}
        except TrueNASError as exc:
            result.capability_error = exc.reason_code
        cmap = build_capability_map(available, version)
        result.capabilities = cmap
        result.nas_version = version

        for kind in kinds:
            if kind == "system":
                result.kinds.append(await _collect_system(client, cmap, version, version_error))
            elif kind == "latest_snapshots":
                result.kinds.append(await _collect_latest_snapshots(client, cmap, result.kind("snapshot_tasks")))
            else:
                result.kinds.append(await _collect_kind(client, cmap, kind))
    finally:
        await client.close()

    unknown = [k for k in result.kinds if k.status != "ok"]
    if not unknown:
        result.status = "ok"
    elif len(unknown) == len(result.kinds):
        result.status = "unknown"
        result.reason_code = unknown[0].reason_code
    else:
        result.status = "partial"
    return result


async def _collect_system(
    client: TrueNASClient, cmap: CapabilityMap, version: str | None, version_error: TrueNASError | None
) -> KindResult:
    info: dict[str, Any] = {}
    info_error: TrueNASError | None = None
    try:
        raw = await client.call("system.info")
        if isinstance(raw, dict):
            info = {
                "versie": norm.as_str(raw.get("version"), 128),
                "hostnaam": norm.as_str(raw.get("hostname"), 128),
                "model": norm.as_str(raw.get("system_product") or raw.get("model"), 128),
                "cpu": norm.as_str(raw.get("model"), 128),
                "cores": norm.as_num(raw.get("cores")),
                "geheugen_bytes": norm.as_num(raw.get("physmem")),
                "uptime_seconden": norm.as_num(raw.get("uptime_seconds")),
                "tijdzone": norm.as_str(raw.get("timezone"), 64),
            }
    except TrueNASError as exc:
        info_error = exc
    if version is None and version_error is not None and not info.get("versie"):
        return _unknown("system", version_error.reason_code, version_error.detail, "system.version")
    data = {"versie": version or info.get("versie"), "info": info or None, "capabilities": cmap.as_dict()}
    if info_error is not None:
        data["info_fout"] = info_error.reason_code
    return KindResult("system", "ok", None, "", "system.version", data, utcnow())


async def _collect_kind(client: TrueNASClient, cmap: CapabilityMap, kind: str) -> KindResult:
    method = cmap.method_for(kind)
    if method is None:
        return _unknown(kind, "method_unavailable", f"geen methode voor '{kind}' op deze TrueNAS-versie")
    try:
        raw = await client.call(method, cmap.params.get(kind, []))
    except TrueNASError as exc:
        return _unknown(kind, exc.reason_code, exc.detail, method)
    try:
        data = _NORMALIZERS[kind](raw)
    except Exception as exc:
        return _unknown(kind, "protocol_error", f"{method}: onverwacht antwoord ({type(exc).__name__})", method)
    return KindResult(kind, "ok", None, "", method, data, utcnow())


async def _collect_latest_snapshots(client: TrueNASClient, cmap: CapabilityMap, tasks: KindResult | None) -> KindResult:
    method = cmap.method_for("snapshots")
    if method is None:
        return _unknown("latest_snapshots", "method_unavailable", "geen snapshot-querymethode op deze versie")
    if tasks is None or tasks.status != "ok":
        reason = tasks.reason_code if tasks and tasks.reason_code else "protocol_error"
        return _unknown(
            "latest_snapshots", reason, "snapshot-taken onbekend; laatste snapshots niet te bepalen", method
        )
    per_dataset: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for ds in sorted({str(t["dataset"]) for t in tasks.data if t.get("dataset")}):
        try:
            raw = await client.call(method, [[["dataset", "=", ds]], {"order_by": ["-createtxg"], "limit": 1}])
            per_dataset[ds] = norm.latest_snapshot(raw)
        except TrueNASError as exc:
            per_dataset[ds] = None
            errors[ds] = exc.reason_code
    if errors and len(errors) == len(per_dataset):
        first = next(iter(errors.values()))
        return _unknown("latest_snapshots", first, "laatste snapshot per dataset niet leesbaar", method)
    return KindResult(
        "latest_snapshots", "ok", None, "", method, {"per_dataset": per_dataset, "fouten": errors}, utcnow()
    )


def tls_settings(pinned: str | None, extra_ca: Path | None) -> TLSSettings:
    return TLSSettings(pinned_fingerprint=pinned, extra_ca_file=extra_ca)
