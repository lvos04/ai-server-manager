"""Incidenten-inbox (B01-005, B09-004…006): lijst per prioriteit, detail met bewijs en readback, erkennen, snoozen,
oplossen (alleen als de bron het niet tegenspreekt), notities en een geschoonde supportbundel.

Rechten: kijker leest (gevoelige details alleen voor admin); operator erkent, snoozet, lost op en maakt een
supportbundel. Alle wijzigingen met ``Idempotency-Key``, optioneel ``If-Match`` (versie) en audit; het antwoord is de
readback van het incident na de wijziging.
"""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, or_, select

from hub import __version__, audit
from hub.deps import (
    DB,
    Cursor,
    Idem,
    Limit,
    Operator,
    Principal,
    SettingsDep,
    Viewer,
    decode_cursor,
    encode_cursor,
    get_vault,
)
from hub.errors import HubError
from hub.incidents import readback
from hub.incidents.engine import ACTIEF, add_event
from hub.incidents.view import etag, event_dict, incident_dict
from hub.logsink import MATCHERS
from hub.logsink import to_dict as log_dict
from hub.models import Incident, IncidentEvent, LogEntry
from hub.redact import redact_log_text, redact_log_value
from hub.security import Role
from hub.timeutil import iso, utcnow
from hub.vault import Vault

router = APIRouter(prefix="/api/v1/incidents", tags=["incidenten"])
VaultDep = Annotated[Vault, Depends(get_vault)]

ERNST_ORDER = case((Incident.ernst == "kritiek", 0), (Incident.ernst == "waarschuwing", 1), else_=2)
STATUS_ORDER = case(
    (Incident.status == "open", 0), (Incident.status == "erkend", 1), (Incident.status == "gesnoozed", 2), else_=3
)
StatusFilter = Literal["actief", "open", "erkend", "gesnoozed", "opgelost", "alle"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErkenIn(Strict):
    minuten: int = Field(default=240, ge=5, le=7 * 24 * 60, description="Erkenning verloopt daarna (escalatie).")
    notitie: str | None = Field(default=None, max_length=500)


class SnoozeIn(Strict):
    minuten: int = Field(ge=0, le=7 * 24 * 60, description="0 = snooze opheffen; kritiek hooguit 24 uur.")
    reden: str | None = Field(default=None, max_length=300)


class OplosIn(Strict):
    reden: str = Field(min_length=3, max_length=300)


class NotitieIn(Strict):
    tekst: str = Field(min_length=1, max_length=2000)


def _get(db: DB, incident_id: uuid.UUID, *, lock: bool = False) -> Incident:
    q = select(Incident).where(Incident.id == incident_id)
    inc = db.scalars(q.with_for_update() if lock else q).first()
    if inc is None:
        raise HubError(404, "not_found", "Incident niet gevonden.")
    return inc


def _check_if_match(inc: Incident, if_match: str | None) -> None:
    if if_match is not None and if_match.strip().strip('"') != str(inc.version):
        raise HubError(
            412, "precondition_failed", "Het incident is intussen gewijzigd; laad het opnieuw.", {"versie": inc.version}
        )


def _view(db: DB, settings: Any, inc: Incident, p: Principal) -> dict[str, Any]:
    now = utcnow()
    rb = readback.state(db, settings, inc, now)
    return incident_dict(inc, show_sensitive=p.role == Role.admin, now=now, role=p.role, readback=rb)


def _touch(inc: Incident) -> None:
    inc.bijgewerkt_op, inc.version = utcnow(), inc.version + 1


@router.get("", summary="Incidenten-inbox per prioriteit (actief eerst, dan ernst en laatste gebeurtenis)")
def list_incidents(
    db: DB,
    principal: Viewer,
    limit: Limit = 50,
    cursor: Cursor = None,
    status: StatusFilter = "actief",
    ernst: Literal["info", "waarschuwing", "kritiek"] | None = None,
    bron: str | None = Query(default=None, max_length=64),
    soort: str | None = Query(default=None, max_length=64),
    oorzaak: str | None = Query(default=None, max_length=96, description="Groepeer op oorzaak-sleutel"),
    q: str | None = Query(default=None, max_length=100, description="Zoek in titel en onderwerp"),
) -> dict[str, Any]:
    offset = decode_cursor(cursor) or 0
    stmt = select(Incident)
    if status == "actief":
        stmt = stmt.where(Incident.status.in_(ACTIEF))
    elif status != "alle":
        stmt = stmt.where(Incident.status == status)
    if ernst:
        stmt = stmt.where(Incident.ernst == ernst)
    if bron:
        stmt = stmt.where(Incident.bron == bron)
    if soort:
        stmt = stmt.where(Incident.soort == soort)
    if oorzaak:
        stmt = stmt.where(Incident.oorzaak_sleutel == oorzaak)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(Incident.titel.ilike(like), Incident.onderwerp_naam.ilike(like)))
    rows = list(
        db.scalars(
            stmt.order_by(STATUS_ORDER, ERNST_ORDER, Incident.laatste_op.desc(), Incident.id)
            .offset(offset)
            .limit(limit + 1)
        )
    )
    now = utcnow()
    admin = principal.role == Role.admin
    return {
        "items": [incident_dict(i, show_sensitive=admin, now=now, role=principal.role) for i in rows[:limit]],
        "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
        "bijgewerkt_op": iso(now),
    }


