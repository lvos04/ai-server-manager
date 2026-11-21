"""Alleen-lezen MediaGuard-overzicht voor het scherm Media (S-P3-082).

Bron: `GET /connector/v1/discover` en `GET /connector/v1/items` (S-P3-610/615, leest onder `observation_read`).
De Hub neemt uitsluitend aantallen, de noodstopstand en meettijden over en bouwt elk veld zelf op. Het item `downloads`
wordt niet opgevraagd: MediaGuard werkt daarbij een index bij en kan de downloadclient aanmelden (geen alleen-lezen).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from hub import outbound
from hub.adapters import basis
from hub.config import Settings
from hub.incidents.downloadketen import Bron, Bronfout, mediaguard_lezer
from hub.models import AdapterLink
from hub.timeutil import UtcDateTime, utcnow
from hub.vault import Vault

# Hub-naam -> connectortype. `limit` 1 volstaat waar alleen het totaal telt.
TYPES: dict[str, tuple[str, int]] = {
    "wanted": ("wanted", 1),
    "status": ("status", 200),
    "av1": ("av1_lanes", 200),
    "incidenten": ("incidents", 1),
}
# Vaste redenen van de bron; een andere waarde wordt niet doorgegeven.
BRONREDENEN = {
    "meting_ontbreekt": "meting ontbreekt bij de bron",
    "meting_verouderd": "meting verouderd",
    "meettijd_ongeldig": "ongeldige bronmeettijd",
    "bron_onbereikbaar": "bron onbereikbaar",
}
MEDIASERVERS_REDEN = "MediaGuard heeft nog geen bijwerkingsvrije mediaserverbron"
DOWNLOADS_REDEN = "MediaGuard heeft nog geen bijwerkingsvrije downloadbron"


class Cijfer(BaseModel):
    status: Literal["gemeten", "onbekend"]
    waarde: int | None = None
    observed_at: UtcDateTime | None = None
    reden: str | None = None


class Noodstop(BaseModel):
    status: Literal["gemeten", "onbekend"]
    actief: bool | None = None
    sinds: UtcDateTime | None = None
    observed_at: UtcDateTime | None = None
    reden: str | None = None


class Mediaservers(BaseModel):
    status: Literal["onbekend"] = "onbekend"
    servers: None = None
    reden: str = MEDIASERVERS_REDEN


class Overzicht(BaseModel):
    correlation_id: UUID
    wanted: Cijfer
    status: Cijfer
    downloads: Cijfer
    av1: Cijfer
    incidenten: Cijfer
    noodstop: Noodstop
    mediaservers: Mediaservers = Mediaservers()


def _moment(value: object, now: datetime) -> datetime | None:
    """Een tijd met zone die niet in de toekomst ligt, anders None."""
    try:
        moment = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
    if moment is None or moment.tzinfo is None or moment.astimezone(UTC) > now:
        return None
    return moment.astimezone(UTC)


def grens(aanbod: dict[str, Any], kind: str) -> int:
    """Strengste geldigheid (contract §6.2): de bronwaarde per itemtype, nooit ruimer dan 900 s; ongeldig = 0."""
    limits = aanbod.get("limits")
    termijnen = limits.get("max_age_s") if isinstance(limits, dict) else None
    if not isinstance(termijnen, dict) or kind not in termijnen:
        return basis.MAX_AGE_S
    waarde = termijnen[kind]
    return min(waarde, basis.MAX_AGE_S) if type(waarde) is int and waarde >= 0 else 0


def _tijd(value: object, now: datetime, max_age_s: int = basis.MAX_AGE_S) -> tuple[datetime | None, str | None]:
    observed = _moment(value, now)
    if observed is None:
        return None, "ongeldige bronmeettijd"
    if (now - observed).total_seconds() > max_age_s:
        return observed, "meting verouderd"
    return observed, None


def _int(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def pagina(
    kind: str, body: dict[str, Any], now: datetime, max_age_s: int = basis.MAX_AGE_S
) -> tuple[Cijfer, list[dict[str, Any]]]:
    """Toets één connectorpagina; geeft een cijfer met het totaal en de items voor verdere telling."""
    if body.get("type") != kind:
        return Cijfer(status="onbekend", reden="ongeldig bronantwoord"), []
    observed, fout = _tijd(body.get("observed_at"), now, max_age_s)
    if body.get("status") != "ok" or body.get("reason_code") is not None:
        code = body.get("reason_code")
        reden = BRONREDENEN.get(code, "onbekende bronreden") if isinstance(code, str) else "onbekende bronreden"
        return Cijfer(status="onbekend", observed_at=observed, reden=reden), []
    if fout:
        return Cijfer(status="onbekend", observed_at=observed, reden=fout), []
    total, items = _int(body.get("total")), body.get("items")
    if total is None or not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        return Cijfer(status="onbekend", observed_at=observed, reden="ongeldig bronantwoord"), []
    # Totaal, ontvangen items en vervolgcursor moeten elkaar bevestigen; anders is het totaal niet te vertrouwen.
    n, verder = len(items), body.get("next_cursor") is not None
    if n > total or (n == total) == verder:
        return Cijfer(status="onbekend", observed_at=observed, reden="tegenstrijdige bronpagina"), []
    return Cijfer(status="gemeten", waarde=total, observed_at=observed), items


def _volledig(cijfer: Cijfer, body: dict[str, Any]) -> Cijfer | None:
    if body.get("next_cursor") is not None or cijfer.waarde != len(body["items"]):
        return Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="onvolledige bronpagina")
    return None


def status_cijfer(
    cijfer: Cijfer, body: dict[str, Any], items: list[dict[str, Any]], now: datetime, max_age_s: int = basis.MAX_AGE_S
) -> tuple[Cijfer, Noodstop]:
    """Status = mislukte jobs; de noodstop komt uit hetzelfde statusitem."""
    onbekend = _volledig(cijfer, body) if cijfer.status == "gemeten" else cijfer
    if onbekend is None and len(items) != 1:
        onbekend = Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="ongeldig bronantwoord")
    if onbekend is None:
        item = items[0]
        # Het statusitem heeft een eigen meettijd; een verse pagina maakt een oude noodstopstand niet actueel.
        gemeten_op, tijdfout = _tijd(item.get("observed_at"), now, max_age_s)
        actief, mislukt = item.get("emergency_stop_active"), _int(item.get("jobs_failed"))
        sinds = item.get("emergency_stop_since")
        sinds_tijd = _moment(sinds, now)
        if tijdfout:
            onbekend = Cijfer(status="onbekend", observed_at=gemeten_op, reden=tijdfout)
        elif type(actief) is not bool or mislukt is None or (sinds is not None and sinds_tijd is None):
            onbekend = Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="ongeldig bronantwoord")
        else:
            stop = Noodstop(
                status="gemeten", actief=actief, sinds=sinds_tijd if actief else None, observed_at=gemeten_op
            )
            return Cijfer(status="gemeten", waarde=mislukt, observed_at=gemeten_op), stop
    return onbekend, Noodstop(status="onbekend", observed_at=onbekend.observed_at, reden=onbekend.reden)


def av1_cijfer(cijfer: Cijfer, body: dict[str, Any], items: list[dict[str, Any]]) -> Cijfer:
    """AV1 = lopende encodes over de CPU- en GPU-baan samen."""
    if cijfer.status != "gemeten":
        return cijfer
    if (onvolledig := _volledig(cijfer, body)) is not None:
        return onvolledig
    lopend = [_int(i.get("running")) for i in items]
    if sorted(str(i.get("lane")) for i in items) != ["cpu", "gpu"] or None in lopend:
        return Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="ongeldig bronantwoord")
    return Cijfer(status="gemeten", waarde=sum(v for v in lopend if v is not None), observed_at=cijfer.observed_at)


def lees_overzicht(db: Session, settings: Settings, vault: Vault | None, row: AdapterLink, cid: UUID) -> Overzicht:
    bron = Bron(db, settings, "mediaguard", row, None)
    cijfers: dict[str, Cijfer] = {}
    noodstop: Noodstop | None = None

    def fout(exc: Bronfout | outbound.OutboundError) -> Cijfer:
        return Cijfer(status="onbekend", reden=bron.leesfout(exc).reden)

    try:
        lees = mediaguard_lezer(bron, vault, cid)
        aanbod = lees("/connector/v1/discover")
        typen = aanbod.get("item_types")
        if (
            aanbod.get("app_id") != "media-guard-ultimate"
            or aanbod.get("schema_version") != "1.0"
            or not isinstance(typen, list)
            or not isinstance(capaciteiten := aanbod.get("capabilities"), list)
            or "read" not in capaciteiten
        ):
            raise Bronfout("connectorversie niet bevestigd")
    except (Bronfout, outbound.OutboundError) as exc:
        algemeen = fout(exc)
        cijfers = dict.fromkeys(TYPES, algemeen)
        noodstop = Noodstop(status="onbekend", reden=algemeen.reden)
    else:
        for naam, (kind, limit) in TYPES.items():
            if kind not in typen:
                cijfers[naam] = Cijfer(status="onbekend", reden="bron levert dit gegeven niet")
                continue
            try:
                body = lees("/connector/v1/items", query={"type": kind, "limit": str(limit)})
            except (Bronfout, outbound.OutboundError) as exc:
                cijfers[naam] = fout(exc)
                continue
            now, termijn = utcnow(), grens(aanbod, kind)
            cijfer, items = pagina(kind, body, now, termijn)
            if naam == "status":
                cijfer, noodstop = status_cijfer(cijfer, body, items, now, termijn)
            elif naam == "av1":
                cijfer = av1_cijfer(cijfer, body, items)
            cijfers[naam] = cijfer
        if noodstop is None:
            noodstop = Noodstop(status="onbekend", reden=cijfers["status"].reden)
    cijfers["downloads"] = Cijfer(status="onbekend", reden=DOWNLOADS_REDEN)
    return Overzicht(correlation_id=cid, noodstop=noodstop, **cijfers)
