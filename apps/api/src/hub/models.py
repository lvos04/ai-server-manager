"""SQLAlchemy 2-modellen van de Hub (eigen ingebouwde PostgreSQL 16; nooit de database van een andere app)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSONB, list[Any]: JSONB}


TS = DateTime(timezone=True)


# ------------------------------------------------------------------ gebruikers, sessies, login
class User(Base):
    __tablename__ = "app_user"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Noodaccount (contract 1.2 §4.1): alleen via /api/v1/auth/break-glass/*; TOTP-geheim versleuteld in de vault.
    break_glass: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    totp_secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # tegen hergebruik van een code
    break_glass_session_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    break_glass_rotation_required: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    break_glass_reconfirmed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    break_glass_last_used_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class WebSession(Base):
    __tablename__ = "web_session"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TS)
    last_seen_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    client_ip: Mapped[str] = mapped_column(String(64), default="")
    break_glass: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class LoginAttempt(Base):
    __tablename__ = "login_attempt"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    key: Mapped[str] = mapped_column(String(160), index=True)
    attempted_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)


# ------------------------------------------------------------------ diensten en enrollment
class Service(Base):
    __tablename__ = "service"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    app_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|revoked
    version: Mapped[str] = mapped_column(String(64), default="")
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    public_key_jwk: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    enrolled_via: Mapped[str] = mapped_column(String(16))  # token|koppelcode
    enrolled_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    # Rotatie aangevraagd door een beheerder (contract 1.2 §3.8): Hub-Token-Rotation tot de dienst geroteerd heeft.
    rotation_requested_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    rotation_requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Werkelijke TrueNAS-appnaam (H14): app_id is vast (§2); de appnaam is gemeten (app.query) en door een beheerder
    # bevestigd. Leeg = nog niet bevestigd; dan geldt de app_id als appnaam.
    truenas_app_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    truenas_app_name_confirmed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    truenas_app_name_confirmed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class EnrollmentGrant(Base):
    __tablename__ = "enrollment_grant"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(16))  # token|koppelcode
    purpose: Mapped[str] = mapped_column(String(16), default="service")  # service|executor (P2)
    app_id: Mapped[str] = mapped_column(String(64), index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TS)
    used_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    used_by_service: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # RFC 7638-thumbprint van public_key_jwk bij het eerste gebruik: toegestane herhaling alleen met dezelfde sleutel.
    used_with_key_thumbprint: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ServiceToken(Base):
    __tablename__ = "service_token"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    last4: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("enrollment_grant.id", ondelete="SET NULL"), nullable=True, index=True
    )
    first_used_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    # Gezet bij een rotatie: vervangen token; vervalt 10 min na het eerste gebruik van het nieuwe (max. 24 uur).
    superseded_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class VaultSecret(Base):
    __tablename__ = "vault_secret"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ref: Mapped[str] = mapped_column(String(200), unique=True)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    last4: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_by: Mapped[str] = mapped_column(String(64))


# ------------------------------------------------------------------ idempotency en audit
class IdempotencyRecord(Base):
    __tablename__ = "idempotency_record"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    scope: Mapped[str] = mapped_column(String(128))
    key: Mapped[uuid.UUID] = mapped_column(Uuid)
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)


class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)
    actor_type: Mapped[str] = mapped_column(String(16))  # user|service|system
    actor_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(96))
    target_type: Mapped[str] = mapped_column(String(64), default="")
    target_id: Mapped[str] = mapped_column(String(128), default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    trace_id: Mapped[str] = mapped_column(String(36), default="")


# ------------------------------------------------------------------ onboarding-besluiten D01–D18
class Decision(Base):
    __tablename__ = "decision"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # D01..D18
    titel: Mapped[str] = mapped_column(String(128))
    wat_vastleggen: Mapped[str] = mapped_column(Text)
    gate: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(16))  # Open|Ingevuld|Getest|Geblokkeerd|N.v.t.
    waarde: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    schema_versie: Mapped[int] = mapped_column(Integer, default=1)
    bewijs: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    reden: Mapped[str] = mapped_column(Text, default="")  # bij Geblokkeerd / N.v.t.
    waarde_bron: Mapped[str | None] = mapped_column(String(16), nullable=True)  # gebruiker|meting|vast
    laatste_meting: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ingevuld_door: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingevuld_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    getest_door: Mapped[str | None] = mapped_column(String(64), nullable=True)
    getest_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


# ------------------------------------------------------------------ TrueNAS-koppeling (read-only) en inventaris
class TrueNASConnection(Base):
    __tablename__ = "truenas_connection"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    api_key_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pinned_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pinned_for_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pinned_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pinned_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    last_test_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    last_test_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_test_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_test_detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    api_key_set_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    api_key_set_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class InventoryRun(Base):
    __tablename__ = "inventory_run"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # ok|partial|unknown
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nas_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capability_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    key_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_url: Mapped[str] = mapped_column(String(512), default="")
    trigger: Mapped[str] = mapped_column(String(32), default="manual")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshot"
    __table_args__ = (Index("ix_inventory_snapshot_kind_observed", "kind", "observed_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("inventory_run.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))  # ok|unknown
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str | None] = mapped_column(String(96), nullable=True)
    data: Mapped[Any] = mapped_column(JSONB, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


# ------------------------------------------------------------------ jobs en worker
class Job(Base):
    __tablename__ = "job"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), index=True)  # inventory_refresh|self_backup
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)  # queued|running|done|failed
    requested_by: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeat"
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    beat_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


# ------------------------------------------------------------------ back-up en herstel (B12)
class SelfBackup(Base):
    __tablename__ = "self_backup"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    trigger: Mapped[str] = mapped_column(String(32))  # schedule|manual|pre-upgrade
    status: Mapped[str] = mapped_column(String(16))  # bezig|geslaagd|mislukt
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    file_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    toc_entries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class RestoreTest(Base):
    """Expliciet bewijsrecord van een echte hersteltest (handmatig; de Hub voert in P0 zelf geen restore uit)."""

    __tablename__ = "restore_test"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    app_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    dataset: Mapped[str | None] = mapped_column(String(512), nullable=True)
    soort: Mapped[str] = mapped_column(String(16))  # foto|database|dataset|config
    resultaat: Mapped[str] = mapped_column(String(16))  # geslaagd|mislukt
    omgeving: Mapped[str] = mapped_column(String(256))
    omschrijving: Mapped[str] = mapped_column(Text)
    referentie: Mapped[str] = mapped_column(String(512), default="")
    duur_minuten: Mapped[int | None] = mapped_column(Integer, nullable=True)  # gemeten hersteltijd (RTO)
    uitgevoerd_op: Mapped[datetime] = mapped_column(TS)
    vastgelegd_door: Mapped[str] = mapped_column(String(64))
    vastgelegd_op: Mapped[datetime] = mapped_column(TS, default=utcnow)


# ------------------------------------------------------------------ events (contract §7)
class InboxEvent(Base):
    __tablename__ = "event_inbox"
    __table_args__ = (UniqueConstraint("source_app", "source_event_id", name="uq_inbox_source_event"),)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    source_app: Mapped[str] = mapped_column(String(64))
    source_event_id: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(200))
    timestamp_utc: Mapped[datetime] = mapped_column(TS)
    trace_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor: Mapped[dict[str, Any]] = mapped_column(JSONB)
    classification: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    payload_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    received_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    received_from_service: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class OutboxEvent(Base):
    __tablename__ = "event_outbox"
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(200))
    timestamp_utc: Mapped[datetime] = mapped_column(TS, default=utcnow)
    trace_id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid.uuid4)
    classification: Mapped[str] = mapped_column(String(16), default="internal")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
