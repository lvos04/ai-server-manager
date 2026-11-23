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
from typing import Any, TypeGuard

from asm_policy.canonical import CanonicalError, canonical_json, canonical_sha256
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.keys import load_private
from hub.models import AuditEvent, CatalogApp
from hub.registry import nas_address
from hub.timeutil import iso

BEVESTIGING_ACTIE = "monitoring.monitorplan.bevestigd"
STAND_BEVESTIGD = "handmatig bevestigd"
PAD = re.compile(r"/(?!/)[A-Za-z0-9._~/-]{0,254}")
HTTP_ADRES = re.compile(r"http://(?:\[[\w:.%-]+\]|[\w.-]+):([0-9]{1,5})(/.*)")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
NAAM = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
MONITOR_VELDEN = {"pad", "verwachte_status", "timeout_s", "interval_s"}
FOUTSTATUS = {
    "monitor_ontbreekt": "ontbreekt",
    "monitor_ongeldig": "ongeldig",
    "manifest_ongeldig": "onbekend",
    "manifest_onbereikbaar": "onbekend",
    "versie_onbekend": "onbekend",
}
UITLEG = (
    "De Hub maakt geen monitors aan in Uptime Kuma. Neem elke regel over in de Kuma-UI (HTTP-monitor) en bevestig hem "
    "daarna hier: de regel krijgt dan de stand 'handmatig bevestigd'. Zonder bevestigde monitor is een app 'niet "
    "bewaakt' en telt hij niet als gezond."
)


def _int(v: Any, lo: int, hi: int) -> int | None:
    return v if type(v) is int and lo <= v <= hi else None


def _poort(v: Any) -> int | str | None:
    return v if v == "same_as_host" else _int(v, 1, 65535)


def _geldige_monitor(mon: Any) -> bool:
    if not isinstance(mon, Mapping) or set(mon) != MONITOR_VELDEN:
        return False
    pad = mon["pad"]
    return (
        isinstance(pad, str)
        and PAD.fullmatch(pad) is not None
        and _int(mon["verwachte_status"], 100, 599) is not None
        and _int(mon["timeout_s"], 1, 300) is not None
        and _int(mon["interval_s"], 10, 86400) is not None
    )


def geldige_hash(sha: Any) -> TypeGuard[str]:
    return isinstance(sha, str) and SHA256.fullmatch(sha) is not None


def normaliseer(blok: Any) -> dict[str, Any] | None:
    """Alleen de openbare monitorvelden met een geldig pad, geldige drempels en manifesthash."""
    if not isinstance(blok, Mapping) or blok.get("status") != "ok" or not _geldige_monitor(blok.get("monitor")):
        return None
    container, host = _poort(blok.get("container_poort")), blok.get("host_poort")
    if (
        container is None
        or (host is not None and _int(host, 1, 65535) is None)
        or not geldige_hash(blok.get("manifest_sha256"))
    ):
        return None
    return {
        "status": "ok",
        "monitor": dict(blok["monitor"]),
        "container_poort": container,
        "host_poort": host,
        "manifest_sha256": blok["manifest_sha256"],
    }


