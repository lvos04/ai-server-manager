"""Bind één runbookactie aan het onderwerp van een incident, vóór de gemeenschappelijke voorstelcontrole."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.actions import beleid, service
from hub.config import Settings
from hub.errors import HubError
from hub.models import CatalogApp, Incident, Service
from hub.registry import measured_apps
from hub.runbooks import engine
from hub.runbooks.catalogus import runbook_hash
from hub.vault import Vault


def _doel(db: Session, inc: Incident) -> CatalogApp | None:
    if inc.onderwerp_type != "app":
        return None
    if inc.bron == "hub:alerts":
        # De Hub heeft het onderwerp zélf uit de inventaris aan de alert gekoppeld.
        try:
            return db.get(CatalogApp, uuid.UUID(inc.onderwerp_id))
        except ValueError:
            return None
    if inc.onderwerp_id != inc.bron:
        return None
    # Een dienst kan alleen over de eigen gekoppelde instantie een voorstel laten maken.
    apps = db.scalars(
        select(CatalogApp)
        .join(Service, CatalogApp.service_id == Service.id)
        .where(Service.app_id == inc.bron, Service.status == "active")
        .limit(2)
    ).all()
    return apps[0] if len(apps) == 1 else None


def voorstel(
    db: Session,
    settings: Settings,
    vault: Vault,
    inc: Incident,
    *,
    request_id: uuid.UUID,
    action_id: str | None,
    target: dict[str, str] | None,
    parameters: dict[str, Any],
    expected_version: str | None,
    trace_id: str,
) -> dict[str, Any]:
    if action_id is not None and beleid.get_policy().actie(action_id) is None:
        raise HubError(422, "actie_onbekend", "Deze actie staat niet in het beleid.")
    rb = engine.runbook_for(inc)
    if inc.status not in ("open", "erkend") or inc.veilige_modus or not rb or not rb.herstart_voorstel:
        raise HubError(422, "geen_runbookvoorstel", "Dit incident heeft nu geen toegestane runbookactie.")
    if action_id is not None and action_id != rb.herstart_voorstel:
        raise HubError(422, "actie_buiten_bereik", "De actie valt buiten het runbook voor dit incident.")
    app = _doel(db, inc)
    if not app or not app.aanwezig:
        raise HubError(422, "doel_buiten_bereik", "Er is geen gekoppelde app voor dit incident.")
    doel = {"host_id": "nas-primary", "app_id": app.runtime_id}
    if target is not None and target != doel:
        raise HubError(422, "doel_buiten_bereik", "Het doel valt buiten dit incident.")
    apps = measured_apps(db, settings)
    if apps["status"] != "ok" or not any(a.get("naam") == app.runtime_id for a in apps["data"] or []):
        raise HubError(422, "doel_buiten_bereik", "De huidige inventaris bevestigt de app niet.")
    service.voorcontrole(db, rb.herstart_voorstel, doel, parameters)
    return service.stel_voor(
        db,
        settings,
        vault,
        None,
        actor=("ai", "hub-ai"),
        request_id=request_id,
        action_id=rb.herstart_voorstel,
        target=doel,
        parameters=parameters,
        reason=f"Voorstel uit runbook {rb.id} voor incident {inc.id}.",
        risk_claim=None,
        evidence_ids=[f"incident:{inc.id}", f"runbook:{rb.id}", runbook_hash()],
        expected_version=expected_version,
        expires_in_seconds=300,
        trace_id=trace_id,
    )
