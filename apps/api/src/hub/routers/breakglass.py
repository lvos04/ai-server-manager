"""Noodlogin (break-glass) in de Hub (contract 1.3 §4.1; Excel B01-006, voorwaarde voor B13-001).

- Eén lokaal noodaccount (rol ``admin``, vlag ``break_glass``): wachtwoord ≥ 20 tekens **plus** TOTP (RFC 6238).
- Inloggen alleen vanaf privé-bereiken op basis van het echte bron-IP (``100.64.0.0/10`` alleen als een beheerder dat
  toestaat); sessie hooguit 60 min (instelbaar 5–240), niet verlengbaar; elke noodlogin → audit + event
  ``auth.break_glass.used`` + rotatieplicht.
- Foute invoer binnen een geldige sessie (eigen wachtwoord, TOTP-code bij bevestigen) is 422, nooit 401: 401 is alleen
  voor authenticatie (contract 1.3 §5).
- Instellen, roteren en bevestigen alleen door een beheerder (met zijn eigen wachtwoord); het zijn geen ``action_id``'s
  en de AI kan ze niet voorstellen. Setup en rotatie geven bewust een nieuw geheim terug (één keer, ``no-store``) en
  zijn daarom, net als wachtwoord wijzigen, uitgezonderd van ``Idempotency-Key`` (contract 1.3 §5).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from hub import audit, breakglass
from hub.deps import DB, Admin, Idem, Principal, SettingsDep, get_vault
from hub.errors import HubError
from hub.events.envelope import emit
from hub.models import User
from hub.routers.auth import USERNAME_PATTERN, client_ip, start_session, user_dict
from hub.security import (
    Role,
    clear_failures,
    failures_in_window,
    hash_password,
    record_failure,
    retry_after_seconds,
    verify_password,
)
from hub.timeutil import iso, utcnow
from hub.vault import Vault, make_ref

router = APIRouter(prefix="/api/v1/auth/break-glass", tags=["aanmelden en gebruikers"])
VaultDep = Annotated[Vault, Depends(get_vault)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetupIn(Strict):
    huidig_wachtwoord: str = Field(min_length=1, max_length=256, description="Wachtwoord van de beheerder zelf")
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=256)
    display_name: str = Field(default="Noodaccount", max_length=128)
    sessieduur_minuten: int = Field(default=60, ge=5, le=240)


class RotateIn(Strict):
    huidig_wachtwoord: str = Field(min_length=1, max_length=256, description="Wachtwoord van de beheerder zelf")
    nieuw_wachtwoord: str = Field(min_length=1, max_length=256)
    sessieduur_minuten: int | None = Field(default=None, ge=5, le=240)


class ConfirmIn(Strict):
    totp: str = Field(min_length=6, max_length=12)


class CgnatIn(Strict):
    toestaan: bool = Field(description="100.64.0.0/10 (CGNAT, ook Tailscale) als privé tellen voor de noodlogin")


class LoginIn(Strict):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    totp: str = Field(min_length=6, max_length=12)


def _reauth(db: Any, settings: Any, principal: Principal, password: str) -> None:
    """Beheerder bevestigt met zijn eigen wachtwoord (een overgenomen sessie alleen is niet genoeg)."""
    key = f"breakglass-admin:{principal.id}"
    if failures_in_window(db, key, settings.login_window_seconds) >= settings.login_max_failures:
        raise HubError(429, "rate_limited", "Te veel mislukte pogingen; probeer het later opnieuw.")
    admin = db.get(User, uuid.UUID(principal.id))
    if admin is None or not verify_password(admin.password_hash, password):
        record_failure(db, key)
        db.commit()
        raise HubError(422, "invalid_credentials", "Je eigen wachtwoord is onjuist.")
    clear_failures(db, key)


def _check_password(password: str, username: str, settings: Any) -> None:
    if len(password) < settings.break_glass_password_min_length:
        raise HubError(
            422,
            "weak_password",
            f"Het noodaccount-wachtwoord moet minstens {settings.break_glass_password_min_length} tekens hebben.",
        )
    if username.lower() in password.lower():
        raise HubError(422, "weak_password", "Het wachtwoord mag de gebruikersnaam niet bevatten.")


def _new_totp(db: Any, vault: Vault, user: User, actor: str) -> dict[str, str]:
    secret = breakglass.generate_secret()
    ref = make_ref("auth", f"break-glass-totp-{user.id}")
    vault.put(db, ref, secret, actor=actor)
    user.totp_secret_ref, user.totp_confirmed_at, user.totp_last_step = ref, None, None
    return {"geheim": secret, "otpauth_uri": breakglass.otpauth_uri(secret, user.username)}


@router.get("", summary="Status van het noodaccount (admin)")
def get_status(db: DB, settings: SettingsDep, _: Admin) -> dict[str, Any]:
    return breakglass.status(db, settings)


@router.post("/setup", status_code=201, summary="Noodaccount aanmaken met TOTP (admin; geheim wordt één keer getoond)")
def setup(body: SetupIn, db: DB, settings: SettingsDep, principal: Admin, vault: VaultDep) -> JSONResponse:
    _reauth(db, settings, principal, body.huidig_wachtwoord)
    if breakglass.account(db) is not None:
        raise HubError(409, "break_glass_exists", "Er is al een noodaccount; gebruik 'roteren'.")
    username = body.username.strip().lower()
    if db.scalars(select(User.id).where(User.username == username)).first() is not None:
        raise HubError(409, "username_taken", "Deze gebruikersnaam bestaat al.")
    _check_password(body.password, username, settings)
    now = utcnow()
    user = User(
        username=username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role=Role.admin.value,
        break_glass=True,
        break_glass_session_minutes=body.sessieduur_minuten,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    totp = _new_totp(db, vault, user, principal.name)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.break_glass.created",
        target_type="user",
        target_id=str(user.id),
        details={"sessieduur_minuten": body.sessieduur_minuten},
    )
    db.commit()
    return JSONResponse(
        {
            "noodaccount": user_dict(user),
            "totp": totp,
            "volgende_stap": "Zet het geheim in een authenticator-app (bewaar het offline) en bevestig met een code.",
        },
        status_code=201,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/rotate", summary="Noodaccount roteren: nieuw wachtwoord en nieuwe TOTP (admin; rotatieplicht)")
def rotate(body: RotateIn, db: DB, settings: SettingsDep, principal: Admin, vault: VaultDep) -> JSONResponse:
    _reauth(db, settings, principal, body.huidig_wachtwoord)
    user = breakglass.account(db)
    if user is None:
        raise HubError(404, "not_found", "Er is nog geen noodaccount.")
    _check_password(body.nieuw_wachtwoord, user.username, settings)
    user.password_hash = hash_password(body.nieuw_wachtwoord)
    if body.sessieduur_minuten is not None:
        user.break_glass_session_minutes = body.sessieduur_minuten
    totp = _new_totp(db, vault, user, principal.name)
    user.updated_at, user.version = utcnow(), user.version + 1
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.break_glass.rotated",
        target_type="user",
        target_id=str(user.id),
    )
    db.commit()
    return JSONResponse(
        {"noodaccount": user_dict(user), "totp": totp, "volgende_stap": "Bevestig de nieuwe TOTP met een code."},
        headers={"Cache-Control": "no-store"},
    )


@router.put(
    "/cgnat",
    summary="100.64.0.0/10 (CGNAT, ook Tailscale) wel of niet als privé tellen voor de noodlogin (admin; audit)",
)
def put_cgnat(body: CgnatIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    """Contract 1.3 §4.1: standaard uit. Alleen een beheerder in de Hub-UI; geen ``action_id``, nooit door de AI."""
    if (replay := idem.replay()) is not None:
        return replay
    before = breakglass.cgnat_allowed(db)
    breakglass.set_cgnat(db, toestaan=body.toestaan, door=principal.name)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.break_glass.cgnat_toegestaan" if body.toestaan else "auth.break_glass.cgnat_uit",
        target_type="hub_setting",
        target_id=breakglass.SETTING_CGNAT,
        details={"was": before, "wordt": body.toestaan},
    )
    db.flush()
    return idem.save(200, breakglass.status(db, settings))


@router.post(
    "/confirm",
    summary="TOTP van het noodaccount bevestigen of herbevestigen (admin); foute code → 422 invalid_totp",
    responses={422: {"description": "invalid_totp: foute code binnen een geldige sessie (nooit 401)"}},
)
def confirm(body: ConfirmIn, db: DB, settings: SettingsDep, principal: Admin, vault: VaultDep) -> dict[str, Any]:
    user = breakglass.account(db)
    if user is None or user.totp_secret_ref is None:
        raise HubError(404, "not_found", "Er is nog geen noodaccount met TOTP.")
    key = f"breakglass-confirm:{principal.id}"
    if failures_in_window(db, key, settings.login_window_seconds) >= settings.login_max_failures:
        raise HubError(429, "rate_limited", "Te veel mislukte pogingen; probeer het later opnieuw.")
    secret = vault.get(db, user.totp_secret_ref)
    now = utcnow()
    step = breakglass.verify_totp(secret, body.totp, now, user.totp_last_step) if secret else None
    if step is None:
        record_failure(db, key)
        db.commit()
        raise HubError(422, "invalid_totp", "De code klopt niet (of is al gebruikt).")
    clear_failures(db, key)
    first = user.totp_confirmed_at is None
    user.totp_last_step = step
    if first:
        user.totp_confirmed_at = now
        user.break_glass_rotation_required = False  # nieuwe TOTP na rotatie bevestigd: rotatieplicht voldaan
    user.break_glass_reconfirmed_at = now
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.break_glass.confirmed" if first else "auth.break_glass.reconfirmed",
        target_type="user",
        target_id=str(user.id),
    )
    db.commit()
    return breakglass.status(db, settings)


@router.post(
    "/login",
    summary="Noodlogin met wachtwoord + TOTP, alleen vanaf privé-adressen (sessie ≤ 60 min, niet verlengbaar)",
    responses={401: {"description": "invalid_credentials"}, 403: {"description": "source_not_private"}},
)
def login(body: LoginIn, request: Request, db: DB, settings: SettingsDep, vault: VaultDep) -> JSONResponse:
    ip = client_ip(request)
    username = body.username.strip().lower()
    # Per (account, bron-IP), nooit alleen per account: anders kan iemand op het LAN het noodaccount blokkeren.
    key = f"breakglass:{username}:{ip}"
    window, max_failures = settings.login_window_seconds, settings.login_max_failures
    if failures_in_window(db, key, window) >= max_failures:
        wait = retry_after_seconds(db, key, window, max_failures) or 1
        raise HubError(
            429,
            "rate_limited",
            "Te veel mislukte pogingen; probeer het later opnieuw.",
            headers={"Retry-After": str(wait)},
        )
    if not breakglass.is_private_source(ip, allow_cgnat=breakglass.cgnat_allowed(db)):
        record_failure(db, key)
        audit.record(
            db, actor_type="user", actor_id=username[:64], action="auth.break_glass.refused", details={"ip": ip}
        )
        db.commit()
        raise HubError(
            403,
            "source_not_private",
            "Noodlogin kan alleen vanaf een privé-netwerkadres (thuisnetwerk), nooit vanaf internet.",
            {"bron_ip": ip},
        )
    user = db.scalars(select(User).where(User.username == username)).first()
    ok_password = verify_password(user.password_hash if user else None, body.password)
    now = utcnow()
    step = None
    if ok_password and breakglass.is_working(user) and user is not None and user.totp_secret_ref is not None:
        secret = vault.get(db, user.totp_secret_ref)
        step = breakglass.verify_totp(secret, body.totp, now, user.totp_last_step) if secret else None
    if user is None or step is None:
        record_failure(db, key)
        audit.record(
            db, actor_type="user", actor_id=username[:64], action="auth.break_glass.failed", details={"ip": ip}
        )
        db.commit()
        raise HubError(401, "invalid_credentials", "Gebruikersnaam, wachtwoord of code onjuist.")
    clear_failures(db, key)
    user.totp_last_step = step
    user.break_glass_last_used_at = now
    user.break_glass_rotation_required = True
    emit(
        db,
        "auth.break_glass.used",
        "user",
        str(user.id),
        {"bron_ip": ip, "op": iso(now), "sessieduur_minuten": breakglass.session_minutes(user, settings)},
        classification="sensitive",
    )
    audit.record(
        db,
        actor_type="user",
        actor_id=user.username,
        action="auth.break_glass.used",
        target_type="user",
        target_id=str(user.id),
        details={"ip": ip},
    )
    minutes = breakglass.session_minutes(user, settings)
    return start_session(request, db, settings, user, ttl_seconds=minutes * 60, break_glass=True)


@router.post("/selftest", summary="Zelftest van de noodlogin zonder in te loggen en zonder mutatie (admin)")
def selftest(request: Request, db: DB, _: Admin) -> dict[str, Any]:
    return breakglass.selftest(db, client_ip(request))