@router.get("/samenvatting", summary="Aantallen per status en ernst, en groepen per oorzaak-hypothese")
def summary(db: DB, _: Viewer) -> dict[str, Any]:
    per = db.execute(select(Incident.status, Incident.ernst, func.count()).group_by(Incident.status, Incident.ernst))
    counts: dict[str, dict[str, int]] = {}
    for status, ernst, n in per:
        counts.setdefault(status, {})[ernst] = int(n)
    groups = db.execute(
        select(Incident.oorzaak_sleutel, func.count(), func.max(Incident.laatste_op))
        .where(Incident.status.in_(ACTIEF), Incident.oorzaak_sleutel.is_not(None))
        .group_by(Incident.oorzaak_sleutel)
        .order_by(func.count().desc())
    )
    return {
        "per_status": counts,
        "actief": sum(n for s, per_e in counts.items() if s in ACTIEF for n in per_e.values()),
        "groepen": [{"oorzaak": k, "aantal": int(n), "laatste": iso(last)} for k, n, last in groups],
        "bijgewerkt_op": iso(utcnow()),
    }


@router.get("/{incident_id}", summary="Incident met hypothese, readback en de laatste gebeurtenissen (ETag)")
def get_incident(incident_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Viewer) -> JSONResponse:
    inc = _get(db, incident_id)
    body = _view(db, settings, inc, principal)
    rows = db.scalars(
        select(IncidentEvent).where(IncidentEvent.incident_id == inc.id).order_by(IncidentEvent.op.desc()).limit(50)
    )
    body["gebeurtenissen"] = [event_dict(e, show_sensitive=principal.role == Role.admin) for e in rows]
    return JSONResponse(body, headers={"ETag": etag(inc)})


