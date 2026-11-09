"""Uptime Kuma-adapter (B09-002): alleen lezen via ``/metrics`` (met API-key) en/of de status-page-API.

Bronwaarneming in de broncode van Uptime Kuma 2.5.9 (NIET GEVALIDEERD tegen een echte installatie):
- ``GET /metrics`` achter HTTP Basic; met API-keys aan is het wachtwoord de API-key (gebruikersnaam leeg). De Hub
  gebruikt **alleen** een API-key, nooit een gebruikerswachtwoord.
- ``monitor_status{monitor_id,monitor_name,monitor_type,monitor_url,monitor_hostname,monitor_port,…}``:
  1 = UP, 0 = DOWN, 2 = PENDING, 3 = MAINTENANCE; daarnaast ``monitor_response_time`` (ms),
  ``monitor_uptime_ratio{window}``, ``monitor_cert_days_remaining`` en ``app_version{version}`` (versie-detectie,
  via ``prometheus-api-metrics``).
- ``GET /api/status-page/{slug}`` (monitorlijst) en ``GET /api/status-page/heartbeat/{slug}`` (laatste 100
  hartslagen per monitor, ``time`` in UTC ``YYYY-MM-DD HH:mm:ss.SSS``, ``uptimeList["<id>_24"]``), zonder aanmelding.
Statusvertaling: UP → healthy, DOWN → down, PENDING → degraded, MAINTENANCE → unknown (``onderhoud``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlsplit

from hub.monitoring import prometheus
from hub.outbound import OutboundError, OutboundPolicy, basic_auth, request
from hub.redact import redact_text

KUMA_STATUS = {
    1: ("healthy", None),
    0: ("down", "monitor_down"),
    2: ("degraded", "monitor_wacht"),
    3: ("unknown", "onderhoud"),
}
SLUG = re.compile(r"^[a-z0-9-]{1,64}$")
MAX_METRICS_BYTES = 8 * 1024 * 1024


@dataclass
class KumaMonitor:
    sleutel: str
    naam: str
    id: str | None = None
    type: str | None = None
    url: str | None = None
    hostname: str | None = None
    port: int | None = None
    status: str = "unknown"
    reason_code: str | None = None
    observed_at: datetime | None = None
    latency_ms: float | None = None
    uptime_24u: float | None = None
    cert_dagen: float | None = None
    bronnen: list[str] = field(default_factory=list)


@dataclass
class KumaResult:
    ok: bool
    reden: str | None = None
    versie: str | None = None
    monitors: dict[str, KumaMonitor] = field(default_factory=dict)
    fouten: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        return {
            "versie": self.versie,
            "monitors": len(self.monitors),
            "per_status": {
                s: sum(1 for m in self.monitors.values() if m.status == s)
                for s in ("healthy", "degraded", "down", "unknown")
            },
            "fouten": self.fouten,
        }


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN → None


def _clean_url(u: str | None) -> str | None:
    """Monitor-URL zonder inloggegevens of query (kan geheimen bevatten), hooguit 256 tekens."""
    if not u or u == "null":
        return None
    try:
        p = urlsplit(u)
    except ValueError:
        return None
    if not p.scheme or not p.hostname:
        return None
    port = f":{p.port}" if p.port else ""
    host = f"[{p.hostname}]" if ":" in p.hostname else p.hostname
    return redact_text(f"{p.scheme}://{host}{port}{p.path}")[:256]


def _key(monitor_id: str | None, naam: str) -> str:
    return f"id:{monitor_id}" if monitor_id else f"naam:{naam}"[:200]


def parse_metrics(text: str, now: datetime) -> tuple[dict[str, KumaMonitor], str | None, int]:
    res = prometheus.parse(text)
    monitors: dict[str, KumaMonitor] = {}
    version = None
    for m in res.by_name("app_version"):
        version = m.labels.get("version") or version
    for m in res.by_name("monitor_status"):
        mid = m.labels.get("monitor_id") or None
        naam = m.labels.get("monitor_name") or (f"monitor {mid}" if mid else "naamloos")
        status, reason = KUMA_STATUS.get(int(m.waarde), ("unknown", "status_onbekend"))
        port = _num(m.labels.get("monitor_port"))
        monitors[_key(mid, naam)] = KumaMonitor(
            sleutel=_key(mid, naam),
            naam=naam[:200],
            id=mid,
            type=(m.labels.get("monitor_type") or None),
            url=_clean_url(m.labels.get("monitor_url")),
            hostname=(m.labels.get("monitor_hostname") or None) if m.labels.get("monitor_hostname") != "null" else None,
            port=int(port) if port else None,
            status=status,
            reason_code=reason,
            observed_at=now,
            bronnen=["metrics"],
        )

    def attach(metric: str, attr: str, window: str | None = None) -> None:
        for m in res.by_name(metric):
            if window is not None and m.labels.get("window") not in (window,):
                continue
            mid = m.labels.get("monitor_id") or None
            naam = m.labels.get("monitor_name") or (f"monitor {mid}" if mid else "naamloos")
            mon = monitors.get(_key(mid, naam))
            if mon is not None and m.waarde >= 0:
                setattr(mon, attr, m.waarde)

    attach("monitor_response_time", "latency_ms")
    attach("monitor_cert_days_remaining", "cert_dagen")
    attach("monitor_uptime_ratio", "uptime_24u", "1d")
    return monitors, version, res.onleesbaar


def _parse_time(v: Any) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        dt = datetime.fromisoformat(v.strip().replace(" ", "T").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def merge_status_page(
    monitors: dict[str, KumaMonitor], page: dict[str, Any], beats: dict[str, Any]
) -> dict[str, KumaMonitor]:
    raw_hb, raw_up = beats.get("heartbeatList"), beats.get("uptimeList")
    hb_list: dict[str, Any] = raw_hb if isinstance(raw_hb, dict) else {}
    uptime: dict[str, Any] = raw_up if isinstance(raw_up, dict) else {}
    for group in page.get("publicGroupList") or []:
        if not isinstance(group, dict):
            continue
        for mon in group.get("monitorList") or []:
            if not isinstance(mon, dict) or mon.get("id") is None:
                continue
            mid = str(mon["id"])
            naam = str(mon.get("name") or f"monitor {mid}")[:200]
            key = _key(mid, naam)
            beats_for = [b for b in (hb_list.get(mid) or []) if isinstance(b, dict)]
            last = beats_for[-1] if beats_for else None  # oplopend gesorteerd (oud → nieuw)
            entry = monitors.get(key) or KumaMonitor(sleutel=key, naam=naam, id=mid, type=mon.get("type"))
            if mon.get("url") and not entry.url:
                entry.url = _clean_url(str(mon["url"]))
            if last is not None:
                ts = _parse_time(last.get("time"))
                if "metrics" not in entry.bronnen or entry.observed_at is None:
                    status, reason = KUMA_STATUS.get(int(_num(last.get("status")) or 0), ("unknown", "status_onbekend"))
                    entry.status, entry.reason_code, entry.observed_at = status, reason, ts
                    ping = _num(last.get("ping"))
                    entry.latency_ms = ping if ping is not None and ping >= 0 else entry.latency_ms
            up = _num(uptime.get(f"{mid}_24"))
            if up is not None:
                entry.uptime_24u = up
            entry.bronnen = sorted({*entry.bronnen, "status_pagina"})
            monitors[key] = entry
    return monitors


def fetch(
    base_url: str,
    api_key: str | None,
    status_paginas: list[str],
    *,
    use_metrics: bool,
    policy: OutboundPolicy,
    now: datetime,
) -> KumaResult:
    out = KumaResult(ok=False)
    attempted = 0
    if use_metrics:
        if not api_key:
            out.fouten.append({"bron": "metrics", "reden": "api_key_ontbreekt"})
        else:
            attempted += 1
            try:
                res = request(
                    base_url,
                    "GET",
                    "/metrics",
                    policy=policy,
                    headers={"Authorization": basic_auth("", api_key), "Accept": "text/plain"},
                    max_bytes=MAX_METRICS_BYTES,
                )
                if res.status in (401, 403):
                    out.fouten.append({"bron": "metrics", "reden": "api_key_geweigerd", "http": res.status})
                elif res.status != 200:
                    out.fouten.append({"bron": "metrics", "reden": f"http_{res.status}"})
                else:
                    mons, version, bad = parse_metrics(res.text(), now)
                    out.monitors.update(mons)
                    out.versie = version
                    if bad:
                        out.fouten.append({"bron": "metrics", "reden": "onleesbare_regels", "aantal": bad})
                    out.ok = True
            except OutboundError as exc:
                out.fouten.append({"bron": "metrics", "reden": exc.reason})
    for slug in status_paginas:
        if not SLUG.match(slug):
            out.fouten.append({"bron": f"status_pagina:{slug[:64]}", "reden": "slug_ongeldig"})
            continue
        attempted += 1
        try:
            page = request(base_url, "GET", f"/api/status-page/{quote(slug)}", policy=policy)
            beats = request(base_url, "GET", f"/api/status-page/heartbeat/{quote(slug)}", policy=policy)
        except OutboundError as exc:
            out.fouten.append({"bron": f"status_pagina:{slug}", "reden": exc.reason})
            continue
        pj, bj = page.json(), beats.json()
        if page.status != 200 or beats.status != 200 or not isinstance(pj, dict) or not isinstance(bj, dict):
            out.fouten.append({"bron": f"status_pagina:{slug}", "reden": "statuspagina_niet_gevonden"})
            continue
        merge_status_page(out.monitors, pj, bj)
        out.ok = True
    if not attempted:
        out.reden = "niets_ingesteld"
    elif not out.ok:
        reasons = {f["reden"] for f in out.fouten}
        out.reden = "api_key_geweigerd" if "api_key_geweigerd" in reasons else next(iter(sorted(reasons)), "fout")
    return out