def uit_manifest(manifest: Mapping[str, Any], manifest_sha256: str) -> dict[str, Any]:
    """Monitorblok uit een (al op hash gecontroleerd) manifest: ``ok``, ``ontbreekt`` of ``ongeldig``."""
    hc = manifest.get("healthcheck")
    mon = hc.get("monitor") if isinstance(hc, Mapping) else None
    if mon is None:
        return {"status": "ontbreekt", "reden": "monitor_ontbreekt", "manifest_sha256": manifest_sha256}
    assert isinstance(hc, Mapping)
    netwerk = manifest.get("network")
    ports = netwerk.get("ports") if isinstance(netwerk, Mapping) else None
    poorten = [
        p for p in (ports if isinstance(ports, list) else []) if isinstance(p, Mapping) and p.get("protocol") == "tcp"
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


def _bronbewijs(app_id: str, blok: Mapping[str, Any]) -> bytes:
    return canonical_json({"soort": "hub.monitorplan.v1", "app_id": app_id, "blok": blok})


def gecontroleerd_manifest(manifest: Any, sha: str, app_id: str, identiteit: Ed25519PrivateKey) -> dict[str, Any]:
    """Bind uitsluitend de uit het gecontroleerde manifest afgeleide velden aan de identiteit van de Hub."""
    try:
        if isinstance(manifest, dict) and manifest.get("app_id") == app_id and canonical_sha256(manifest) == sha:
            blok = uit_manifest(manifest, sha)
            if blok["status"] == "ok":
                blok["bronbewijs"] = identiteit.sign(_bronbewijs(app_id, blok)).hex()
            return blok
    except CanonicalError:
        pass
    return {"status": "onbekend", "reden": "manifest_ongeldig"}


def monitorbron(entry: dict[str, Any]) -> dict[str, Any]:
    vorig = entry.get("laatst_bekend")
    return vorig if "monitor" not in entry and isinstance(vorig, dict) else entry


def uit_cache(entry: Mapping[str, Any], app_id: str, sha: Any, sleutel: Ed25519PublicKey) -> dict[str, Any] | None:
    # Een los bronbewijs bindt zelf app-ID en hash. Bij een catalogusversie moeten beide ook in de metadata kloppen.
    if {"app_id", "manifest_sha256", "laatste_versie"}.intersection(entry) and (
        entry.get("app_id") != app_id or entry.get("manifest_sha256") != sha
    ):
        return None
    blok = entry.get("monitor")
    schoon = normaliseer(blok)
    if (
        not isinstance(blok, dict)
        or schoon is None
        or schoon["manifest_sha256"] != sha
        or set(blok) != {*schoon, "bronbewijs"}
    ):
        return None
    bewijs = blok["bronbewijs"]
    if not isinstance(bewijs, str) or len(bewijs) != 128:
        return None
    try:
        sleutel.verify(bytes.fromhex(bewijs), _bronbewijs(app_id, schoon))
    except (InvalidSignature, ValueError):
        return None
    return {**schoon, "bronbewijs": bewijs}


def lees_monitor(bron: Mapping[str, Any], app_id: str, settings: Settings) -> dict[str, Any]:
    """Eigen of laatst bekende catalogus-entry. Een oud blok zonder bewijs wacht op de volgende synchronisatie."""
    blok = bron.get("monitor")
    if isinstance(blok, dict) and bron.get("app_id", app_id) == app_id:
        sha = blok.get("manifest_sha256")
        if blok.get("status") == "ok" and geldige_hash(sha):
            try:
                sleutel = load_private(settings.secrets_dir / "hub-identity.ed25519").public_key()
                schoon = uit_cache(bron, app_id, sha, sleutel)
                if schoon is not None:
                    return schoon
            except (OSError, ValueError, TypeError, UnsupportedAlgorithm):
                pass
        reden = blok.get("reden")
        if isinstance(reden, str) and reden in FOUTSTATUS and blok.get("status") == FOUTSTATUS[reden]:
            fout = {"status": FOUTSTATUS[reden], "reden": reden}
            if geldige_hash(sha):
                fout["manifest_sha256"] = sha
            return fout
    return {"status": "ongeldig", "reden": "monitor_ongeldig"}


def _bron(row: CatalogApp, settings: Settings) -> tuple[dict[str, Any] | None, str]:
    appstore = row.appstore or {}
    bron = monitorbron(appstore)
    if "monitor" not in bron:
        status = appstore.get("status")
        reden = appstore.get("reden") if status == "unknown" else status if status == "niet_in_appstore" else None
        return None, str(reden or "manifest_onbekend")[:64]
    blok = lees_monitor(bron, row.app_id or row.runtime_id, settings)
    if blok["status"] != "ok":
        return None, blok["reden"]
    return blok, ""


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
    return {"op": iso(row.at), "door": row.actor_id, "plan_sha256": sha if geldige_hash(sha) else None}


def bevestigingsbewijs(app_id: str, sha: Any) -> dict[str, Any]:
    return {"app_id": app_id, "plan_sha256": sha if geldige_hash(sha) else None, "soort_bewijs": STAND_BEVESTIGD}


def _ontbreekt(app: dict[str, Any], reden: str) -> dict[str, Any]:
    return {
        "app": app,
        "stand": "ontbreekt",
        "reden": reden,
        "controle": None,
        "bewaakt": False,
        "bewaking": "niet bewaakt",
        "plan_sha256": None,
        "bevestiging": None,
        "bevestiging_verouderd": False,
    }


def bevestigingsantwoord(antwoord: Any, app_id: uuid.UUID, sha: str) -> dict[str, Any]:
    """Een historisch ontvangstbewijs hoort bij dit verzoek. Controleer ook daar het volledige HTTP-adres."""
    ontbreekt = _ontbreekt({"id": str(app_id)}, "monitor_ongeldig")
    data = antwoord if isinstance(antwoord, dict) else {}
    app = data.get("app")
    if not isinstance(app, dict) or app.get("id") != str(app_id) or data.get("stand") != STAND_BEVESTIGD:
        return ontbreekt
    controle = data.get("controle")
    if not isinstance(controle, dict) or controle.get("soort") != "http":
        return ontbreekt
    adres = controle.get("adres")
    match = HTTP_ADRES.fullmatch(adres) if isinstance(adres, str) else None
    if not match or not 1 <= int(match[1]) <= 65535 or set(controle) != (MONITOR_VELDEN - {"pad"}) | {"soort", "adres"}:
        return ontbreekt
    drempels = {k: controle[k] for k in MONITOR_VELDEN - {"pad"}}
    if not _geldige_monitor({**drempels, "pad": match[2]}):
        return ontbreekt
    bevestiging = data.get("bevestiging")
    if (
        data.get("plan_sha256") != sha
        or not geldige_hash(data.get("manifest_sha256"))
        or canonical_sha256({"app": str(app_id), "controle": controle}) != sha
        or not isinstance(bevestiging, dict)
        or bevestiging.get("plan_sha256") != sha
    ):
        return ontbreekt
    return {
        **ontbreekt,
        "app": {k: app.get(k) for k in ("id", "naam", "app_id")},
        "stand": STAND_BEVESTIGD,
        "reden": None,
        "controle": controle,
        "bewaakt": True,
        "bewaking": "bewaakt",
        "plan_sha256": sha,
        "manifest_sha256": data["manifest_sha256"],
        "bevestiging": {k: bevestiging.get(k) for k in ("op", "door", "plan_sha256")},
    }


def regel(db: Session, row: CatalogApp, settings: Settings, nas: str | None = None) -> dict[str, Any]:
    """Eén planregel. Stand: ``ontbreekt`` | ``onvolledig`` | ``voorgesteld`` | ``handmatig bevestigd``."""
    bron, reden = _bron(row, settings)
    out = _ontbreekt({"id": str(row.id), "naam": row.naam, "app_id": row.app_id}, reden)
    if bron is None:
        return out
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


def bewaakt(db: Session, row: CatalogApp, settings: Settings) -> bool:
    return bool(regel(db, row, settings)["bewaakt"])


def plan(db: Session, settings: Settings) -> list[dict[str, Any]]:
    nas = nas_address(db) or ""
    rows = db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True)).order_by(CatalogApp.naam))
    return [regel(db, r, settings, nas) for r in rows]
