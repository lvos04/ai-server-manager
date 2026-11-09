"""Alertregels en alerts (B09-003): drempel + duur + hysterese, dempen per regel of per alert.

Regels beheert een beheerder; dempen mag een operator (geen wijziging aan apps of NAS). Alles met audit en
``Idempotency-Key``. Een gedempt alert blijft geëvalueerd en zichtbaar; alleen de melding wordt ``onderdrukt``.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import case, select

from hub import audit
from hub.deps import DB, Admin, Cursor, Idem, Limit, Operator, Viewer, decode_cursor, encode_cursor
from hub.errors import HubError
from hub.models import AlertInstance, AlertRule, NotificationChannel
from hub.monitoring.alerts import hysteresis_ok, instance_dict, rule_dict
from hub.monitoring.timeseries import ONDERWERPEN
from hub.timeutil import utcnow

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

METRIEK = r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$"
Operatoren = Literal["gt", "ge", "lt", "le"]
Ernst = Literal["info", "waarschuwing", "kritiek"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleIn(Strict):
    naam: str = Field(min_length=1, max_length=120)
    metriek: str = Field(min_length=3, max_length=64, pattern=METRIEK)
    onderwerp_type: str | None = None
    onderwerp_id: str | None = Field(default=None, min_length=1, max_length=128)
    bron: str | None = Field(default=None, min_length=1, max_length=96)
    operator: Operatoren
    drempel: float
    herstel_drempel: float
    duur_s: int = Field(default=300, ge=0, le=86400)
    herstel_duur_s: int = Field(default=120, ge=0, le=86400)
    ernst: Ernst = "waarschuwing"
    herhaal_na_s: int | None = Field(default=None, ge=900, le=7 * 86400)
    kanalen: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    ingeschakeld: bool = True

    @field_validator("onderwerp_type")
    @classmethod
    def _otype(cls, v: str | None) -> str | None:
        if v is not None and v not in ONDERWERPEN:
            raise ValueError(f"onbekend onderwerp; kies uit {', '.join(ONDERWERPEN)}")
        return v

    @model_validator(mode="after")
    def _hysteresis(self) -> RuleIn:
        if not hysteresis_ok(self.operator, self.drempel, self.herstel_drempel):
            raise ValueError("de herstelgrens moet aan de veilige kant van de drempel liggen (hysterese)")
        return self


class RulePatch(Strict):
    naam: str | None = Field(default=None, min_length=1, max_length=120)
    drempel: float | None = None
    herstel_drempel: float | None = None
    duur_s: int | None = Field(default=None, ge=0, le=86400)
    herstel_duur_s: int | None = Field(default=None, ge=0, le=86400)
    ernst: Ernst | None = None
    herhaal_na_s: int | None = Field(default=None, ge=900, le=7 * 86400)
    herhaling_uit: bool = False
    kanalen: list[uuid.UUID] | None = Field(default=None, max_length=10)
    ingeschakeld: bool | None = None


class SnoozeIn(Strict):
    minuten: int = Field(ge=0, le=7 * 24 * 60, description="0 = dempen opheffen; maximaal 7 dagen.")
    reden: str | None = Field(default=None, max_length=200)


def _check_channels(db: DB, kanalen: list[uuid.UUID]) -> list[str]:
    if not kanalen:
        return []
    found = set(db.scalars(select(NotificationChannel.id).where(NotificationChannel.id.in_(kanalen))))
    missing = [str(k) for k in kanalen if k not in found]
    if missing:
        raise HubError(422, "validation_error", "Onbekend meldingskanaal.", {"kanalen": missing})
    return [str(k) for k in kanalen]


@router.get("", summary="Alerts per regel en onderwerp (actief eerst), met laatste waarde en veroudering")
def list_alerts(
    db: DB,
    _: Viewer,
    limit: Limit = 100,
    cursor: Cursor = None,
    toestand: Literal["ok", "pending", "firing"] | None = None,
) -> dict[str, Any]:
    offset = decode_cursor(cursor) or 0
    order = case((AlertInstance.toestand == "firing", 0), (AlertInstance.toestand == "pending", 1), else_=2)
    q = select(AlertInstance)
    if toestand:
        q = q.where(AlertInstance.toestand == toestand)
    rows = list(db.scalars(q.order_by(order, AlertInstance.sinds.desc()).offset(offset).limit(limit + 1)))
    rules = {r.id: r for r in db.scalars(select(AlertRule))}
    now = utcnow()
    return {
        "items": [instance_dict(i, rules.get(i.rule_id), now) for i in rows[:limit]],
        "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
    }


@router.post("/{alert_id}/snooze", summary="Alert dempen of dempen opheffen (operator); evaluatie gaat door")
def snooze_alert(alert_id: uuid.UUID, body: SnoozeIn, db: DB, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    inst = db.get(AlertInstance, alert_id)
    if inst is None:
        raise HubError(404, "not_found", "Alert niet gevonden.")
    now = utcnow()
    inst.gedempt_tot = now + timedelta(minutes=body.minuten) if body.minuten else None
    inst.gedempt_door = principal.actor if body.minuten else None
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="alert.snoozed" if body.minuten else "alert.unsnoozed",
        target_type="alert_instance",
        target_id=str(inst.id),
        details={"minuten": body.minuten, "reden": body.reden},
    )
    db.flush()
    return idem.save(200, instance_dict(inst, db.get(AlertRule, inst.rule_id), now))


@router.get("/rules", summary="Alertregels (standaardregels en eigen regels)")
def list_rules(db: DB, _: Viewer) -> dict[str, Any]:
    rows = db.scalars(select(AlertRule).order_by(AlertRule.naam))
    return {"items": [rule_dict(r) for r in rows]}


@router.post("/rules", status_code=201, summary="Alertregel toevoegen (admin)")
def create_rule(body: RuleIn, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    rule = AlertRule(
        naam=body.naam,
        metriek=body.metriek,
        onderwerp_type=body.onderwerp_type,
        onderwerp_id=body.onderwerp_id,
        bron=body.bron,
        operator=body.operator,
        drempel=body.drempel,
        herstel_drempel=body.herstel_drempel,
        duur_s=body.duur_s,
        herstel_duur_s=body.herstel_duur_s,
        ernst=body.ernst,
        herhaal_na_s=body.herhaal_na_s,
        kanalen=_check_channels(db, body.kanalen),
        ingeschakeld=body.ingeschakeld,
        aangemaakt_door=principal.actor,
        bijgewerkt_door=principal.actor,
    )
    db.add(rule)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="alert.rule.created",
        target_type="alert_rule",
        target_id=str(rule.id),
        details=body.model_dump(mode="json"),
    )
    return idem.save(201, rule_dict(rule))


@router.patch("/rules/{rule_id}", summary="Alertregel wijzigen (admin; If-Match met de versie optioneel)")
def update_rule(
    rule_id: uuid.UUID,
    body: RulePatch,
    db: DB,
    principal: Admin,
    idem: Idem,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HubError(404, "not_found", "Alertregel niet gevonden.")
    if if_match is not None and if_match.strip('"') != str(rule.version):
        raise HubError(412, "precondition_failed", "De regel is intussen gewijzigd; laad hem opnieuw.")
    data = body.model_dump(exclude_unset=True, exclude={"herhaling_uit", "kanalen"})
    drempel = data.get("drempel", rule.drempel)
    herstel = data.get("herstel_drempel", rule.herstel_drempel)
    if not hysteresis_ok(rule.operator, drempel, herstel):
        raise HubError(
            422, "validation_error", "De herstelgrens moet aan de veilige kant van de drempel liggen (hysterese)."
        )
    for k, v in data.items():
        if v is not None:
            setattr(rule, k, v)
    if body.herhaling_uit:
        rule.herhaal_na_s = None
    if body.kanalen is not None:
        rule.kanalen = _check_channels(db, body.kanalen)
    rule.version += 1
    rule.bijgewerkt_door, rule.bijgewerkt_op = principal.actor, utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="alert.rule.updated",
        target_type="alert_rule",
        target_id=str(rule.id),
        details=body.model_dump(mode="json", exclude_unset=True),
    )
    db.flush()
    return idem.save(200, rule_dict(rule))


@router.post("/rules/{rule_id}/snooze", summary="Hele regel dempen of dempen opheffen (operator)")
def snooze_rule(rule_id: uuid.UUID, body: SnoozeIn, db: DB, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HubError(404, "not_found", "Alertregel niet gevonden.")
    rule.gedempt_tot = utcnow() + timedelta(minutes=body.minuten) if body.minuten else None
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="alert.rule.snoozed" if body.minuten else "alert.rule.unsnoozed",
        target_type="alert_rule",
        target_id=str(rule.id),
        details={"minuten": body.minuten, "reden": body.reden},
    )
    db.flush()
    return idem.save(200, rule_dict(rule))
