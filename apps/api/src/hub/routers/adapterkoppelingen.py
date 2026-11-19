"""Beheer en contactproef voor koppelingen met bestaande apps (S-P3-020)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select

from hub import audit
from hub.adapters import basis
from hub.deps import DB, Admin, AnyUser, Cursor, Idem, Limit, Principal, SettingsDep, get_vault
from hub.errors import HubError
from hub.models import AdapterLink, CatalogApp, VaultSecret
from hub.outbound import OutboundError
from hub.timeutil import UtcDateTime
from hub.vault import Vault, make_ref

router = APIRouter(prefix="/api/v1/adapterkoppelingen", tags=["adapterkoppelingen"])
VaultDep = Annotated[Vault, Depends(get_vault)]
Credential = Annotated[
    SecretStr | None,
    Header(
        alias="X-Adapter-Credential", description="Alleen invoer. Gebruik een nieuwe Idempotency-Key bij wijziging."
    ),
]
IfMatch = Annotated[str | None, Header(alias="If-Match")]
BasisUrl = Annotated[str, Field(min_length=8, max_length=512)]


class LinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: basis.AppId
    catalog_app_id: uuid.UUID
    basis_url: BasisUrl
    doel_bevestigd: Literal[True]


class LinkPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_app_id: uuid.UUID | None = None
    basis_url: BasisUrl | None = None
    doel_bevestigd: bool = False


class LinkView(BaseModel):
    id: uuid.UUID
    app_id: str
    catalog_app_id: uuid.UUID
    basis_url: str
    laatste4: str
    ingevoerd_op: UtcDateTime
    verbinding: basis.Measurement
    gezondheid: basis.Measurement
    version: int


class LinkList(BaseModel):
    items: list[LinkView]
    next_cursor: str | None


class LinkReceipt(BaseModel):
    id: uuid.UUID
    version: int


class Verwijderd(BaseModel):
    verwijderd: Literal[True]


def _view(row: AdapterLink) -> LinkView:
    measurement = basis.Measurement(status=row.laatste_status or "unknown", observed_at=row.observed_at)
    if row.laatste_fout:
        measurement = basis.Measurement(
            status="unknown",
            reason_code=row.laatste_fout,
            observed_at=row.observed_at,
            laatste_status=measurement.status if row.observed_at else None,
        )
    return LinkView(
        id=row.id,
        app_id=row.app_id,
        catalog_app_id=row.catalog_app_id,
        basis_url=row.basis_url,
        laatste4=row.laatste4,
        ingevoerd_op=row.ingevoerd_op,
        verbinding=basis.fresh_measurement(measurement, max_age_s=row.max_age_s or basis.MAX_AGE_S),
        gezondheid=basis.Measurement(status="unknown", reason_code="capability_unavailable"),
        version=row.version,
    )


def _link(db: DB, link_id: uuid.UUID, *, lock: bool = False) -> AdapterLink:
    row = db.get(AdapterLink, link_id, with_for_update=lock)
    if row is None:
        raise HubError(404, "not_found", "Adapterkoppeling niet gevonden.")
    return row


def _target(db: DB, app_id: str, catalog_app_id: uuid.UUID) -> None:
    target = db.get(CatalogApp, catalog_app_id, with_for_update=True)
    if target is None or not target.aanwezig or target.app_id != app_id or target.soort != "bestaand":
        raise HubError(
            409, "conflict", "De doelinstantie is niet geregistreerd voor deze app.", {"reason": "doelbinding"}
        )


def _destination(url: str, credential: str) -> tuple[str, list[str]]:
    try:
        base = basis.validate_base_url(url)
        if credential.casefold() in base.casefold():
            raise OutboundError("adres_ongeldig")
        return base, basis.resolve_binding(base)
    except OutboundError as exc:
        raise HubError(422, "validation_error", "Ongeldig basisadres.", {"reason": exc.reason}) from None


def _credential(value: SecretStr | None) -> str:
    if value is None:
        raise HubError(422, "validation_error", "Voer een nieuw adaptercredential in.")
    secret = value.get_secret_value()
    if not re.fullmatch(r"[!-~]{8,512}", secret):
        raise HubError(422, "validation_error", "De waarde van het adaptercredential is ongeldig.")
    return secret


def _record(db: DB, principal: Principal, row: AdapterLink, action: str) -> None:
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action=f"adapter_link.{action}",
        target_type="adapter_link",
        target_id=str(row.id),
        details={"app_id": row.app_id},
    )


def _etag(version: int) -> str:
    return f'"{version}"'


def _precondition(row: AdapterLink, if_match: str | None) -> None:
    if if_match is not None and if_match.strip() not in ("*", _etag(row.version)):
        raise HubError(412, "precondition_failed", "De koppeling is gewijzigd.", {"huidige_etag": _etag(row.version)})


def _save_link(idem: Idem, status: int, row: AdapterLink) -> JSONResponse:
    receipt = LinkReceipt(id=row.id, version=row.version)
    response = idem.save(status, receipt.model_dump(mode="json"))
    response.headers["ETag"] = _etag(row.version)
    return response


def _replay_link(idem: Idem) -> JSONResponse | None:
    replay = idem.replay()
    if replay is not None:
        replay.headers["ETag"] = _etag(json.loads(bytes(replay.body))["version"])
    return replay


def _unique_target(db: DB, catalog_app_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    existing = db.scalar(select(AdapterLink.id).where(AdapterLink.catalog_app_id == catalog_app_id))
    if existing is not None and existing != except_id:
        raise HubError(409, "conflict", "Deze instantie heeft al een adapterkoppeling.", {"reason": "al_gekoppeld"})


@router.get("", summary="Adapterkoppelingen lezen")
def list_links(db: DB, _: AnyUser, cursor: Cursor = None, limit: Limit = 50) -> LinkList:
    query = select(AdapterLink).order_by(AdapterLink.id).limit(limit + 1)
    if cursor:
        try:
            after = uuid.UUID(cursor)
        except ValueError:
            raise HubError(400, "invalid_cursor", "Ongeldige cursor.") from None
        query = query.where(AdapterLink.id > after)
    rows = db.scalars(query).all()
    return LinkList(
        items=[_view(row) for row in rows[:limit]], next_cursor=str(rows[limit - 1].id) if len(rows) > limit else None
    )


@router.get("/{link_id}", summary="Adapterkoppeling lezen")
def get_link(link_id: uuid.UUID, response: Response, db: DB, _: AnyUser) -> LinkView:
    row = _link(db, link_id)
    response.headers["ETag"] = _etag(row.version)
    return _view(row)


@router.post(
    "",
    status_code=201,
    response_model=LinkReceipt,
    summary="Adapterkoppeling maken (beheerder)",
    responses={501: {"description": "De inwisseling van my_house-koppelcodes is nog niet beschikbaar."}},
)
def create_link(
    body: LinkIn, db: DB, admin: Admin, idem: Idem, vault: VaultDep, credential: Credential
) -> JSONResponse:
    if (replay := _replay_link(idem)) is not None:
        return replay
    secret = _credential(credential)
    _target(db, body.app_id, body.catalog_app_id)
    if (replay := _replay_link(idem)) is not None:
        return replay
    if body.app_id == "my_house":
        raise HubError(
            501, "capability_unavailable", "De inwisseling van my_house-koppelcodes is nog niet beschikbaar."
        )
    base, peers = _destination(body.basis_url, secret)
    _unique_target(db, body.catalog_app_id)
    link_id = uuid.uuid4()
    ref = make_ref("adapters", f"{body.app_id}.{link_id}")
    meta = vault.put(db, ref, secret, actor=admin.actor)
    row = AdapterLink(
        id=link_id,
        app_id=body.app_id,
        catalog_app_id=body.catalog_app_id,
        basis_url=base,
        peer_addresses=peers,
        geheim_ref=ref,
        laatste4=meta.last4,
        ingevoerd_op=meta.updated_at,
    )
    db.add(row)
    db.flush()
    _record(db, admin, row, "created")
    return _save_link(idem, 201, row)


@router.patch("/{link_id}", response_model=LinkReceipt, summary="Adapterkoppeling wijzigen (beheerder)")
def update_link(
    link_id: uuid.UUID,
    body: LinkPatch,
    db: DB,
    admin: Admin,
    idem: Idem,
    vault: VaultDep,
    credential: Credential = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    if (replay := _replay_link(idem)) is not None:
        return replay
    row = _link(db, link_id, lock=True)
    if (replay := _replay_link(idem)) is not None:
        return replay
    _precondition(row, if_match)
    catalog_app_id = body.catalog_app_id or row.catalog_app_id
    base = body.basis_url or row.basis_url
    if not body.doel_bevestigd and (catalog_app_id != row.catalog_app_id or base.rstrip("/") != row.basis_url):
        raise HubError(422, "validation_error", "Bevestig de nieuwe bestemming en voer een nieuw credential in.")
    if credential is None and not body.doel_bevestigd:
        raise HubError(422, "validation_error", "Geef een wijziging op.")
    secret = _credential(credential)
    _target(db, row.app_id, catalog_app_id)
    if body.doel_bevestigd:
        base, peers = _destination(base, secret)
        _unique_target(db, catalog_app_id, except_id=row.id)
        row.catalog_app_id, row.basis_url, row.peer_addresses = catalog_app_id, base, peers
    elif secret.casefold() in row.basis_url.casefold():
        raise HubError(422, "validation_error", "De waarde van het adaptercredential is ongeldig.")
    meta = vault.put(db, row.geheim_ref, secret, actor=admin.actor)
    row.laatste4, row.ingevoerd_op = meta.last4, meta.updated_at
    row.laatste_status, row.observed_at, row.max_age_s, row.laatste_fout = None, None, None, None
    row.version += 1
    _record(db, admin, row, "updated")
    return _save_link(idem, 200, row)


@router.post("/{link_id}/test", response_model=LinkReceipt, summary="Openbare verbinding testen (beheerder)")
def test_link(link_id: uuid.UUID, db: DB, admin: Admin, idem: Idem, settings: SettingsDep) -> JSONResponse:
    if (replay := _replay_link(idem)) is not None:
        return replay
    row = _link(db, link_id, lock=True)
    if (replay := _replay_link(idem)) is not None:
        return replay
    _target(db, row.app_id, row.catalog_app_id)
    measurement = basis.probe(row, settings.outbound_policy())
    row.laatste_fout = measurement.reason_code
    if measurement.observed_at is not None:
        row.laatste_status = measurement.status
        row.observed_at = measurement.observed_at
        row.max_age_s = basis.MAX_AGE_S
    row.version += 1
    _record(db, admin, row, "tested")
    return _save_link(idem, 200, row)


@router.delete("/{link_id}", response_model=Verwijderd, summary="Adapterkoppeling en kluiswaarde wissen (beheerder)")
def delete_link(link_id: uuid.UUID, db: DB, admin: Admin, idem: Idem, if_match: IfMatch = None) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = db.get(AdapterLink, link_id, with_for_update=True)
    if (replay := idem.replay()) is not None:
        return replay
    if row is None:
        raise HubError(404, "not_found", "Adapterkoppeling niet gevonden.")
    _precondition(row, if_match)
    secret = db.scalar(select(VaultSecret).where(VaultSecret.ref == row.geheim_ref))
    if secret is not None:
        db.delete(secret)
    _record(db, admin, row, "deleted")
    db.delete(row)
    return idem.save(200, {"verwijderd": True})
