"""Aanmelden van eigen diensten bij de Hub (enrollment, contract 1.3 §3.3–§3.9) en het register van service-tokens.

- Eenmalige enrollment-tokens (60 min) voor apps die de Hub via de TrueNAS-API installeert (env ``HUB_URL`` +
  ``HUB_ENROLLMENT_TOKEN`` + ``HUB_KEY_FINGERPRINT``), en koppelcodes (60 min; executor 30 min) voor handmatig
  geïnstalleerde apps. Alleen hashes in de database; het service-token wordt precies één keer teruggegeven.
- Toegestane herhaling na een herstart halverwege (§3.6): zelfde grant, ``app_id`` en sleutel-thumbprint, binnen de
  60 min, en het eerder uitgegeven token is nooit gebruikt.
- Nieuwe enrollment van een bestaande registratie (1.3 §3.6): ``service_id`` blijft; de oude tokens worden pas
  ingetrokken bij het **eerste gebruik** van het nieuwe token; blijft het nieuwe 60 min ongebruikt, dan vervalt het en
  blijven de oude geldig (een mislukte herkoppeling breekt een bestaande koppeling niet).
- ``base_url`` is alleen informatief: een waarde die niet aan §3.3 voldoet, wordt ``null`` met een waarschuwing in de
  Hub-UI — nooit een reden om te weigeren (alleen een ander type dan string/null → 422).
- Rotatie (§3.8): de dienst roteert zelf (``self/rotate``); een beheerder kan rotatie alleen **aanvragen** (202).
  Het oude token vervalt 10 min na het eerste gebruik van het nieuwe, hooguit 24 uur na de rotatie.
- Koppelbeheer is nooit een ``action_id`` (§8): alleen beheerdersroutes met audit; de AI kan dit niet.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from hub import APP_ID, audit
from hub.config import Settings
from hub.deps import DB, Admin, Idem, Operator, Principal, ServiceP, SettingsDep, get_keyring
from hub.errors import HubError
from hub.keys import ROTATION_SEQUENCE, KeyRing, jwk_thumbprint
from hub.models import EnrollmentGrant, Service, ServiceToken
from hub.outbound import OutboundError, validate_base_url
from hub.registry import app_name_candidates, app_name_for, measured_apps, service_base_url
from hub.scopes import scopes_for
from hub.security import (
    clear_failures,
    failures_in_window,
    is_valid_pairing_code,
    new_pairing_code,
    new_token,
    normalize_pairing_code,
    record_failure,
    retry_after_seconds,
    sha256_hex,
)
from hub.servicecalls import ServiceCallError, call
from hub.timeutil import iso, utcnow
from hub.vault import last4

router = APIRouter(prefix="/api/v1/services", tags=["diensten en enrollment"])

ENROLL_SCHEMA_VERSION = "1.3"
EXECUTOR_APP_ID = "ai-server-manager-executor"
# TrueNAS-appnaampatroon (contract 1.3 §3.3), 1–40 tekens.
TRUENAS_APP_NAME = r"^[a-z]([-a-z0-9]*[a-z0-9])?$"
ENROLLMENT_TOKEN = r"^enr_[A-Za-z0-9_-]{43}$"  # noqa: S105 — patroon, geen geheim
SERVICE_VERSION = r"^[0-9A-Za-z][0-9A-Za-z.+_-]*$"
JWK_FIELDS = {"kty", "crv", "x", "kid"}
REENROLL_UNUSED_SECONDS = 60 * 60  # §3.6: een nieuw token van een bestaande registratie vervalt na 60 min ongebruikt


def informative_base_url(value: str | None) -> tuple[str | None, bool]:
    """§3.3: ``http(s)://host[:poort][/pad]``, ≤ 512 tekens en de adresregels van §3.2 → ``(waarde, genegeerd)``.
    Een string die daar niet aan voldoet wordt ``null`` met ``genegeerd=True`` (waarschuwing), nooit een weigering."""
    if value is None:
        return None, False
    if len(value) > 512 or value != value.strip():
        return None, True
    try:
        return validate_base_url(value), False
    except OutboundError:
        return None, True


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GrantIn(Strict):
    app_id: str = Field(min_length=1, max_length=40, pattern=TRUENAS_APP_NAME)

    @field_validator("app_id")
    @classmethod
    def _not_hub(cls, v: str) -> str:
        if v == APP_ID:
            raise ValueError("de Hub meldt zich niet bij zichzelf aan")
        return v


class EnrollIn(Strict):
    """Exact schema van contract 1.3 §3.3; onbekende velden → 422. ``base_url`` alleen op type (string of null)."""

    app_id: str = Field(min_length=1, max_length=40, pattern=TRUENAS_APP_NAME)
    enrollment_token: str | None = Field(default=None, pattern=ENROLLMENT_TOKEN)
    pairing_code: str | None = Field(default=None, max_length=32)
    version: str = Field(min_length=1, max_length=64, pattern=SERVICE_VERSION)
    base_url: str | None
    public_key_jwk: dict[str, Any]

    @field_validator("pairing_code")
    @classmethod
    def _code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not is_valid_pairing_code(normalize_pairing_code(v)):
            raise ValueError("koppelcode moet na normalisatie precies 12 tekens uit het Crockford-alfabet zijn")
        return v

    @field_validator("public_key_jwk")
    @classmethod
    def _jwk(cls, v: dict[str, Any]) -> dict[str, Any]:
        extra = sorted(set(v) - JWK_FIELDS)
        if extra:
            raise ValueError(f"niet toegestane JWK-velden: {', '.join(extra)} (alleen kty, crv, x en kid)")
        if not all(isinstance(value, str) for value in v.values()):
            raise ValueError("JWK-waarden moeten tekst zijn")
        if len(v.get("x", "")) != 43:
            raise ValueError("x moet 43 tekens base64url zijn (32 bytes)")
        thumbprint = jwk_thumbprint(v)
        if "kid" in v and v["kid"] != thumbprint:
            raise ValueError("kid moet de RFC 7638-thumbprint van de sleutel zijn")
        return {"kty": "OKP", "crv": "Ed25519", "x": v["x"], "kid": thumbprint}

    @model_validator(mode="after")
    def _one_secret(self) -> EnrollIn:
        if (self.enrollment_token is None) == (self.pairing_code is None):
            raise ValueError("geef precies één van enrollment_token of pairing_code")
        return self


class TrueNasAppIn(Strict):
    app_name: str = Field(min_length=1, max_length=40, pattern=TRUENAS_APP_NAME)


# ------------------------------------------------------------------ hulpfuncties
def _valid_tokens(db: Session, svc: Service) -> list[ServiceToken]:
    now = utcnow()
    return [
        t
        for t in db.scalars(
            select(ServiceToken)
            .where(ServiceToken.service_id == svc.id, ServiceToken.revoked_at.is_(None))
            .order_by(ServiceToken.created_at.desc())
        )
        if t.expires_at is None or t.expires_at > now
    ]


def _service_dict(db: Session, settings: Settings, svc: Service) -> dict[str, Any]:
    tokens = list(
        db.scalars(
            select(ServiceToken).where(ServiceToken.service_id == svc.id).order_by(ServiceToken.created_at.desc())
        )
    )
    now = utcnow()
    valid = [t for t in tokens if t.revoked_at is None and (t.expires_at is None or t.expires_at > now)]
    newest = valid[0] if valid else None
    advice_after = timedelta(days=settings.service_token_rotation_advice_days)
    return {
        "id": str(svc.id),
        "app_id": svc.app_id,
        "status": svc.status,
        "version": svc.version,
        "base_url": svc.base_url,
        # Contract 1.3 §3.3: de dienst stuurde een base_url die niet aan de regels voldoet; bewaard als null.
        "base_url_genegeerd": svc.base_url_genegeerd,
        # Contract 1.3 §4.4: vaste leesscopes van deze dienst (in de Hub vastgelegd, niet door de dienst te kiezen).
        "scopes": scopes_for(svc.app_id),
        "public_key_jwk": svc.public_key_jwk,
        "enrolled_via": svc.enrolled_via,
        "enrolled_at": iso(svc.enrolled_at),
        "updated_at": iso(svc.updated_at),
        "truenas_app": {
            "naam": app_name_for(svc),
            "bevestigd": svc.truenas_app_name is not None,
            "bevestigd_door": svc.truenas_app_name_confirmed_by,
            "bevestigd_op": iso(svc.truenas_app_name_confirmed_at),
        },
        "rotatie": {
            "aangevraagd_op": iso(svc.rotation_requested_at),
            "aangevraagd_door": svc.rotation_requested_by,
            # Alleen een melding (contract 1.3 §3.8): de Hub roteert nooit op eigen initiatief.
            "aanbevolen": newest is not None and now - newest.created_at > advice_after,
            "token_leeftijd_dagen": None if newest is None else (now - newest.created_at).days,
        },
        "tokens": [
            {
                "id": str(t.id),
                "laatste4": t.last4,
                "aangemaakt": iso(t.created_at),
                "verloopt": iso(t.expires_at),
                "ingetrokken": iso(t.revoked_at),
                "eerst_gebruikt": iso(t.first_used_at),
                "laatst_gebruikt": iso(t.last_used_at),
                "vervangen_op": iso(t.superseded_at),
                "geldig": t in valid,
            }
            for t in tokens
        ],
    }


def _issue_token(
    db: Session,
    svc: Service,
    *,
    grant_id: uuid.UUID | None,
    rotated_from: uuid.UUID | None,
    expires_at: datetime | None = None,
) -> str:
    token = new_token("svc")
    db.add(
        ServiceToken(
            service_id=svc.id,
            token_hash=sha256_hex(token),
            last4=last4(token),
            rotated_from=rotated_from,
            grant_id=grant_id,
            expires_at=expires_at,
        )
    )
    return token


def _has_other_valid_tokens(db: Session, svc: Service, grant_id: uuid.UUID) -> bool:
    """Geldige tokens van deze registratie die niet via deze grant zijn uitgegeven (herkoppelen van een bestaande)."""
    if svc.id is None:
        return False
    return any(t.grant_id != grant_id for t in _valid_tokens(db, svc))


def _grant(
    db: Session, settings: Settings, principal: Principal, app_id: str, kind: Literal["token", "koppelcode"]
) -> tuple[EnrollmentGrant, str]:
    executor = app_id == EXECUTOR_APP_ID
    if executor and kind == "token":
        raise HubError(
            422,
            "executor_requires_pairing_code",
            "De executor koppelt alleen met een koppelcode (30 min) op zijn eigen statuspagina (contract §3.9).",
        )
    secret = new_token("enr") if kind == "token" else new_pairing_code()
    hashed = sha256_hex(secret) if kind == "token" else sha256_hex(normalize_pairing_code(secret))
    if kind == "token":
        ttl = settings.enrollment_token_ttl_seconds
    else:
        ttl = settings.executor_pairing_code_ttl_seconds if executor else settings.pairing_code_ttl_seconds
    grant = EnrollmentGrant(
        kind=kind,
        purpose="executor" if executor else "service",
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


def _replay_allowed(db: Session, grant: EnrollmentGrant, thumbprint: str) -> Service | None:
    """Toegestane herhaling (§3.6): zelfde sleutel en het via deze grant uitgegeven token is nooit gebruikt."""
    if grant.used_with_key_thumbprint != thumbprint or grant.used_by_service is None:
        return None
    tokens = list(
        db.scalars(
            select(ServiceToken).where(ServiceToken.grant_id == grant.id).order_by(ServiceToken.created_at.desc())
        )
    )
    if not tokens or tokens[0].revoked_at is not None:
        return None  # ingetrokken (beheerder, herinschrijving met een andere grant): geen herhaling
    if any(t.first_used_at is not None or t.last_used_at is not None for t in tokens):
        return None  # de dienst heeft het token gebruikt (bevestiging): de herhaling is dicht
    svc = db.get(Service, grant.used_by_service)
    return svc if svc is not None and svc.status == "active" else None


def _revoke_all(db: Session, svc: Service) -> None:
    db.execute(
        update(ServiceToken)
        .where(ServiceToken.service_id == svc.id, ServiceToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


# ------------------------------------------------------------------ uitgifte (admin)
@router.post("/enrollment-tokens", status_code=201, summary="Eenmalig enrollment-token (60 min) voor een app (admin)")
def create_enrollment_token(
    body: GrantIn,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> JSONResponse:
    # Geeft een geheim terug: niet idempotent opgeslagen (ADR-0006); elke aanroep maakt een nieuw token.
    grant, secret = _grant(db, settings, principal, body.app_id, "token")
    fingerprint = keyring.keyset_fingerprint()
    return JSONResponse(
        {
            "grant_id": str(grant.id),
            "app_id": body.app_id,
            "enrollment_token": secret,
            "verloopt_op": iso(grant.expires_at),
            "keyset_fingerprint": fingerprint,
            "env": {
                "HUB_URL": "<adres van de Hub>",
                "HUB_ENROLLMENT_TOKEN": "<dit token>",
                "HUB_KEY_FINGERPRINT": fingerprint,
            },
        },
        status_code=201,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/pairing-codes", status_code=201, summary="Koppelcode voor een handmatig geïnstalleerde app (admin)")
def create_pairing_code(
    body: GrantIn,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> JSONResponse:
    grant, secret = _grant(db, settings, principal, body.app_id, "koppelcode")
    return JSONResponse(
        {
            "grant_id": str(grant.id),
            "app_id": body.app_id,
            "koppelcode": secret,
            "verloopt_op": iso(grant.expires_at),
            "keyset_fingerprint": keyring.keyset_fingerprint(),
        },
        status_code=201,
        headers={"Cache-Control": "no-store"},
    )


# ------------------------------------------------------------------ enrollment (geen authenticatie)
@router.post(
    "/enroll",
    summary="Dienst meldt zich aan met enrollment-token of koppelcode (contract 1.3 §3.3); antwoord schema_version 1.3",
    responses={
        401: {"description": "invalid_enrollment (onbekend, verlopen, al gebruikt of andere app_id)"},
        422: {"description": "validation_error"},
        429: {"description": "rate_limited (met Retry-After)"},
    },
)
def enroll(
    body: EnrollIn,
    request: Request,
    db: DB,
    settings: SettingsDep,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> JSONResponse:
    ip = request.client.host if request.client else "onbekend"
    rl_key = f"enroll:{ip}"
    window, max_failures = settings.enroll_window_seconds, settings.enroll_max_failures
    if failures_in_window(db, rl_key, window) >= max_failures:
        wait = retry_after_seconds(db, rl_key, window, max_failures) or 1
        raise HubError(
            429,
            "rate_limited",
            "Te veel mislukte aanmeldingen vanaf dit adres; probeer het later opnieuw.",
            details={"retry_after_seconds": wait},
            headers={"Retry-After": str(wait)},
        )
    if body.enrollment_token is not None:
        kind, hashed = "token", sha256_hex(body.enrollment_token)
    else:
        kind, hashed = "koppelcode", sha256_hex(normalize_pairing_code(body.pairing_code or ""))
    thumbprint = str(body.public_key_jwk["kid"])
    now = utcnow()
    # Rijvergrendeling: twee gelijktijdige pogingen met hetzelfde geheim worden na elkaar beoordeeld.
    grant = db.scalars(
        select(EnrollmentGrant)
        .where(EnrollmentGrant.secret_hash == hashed, EnrollmentGrant.kind == kind)
        .with_for_update()
    ).first()
    replay_svc: Service | None = None
    ok = (
        grant is not None
        and grant.app_id == body.app_id
        and grant.expires_at > now
        and grant.purpose == ("executor" if body.app_id == EXECUTOR_APP_ID else "service")
    )
    if ok and grant is not None and grant.used_at is not None:
        replay_svc = _replay_allowed(db, grant, thumbprint)
        ok = replay_svc is not None
    if not ok or grant is None:
        db.rollback()
        record_failure(db, rl_key)
        audit.record(
            db, actor_type="service", actor_id=body.app_id, action="enrollment.failed", details={"ip": ip, "via": kind}
        )
        db.commit()
        raise HubError(401, "invalid_enrollment", "Enrollment-token of koppelcode ongeldig, al gebruikt of verlopen.")

    if replay_svc is not None:
        svc = replay_svc
        db.execute(
            update(ServiceToken)
            .where(ServiceToken.grant_id == grant.id, ServiceToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
    else:
        grant.used_at, grant.used_with_key_thumbprint = now, thumbprint
        found = db.scalars(select(Service).where(Service.app_id == body.app_id)).first()
        if found is None:
            svc = Service(app_id=body.app_id, enrolled_via=kind, enrolled_at=now)
            db.add(svc)
            db.flush()
        else:
            # Herinstallatie/opnieuw koppelen (§3.6): service_id blijft. De oude tokens blijven geldig tot het eerste
            # gebruik van het nieuwe token (deps._service_principal); blijft dat 60 min ongebruikt, dan vervalt het.
            svc = found
            svc.enrolled_via, svc.enrolled_at = kind, now
        grant.used_by_service = svc.id
    base_url, ignored = informative_base_url(body.base_url)
    svc.status, svc.version, svc.base_url, svc.updated_at = "active", body.version, base_url, now
    svc.base_url_genegeerd = ignored
    svc.public_key_jwk = body.public_key_jwk
    svc.rotation_requested_at = svc.rotation_requested_by = None
    # §3.6: bestaan er nog geldige tokens van deze registratie, dan blijven die geldig tot het eerste gebruik van het
    # nieuwe token; het nieuwe vervalt als het 60 min ongebruikt blijft.
    deadline = now + timedelta(seconds=REENROLL_UNUSED_SECONDS) if _has_other_valid_tokens(db, svc, grant.id) else None
    token = _issue_token(db, svc, grant_id=grant.id, rotated_from=None, expires_at=deadline)
    clear_failures(db, rl_key)
    audit.record(
        db,
        actor_type="service",
        actor_id=body.app_id,
        action="enrollment.replayed" if replay_svc is not None else "enrollment.completed",
        target_type="service",
        target_id=str(svc.id),
        details={"via": kind, "version": body.version, "grant_id": str(grant.id), "key_thumbprint": thumbprint},
    )
    db.commit()
    return JSONResponse(
        {
            "schema_version": ENROLL_SCHEMA_VERSION,
            "service_id": str(svc.id),
            "app_id": svc.app_id,
            "service_token": token,
            "token_type": "Bearer",
            "hub_issuer": "hub",
            "jwks": keyring.jwks(),
            "policy_public_key": keyring.policy_public_jwk(),
            "keyset_fingerprint": keyring.keyset_fingerprint(),
            "jwks_url": "/api/v1/auth/jwks",
            "events_inbox_url": "/api/v1/events/inbox",
            "key_rotation_url": "/api/v1/auth/key-rotations",
            "enrollment_replayed": replay_svc is not None,
            # Nieuw in 1.3 (§3.3): huidige reeks van de sleutelrotatie; de dienst vraagt alleen key-rotations?after=.
            "rotation_sequence": ROTATION_SEQUENCE,
        },
        headers={"Cache-Control": "no-store"},
    )


# ------------------------------------------------------------------ dienst zelf (Bearer service-token)
@router.get("/self", summary="Dienst bevestigt zijn koppeling (Bearer service-token, contract 1.3 §3.6)")
def service_self(db: DB, principal: ServiceP, keyring: Annotated[KeyRing, Depends(get_keyring)]) -> dict[str, Any]:
    svc = db.get(Service, uuid.UUID(principal.id))
    if svc is None:
        raise HubError(401, "unauthorized", "Deze dienst is niet (meer) ingeschreven.")
    return {
        "service_id": str(svc.id),
        "app_id": svc.app_id,
        "status": svc.status,
        "version": svc.version,
        "enrolled_at": iso(svc.enrolled_at),
        "keyset_fingerprint": keyring.keyset_fingerprint(),
    }


@router.post("/self/rotate", summary="Dienst roteert zijn eigen service-token (Bearer, contract 1.3 §3.8)")
def rotate_self(db: DB, settings: SettingsDep, principal: ServiceP) -> JSONResponse:
    svc = db.get(Service, uuid.UUID(principal.id))
    if svc is None:
        raise HubError(401, "unauthorized", "Deze dienst is niet (meer) ingeschreven.")
    now = utcnow()
    cap = now + timedelta(seconds=settings.service_token_rotation_max_seconds)
    current_id = principal.service_token_id
    current_expires = None
    for t in _valid_tokens(db, svc):
        if t.id != current_id and t.first_used_at is None and t.grant_id is not None:
            continue  # nog ongebruikt token van een herkoppeling (§3.6): dat beslist zelf bij zijn eerste gebruik
        if t.id != current_id and t.first_used_at is None:
            t.revoked_at = now  # eerder uitgegeven, nooit gebruikte nieuwe tokens (herhaalde rotatie)
            continue
        t.superseded_at = t.superseded_at or now
        if t.expires_at is None or t.expires_at > cap:
            t.expires_at = cap  # bovengrens; het eerste gebruik van het nieuwe token verkort dit tot 10 min
        if t.id == current_id:
            current_expires = t.expires_at
    token = _issue_token(db, svc, grant_id=None, rotated_from=current_id)
    svc.rotation_requested_at = svc.rotation_requested_by = None
    svc.updated_at = now
    audit.record(
        db,
        actor_type="service",
        actor_id=svc.app_id,
        action="service.token_rotated",
        target_type="service",
        target_id=str(svc.id),
    )
    db.commit()
    return JSONResponse(
        {"service_id": str(svc.id), "service_token": token, "oude_tokens_geldig_tot": iso(current_expires or cap)},
        headers={"Cache-Control": "no-store"},
    )


# ------------------------------------------------------------------ register en beheer (gebruikers)
@router.get("", summary="Register van diensten en tokens (alleen laatste 4 tekens)")
def list_services(db: DB, settings: SettingsDep, _: Operator) -> dict[str, Any]:
    st = measured_apps(db, settings)
    apps = st.get("data") if st.get("status") == "ok" else None
    items = []
    for s in db.scalars(select(Service).order_by(Service.app_id)):
        item = _service_dict(db, settings, s)
        item["truenas_app"]["gemeten_kandidaten"] = None if apps is None else app_name_candidates(apps, s.app_id)
        items.append(item)
    return {"items": items, "inventaris": {"status": st.get("status"), "observed_at": st.get("observed_at")}}


# Contract 1.3 §3.5: de publieke witte lijst van een dienst (een maximum); de Hub geeft nooit meer door dan dit.
HUB_LINK_FIELDS = (
    "state",
    "koppelen_bezig",
    "hub_url",
    "service_id",
    "via",
    "linked_at",
    "first_linked_at",
    "keyset_fingerprint",
    "service_token_last4",
)


def _short(value: Any, n: int = 300) -> Any:
    return value[:n] if isinstance(value, str) else value if isinstance(value, bool | int) or value is None else None


@router.get(
    "/{service_id}/koppelstatus",
    summary="Koppelstatus zoals de dienst hem zelf meldt (witte lijst §3.5, met de NL-melding van de dienst; operator)",
)
def koppelstatus(
    service_id: uuid.UUID,
    db: DB,
    settings: SettingsDep,
    _: Operator,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> dict[str, Any]:
    """C1.3-ASM-16: live gelezen bij de dienst (``GET /connector/v1/hub-link`` met een dienst-JWT), nooit opgeslagen.
    De Hub toont de **meegeleverde** NL-melding van ``last_error`` en hardcodeert geen codes. Weigert de dienst de
    Hub (401), dan kijkt de Hub in de openbare ``/readyz`` of de dienst ``koppelstatus_onleesbaar`` meldt (storing)."""
    svc = db.get(Service, service_id)
    if svc is None:
        raise HubError(404, "not_found", "Dienst niet gevonden.")
    now = utcnow()
    out: dict[str, Any] = {"service_id": str(svc.id), "app_id": svc.app_id, "observed_at": iso(now)}
    if svc.status != "active":
        return {**out, "status": "ingetrokken_in_hub", "reden": "dienst_ingetrokken"}
    base, why = service_base_url(db, settings, svc)
    if base is None:
        return {**out, "status": "onbekend", "reden": "dienst_adres_onbekend", "detail": why}
    bearer, _jti = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    ct, rt = settings.service_call_connect_timeout, settings.service_call_read_timeout
    try:
        res = call(base, "GET", "/connector/v1/hub-link", bearer=bearer, connect_timeout=ct, read_timeout=rt)
    except ServiceCallError as exc:
        return {**out, "status": "onbekend", "reden": "dienst_onbereikbaar", "detail": exc.reason}
    if res.status == 200 and isinstance(res.body, dict):
        body = res.body
        link = {k: _short(body.get(k)) for k in HUB_LINK_FIELDS}
        err = body.get("last_error")
        link["last_error"] = (
            {"code": _short(err.get("code"), 64), "melding": _short(err.get("melding"))}
            if isinstance(err, dict)
            else None
        )
        seq = body.get("rotation_sequence")
        link["rotation_sequence"] = seq if type(seq) is int else None
        fp = link.get("keyset_fingerprint")
        return {
            **out,
            "status": "gelezen",
            "koppeling": link,
            "vingerafdruk_gelijk": None if not isinstance(fp, str) else fp == keyring.keyset_fingerprint(),
        }
    if res.status == 401:
        try:
            ready = call(base, "GET", "/readyz", bearer=bearer, connect_timeout=ct, read_timeout=rt)
            onleesbaar = "koppelstatus_onleesbaar" in json.dumps(ready.body, default=str)
        except ServiceCallError:
            onleesbaar = False
        if onleesbaar:
            return {**out, "status": "onleesbaar", "reden": "koppelstatus_onleesbaar"}
        return {**out, "status": "dienst_weigerde", "reden": res.reason or "unauthorized"}
    if res.status == 404:
        return {**out, "status": "onbekend", "reden": "capability_unavailable"}
    return {**out, "status": "onbekend", "reden": f"http_{res.status}"}


@router.post(
    "/{service_id}/rotate",
    status_code=202,
    summary="Rotatie van het service-token aanvragen (admin); de dienst roteert zelf, er komt geen token terug",
)
def request_rotation(service_id: uuid.UUID, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    svc = db.get(Service, service_id)
    if svc is None or svc.status != "active":
        raise HubError(404, "not_found", "Actieve dienst niet gevonden.")
    if svc.rotation_requested_at is None:
        svc.rotation_requested_at, svc.rotation_requested_by = utcnow(), principal.name
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="service.rotation_requested",
        target_type="service",
        target_id=str(svc.id),
    )
    db.flush()
    return idem.save(
        202,
        {
            "service_id": str(svc.id),
            "status": "rotatie_aangevraagd",
            "aangevraagd_op": iso(svc.rotation_requested_at),
            "toelichting": "De dienst krijgt 'Hub-Token-Rotation: required' bij zijn volgende aanroep en roteert dan "
            "zelf binnen 5 minuten. Een token aan de beheerder tonen heeft geen zin: hij kan het niet afleveren.",
        },
    )


@router.post("/{service_id}/revoke", summary="Dienst en al zijn tokens intrekken (admin)")
def revoke(service_id: uuid.UUID, db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    svc = db.get(Service, service_id)
    if svc is None:
        raise HubError(404, "not_found", "Dienst niet gevonden.")
    svc.status, svc.updated_at = "revoked", utcnow()
    svc.rotation_requested_at = svc.rotation_requested_by = None
    _revoke_all(db, svc)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="service.revoked",
        target_type="service",
        target_id=str(svc.id),
    )
    db.flush()
    return idem.save(200, _service_dict(db, settings, svc))


@router.post(
    "/{service_id}/unlink",
    summary="Ontkoppelen (admin): de Hub roept bij de dienst hub-link/unlink aan en trekt daarna de registratie in",
    responses={409: {"description": "adres onbekend"}, 502: {"description": "dienst onbereikbaar of weigerde"}},
)
def unlink(
    service_id: uuid.UUID,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    idem: Idem,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    svc = db.get(Service, service_id)
    if svc is None or svc.status != "active":
        raise HubError(404, "not_found", "Actieve dienst niet gevonden.")
    base, reason = service_base_url(db, settings, svc)
    if base is None:
        raise HubError(
            409,
            "service_address_unknown",
            "Het adres van deze dienst is niet gemeten (NAS-adres D03 + hostpoort uit de inventaris). Vernieuw de "
            "inventaris of trek de registratie alleen in.",
            details={"reason": reason},
        )
    bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    try:
        res = call(
            base,
            "POST",
            "/connector/v1/hub-link/unlink",
            bearer=bearer,
            idempotency_key=str(idem.key),
            body={},
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except ServiceCallError as exc:
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="service.unlink_failed",
            target_type="service",
            target_id=str(svc.id),
            details={"reason": exc.reason},
        )
        db.commit()
        raise HubError(
            502, "service_unreachable", "De dienst is niet bereikbaar; er is niets ontkoppeld.", {"reason": exc.reason}
        ) from None
    # Een herhaalde unlink waarvan de Hub het antwoord niet kreeg, geeft 401 not_linked: dat telt als geslaagd (§3.8).
    if not (200 <= res.status < 300 or (res.status == 401 and res.reason == "not_linked")):
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="service.unlink_failed",
            target_type="service",
            target_id=str(svc.id),
            details={"status": res.status, "code": res.code, "reason": res.reason},
        )
        db.commit()
        raise HubError(
            502,
            "unlink_refused",
            "De dienst weigerde het ontkoppelen; er is niets ingetrokken.",
            {"status": res.status, "code": res.code, "reason": res.reason},
        )
    svc.status, svc.updated_at = "revoked", utcnow()
    svc.rotation_requested_at = svc.rotation_requested_by = None
    _revoke_all(db, svc)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="service.unlinked",
        target_type="service",
        target_id=str(svc.id),
        details={"dienst_antwoord": res.status},
    )
    db.flush()
    return idem.save(200, {**_service_dict(db, settings, svc), "ontkoppeld_bij_dienst": True})


@router.put("/{service_id}/truenas-app", summary="Gemeten TrueNAS-appnaam van deze dienst bevestigen (admin, H14)")
def confirm_truenas_app(
    service_id: uuid.UUID, body: TrueNasAppIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    svc = db.get(Service, service_id)
    if svc is None:
        raise HubError(404, "not_found", "Dienst niet gevonden.")
    st = measured_apps(db, settings)
    if st.get("status") != "ok":
        raise HubError(
            409, "inventory_not_current", "De app-inventaris is niet actueel; vernieuw hem eerst (alleen-lezen)."
        )
    if body.app_name not in app_name_candidates(st.get("data"), svc.app_id):
        raise HubError(
            422,
            "app_name_not_measured",
            "Deze appnaam is niet gemeten met de eigen image van deze dienst (app.query op image-repository).",
            {"kandidaten": app_name_candidates(st.get("data"), svc.app_id)},
        )
    svc.truenas_app_name = body.app_name
    svc.truenas_app_name_confirmed_by, svc.truenas_app_name_confirmed_at = principal.name, utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="service.truenas_app_confirmed",
        target_type="service",
        target_id=str(svc.id),
        details={"app_name": body.app_name},
    )
    db.flush()
    return idem.save(200, _service_dict(db, settings, svc))
