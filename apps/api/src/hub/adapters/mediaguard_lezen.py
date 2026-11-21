"""Alleen-lezen MediaGuard-overzicht voor het scherm Media (S-P3-082).

Bron: `GET /connector/v1/discover` en `GET /connector/v1/items` (S-P3-610/615, leest onder `observation_read`).
De Hub neemt uitsluitend aantallen, de noodstopstand en meettijden over en bouwt elk veld zelf op. Het item `downloads`
wordt niet opgevraagd: MediaGuard werkt daarbij een index bij en kan de downloadclient aanmelden (geen alleen-lezen).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
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


# Strikt bronschema (mediaguard.openapi.json ItemPage/SystemItem/LaneItem, contract §6.2): exacte typen, een booleaan
# is geen getal, een ontbrekend verplicht veld is geen null. Extra velden worden genegeerd en nooit doorgegeven.
Aantal = Annotated[int, Field(ge=0)]


class _Strikt(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")


class _Limieten(_Strikt):
    max_age_s: dict[str, Aantal] = {}


class _Aanbod(_Strikt):
    app_id: Literal["media-guard-ultimate"]
    schema_version: Literal["1.0"]
    capabilities: list[str]
    item_types: list[str]
    limits: _Limieten = _Limieten()  # ontbreekt = standaard 900 s (§6.2); null of verkeerd gevormd = ongeldig


class _Pagina(_Strikt):
    type: str
    status: str
    reason_code: str | None
    snapshot_id: str | None
    observed_at: str | None
    total: Aantal | None
    items: list[dict[str, Any]]
    next_cursor: str | None


class _Systeem(_Strikt):
    observed_at: str | None
    emergency_stop_active: bool
    emergency_stop_since: str | None
    jobs_failed: Aantal


class _Baan(_Strikt):
    lane: str
    running: Aantal


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
    # Geldigheid per gegeven in seconden; het scherm rekent de ouderdom zelf mee (noodstop volgt status).
    max_age_s: dict[str, int] = {}


def _moment(value: object, now: datetime) -> datetime | None:
    """Een tijd met zone die niet in de toekomst ligt, anders None."""
    try:
        moment = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
    if moment is None or moment.tzinfo is None or moment.astimezone(UTC) > now:
        return None
    return moment.astimezone(UTC)


def aanbod(body: object) -> tuple[list[str], dict[str, int]] | None:
    """Itemtypen en termijnen uit discover; None als het aanbod niet exact klopt of geen leesrecht 'read' geeft."""
    try:
        a = _Aanbod.model_validate(body)
    except ValidationError:
        return None
    return (a.item_types, a.limits.max_age_s) if "read" in a.capabilities else None


def grens(termijnen: dict[str, int], kind: str) -> int:
    """Strengste geldigheid (contract §6.2): de bronwaarde per itemtype, nooit ruimer dan 900 s."""
    return min(termijnen.get(kind, basis.MAX_AGE_S), basis.MAX_AGE_S)


def _tijd(value: object, now: datetime, max_age_s: int = basis.MAX_AGE_S) -> tuple[datetime | None, str | None]:
    observed = _moment(value, now)
    if observed is None:
        return None, "ongeldige bronmeettijd"
    if (now - observed).total_seconds() > max_age_s:
        return observed, "meting verouderd"
    return observed, None


def pagina(
    kind: str, body: object, now: datetime, max_age_s: int = basis.MAX_AGE_S
) -> tuple[Cijfer, list[dict[str, Any]]]:
    """Toets één connectorpagina; geeft een cijfer met het totaal en de items voor verdere telling."""
    try:
        p = _Pagina.model_validate(body)
    except ValidationError:
        return Cijfer(status="onbekend", reden="ongeldig bronantwoord"), []
    if p.type != kind:
        return Cijfer(status="onbekend", reden="ongeldig bronantwoord"), []
    observed, fout = _tijd(p.observed_at, now, max_age_s)
    if p.status != "ok" or p.reason_code is not None:
        reden = BRONREDENEN.get(p.reason_code or "", "onbekende bronreden")
        return Cijfer(status="onbekend", observed_at=observed, reden=reden), []
    if fout:
        return Cijfer(status="onbekend", observed_at=observed, reden=fout), []
    if p.total is None:
        return Cijfer(status="onbekend", observed_at=observed, reden="ongeldig bronantwoord"), []
    # Totaal, ontvangen items en vervolgcursor moeten elkaar bevestigen; anders is het totaal niet te vertrouwen.
    n, verder = len(p.items), p.next_cursor is not None
    if n > p.total or (n == p.total) == verder:
        return Cijfer(status="onbekend", observed_at=observed, reden="tegenstrijdige bronpagina"), []
    return Cijfer(status="gemeten", waarde=p.total, observed_at=observed), p.items


def _volledig(cijfer: Cijfer, body: dict[str, Any]) -> Cijfer | None:
    if body["next_cursor"] is not None or cijfer.waarde != len(body["items"]):
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
        try:
            item = _Systeem.model_validate(items[0])
        except ValidationError:
            item = None
        gemeten_op, tijdfout = _tijd(item.observed_at if item else None, now, max_age_s)
        # Het statusitem heeft een eigen meettijd; een verse pagina maakt een oude noodstopstand niet actueel.
        sinds = item.emergency_stop_since if item else None
        sinds_tijd = _moment(sinds, now)
        if item is None or (sinds is not None and sinds_tijd is None):
            onbekend = Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="ongeldig bronantwoord")
        elif tijdfout:
            onbekend = Cijfer(status="onbekend", observed_at=gemeten_op, reden=tijdfout)
        else:
            actief = item.emergency_stop_active
            stop = Noodstop(
                status="gemeten", actief=actief, sinds=sinds_tijd if actief else None, observed_at=gemeten_op
            )
            return Cijfer(status="gemeten", waarde=item.jobs_failed, observed_at=gemeten_op), stop
    return onbekend, Noodstop(status="onbekend", observed_at=onbekend.observed_at, reden=onbekend.reden)


def av1_cijfer(cijfer: Cijfer, body: dict[str, Any], items: list[dict[str, Any]]) -> Cijfer:
    """AV1 = lopende encodes over de CPU- en GPU-baan samen."""
    if cijfer.status != "gemeten":
        return cijfer
    if (onvolledig := _volledig(cijfer, body)) is not None:
        return onvolledig
    try:
        banen = [_Baan.model_validate(i) for i in items]
    except ValidationError:
        banen = []
    if sorted(b.lane for b in banen) != ["cpu", "gpu"]:
        return Cijfer(status="onbekend", observed_at=cijfer.observed_at, reden="ongeldig bronantwoord")
    return Cijfer(status="gemeten", waarde=sum(b.running for b in banen), observed_at=cijfer.observed_at)


def lees_overzicht(db: Session, settings: Settings, vault: Vault | None, row: AdapterLink, cid: UUID) -> Overzicht:
    bron = Bron(db, settings, "mediaguard", row, None)
    cijfers: dict[str, Cijfer] = {}
    noodstop: Noodstop | None = None
    max_age: dict[str, int] = {}

    def fout(exc: Bronfout | outbound.OutboundError) -> Cijfer:
        return Cijfer(status="onbekend", reden=bron.leesfout(exc).reden)

    try:
        lees = mediaguard_lezer(bron, vault, cid)
        geldig = aanbod(lees("/connector/v1/discover"))
        if geldig is None:
            raise Bronfout("connectorversie niet bevestigd")
        typen, termijnen = geldig
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
            now, termijn = utcnow(), grens(termijnen, kind)
            max_age[naam] = termijn
            cijfer, items = pagina(kind, body, now, termijn)
            if naam == "status":
                cijfer, noodstop = status_cijfer(cijfer, body, items, now, termijn)
            elif naam == "av1":
                cijfer = av1_cijfer(cijfer, body, items)
            cijfers[naam] = cijfer
        if noodstop is None:
            noodstop = Noodstop(status="onbekend", reden=cijfers["status"].reden)
    cijfers["downloads"] = Cijfer(status="onbekend", reden=DOWNLOADS_REDEN)
    return Overzicht(correlation_id=cid, noodstop=noodstop, max_age_s=max_age, **cijfers)
