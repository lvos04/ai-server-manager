"""Beheer en contactproef voor koppelingen met bestaande apps (S-P3-020)."""

from __future__ import annotations

import json
import re
import uuid
from ipaddress import ip_address
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select

from hub import audit
from hub.adapters import basis, mso
from hub.config import Settings
from hub.deps import DB, Admin, AnyUser, Cursor, Idem, Limit, Principal, SettingsDep, get_vault
from hub.errors import HubError
from hub.events.envelope import emit
from hub.inventory.store import kind_state
from hub.models import AdapterLink, CatalogApp, VaultSecret
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
            "Alleen invoer. Laat weg voor openbare MSO-probes. Gebruik een nieuwe Idempotency-Key bij wijziging."
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
    ingevoerd_op: UtcDateTime | None
    verbinding: basis.Measurement
    gezondheid: basis.Measurement
    version: int


class LinkList(BaseModel):
    items: list[LinkView]
    next_cursor: str | None


class LinkReceipt(BaseModel):
    id: uuid.UUID
    version: int


class MsoTestReceipt(LinkReceipt):
    probes: mso.PublicProbes


class Verwijderd(BaseModel):
    verwijderd: Literal[True]


def _view(row: AdapterLink, *, bound: bool) -> LinkView:
    measurement = basis.Measurement(status=row.laatste_status or "unknown", observed_at=row.observed_at)
    if row.laatste_fout:
        measurement = basis.Measurement(
            status="unknown",
            reason_code=row.laatste_fout,
            observed_at=row.observed_at,
            laatste_status=measurement.status if row.observed_at else None,
        )
    measurement = basis.fresh_measurement(measurement, max_age_s=row.max_age_s or basis.MAX_AGE_S)
    if not bound:
        measurement = basis.Measurement(
            status="unknown",
            reason_code="doelbinding",
            observed_at=row.observed_at,
            laatste_status=row.laatste_status if row.observed_at else None,
        )
    is_mso = row.app_id == mso.APP_ID
    health = mso.health() if is_mso else basis.Measurement(status="unknown", reason_code="capability_unavailable")
    return LinkView(
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


def _save_link(idem: Idem, status: int, row: AdapterLink, *, probes: mso.PublicProbes | None = None) -> JSONResponse:
    receipt: LinkReceipt
    if probes is None:
        receipt = LinkReceipt(id=row.id, version=row.version)
    else:
        receipt = MsoTestReceipt(id=row.id, version=row.version, probes=probes)
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
def get_link(link_id: uuid.UUID, response: Response, db: DB, _: AnyUser, settings: SettingsDep) -> LinkView:
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
    responses={501: {"description": "De inwisseling van my_house-koppelcodes is nog niet beschikbaar."}},
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
    if (replay := _replay_link(idem)) is not None:
        return replay
    secret = None if body.app_id == mso.APP_ID else _credential(credential)
    target = _target(db, body.app_id, body.catalog_app_id)
    if (replay := _replay_link(idem)) is not None:
        return replay
    if body.app_id == "my_house":
        raise HubError(
            501, "capability_unavailable", "De inwisseling van my_house-koppelcodes is nog niet beschikbaar."
        )
    nas = current_target(db)
    base, peers = _destination(target, body.basis_url, secret, nas, _published_ports(db, settings, nas))
    _unique_target(db, body.catalog_app_id)
    link_id = uuid.uuid4()
    ref = make_ref("adapters", f"{body.app_id}.{link_id}")
    meta = vault.put(db, ref, secret, actor=admin.actor) if secret is not None else None
    row = AdapterLink(
        id=link_id,
        app_id=body.app_id,
        catalog_app_id=body.catalog_app_id,
        basis_url=base,
        peer_addresses=peers,
        geheim_ref=ref,
        laatste4=meta.last4 if meta else "",
        ingevoerd_op=meta.updated_at if meta else utcnow(),
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
    if secret is None:
        _delete_credential(db, row)
        row.laatste4, row.ingevoerd_op = "", utcnow()
    else:
        meta = vault.put(db, row.geheim_ref, secret, actor=admin.actor)
        row.laatste4, row.ingevoerd_op = meta.last4, meta.updated_at
    row.laatste_status, row.observed_at, row.max_age_s, row.laatste_fout = None, None, None, None
    row.version += 1
    _record(db, admin, row, "updated")
    return _save_link(idem, 200, row)


@router.post(
    "/{link_id}/test", response_model=MsoTestReceipt | LinkReceipt, summary="Openbare verbinding testen (beheerder)"
)
def test_link(link_id: uuid.UUID, db: DB, admin: Admin, idem: Idem, settings: SettingsDep) -> JSONResponse:
    if (replay := _replay_link(idem)) is not None:
        return replay
    row = _link(db, link_id, lock=True)
    if (replay := _replay_link(idem)) is not None:
        return replay
    target = _target(db, row.app_id, row.catalog_app_id)

    def check_binding() -> None:
        nas = current_target(db)
        if not _binding_is_current(row, target, nas, _published_ports(db, settings, nas)):
            raise _binding_conflict()

    policy = settings.outbound_policy()
    probes = None
    if row.app_id == mso.APP_ID:
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
        measurement = basis.probe(row, policy)
    row.laatste_fout = measurement.reason_code
    if measurement.observed_at is not None:
        row.laatste_status = measurement.status
        row.observed_at = measurement.observed_at
        row.max_age_s = basis.MAX_AGE_S
    row.version += 1
    _record(db, admin, row, "tested")
    return _save_link(idem, 200, row, probes=probes)


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
    _delete_credential(db, row)
    _record(db, admin, row, "deleted")
    db.delete(row)
    return idem.save(200, {"verwijderd": True})