@router.get("/{incident_id}/events", summary="Onderliggende gebeurtenissen (nieuwste eerst, cursor)")
def list_incident_events(
    incident_id: uuid.UUID, db: DB, principal: Viewer, limit: Limit = 100, cursor: Cursor = None
) -> dict[str, Any]:
    inc = _get(db, incident_id)
    before = decode_cursor(cursor)
    q = select(IncidentEvent).where(IncidentEvent.incident_id == inc.id)
    if before is not None:
        q = q.where(IncidentEvent.id < before)
    rows = list(db.scalars(q.order_by(IncidentEvent.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [event_dict(e, show_sensitive=principal.role == Role.admin) for e in rows],
        "next_cursor": encode_cursor(rows[-1].id) if more and rows else None,
    }


@router.get("/{incident_id}/bewijs", summary="Toon bewijs: de gegevens achter de hypothese en de readback")
def evidence(incident_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Viewer) -> dict[str, Any]:
    inc = _get(db, incident_id)
    now = utcnow()
    admin = principal.role == Role.admin
    first = db.scalars(
        select(IncidentEvent).where(IncidentEvent.incident_id == inc.id).order_by(IncidentEvent.op).limit(5)
    )
    last = db.scalars(
        select(IncidentEvent).where(IncidentEvent.incident_id == inc.id).order_by(IncidentEvent.op.desc()).limit(10)
    )
    seen: dict[int, dict[str, Any]] = {}
    for e in [*first, *last]:
        seen[e.id] = event_dict(e, show_sensitive=admin)
    hyp = inc.hypothese or {}
    return {
        "incident_id": str(inc.id),
        "hypothese": hyp,
        "zekerheid_uitleg": "Zekerheid is een grove inschatting van een vaste regel, geen statistiek. "
        "'Ik weet het niet' is een geldige uitkomst.",
        "readback": readback.state(db, settings, inc, now),
        "gebeurtenissen": sorted(seen.values(), key=lambda e: e["op"] or ""),
        "trace_ids": list(inc.trace_ids or []),
        "bijgewerkt_op": iso(now),
    }


def _audit(db: DB, p: Principal, action: str, inc: Incident, details: dict[str, Any]) -> None:
    audit.record(
        db,
        actor_type="user",
        actor_id=p.name,
        action=action,
        target_type="incident",
        target_id=str(inc.id),
        details=details,
    )


@router.post("/{incident_id}/erkennen", summary="Erkennen (operator); verloopt na 'minuten' (escalatie)")
def acknowledge(
    incident_id: uuid.UUID,
    body: ErkenIn,
    db: DB,
    settings: SettingsDep,
    principal: Operator,
    idem: Idem,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    inc = _get(db, incident_id, lock=True)
    _check_if_match(inc, if_match)
    if inc.status == "opgelost":
        raise HubError(409, "already_resolved", "Dit incident is al opgelost.")
    now = utcnow()
    inc.status = "erkend"
    inc.erkend_door, inc.erkend_op = principal.actor, now
    inc.erkend_tot = now + timedelta(minutes=body.minuten)
    inc.gesnoozed_tot = inc.gesnoozed_door = None
    _touch(inc)
    add_event(
        db,
        inc,
        ref=f"status:{uuid.uuid4()}",
        soort="status",
        op=now,
        actor=principal.actor,
        force=True,
        samenvatting=f"Erkend door {principal.name} tot {iso(inc.erkend_tot)}."
        + (f" Notitie: {body.notitie}" if body.notitie else ""),
    )
    _audit(db, principal, "incident.acknowledged", inc, {"minuten": body.minuten})
    db.flush()
    return idem.save(200, _view(db, settings, inc, principal))


@router.post("/{incident_id}/snooze", summary="Snoozen of snooze opheffen (operator); meldingen worden onderdrukt")
def snooze(
    incident_id: uuid.UUID,
    body: SnoozeIn,
    db: DB,
    settings: SettingsDep,
    principal: Operator,
    idem: Idem,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    inc = _get(db, incident_id, lock=True)
    _check_if_match(inc, if_match)
    if inc.status == "opgelost":
        raise HubError(409, "already_resolved", "Dit incident is al opgelost.")
    if inc.ernst == "kritiek" and body.minuten > settings.incident_snooze_max_kritiek_minutes:
        raise HubError(
            422,
            "snooze_too_long",
            "Een kritiek incident kan hooguit 24 uur gesnoozed worden.",
            {"max_minuten": settings.incident_snooze_max_kritiek_minutes},
        )
    now = utcnow()
    if body.minuten:
        inc.status, inc.gesnoozed_door = "gesnoozed", principal.actor
        inc.gesnoozed_tot = now + timedelta(minutes=body.minuten)
        text = f"Gesnoozed door {principal.name} tot {iso(inc.gesnoozed_tot)}."
    else:
        inc.status, inc.gesnoozed_tot, inc.gesnoozed_door = "open", None, None
        text = f"Snooze opgeheven door {principal.name}."
    _touch(inc)
    add_event(
        db,
        inc,
        ref=f"status:{uuid.uuid4()}",
        soort="status",
        op=now,
        actor=principal.actor,
        force=True,
        samenvatting=text + (f" Reden: {body.reden}" if body.reden else ""),
    )
    _audit(
        db,
        principal,
        "incident.snoozed" if body.minuten else "incident.unsnoozed",
        inc,
        {"minuten": body.minuten, "reden": body.reden},
    )
    db.flush()
    return idem.save(200, _view(db, settings, inc, principal))


@router.post(
    "/{incident_id}/oplossen",
    summary="Handmatig oplossen (operator); geweigerd als de readback van de bron nog 'actief' meldt",
    responses={409: {"description": "nog_actief: de bron meldt het probleem nog"}},
)
def resolve_incident(
    incident_id: uuid.UUID,
    body: OplosIn,
    db: DB,
    settings: SettingsDep,
    principal: Operator,
    idem: Idem,
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    inc = _get(db, incident_id, lock=True)
    _check_if_match(inc, if_match)
    if inc.status == "opgelost":
        raise HubError(409, "already_resolved", "Dit incident is al opgelost.")
    now = utcnow()
    rb = readback.state(db, settings, inc, now)
    if rb["toestand"] == "actief":
        raise HubError(
            409,
            "nog_actief",
            "Volgens de bron is het probleem nog actief; erken of snooze het incident in plaats van het op te lossen.",
            {"readback": rb},
        )
    inc.status, inc.opgelost_op, inc.opgelost_door = "opgelost", now, principal.actor
    inc.oplos_reden = redact_log_text(f"handmatig: {body.reden} (readback {rb['toestand']})", max_len=300)
    inc.erkend_tot = inc.gesnoozed_tot = None
    _touch(inc)
    add_event(
        db,
        inc,
        ref=f"status:{uuid.uuid4()}",
        soort="status",
        op=now,
        actor=principal.actor,
        force=True,
        samenvatting=f"Handmatig opgelost door {principal.name}: {body.reden} (readback: {rb['toestand']}).",
    )
    _audit(db, principal, "incident.resolved", inc, {"reden": body.reden, "readback": rb["toestand"]})
    db.flush()
    return idem.save(200, _view(db, settings, inc, principal))


@router.post("/{incident_id}/notities", status_code=201, summary="Notitie toevoegen (operator; geschoond opgeslagen)")
def add_note(incident_id: uuid.UUID, body: NotitieIn, db: DB, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    inc = _get(db, incident_id, lock=True)
    now = utcnow()
    row = add_event(
        db,
        inc,
        ref=f"notitie:{uuid.uuid4()}",
        soort="notitie",
        op=now,
        actor=principal.actor,
        samenvatting=body.tekst,
        force=True,
    )
    _touch(inc)
    _audit(db, principal, "incident.note_added", inc, {"lengte": len(body.tekst)})
    db.flush()
    assert row is not None
    return idem.save(201, event_dict(row, show_sensitive=False))


@router.get(
    "/{incident_id}/supportbundel",
    summary="Geschoonde supportbundel (operator): incident, gebeurtenissen en gerelateerde logregels",
)
def support_bundle(
    incident_id: uuid.UUID,
    db: DB,
    settings: SettingsDep,
    principal: Operator,
    vault: VaultDep,
) -> JSONResponse:
    inc = _get(db, incident_id)
    now = utcnow()
    events = list(
        db.scalars(
            select(IncidentEvent)
            .where(IncidentEvent.incident_id == inc.id)
            .order_by(IncidentEvent.op.desc())
            .limit(200)
        )
    )
    window = timedelta(minutes=15)
    traces = [t for t in inc.trace_ids or [] if t]
    log_q = select(LogEntry).where(
        or_(
            LogEntry.trace_id.in_(traces) if traces else LogEntry.id < 0,
            (LogEntry.op >= inc.eerste_op - window)
            & (LogEntry.op <= (inc.opgelost_op or now) + window)
            & (LogEntry.niveau.in_(("warning", "error", "critical"))),
        )
    )
    logs = list(db.scalars(log_q.order_by(LogEntry.op.desc()).limit(300)))
    bundle = {
        "soort": "supportbundel",
        "schema_versie": "1",
        "gemaakt_op": iso(now),
        "hub_versie": __version__,
        "incident": incident_dict(inc, show_sensitive=False, now=now, readback=readback.state(db, settings, inc, now)),
        "gebeurtenissen": [event_dict(e, show_sensitive=False) for e in events],
        "logregels": [log_dict(r) for r in logs],
        "schoning": "Geheimen, tokens, JWT's, PEM-blokken, lange hex/base64-reeksen, e-mailadressen en IP-adressen "
        "zijn gemaskeerd; gevoelige details (classificatie 'sensitive') zijn weggelaten. Controleer de bundel "
        "toch voordat je hem deelt.",
    }
    # Tweede, volledige schoning (verdediging in de diepte) over de hele bundel.
    clean = redact_log_value(bundle, MATCHERS.get(db, vault), max_items=1000, max_str=2000)
    raw = json.dumps(clean, ensure_ascii=False)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="incident.support_bundle",
        target_type="incident",
        target_id=str(inc.id),
        details={"bytes": len(raw), "logregels": len(logs)},
    )
    db.commit()
    return JSONResponse(
        clean,
        headers={
            "Content-Disposition": f'attachment; filename="incident-{inc.id}-supportbundel.json"',
            "Cache-Control": "no-store",
        },
    )
