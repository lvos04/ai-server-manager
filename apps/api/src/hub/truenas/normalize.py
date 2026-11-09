"""Normaliseren van TrueNAS-antwoorden naar stabiele, geschoonde Hub-structuren.

Alleen expliciet genoemde velden worden overgenomen (whitelist); credentials, app-configuratie en omgevingsvariabelen
komen nooit in de Hub-database. Velden die per TrueNAS-versie verschillen worden defensief gelezen; ontbreekt iets,
dan wordt het ``None`` (onbekend) en nooit een verzonnen waarde.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from hub.redact import redact_text
from hub.timeutil import iso

# Bekende apps (alleen voor herkenning in de inventaris; installatie/mutatie gebeurt hier nooit).
KNOWN_APPS: list[tuple[str, tuple[str, ...]]] = [
    ("mediaguard", ("mediaguard",)),
    ("media-source-optimizer", ("media-source-optimizer", "mso")),
    ("my_house", ("my_house", "my-house", "myhouse")),
    ("ai-server-manager", ("ai-server-manager",)),
    ("ai-server-manager-executor", ("ai-server-manager-executor",)),
    ("jellyfin", ("jellyfin",)),
    ("jelly-leon", ("jelly-leon",)),
    ("plex", ("plex",)),
    ("emby", ("emby",)),
    ("immich", ("immich",)),
    ("prowlarr", ("prowlarr",)),
    ("sabnzbd", ("sabnzbd",)),
    ("qbittorrent", ("qbittorrent",)),
    ("bazarr", ("bazarr",)),
    ("seerr", ("seerr", "jellyseerr", "overseerr")),
    ("readarr", ("readarr",)),
    ("flaresolverr", ("flaresolverr",)),
    ("tailscale", ("tailscale",)),
    ("cloudflared", ("cloudflared",)),
    ("uptime-kuma", ("uptime-kuma", "uptimekuma")),
    ("beszel", ("beszel",)),
    ("gotify", ("gotify",)),
    ("authentik", ("authentik",)),
    ("node-red", ("node-red", "nodered")),
    ("adguard-home", ("adguard",)),
    ("netalertx", ("netalertx",)),
]

_IMAGE_RE = re.compile(
    r"^(?P<repo>[^@]+?)(?::(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}))?(?:@(?P<digest>sha256:[0-9a-f]{64}))?$"
)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def parse_ts(value: Any) -> str | None:
    """TrueNAS-tijden: ``{"$date": ms}``, epoch (s of ms), numerieke string of ISO → ISO-UTC met ``Z``."""
    if value is None:
        return None
    if isinstance(value, dict):
        if "$date" in value:
            return parse_ts(value["$date"])
        for key in ("parsed", "rawvalue", "value"):
            if key in value:
                return parse_ts(value[key])
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 10**11 else value
        try:
            return iso(datetime.fromtimestamp(seconds, UTC))
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return parse_ts(int(s))
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
        return iso(dt if dt.tzinfo else dt.replace(tzinfo=UTC))
    return None


def _num(value: Any) -> int | float | None:
    if isinstance(value, dict):
        for key in ("parsed", "rawvalue", "value"):
            if key in value:
                return _num(value[key])
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _str(value: Any, limit: int = 256) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("value", "parsed", "rawvalue"):
            if key in value:
                return _str(value[key], limit)
        return None
    return str(value)[:limit]


def parse_image(image: str | None) -> dict[str, str | None]:
    if not image:
        return {"image": None, "repository": None, "tag": None, "digest": None}
    m = _IMAGE_RE.match(image.strip())
    if not m:
        return {"image": image, "repository": None, "tag": None, "digest": None}
    return {"image": image, "repository": m.group("repo"), "tag": m.group("tag"), "digest": m.group("digest")}


def recognize_app(name: str, images: list[str]) -> str | None:
    haystack = [name.lower()] + [str(i).lower().rsplit("/", 1)[-1].split(":")[0].split("@")[0] for i in images]
    for app_id, needles in KNOWN_APPS:
        for needle in needles:
            if any(h == needle or h.startswith(needle + "-") or h.startswith(needle + "_") for h in haystack):
                return app_id
    return None


def pools(raw: Any) -> list[dict[str, Any]]:
    out = []
    for p in raw or []:
        if not isinstance(p, dict):
            continue
        size, alloc, free = _num(p.get("size")), _num(p.get("allocated")), _num(p.get("free"))
        scan = _dict(p.get("scan"))
        status = _str(p.get("status"), 32)
        healthy = p.get("healthy")
        out.append(
            {
                "naam": _str(p.get("name"), 128),
                "status": status,
                "gezond": bool(healthy) if isinstance(healthy, bool) else (status == "ONLINE" if status else None),
                "waarschuwing": bool(p.get("warning")) if isinstance(p.get("warning"), bool) else None,
                "grootte_bytes": size,
                "gebruikt_bytes": alloc,
                "vrij_bytes": free,
                "gebruik_pct": round(alloc / size * 100, 1)
                if isinstance(size, int | float) and size and isinstance(alloc, int | float)
                else None,
                "scrub": {
                    "functie": _str(scan.get("function"), 32),
                    "staat": _str(scan.get("state"), 32),
                    "laatst_beeindigd": parse_ts(scan.get("end_time")),
                    "fouten": _num(scan.get("errors")),
                },
            }
        )
    return out


def _flatten_datasets(raw: Any) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    stack = list(raw or [])
    while stack:
        d = stack.pop(0)
        if not isinstance(d, dict):
            continue
        flat.append(d)
        children = d.get("children")
        if isinstance(children, list):
            stack.extend(children)
    return flat


def datasets(raw: Any) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for d in _flatten_datasets(raw):
        name = _str(d.get("name") or d.get("id"), 512)
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(
            {
                "naam": name,
                "pool": _str(d.get("pool"), 128) or name.split("/", 1)[0],
                "type": _str(d.get("type"), 32),
                "mountpoint": _str(d.get("mountpoint"), 512),
                "gebruikt_bytes": _num(d.get("used")),
                "beschikbaar_bytes": _num(d.get("available")),
                "versleuteld": d.get("encrypted") if isinstance(d.get("encrypted"), bool) else None,
            }
        )
    out.sort(key=lambda x: str(x["naam"]))
    return out


def apps(raw: Any) -> list[dict[str, Any]]:
    out = []
    for a in raw or []:
        if not isinstance(a, dict):
            continue
        name = _str(a.get("name") or a.get("id"), 128) or ""
        wl = _dict(a.get("active_workloads"))
        images = [str(i) for i in (wl.get("images") or []) if i]
        details = _list(wl.get("container_details"))
        for c in details:
            if isinstance(c, dict) and c.get("image") and str(c["image"]) not in images:
                images.append(str(c["image"]))
        ports: list[dict[str, Any]] = []
        for p in wl.get("used_ports") or []:
            if not isinstance(p, dict):
                continue
            host_ports = [hp for hp in (p.get("host_ports") or []) if isinstance(hp, dict)]
            for hp in host_ports or [{}]:
                ports.append(
                    {
                        "container_poort": _num(p.get("container_port")),
                        "host_poort": _num(hp.get("host_port")),
                        "host_ip": _str(hp.get("host_ip"), 64),
                        "protocol": (_str(p.get("protocol"), 8) or "tcp").lower(),
                    }
                )
        mounts: list[dict[str, Any]] = []
        for v in wl.get("volumes") or []:
            if isinstance(v, dict):
                mounts.append(
                    {
                        "bron": _str(v.get("source"), 512),
                        "doel": _str(v.get("destination"), 512),
                        "type": _str(v.get("type"), 16),
                    }
                )
        meta = _dict(a.get("metadata"))
        out.append(
            {
                "naam": name,
                "runtime_id": _str(a.get("id"), 128) or name,
                "staat": _str(a.get("state"), 32),
                "versie": _str(a.get("version"), 64),
                "app_versie": _str(meta.get("app_version") or a.get("human_version"), 128),
                "custom_app": a.get("custom_app") if isinstance(a.get("custom_app"), bool) else None,
                "upgrade_beschikbaar": a.get("upgrade_available")
                if isinstance(a.get("upgrade_available"), bool)
                else None,
                "images": [parse_image(i) for i in images],
                "poorten": ports,
                "opslag": mounts,
                "herkend_als": recognize_app(name, images),
            }
        )
    out.sort(key=lambda x: str(x["naam"]))
    return out


def disks(raw: Any) -> list[dict[str, Any]]:
    out = []
    for d in raw or []:
        if not isinstance(d, dict):
            continue
        serial = _str(d.get("serial"), 64) or ""
        out.append(
            {
                "naam": _str(d.get("name"), 64),
                "model": _str(d.get("model"), 128),
                "serienummer_laatste4": serial[-4:] if serial else None,
                "grootte_bytes": _num(d.get("size")),
                "type": _str(d.get("type"), 16),
                "pool": _str(d.get("pool"), 128),
            }
        )
    return out


def smart(raw: Any) -> list[dict[str, Any]]:
    out = []
    for d in raw or []:
        if not isinstance(d, dict):
            continue
        tests = [t for t in (d.get("tests") or []) if isinstance(t, dict)]
        last = tests[0] if tests else None
        out.append(
            {
                "disk": _str(d.get("disk"), 64),
                "laatste_test": None
                if last is None
                else {
                    "omschrijving": _str(last.get("description"), 64),
                    "status": _str(last.get("status"), 32),
                    "status_tekst": _str(last.get("status_verbose"), 128),
                    "levensduur_uren": _num(last.get("lifetime")),
                },
                "aantal_tests": len(tests),
            }
        )
    return out


def _gpu_role(description: str) -> str:
    low = description.lower()
    if "a310" in low or ("arc" in low and "dg2" in low):
        return "a310"
    if "uhd" in low and "770" in low:
        return "uhd770"
    return "onbekend"


def gpus(raw: Any) -> list[dict[str, Any]]:
    """Identiteit = PCI-slot (stabiel), nooit de render-node (die kan per boot wisselen; zie D08)."""
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for slot, g in raw.items():
            if isinstance(g, dict):
                items.append({**g, "pci_slot": g.get("pci_slot") or slot})
    elif isinstance(raw, list):
        items = [g for g in raw if isinstance(g, dict)]
    out = []
    for g in items:
        desc = _str(g.get("description") or g.get("model"), 256) or ""
        addr = _dict(g.get("addr"))
        out.append(
            {
                "pci_slot": _str(g.get("pci_slot") or addr.get("pci_slot"), 32),
                "vendor": _str(g.get("vendor"), 32),
                "beschrijving": desc,
                "herkend_als": _gpu_role(desc),
                "fout": _str(g.get("error"), 256),
                "render_node": None,  # wordt niet uit de API afgeleid; komt uit D08 (bevestigd door de gebruiker)
            }
        )
    out.sort(key=lambda x: str(x["pci_slot"]))
    return out


def snapshot_tasks(raw: Any) -> list[dict[str, Any]]:
    out = []
    for t in raw or []:
        if not isinstance(t, dict):
            continue
        state = _dict(t.get("state"))
        schedule = _dict(t.get("schedule"))
        out.append(
            {
                "id": _num(t.get("id")),
                "dataset": _str(t.get("dataset"), 512),
                "recursief": bool(t.get("recursive")),
                "uitgesloten": [str(x) for x in (t.get("exclude") or [])],
                "bewaartermijn": {"waarde": _num(t.get("lifetime_value")), "eenheid": _str(t.get("lifetime_unit"), 16)},
                "schema": {
                    k: _str(schedule.get(k), 32) for k in ("minute", "hour", "dom", "month", "dow") if k in schedule
                },
                "ingeschakeld": bool(t.get("enabled")),
                "laatste_staat": _str(state.get("state"), 32),
                "laatste_run": parse_ts(state.get("datetime")),
            }
        )
    return out


def latest_snapshot(raw: Any) -> dict[str, Any] | None:
    items = [s for s in (raw or []) if isinstance(s, dict)]
    if not items:
        return None
    s = items[0]
    props = _dict(s.get("properties"))
    created = parse_ts(props.get("creation")) if props else None
    return {"naam": _str(s.get("name") or s.get("id"), 512), "aangemaakt_op": created}


def _provider(task: dict[str, Any]) -> str | None:
    cred = task.get("credentials")
    if isinstance(cred, dict):
        prov = cred.get("provider")
        if isinstance(prov, dict):
            return _str(prov.get("type"), 32)
        return _str(prov, 32)
    return None


def _job(job: Any) -> dict[str, Any] | None:
    if not isinstance(job, dict):
        return None
    return {
        "staat": _str(job.get("state"), 32),
        "gestart": parse_ts(job.get("time_started")),
        "beeindigd": parse_ts(job.get("time_finished")),
        "fout": redact_text(str(job["error"]))[:300] if job.get("error") else None,
    }


def cloudsync(raw: Any) -> list[dict[str, Any]]:
    """Alleen taakmetadata; nooit credential-attributen (tokens, wachtwoorden)."""
    out = []
    for t in raw or []:
        if not isinstance(t, dict):
            continue
        provider = _provider(t)
        out.append(
            {
                "id": _num(t.get("id")),
                "omschrijving": _str(t.get("description"), 256),
                "pad": _str(t.get("path"), 512),
                "richting": _str(t.get("direction"), 8),
                "modus": _str(t.get("transfer_mode"), 8),
                "provider": provider,
                "is_onedrive": (provider or "").upper() == "ONEDRIVE",
                "versleuteld": t.get("encryption") if isinstance(t.get("encryption"), bool) else None,
                "ingeschakeld": bool(t.get("enabled")),
                "laatste_job": _job(t.get("job")),
            }
        )
    return out


def replication(raw: Any) -> list[dict[str, Any]]:
    out = []
    for t in raw or []:
        if not isinstance(t, dict):
            continue
        state = _dict(t.get("state"))
        out.append(
            {
                "id": _num(t.get("id")),
                "naam": _str(t.get("name"), 256),
                "richting": _str(t.get("direction"), 8),
                "transport": _str(t.get("transport"), 16),
                "bron_datasets": [str(x) for x in (t.get("source_datasets") or [])],
                "doel_dataset": _str(t.get("target_dataset"), 512),
                "ingeschakeld": bool(t.get("enabled")),
                "laatste_staat": _str(state.get("state"), 32),
                "laatste_run": parse_ts(state.get("datetime")),
                "laatste_job": _job(t.get("job")),
            }
        )
    return out


def alerts(raw: Any) -> list[dict[str, Any]]:
    out = []
    for a in raw or []:
        if not isinstance(a, dict):
            continue
        out.append(
            {
                "uuid": _str(a.get("uuid"), 64),
                "niveau": _str(a.get("level"), 16),
                "klasse": _str(a.get("klass"), 64),
                "tekst": redact_text(str(a.get("formatted") or ""))[:500],
                "tijd": parse_ts(a.get("datetime")),
                "genegeerd": bool(a.get("dismissed")),
            }
        )
    return out


def network(raw: Any) -> dict[str, Any]:
    """Gemeten LAN-adressen (alleen als voorstel voor D03; de gebruiker bevestigt)."""
    if isinstance(raw, dict):
        ips = _dict(raw.get("ips"))
        adressen = []
        for iface, fams in ips.items():
            if not isinstance(fams, dict):
                continue
            for fam in ("IPV4", "IPV6"):
                for addr in fams.get(fam) or []:
                    adressen.append({"interface": str(iface), "familie": fam, "adres": str(addr)})
        return {"adressen": adressen, "standaardroutes": [str(r) for r in (raw.get("default_routes") or [])]}
    if isinstance(raw, list):  # interface.query
        adressen = []
        for iface in raw:
            if not isinstance(iface, dict):
                continue
            for alias in (iface.get("state") or {}).get("aliases") or []:
                if isinstance(alias, dict) and alias.get("type") in ("INET", "INET6"):
                    adressen.append(
                        {
                            "interface": str(iface.get("name")),
                            "familie": "IPV4" if alias.get("type") == "INET" else "IPV6",
                            "adres": f"{alias.get('address')}/{alias.get('netmask')}",
                        }
                    )
        return {"adressen": adressen, "standaardroutes": []}
    return {"adressen": [], "standaardroutes": []}


READONLY_ROLE = "READONLY_ADMIN"


def key_scope(me: Any) -> str:
    """``alleen_lezen`` | ``schrijfrechten`` | ``onbekend`` op basis van de rollen van de key-gebruiker."""
    if not isinstance(me, dict):
        return "onbekend"
    priv = _dict(me.get("privilege"))
    roles_raw = priv.get("roles")
    if isinstance(roles_raw, dict):
        roles_raw = roles_raw.get("$set")
    roles = [str(r) for r in (roles_raw or [])]
    if not roles:
        return "onbekend"
    if any(r == "FULL_ADMIN" or not (r == READONLY_ROLE or r.endswith("_READ")) for r in roles):
        return "schrijfrechten"
    return "alleen_lezen"


# Publieke aliassen voor hergebruik buiten deze module.
as_str = _str
as_num = _num
