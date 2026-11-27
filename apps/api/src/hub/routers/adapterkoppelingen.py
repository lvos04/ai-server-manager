"""Beheer en contactproef voor koppelingen met bestaande apps (S-P3-020)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from cryptography.exceptions import InvalidTag
from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select, update

from hub import audit
from hub.adapters import basis, mediaguard, mediaguard_lezen, mso, my_house
from hub.adapters.binding import (
    binding_is_current,
    confirmed_binding,
    published_ports,
    registered_peers,
    registered_port,
    target_matches,
)
from hub.adapters.health import stored_health
from hub.backup.appdekking import Meting, huisrapport
from hub.config import Settings
from hub.deps import DB, Admin, AnyUser, Cursor, Idem, Limit, Principal, SettingsDep, Viewer, get_vault
from hub.errors import ErrorResponse, HubError
from hub.events.envelope import emit
from hub.incidents.rules import ADAPTER_HEALTH_FAILED, ADAPTER_HEALTH_RECOVERED, adapter_health_transition
from hub.inventory.store import kind_state
from hub.models import (
    AdapterHouseSnapshot,
    AdapterLink,
    CatalogApp,
    IdempotencyRecord,
    Incident,
    OutboxEvent,
    VaultSecret,
)
from hub.outbound import OutboundError
from hub.security import new_token, sha256_hex
from hub.timeutil import UtcDateTime, utcnow
from hub.truenas.connection import NasTarget, current_target
from hub.vault import Vault, VaultError, make_ref

log = logging.getLogger("hub.adapters")
router = APIRouter(
    prefix="/api/v1/adapterkoppelingen", tags=["adapterkoppelingen"], responses={422: {"model": ErrorResponse}}
)
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
    poolleesrecht: bool


class LinkList(BaseModel):
    items: list[MediaGuardLinkView | LinkView]
    next_cursor: str | None


class HouseLinks(BaseModel):
    items: list[uuid.UUID]
    next_cursor: str | None


class LinkReceipt(BaseModel):
    id: uuid.UUID
    version: int


class PoolrechtIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingeschakeld: bool = Field(strict=True)


class PoolrechtReceipt(LinkReceipt):
    pool_token: str | None = Field(
        default=None, description="Alleen bij de eerste afgifte van een nieuw poolleestoken."
    )


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
    contacttijd = row.observed_at if row.observed_at is not None and row.observed_at <= now else None
    measurement = basis.Measurement(status=row.laatste_status or "unknown", observed_at=contacttijd)
    if reason:
        measurement = basis.Measurement(
            status="unknown",
            reason_code=reason,
            observed_at=contacttijd,
            laatste_status=row.laatste_status if contacttijd else None,
        )
    if not is_mediaguard and (row.app_id != my_house.APP_ID or (bound and reason is None)):
        measurement = basis.fresh_measurement(measurement, now=now, max_age_s=row.max_age_s or basis.MAX_AGE_S)
    if not bound:
        measurement = basis.Measurement(
            status="unknown",
            reason_code="doelbinding",
            observed_at=contacttijd,
            laatste_status=row.laatste_status if contacttijd else None,
        )
    is_mso = row.app_id == mso.APP_ID
    view = LinkView(
        id=row.id,
        app_id=row.app_id,
        catalog_app_id=row.catalog_app_id,
        basis_url=row.basis_url,
        laatste4="" if is_mso else row.laatste4,
        ingevoerd_op=None if is_mso else row.ingevoerd_op,
        verbinding=measurement,
        gezondheid=stored_health(row, now, bound=bound),
        version=row.version,
    )
    if is_mediaguard:
        return MediaGuardLinkView(
            **view.model_dump(), mediaguard=mediaguard.Readings(), poolleesrecht=row.pool_token_hash is not None
        )
    return view


def _link(db: DB, link_id: uuid.UUID, *, lock: bool = False) -> AdapterLink:
    row = db.get(AdapterLink, link_id, with_for_update=lock)
    if row is None:
        raise HubError(404, "not_found", "Adapterkoppeling niet gevonden.")
    return row


def _binding_conflict() -> HubError:
    return HubError(
        409, "conflict", "De bestemming is niet geregistreerd voor deze app-instantie.", {"reason": "doelbinding"}
    )


def _target(db: DB, app_id: str, catalog_app_id: uuid.UUID) -> CatalogApp:
    target = db.get(CatalogApp, catalog_app_id, with_for_update=True)
    if target is None or not target_matches(target, app_id):
        raise _binding_conflict()
    return target


def _published_ports(db: DB, settings: Settings, nas: NasTarget | None) -> dict[int, list[dict[str, Any]]]:
    inventory = kind_state(db, "apps", target=nas.url if nas else None, ttl_seconds=settings.inventory_max_age_seconds)
    return published_ports(inventory)


def _destination(
    target: CatalogApp, url: str, credential: str | None, nas: NasTarget | None, owners: dict[int, list[dict[str, Any]]]
) -> tuple[str, list[str]]:
    try:
        base = basis.validate_base_url(url)
        if credential is not None and credential.casefold() in base.casefold():
            raise OutboundError("adres_ongeldig")
        port = registered_port(base, target, nas, owners)
        if port is None:
            raise _binding_conflict()
        peers = basis.resolve_binding(base)
        if not registered_peers(target, port, peers):
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
        if not binding_is_current(row, target, nas, _published_ports(db, settings, nas)):
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
    except (InvalidTag, ValueError, VaultError):
        raise OutboundError("bron_credential_geweigerd") from None
    if token is None or my_house.TOKEN.fullmatch(token) is None:
        raise OutboundError("bron_credential_geweigerd")
    return my_house.Credential(token, expires)


def lees_huisbackup(db: DB, settings: Settings, vault: Vault, row: AdapterLink, target: CatalogApp) -> Meting:
    credential = _house_credential(db, vault, row, utcnow())
    return huisrapport(*_house_adapter(db, settings, row, target).backupstatus(credential.token))


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
    try:
        meta = vault.put(db, row.geheim_ref, renewed.token, actor="my_house-vernieuwing")
    except VaultError:
        raise OutboundError("bron_vernieuwing_mislukt") from None
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


def _adapter_problem_active(db: DB, catalog_id: str) -> bool:
    # De incidentenworker kan de storing of het herstel nog in de outbox hebben staan.
    pending = db.scalar(
        select(OutboxEvent.event_type)
        .where(
            OutboxEvent.entity_type == "catalog_app",
            OutboxEvent.entity_id == catalog_id,
            OutboxEvent.event_type.in_((ADAPTER_HEALTH_FAILED, ADAPTER_HEALTH_RECOVERED)),
            OutboxEvent.incident_verwerkt_op.is_(None),
        )
        .order_by(OutboxEvent.seq.desc())
        .limit(1)
    )
    if pending is not None:
        return pending == ADAPTER_HEALTH_FAILED
    return (
        db.scalar(
            select(Incident.id)
            .where(
                Incident.soort == "monitoring.adapter_health",
                Incident.onderwerp_type == "catalog_app",
                Incident.onderwerp_id == catalog_id,
                Incident.status != "opgelost",
            )
            .limit(1)
        )
        is not None
    )


def _record_health_measurement(db: DB, row: AdapterLink, now: datetime) -> None:
    # De contactproef vergrendelt de koppeling; een idempotente herhaling komt hier niet.
    health = stored_health(row, now, bound=True)
    incident_active = row.health_failures < 3 and _adapter_problem_active(db, str(row.catalog_app_id))
    row.health_failures, transition = adapter_health_transition(
        row.health_failures, health.status, incident_active=incident_active
    )
    if transition is not None:
        emit(
            db,
            ADAPTER_HEALTH_FAILED if transition == "probleem" else ADAPTER_HEALTH_RECOVERED,
            "catalog_app",
            str(row.catalog_app_id),
            {"app_id": row.app_id, "status": health.status, "reason_code": health.reason_code},
            timestamp=now,
        )


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
            if not target_matches(target, my_house.APP_ID) or target is None:
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
        items=[_view(row, bound=binding_is_current(row, target, nas, owners)) for row, target in rows[:limit]],
        next_cursor=str(rows[limit - 1][0].id) if len(rows) > limit else None,
    )


@router.get("/my-house", summary="Koppelingen voor het woningoverzicht lezen")
def list_house_links(db: DB, _: Viewer, response: Response, cursor: Cursor = None, limit: Limit = 50) -> HouseLinks:
    response.headers["Cache-Control"] = "no-store"
    query = (
        select(AdapterLink.id).where(AdapterLink.app_id == my_house.APP_ID).order_by(AdapterLink.id).limit(limit + 1)
    )
    if cursor:
        try:
            after = uuid.UUID(cursor)
        except ValueError:
            raise HubError(400, "invalid_cursor", "Ongeldige cursor.") from None
        query = query.where(AdapterLink.id > after)
    ids = db.scalars(query).all()
    return HouseLinks(items=list(ids[:limit]), next_cursor=str(ids[limit - 1]) if len(ids) > limit else None)


@router.get("/{link_id}/huis", summary="Woningoverzicht lezen")
def read_house(
    link_id: uuid.UUID, db: DB, _: Viewer, response: Response, settings: SettingsDep, vault: VaultDep
) -> my_house.Snapshot:
    row = _link(db, link_id)
    if row.app_id != my_house.APP_ID:
        raise HubError(404, "not_found", "Geen my_house-koppeling gevonden.")
    target = db.get(CatalogApp, row.catalog_app_id)
    if target is None or not target_matches(target, my_house.APP_ID):
        raise HubError(409, "doelbinding", "De gekoppelde my_house-installatie kan niet worden bevestigd.")
    try:
        credential = _house_credential(db, vault, row, utcnow())
        snapshot = _house_adapter(db, settings, row, target).snapshot(credential.token)
    except OutboundError as exc:
        if exc.reason in {"bron_token_verlopen", "bron_token_ingetrokken"}:
            raise HubError(409, exc.reason, "Een beheerder kan de leesverbinding opnieuw koppelen.") from None
        if exc.reason not in my_house.CONNECTION_ERRORS:
            raise HubError(409, exc.reason, "De Hub kan de leesverbinding met my_house niet bevestigen.") from None
        raise HubError(
            503,
            "my_house_unavailable",
            "De Hub kon de gegevens van my_house niet ophalen.",
            headers={"Retry-After": "1"},
        ) from None
    response.headers["Cache-Control"] = "no-store"
    return snapshot


@router.get("/{link_id}/mediaguard", summary="MediaGuard-overzicht lezen (alleen lezen)")
def read_mediaguard(
    link_id: uuid.UUID, db: DB, _: Viewer, response: Response, settings: SettingsDep, vault: VaultDep
) -> mediaguard_lezen.Overzicht:
    """Vijf cijfers en de noodstop uit de MediaGuard-connector; bij twijfel `onbekend` met reden, nooit 0."""
    row = _link(db, link_id)
    if row.app_id != mediaguard.APP_ID:
        raise HubError(404, "not_found", "Geen MediaGuard-koppeling gevonden.")
    response.headers["Cache-Control"] = "no-store"
    return mediaguard_lezen.lees_overzicht(db, settings, vault, row, uuid.uuid4())


@router.get("/{link_id}", summary="Adapterkoppeling lezen")
def get_link(
    link_id: uuid.UUID, response: Response, db: DB, _: AnyUser, settings: SettingsDep
) -> MediaGuardLinkView | LinkView:
    row = _link(db, link_id)
    response.headers["ETag"] = _etag(row.version)
    target = db.get(CatalogApp, row.catalog_app_id)
    nas = current_target(db)
    return _view(row, bound=binding_is_current(row, target, nas, _published_ports(db, settings, nas)))


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


@router.put(
    "/{link_id}/poolleesrecht",
    response_model=PoolrechtReceipt,
    summary="Poolleesrecht voor MediaGuard uitgeven, vervangen of intrekken (beheerder)",
)
def poolleesrecht(
    link_id: uuid.UUID,
    body: PoolrechtIn,
    db: DB,
    admin: Admin,
    idem: Idem,
    settings: SettingsDep,
    if_match: IfMatch = None,
) -> JSONResponse:
    """Bij inschakelen verschijnt `pool_token` eenmaal. Dezelfde Idempotency-Key geeft daarna alleen de bevestiging."""
    if (replay := _replay_link(idem)) is not None:
        return replay
    row = _link(db, link_id, lock=True)
    if (replay := _replay_link(idem)) is not None:
        return replay
    _precondition(row, if_match)
    if row.app_id != mediaguard.APP_ID:
        raise HubError(403, "forbidden", "Alleen MediaGuard kan het poolleesrecht krijgen.")
    if body.ingeschakeld and not confirmed_binding(db, settings, row, current_target(db)):
        raise _binding_conflict()
    token = new_token(mediaguard.POOL_TOKEN_PREFIX) if body.ingeschakeld else None
    row.pool_token_hash = sha256_hex(token) if token else None
    row.version += 1
    _record(db, admin, row, "poolleesrecht_uitgegeven" if token else "poolleesrecht_ingetrokken")
    receipt = PoolrechtReceipt(id=row.id, version=row.version, pool_token=token)
    response = _save_link(idem, 200, row)
    if token is None:
        return response
    # Alleen de bevestiging is herhaalbaar. Het token komt nooit in het idempotentieregister.
    return JSONResponse(
        receipt.model_dump(mode="json"), headers={"ETag": response.headers["ETag"], "Cache-Control": "no-store"}
    )


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
        if row.app_id == mso.APP_ID and (catalog_app_id, base, peers) != (
            row.catalog_app_id,
            row.basis_url,
            row.peer_addresses,
        ):
            row.laatste_fout = None
        row.catalog_app_id, row.basis_url, row.peer_addresses = catalog_app_id, base, peers
    elif secret is not None and secret.casefold() in row.basis_url.casefold():
        raise HubError(422, "validation_error", "De waarde van het adaptercredential is ongeldig.")
    elif not binding_is_current(row, target, nas, owners):
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
    if row.pool_token_hash is not None:
        row.pool_token_hash = None
        _record(db, admin, row, "poolleesrecht_ingetrokken")
    # Een nieuwe koppeling begint met een schone reeks; een open incident vereist nog steeds herstel.
    if row.health_failures < 3:
        row.health_failures = 0
    if row.app_id not in (my_house.APP_ID, mso.APP_ID):
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
        if not binding_is_current(row, target, nas, _published_ports(db, settings, nas)):
            raise _binding_conflict()

    policy = settings.outbound_policy()
    probes = None
    snapshot = None
    if row.app_id == my_house.APP_ID:
        adapter = _house_adapter(db, settings, row, target)
        now = utcnow()
        try:
            # Behoud een vernieuwd token als de daaropvolgende gezondheidslezing faalt.
            with db.begin_nested():
                credential = _house_credential(db, vault, row, now)
                credential = _house_renew(db, vault, row, adapter, credential, now)
            with db.begin_nested():
                reading = adapter.read_snapshot(credential.token)
                row.my_house_checks = my_house.CheckReadings.dump_python(reading.checks, mode="json")
                db.add(
                    AdapterHouseSnapshot(
                        receipt_scope=idem.scope,
                        receipt_key=idem.key,
                        link_id=row.id,
                        measurement=reading.model_dump(mode="json"),
                    )
                )
        except OutboundError as exc:
            measurement = basis.Measurement(status="unknown", reason_code=exc.reason)
        except Exception as exc:
            log.warning("Adaptercontrole mislukt (%s)", type(exc).__name__)
            measurement = basis.Measurement(status="unknown", reason_code="bron_onbereikbaar")
        else:
            snapshot = reading
            measurement = basis.Measurement(status="healthy", observed_at=reading.snapshot.observed_at)
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
    if row.app_id == my_house.APP_ID:
        _record_health_measurement(db, row, utcnow())
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
