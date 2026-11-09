"""Gedeelde afhankelijkheden: database, aanmelding (sessie of service-token), rollen, CSRF, idempotency, paginering."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Any

from fastapi import Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import IdempotencyRecord, Service, ServiceToken, User, WebSession
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


DB = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@dataclass
class Principal:
    kind: str  # user | service
    id: str
    name: str
    role: Role | None = None
    session_id: uuid.UUID | None = None
    service_app_id: str | None = None
    service_token_id: uuid.UUID | None = None

    @property
    def actor(self) -> str:
        return f"{self.kind}:{self.name}"


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _service_principal(db: Session, token: str) -> Principal:
    row = db.scalars(select(ServiceToken).where(ServiceToken.token_hash == sha256_hex(token))).first()
    now = utcnow()
    if row is None or row.revoked_at is not None or (row.expires_at is not None and row.expires_at <= now):
        raise HubError(401, "unauthorized", "Service-token ongeldig, verlopen of ingetrokken.")
    svc = db.get(Service, row.service_id)
    if svc is None or svc.status != "active":
        raise HubError(401, "unauthorized", "Deze dienst is ingetrokken.")
    if row.last_used_at is None or now - row.last_used_at > timedelta(minutes=1):
        row.last_used_at = now
        db.commit()
    return Principal("service", str(svc.id), svc.app_id, service_app_id=svc.app_id, service_token_id=row.id)


def _session_principal(request: Request, db: Session, settings: Settings) -> Principal | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    sess = db.scalars(select(WebSession).where(WebSession.token_hash == sha256_hex(token))).first()
    now = utcnow()
    if sess is None or sess.revoked_at is not None or sess.expires_at <= now:
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
    return Principal("user", str(user.id), user.username, role=Role(user.role), session_id=sess.id)


def optional_principal(request: Request, db: DB, settings: SettingsDep) -> Principal | None:
    token = _bearer(request)
    if token:
        return _service_principal(db, token)
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
        raise HubError(401, "unauthorized", "Service-token vereist (Authorization: Bearer).")
    return principal


def require_viewer_or_service(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if principal is None:
        raise HubError(401, "unauthorized", "Niet aangemeld.")
    if principal.kind == "user" and (principal.role is None or ROLE_RANK[principal.role] < ROLE_RANK[Role.viewer]):
        raise HubError(403, "forbidden", "Hiervoor is minimaal de rol 'viewer' nodig.")
    return principal


Admin = Annotated[Principal, Depends(require_user(Role.admin))]
Operator = Annotated[Principal, Depends(require_user(Role.operator))]
Viewer = Annotated[Principal, Depends(require_user(Role.viewer))]
AnyUser = Annotated[Principal, Depends(require_user(Role.kind))]
ServiceP = Annotated[Principal, Depends(require_service)]
ViewerOrService = Annotated[Principal, Depends(require_viewer_or_service)]


# ------------------------------------------------------------------ idempotency (contract §5)
class Idempotency:
    """Herhaling met dezelfde ``Idempotency-Key`` → hetzelfde antwoord, geen tweede uitvoering."""

    def __init__(self, db: Session, scope: str, key: uuid.UUID, request_hash: str) -> None:
        self.db, self.scope, self.key, self.request_hash = db, scope, key, request_hash

    def replay(self) -> JSONResponse | None:
        rec = self.db.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.scope == self.scope, IdempotencyRecord.key == self.key)
        ).first()
        if rec is None:
            return None
        if rec.request_hash != self.request_hash:
            raise HubError(422, "idempotency_key_reused", "Deze Idempotency-Key is al gebruikt voor een ander verzoek.")
        return JSONResponse(rec.response_body, status_code=rec.status_code, headers={"Idempotent-Replay": "true"})

    def save(self, status_code: int, body: Any) -> JSONResponse:
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
    return Idempotency(db, scope, key, rhash)


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
