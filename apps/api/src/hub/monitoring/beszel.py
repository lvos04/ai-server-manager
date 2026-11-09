"""Beszel-adapter (B09-001/002, B01-004): alleen lezen via de hub-API (PocketBase), alleen voor het NAS-systeem.

Bronwaarneming in de broncode van Beszel v0.21.1 (NIET GEVALIDEERD tegen een echte installatie):
- Aanmelden: ``POST /api/collections/users/auth-with-password`` ``{identity, password}`` → ``{token}``; daarna header
  ``Authorization: <token>``. Gebruik een Beszel-gebruiker met de rol ``readonly`` die alleen het NAS-systeem ziet.
- ``GET /api/beszel/info`` → ``{"v": versie}``; ``GET /api/collections/systems/records`` → systemen met
  ``status`` (up|down|paused|pending), ``host`` en ``info``; ``GET /api/collections/system_stats/records`` met
  ``type='1m'`` → ``stats``: ``cpu`` (%), ``mem`` [totaal, gebruikt, buff/cache, ZFS-ARC] bytes (oudere agents:
  ``m``/``mu``/``mz`` in GB), ``dio`` [lezen, schrijven] B/s, ``b`` [verzonden, ontvangen] B/s, ``t`` (sensoren °C),
  ``g`` (GPU's: ``n`` naam, ``u`` gebruik %, ``p`` W; **geen** temperatuur in de JSON).
- Alleen het systeem dat de beheerder als NAS koppelt (of waarvan ``host`` exact het NAS-adres uit D03 is) telt;
  alle andere systemen (bv. de mini-pc, D10) worden **uitgesloten** en nooit als NAS getoond.
- GPU's worden alleen aan een GPU uit de TrueNAS-inventaris (PCI-slot) gekoppeld als de naam **eenduidig** past;
  anders geen meting (nooit A310 en iGPU verwisselen). Temperaturen ≤ 0 °C of > 150 °C zijn ongeldig (nooit 0 °C).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from hub.monitoring.timeseries import Sample
from hub.outbound import OutboundError, OutboundPolicy, request

SYSTEM_ID = re.compile(r"^[a-z0-9]{1,32}$")
GIB = 1024**3
MIB = 1024**2
CPU_SENSOR = re.compile(r"(?i)^(coretemp_package_id_\d+|cpu_thermal|k10temp_tctl|k10temp_tdie|.*package.*)$")
MODEL = re.compile(r"(?i)\b([a-z]?\d{3,4}[a-z]?)\b")


@dataclass
class BeszelResult:
    ok: bool
    reden: str | None = None
    versie: str | None = None
    systemen: list[dict[str, Any]] = field(default_factory=list)
    nas: dict[str, Any] | None = None
    samples: list[Sample] = field(default_factory=list)
    gpu_niet_toegewezen: list[dict[str, Any]] = field(default_factory=list)


def _parse_time(v: Any) -> datetime | None:
    if not isinstance(v, str) or not v:
        return None
    try:
        dt = datetime.fromisoformat(v.strip().replace(" ", "T").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, int | float):
        return None
    f = float(v)
    return f if f == f and abs(f) != float("inf") else None


def valid_temp(v: Any) -> float | None:
    t = _num(v)
    return t if t is not None and 0 < t <= 150 else None


def match_gpu(name: str, gpus: list[dict[str, Any]]) -> tuple[str | None, str]:
    """PCI-slot van de GPU uit de inventaris die eenduidig bij deze naam past; anders (None, reden)."""
    tokens = {t.lower() for t in MODEL.findall(name or "")}
    if not tokens:
        return None, "geen_modelnummer_in_naam"
    hits = [g for g in gpus if tokens & {t.lower() for t in MODEL.findall(str(g.get("beschrijving") or ""))}]
    if len(hits) == 1 and hits[0].get("pci_slot"):
        return str(hits[0]["pci_slot"]), "naam_eenduidig"
    return None, "geen_eenduidige_gpu" if hits else "geen_gpu_met_deze_naam"


def nas_samples(
    stats: dict[str, Any], ts: datetime, bron: str, gpus: list[dict[str, Any]]
) -> tuple[list[Sample], list[dict[str, Any]]]:
    out: list[Sample] = []

    def add(metriek: str, eenheid: str, v: float | None, onderwerp: tuple[str, str] = ("nas", "nas")) -> None:
        if v is not None:
            out.append(Sample(onderwerp[0], onderwerp[1], metriek, eenheid, bron, ts, v))

    add("cpu.gebruik", "%", _num(stats.get("cpu")))
    mem = stats.get("mem")
    total = used = arc = None
    if isinstance(mem, list) and len(mem) >= 4 and all(_num(x) is not None for x in mem[:4]):
        total, used, arc = float(mem[0]), float(mem[1]), float(mem[3])
    else:  # oudere agents: GB-velden
        m, mu, mz = _num(stats.get("m")), _num(stats.get("mu")), _num(stats.get("mz"))
        total = m * GIB if m is not None else None
        used = mu * GIB if mu is not None else None
        arc = mz * GIB if mz is not None else None
    add("geheugen.totaal", "B", total if total else None)
    add("geheugen.gebruikt", "B", used)
    add("zfs.arc", "B", arc if arc else None)
    if total and used is not None:
        add("geheugen.beschikbaar_pct", "%", max(0.0, (total - used) / total * 100))
    dio = stats.get("dio")
    if isinstance(dio, list) and len(dio) == 2:
        add("schijf.lezen", "B/s", _num(dio[0]))
        add("schijf.schrijven", "B/s", _num(dio[1]))
    else:
        dr, dw = _num(stats.get("dr")), _num(stats.get("dw"))
        add("schijf.lezen", "B/s", dr * MIB if dr is not None else None)
        add("schijf.schrijven", "B/s", dw * MIB if dw is not None else None)
    bw = stats.get("b")
    if isinstance(bw, list) and len(bw) == 2:
        add("netwerk.verzonden", "B/s", _num(bw[0]))
        add("netwerk.ontvangen", "B/s", _num(bw[1]))
    raw_t = stats.get("t")
    temps: dict[str, Any] = raw_t if isinstance(raw_t, dict) else {}
    cpu_temps = [valid_temp(v) for k, v in temps.items() if CPU_SENSOR.match(str(k))]
    cpu_temps_ok = [t for t in cpu_temps if t is not None]
    if cpu_temps_ok:
        add("cpu.temperatuur", "°C", max(cpu_temps_ok))
    unassigned: list[dict[str, Any]] = []
    for key, g in (stats.get("g") or {}).items() if isinstance(stats.get("g"), dict) else []:
        if not isinstance(g, dict):
            continue
        slot, reason = match_gpu(str(g.get("n") or ""), gpus)
        if slot is None:
            unassigned.append({"sleutel": str(key)[:32], "naam": str(g.get("n") or "")[:128], "reden": reason})
            continue
        add("gpu.gebruik", "%", _num(g.get("u")), ("gpu", slot))
        add("gpu.vermogen", "W", _num(g.get("p")), ("gpu", slot))
    return out, unassigned


def fetch(
    base_url: str,
    identity: str,
    password: str,
    *,
    nas_system: str | None,
    nas_address: str | None,
    gpus: list[dict[str, Any]],
    bron: str,
    policy: OutboundPolicy,
) -> BeszelResult:
    out = BeszelResult(ok=False)
    try:
        auth = request(
            base_url,
            "POST",
            "/api/collections/users/auth-with-password",
            policy=policy,
            json_body={"identity": identity, "password": password},
        )
    except OutboundError as exc:
        out.reden = exc.reason
        return out
    tok = auth.json().get("token") if isinstance(auth.json(), dict) else None
    if auth.status in (400, 401, 403) or not tok:
        out.reden = "inloggen_mislukt"
        return out
    hdr = {"Authorization": str(tok)}
    try:
        info = request(base_url, "GET", "/api/beszel/info", policy=policy, headers=hdr, max_bytes=64 * 1024)
        if info.status == 200 and isinstance(info.json(), dict) and isinstance(info.json().get("v"), str):
            out.versie = str(info.json()["v"])[:64]
        systems = request(
            base_url,
            "GET",
            "/api/collections/systems/records",
            policy=policy,
            headers=hdr,
            query={"perPage": "200", "sort": "name"},
        )
    except OutboundError as exc:
        out.reden = exc.reason
        return out
    sj = systems.json()
    if systems.status in (401, 403):
        out.reden = "geen_leesrecht"
        return out
    if systems.status != 200 or not isinstance(sj, dict) or not isinstance(sj.get("items"), list):
        out.reden = "antwoord_ongeldig"
        return out
    chosen: dict[str, Any] | None = None
    for s in sj["items"]:
        if not isinstance(s, dict) or not SYSTEM_ID.match(str(s.get("id") or "")):
            continue
        is_nas = (nas_system is not None and s["id"] == nas_system) or (
            nas_system is None and nas_address is not None and str(s.get("host") or "") == nas_address
        )
        raw_info = s.get("info")
        info_d: dict[str, Any] = raw_info if isinstance(raw_info, dict) else {}
        entry = {
            "id": s["id"],
            "naam": str(s.get("name") or "")[:128],
            "status": str(s.get("status") or "")[:16],
            "agent_versie": str(info_d.get("v") or "")[:32] or None,
            "bijgewerkt": s.get("updated"),
            "rol": "nas" if is_nas else "uitgesloten",
            "reden": None if is_nas else "geen NAS (alleen het NAS-systeem telt; D10: mini-pc niet in het platform)",
        }
        out.systemen.append(entry)
        if is_nas and chosen is None:
            chosen = s
    out.ok = True
    if chosen is None:
        out.reden = "nas_systeem_niet_gekoppeld"
        return out
    out.nas = {
        "id": chosen["id"],
        "naam": chosen.get("name"),
        "status": chosen.get("status"),
        "koppeling": "handmatig" if nas_system else "automatisch (host = NAS-adres uit D03)",
    }
    try:
        stats = request(
            base_url,
            "GET",
            "/api/collections/system_stats/records",
            policy=policy,
            headers=hdr,
            query={"filter": f"(system='{chosen['id']}' && type='1m')", "sort": "-created", "perPage": "1"},
        )
    except OutboundError as exc:
        out.reden = exc.reason
        return out
    stj = stats.json()
    items = stj.get("items") if isinstance(stj, dict) else None
    if stats.status != 200 or not isinstance(items, list):
        out.reden = "antwoord_ongeldig"
        return out
    if not items or not isinstance(items[0], dict) or not isinstance(items[0].get("stats"), dict):
        out.reden = "geen_metingen"
        return out
    ts = _parse_time(items[0].get("created")) or _parse_time(items[0].get("updated"))
    if ts is None:
        out.reden = "tijd_onbekend"
        return out
    out.nas["observed_at"] = ts
    out.samples, out.gpu_niet_toegewezen = nas_samples(items[0]["stats"], ts, bron, gpus)
    return out
