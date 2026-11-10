"""Idempotente discovery van de appcatalogus uit de alleen-lezen TrueNAS-inventaris (B01-002).

- Alleen een **verse, geslaagde** ``apps``-meting telt (``kind_state`` = ok). Is de inventaris verouderd of mislukt,
  dan verandert er niets aan aanwezigheid of gegevens: de catalogus kan dan niets vaststellen.
- Identiteit = ``runtime_id`` (TrueNAS-app-id). Dezelfde app krijgt na een herstart van de NAS dezelfde Hub-UUID.
- Een app die in een verse meting ontbreekt, wordt nooit verwijderd: ``aanwezig = false`` + ``verdwenen_sinds``.
- Er wordt niets op de NAS geïnstalleerd of gewijzigd; discovery leest alleen al opgeslagen inventaris.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.catalog.profiles import profile_for
from hub.config import Settings
from hub.inventory.store import kind_state, latest_run
from hub.models import CatalogApp, Service
from hub.registry import app_name_for, expected_repository
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target

IX_APP = "ix-app"
HISTORY_MAX = 20


@dataclass
class DiscoveryResult:
    status: str  # ok | unknown
    reason_code: str | None = None
    nieuw: int = 0
    bijgewerkt: int = 0
    ongewijzigd: int = 0
    verdwenen: int = 0
    observed_at: str | None = None
    apps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "nieuw": self.nieuw,
            "bijgewerkt": self.bijgewerkt,
            "ongewijzigd": self.ongewijzigd,
            "verdwenen": self.verdwenen,
            "observed_at": self.observed_at,
        }


def install_method(app: dict[str, Any]) -> str:
    """Standaard Custom App-formulier = catalogus-app ``ix-app`` (``custom_app: false``); ``custom_app: true`` is een
    compose-app (Install via YAML, buiten het platformbeleid); andere catalogus-apps → ``catalog_app``.
    Bronwaarneming uit de TrueNAS-broncode (NIET GEVALIDEERD op een echte NAS)."""
    custom = app.get("custom_app")
    if custom is True:
        return "custom_compose"
    if custom is False:
        cat = app.get("catalogus_app")
        if cat == IX_APP:
            return "custom_app"
        if cat:
            return "catalog_app"
    return "onbekend"


def _digest_index(images: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [i for i in images or [] if isinstance(i, dict)]


def readback_digests(repo: str, tag: str | None, digest: str | None, images: list[dict[str, Any]]) -> list[str]:
    """Digests die ``app.image.query`` voor deze image teruggeeft (``repo_digests`` met dezelfde repository)."""
    found: set[str] = set()
    for img in images:
        tags = img.get("repo_tags") or []
        digests = [str(d) for d in img.get("repo_digests") or []]
        match = (tag is not None and f"{repo}:{tag}" in tags) or (digest is not None and f"{repo}@{digest}" in digests)
        if not match:
            continue
        for d in digests:
            r, _sep, dg = d.partition("@")
            if r == repo and dg.startswith("sha256:"):
                found.add(dg)
    return sorted(found)


def image_info(app: dict[str, Any], app_id: str | None, images: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Hoofdimage van de app met tag, digest en de digest-readback. Bij een eigen app de image
    ``ghcr.io/lvos04/<app_id>``, anders de eerste image."""
    imgs = [i for i in app.get("images") or [] if isinstance(i, dict) and i.get("repository")]
    if not imgs:
        return {"repository": None, "tag": None, "digest": None, "digest_bron": None, "readback": None}
    own = expected_repository(app_id) if app_id else None
    main = next((i for i in imgs if own and i.get("repository") == own), imgs[0])
    repo, tag, digest = str(main["repository"]), main.get("tag"), main.get("digest")
    out: dict[str, Any] = {
        "repository": repo,
        "tag": tag,
        "digest": digest,
        "digest_bron": "tagveld" if digest else None,
    }
    if images is None:
        out["readback"] = {"status": "unknown", "reden": "images_niet_gemeten", "digests": []}
        return out
    found = readback_digests(repo, tag, digest, images)
    if not found:
        out["readback"] = {"status": "unknown", "reden": "geen_digest_in_app_image_query", "digests": []}
    elif digest and digest not in found:
        out["readback"] = {"status": "afwijking", "reden": "digest_wijkt_af_van_tagveld", "digests": found}
    else:
        out["readback"] = {"status": "ok", "reden": None, "digests": found}
        if not digest and len(found) == 1:
            out["digest"], out["digest_bron"] = found[0], "app.image.query"
    return out


