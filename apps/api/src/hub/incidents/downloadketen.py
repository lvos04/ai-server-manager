"""Lees de diagnose van één wanted-item en houd de context van iedere eigenaar apart."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from cryptography.exceptions import InvalidTag
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import outbound
from hub.adapters import basis, mediaguard, mso
from hub.adapters.binding import binding_is_current, published_ports
from hub.config import Settings
from hub.inventory.store import kind_state
from hub.models import AdapterLink, CatalogApp
from hub.timeutil import UtcDateTime, utcnow
from hub.truenas.connection import current_target
from hub.vault import Vault, VaultError, make_ref

type Eigenaar = Literal["mediaguard", "media-source-optimizer"]
type Onderdeel = Literal["wanted_diagnose", "downloadfouten", "foutredenen", "categoriediagnose", "compatibiliteit"]
INSTELLINGEN = "/instellingen/diensten"

# MediaGuard wanted/diagnosis.py::REASONS. Een nieuwe of vrije bronwaarde wordt niet doorgegeven.
DIAGNOSECODES = frozenset(
    {
        "intentional-exception",
        "unmonitored",
        "not-yet-aired",
        "instance-suspended",
        "root-folder-missing",
        "file-not-linked",
        "import-failed",
        "download-client-failed",
        "stuck-queue",
        "downloading",
        "download-client-missing",
        "no-indexers",
        "indexer-auth",
        "indexer-rate-limit",
        "indexer-offline",
        "incorrect-mapping",
        "rejected-quality",
        "rejected-language",
        "rejected-custom-format",
        "rejected-size",
        "rejected-other",
        "release-available",
        "no-indexer-hit",
        "searched-no-grab",
        "not-searched-yet",
        "unknown",
        "niet-gediagnosticeerd",
    }
)


class Waarneming(BaseModel):
    oorzaakcode: str | None = None
    bronstatus: Literal["aanwezig", "ontbreekt"] | None = None
    observed_at: UtcDateTime | None = None
    reden: str | None = None


class Schakel(Waarneming):
    onderdeel: Onderdeel
    eigenaar: Eigenaar
    href: str
    status: Literal["bekend", "onbekend"]


class Downloadketen(BaseModel):
    wanted_id: int
    mso_change_id: int | None
    correlation_id: UUID
    schakels: list[Schakel]


def _brontijd(ts: object, now: datetime) -> Waarneming:
    try:
        observed = datetime.fromisoformat(ts) if isinstance(ts, str) else None
        if observed is None or observed.tzinfo is None:
            return Waarneming(reden="ongeldige bronmeettijd")
        observed = observed.astimezone(UTC)
        age = (now - observed).total_seconds()
    except (ValueError, OverflowError):
        return Waarneming(reden="ongeldige bronmeettijd")
    if age < 0:
        return Waarneming(reden="ongeldige bronmeettijd")
    if age > basis.MAX_AGE_S:
        return Waarneming(reden="meting verouderd", observed_at=observed)
    return Waarneming(observed_at=observed)


def diagnose(wanted_id: int, body: dict[str, Any], now: datetime) -> Waarneming:
    if type(body.get("wanted_id")) is not int or body["wanted_id"] != wanted_id:
        return Waarneming(reden="antwoord voor een andere aflevering")
    meting = _brontijd(body.get("ts"), now)
    if meting.reden:
        return meting
    code = body.get("primary_code")
    if not isinstance(code, str) or code not in DIAGNOSECODES:
        meting.reden = "onbekende oorzaakcode"
    else:
        meting.oorzaakcode = code
        if code in {"unknown", "niet-gediagnosticeerd"}:
            meting.reden = "oorzaak onbekend bij de bron"
    return meting


def compatibiliteit(body: dict[str, Any], now: datetime) -> Waarneming:
    if body.get("live_source") != "probe":
        return Waarneming(reden="livecontrole ontbreekt")
    meting = _brontijd(body.get("checked_at"), now)
    if meting.reden:
        return meting
    routes = body.get("routes")
    if not isinstance(routes, list):
        return Waarneming(reden="ongeldig bronantwoord")
    standen = [r.get("live") for r in routes if isinstance(r, dict) and r.get("id") == "wanted_diagnosis"]
    if len(standen) == 1 and standen[0] in ("aanwezig", "ontbreekt"):
        meting.bronstatus = standen[0]
    else:
        meting.reden = "routestatus onbekend"
    return meting


class Bronfout(Exception):
    """Bevat uitsluitend een vaste, toonbare Hub-reden."""


def _body(
    response: outbound.Response, *, ontbreekt: str = "bronroute ontbreekt", onbevoegd: str = "sleutel geweigerd"
) -> dict[str, Any]:
    if response.status != 200:
        raise Bronfout(
            {401: onbevoegd, 403: "geen leesrecht", 404: ontbreekt, 429: "bronlimiet bereikt"}.get(
                response.status, "bron onbereikbaar"
            )
        )
    try:
        data = response.json()
    except RecursionError:
        data = None
    if not isinstance(data, dict):
        raise Bronfout("ongeldig bronantwoord")
    return data


@dataclass
class Bron:
    db: Session
    settings: Settings
    eigenaar: Eigenaar
    koppeling: AdapterLink | None
    reden: str | None
    basis_url: str | None = None

    def controleer(self) -> AdapterLink:
        row = self.koppeling
        if self.reden or row is None:
            raise Bronfout(self.reden or "geen koppeling")
        nas = current_target(self.db)
        inventory = kind_state(
            self.db, "apps", target=nas.url if nas else None, ttl_seconds=self.settings.inventory_max_age_seconds
        )
        target = self.db.get(CatalogApp, row.catalog_app_id, populate_existing=True)
        version = self.db.scalar(select(AdapterLink.version).where(AdapterLink.id == row.id))
        if version != row.version or not binding_is_current(row, target, nas, published_ports(inventory)):
            self.reden, self.basis_url = "doelbinding vervallen", None
            raise Bronfout(self.reden)
        self.basis_url = basis.validate_base_url(row.basis_url)
        return row

    def leesfout(self, exc: Bronfout | outbound.OutboundError) -> Waarneming:
        if isinstance(exc, Bronfout):
            return Waarneming(reden=str(exc))
        if exc.reason in {"doelbinding_gewijzigd", "doelbinding_ontbreekt", "adres_niet_toegestaan"}:
            self.reden, self.basis_url = "doelbinding vervallen", None
            return Waarneming(reden=self.reden)
        if exc.reason == "capability_unavailable":
            return Waarneming(reden="leesrecht niet bevestigd")
        return Waarneming(reden="bron onbereikbaar")

    def schakel(self, onderdeel: Onderdeel, scherm: str, meting: Waarneming) -> Schakel:
        if self.reden:
            meting = Waarneming(reden=self.reden)
        return Schakel(
            onderdeel=onderdeel,
            eigenaar=self.eigenaar,
            href=self.basis_url + scherm if self.basis_url else INSTELLINGEN,
            status="onbekend" if meting.reden else "bekend",
            reden=meting.reden,
            oorzaakcode=meting.oorzaakcode,
            bronstatus=meting.bronstatus,
            observed_at=meting.observed_at,
        )


def _bron(db: Session, settings: Settings, eigenaar: Eigenaar, link_id: UUID | None) -> Bron:
    q = select(AdapterLink).where(AdapterLink.app_id == eigenaar)
    if link_id is not None:
        q = q.where(AdapterLink.id == link_id)
    rows = db.scalars(q.limit(2)).all()
    if len(rows) == 1:
        return Bron(db, settings, eigenaar, rows[0], None)
    return Bron(db, settings, eigenaar, None, "kies een koppeling" if rows else "geen koppeling")


def _sleutel(db: Session, row: AdapterLink, vault: Vault | None) -> str:
    ref = make_ref("adapters", f"{mediaguard.APP_ID}.{row.id}")
    if vault is None or row.geheim_ref != ref:
        raise Bronfout("sleutel niet beschikbaar")
    try:
        key = vault.get(db, ref)
    except (InvalidTag, ValueError, VaultError):
        key = None
    if key is None or not re.fullmatch(r"mgk_[A-Za-z0-9_-]{43}", key):
        raise Bronfout("sleutel niet beschikbaar")
    return key


def _mediaguard(bron: Bron, vault: Vault | None, wanted_id: int, cid: UUID) -> list[Schakel]:
    def lees(pad: str, *, cache: bool = False) -> dict[str, Any]:
        row = bron.controleer()
        response = outbound.request(
            row.basis_url,
            "GET",
            pad,
            policy=basis.bound_policy(row, bron.settings.outbound_policy()),
            headers={"X-Api-Key": sleutel, "X-Correlation-Id": str(cid)},
            query={"cached": "true"} if cache else None,
            max_bytes=basis.MAX_RESPONSE_BYTES,
        )
        return _body(response, ontbreekt="geen gecachte diagnose" if cache else "bronroute ontbreekt")

    try:
        sleutel = _sleutel(bron.db, bron.controleer(), vault)
        identiteit = lees("/api/v1/auth/me")
        if (
            identiteit.get("username") != "apikey:hub"
            or identiteit.get("role") != "viewer"
            or "scopes" not in identiteit
            or identiteit["scopes"] not in (None, [])
        ):
            raise Bronfout("geen leesrecht")
    except (Bronfout, outbound.OutboundError) as exc:
        diagnosemeting = downloadmeting = bron.leesfout(exc)
    else:
        try:
            data = lees(f"/api/v1/wanted/{wanted_id}/diagnosis", cache=True)
            diagnosemeting = diagnose(wanted_id, data, utcnow())
        except (Bronfout, outbound.OutboundError) as exc:
            diagnosemeting = bron.leesfout(exc)
        try:
            groepen = lees("/api/v1/downloads/failures").get("groups")
            if not isinstance(groepen, list):
                raise Bronfout("ongeldig bronantwoord")
            downloadmeting = Waarneming(reden="downloadgroepen zonder verwijzing naar deze aflevering")
        except (Bronfout, outbound.OutboundError) as exc:
            downloadmeting = bron.leesfout(exc)
    return [
        bron.schakel("wanted_diagnose", "/ontbrekend", diagnosemeting),
        bron.schakel("downloadfouten", "/downloads", downloadmeting),
    ]


def _mso(bron: Bron, cid: UUID) -> list[Schakel]:
    def lees(pad: str) -> dict[str, Any]:
        row = bron.controleer()
        antwoord = basis.read_request(row, pad, policy=bron.settings.outbound_policy(), correlation_id=cid)
        return _body(antwoord, onbevoegd="aanmelding vereist")

    toegang: Waarneming | None
    try:
        mso.Liveness.model_validate(lees(mso.HEALTH_PATH), strict=True)
    except ValidationError:
        toegang = Waarneming(reden="ongeldig bronantwoord")
    except (Bronfout, outbound.OutboundError) as exc:
        toegang = bron.leesfout(exc)
    else:
        toegang = None

    def context(pad: str) -> Waarneming:
        if toegang is not None:
            return toegang
        try:
            # De bestaande MSO-adapter weigert beschermde routes vóór transport
            # zolang MSO de exacte machinerechten niet verifieerbaar verklaart.
            data = lees(pad)
        except (Bronfout, outbound.OutboundError) as exc:
            return bron.leesfout(exc)
        if pad == "/api/v1/mediaguard/compat":
            return compatibiliteit(data, utcnow())
        if not isinstance(data.get("items"), list):
            return Waarneming(reden="ongeldig bronantwoord")
        return Waarneming(reden="woordenlijst zonder verwijzing naar deze aflevering")

    fouten = context("/api/v1/usenet/failure-reasons")
    compat = context("/api/v1/mediaguard/compat")
    # /api/v1/usenet/categories/diagnosis staat buiten MSO READ_ROUTES. Nooit verversen.
    categorie = Waarneming(reden=bron.reden or "geen leesrecht")
    return [
        bron.schakel("foutredenen", "/downloads", fouten),
        bron.schakel("categoriediagnose", "/usenet-providers", categorie),
        bron.schakel("compatibiliteit", "/mediaguard", compat),
    ]


def lees_keten(
    db: Session,
    settings: Settings,
    vault: Vault | None,
    wanted_id: int,
    mso_change_id: int | None,
    mediaguard_link_id: UUID | None,
    mso_link_id: UUID | None,
    correlation_id: UUID,
) -> Downloadketen:
    mg_bron = _bron(db, settings, "mediaguard", mediaguard_link_id)
    mso_bron = _bron(db, settings, "media-source-optimizer", mso_link_id)
    return Downloadketen(
        wanted_id=wanted_id,
        mso_change_id=mso_change_id,
        correlation_id=correlation_id,
        schakels=[*_mediaguard(mg_bron, vault, wanted_id, correlation_id), *_mso(mso_bron, correlation_id)],
    )
