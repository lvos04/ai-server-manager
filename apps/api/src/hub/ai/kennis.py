"""Vier lokale leesinstrumenten. De bron bepaalt de classificatie, de tijd en de rolgrens."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.deps import Principal
from hub.errors import HubError
from hub.models import Incident, LogEntry
from hub.redact import redact_log_text
from hub.registry import measured_apps
from hub.runbooks import engine
from hub.runbooks.catalogus import runbook_hash
from hub.security import Role
from hub.timeutil import UtcDateTime


class InventarisBron(BaseModel):
    ref: str = "/api/v1/inventory/apps"
    status: Literal["ok", "unknown"]
    observed_at: str | None
    verouderd: bool
    aantal_apps: int | None


class IncidentBron(BaseModel):
    ref: str
    classificatie: str
    observed_at: UtcDateTime
    soort: str
    ernst: Literal["info", "waarschuwing", "kritiek"]
    status: str
    gebeurtenissen: int
    regel: str
    hypothese: str
    zekerheid: float | None


class LogBron(BaseModel):
    ref: str
    observed_at: UtcDateTime
    niveau: str
    bericht: str = Field(max_length=500)


class RunbookBron(BaseModel):
    ref: str
    runbook_hash: str
    observeren: list[str]
    terugdraaien: list[str]


class Kennis(BaseModel):
    inventaris: InventarisBron
    incident: IncidentBron
    logs_toegestaan: bool
    logs: list[LogBron] = Field(max_length=10)
    runbook: RunbookBron | None


def incident(db: Session, incident_id: uuid.UUID, principal: Principal, *, vergrendel: bool = False) -> Incident:
    inc = db.get(Incident, incident_id, with_for_update=vergrendel)
    if inc is None:
        raise HubError(404, "not_found", "Incident niet gevonden.")
    if inc.classificatie == "sensitive" and principal.role != Role.admin:
        raise HubError(403, "forbidden", "Alleen een beheerder mag gevoelige incidentgegevens voor diagnose opvragen.")
    return inc


def lees(db: Session, settings: Settings, inc: Incident, principal: Principal) -> Kennis:
    inv = measured_apps(db, settings)
    rb = engine.runbook_for(inc)
    mag_logs = principal.role in (Role.admin, Role.operator)
    logs: list[LogBron] = []
    if mag_logs and inc.trace_ids:
        # Alleen aan dit incident gebonden, reeds geschoonde regels van zijn eigen bron.
        rows = db.scalars(
            select(LogEntry)
            .where(LogEntry.trace_id.in_(inc.trace_ids), LogEntry.bron == inc.bron)
            .order_by(LogEntry.id.desc())
            .limit(10)
        )
        logs = [
            LogBron(
                ref=f"log:{r.id}", observed_at=r.op, niveau=r.niveau, bericht=redact_log_text(r.bericht, max_len=500)
            )
            for r in rows
        ]
    h = inc.hypothese or {}
    return Kennis(
        inventaris=InventarisBron(
            status=inv["status"],
            observed_at=inv["observed_at"],
            verouderd=inv["verouderd"],
            aantal_apps=len(inv["data"]) if isinstance(inv["data"], list) else None,
        ),
        incident=IncidentBron(
            ref=f"/api/v1/incidents/{inc.id}",
            classificatie=inc.classificatie,
            observed_at=inc.laatste_op,
            soort=inc.soort,
            ernst=inc.ernst,
            status=inc.status,
            gebeurtenissen=inc.aantal,
            regel=h.get("regel") or "geen_regel",
            hypothese=redact_log_text(h.get("tekst") or "De oorzaak is onbekend.", max_len=500),
            zekerheid=h.get("zekerheid"),
        ),
        logs_toegestaan=mag_logs,
        logs=logs,
        runbook=RunbookBron(
            ref=f"/api/v1/runbooks/{rb.id}",
            runbook_hash=runbook_hash(),
            observeren=[stap.tekst for stap in rb.observeren],
            terugdraaien=[stap.tekst for stap in rb.terugdraaien],
        )
        if rb
        else None,
    )
