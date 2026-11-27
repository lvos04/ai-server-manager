"""Kredietbewaking op de Hub. Een reservering blijft na een storing voor het volledige taakmaximum staan."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hub import audit
from hub.ai.runner import Aanvraag, Triage
from hub.config import Settings
from hub.errors import HubError
from hub.models import AuditEvent, Decision
from hub.onboarding.catalog import D09Waarde
from hub.timeutil import utcnow

RESERVERING = "ai.tegoed.gereserveerd"
UITGEPUT = "ai.tegoed.uitgeput"


class Tegoed(BaseModel):
    status: str
    maand: str
    aanbieder: str | None = None
    modelkeuze: str | None = None
    inbegrepen: int | None = None
    max_per_taak: int | None = None
    gereserveerd: int = 0
    beschikbaar: int | None = None


def stand(db: Session, settings: Settings, now: datetime, *, vergrendel: bool = False) -> Tegoed:
    maand = now.strftime("%Y-%m")
    row = db.get(Decision, "D09", with_for_update=vergrendel, populate_existing=True)
    saldo = Tegoed(status="d09_open" if settings.ai_enabled else "uitgeschakeld", maand=maand)
    if row is None or row.status != "Getest":
        return saldo
    try:
        config = D09Waarde.model_validate(row.waarde, strict=True)
    except ValidationError:
        return saldo
    if not (config.account_gekoppeld and config.harde_stop and not config.overage_toegestaan):
        return saldo
    saldo.aanbieder, saldo.modelkeuze = config.aanbieder, config.modelkeuze
    if not settings.ai_enabled:
        return saldo
    saldo.status = "tegoed_onbekend"
    if config.tegoedmaand != maand or config.inbegrepen_eenheden is None:
        return saldo
    saldo.inbegrepen, saldo.max_per_taak = config.inbegrepen_eenheden, config.max_eenheden_per_taak
    periode = AuditEvent.details["maand"].astext == maand
    som = func.sum(AuditEvent.details["eenheden"].as_integer())
    saldo.gereserveerd = db.scalar(select(som).where(periode, AuditEvent.action == RESERVERING)) or 0
    stop = db.scalar(select(AuditEvent.id).where(periode, AuditEvent.action == UITGEPUT).limit(1))
    saldo.beschikbaar = 0 if stop else max(0, config.inbegrepen_eenheden - saldo.gereserveerd)
    if not saldo.beschikbaar or (saldo.max_per_taak or 0) > saldo.beschikbaar:
        saldo.status = "tegoed_op"
    elif saldo.max_per_taak and saldo.aanbieder and saldo.modelkeuze and settings.ai_provider_url:
        saldo.status = "beschikbaar"
    return saldo


def reserveer(
    db: Session, settings: Settings, taak_id: uuid.UUID, gebruiker: str, triage: Triage
) -> tuple[str, Aanvraag | None]:
    # De rij van D09 serialiseert alle budgetbeslissingen, ook tussen API-processen. Commit vóór het netwerk:
    # een time-out of herstart kan nooit een tweede poging uit hetzelfde krediet financieren.
    saldo = stand(db, settings, utcnow(), vergrendel=True)
    eerder = db.scalar(
        select(AuditEvent.id).where(AuditEvent.action == RESERVERING, AuditEvent.target_id == str(taak_id))
    )
    if eerder is not None:
        raise HubError(409, "diagnose_al_gereserveerd", "Deze taak heeft al krediet gereserveerd. Raadpleeg de audit.")
    if saldo.status != "beschikbaar" or not (saldo.aanbieder and saldo.modelkeuze and saldo.max_per_taak):
        return saldo.status, None
    taak = Aanvraag(
        taak_id=taak_id,
        aanbieder=saldo.aanbieder,
        modelkeuze=saldo.modelkeuze,
        maand=saldo.maand,
        max_eenheden=saldo.max_per_taak,
        triage=triage,
    )
    audit.record(
        db,
        actor_type="user",
        actor_id=gebruiker,
        action=RESERVERING,
        target_type="diagnose",
        target_id=str(taak_id),
        details={"maand": taak.maand, "eenheden": taak.max_eenheden},
    )
    db.commit()
    return "gereserveerd", taak


def uitgeput(db: Session, taak: Aanvraag) -> None:
    audit.record(
        db,
        actor_type="ai",
        actor_id="hub-ai",
        action=UITGEPUT,
        target_type="diagnose",
        target_id=str(taak.taak_id),
        details={"maand": taak.maand},
    )
