"""Gedeelde afhankelijkheden: database, aanmelding (sessie of service-token), rollen, CSRF, idempotency, paginering."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from hub.config import Settings
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import IdempotencyRecord, OidcConfig, Service, ServiceToken, User, WebSession
from hub.oidc import IDEMPOTENCY_ROUTES
from hub.scopes import has_scope
from hub.security import ROLE_RANK, Role, constant_eq, sha256_hex
from hub.timeutil import utcnow
from hub.vault import Vault

SESSION_COOKIE = "hub_session"
CSRF_COOKIE = "hub_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_settings(request: Request) -> Settings:
    return request.app.state.settings  # type: ignore[no-any-return]


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.sessionmaker()
    try:
        yield db
    finally:
        db.close()


def get_keyring(request: Request) -> KeyRing:
    return request.app.state.keyring()  # type: ignore[no-any-return]


def get_vault(request: Request) -> Vault:
    return request.app.state.vault()  # type: ignore[no-any-return]


def get_readable_vault(request: Request) -> Vault | None:
    return request.app.state.readable_vault()  # type: ignore[no-any-return]


DB = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ReadableVault = Annotated[Vault | None, Depends(get_readable_vault)]


@dataclass
class Principal:
    kind: str  # user | service
    id: str
    name: str
    role: Role | None = None
    session_id: uuid.UUID | None = None
    service_app_id: str | None = None
    service_token_id: uuid.UUID | None = None
    auth_bron: str | None = None
    break_glass: bool = False

    @property
    def actor(self) -> str:
        return f"{self.kind}:{self.name}"


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _service_principal(request: Request, db: Session, settings: Settings, token: str) -> Principal:
    row = db.scalars(select(ServiceToken).where(ServiceToken.token_hash == sha256_hex(token))).first()
    now = utcnow()
    if row is None:
        raise HubError(401, "unauthorized", "Ongeldig service-token.", {"reason": "invalid_token"})
    svc = db.get(Service, row.service_id)
    if svc is None:
        raise HubError(401, "unauthorized", "Deze dienst is niet gekoppeld.", {"reason": "not_linked"})
    if svc.status != "active" or row.revoked_at is not None:
        raise HubError(401, "unauthorized", "Deze dienst of het service-token is ingetrokken.", {"reason": "revoked"})
    if row.expires_at is not None and row.expires_at <= now:
        raise HubError(401, "unauthorized", "Dit service-token is verlopen.", {"reason": "token_expired"})
    changed = False
    if row.first_used_at is None and row.grant_id is not None:
        # Eerste gebruik van een token uit een (her)koppeling (contract 1.3 §3.6): nu pas vervallen de oude tokens van
        # deze registratie (ook rotaties die de oude installatie intussen deed), en de termijn van 60 min voor dit token
        # vervalt (het is in gebruik). Een nóg nieuwere, ongebruikte herkoppeling blijft wachten op haar eigen gebruik.
        newer_enrollment = (ServiceToken.created_at > row.created_at) & ServiceToken.grant_id.is_not(None)
        db.execute(
            update(ServiceToken)
            .where(
                ServiceToken.service_id == row.service_id,
                ServiceToken.id != row.id,
                ServiceToken.revoked_at.is_(None),
                ~newer_enrollment,
            )
            .values(revoked_at=now)
        )
        if row.superseded_at is None:
            row.expires_at = None
    if row.first_used_at is None:
        # Eerste gebruik van een (nieuw) token: vervangen oudere tokens vervallen 10 min later (contract 1.3 §3.8).
        row.first_used_at = now
        grace_until = now + timedelta(seconds=settings.service_token_rotation_grace_seconds)
        older = db.scalars(
            select(ServiceToken).where(
                ServiceToken.service_id == row.service_id,
                ServiceToken.id != row.id,
                ServiceToken.superseded_at.is_not(None),
                ServiceToken.created_at < row.created_at,
                ServiceToken.revoked_at.is_(None),
            )
        )
        for t in older:
            if t.expires_at is None or t.expires_at > grace_until:
                t.expires_at = grace_until
        changed = True
    if row.last_used_at is None or now - row.last_used_at > timedelta(minutes=1):
        row.last_used_at = now
        changed = True
    if changed:
        db.commit()
    newest = db.scalars(
        select(ServiceToken)
        .where(ServiceToken.service_id == row.service_id, ServiceToken.revoked_at.is_(None))
        .order_by(ServiceToken.created_at.desc())
        .limit(1)
    ).first()
    # Een nieuwer, nooit gebruikt token uit een rotatie (geen grant) = onderbroken rotatie; een ongebruikt token uit een
    # herkoppeling (§3.6) is dat niet: de oude installatie mag dan gewoon doorwerken tot het nieuwe in gebruik is.
    stale_token = (
        newest is not None and newest.id != row.id and newest.first_used_at is None and newest.grant_id is None
    )
    if svc.rotation_requested_at is not None or stale_token:
        # Aangevraagde rotatie of herstel na een onderbroken rotatie: de middleware zet Hub-Token-Rotation: required.
        request.state.hub_token_rotation = True
    return Principal("service", str(svc.id), svc.app_id, service_app_id=svc.app_id, service_token_id=row.id)


def _session_principal(request: Request, db: Session, settings: Settings) -> Principal | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    sess = db.scalars(select(WebSession).where(WebSession.token_hash == sha256_hex(token))).first()
    now = utcnow()
    if sess is None or sess.revoked_at is not None or sess.expires_at <= now:
        return None
    if sess.auth_bron == "oidc" and not sess.break_glass:
        cfg = db.get(OidcConfig, 1)
        if cfg is None or not cfg.ingeschakeld or sess.oidc_config_versie != cfg.config_versie:
            sess.revoked_at = now
            db.commit()
            return None
    if now - sess.last_seen_at > timedelta(seconds=settings.session_idle_seconds):
        sess.revoked_at = now
        db.commit()
        return None
    user = db.get(User, sess.user_id)
    if user is None or user.disabled:
        return None
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not constant_eq(sha256_hex(sent), sess.csrf_hash):
            raise HubError(403, "csrf_failed", "CSRF-controle mislukt: stuur de header X-CSRF-Token mee.")
    if now - sess.last_seen_at > timedelta(seconds=60):
        sess.last_seen_at = now
        db.commit()
    return Principal(
        "user",
        str(user.id),
        user.username,
        role=Role(user.role),
        session_id=sess.id,
        auth_bron=sess.auth_bron,
        break_glass=sess.break_glass,
    )


def visible_oidc_session(now: datetime, settings: Settings) -> ColumnElement[bool]:
    """Toon OIDC-sessies alleen zolang ze op een verzoek geldig zouden zijn."""
    current = (
        select(OidcConfig.id)
        .where(OidcConfig.id == 1, OidcConfig.ingeschakeld, OidcConfig.config_versie == WebSession.oidc_config_versie)
        .correlate(WebSession)
        .exists()
    )
    enabled_user = (
        select(User.id).where(User.id == WebSession.user_id, User.disabled.is_(False)).correlate(WebSession).exists()
    )
    return or_(
        WebSession.auth_bron != "oidc",
        WebSession.break_glass,
        and_(current, enabled_user, WebSession.last_seen_at >= now - timedelta(seconds=settings.session_idle_seconds)),
    )


def optional_principal(request: Request, db: DB, settings: SettingsDep) -> Principal | None:
    token = _bearer(request)
    if token:
        return _service_principal(request, db, settings, token)
    return _session_principal(request, db, settings)


def require_user(min_role: Role) -> Callable[..., Principal]:
    def dep(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
        if principal is None:
            raise HubError(401, "unauthorized", "Niet aangemeld.")
        if principal.kind != "user" or principal.role is None:
            raise HubError(403, "forbidden", "Alleen voor aangemelde gebruikers.")
        if ROLE_RANK[principal.role] < ROLE_RANK[min_role]:
            raise HubError(403, "forbidden", f"Hiervoor is minimaal de rol '{min_role.value}' nodig.")
        return principal

    return dep


def require_service(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if principal is None or principal.kind != "service":
        raise HubError(
            401, "unauthorized", "Service-token vereist (Authorization: Bearer).", {"reason": "invalid_token"}
        )
    return principal


def require_viewer_or_service(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if principal is None:
        raise HubError(401, "unauthorized", "Niet aangemeld.")
    if principal.kind == "user" and (principal.role is None or ROLE_RANK[principal.role] < ROLE_RANK[Role.viewer]):
        raise HubError(403, "forbidden", "Hiervoor is minimaal de rol 'viewer' nodig.")
    return principal


def require_viewer_or_scope(scope: str | None) -> Callable[..., Principal]:
    """Gebruiker met rol ``viewer``+, of een dienst met precies deze vaste scope (contract 1.3 §4.4). Zonder scope →
    403 ``scope_ontbreekt`` (nooit een intrekking); ``scope=None`` = alleen gebruikers."""

    def dep(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
        if principal is None:
            raise HubError(401, "unauthorized", "Niet aangemeld.")
        if principal.kind == "service":
            if scope is None or not has_scope(principal.service_app_id, scope):
                raise HubError(
                    403,
                    "scope_ontbreekt",
                    "Deze dienst heeft geen leesrecht op deze route (vaste scopes per dienst, contract §4.4).",
                    {"vereiste_scope": scope},
                )
            return principal
        if principal.role is None or ROLE_RANK[principal.role] < ROLE_RANK[Role.viewer]:
            raise HubError(403, "forbidden", "Hiervoor is minimaal de rol 'viewer' nodig.")
        return principal

    return dep


Admin = Annotated[Principal, Depends(require_user(Role.admin))]


def is_local_admin(principal: Principal) -> bool:
    """De aanmeldbron komt uit de levende sessie, nooit uit een header of gebruikersclaim."""
    return principal.role == Role.admin and (principal.auth_bron == "lokaal" or principal.break_glass)


def require_local_admin(principal: Admin) -> Principal:
    if not is_local_admin(principal):
        raise HubError(403, "lokale_beheerder_vereist", "Hiervoor is een lokale beheerderssessie of noodsessie nodig.")
    return principal


LocalAdmin = Annotated[Principal, Depends(require_local_admin)]
Operator = Annotated[Principal, Depends(require_user(Role.operator))]
Viewer = Annotated[Principal, Depends(require_user(Role.viewer))]
AnyUser = Annotated[Principal, Depends(require_user(Role.kind))]
ServiceP = Annotated[Principal, Depends(require_service)]
ViewerOrService = Annotated[Principal, Depends(require_viewer_or_service)]


# ------------------------------------------------------------------ idempotency (contract §5)
class Idempotency:
    """Herhaling met dezelfde ``Idempotency-Key`` → hetzelfde antwoord, geen tweede uitvoering."""

    def __init__(
        self,
        db: Session,
        scope: str,
        key: uuid.UUID,
        request_hash: str,
        response_filter: Callable[[Any], Any] | None = None,
    ) -> None:
        self.db, self.scope, self.key, self.request_hash = db, scope, key, request_hash
        self.response_filter = response_filter

    def replay(self) -> JSONResponse | None:
        rec = self.db.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.scope == self.scope, IdempotencyRecord.key == self.key)
        ).first()
        if rec is None:
            return None
        if rec.request_hash != self.request_hash:
            raise HubError(422, "idempotency_key_reused", "Deze Idempotency-Key is al gebruikt voor een ander verzoek.")
        if self.response_filter is not None:
            clean = self.response_filter(rec.response_body)
            if clean != rec.response_body:
                rec.response_body = clean
                self.db.commit()
        return JSONResponse(rec.response_body, status_code=rec.status_code, headers={"Idempotent-Replay": "true"})

    def save(self, status_code: int, body: Any) -> JSONResponse:
        if self.response_filter is not None:
            body = self.response_filter(body)
        rec = IdempotencyRecord(
            scope=self.scope, key=self.key, request_hash=self.request_hash, status_code=status_code, response_body=body
        )
        self.db.add(rec)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HubError(409, "idempotency_in_progress", "Een verzoek met deze Idempotency-Key loopt al.") from exc
        return JSONResponse(body, status_code=status_code)


async def _idempotency(
    request: Request,
    db: DB,
    principal: Annotated[Principal | None, Depends(optional_principal)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Idempotency:
    if not idempotency_key:
        raise HubError(400, "idempotency_key_required", "Header Idempotency-Key (UUID) is verplicht voor wijzigingen.")
    try:
        key = uuid.UUID(idempotency_key)
    except ValueError as exc:
        raise HubError(400, "idempotency_key_invalid", "Idempotency-Key moet een UUID zijn.") from exc
    body = await request.body()
    try:
        canonical = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":")) if body else ""
    except ValueError:
        canonical = body.decode(errors="replace")
    who = principal.actor if principal else "anoniem"
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    scope = f"{who}:{request.method}:{path}"[:128]
    rhash = hashlib.sha256(f"{request.url.path}\n{canonical}".encode()).hexdigest()
    response_filter = None
    if (request.method, request.url.path) in IDEMPOTENCY_ROUTES:
        from hub.oidc.service import idempotency_response

        response_filter = idempotency_response
    elif path == "/api/v1/actions" or path.startswith("/api/v1/actions/{request_id}/"):
        from hub.actions.preview import idempotency_response as actieantwoord

        response_filter = actieantwoord
    return Idempotency(db, scope, key, rhash, response_filter=response_filter)


Idem = Annotated[Idempotency, Depends(_idempotency)]


# ------------------------------------------------------------------ paginering
def encode_cursor(value: int) -> str:
    return base64.urlsafe_b64encode(str(value).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int | None:
    if not cursor:
        return None
    try:
        pad = "=" * (-len(cursor) % 4)
        return int(base64.urlsafe_b64decode(cursor + pad).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise HubError(400, "invalid_cursor", "Ongeldige cursor.") from exc


Limit = Annotated[int, Query(ge=1, le=200, description="Maximaal 200 per pagina.")]
Cursor = Annotated[str | None, Query(description="Cursor uit `next_cursor` van de vorige pagina.")]
