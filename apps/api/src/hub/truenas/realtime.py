"""Live NAS-metingen uit TrueNAS (B01-004): event source ``reporting.realtime`` (één bericht per poll).

Bronwaarneming in de middleware TS-25.10.8 (commit 29ed02b8, ``plugins/reporting/events.py`` en
``realtime_reporting/*``), NIET GEVALIDEERD op een echte NAS:
- ``cpu``: ``{"cpu": {"usage", "temp"}, "cpu0": {...}, …}`` (``temp`` is ``None`` als er geen sensor is);
- ``memory``: ``physical_memory_total``, ``physical_memory_available``, ``arc_size`` (bytes);
- ``disks``: ``read_bytes``, ``write_bytes`` (B/s), ``busy`` (%), samengeteld over alle schijven;
- ``interfaces``: per interface ``link_state``, ``speed`` (Mb/s), ``received_bytes_rate``/``sent_bytes_rate`` (B/s);
- ``zfs``: ARC-statistieken (o.a. ``demand_data_hit_percentage``).
Alleen de NAS zelf (TrueNAS); de mini-pc komt hier per definitie niet in voor. Een ontbrekende of ongeldige waarde
wordt geen meting (nooit 0 voor onbekend; temperatuur ≤ 0 °C of > 150 °C is ongeldig).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hub.monitoring.timeseries import Sample
from hub.timeutil import utcnow
from hub.truenas.client import TLSSettings, TrueNASClient, TrueNASError

BRON = "truenas.reporting.realtime"
EVENT = "reporting.realtime"
CPU_CORE = re.compile(r"^cpu\d+$")


@dataclass
class RealtimeResult:
    status: str  # ok | unknown
    reason_code: str | None = None
    detail: str = ""
    observed_at: datetime | None = None
    samples: list[Sample] = field(default_factory=list)
    threads: int | None = None
    interfaces: list[dict[str, Any]] = field(default_factory=list)


def _d(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    f = float(v)
    return f if f == f and abs(f) != float("inf") else None


def _temp(v: Any) -> float | None:
    t = _num(v)
    return t if t is not None and 0 < t <= 150 else None


def normalize(fields: dict[str, Any], ts: datetime) -> RealtimeResult:
    out: list[Sample] = []

    def add(metriek: str, eenheid: str, v: float | None, onderwerp: tuple[str, str] = ("nas", "nas")) -> None:
        if v is not None:
            out.append(Sample(onderwerp[0], onderwerp[1], metriek, eenheid, BRON, ts, v))

    res = RealtimeResult(status="ok", observed_at=ts)
    cpu = _d(fields.get("cpu"))
    agg = cpu.get("cpu") if isinstance(cpu.get("cpu"), dict) else cpu.get("average")
    if isinstance(agg, dict):
        usage = _num(agg.get("usage"))
        add("cpu.gebruik", "%", usage if usage is not None and 0 <= usage <= 100 else None)
        add("cpu.temperatuur", "°C", _temp(agg.get("temp")))
    cores = [k for k in cpu if CPU_CORE.match(str(k))]
    res.threads = len(cores) or None
    mem = _d(fields.get("memory"))
    total, avail = _num(mem.get("physical_memory_total")), _num(mem.get("physical_memory_available"))
    if total and avail is not None and 0 <= avail <= total:
        add("geheugen.totaal", "B", total)
        add("geheugen.gebruikt", "B", total - avail)
        add("geheugen.beschikbaar_pct", "%", avail / total * 100)
    arc = _num(mem.get("arc_size"))
    add("zfs.arc", "B", arc if arc else None)
    disks = _d(fields.get("disks"))
    add("schijf.lezen", "B/s", _num(disks.get("read_bytes")))
    add("schijf.schrijven", "B/s", _num(disks.get("write_bytes")))
    busy = _num(disks.get("busy"))
    add("schijf.bezet", "%", busy if busy is not None and 0 <= busy <= 100 else None)
    zfs = _d(fields.get("zfs"))
    hit = _num(zfs.get("demand_data_hit_percentage"))
    add("zfs.arc_treffers", "%", hit if hit is not None and 0 <= hit <= 100 else None)
    up: list[str] = []
    ifaces = _d(fields.get("interfaces"))
    for name, d in sorted(ifaces.items()):
        if not isinstance(d, dict) or not re.match(r"^[A-Za-z0-9_.:-]{1,32}$", str(name)):
            continue
        link_up = d.get("link_state") == "LINK_STATE_UP"
        onderwerp = ("interface", str(name))
        add("netwerk.link", "status", 1.0 if link_up else 0.0, onderwerp)
        speed = _num(d.get("speed"))
        add("netwerk.snelheid", "Mb/s", speed if speed else None, onderwerp)
        if link_up:
            up.append(str(name))
            add("netwerk.ontvangen", "B/s", _num(d.get("received_bytes_rate")), onderwerp)
            add("netwerk.verzonden", "B/s", _num(d.get("sent_bytes_rate")), onderwerp)
        res.interfaces.append({"naam": str(name), "link": "up" if link_up else "down", "snelheid_mbps": speed})
    if len(up) == 1:
        # Totaal alleen bij precies één actieve interface: bij meer (bridge, VLAN, bond) zou optellen dubbel tellen.
        d = ifaces[up[0]]
        add("netwerk.ontvangen", "B/s", _num(d.get("received_bytes_rate")))
        add("netwerk.verzonden", "B/s", _num(d.get("sent_bytes_rate")))
    res.samples = out
    return res


async def fetch(
    url: str, api_key: str, *, tls: TLSSettings, connect_timeout: float, read_timeout: float
) -> RealtimeResult:
    try:
        client = TrueNASClient(url, api_key, tls=tls, connect_timeout=connect_timeout, read_timeout=read_timeout)
        await client.open()
    except TrueNASError as exc:
        return RealtimeResult(status="unknown", reason_code=exc.reason_code, detail=exc.detail)
    try:
        fields = await client.first_event(EVENT, read_timeout)
    except TrueNASError as exc:
        return RealtimeResult(status="unknown", reason_code=exc.reason_code, detail=exc.detail)
    finally:
        await client.close()
    return normalize(fields, utcnow())
