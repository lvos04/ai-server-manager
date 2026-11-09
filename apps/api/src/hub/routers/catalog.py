"""Centrale appcatalogus (B01-002): zoeken, filteren, detail en idempotente discovery.

Alles is alleen-lezen ten opzichte van de NAS: discovery verwerkt alleen de al opgehaalde inventaris. Gezondheid wordt
op leestijd beoordeeld; een verouderde bron is ``unknown``, nooit gezond.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from hub import audit
from hub.catalog.discovery import discover, is_inventory_fresh
from hub.catalog.profiles import ADAPTER_TYPES, SOORTEN
from hub.catalog.view import detail, summary
from hub.deps import DB, Cursor, Idem, Limit, Operator, SettingsDep, Viewer, decode_cursor, encode_cursor
from hub.errors import HubError
from hub.models import CatalogApp
from hub.registry import nas_address
from hub.timeutil import iso, utcnow

router = APIRouter(prefix="/api/v1/apps", tags=["appcatalogus"])

Status = Literal["healthy", "degraded", "down", "unknown"]


@router.get("", summary="Appcatalogus: alle apps met status, versie, herkomst en gezondheid (zoeken/filteren)")
def list_apps(
    db: DB,
    settings: SettingsDep,
    principal: Viewer,
    limit: Limit = 50,
    cursor: Cursor = None,
    q: str | None = Query(default=None, max_length=80, description="Zoek in naam, app_id en image."),
    status: Status | None = None,
    adaptertype: str | None = Query(default=None, max_length=32),
    soort: str | None = Query(default=None, max_length=16),
    alleen_aanwezig: bool = Query(default=True, description="Verdwenen apps verbergen (standaard)."),
) -> dict[str, Any]:
    if adaptertype is not None and adaptertype not in ADAPTER_TYPES:
        raise HubError(422, "validation_error", f"Onbekend adaptertype; kies uit: {', '.join(ADAPTER_TYPES)}.")
    if soort is not None and soort not in SOORTEN:
        raise HubError(422, "validation_error", f"Onbekende soort; kies uit: {', '.join(SOORTEN)}.")
    now = utcnow()
    inv = is_inventory_fresh(db, settings, now)
    nas = nas_address(db)
    stmt = select(CatalogApp).order_by(CatalogApp.naam, CatalogApp.runtime_id)
    if alleen_aanwezig:
        stmt = stmt.where(CatalogApp.aanwezig.is_(True))
    if adaptertype:
        stmt = stmt.where(CatalogApp.adaptertype == adaptertype)
    if soort:
        stmt = stmt.where(CatalogApp.soort == soort)
    items = []
    needle = (q or "").strip().lower()
    for row in db.scalars(stmt):
        if needle and not any(
            needle in str(v or "").lower() for v in (row.naam, row.app_id, row.runtime_id, row.image_repository)
        ):
            continue
        item = summary(db, settings, row, inv, nas, now)
        if status and item["gezondheid"]["status"] != status:
            continue
        items.append(item)
    offset = decode_cursor(cursor) or 0
    page = items[offset : offset + limit]
    counts: dict[str, int] = dict.fromkeys(("healthy", "degraded", "down", "unknown"), 0)
    for it in items:
        counts[it["gezondheid"]["status"]] += 1
    return {
        "items": page,
        "totaal": len(items),
        "per_status": counts,
        "next_cursor": encode_cursor(offset + limit) if offset + limit < len(items) else None,
        "inventaris": {
            "status": inv.get("status"),
            "reason_code": inv.get("reason_code"),
            "observed_at": inv.get("observed_at"),
            "verouderd": inv.get("verouderd"),
        },
        "observed_at": iso(now),
        "alleen_lezen": True,
    }


@router.post("/discover", summary="Catalogus bijwerken uit de laatste inventaris (idempotent; niets op de NAS)")
def run_discovery(db: DB, settings: SettingsDep, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    res = discover(db, settings)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="catalog.discovery",
        target_type="catalog",
        details=res.as_dict(),
    )
    db.flush()
    return idem.save(200, {**res.as_dict(), "toelichting": "Alleen de catalogus is bijgewerkt; op de NAS is niets "
                           "gewijzigd. Vernieuw eerst de inventaris voor verse gegevens."})  # fmt: skip


@router.get("/{app_uuid}", summary="Appdetail: herkomst, image/digest, opslag, poorten, gezondheid per component")
def get_app(
    app_uuid: uuid.UUID, response: Response, db: DB, settings: SettingsDep, principal: Viewer
) -> dict[str, Any]:
    row = db.get(CatalogApp, app_uuid)
    if row is None:
        raise HubError(404, "not_found", "App niet gevonden in de catalogus.")
    now = utcnow()
    response.headers["ETag"] = f'"{row.version}"'
    return detail(db, settings, row, is_inventory_fresh(db, settings, now), nas_address(db), now, principal.role)
