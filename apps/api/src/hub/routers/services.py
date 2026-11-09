"""Aanmelden van eigen diensten bij de Hub (enrollment, contract §3) en het register van service-tokens.

- Eenmalige enrollment-tokens (60 min, single-use) voor apps die de Hub via de TrueNAS-API installeert
  (env ``HUB_URL`` + ``HUB_ENROLLMENT_TOKEN``), en koppelcodes voor handmatig geïnstalleerde apps.
- Alleen hashes van tokens/codes in de database; het service-token wordt precies één keer getoond.
- Rotatie zonder herinstallatie: de oude token blijft een korte overgangstijd geldig.
"""

from __future__ import annotations

import base64
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update

from hub import audit
from hub.deps import DB, Admin, Idem, Operator, ServiceP, SettingsDep, get_keyring
from hub.errors import HubError
from hub.events.envelope import APP_ID_PATTERN
from hub.keys import KeyRing
from hub.models import EnrollmentGrant, Service, ServiceToken
from hub.security import (
    clear_failures,
    failures_in_window,
    new_pairing_code,
    new_token,
    normalize_pairing_code,
    record_failure,
    sha256_hex,
)
from hub.timeutil import iso, utcnow
from hub.vault import last4

router = APIRouter(prefix="/api/v1/services", tags=["diensten en enrollment"])


class GrantIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: str = Field(pattern=APP_ID_PATTERN)


class EnrollIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    app_id: str = Field(pattern=APP_ID_PATTERN)
    enrollment_token: str | None = Field(default=None, max_length=128)
    pairing_code: str | None = Field(default=None, max_length=32)
    version: str = Field(default="", max_length=64)
    base_url: str | None = Field(default=None, max_length=512, pattern=r"^https?://[^\s/]+(:\d+)?(/.*)?$")
    public_key_jwk: dict[str, str] | None = None

    @model_validator(mode="after")
    def _one_secret(self) -> EnrollIn:
        if bool(self.enrollment_token) == bool(self.pairing_code):
            raise ValueError("geef precies één van enrollment_token of pairing_code")
        return self

    @field_validator("public_key_jwk")
    @classmethod
    def _jwk(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None:
            return v
        if v.get("kty") != "OKP" or v.get("crv") != "Ed25519" or "d" in v:
            raise ValueError("alleen een publieke Ed25519-JWK (kty=OKP, crv=Ed25519, zonder 'd')")
        x = v.get("x", "")
        try:
            raw = base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))
        except ValueError as exc:
            raise ValueError("x is geen base64url") from exc
        if len(raw) != 32:
            raise ValueError("x moet 32 bytes zijn")
        return {k: v[k] for k in ("kty", "crv", "x", "kid") if k in v}


def _service_dict(db: Any, svc: Service) -> dict[str, Any]:
    tokens = db.scalars(
        select(ServiceToken).where(ServiceToken.service_id == svc.id).order_by(ServiceToken.created_at.desc())
    )
    now = utcnow()
    return {
        "id": str(svc.id),
        "app_id": svc.app_id,
        "status": svc.status,
        "version": svc.version,
        "base_url": svc.base_url,
        "public_key_jwk": svc.public_key_jwk,
        "enrolled_via": svc.enrolled_via,
        "enrolled_at": iso(svc.enrolled_at),
        "updated_at": iso(svc.updated_at),
        "tokens": [
            {
                "id": str(t.id),
                "laatste4": t.last4,
                "aangemaakt": iso(t.created_at),
                "verloopt": iso(t.expires_at),
                "ingetrokken": iso(t.revoked_at),
                "laatst_gebruikt": iso(t.last_used_at),
                "geldig": t.revoked_at is None and (t.expires_at is None or t.expires_at > now),
            }
            for t in tokens
        ],
    }


def _issue_token(db: Any, svc: Service, rotated_from: uuid.UUID | None = None) -> str:
    token = new_token("svc")
    db.add(ServiceToken(service_id=svc.id, token_hash=sha256_hex(token), last4=last4(token), rotated_from=rotated_from))
    return token


