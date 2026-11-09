"""Dienstenregister: vaste ``app_id`` (contract §2) naast de werkelijke TrueNAS-appnaam en het gemeten adres.

Het adres van een eigen dienst is altijd ``http://<NAS-adres uit D03>:<hostpoort uit app.query>`` (contract §2, §3.3:
``base_url`` uit het enroll-verzoek is alleen informatief). De appnaam is standaard gelijk aan de ``app_id``; kiest de
gebruiker bij een handmatige installatie een andere naam, dan bevestigt een beheerder de gemeten naam (H14). Nooit
voorbeeldwaarden: zonder D03 of zonder verse meting is er geen adres.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from hub.config import Settings
from hub.inventory.store import kind_state
from hub.models import Decision, Service
from hub.truenas.connection import current_target

OWN_IMAGE_PREFIX = "ghcr.io/lvos04/"
# Containerpoorten uit contract §2 (de hostpoort is een voorstel en wordt altijd gemeten).
CONTAINER_PORTS = {
    "ai-server-manager": 30400,
    "ai-server-manager-executor": 30410,
    "home-control-hub": 30420,
    "appstore-en-fork": 30430,
    "jelly-leon-platform": 30440,
    "zoeken-en-persoonlijke-ai": 30450,
    "jelly-leon": 8096,
}


def expected_repository(app_id: str) -> str:
    return f"{OWN_IMAGE_PREFIX}{app_id}"


def nas_address(db: Session) -> str | None:
    d03 = db.get(Decision, "D03")
    if d03 is None or d03.status not in ("Ingevuld", "Getest") or not isinstance(d03.waarde, dict):
        return None
    return str(d03.waarde.get("nas_adres") or "") or None


def measured_apps(db: Session, settings: Settings) -> dict[str, Any]:
    target = current_target(db)
    return kind_state(db, "apps", target=target.url if target else None, ttl_seconds=settings.inventory_ttl_seconds)


def _repositories(app: dict[str, Any]) -> set[str]:
    return {str(i.get("repository")) for i in app.get("images") or [] if isinstance(i, dict) and i.get("repository")}


def app_name_candidates(apps: list[dict[str, Any]] | None, app_id: str) -> list[str]:
    """Gemeten TrueNAS-apps die de eigen image van deze dienst draaien (op image-repository, niet op naam)."""
    repo = expected_repository(app_id)
    return sorted(str(a["naam"]) for a in apps or [] if isinstance(a, dict) and repo in _repositories(a))


def app_name_for(svc: Service) -> str:
    return svc.truenas_app_name or svc.app_id


def service_base_url(db: Session, settings: Settings, svc: Service) -> tuple[str | None, str | None]:
    """``(basis-URL, None)`` of ``(None, reden)``; de reden is een vaste code voor de UI."""
    address = nas_address(db)
    if not address:
        return None, "nas_adres_onbekend"
    st = measured_apps(db, settings)
    if st.get("status") != "ok":
        return None, "inventaris_niet_actueel"
    name = app_name_for(svc)
    app = next((a for a in st.get("data") or [] if isinstance(a, dict) and a.get("naam") == name), None)
    if app is None:
        return None, "app_niet_gevonden"
    if expected_repository(svc.app_id) not in _repositories(app):
        return None, "image_komt_niet_overeen"
    ports = [p for p in app.get("poorten") or [] if p.get("host_poort") and p.get("protocol") == "tcp"]
    preferred = [p for p in ports if p.get("container_poort") == CONTAINER_PORTS.get(svc.app_id)]
    chosen = (preferred or ports)[:1]
    if not chosen:
        return None, "geen_tcp_hostpoort"
    host = f"[{address}]" if ":" in address else address
    return f"http://{host}:{chosen[0]['host_poort']}", None
