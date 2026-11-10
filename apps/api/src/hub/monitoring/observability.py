"""Observability van de NAS in één antwoord (B01-004): CPU, geheugen/ARC, GPU's, schijven, pools, netwerk.

- Alleen de TrueNAS-NAS: reeksen met onderwerp ``nas``/``pool``/``gpu``/``interface`` uit TrueNAS of het Beszel-systeem
  dat als NAS is gekoppeld; andere Beszel-systemen (mini-pc, D10) staan alleen in ``uitgesloten_systemen``.
- Per metriek: waarde + eenheid + bron + ``observed_at``. Ouder dan ``nas_metrics_ttl_seconds`` → ``unknown`` zonder
  waarde (wel ``laatst_bekend``); geen enkele bron → ``unknown`` met reden. Bronvoorkeur: TrueNAS, dan Beszel.
- GPU's op PCI-slot (stabiel), nooit op render-node; GPU-temperatuur levert geen bron → altijd ``unknown``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.inventory.store import kind_state
from hub.models import MetricSeries, MonitorSource, PeriodicTask
from hub.monitoring.alerts import BRON_VOORKEUR
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target

GEEN_GPU_TEMP = (
    "Geen bron levert de GPU-temperatuur (TrueNAS niet; Beszel stuurt hem niet mee). Een aparte collector met "
    "intel_gpu_top vraagt toegang tot de render-node en is bewust niet gebouwd (nooit privileged). "
    "Onbekend, nooit 0 °C."
)


def _priority(bron: str) -> int:
    for i, prefix in enumerate(BRON_VOORKEUR):
        if bron.startswith(prefix):
            return i
    return len(BRON_VOORKEUR)


def _bron_naam(bron: str, sources: dict[str, MonitorSource]) -> str:
    if bron.startswith("beszel:"):
        src = sources.get(bron.split(":", 1)[1])
        return f"Beszel ({src.naam})" if src else "Beszel"
    return {
        "truenas.reporting.realtime": "TrueNAS (reporting.realtime)",
        "truenas.pool.query": "TrueNAS (pool.query)",
    }.get(bron, bron)


class Picker:
    def __init__(self, db: Session, ttl: int, now: datetime) -> None:
        self.ttl, self.now = ttl, now
        self.by: dict[tuple[str, str, str], list[MetricSeries]] = {}
        rows = db.scalars(
            select(MetricSeries).where(MetricSeries.onderwerp_type.in_(("nas", "pool", "gpu", "interface")))
        )
        for s in rows:
            self.by.setdefault((s.onderwerp_type, s.onderwerp_id, s.metriek), []).append(s)
        self.sources = {str(s.id): s for s in db.scalars(select(MonitorSource))}

    def fresh(self, s: MetricSeries) -> bool:
        return s.laatste_op is not None and (self.now - s.laatste_op).total_seconds() <= self.ttl

    def metric(self, otype: str, oid: str, metriek: str, eenheid: str) -> dict[str, Any]:
        cands = sorted(self.by.get((otype, oid, metriek), []), key=lambda s: _priority(s.bron))
        fresh = [s for s in cands if self.fresh(s)]
        if fresh:
            s = fresh[0]
            return {
                "waarde": s.laatste_waarde,
                "eenheid": s.eenheid,
                "bron": _bron_naam(s.bron, self.sources),
                "bron_id": s.bron,
                "observed_at": iso(s.laatste_op),
                "status": "ok",
                "reden": None,
                "reeks_id": s.id,
                "alternatieven": [_bron_naam(o.bron, self.sources) for o in fresh[1:]],
            }
        last = max(cands, key=lambda s: s.laatste_op.timestamp() if s.laatste_op else 0, default=None)
        return {
            "waarde": None,
            "eenheid": eenheid,
            "bron": None,
            "observed_at": None,
            "status": "unknown",
            "reden": "verouderd" if last is not None else "geen_bron",
            "reason_code": "meting_verouderd" if last is not None else "geen_bron",
            "laatst_bekend": None
            if last is None
            else {
                "waarde": last.laatste_waarde,
                "observed_at": iso(last.laatste_op),
                "bron": _bron_naam(last.bron, self.sources),
            },
        }

    def interfaces(self) -> list[str]:
        return sorted({oid for (otype, oid, _m) in self.by if otype == "interface"})


def nas_view(db: Session, settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    pick = Picker(db, settings.nas_metrics_ttl_seconds, now)
    target = current_target(db)
    url = target.url if target else None
    ttl = settings.inventory_max_age_seconds

    def inv(kind: str) -> dict[str, Any]:
        return kind_state(db, kind, target=url, ttl_seconds=ttl, now=now)

    system, pools, gpus, disks = inv("system"), inv("pools"), inv("gpus"), inv("disks")
    info = (system.get("data") or {}).get("info") or {} if isinstance(system.get("data"), dict) else {}
    task = db.get(PeriodicTask, "nas_meten")
    realtime = {
        "laatste_poging": iso(task.laatst_klaar) if task else None,
        "meting": (task.details or {}).get("meting", "unknown") if task else "unknown",
        "reden": (task.details or {}).get("reden") if task else "nog_niet_gemeten",
        "threads": (task.details or {}).get("threads") if task else None,
    }
    gpu_items = []
    for g in gpus.get("data") or []:
        slot = str(g.get("pci_slot") or "")
        gpu_items.append(
            {
                "pci_slot": slot,
                "beschrijving": g.get("beschrijving"),
                "herkend_als": g.get("herkend_als"),
                "gebruik": pick.metric("gpu", slot, "gpu.gebruik", "%"),
                "vermogen": pick.metric("gpu", slot, "gpu.vermogen", "W"),
                "temperatuur": {
                    "waarde": None,
                    "eenheid": "°C",
                    "status": "unknown",
                    "reden": "niet_geleverd",
                    "toelichting": GEEN_GPU_TEMP,
                },
                "identiteit": "PCI-slot uit app.gpu_choices (stabiel); nooit de render-node",
            }
        )
    pool_items = []
    for p in pools.get("data") or []:
        name = str(p.get("naam") or "")
        pool_items.append(
            {
                "naam": name,
                "status": p.get("status") if pools["status"] == "ok" else None,
                "gezond": p.get("gezond") if pools["status"] == "ok" else None,
                "gebruik": pick.metric("pool", name, "pool.gebruik", "%"),
                "vrij": pick.metric("pool", name, "pool.vrij", "B"),
            }
        )
    excluded: list[dict[str, Any]] = []
    for src in pick.sources.values():
        if src.soort == "beszel":
            for sys in (src.laatste_detail or {}).get("systemen") or []:
                if sys.get("rol") == "uitgesloten":
                    excluded.append(
                        {"bron": f"Beszel ({src.naam})", "naam": sys.get("naam"), "reden": sys.get("reden")}
                    )
    return {
        "nas": {
            "hostnaam": info.get("hostnaam"),
            "versie": (system.get("data") or {}).get("versie") if isinstance(system.get("data"), dict) else None,
            "cpu_model": info.get("cpu"),
            "inventaris": {"status": system.get("status"), "observed_at": system.get("observed_at")},
        },
        "cpu": {
            "gebruik": pick.metric("nas", "nas", "cpu.gebruik", "%"),
            "temperatuur": pick.metric("nas", "nas", "cpu.temperatuur", "°C"),
            "threads": realtime["threads"],
        },
        "geheugen": {
            "totaal": pick.metric("nas", "nas", "geheugen.totaal", "B"),
            "gebruikt": pick.metric("nas", "nas", "geheugen.gebruikt", "B"),
            "beschikbaar_pct": pick.metric("nas", "nas", "geheugen.beschikbaar_pct", "%"),
            "zfs_arc": pick.metric("nas", "nas", "zfs.arc", "B"),
            "zfs_arc_treffers": pick.metric("nas", "nas", "zfs.arc_treffers", "%"),
        },
        "schijven": {
            "lezen": pick.metric("nas", "nas", "schijf.lezen", "B/s"),
            "schrijven": pick.metric("nas", "nas", "schijf.schrijven", "B/s"),
            "bezet": pick.metric("nas", "nas", "schijf.bezet", "%"),
            "aantal": len(disks.get("data") or []) if disks.get("status") == "ok" else None,
        },
        "pools": pool_items,
        "netwerk": {
            "totaal": {
                "ontvangen": pick.metric("nas", "nas", "netwerk.ontvangen", "B/s"),
                "verzonden": pick.metric("nas", "nas", "netwerk.verzonden", "B/s"),
                "toelichting": "TrueNAS: alleen bij precies één actieve interface (anders dubbeltelling door bridges/"
                "VLAN's); Beszel: totaal volgens de agent.",
            },
            "interfaces": [
                {
                    "naam": name,
                    "link": pick.metric("interface", name, "netwerk.link", "status"),
                    "snelheid": pick.metric("interface", name, "netwerk.snelheid", "Mb/s"),
                    "ontvangen": pick.metric("interface", name, "netwerk.ontvangen", "B/s"),
                    "verzonden": pick.metric("interface", name, "netwerk.verzonden", "B/s"),
                }
                for name in pick.interfaces()
            ],
        },
        "gpus": gpu_items,
        "uitgesloten_systemen": excluded,
        "realtime": realtime,
        "ttl_seconden": settings.nas_metrics_ttl_seconds,
        "alleen_truenas": True,
        "observed_at": iso(now),
    }
