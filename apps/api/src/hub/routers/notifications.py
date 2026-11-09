"""Meldingskanalen (Gotify) en meldingen, inclusief ``notification.send`` (R0).

- Kanalen beheert alleen een beheerder; het applicatietoken gaat de vault in en komt nooit terug (alleen de laatste
  4 tekens en de datum).
- ``POST /api/v1/notifications`` is de getypte actie ``notification.send`` (risicoklasse R0: alleen een bericht, geen
  wijziging aan apps of NAS) met harde grenzen, audit en dezelfde rate-limit als alerts. De policy-engine (P2)
  gebruikt dezelfde adapter.
- Een testmelding wordt echt verstuurd en het echte resultaat teruggegeven — nooit gesimuleerd succes.
"""

from __future__ import annotations

import re
import uuid
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from hub import audit
from hub.deps import DB, Admin, Cursor, Idem, Limit, Operator, SettingsDep, decode_cursor, encode_cursor, get_vault
from hub.errors import HubError
from hub.models import Notification, NotificationChannel, VaultSecret
from hub.monitoring.alerts import ERNST, ERNST_RANK
from hub.notify import gotify
from hub.outbound import OutboundError, validate_base_url
from hub.timeutil import iso, utcnow
from hub.vault import Vault, make_ref

router = APIRouter(prefix="/api/v1/notifications", tags=["meldingen"])
VaultDep = Annotated[Vault, Depends(get_vault)]

