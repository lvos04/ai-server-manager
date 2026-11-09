"""Weergave van de appcatalogus voor de API (lijst en detail), met gezondheid, deep-link en acties per rol."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from hub.catalog.discovery import deep_link
from hub.catalog.profiles import profile_for
from hub.config import Settings
from hub.models import CatalogApp, Service
from hub.monitoring.appstatus import app_health
from hub.security import ROLE_RANK, Role
from hub.timeutil import iso


def actions(link: dict[str, Any], role: Role | None) -> list[dict[str, Any]]:
    """Knoppen voor de UI: alleen 'openen' kan nu; logs en herstart lopen in P2 via policy en executor (R1/R2)."""
    can_operate = role is not None and ROLE_RANK[role] >= ROLE_RANK[Role.operator]
    return [
        {
            "id": "openen",
            "beschikbaar": bool(link.get("url")),
            "url": link.get("url"),
            "reden": None if link.get("url") else link.get("reden"),
        },
        {
            "id": "logs",
            "beschikbaar": False,
            "vereiste_rol": "operator",
            "reden": "Volgt in fase P2 (alleen-lezen logs via de executor, geschoond)."
            if can_operate
            else "Alleen voor operator of beheerder.",
        },
        {
            "id": "herstarten",
            "beschikbaar": False,
            "vereiste_rol": "operator",
            "risico": "R1/R2 (policy bepaalt)",
            "reden": "Volgt in fase P2: app.restart via voorstel, policy en executor."
            if can_operate
            else "Alleen voor operator of beheerder.",
        },
    ]


def _resources() -> dict[str, Any]:
    return {
        "status": "unknown",
        "reden": "config_niet_gelezen",
        "toelichting": "Resourcegrenzen staan in de app-configuratie; die leest de Hub nooit uit TrueNAS omdat ze "
        "geheimen kan bevatten. Voor apps die de Hub zelf installeert (P2) komen ze uit het manifest.",
    }


def summary(
    db: Session,
    settings: Settings,
    row: CatalogApp,
    inv_state: dict[str, Any],
    nas: str | None,
    now: datetime,
    health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prof = profile_for(row.app_id)
    health = health or app_health(db, settings, row, inv_state, now)
    link = deep_link(row, nas)
    return {
        "id": str(row.id),
        "runtime_id": row.runtime_id,
        "naam": row.naam,
        "titel": prof.titel if row.app_id else row.naam,
        "app_id": row.app_id,
        "adaptertype": row.adaptertype,
        "soort": row.soort,
        "installatiewijze": row.installatiewijze,
        "image": {"repository": row.image_repository, "tag": row.image_tag, "digest": row.image_digest},
        "versie": (row.catalogus or {}).get("app_versie"),
        "runtime_staat": row.runtime_staat,
        "gezondheid": {k: v for k, v in health.items() if k != "componenten"},
        "deep_link": link.get("url"),
        "eigenaar": {"repo": prof.eigenaar_repo, "soort": prof.soort},
        "aanwezig": row.aanwezig,
        "eerst_gezien": iso(row.eerst_gezien),
        "laatst_gezien": iso(row.laatst_gezien),
        "verdwenen_sinds": iso(row.verdwenen_sinds),
        "laatst_getest": health.get("laatst_getest"),
        "appstore_status": (row.appstore or {}).get("status", "unknown"),
        "versie_etag": row.version,
    }


def detail(
    db: Session,
    settings: Settings,
    row: CatalogApp,
    inv_state: dict[str, Any],
    nas: str | None,
    now: datetime,
    role: Role | None,
) -> dict[str, Any]:
    prof = profile_for(row.app_id)
    health = app_health(db, settings, row, inv_state, now)
    out = summary(db, settings, row, inv_state, nas, now, health)
    link = deep_link(row, nas)
    svc = db.get(Service, row.service_id) if row.service_id else None
    out.update(
        {
            "gezondheid": health,
            "deep_link_detail": link,
            "catalogus": row.catalogus,
            "images": row.images,
            "image_historie": row.image_historie,
            "poorten": row.poorten,
            "opslag": row.opslag,
            "datasets": sorted({str(m["dataset"]) for m in row.opslag or [] if m.get("dataset")}),
            "portals": row.portals,
            "resourcegrenzen": _resources(),
            "documentatie": prof.documentatie,
            "gezondheidsprofiel": {
                "binnenkant": prof.binnenkant,
                "binnenkant_vereist": prof.binnenkant_vereist,
            },
            "dienst": None
            if svc is None
            else {"id": str(svc.id), "app_id": svc.app_id, "status": svc.status, "versie": svc.version},
            "appstore": row.appstore or {"status": "unknown", "reden": "nog_niet_gesynchroniseerd"},
            "bron": row.bron,
            "acties": actions(link, role),
            "alleen_lezen": True,
        }
    )
    return out
