"""Centrale appcatalogus (B01-002): zoeken, filteren, sorteren, detail en idempotente discovery.

Alles is alleen-lezen ten opzichte van de NAS: discovery verwerkt alleen de al opgehaalde inventaris. Gezondheid wordt
op leestijd beoordeeld; een verouderde bron is ``unknown``, nooit gezond.

Contract 1.3: leesbaar voor gebruikers (``viewer``+) en voor diensten met de vaste scope ``inventaris.lezen`` (§4.4);
de lijst komt uit een meting en wordt **gepagineerd over een momentopname** (§5, K5): elke pagina noemt
``snapshot_id`` en de ``observed_at`` van de meting met hetzelfde totaal; is de momentopname veranderd (nieuwe meting,
andere gezondheid of filter), dan 409 ``snapshot_changed`` — opnieuw beginnen.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select

from hub import audit
from hub.catalog.discovery import discover, is_inventory_fresh
from hub.catalog.profiles import ADAPTER_TYPES, SOORTEN
from hub.catalog.view import detail, summary
from hub.deps import DB, Cursor, Idem, Limit, Operator, Principal, SettingsDep, require_viewer_or_scope
from hub.errors import HubError
from hub.models import CatalogApp
from hub.registry import nas_address
from hub.scopes import INVENTARIS_LEZEN
from hub.timeutil import iso, utcnow

router = APIRouter(prefix="/api/v1/apps", tags=["appcatalogus"])

Status = Literal["healthy", "degraded", "down", "unknown"]
Sortering = Literal["naam", "status"]
InventoryReader = Annotated[Principal, Depends(require_viewer_or_scope(INVENTARIS_LEZEN))]
# Sorteren op status: eerst wat aandacht vraagt (C01): storing, beperkt, onbekend, gezond; daarbinnen op naam.
STATUS_ORDER = {"down": 0, "degraded": 1, "unknown": 2, "healthy": 3}


def _snapshot_id(inv: dict[str, Any], params: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Vingerafdruk van de momentopname: de meting (observed_at), de filters en per app id, versie en gezondheid."""
    basis = {
        "meting": inv.get("observed_at"),
        "filters": params,
        "apps": [(i["id"], i["versie_etag"], i["gezondheid"]["status"]) for i in items],
    }
    return hashlib.sha256(json.dumps(basis, sort_keys=True, default=str).encode()).hexdigest()[:20]


def _encode(offset: int, snapshot: str) -> str:
    raw = json.dumps({"o": offset, "s": snapshot}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str | None) -> tuple[int, str | None]:
    if not cursor:
        return 0, None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        offset, snapshot = data["o"], data["s"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HubError(400, "invalid_cursor", "Ongeldige cursor.") from exc
    if type(offset) is not int or offset < 0 or not isinstance(snapshot, str):
        raise HubError(400, "invalid_cursor", "Ongeldige cursor.")
    return offset, snapshot


@router.get(
    "",
    summary="Appcatalogus: alle apps met status, versie, herkomst en gezondheid (zoeken/filteren/sorteren); viewer+ of "
    "dienst met scope inventaris.lezen; gepagineerd over een momentopname",
    responses={
        403: {"description": "scope_ontbreekt (dienst zonder inventaris.lezen) of forbidden"},
        409: {"description": "snapshot_changed: de momentopname van de cursor bestaat niet meer; begin opnieuw"},
    },
)
def list_apps(
    db: DB,
    settings: SettingsDep,
    principal: InventoryReader,
    limit: Limit = 50,
    cursor: Cursor = None,
    q: str | None = Query(default=None, max_length=80, description="Zoek in naam, app_id en image."),
    status: Status | None = None,
    adaptertype: str | None = Query(default=None, max_length=32),
    soort: str | None = Query(default=None, max_length=16),
    alleen_aanwezig: bool = Query(default=True, description="Verdwenen apps verbergen (standaard)."),
    sortering: Annotated[Sortering, Query(description="naam (standaard) of status (storing eerst).")] = "naam",
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
    if sortering == "status":
        items.sort(key=lambda it: (STATUS_ORDER.get(it["gezondheid"]["status"], 2), str(it["naam"]), it["id"]))
    params = {"q": needle, "status": status, "adaptertype": adaptertype, "soort": soort,
              "alleen_aanwezig": alleen_aanwezig, "sortering": sortering}  # fmt: skip
    snapshot = _snapshot_id(inv, params, items)
    offset, wanted = _decode(cursor)
    if wanted is not None and wanted != snapshot:
        raise HubError(
            409,
            "snapshot_changed",
            "De lijst is veranderd sinds de vorige pagina (nieuwe meting of andere gezondheid). Begin opnieuw.",
            {"snapshot_id": snapshot},
        )
    page = items[offset : offset + limit]
    counts: dict[str, int] = dict.fromkeys(("healthy", "degraded", "down", "unknown"), 0)
    for it in items:
        counts[it["gezondheid"]["status"]] += 1
    return {
        "items": page,
        "totaal": len(items),
        "per_status": counts,
        "snapshot_id": snapshot,
        "meting_observed_at": inv.get("observed_at"),
        "next_cursor": _encode(offset + limit, snapshot) if offset + limit < len(items) else None,
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


@router.get(
    "/{app_uuid}",
    summary="Appdetail: herkomst, image/digest, opslag, poorten, gezondheid per component (viewer+, inventaris.lezen)",
    responses={403: {"description": "scope_ontbreekt (dienst zonder inventaris.lezen) of forbidden"}},
)
def get_app(
    app_uuid: uuid.UUID, response: Response, db: DB, settings: SettingsDep, principal: InventoryReader
) -> dict[str, Any]:
    row = db.get(CatalogApp, app_uuid)
    if row is None:
        raise HubError(404, "not_found", "App niet gevonden in de catalogus.")
    now = utcnow()
    response.headers["ETag"] = f'"{row.version}"'
    return detail(db, settings, row, is_inventory_fresh(db, settings, now), nas_address(db), now, principal.role)
