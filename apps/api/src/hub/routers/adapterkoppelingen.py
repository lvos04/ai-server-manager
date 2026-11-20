"""Beheer en contactproef voor koppelingen met bestaande apps (S-P3-020)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select, update

from hub import audit
from hub.adapters import basis, mediaguard, mso, my_house
from hub.config import Settings
from hub.deps import DB, Admin, AnyUser, Cursor, Idem, Limit, Principal, SettingsDep, get_vault
from hub.errors import HubError
from hub.events.envelope import emit
from hub.inventory.store import kind_state
from hub.models import AdapterHouseSnapshot, AdapterLink, CatalogApp, IdempotencyRecord, VaultSecret
from hub.outbound import OutboundError
from hub.timeutil import UtcDateTime, utcnow
from hub.truenas.connection import NasTarget, current_target
from hub.vault import Vault, make_ref

router = APIRouter(prefix="/api/v1/adapterkoppelingen", tags=["adapterkoppelingen"])
VaultDep = Annotated[Vault, Depends(get_vault)]
Credential = Annotated[
    SecretStr | None,
    Header(
        alias="X-Adapter-Credential",
        description=(
            "Alleen invoer. Gebruik voor my_house een Hub-koppelcode en laat weg voor openbare MSO-probes. "
            "Gebruik een nieuwe Idempotency-Key bij wijziging."
        ),
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
    server_id: uuid.UUID | None = None


class LinkPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_app_id: uuid.UUID | None = None
    basis_url: BasisUrl | None = None
    doel_bevestigd: bool = False
    server_id: uuid.UUID | None = None


class LinkView(BaseModel):
    id: uuid.UUID
    app_id: str
    catalog_app_id: uuid.UUID
    basis_url: str
    laatste4: str
    ingevoerd_op: UtcDateTime | None
    verbinding: basis.Measurement
    gezondheid: basis.Measurement
    version: int


class MediaGuardLinkView(LinkView):
    mediaguard: mediaguard.Readings


class LinkList(BaseModel):
    items: list[MediaGuardLinkView | LinkView]
    next_cursor: str | None


class LinkReceipt(BaseModel):
    id: uuid.UUID
    version: int


class MsoTestReceipt(LinkReceipt):
    probes: mso.PublicProbes


class MyHouseTestReceipt(LinkReceipt):
    my_house: my_house.Snapshot | None


class Verwijderd(BaseModel):
    verwijderd: Literal[True]


def _view(row: AdapterLink, *, bound: bool) -> MediaGuardLinkView | LinkView:
    now = utcnow()
    is_mediaguard = row.app_id == mediaguard.APP_ID
    reason = mediaguard.REASON_CODE if is_mediaguard else row.laatste_fout
    if row.app_id == my_house.APP_ID and row.my_house_expires_at is not None and row.my_house_expires_at <= now:
        reason = "bron_token_verlopen"
    measurement = basis.Measurement(status=row.laatste_status or "unknown", observed_at=row.observed_at)
    if reason:
        measurement = basis.Measurement(
            status="unknown",
            reason_code=reason,
            observed_at=row.observed_at,
            laatste_status=measurement.status if row.observed_at else None,
        )
    if not is_mediaguard and (row.app_id != my_house.APP_ID or (bound and reason is None)):
        measurement = basis.fresh_measurement(measurement, now=now, max_age_s=row.max_age_s or basis.MAX_AGE_S)
    if not bound:
        measurement = basis.Measurement(
            status="unknown",
            reason_code="doelbinding",
            observed_at=row.observed_at,
            laatste_status=row.laatste_status if row.observed_at else None,
        )
    is_mso = row.app_id == mso.APP_ID
    if is_mediaguard:
        health = mediaguard.health()
    else:
        health = mso.health() if is_mso else basis.Measurement(status="unknown", reason_code="capability_unavailable")
    if row.app_id == my_house.APP_ID:
        last = (
            my_house.health(my_house.CheckReadings.validate_python(row.my_house_checks), now)
            if row.my_house_checks
            else None
        )
        if last is not None and bound and reason is None:
            health = last
        else:
            health = basis.Measurement(
                status="unknown",
                reason_code=measurement.reason_code or "meting_onbekend",
                observed_at=last.observed_at if last is not None else row.observed_at,
                laatste_status=(last.laatste_status or last.status) if last is not None else None,
            )
    view = LinkView(
        id=row.id,
        app_id=row.app_id,
        catalog_app_id=row.catalog_app_id,
        basis_url=row.basis_url,
        laatste4="" if is_mso else row.laatste4,
        ingevoerd_op=None if is_mso else row.ingevoerd_op,
        verbinding=measurement,
        gezondheid=health,
        version=row.version,
    )
    if is_mediaguard:
        return MediaGuardLinkView(**view.model_dump(), mediaguard=mediaguard.Readings())
    return view


def _link(db: DB, link_id: uuid.UUID, *, lock: bool = False) -> AdapterLink:
    row = db.get(AdapterLink, link_id, with_for_update=lock)
    if row is None:
        raise HubError(404, "not_found", "Adapterkoppeling niet gevonden.")
    return row


def _target_matches(target: CatalogApp | None, app_id: str) -> bool:
    return target is not None and target.aanwezig and target.app_id == app_id and target.soort == "bestaand"


def _binding_conflict() -> HubError:
    return HubError(
        409, "conflict", "De bestemming is niet geregistreerd voor deze app-instantie.", {"reason": "doelbinding"}
    )


def _target(db: DB, app_id: str, catalog_app_id: uuid.UUID) -> CatalogApp:
    target = db.get(CatalogApp, catalog_app_id, with_for_update=True)
    if target is None or not _target_matches(target, app_id):
        raise _binding_conflict()
    return target


def _published_ports(db: DB, settings: Settings, nas: NasTarget | None) -> dict[int, list[dict[str, Any]]]:
    inventory = kind_state(db, "apps", target=nas.url if nas else None, ttl_seconds=settings.inventory_max_age_seconds)
    owners: dict[int, list[dict[str, Any]]] = {}
    if inventory["status"] != "ok" or not isinstance(inventory["data"], list):
        return owners
    for app in inventory["data"]:
        if not isinstance(app, dict) or not isinstance(app.get("poorten"), list):
            continue
        for port in {
            binding["host_poort"]
            for binding in app["poorten"]
            if isinstance(binding, dict) and binding.get("protocol") == "tcp" and type(binding.get("host_poort")) is int
        }:
            owners.setdefault(port, []).append(app)
    return owners


def _registered_port(
    base: str, target: CatalogApp, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> int | None:
    # De inventaris kan al zijn vastgelegd terwijl de worker de catalogus nog bijwerkt.
    parts = urlsplit(base)
    port = parts.port or 443
    if nas is None or parts.hostname != nas.host.strip("[]").lower() or target.bron.get("nas", nas.url) != nas.url:
        return None
    port_owners = owners.get(port, [])
    if len(port_owners) != 1:
        return None
    owner = port_owners[0]
    if (
        owner.get("runtime_id") != target.runtime_id
        or owner.get("herkend_als") != target.app_id
        or owner.get("poorten") != target.poorten
        or owner.get("portals") != target.portals
    ):
        return None
    if any(
        isinstance(portal, dict)
        and portal.get("schema") == "https"
        and portal.get("poort") == port
        and str(portal.get("pad") or "/").rstrip("/") == parts.path
        for portal in target.portals
    ):
        return port
    return None


def _registered_peers(target: CatalogApp, port: int, peers: list[str]) -> bool:
    interfaces = [
        binding.get("host_ip")
        for binding in target.poorten
        if isinstance(binding, dict) and binding.get("protocol") == "tcp" and binding.get("host_poort") == port
    ]
    if not peers:
        return False
    if None in interfaces or "" in interfaces:
        return True
    try:
        addresses = {ip_address(str(interface)) for interface in interfaces}
        return all(
            peer in addresses or any(addr.is_unspecified and addr.version == peer.version for addr in addresses)
            for peer in map(ip_address, peers)
        )
    except ValueError:
        return False


def _binding_is_current(
    row: AdapterLink, target: CatalogApp | None, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> bool:
    if target is None or not _target_matches(target, row.app_id):
        return False
    try:
        base = basis.validate_base_url(row.basis_url)
    except OutboundError:
        return False
    port = _registered_port(base, target, nas, owners)
    return port is not None and _registered_peers(target, port, row.peer_addresses)


def _destination(
    target: CatalogApp, url: str, credential: str | None, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> tuple[str, list[str]]:
    try:
        base = basis.validate_base_url(url)
        if credential is not None and credential.casefold() in base.casefold():
            raise OutboundError("adres_ongeldig")
        port = _registered_port(base, target, nas, owners)
        if port is None:
            raise _binding_conflict()
        peers = basis.resolve_binding(base)
        if not _registered_peers(target, port, peers):
            raise _binding_conflict()
        return base, peers
    except OutboundError as exc:
        raise HubError(422, "validation_error", "Ongeldig basisadres.", {"reason": exc.reason}) from None


def _credential(value: SecretStr | None) -> str:
    if value is None:
        raise HubError(422, "validation_error", "Voer een nieuw adaptercredential in.")
    secret = value.get_secret_value()
    if not re.fullmatch(r"[!-~]{8,512}", secret):
        raise HubError(422, "validation_error", "De waarde van het adaptercredential is ongeldig.")
    return secret


def _reject_mso_credential(app_id: str | None, credential: SecretStr | None) -> None:
    if app_id == mso.APP_ID and credential is not None:
        raise HubError(422, "validation_error", "MSO gebruikt voor deze koppeling alleen openbare probes.")


def _delete_credential(db: DB, row: AdapterLink) -> None:
    secret = db.scalar(select(VaultSecret).where(VaultSecret.ref == row.geheim_ref))
    if secret is not None:
        db.delete(secret)


def _clear_legacy_house_measurements(db: DB, link_id: uuid.UUID) -> None:
    body = IdempotencyRecord.response_body
    db.execute(
        update(IdempotencyRecord)
        .where(
            IdempotencyRecord.scope.endswith(f":POST:{router.prefix}/{{link_id}}/test", autoescape=True),
            body["id"].astext == str(link_id),
            body["my_house"].astext.is_not(None),
        )
        .values(response_body=body.op("||")({"my_house": None}))
    )


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


def _save_link(idem: Idem, status: int, row: AdapterLink, receipt: LinkReceipt | None = None) -> JSONResponse:
    if receipt is None:
        receipt = LinkReceipt(id=row.id, version=row.version)
    response = idem.save(status, receipt.model_dump(mode="json"))
    response.headers["ETag"] = _etag(row.version)
    return response


def _replay_link(idem: Idem) -> JSONResponse | None:
    replay = idem.replay()
    if replay is not None:
        replay.headers["ETag"] = _etag(json.loads(bytes(replay.body))["version"])
    return replay


def _house_test_response(response: JSONResponse, snapshot: my_house.SnapshotReading | None) -> JSONResponse:
    body = json.loads(bytes(response.body))
    body["my_house"] = None if snapshot is None else snapshot.project(utcnow()).model_dump(mode="json")
    headers = dict(response.headers)
    del headers["content-length"]
    return JSONResponse(body, status_code=response.status_code, headers=headers)


def _replay_test(db: DB, idem: Idem, link_id: uuid.UUID) -> JSONResponse | None:
    replay = _replay_link(idem)
    if replay is None or "my_house" not in json.loads(bytes(replay.body)):
        return replay
    stored = db.get(AdapterHouseSnapshot, (idem.scope, idem.key))
    snapshot = (
        my_house.SnapshotReading.model_validate(stored.measurement) if stored and stored.link_id == link_id else None
    )
    return _house_test_response(replay, snapshot)


def _unique_target(db: DB, catalog_app_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    existing = db.scalar(select(AdapterLink.id).where(AdapterLink.catalog_app_id == catalog_app_id))
    if existing is not None and existing != except_id:
        raise HubError(409, "conflict", "Deze instantie heeft al een adapterkoppeling.", {"reason": "al_gekoppeld"})


def _house_adapter(db: DB, settings: Settings, row: AdapterLink, target: CatalogApp) -> my_house.Adapter:
    def check_binding() -> None:
        nas = current_target(db)
        if not _binding_is_current(row, target, nas, _published_ports(db, settings, nas)):
            raise OutboundError("doelbinding")

    return my_house.Adapter(row, settings.outbound_policy(), check_binding=check_binding)


def _house_pair(
    db: DB, settings: Settings, row: AdapterLink, target: CatalogApp, code: str, server_id: uuid.UUID | None
) -> str:
    if server_id is None:
        raise HubError(422, "validation_error", "Bevestig de server-ID uit my_house.")
    if row.geheim_ref != make_ref("adapters", f"{my_house.APP_ID}.{row.id}"):
        raise _binding_conflict()
    row.my_house_server_id = server_id
    try:
        pairing = _house_adapter(db, settings, row, target).pair(code)
    except OutboundError as exc:
        raise HubError(422, "validation_error", "De my_house-koppeling is geweigerd.", {"reason": exc.reason}) from None
    row.my_house_client_id = pairing.client_id
    row.my_house_expires_at = pairing.credential.expires_at
    return pairing.credential.token


def _house_credential(db: DB, vault: Vault, row: AdapterLink, now: datetime) -> my_house.Credential:
    expires = row.my_house_expires_at
    if expires is None or row.geheim_ref != make_ref("adapters", f"{my_house.APP_ID}.{row.id}"):
        raise OutboundError("bron_credential_geweigerd")
    if expires <= now:
        raise OutboundError("bron_token_verlopen")
    try:
        token = vault.get(db, row.geheim_ref)
    except (InvalidTag, ValueError):
        raise OutboundError("bron_credential_geweigerd") from None
    if token is None or my_house.TOKEN.fullmatch(token) is None:
        raise OutboundError("bron_credential_geweigerd")
    return my_house.Credential(token, expires)


def _house_renew(
    db: DB, vault: Vault, row: AdapterLink, adapter: my_house.Adapter, credential: my_house.Credential, now: datetime
) -> my_house.Credential:
    if credential.expires_at - now > my_house.RENEW_BEFORE:
        return credential
    try:
        renewed = adapter.refresh(credential, now)
    except OutboundError as exc:
        if exc.reason in {"bron_token_verlopen", "bron_token_ingetrokken", "doelbinding"}:
            raise
        raise OutboundError("bron_vernieuwing_mislukt") from None
    meta = vault.put(db, row.geheim_ref, renewed.token, actor="my_house-vernieuwing")
    row.laatste4, row.ingevoerd_op = meta.last4, meta.updated_at
    row.my_house_expires_at = renewed.expires_at
    return renewed


def _house_transition(db: DB, row: AdapterLink, reason: str | None) -> None:
    previous = row.laatste_fout
    if reason is not None and reason != previous:
        emit(db, "monitoring.my_house.failed", "adapter_link", str(row.id), {"reason_code": reason})
    elif reason is None and previous is not None:
        emit(db, "monitoring.my_house.recovered", "adapter_link", str(row.id), {})
    row.laatste_fout = reason


def renew_my_house_links(db: DB, settings: Settings, vault: Vault, now: datetime) -> dict[str, int]:
    """Vernieuw tijdig, ook zonder handmatige test. De rijvergrendeling serialiseert tokenwissels."""
    ids = list(
        db.scalars(
            select(AdapterLink.id).where(
                AdapterLink.app_id == my_house.APP_ID, AdapterLink.my_house_expires_at <= now + my_house.RENEW_BEFORE
            )
        )
    )
    renewed = failed = 0
    for link_id in ids:
        row = db.scalars(select(AdapterLink).where(AdapterLink.id == link_id).with_for_update(skip_locked=True)).first()
        if row is None or row.my_house_expires_at is None or row.my_house_expires_at > now + my_house.RENEW_BEFORE:
            continue
        try:
            target = db.get(CatalogApp, row.catalog_app_id)
            if not _target_matches(target, my_house.APP_ID) or target is None:
                raise OutboundError("doelbinding")
            credential = _house_credential(db, vault, row, now)
            _house_renew(db, vault, row, _house_adapter(db, settings, row, target), credential, now)
        except OutboundError as exc:
            if row.laatste_fout != exc.reason:
                row.version += 1
            _house_transition(db, row, exc.reason)
            failed += 1
        else:
            row.version += 1
            renewed += 1
        db.commit()
    return {"vernieuwd": renewed, "mislukt": failed}


@router.get("", summary="Adapterkoppelingen lezen")
def list_links(db: DB, _: AnyUser, settings: SettingsDep, cursor: Cursor = None, limit: Limit = 50) -> LinkList:
    query = select(AdapterLink, CatalogApp).join(CatalogApp).order_by(AdapterLink.id).limit(limit + 1)
    if cursor:
        try:
            after = uuid.UUID(cursor)
        except ValueError:
            raise HubError(400, "invalid_cursor", "Ongeldige cursor.") from None
        query = query.where(AdapterLink.id > after)
    rows = db.execute(query).all()
    nas = current_target(db)
    owners = _published_ports(db, settings, nas)
    return LinkList(
        items=[_view(row, bound=_binding_is_current(row, target, nas, owners)) for row, target in rows[:limit]],
        next_cursor=str(rows[limit - 1][0].id) if len(rows) > limit else None,
    )


@router.get("/{link_id}", summary="Adapterkoppeling lezen")
def get_link(
    link_id: uuid.UUID, response: Response, db: DB, _: AnyUser, settings: SettingsDep
) -> MediaGuardLinkView | LinkView:
    row = _link(db, link_id)
    response.headers["ETag"] = _etag(row.version)
    target = db.get(CatalogApp, row.catalog_app_id)
    nas = current_target(db)
    return _view(row, bound=_binding_is_current(row, target, nas, _published_ports(db, settings, nas)))


@router.post(
    "",
    status_code=201,
    response_model=LinkReceipt,
    summary="Adapterkoppeling maken (beheerder)",
)
def create_link(
    body: LinkIn,
    db: DB,
    admin: Admin,
    idem: Idem,
    vault: VaultDep,
    settings: SettingsDep,
    credential: Credential = None,
) -> JSONResponse:
    _reject_mso_credential(body.app_id, credential)
    if body.server_id is not None and body.app_id != my_house.APP_ID:
        raise HubError(422, "validation_error", "Alleen my_house gebruikt een server-ID.")
    if (replay := _replay_link(idem)) is not None:
        return replay
    secret = None if body.app_id == mso.APP_ID else _credential(credential)
    target = _target(db, body.app_id, body.catalog_app_id)
    if (replay := _replay_link(idem)) is not None:
        return replay
    nas = current_target(db)
    base, peers = _destination(target, body.basis_url, secret, nas, _published_ports(db, settings, nas))
    _unique_target(db, body.catalog_app_id)
    link_id = uuid.uuid4()
    ref = make_ref("adapters", f"{body.app_id}.{link_id}")
    row = AdapterLink(
        id=link_id,
        app_id=body.app_id,
        catalog_app_id=body.catalog_app_id,
        basis_url=base,
        peer_addresses=peers,
        geheim_ref=ref,
        laatste4="",
        ingevoerd_op=utcnow(),
    )
    if body.app_id == my_house.APP_ID and secret is not None:
        secret = _house_pair(db, settings, row, target, secret, body.server_id)
    if secret is not None:
        meta = vault.put(db, ref, secret, actor=admin.actor)
        row.laatste4, row.ingevoerd_op = meta.last4, meta.updated_at
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
    settings: SettingsDep,
    credential: Credential = None,
    if_match: IfMatch = None,
) -> JSONResponse:
    if (replay := _replay_link(idem)) is not None:
        if credential is not None:
            app_id = db.scalar(select(AdapterLink.app_id).where(AdapterLink.id == link_id))
            _reject_mso_credential(app_id, credential)
        return replay
    row = _link(db, link_id, lock=True)
    _reject_mso_credential(row.app_id, credential)
    if (replay := _replay_link(idem)) is not None:
        return replay
    _precondition(row, if_match)
    if body.server_id is not None and row.app_id != my_house.APP_ID:
        raise HubError(422, "validation_error", "Alleen my_house gebruikt een server-ID.")
    catalog_app_id = body.catalog_app_id or row.catalog_app_id
    base = body.basis_url or row.basis_url
    if not body.doel_bevestigd and (catalog_app_id != row.catalog_app_id or base.rstrip("/") != row.basis_url):
        melding = (
            "Bevestig de nieuwe bestemming."
            if row.app_id == mso.APP_ID
            else "Bevestig de nieuwe bestemming en voer een nieuw credential in."
        )
        raise HubError(422, "validation_error", melding)
    if credential is None and not body.doel_bevestigd:
        raise HubError(422, "validation_error", "Geef een wijziging op.")
    secret = None if row.app_id == mso.APP_ID else _credential(credential)
    target = _target(db, row.app_id, catalog_app_id)
    nas = current_target(db)
    owners = _published_ports(db, settings, nas)
    if body.doel_bevestigd:
        base, peers = _destination(target, base, secret, nas, owners)
        _unique_target(db, catalog_app_id, except_id=row.id)
        row.catalog_app_id, row.basis_url, row.peer_addresses = catalog_app_id, base, peers
    elif secret is not None and secret.casefold() in row.basis_url.casefold():
        raise HubError(422, "validation_error", "De waarde van het adaptercredential is ongeldig.")
    elif not _binding_is_current(row, target, nas, owners):
        raise _binding_conflict()
    if row.app_id == my_house.APP_ID and secret is not None:
        if not body.doel_bevestigd and body.server_id not in (None, row.my_house_server_id):
            raise HubError(422, "validation_error", "Bevestig de nieuwe server-ID.")
        server_id = body.server_id if body.doel_bevestigd else row.my_house_server_id
        secret = _house_pair(db, settings, row, target, secret, server_id)
    if secret is None:
        _delete_credential(db, row)
        row.laatste4, row.ingevoerd_op = "", utcnow()
    else:
        meta = vault.put(db, row.geheim_ref, secret, actor=admin.actor)
        row.laatste4, row.ingevoerd_op = meta.last4, meta.updated_at
    row.laatste_status, row.observed_at, row.max_age_s = None, None, None
    row.my_house_checks = None
    if row.app_id != my_house.APP_ID:
        row.laatste_fout = None
    row.version += 1
    _record(db, admin, row, "updated")
    return _save_link(idem, 200, row)


@router.post(
    "/{link_id}/test",
    response_model=MsoTestReceipt | MyHouseTestReceipt | LinkReceipt,
    summary="Adapterverbinding testen (beheerder)",
)
def test_link(
    link_id: uuid.UUID, db: DB, admin: Admin, idem: Idem, settings: SettingsDep, vault: VaultDep
) -> JSONResponse:
    if (replay := _replay_test(db, idem, link_id)) is not None:
        return replay
    row = _link(db, link_id, lock=True)
    if (replay := _replay_test(db, idem, link_id)) is not None:
        return replay
    target = _target(db, row.app_id, row.catalog_app_id)

    def check_binding() -> None:
        nas = current_target(db)
        if not _binding_is_current(row, target, nas, _published_ports(db, settings, nas)):
            raise _binding_conflict()

    policy = settings.outbound_policy()
    probes = None
    snapshot = None
    if row.app_id == my_house.APP_ID:
        adapter = _house_adapter(db, settings, row, target)
        now = utcnow()
        try:
            credential = _house_credential(db, vault, row, now)
            credential = _house_renew(db, vault, row, adapter, credential, now)
            snapshot = adapter.read_snapshot(credential.token)
        except OutboundError as exc:
            measurement = basis.Measurement(status="unknown", reason_code=exc.reason)
        else:
            measurement = basis.Measurement(status="healthy", observed_at=snapshot.snapshot.observed_at)
            row.my_house_checks = my_house.CheckReadings.dump_python(snapshot.checks, mode="json")
            db.add(
                AdapterHouseSnapshot(
                    receipt_scope=idem.scope,
                    receipt_key=idem.key,
                    link_id=row.id,
                    measurement=snapshot.model_dump(mode="json"),
                )
            )
        _house_transition(db, row, measurement.reason_code)
    elif row.app_id == mso.APP_ID:
        result = mso.public_probes(row, policy, check_binding=check_binding)
        measurement, probes = result.connection, result.probes
        for failure in result.failures:
            emit(
                db,
                "monitoring.mso_probe.failed",
                "adapter_link",
                str(row.id),
                {"reason_code": failure.reason_code, "correlation_id": failure.correlation_id},
            )
        if row.laatste_fout is not None and not result.failures:
            emit(db, "monitoring.mso_probe.recovered", "adapter_link", str(row.id), {})
    else:
        check_binding()
        measurement = mediaguard.health()
    row.laatste_fout = measurement.reason_code
    if measurement.observed_at is not None:
        row.laatste_status = measurement.status
        row.observed_at = measurement.observed_at
        row.max_age_s = basis.MAX_AGE_S
    row.version += 1
    _record(db, admin, row, "tested")
    receipt: LinkReceipt | None = None
    if probes is not None:
        receipt = MsoTestReceipt(id=row.id, version=row.version, probes=probes)
    if row.app_id == my_house.APP_ID:
        receipt = MyHouseTestReceipt(id=row.id, version=row.version, my_house=None)
    response = _save_link(idem, 200, row, receipt)
    return _house_test_response(response, snapshot) if snapshot is not None else response


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
    if row.app_id == my_house.APP_ID:
        if row.geheim_ref != make_ref("adapters", f"{my_house.APP_ID}.{row.id}"):
            raise _binding_conflict()
        _clear_legacy_house_measurements(db, row.id)
    _delete_credential(db, row)
    _record(db, admin, row, "deleted")
    db.delete(row)
    return idem.save(200, {"verwijderd": True})
