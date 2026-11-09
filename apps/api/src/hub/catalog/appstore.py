"""Koppeling catalogus ↔ appstore-entries (B01-002) via het dienstenregister.

Alleen als ``appstore-en-fork`` als eigen dienst is ingeschreven (actief) en zijn adres gemeten is (D03 + hostpoort,
``registry.service_base_url``). De Hub leest dan ``GET /catalog/v1/entries`` met een kortlevende dienst-JWT
(contract §4.3) en koppelt op ``app_id``. Anders, of bij een storing, is de koppeling ``unknown`` met een vaste reden —
nooit een gegokte entry. Er wordt niets in de appstore gewijzigd.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.keys import KeyRing
from hub.models import CatalogApp, Service
from hub.registry import service_base_url
from hub.servicecalls import ServiceCallError, call
from hub.timeutil import iso, utcnow

APPSTORE_APP_ID = "appstore-en-fork"
MAX_PAGES = 10


def _unknown(reason: str, now: datetime, previous: dict[str, Any] | None, detail: Any = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "unknown", "reden": reason, "laatste_poging": iso(now)}
    if detail is not None:
        out["detail"] = detail
    if previous and previous.get("status") in ("gekoppeld", "niet_in_appstore"):
        out["laatst_bekend"] = {k: v for k, v in previous.items() if k != "laatst_bekend"}
    elif previous and previous.get("laatst_bekend"):
        out["laatst_bekend"] = previous["laatst_bekend"]
    return out


def _entry(e: dict[str, Any], now: datetime) -> dict[str, Any]:
    raw_latest = e.get("latest_version")
    latest: dict[str, Any] = raw_latest if isinstance(raw_latest, dict) else {}
    return {
        "status": "gekoppeld",
        "app_id": str(e.get("app_id")),
        "naam": e.get("name"),
        "categorie": e.get("category"),
        "eigenaar_repo": e.get("owner_repo"),
        "installatiewijze": e.get("install_method"),
        "entry_status": e.get("status"),
        "laatste_versie": latest.get("version"),
        "manifest_sha256": latest.get("manifest_sha256"),
        "manifest_geldig": latest.get("valid"),
        "observed_at": iso(now),
        "bron": "appstore-en-fork /catalog/v1/entries",
    }


def _set(row: CatalogApp, value: dict[str, Any], now: datetime) -> None:
    def comparable(v: dict[str, Any]) -> dict[str, Any]:
        return {k: x for k, x in v.items() if k not in ("observed_at", "laatste_poging")}

    if comparable(row.appstore or {}) != comparable(value):
        row.version += 1
        row.updated_at = now
    row.appstore = value


def fetch_entries(base: str, keyring: KeyRing, svc: Service, settings: Settings) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        bearer, _jti = keyring.issue_hub_service_jwt(audience=APPSTORE_APP_ID, service_id=str(svc.id))
        path = "/catalog/v1/entries?limit=200" + (f"&cursor={quote(cursor, safe='')}" if cursor else "")
        res = call(
            base,
            "GET",
            path,
            bearer=bearer,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
        if res.status != 200 or not isinstance(res.body, dict) or not isinstance(res.body.get("items"), list):
            raise ServiceCallError(f"http_{res.status}" if res.status != 200 else "antwoord_ongeldig")
        for e in res.body["items"]:
            if isinstance(e, dict) and isinstance(e.get("app_id"), str):
                entries[e["app_id"]] = e
        nxt = res.body.get("next_cursor")
        if not isinstance(nxt, str) or not nxt:
            break
        cursor = nxt
    return entries


def sync_appstore(db: Session, settings: Settings, keyring: KeyRing, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    rows = list(db.scalars(select(CatalogApp)))
    svc = db.scalars(select(Service).where(Service.app_id == APPSTORE_APP_ID, Service.status == "active")).first()
    if svc is None:
        for row in rows:
            _set(row, _unknown("appstore_niet_gekoppeld", now, row.appstore), now)
        db.flush()
        return {"status": "unknown", "reden": "appstore_niet_gekoppeld"}
    base, reason = service_base_url(db, settings, svc)
    if base is None:
        for row in rows:
            _set(row, _unknown("appstore_adres_onbekend", now, row.appstore, reason), now)
        db.flush()
        return {"status": "unknown", "reden": "appstore_adres_onbekend", "detail": reason}
    try:
        entries = fetch_entries(base, keyring, svc, settings)
    except ServiceCallError as exc:
        for row in rows:
            _set(row, _unknown("appstore_onbereikbaar", now, row.appstore, exc.reason), now)
        db.flush()
        return {"status": "unknown", "reden": "appstore_onbereikbaar", "detail": exc.reason}
    linked = 0
    for row in rows:
        key = row.app_id or row.runtime_id
        e = entries.get(key)
        if e is not None:
            _set(row, _entry(e, now), now)
            linked += 1
        else:
            _set(
                row,
                {"status": "niet_in_appstore", "app_id": key, "observed_at": iso(now), "bron": "appstore-en-fork"},
                now,
            )
    db.flush()
    return {"status": "ok", "gekoppeld": linked, "entries": len(entries)}
