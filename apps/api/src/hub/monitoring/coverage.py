"""Meetdekking (B09-001): welke bron welke metriek levert, wat er nu echt binnenkomt en waar de hiaten zitten.

Twee lagen per (metriek, bron):
- ``kan_leveren``: bronwaarneming uit de broncode (TrueNAS-middleware TS-25.10.8, Beszel v0.21.1, Uptime Kuma 2.5.9) —
  ``ja``/``nee``/``afhankelijk`` met toelichting; **NIET GEVALIDEERD** op de NAS van de gebruiker.
- ``levert``: gemeten — er is een verse reeks van die bron (binnen de TTL) → ``true``; bron gekoppeld maar niets vers →
  ``false``; bron niet gekoppeld → ``null``.
Een metriek zonder enige verse bron is een **hiaat** (met reden en eventueel alternatief). GPU-metrieken staan per GPU
(PCI-slot). Gezondheid per app telt hoeveel apps een verse buiten- en binnenkant-controle hebben.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.catalog.discovery import is_inventory_fresh
from hub.catalog.profiles import profile_for
from hub.config import Settings
from hub.inventory.store import kind_state
from hub.models import CatalogApp, MetricSeries, MonitorSource, PeriodicTask, VaultSecret
from hub.monitoring.appstatus import app_health
from hub.timeutil import iso, utcnow
from hub.truenas.connection import API_KEY_REF, current_target

TRUENAS_RT = "truenas.reporting.realtime"
TRUENAS_INV = "truenas.pool.query"


@dataclass(frozen=True)
class Cap:
    bron: str  # truenas_realtime | truenas_inventaris | beszel
    kan: str  # ja | nee | afhankelijk
    toelichting: str


@dataclass(frozen=True)
class Entry:
    metriek: str
    titel: str
    eenheid: str
    onderwerp: str  # nas | pool | gpu | interface
    caps: tuple[Cap, ...]
    alternatief: str | None = None


_RT = "truenas_realtime"
_INV = "truenas_inventaris"
_BES = "beszel"
NAS_ENTRIES: tuple[Entry, ...] = (
    Entry("cpu.gebruik", "CPU-gebruik", "%", "nas", (Cap(_RT, "ja", "cpu.cpu.usage"), Cap(_BES, "ja", "stats.cpu"))),
    Entry(
        "cpu.temperatuur",
        "CPU-temperatuur",
        "°C",
        "nas",
        (
            Cap(_RT, "afhankelijk", "cpu.cpu.temp; None als TrueNAS geen sensor heeft"),
            Cap(_BES, "afhankelijk", "stats.t (coretemp/k10temp-sensor) als de agent sensoren ziet"),
        ),
    ),
    Entry(
        "geheugen.gebruikt",
        "Geheugen in gebruik",
        "B",
        "nas",
        (Cap(_RT, "ja", "physical_memory_total − available"), Cap(_BES, "ja", "stats.mem[1]")),
    ),
    Entry(
        "zfs.arc",
        "ZFS ARC",
        "B",
        "nas",
        (Cap(_RT, "ja", "memory.arc_size"), Cap(_BES, "afhankelijk", "stats.mem[3] als de agent ZFS ziet")),
    ),
    Entry(
        "schijf.lezen",
        "Schijf lezen",
        "B/s",
        "nas",
        (Cap(_RT, "ja", "disks.read_bytes"), Cap(_BES, "ja", "stats.dio[0]")),
    ),
    Entry(
        "schijf.schrijven",
        "Schijf schrijven",
        "B/s",
        "nas",
        (Cap(_RT, "ja", "disks.write_bytes"), Cap(_BES, "ja", "stats.dio[1]")),
    ),
    Entry(
        "netwerk.ontvangen",
        "Netwerk in (totaal)",
        "B/s",
        "nas",
        (
            Cap(_RT, "afhankelijk", "alleen bij precies één actieve interface (geen dubbeltelling)"),
            Cap(_BES, "ja", "stats.b[1]"),
        ),
    ),
    Entry(
        "pool.gebruik",
        "Poolgebruik",
        "%",
        "pool",
        (
            Cap(_INV, "ja", "pool.query allocated/size"),
            Cap(_BES, "afhankelijk", "stats.z (niet gebruikt: TrueNAS is leidend)"),
        ),
    ),
    Entry("pool.gezond", "Poolgezondheid", "status", "pool", (Cap(_INV, "ja", "pool.query healthy/status"),)),
    Entry(
        "schijf.temperatuur",
        "Schijftemperatuur",
        "°C",
        "nas",
        (Cap(_RT, "nee", "niet in reporting.realtime; disk.temperatures wordt in P1 niet gelezen"),),
        alternatief="disk.temperatures (REPORTING_READ) in een volgende fase; schijfidentiteit op serienummer.",
    ),
    Entry(
        "docker.containers",
        "Container-CPU/geheugen per app",
        "%",
        "nas",
        (Cap(_BES, "afhankelijk", "container_stats-collectie (niet gelezen in P1)"),),
        alternatief="Beszel container_stats of TrueNAS app.stats (event) in een volgende fase.",
    ),
)
GPU_ENTRIES: tuple[Entry, ...] = (
    Entry(
        "gpu.gebruik",
        "GPU-gebruik",
        "%",
        "gpu",
        (
            Cap(_RT, "nee", "TrueNAS levert geen GPU-belasting"),
            Cap(_BES, "afhankelijk", "stats.g via intel_gpu_top in de agent; alleen bij eenduidige naam"),
        ),
        alternatief="Beszel-agent met intel_gpu_top (vraagt toegang tot de render-node; NIET GEVALIDEERD).",
    ),
    Entry(
        "gpu.temperatuur",
        "GPU-temperatuur",
        "°C",
        "gpu",
        (
            Cap(_RT, "nee", "geen GPU-sensoren in reporting"),
            Cap(_BES, "nee", "GPUData.Temperature staat niet in de JSON"),
        ),
        alternatief="Geen: een eigen collector vraagt render-node-/root-toegang en wordt bewust niet gebouwd.",
    ),
)


def _bron_prefix(cap: Cap, beszel_ids: list[str]) -> list[str]:
    if cap.bron == _RT:
        return [TRUENAS_RT]
    if cap.bron == _INV:
        return [TRUENAS_INV]
    return [f"beszel:{i}" for i in beszel_ids]


def compute(db: Session, settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    ttl = settings.nas_metrics_ttl_seconds
    series = list(db.scalars(select(MetricSeries).where(MetricSeries.onderwerp_type.in_(("nas", "pool", "gpu")))))
    beszel = list(db.scalars(select(MonitorSource).where(MonitorSource.soort == "beszel")))
    beszel_ids = [str(s.id) for s in beszel if s.ingeschakeld]
    target = current_target(db)
    truenas_linked = target is not None and db.scalar(select(VaultSecret.id).where(VaultSecret.ref == API_KEY_REF))
    task = db.get(PeriodicTask, "nas_meten")
    rt_reason = (task.details or {}).get("reden") if task else "nog_niet_gemeten"

    def fresh_for(metriek: str, otype: str, oid: str | None, prefixes: list[str]) -> tuple[bool, str | None]:
        cands = [
            s
            for s in series
            if s.metriek == metriek
            and s.onderwerp_type == otype
            and (oid is None or s.onderwerp_id == oid)
            and any(s.bron == p for p in prefixes)
        ]
        newest = max((s.laatste_op for s in cands if s.laatste_op), default=None)
        threshold = settings.inventory_max_age_seconds if otype == "pool" else ttl
        return newest is not None and (now - newest).total_seconds() <= threshold, iso(newest)

    def row(e: Entry, oid: str | None, label: str | None = None) -> dict[str, Any]:
        bronnen = []
        delivered = False
        for cap in e.caps:
            linked: bool | None = bool(truenas_linked) if cap.bron in (_RT, _INV) else (bool(beszel_ids) or None)
            prefixes = _bron_prefix(cap, beszel_ids)
            ok, last = fresh_for(e.metriek, e.onderwerp, oid, prefixes) if linked else (False, None)
            levert: bool | None = ok if linked else None
            delivered = delivered or bool(ok)
            reden = None
            if linked is None or linked is False:
                reden = "bron_niet_gekoppeld"
            elif not ok:
                reden = (
                    rt_reason
                    if cap.bron == _RT and rt_reason
                    else ("niet_geleverd" if cap.kan == "nee" else "geen_verse_meting")
                )
            bronnen.append(
                {
                    "bron": cap.bron,
                    "kan_leveren": cap.kan,
                    "toelichting": cap.toelichting,
                    "zekerheid": "bronwaarneming (broncode); NIET GEVALIDEERD op de NAS",
                    "gekoppeld": linked,
                    "levert": levert,
                    "laatst": last,
                    "reden": reden,
                }
            )
        return {
            "metriek": e.metriek,
            "titel": e.titel if label is None else f"{e.titel} — {label}",
            "eenheid": e.eenheid,
            "onderwerp": e.onderwerp,
            "onderwerp_id": oid,
            "gedekt": delivered,
            "hiaat": None if delivered else (e.alternatief or "Geen verse bron voor deze metriek."),
            "bronnen": bronnen,
        }

    rows: list[dict[str, Any]] = []
    pools_st = kind_state(
        db, "pools", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds
    )
    pool_names = [str(p.get("naam")) for p in pools_st.get("data") or [] if p.get("naam")]
    for e in NAS_ENTRIES:
        if e.onderwerp == "pool":
            for name in pool_names or [None]:  # type: ignore[list-item]
                rows.append(row(e, name, name))
        else:
            rows.append(row(e, "nas"))
    gpus_st = kind_state(
        db, "gpus", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds
    )
    gpus = [g for g in gpus_st.get("data") or [] if g.get("pci_slot")]
    for g in gpus:
        label = f"{g.get('herkend_als') or 'gpu'} ({g['pci_slot']})"
        for e in GPU_ENTRIES:
            rows.append(row(e, str(g["pci_slot"]), label))
    if not gpus:
        rows.append(
            {
                "metriek": "gpu.*",
                "titel": "GPU's",
                "eenheid": "",
                "onderwerp": "gpu",
                "onderwerp_id": None,
                "gedekt": False,
                "hiaat": "Geen GPU's in de inventaris (of de inventaris is niet gemeten); D08 meet de render-nodes.",
                "bronnen": [],
            }
        )

    inv = is_inventory_fresh(db, settings, now)
    apps = []
    for app in db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True)).order_by(CatalogApp.naam)):
        h = app_health(db, settings, app, inv, now)
        kinds = {c["soort"]: c for c in h["componenten"]}
        prof = profile_for(app.app_id)
        buiten = any(c["soort"] == "buitenkant" and c["status"] != "unknown" for c in h["componenten"])
        binnen = any(c["soort"] == "binnenkant" and c["status"] != "unknown" for c in h["componenten"])
        apps.append(
            {
                "id": str(app.id),
                "naam": app.naam,
                "buitenkant": buiten,
                "binnenkant": binnen,
                "binnenkant_vereist": prof.binnenkant_vereist,
                "binnenkant_bron": prof.binnenkant,
                "hiaat": None
                if (buiten or binnen) and (binnen or not prof.binnenkant_vereist)
                else h["reason_code"] or "geen_gezondheidsbron",
                "truenas": kinds.get("truenas", {}).get("status"),
            }
        )
    return {
        "metrieken": rows,
        "hiaten": [r["titel"] for r in rows if not r["gedekt"]],
        "apps": {
            "totaal": len(apps),
            "met_buitenkant": sum(1 for a in apps if a["buitenkant"]),
            "met_binnenkant": sum(1 for a in apps if a["binnenkant"]),
            "hiaten": [a for a in apps if a["hiaat"]],
        },
        "bronnen": {
            "truenas": {"gekoppeld": bool(truenas_linked), "realtime_reden": rt_reason},
            "beszel": [{"id": str(s.id), "naam": s.naam, "status": s.laatste_status or "unknown"} for s in beszel],
            "uptime_kuma": [
                {"id": str(s.id), "naam": s.naam, "status": s.laatste_status or "unknown"}
                for s in db.scalars(select(MonitorSource).where(MonitorSource.soort == "uptime_kuma"))
            ],
        },
        "zekerheid": "kan_leveren = bronwaarneming uit de broncode (NIET GEVALIDEERD op de NAS); levert = gemeten.",
        "observed_at": iso(now),
    }
