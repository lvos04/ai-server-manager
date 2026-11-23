"""Monitorplan per app (B09, contract 1.3 §9 ``healthcheck.monitor``, C1.3-ASM-20).

De Hub stelt per app uit het register (D03 + gemeten hostpoort) en ``healthcheck.monitor`` van het manifest een plan
op: welke controle, welk adres, welke drempel. **De Hub maakt geen monitors aan in Uptime Kuma** en past Kuma niet aan.
De beheerder neemt de regel over in de Kuma-UI en bevestigt hem hier; dat heet "handmatig bevestigd", nooit
"gevalideerd door de Hub". De bevestiging is gebonden aan de inhoud van de regel (``plan_sha256``): verandert adres of
drempel, dan geldt de app weer als "niet bewaakt". Een app zonder bevestigde monitor telt nooit als gezond.

Het manifest komt uit de appstore (``hub.catalog.appstore``): alleen een manifest waarvan de Hub de hash zelf nagerekend
heeft, en daaruit alleen de velden van een positieve witte lijst (vorm en type strikt), bij opslaan én bij lezen.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from typing import Any

from asm_policy.canonical import canonical_sha256
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.models import AuditEvent, CatalogApp
from hub.registry import nas_address
from hub.timeutil import iso

BEVESTIGING_ACTIE = "monitoring.monitorplan.bevestigd"
STAND_BEVESTIGD = "handmatig bevestigd"
PAD = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/?-]{0,255}$")
NAAM = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
MONITOR_VELDEN = {"pad", "verwachte_status", "timeout_s", "interval_s"}
UITLEG = (
    "De Hub maakt geen monitors aan in Uptime Kuma. Neem elke regel over in de Kuma-UI (HTTP-monitor) en bevestig hem "
    "daarna hier: de regel krijgt dan de stand 'handmatig bevestigd'. Zonder bevestigde monitor is een app 'niet "
    "bewaakt' en telt hij niet als gezond."
)


def _int(v: Any, lo: int, hi: int) -> int | None:
    return v if type(v) is int and lo <= v <= hi else None


def _poort(v: Any) -> int | str | None:
    return v if v == "same_as_host" else _int(v, 1, 65535)


def normaliseer(blok: Any) -> dict[str, Any] | None:
    """Witte lijst van een (opgeslagen) monitorblok: precies deze velden met dit type, anders ``None``."""
    if not isinstance(blok, Mapping) or blok.get("status") != "ok":
        return None
    mon = blok.get("monitor")
    if not isinstance(mon, Mapping) or set(mon) != MONITOR_VELDEN:
        return None
    pad = mon["pad"]
    waarden = (
        _int(mon["verwachte_status"], 100, 599),
        _int(mon["timeout_s"], 1, 300),
        _int(mon["interval_s"], 10, 86400),
    )
    container, host = _poort(blok.get("container_poort")), blok.get("host_poort")
    host = None if host is None else _int(host, 1, 65535)
    if not isinstance(pad, str) or not PAD.match(pad) or None in waarden or container is None:
        return None
    if blok.get("host_poort") is not None and host is None:
        return None
    sha = blok.get("manifest_sha256")
    return {
        "status": "ok",
        "monitor": {"pad": pad, "verwachte_status": waarden[0], "timeout_s": waarden[1], "interval_s": waarden[2]},
        "container_poort": container,
        "host_poort": host,
        "manifest_sha256": sha if isinstance(sha, str) and len(sha) <= 80 else None,
    }


def uit_manifest(manifest: Mapping[str, Any], manifest_sha256: str) -> dict[str, Any]:
    """Monitorblok uit een (al op hash gecontroleerd) manifest: ``ok``, ``ontbreekt`` of ``ongeldig``."""
    hc = manifest.get("healthcheck")
    mon = hc.get("monitor") if isinstance(hc, Mapping) else None
    if mon is None:
        return {"status": "ontbreekt", "reden": "monitor_ontbreekt", "manifest_sha256": manifest_sha256}
    assert isinstance(hc, Mapping)
    netwerk = manifest.get("network")
    poorten = [
        p
        for p in (netwerk.get("ports") if isinstance(netwerk, Mapping) else None) or []
        if isinstance(p, Mapping) and p.get("protocol") == "tcp"
    ]
    naam = hc.get("port")
    if naam is None:
        gekozen = poorten if len(poorten) == 1 else []
    else:
        gekozen = [p for p in poorten if isinstance(naam, str) and NAAM.match(naam) and p.get("name") == naam]
    host = gekozen[0].get("host_port") if len(gekozen) == 1 else None
    blok = {
        "status": "ok",
        "monitor": dict(mon) if isinstance(mon, Mapping) else None,
        "container_poort": gekozen[0].get("container_port") if len(gekozen) == 1 else None,
        "host_poort": host if type(host) is int else None,  # een {param: ...} volgt uit de meting
        "manifest_sha256": manifest_sha256,
    }
    schoon = normaliseer(blok)
    if schoon is None:
        return {"status": "ongeldig", "reden": "monitor_ongeldig", "manifest_sha256": manifest_sha256}
    return schoon


def _bron(row: CatalogApp) -> tuple[dict[str, Any] | None, str]:
    appstore = row.appstore or {}
    blok = appstore.get("monitor")
    if blok is None and isinstance(appstore.get("laatst_bekend"), Mapping):
        blok = appstore["laatst_bekend"].get("monitor")
    if not isinstance(blok, Mapping):
        status = appstore.get("status")
        reden = appstore.get("reden") if status == "unknown" else status if status == "niet_in_appstore" else None
        return None, str(reden or "manifest_onbekend")[:64]
    schoon = normaliseer(blok)
    if schoon is None:
        reden = blok.get("reden") if isinstance(blok.get("reden"), str) else "monitor_ongeldig"
        return None, str(reden)[:64]
    return schoon, ""


def _hostpoort(row: CatalogApp, bron: Mapping[str, Any]) -> int | None:
    tcp = [p for p in row.poorten or [] if isinstance(p, Mapping) and p.get("protocol") == "tcp"]
    if bron["host_poort"] is not None:
        hits = {p.get("host_poort") for p in tcp if p.get("host_poort") == bron["host_poort"]}
    elif bron["container_poort"] == "same_as_host":
        hits = {p.get("host_poort") for p in tcp if p.get("container_poort") == p.get("host_poort")}
    else:
        hits = {p.get("host_poort") for p in tcp if p.get("container_poort") == bron["container_poort"]}
    hits.discard(None)
    found = next(iter(hits)) if len(hits) == 1 else None
    return _int(found, 1, 65535)


def laatste_bevestiging(db: Session, app_id: uuid.UUID) -> dict[str, Any] | None:
    """Alleen de laatste bevestiging telt: een oudere regel met dezelfde inhoud maakt een nieuwere niet ongedaan."""
    row = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.action == BEVESTIGING_ACTIE, AuditEvent.target_id == str(app_id))
        .order_by(AuditEvent.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    details = row.details or {}
    sha = details.get("plan_sha256")
    return {"op": iso(row.at), "door": row.actor_id, "plan_sha256": sha if isinstance(sha, str) else None}


def regel(db: Session, row: CatalogApp, nas: str | None = None) -> dict[str, Any]:
    """Eén planregel. Stand: ``ontbreekt`` | ``onvolledig`` | ``voorgesteld`` | ``handmatig bevestigd``."""
    out: dict[str, Any] = {
        "app": {"id": str(row.id), "naam": row.naam, "app_id": row.app_id},
        "controle": None,
        "plan_sha256": None,
        "bewaakt": False,
        "bewaking": "niet bewaakt",
        "bevestiging": None,
        "bevestiging_verouderd": False,
    }
    bron, reden = _bron(row)
    if bron is None:
        return {**out, "stand": "ontbreekt", "reden": reden}
    nas = nas if nas is not None else nas_address(db)
    poort = _hostpoort(row, bron)
    if not nas or poort is None:
        return {**out, "stand": "onvolledig", "reden": "nas_adres_onbekend" if not nas else "hostpoort_onbekend"}
    host = f"[{nas}]" if ":" in nas else nas
    controle = {"soort": "http", "adres": f"http://{host}:{poort}{bron['monitor']['pad']}", **bron["monitor"]}
    del controle["pad"]
    sha = canonical_sha256({"app": str(row.id), "controle": controle})
    bevestiging = laatste_bevestiging(db, row.id)
    bewaakt = bevestiging is not None and bevestiging["plan_sha256"] == sha
    return {
        **out,
        "stand": STAND_BEVESTIGD if bewaakt else "voorgesteld",
        "reden": None,
        "controle": controle,
        "plan_sha256": sha,
        "manifest_sha256": bron["manifest_sha256"],
        "bewaakt": bewaakt,
        "bewaking": "bewaakt" if bewaakt else "niet bewaakt",
        "bevestiging": bevestiging,
        "bevestiging_verouderd": bevestiging is not None and not bewaakt,
    }


def bewaakt(db: Session, row: CatalogApp) -> bool:
    return bool(regel(db, row)["bewaakt"])


def plan(db: Session) -> list[dict[str, Any]]:
    nas = nas_address(db) or ""
    rows = db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True)).order_by(CatalogApp.naam))
    return [regel(db, r, nas) for r in rows]