Ernst = Literal["info", "waarschuwing", "kritiek"]
HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"
MELDING_KANAAL = {
    "token_geweigerd": "Gotify weigerde het token; vervang het applicatietoken. Tot dan wordt niets verstuurd.",
    "token_ontbreekt": "Er is geen token ingesteld.",
    "niet_bereikbaar": "Gotify is niet bereikbaar.",
    "tijdslimiet": "Gotify reageerde niet op tijd.",
    "tls_fout": "Het HTTPS-certificaat van Gotify wordt niet vertrouwd.",
    "redirect_niet_gevolgd": "Gotify antwoordde met een doorverwijzing; die volgt de Hub nooit.",
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuietHours(Strict):
    van: str = Field(pattern=HHMM)
    tot: str = Field(pattern=HHMM)
    tijdzone: str = Field(min_length=1, max_length=64)

    @field_validator("tijdzone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("onbekende tijdzone (IANA-naam, bv. Europe/Amsterdam)") from exc
        return v


class ChannelIn(Strict):
    soort: Literal["gotify"] = "gotify"
    naam: str = Field(min_length=1, max_length=64)
    basis_url: str = Field(min_length=8, max_length=512)
    token: str = Field(min_length=8, max_length=256, description="Gotify-applicatietoken (nooit een client-token).")
    min_ernst: Ernst = "info"
    stille_uren: QuietHours | None = None
    max_per_venster: int = Field(default=10, ge=1, le=100)
    venster_s: int = Field(default=900, ge=60, le=86400)
    ingeschakeld: bool = True


class ChannelPatch(Strict):
    naam: str | None = Field(default=None, min_length=1, max_length=64)
    basis_url: str | None = Field(default=None, min_length=8, max_length=512)
    token: str | None = Field(default=None, min_length=8, max_length=256)
    min_ernst: Ernst | None = None
    stille_uren: QuietHours | None = None
    stille_uren_wissen: bool = False
    max_per_venster: int | None = Field(default=None, ge=1, le=100)
    venster_s: int | None = Field(default=None, ge=60, le=86400)
    ingeschakeld: bool | None = None


class SendIn(Strict):
    """Getypte parameters van ``notification.send`` (R0) met harde grenzen."""

    kanaal_id: uuid.UUID | None = None
    titel: str = Field(min_length=1, max_length=120)
    bericht: str = Field(min_length=1, max_length=2000)
    ernst: Ernst = "info"


def _url(settings: Any, url: str) -> str:
    try:
        return validate_base_url(url, allow_loopback=settings.outbound_allow_loopback)
    except OutboundError as exc:
        raise HubError(
            422, "validation_error", "Ongeldig adres voor Gotify.", {"reden": exc.reason, "detail": exc.detail}
        ) from None


def channel_dict(db: Any, ch: NotificationChannel) -> dict[str, Any]:
    secret = db.scalar(select(VaultSecret).where(VaultSecret.ref == ch.token_ref))
    return {
        "id": str(ch.id),
        "soort": ch.soort,
        "naam": ch.naam,
        "basis_url": ch.basis_url,
        "token": {
            "ingesteld": secret is not None,
            "laatste4": secret.last4 if secret else None,
            "gewijzigd_op": iso(secret.updated_at) if secret else None,
        },
        "min_ernst": ch.min_ernst,
        "stille_uren": ch.stille_uren,
        "max_per_venster": ch.max_per_venster,
        "venster_s": ch.venster_s,
        "ingeschakeld": ch.ingeschakeld,
        "status": {
            "laatste_status": ch.laatste_status or "unknown",
            "laatste_reden": ch.laatste_reden,
            "melding": MELDING_KANAAL.get(ch.laatste_reden or "", "") if ch.laatste_reden else "",
            "laatste_op": iso(ch.laatste_op),
            "gotify_versie": ch.laatste_versie,
        },
        "onderdrukt": {"aantal": ch.onderdrukt_teller, "sinds": iso(ch.onderdrukt_sinds)},
        "versie": ch.version,
    }


def notification_dict(n: Notification) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "kanaal_id": str(n.kanaal_id),
        "bron": n.bron,
        "soort": n.soort,
        "alert_id": str(n.alert_instance_id) if n.alert_instance_id else None,
        "ernst": n.ernst,
        "titel": n.titel,
        "bericht": n.bericht,
        "status": n.status,
        "reden": n.reden,
        "pogingen": n.pogingen,
        "volgende_poging_op": iso(n.volgende_poging_op) if n.status in ("wachtrij", "uitgesteld") else None,
        "aangemaakt_op": iso(n.aangemaakt_op),
        "aangemaakt_door": n.aangemaakt_door,
        "verzonden_op": iso(n.verzonden_op),
    }


@router.get("/channels", summary="Meldingskanalen (token nooit terug, alleen de laatste 4 tekens)")
def list_channels(db: DB, _: Operator) -> dict[str, Any]:
    rows = db.scalars(select(NotificationChannel).order_by(NotificationChannel.naam))
    return {"items": [channel_dict(db, c) for c in rows]}


@router.post("/channels", status_code=201, summary="Gotify-kanaal toevoegen (admin; applicatietoken in de vault)")
def create_channel(
    body: ChannelIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem, vault: VaultDep
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    url = _url(settings, body.basis_url)
    cid = uuid.uuid4()
    ref = make_ref("meldingen", str(cid))
    ch = NotificationChannel(
        id=cid,
        soort=body.soort,
        naam=body.naam,
        basis_url=url,
        token_ref=ref,
        min_ernst=body.min_ernst,
        stille_uren=body.stille_uren.model_dump() if body.stille_uren else None,
        max_per_venster=body.max_per_venster,
        venster_s=body.venster_s,
        ingeschakeld=body.ingeschakeld,
        onderdrukt_teller=0,
        aangemaakt_door=principal.actor,
        bijgewerkt_door=principal.actor,
    )
    db.add(ch)
    vault.put(db, ref, body.token, actor=principal.actor)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="notification.channel.created",
        target_type="notification_channel",
        target_id=str(cid),
        details={"soort": body.soort, "naam": body.naam, "basis_url": url},
    )
    return idem.save(201, channel_dict(db, ch))


@router.patch("/channels/{channel_id}", summary="Kanaal wijzigen (admin); een nieuw token heft 'token geweigerd' op")
def update_channel(
    channel_id: uuid.UUID,
    body: ChannelPatch,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    idem: Idem,
    vault: VaultDep,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    ch = db.get(NotificationChannel, channel_id)
    if ch is None:
        raise HubError(404, "not_found", "Kanaal niet gevonden.")
    changed: list[str] = []
    if body.naam is not None:
        ch.naam = body.naam
        changed.append("naam")
    if body.basis_url is not None:
        ch.basis_url = _url(settings, body.basis_url)
        ch.laatste_status = ch.laatste_reden = None
        changed.append("basis_url")
    if body.token is not None:
        vault.put(db, ch.token_ref, body.token, actor=principal.actor)
        if ch.laatste_reden in ("token_geweigerd", "token_ontbreekt"):
            ch.laatste_status = ch.laatste_reden = None
        changed.append("token")
    if body.min_ernst is not None:
        ch.min_ernst = body.min_ernst
        changed.append("min_ernst")
    if body.stille_uren is not None:
        ch.stille_uren = body.stille_uren.model_dump()
        changed.append("stille_uren")
    elif body.stille_uren_wissen:
        ch.stille_uren = None
        changed.append("stille_uren")
    for field in ("max_per_venster", "venster_s", "ingeschakeld"):
        value = getattr(body, field)
        if value is not None:
            setattr(ch, field, value)
            changed.append(field)
    if changed:
        ch.version += 1
        ch.bijgewerkt_door, ch.bijgewerkt_op = principal.actor, utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="notification.channel.updated",
        target_type="notification_channel",
        target_id=str(ch.id),
        details={"velden": changed},
    )
    db.flush()
    return idem.save(200, channel_dict(db, ch))


@router.post("/channels/{channel_id}/test", summary="Testmelding echt versturen (admin) en het echte resultaat tonen")
def test_channel(
    channel_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Admin, idem: Idem, vault: VaultDep
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    ch = db.get(NotificationChannel, channel_id)
    if ch is None:
        raise HubError(404, "not_found", "Kanaal niet gevonden.")
    now = utcnow()
    policy = settings.outbound_policy()
    versie, versie_reden = gotify.version(ch.basis_url, policy)
    token = vault.get(db, ch.token_ref)
    n = Notification(
        kanaal_id=ch.id,
        dedupe_sleutel=f"test:{idem.key}",
        bron="test",
        soort="bericht",
        ernst="info",
        titel="Testmelding van de Hub",
        bericht=f"Testmelding, aangevraagd door {principal.name}. Komt dit bericht aan, dan werkt het kanaal.",
        status="wachtrij",
        volgende_poging_op=now,
        aangemaakt_op=now,
        aangemaakt_door=principal.actor,
        pogingen=1,
    )
    db.add(n)
    res = (
        gotify.send(ch.basis_url, token, titel=n.titel, bericht=n.bericht, ernst="info", policy=policy)
        if token
        else gotify.SendResult(False, "token_ontbreekt", definitief=True)
    )
    if res.ok:
        n.status, n.verzonden_op, n.extern_id = "verzonden", now, res.extern_id
    else:
        n.status, n.reden = "mislukt", res.reden
    ch.laatste_status, ch.laatste_reden, ch.laatste_op = ("ok" if res.ok else "fout"), res.reden, now
    if versie:
        ch.laatste_versie = versie
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="notification.channel.tested",
        target_type="notification_channel",
        target_id=str(ch.id),
        details={"verzonden": res.ok, "reden": res.reden, "http": res.http},
    )
    db.flush()
    return idem.save(
        200,
        {
            "verzonden": res.ok,
            "reden": res.reden,
            "melding": "Testmelding verstuurd." if res.ok else MELDING_KANAAL.get(res.reden or "", "Mislukt."),
            "http": res.http,
            "gotify_versie": versie,
            "versie_reden": versie_reden,
            "kanaal": channel_dict(db, ch),
        },
    )


@router.get("", summary="Meldingen (nieuwste eerst) met status: wachtrij, uitgesteld, verzonden, onderdrukt, mislukt")
def list_notifications(
    db: DB,
    _: Operator,
    limit: Limit = 50,
    cursor: Cursor = None,
    status: Literal["wachtrij", "uitgesteld", "verzonden", "onderdrukt", "mislukt"] | None = None,
    kanaal_id: uuid.UUID | None = None,
    bron: str | None = Query(default=None, pattern=r"^(alert|handmatig|test|samenvatting)$"),
) -> dict[str, Any]:
    offset = decode_cursor(cursor) or 0
    q = select(Notification)
    if status:
        q = q.where(Notification.status == status)
    if kanaal_id:
        q = q.where(Notification.kanaal_id == kanaal_id)
    if bron:
        q = q.where(Notification.bron == bron)
    rows = list(db.scalars(q.order_by(Notification.aangemaakt_op.desc()).offset(offset).limit(limit + 1)))
    return {
        "items": [notification_dict(n) for n in rows[:limit]],
        "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
    }


@router.post("", status_code=202, summary="notification.send (R0): bericht in de wachtrij (operator, Idempotency-Key)")
def send_notification(body: SendIn, db: DB, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    now = utcnow()
    q = select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True))
    if body.kanaal_id is not None:
        q = q.where(NotificationChannel.id == body.kanaal_id)
    chans = [c for c in db.scalars(q) if ERNST_RANK[body.ernst] >= ERNST_RANK.get(c.min_ernst, 0)]
    if not chans:
        raise HubError(
            409,
            "geen_kanaal",
            "Er is geen ingeschakeld meldingskanaal dat deze ernst ontvangt; er is niets verstuurd.",
            {"ernst": body.ernst, "kanaal_id": str(body.kanaal_id) if body.kanaal_id else None},
        )
    ids = []
    for ch in chans:
        n = Notification(
            kanaal_id=ch.id,
            dedupe_sleutel=f"handmatig:{idem.key}",
            bron="handmatig",
            soort="bericht",
            ernst=body.ernst,
            titel=re.sub(r"\s+", " ", body.titel).strip(),
            bericht=body.bericht,
            status="wachtrij",
            volgende_poging_op=now,
            aangemaakt_op=now,
            aangemaakt_door=principal.actor,
        )
        db.add(n)
        db.flush()
        ids.append(str(n.id))
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="notification.send",
        target_type="notification",
        target_id=",".join(ids)[:128],
        details={"risico": "R0", "ernst": body.ernst, "kanalen": len(chans), "titel": body.titel},
    )
    return idem.save(
        202,
        {
            "action_id": "notification.send",
            "risico": "R0",
            "meldingen": ids,
            "status": "wachtrij",
            "toelichting": "De worker verstuurt de melding; rate-limit en stille uren gelden ook hier.",
        },
    )


__all__ = ["ERNST", "router"]