def _grant(
    db: Any, settings: Any, principal: Any, app_id: str, kind: Literal["token", "koppelcode"]
) -> tuple[EnrollmentGrant, str]:
    secret = new_token("enr") if kind == "token" else new_pairing_code()
    hashed = sha256_hex(secret) if kind == "token" else sha256_hex(normalize_pairing_code(secret))
    ttl = settings.enrollment_token_ttl_seconds if kind == "token" else settings.pairing_code_ttl_seconds
    grant = EnrollmentGrant(
        kind=kind,
        purpose="service",
        app_id=app_id,
        secret_hash=hashed,
        created_by=principal.name,
        expires_at=utcnow() + timedelta(seconds=ttl),
    )
    db.add(grant)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action=f"enrollment.{kind}_created",
        target_type="service",
        target_id=app_id,
        details={"grant_id": str(grant.id)},
    )
    db.commit()
    return grant, secret


@router.post("/enrollment-tokens", status_code=201, summary="Eenmalig enrollment-token (60 min) voor een app (admin)")
def create_enrollment_token(body: GrantIn, db: DB, settings: SettingsDep, principal: Admin) -> JSONResponse:
    # Geeft een geheim terug: niet idempotent opgeslagen (ADR-0006); elke aanroep maakt een nieuw token.
    grant, secret = _grant(db, settings, principal, body.app_id, "token")
    return JSONResponse(
        {
            "grant_id": str(grant.id),
            "app_id": body.app_id,
            "enrollment_token": secret,
            "verloopt_op": iso(grant.expires_at),
            "env": {"HUB_ENROLLMENT_TOKEN": "<dit token>", "HUB_URL": "<adres van de Hub>"},
        },
        status_code=201,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/pairing-codes", status_code=201, summary="Koppelcode voor een handmatig geïnstalleerde app (admin)")
def create_pairing_code(body: GrantIn, db: DB, settings: SettingsDep, principal: Admin) -> JSONResponse:
    grant, secret = _grant(db, settings, principal, body.app_id, "koppelcode")
    return JSONResponse(
        {"grant_id": str(grant.id), "app_id": body.app_id, "koppelcode": secret, "verloopt_op": iso(grant.expires_at)},
        status_code=201,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/enroll", summary="Dienst meldt zich aan met enrollment-token of koppelcode (eenmalig)")
def enroll(
    body: EnrollIn, request: Request, db: DB, settings: SettingsDep, keyring: Annotated[KeyRing, Depends(get_keyring)]
) -> JSONResponse:
    ip = request.client.host if request.client else "onbekend"
    rl_key = f"enroll:{ip}"
    if failures_in_window(db, rl_key, settings.login_window_seconds) >= settings.login_max_failures * 2:
        raise HubError(
            429,
            "rate_limited",
            "Te veel mislukte aanmeldingen; probeer het later opnieuw.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
    if body.enrollment_token:
        kind, hashed = "token", sha256_hex(body.enrollment_token)
    else:
        kind, hashed = "koppelcode", sha256_hex(normalize_pairing_code(body.pairing_code or ""))
    now = utcnow()
    grant_id = db.scalar(
        update(EnrollmentGrant)
        .where(
            EnrollmentGrant.secret_hash == hashed,
            EnrollmentGrant.kind == kind,
            EnrollmentGrant.app_id == body.app_id,
            EnrollmentGrant.used_at.is_(None),
            EnrollmentGrant.expires_at > now,
            EnrollmentGrant.purpose == "service",
        )
        .values(used_at=now)
        .returning(EnrollmentGrant.id)
    )
    if grant_id is None:
        record_failure(db, rl_key)
        audit.record(
            db, actor_type="service", actor_id=body.app_id, action="enrollment.failed", details={"ip": ip, "via": kind}
        )
        db.commit()
        raise HubError(401, "invalid_enrollment", "Enrollment-token of koppelcode ongeldig, al gebruikt of verlopen.")
    svc = db.scalars(select(Service).where(Service.app_id == body.app_id)).first()
    if svc is None:
        svc = Service(app_id=body.app_id, enrolled_via=kind)
        db.add(svc)
        db.flush()
    else:  # herinstallatie/herkoppeling: oude tokens vervallen
        db.execute(
            update(ServiceToken)
            .where(ServiceToken.service_id == svc.id, ServiceToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        svc.enrolled_via, svc.enrolled_at = kind, now
    svc.status, svc.version, svc.base_url, svc.updated_at = "active", body.version, body.base_url, now
    svc.public_key_jwk = body.public_key_jwk
    grant = db.get(EnrollmentGrant, grant_id)
    if grant is not None:
        grant.used_by_service = svc.id
    token = _issue_token(db, svc)
    clear_failures(db, rl_key)
    audit.record(
        db,
        actor_type="service",
        actor_id=body.app_id,
        action="enrollment.completed",
        target_type="service",
        target_id=str(svc.id),
        details={"via": kind, "version": body.version},
    )
    db.commit()
    return JSONResponse(
        {
            "service_id": str(svc.id),
            "app_id": svc.app_id,
            "service_token": token,
            "token_type": "Bearer",
            "hub_issuer": "hub",
            "jwks": keyring.jwks(),
            "jwks_url": "/api/v1/auth/jwks",
            "policy_public_key": keyring.policy_public_jwk(),
            "events_inbox_url": "/api/v1/events/inbox",
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("", summary="Register van diensten en tokens (alleen laatste 4 tekens)")
def list_services(db: DB, _: Operator) -> dict[str, Any]:
    return {"items": [_service_dict(db, s) for s in db.scalars(select(Service).order_by(Service.app_id))]}


@router.post("/self/rotate", summary="Dienst roteert zijn eigen token (Bearer)")
def rotate_self(db: DB, settings: SettingsDep, principal: ServiceP) -> JSONResponse:
    svc = db.get(Service, uuid.UUID(principal.id))
    assert svc is not None
    return _rotate(db, settings, svc, principal.actor, current=principal.service_token_id)


@router.post("/{service_id}/rotate", summary="Service-token roteren (admin); nieuw token wordt één keer getoond")
def rotate(service_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Admin) -> JSONResponse:
    svc = db.get(Service, service_id)
    if svc is None or svc.status != "active":
        raise HubError(404, "not_found", "Actieve dienst niet gevonden.")
    return _rotate(db, settings, svc, principal.actor)


def _rotate(db: Any, settings: Any, svc: Service, actor: str, current: uuid.UUID | None = None) -> JSONResponse:
    grace_until = utcnow() + timedelta(seconds=settings.service_token_rotation_grace_seconds)
    olds = list(
        db.scalars(select(ServiceToken).where(ServiceToken.service_id == svc.id, ServiceToken.revoked_at.is_(None)))
    )
    for t in olds:
        if t.expires_at is None or t.expires_at > grace_until:
            t.expires_at = grace_until
    token = _issue_token(db, svc, rotated_from=current or (olds[0].id if olds else None))
    audit.record(
        db,
        actor_type=actor.split(":")[0],
        actor_id=actor.split(":", 1)[1],
        action="service.token_rotated",
        target_type="service",
        target_id=str(svc.id),
    )
    db.commit()
    return JSONResponse(
        {"service_id": str(svc.id), "service_token": token, "oude_tokens_geldig_tot": iso(grace_until)},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{service_id}/revoke", summary="Dienst en al zijn tokens intrekken (admin)")
def revoke(service_id: uuid.UUID, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    svc = db.get(Service, service_id)
    if svc is None:
        raise HubError(404, "not_found", "Dienst niet gevonden.")
    svc.status, svc.updated_at = "revoked", utcnow()
    db.execute(
        update(ServiceToken)
        .where(ServiceToken.service_id == svc.id, ServiceToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="service.revoked",
        target_type="service",
        target_id=str(svc.id),
    )
    db.flush()
    return idem.save(200, _service_dict(db, svc))