def storage(app: dict[str, Any], datasets: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    mounts = [(str(d["mountpoint"]), str(d["naam"])) for d in datasets or [] if d.get("mountpoint") and d.get("naam")]
    out = []
    for m in app.get("opslag") or []:
        src = str(m.get("bron") or "")
        entry = {"bron": m.get("bron"), "doel": m.get("doel"), "type": m.get("type"), "dataset": None}
        if src.startswith("/mnt/.ix-apps/"):
            entry["soort"] = "ixvolume"
        elif src.startswith("/mnt/"):
            entry["soort"] = "hostpad"
            best: tuple[int, str] | None = None
            for mp, name in mounts:
                if (src == mp or src.startswith(mp.rstrip("/") + "/")) and (best is None or len(mp) > best[0]):
                    best = (len(mp), name)
            entry["dataset"] = best[1] if best else None
        else:
            entry["soort"] = "overig"
        out.append(entry)
    return out


def _fields(
    app: dict[str, Any], images: list[dict[str, Any]] | None, datasets: list[dict[str, Any]] | None
) -> dict[str, Any]:
    app_id = app.get("herkend_als")
    prof = profile_for(app_id)
    img = image_info(app, app_id, images)
    all_images = [
        {"repository": i.get("repository"), "tag": i.get("tag"), "digest": i.get("digest")}
        for i in app.get("images") or []
        if isinstance(i, dict)
    ]
    return {
        "naam": str(app.get("naam") or app.get("runtime_id")),
        "app_id": app_id,
        "adaptertype": prof.adapter,
        "soort": prof.soort,
        "installatiewijze": install_method(app),
        "catalogus": {
            "app": app.get("catalogus_app"),
            "trein": app.get("trein"),
            "versie": app.get("versie"),
            "app_versie": app.get("app_versie"),
            "nieuwste_versie": app.get("nieuwste_versie"),
            "upgrade_beschikbaar": app.get("upgrade_beschikbaar"),
            "image_updates_beschikbaar": app.get("image_updates_beschikbaar"),
        },
        "image_repository": img["repository"],
        "image_tag": img["tag"],
        "image_digest": img["digest"],
        "images": [{**all_images[0], "digest_bron": img["digest_bron"], "readback": img["readback"]}, *all_images[1:]]
        if all_images
        else [],
        "poorten": list(app.get("poorten") or []),
        "opslag": storage(app, datasets),
        "portals": list(app.get("portals") or []),
        "runtime_staat": app.get("staat"),
    }


def _service_for(services: list[Service], app: dict[str, Any]) -> Service | None:
    """Een ingeschreven eigen dienst hoort bij deze app als de appnaam klopt (bevestigd of = app_id, H14) én de app de
    eigen image van die dienst draait (op repository, nooit op naam alleen)."""
    repos = {str(i.get("repository")) for i in app.get("images") or [] if isinstance(i, dict)}
    for svc in services:
        if app_name_for(svc) == app.get("runtime_id") and expected_repository(svc.app_id) in repos:
            return svc
    return None


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def discover(db: Session, settings: Settings, *, now: datetime | None = None) -> DiscoveryResult:
    now = now or utcnow()
    target = current_target(db)
    url = target.url if target else None
    st = kind_state(db, "apps", target=url, ttl_seconds=settings.inventory_max_age_seconds, now=now)
    if st["status"] != "ok" or not isinstance(st.get("data"), list):
        return DiscoveryResult(status="unknown", reason_code=st.get("reason_code") or "stale")
    images_st = kind_state(db, "images", target=url, ttl_seconds=settings.inventory_max_age_seconds, now=now)
    ds_st = kind_state(db, "datasets", target=url, ttl_seconds=settings.inventory_max_age_seconds, now=now)
    images = images_st["data"] if images_st["status"] == "ok" and isinstance(images_st.get("data"), list) else None
    # Datasets mogen de laatst bekende zijn (alleen voor de koppeling pad → dataset).
    datasets = ds_st.get("data") if isinstance(ds_st.get("data"), list) else None
    observed = _parse(st.get("observed_at")) or now
    run = latest_run(db, url)
    services = list(db.scalars(select(Service).where(Service.status == "active")))
    rows = {r.runtime_id: r for r in db.scalars(select(CatalogApp))}
    res = DiscoveryResult(status="ok", observed_at=iso(observed))
    seen: set[str] = set()
    bron = {
        "methode": "app.query",
        "nas": url,
        "inventaris_run": str(run.id) if run else None,
        "observed_at": iso(observed),
        "images_methode": "app.image.query" if images is not None else None,
    }
    for app in st["data"]:
        if not isinstance(app, dict) or not (app.get("runtime_id") or app.get("naam")):
            continue
        rid = str(app.get("runtime_id") or app.get("naam"))
        if rid in seen:
            continue
        seen.add(rid)
        res.apps.append(rid)
        fields = _fields({**app, "runtime_id": rid}, images, datasets)
        svc = _service_for(services, {**app, "runtime_id": rid})
        fields["service_id"] = svc.id if svc else None
        row = rows.get(rid)
        if row is None:
            row = CatalogApp(
                runtime_id=rid,
                **fields,
                appstore={},
                bron=bron,
                image_historie=[_history_entry(fields, observed)] if fields["image_repository"] else [],
                aanwezig=True,
                eerst_gezien=observed,
                laatst_gezien=observed,
                created_at=now,
                updated_at=now,
                version=1,
            )
            db.add(row)
            rows[rid] = row
            res.nieuw += 1
            continue
        changed = {k: v for k, v in fields.items() if getattr(row, k) != v}
        if not row.aanwezig:
            changed["aanwezig"] = True
            changed["verdwenen_sinds"] = None
        if any(k in changed for k in ("image_repository", "image_tag", "image_digest")):
            row.image_historie = [*(row.image_historie or []), _history_entry(fields, observed)][-HISTORY_MAX:]
        for k, v in changed.items():
            setattr(row, k, v)
        row.laatst_gezien = observed
        row.bron = bron
        if changed:
            row.version += 1
            row.updated_at = now
            res.bijgewerkt += 1
        else:
            res.ongewijzigd += 1
    for rid, row in rows.items():
        if rid not in seen and row.aanwezig:
            row.aanwezig = False
            row.verdwenen_sinds = observed
            row.version += 1
            row.updated_at = now
            res.verdwenen += 1
    db.flush()
    return res


def _history_entry(fields: dict[str, Any], at: datetime) -> dict[str, Any]:
    return {
        "op": iso(at),
        "repository": fields.get("image_repository"),
        "tag": fields.get("image_tag"),
        "digest": fields.get("image_digest"),
    }


def deep_link(row: CatalogApp, nas_address: str | None) -> dict[str, Any]:
    """Link naar de eigen UI van de app: NAS-adres uit D03 + hostpoort (portal of UI-poort uit het profiel).
    Zonder D03 geen link (nooit een aangenomen adres)."""
    if not nas_address:
        return {"url": None, "reden": "nas_adres_onbekend"}
    host = f"[{nas_address}]" if ":" in nas_address else nas_address
    portals = [p for p in row.portals or [] if isinstance(p, dict) and p.get("poort")]
    if portals:
        p = portals[0]
        scheme = p.get("schema") or "http"
        return {"url": f"{scheme}://{host}:{p['poort']}{p.get('pad') or '/'}", "reden": None, "bron": "portal"}
    prof = profile_for(row.app_id)
    ports = [p for p in row.poorten or [] if p.get("host_poort") and p.get("protocol") == "tcp"]
    preferred = [p for p in ports if prof.ui_poort and p.get("container_poort") == prof.ui_poort]
    chosen = (preferred or ports)[:1]
    if not chosen:
        return {"url": None, "reden": "geen_tcp_hostpoort"}
    return {"url": f"http://{host}:{chosen[0]['host_poort']}/", "reden": None, "bron": "hostpoort"}


def is_inventory_fresh(db: Session, settings: Settings, now: datetime | None = None) -> dict[str, Any]:
    target = current_target(db)
    return kind_state(
        db, "apps", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds, now=now
    )


__all__ = ["DiscoveryResult", "deep_link", "discover", "image_info", "install_method"]
