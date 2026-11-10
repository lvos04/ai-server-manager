"""Setup (setupcode → eerste admin), login/logout, sessies, wachtwoord, gebruikers, JWKS en dienst-JWT (contract §4)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from hub import audit
from hub.deps import (
    CSRF_COOKIE,
    DB,
    SESSION_COOKIE,
    Admin,
    AnyUser,
    Idem,
    Principal,
    SettingsDep,
    Viewer,
    get_keyring,
)
from hub.errors import HubError
from hub.firststart import mark_setup_completed, setup_pending, verify_setup_code
from hub.keys import KeyRing
from hub.models import Service, User, WebSession
from hub.security import (
    Role,
    clear_failures,
    failures_in_window,
    hash_password,
    needs_rehash,
    record_failure,
    sha256_hex,
    verify_password,
)
from hub.timeutil import iso, utcnow

router = APIRouter(prefix="/api/v1", tags=["aanmelden en gebruikers"])

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,63}$"
# Vaste sleutel voor pg_advisory_xact_lock rond het aanmaken van de eerste beheerder (setupcode is eenmalig).
SETUP_LOCK_KEY = 0x48554253_45545550  # "HUBSETUP"
# Platformdiensten die gebruikerscontext-JWT's mogen ontvangen (naast ingeschreven diensten).
KNOWN_AUDIENCES = {
    "home-control-hub",
    "appstore-en-fork",
    "jelly-leon-platform",
    "zoeken-en-persoonlijke-ai",
    "jelly-leon",
    "ai-server-manager-executor",
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetupAdminIn(Strict):
    setup_code: str = Field(min_length=4, max_length=32)
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=256)
    display_name: str = Field(default="", max_length=128)


class LoginIn(Strict):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordIn(Strict):
    huidig_wachtwoord: str = Field(min_length=1, max_length=256)
    nieuw_wachtwoord: str = Field(min_length=1, max_length=256)


class UserIn(Strict):
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=256)
    role: Role
    display_name: str = Field(default="", max_length=128)


class UserPatch(Strict):
    role: Role | None = None
    disabled: bool | None = None
    display_name: str | None = Field(default=None, max_length=128)


class ServiceJwtIn(Strict):
    audience: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "onbekend"


def _rate_check(db: Any, key: str, settings: Any) -> None:
    n = failures_in_window(db, key, settings.login_window_seconds)
    if n >= settings.login_max_failures:
        raise HubError(
            429,
            "rate_limited",
            "Te veel mislukte pogingen; probeer het later opnieuw.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )


def _check_password_policy(password: str, min_len: int, username: str) -> None:
    if len(password) < min_len:
        raise HubError(422, "weak_password", f"Wachtwoord moet minstens {min_len} tekens hebben.")
    if password.lower() == username.lower():
        raise HubError(422, "weak_password", "Wachtwoord mag niet gelijk zijn aan de gebruikersnaam.")


def user_dict(u: User) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "username": u.username,
        "display_name": u.display_name,
        "role": u.role,
        "disabled": u.disabled,
        "break_glass": u.break_glass,
        "auth_bron": u.auth_bron,
        "created_at": iso(u.created_at),
        "updated_at": iso(u.updated_at),
        "version": u.version,
    }


def create_session(
    request: Request,
    db: Any,
    settings: Any,
    user: User,
    *,
    ttl_seconds: int | None = None,
    break_glass: bool = False,
    auth_bron: str = "lokaal",
    action: str | None = None,
    details: dict[str, Any] | None = None,
) -> tuple[str, str, WebSession, int]:
    """Nieuwe websessie (alleen hashes in de database) + audit; commit. Geeft (token, csrf, sessie, ttl)."""
    from hub.security import new_token

    token, csrf = new_token("ses"), new_token("csrf", 24)
    now = utcnow()
    ttl = ttl_seconds or settings.session_ttl_seconds
    sess = WebSession(
        token_hash=sha256_hex(token),
        csrf_hash=sha256_hex(csrf),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl),
        last_seen_at=now,
        user_agent=request.headers.get("user-agent", "")[:256],
        client_ip=client_ip(request),
        break_glass=break_glass,
        auth_bron=auth_bron,
    )
    db.add(sess)
    audit.record(
        db,
        actor_type="user",
        actor_id=user.username,
        action=action or ("auth.break_glass_login" if break_glass else "auth.login"),
        target_type="session",
        target_id=str(sess.id),
        details=details,
        trace_id=str(getattr(request.state, "trace_id", "")),
    )
    db.commit()
    return token, csrf, sess, ttl


def set_session_cookies(resp: Response, request: Request, settings: Any, token: str, csrf: str, ttl: int) -> None:
    secure = settings.cookie_secure == "true" or (settings.cookie_secure == "auto" and request.url.scheme == "https")
    resp.set_cookie(SESSION_COOKIE, token, max_age=ttl, httponly=True, secure=secure, samesite="strict", path="/")
    resp.set_cookie(CSRF_COOKIE, csrf, max_age=ttl, httponly=False, secure=secure, samesite="strict", path="/")


def start_session(
    request: Request, db: Any, settings: Any, user: User, *, ttl_seconds: int | None = None, break_glass: bool = False
) -> JSONResponse:
    token, csrf, sess, ttl = create_session(
        request, db, settings, user, ttl_seconds=ttl_seconds, break_glass=break_glass
    )
    body: dict[str, Any] = {"user": user_dict(user), "csrf_token": csrf, "sessie_verloopt_op": iso(sess.expires_at)}
    if break_glass:
        body["noodlogin"] = True
    resp = JSONResponse(body, headers={"Cache-Control": "no-store"})
    set_session_cookies(resp, request, settings, token, csrf, ttl)
    return resp


def _has_admin(db: Any) -> bool:
    return db.scalars(select(User.id).where(User.role == "admin")).first() is not None


def _heal_setup_marker(db: Any, settings: Any) -> bool:
    """Er is al een beheerder maar de markering ontbreekt (bv. stroomuitval tussen commit en markering): herstel die,
    zodat ``hub init`` nooit meer een (onbruikbare) setupcode in de log zet. Geeft ``True`` als er een beheerder is."""
    if not _has_admin(db):
        return False
    if setup_pending(settings.secrets_dir):
        mark_setup_completed(settings.secrets_dir)
    return True


@router.get("/setup/status", summary="Is de eerste setup nog nodig?")
def setup_status(db: DB, settings: SettingsDep) -> dict[str, Any]:
    has_admin = _heal_setup_marker(db, settings)
    pending = setup_pending(settings.secrets_dir) and not has_admin
    return {
        "setup_vereist": pending,
        "uitleg": "De eenmalige setupcode staat in de app-log (TrueNAS → Apps → ai-server-manager → Logs)."
        if pending
        else "Setup is afgerond.",
    }


@router.post("/setup/admin", summary="Eerste beheerder aanmaken met de setupcode uit de app-log")
def setup_admin(body: SetupAdminIn, request: Request, db: DB, settings: SettingsDep) -> JSONResponse:
    key = f"setup:{client_ip(request)}"
    _rate_check(db, key, settings)
    # Eenmalig, ook bij gelijktijdige verzoeken met dezelfde code: één transactie tegelijk (advisory lock tot commit of
    # rollback), en pas ná het verkrijgen van de lock opnieuw kijken of er al een beheerder is.
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": SETUP_LOCK_KEY})
    if _heal_setup_marker(db, settings) or not setup_pending(settings.secrets_dir):
        raise HubError(409, "setup_already_done", "Setup is al afgerond.")
    if not verify_setup_code(settings.secrets_dir, body.setup_code):
        record_failure(db, key)
        db.commit()
        raise HubError(
            401, "invalid_setup_code", "Setupcode onjuist of verlopen. Herstart de app voor een nieuwe code."
        )
    _check_password_policy(body.password, settings.password_min_length, body.username)
    user = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role=Role.admin.value,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=body.username,
        action="setup.admin_created",
        target_type="user",
        target_id=str(user.id),
    )
    clear_failures(db, key)
    db.commit()
    mark_setup_completed(settings.secrets_dir)
    return start_session(request, db, settings, user)


@router.post("/auth/login", summary="Aanmelden (argon2id, rate-limit)")
def login(body: LoginIn, request: Request, db: DB, settings: SettingsDep) -> JSONResponse:
    username = body.username.strip().lower()
    key = f"login:{username}:{client_ip(request)}"
    _rate_check(db, key, settings)
    from hub.oidc.service import effective_required

    if effective_required(db):
        # Geen wachtwoordcontrole (geen orakel); het noodaccount logt via /auth/break-glass/login in.
        raise HubError(
            403,
            "oidc_verplicht",
            "Inloggen gaat via SSO (Authentik). Lokaal inloggen staat uit; bij nood: de noodlogin op het thuisnetwerk.",
        )
    user = db.scalars(select(User).where(User.username == username)).first()
    ok = verify_password(user.password_hash if user else None, body.password)
    # Het noodaccount logt alleen in via /auth/break-glass/login (met TOTP, alleen privé-adressen).
    if not ok or user is None or user.disabled or user.break_glass:
        record_failure(db, key)
        audit.record(
            db,
            actor_type="user",
            actor_id=username[:64],
            action="auth.login_failed",
            details={"ip": client_ip(request)},
        )
        db.commit()
        raise HubError(401, "invalid_credentials", "Gebruikersnaam of wachtwoord onjuist.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    clear_failures(db, key)
    return start_session(request, db, settings, user)


@router.post("/auth/logout", summary="Afmelden (sessie intrekken)")
def logout(request: Request, db: DB, principal: AnyUser) -> Response:
    sess = db.get(WebSession, principal.session_id)
    if sess is not None and sess.revoked_at is None:
        sess.revoked_at = utcnow()
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="auth.logout",
            target_type="session",
            target_id=str(sess.id),
        )
        db.commit()
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    resp.delete_cookie(CSRF_COOKIE, path="/")
    return resp


@router.get("/auth/me", summary="Huidige gebruiker")
def me(db: DB, principal: AnyUser) -> dict[str, Any]:
    user = db.get(User, uuid.UUID(principal.id))
    assert user is not None
    return {"user": user_dict(user), "sessie_id": str(principal.session_id)}


@router.get("/auth/sessions", summary="Eigen actieve sessies")
def my_sessions(db: DB, principal: AnyUser) -> dict[str, Any]:
    rows = db.scalars(
        select(WebSession)
        .where(
            WebSession.user_id == uuid.UUID(principal.id),
            WebSession.revoked_at.is_(None),
            WebSession.expires_at > utcnow(),
        )
        .order_by(WebSession.created_at.desc())
    )
    return {
        "items": [
            {
                "id": str(s.id),
                "aangemaakt": iso(s.created_at),
                "laatst_gezien": iso(s.last_seen_at),
                "verloopt": iso(s.expires_at),
                "user_agent": s.user_agent,
                "ip": s.client_ip,
                "huidige": s.id == principal.session_id,
            }
            for s in rows
        ]
    }


@router.post("/auth/sessions/{session_id}/revoke", summary="Sessie intrekken (eigen; admin: iedere)")
def revoke_session(session_id: uuid.UUID, db: DB, principal: AnyUser, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    sess = db.get(WebSession, session_id)
    if sess is None or (str(sess.user_id) != principal.id and principal.role != Role.admin):
        raise HubError(404, "not_found", "Sessie niet gevonden.")
    if sess.revoked_at is None:
        sess.revoked_at = utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.session_revoked",
        target_type="session",
        target_id=str(session_id),
    )
    return idem.save(200, {"id": str(session_id), "ingetrokken_op": iso(sess.revoked_at)})


@router.post("/auth/password", summary="Eigen wachtwoord wijzigen (trekt andere sessies in)")
def change_password(body: PasswordIn, db: DB, settings: SettingsDep, principal: AnyUser) -> dict[str, Any]:
    user = db.get(User, uuid.UUID(principal.id))
    assert user is not None
    if user.break_glass:
        raise HubError(409, "use_break_glass_rotate", "Het noodaccount wijzig je via 'noodaccount roteren'.")
    if user.auth_bron == "oidc":
        raise HubError(409, "sso_account", "Dit is een SSO-account: het wachtwoord beheer je in Authentik.")
    # Zelfde rate-limit als bij inloggen: met een overgenomen sessie mag het huidige wachtwoord niet te raden zijn.
    key = f"password:{user.id}"
    _rate_check(db, key, settings)
    if not verify_password(user.password_hash, body.huidig_wachtwoord):
        record_failure(db, key)
        db.commit()
        raise HubError(401, "invalid_credentials", "Huidig wachtwoord onjuist.")
    clear_failures(db, key)
    _check_password_policy(body.nieuw_wachtwoord, settings.password_min_length, user.username)
    user.password_hash = hash_password(body.nieuw_wachtwoord)
    user.updated_at, user.version = utcnow(), user.version + 1
    db.execute(
        update(WebSession)
        .where(WebSession.user_id == user.id, WebSession.id != principal.session_id, WebSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.password_changed",
        target_type="user",
        target_id=str(user.id),
    )
    db.commit()
    return {"status": "gewijzigd", "andere_sessies_ingetrokken": True}


@router.get("/auth/jwks", summary="Publieke sleutels (JWKS) voor dienst-JWT's")
def jwks(keyring: Annotated[KeyRing, Depends(get_keyring)]) -> JSONResponse:
    return JSONResponse(keyring.jwks(), headers={"Cache-Control": "public, max-age=300"})


@router.get(
    "/auth/key-rotations",
    summary="Ondertekende sleutelrotaties (zonder authenticatie; contract 1.2 §4.5). Nog niet gebouwd: lege lijst",
)
def key_rotations(after: Annotated[int, Query(ge=0, le=2**31)] = 0) -> dict[str, Any]:
    # De Hub roteert zijn sleutels nog niet; rotatie = opnieuw koppelen. Dus nooit een statement.
    return {"items": []}


@router.get("/auth/keyset", summary="Publieke sleutelset (jwks + policy-sleutel) met vingerafdruk, om te kopiëren")
def keyset(_: Viewer, keyring: Annotated[KeyRing, Depends(get_keyring)]) -> dict[str, Any]:
    return {
        "jwks": keyring.jwks(),
        "policy_public_key": keyring.policy_public_jwk(),
        "keyset_fingerprint": keyring.keyset_fingerprint(),
        "toelichting": "Publieke sleutels (geen geheim). Bestaande apps die een ondertekend ExecutionRequest "
        "verifiëren, plakken deze set in hun eigen beheer-UI en vergelijken de vingerafdruk (contract §2.3).",
    }


@router.post("/auth/service-jwt", summary="Kortlevende JWT met gebruikerscontext voor een dienst (exp ≤ 120 s)")
def service_jwt(
    body: ServiceJwtIn,
    db: DB,
    settings: SettingsDep,
    principal: AnyUser,
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> JSONResponse:
    enrolled = db.scalars(select(Service).where(Service.app_id == body.audience, Service.status == "active")).first()
    if enrolled is None and body.audience not in KNOWN_AUDIENCES:
        raise HubError(404, "unknown_audience", "Onbekende dienst; alleen ingeschreven platformdiensten.")
    assert principal.role is not None
    token, expires = keyring.issue_user_jwt(
        subject=principal.id, audience=body.audience, roles=[principal.role.value], ttl_seconds=settings.jwt_ttl_seconds
    )
    return JSONResponse(
        {"token": token, "token_type": "Bearer", "verloopt_op": iso(expires)}, headers={"Cache-Control": "no-store"}
    )


# ------------------------------------------------------------------ gebruikersbeheer (admin)
@router.get("/users", summary="Gebruikers (admin)")
def list_users(db: DB, _: Admin) -> dict[str, Any]:
    return {"items": [user_dict(u) for u in db.scalars(select(User).order_by(User.username))]}


@router.post("/users", status_code=201, summary="Gebruiker aanmaken (admin)")
def create_user(body: UserIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    if db.scalars(select(User.id).where(User.username == body.username)).first() is not None:
        raise HubError(409, "username_taken", "Deze gebruikersnaam bestaat al.")
    _check_password_policy(body.password, settings.password_min_length, body.username)
    user = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=hash_password(body.password),
        role=body.role.value,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        # Gelijktijdig dezelfde naam aangemaakt (unieke index): eerlijk 409 in plaats van een 500 (review N-06).
        db.rollback()
        raise HubError(409, "username_taken", "Deze gebruikersnaam bestaat al.") from exc
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="user.created",
        target_type="user",
        target_id=str(user.id),
        details={"role": body.role.value},
    )
    return idem.save(201, user_dict(user))


@router.patch("/users/{user_id}", summary="Rol/status wijzigen (admin)")
def patch_user(user_id: uuid.UUID, body: UserPatch, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    user = db.get(User, user_id)
    if user is None:
        raise HubError(404, "not_found", "Gebruiker niet gevonden.")
    if user.break_glass and body.role is not None and body.role != Role.admin:
        raise HubError(409, "break_glass_stays_admin", "Het noodaccount houdt de rol 'admin'.")
    demote = (body.role is not None and body.role != Role.admin) or body.disabled is True
    if user.role == Role.admin.value and demote:
        admins = db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.disabled.is_(False)))
        if (admins or 0) <= 1:
            raise HubError(
                409, "last_admin", "De laatste actieve beheerder kan niet worden gedegradeerd of uitgeschakeld."
            )
    if body.role is not None:
        user.role = body.role.value
    if body.disabled is not None:
        user.disabled = body.disabled
    if body.display_name is not None:
        user.display_name = body.display_name
    if demote or body.role is not None:
        db.execute(
            update(WebSession)
            .where(WebSession.user_id == user.id, WebSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
    user.updated_at, user.version = utcnow(), user.version + 1
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="user.updated",
        target_type="user",
        target_id=str(user.id),
        details=body.model_dump(exclude_none=True, mode="json"),
    )
    return idem.save(200, user_dict(user))


def principal_dict(p: Principal) -> dict[str, Any]:
    return {"kind": p.kind, "name": p.name, "role": p.role.value if p.role else None}
