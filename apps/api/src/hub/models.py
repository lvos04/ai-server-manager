"""SQLAlchemy 2-modellen van de Hub (eigen ingebouwde PostgreSQL 16; nooit de database van een andere app)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
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
    # lokaal | oidc (B01-006): een OIDC-account heeft geen bruikbaar wachtwoord en logt alleen via de issuer in.
    auth_bron: Mapped[str] = mapped_column(String(8), default="lokaal", server_default="lokaal")


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
    auth_bron: Mapped[str] = mapped_column(String(8), default="lokaal", server_default="lokaal")


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
    # Hash-ketting (ADR-0022): bij commit verzegeld; een trigger maakt de tabel append-only.
    ketting_nr: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


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
    __table_args__ = (
        UniqueConstraint("source_app", "source_event_id", name="uq_inbox_source_event"),
        Index("ix_event_inbox_onverwerkt", "seq", postgresql_where=text("incident_verwerkt_op IS NULL")),
    )
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
    # Verwerkt door de incidentenmotor (B01-005); NULL = nog te verwerken (geen watermerk: geen gaten bij
    # gelijktijdige commits).
    incident_verwerkt_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class OutboxEvent(Base):
    __tablename__ = "event_outbox"
    __table_args__ = (
        Index("ix_event_outbox_onverwerkt", "seq", postgresql_where=text("incident_verwerkt_op IS NULL")),
    )
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(200))
    timestamp_utc: Mapped[datetime] = mapped_column(TS, default=utcnow)
    trace_id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid.uuid4)
    classification: Mapped[str] = mapped_column(String(16), default="internal")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    incident_verwerkt_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# ------------------------------------------------------------------ centrale appcatalogus (B01-002)
class CatalogApp(Base):
    """Eén app op de NAS. Identiteit = de TrueNAS-app-id (``runtime_id``): die verandert niet bij een herstart van de
    NAS of van de app. De Hub-UUID hoort vast bij die ``runtime_id``; discovery is idempotent en verwijdert nooit."""

    __tablename__ = "catalog_app"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    runtime_id: Mapped[str] = mapped_column(String(128), unique=True)
    naam: Mapped[str] = mapped_column(String(128))
    app_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # herkend profiel of None
    adaptertype: Mapped[str] = mapped_column(String(32))
    soort: Mapped[str] = mapped_column(String(16))  # eigen|bestaand|derde|onbekend
    installatiewijze: Mapped[str] = mapped_column(String(16))  # custom_app|catalog_app|custom_compose|onbekend
    catalogus: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    image_repository: Mapped[str | None] = mapped_column(String(256), nullable=True)
    image_tag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_digest: Mapped[str | None] = mapped_column(String(80), nullable=True)
    images: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    image_historie: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    poorten: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    opslag: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    portals: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    runtime_staat: Mapped[str | None] = mapped_column(String(16), nullable=True)
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service.id", ondelete="SET NULL"), nullable=True, index=True
    )
    appstore: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    bron: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    aanwezig: Mapped[bool] = mapped_column(Boolean, default=True)
    eerst_gezien: Mapped[datetime] = mapped_column(TS, default=utcnow)
    laatst_gezien: Mapped[datetime] = mapped_column(TS, default=utcnow)
    verdwenen_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class HealthObservation(Base):
    """Laatste waarneming per bron (Uptime Kuma-monitor, heartbeat of connector-health van een eigen dienst).
    Veroudering wordt op leestijd beoordeeld (``ttl_seconds``); een verouderde waarneming telt als ``unknown``."""

    __tablename__ = "health_observation"
    __table_args__ = (UniqueConstraint("bron_type", "bron_id", "sleutel", name="uq_health_observation_bron"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bron_type: Mapped[str] = mapped_column(String(16))  # uptime_kuma|heartbeat|connector
    bron_id: Mapped[str] = mapped_column(String(64), index=True)  # bron-uuid (Kuma) of dienst-uuid
    sleutel: Mapped[str] = mapped_column(String(200), default="")  # monitor-sleutel of ""
    naam: Mapped[str] = mapped_column(String(200), default="")
    subject_app_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_app.id", ondelete="SET NULL"), nullable=True, index=True
    )
    koppeling: Mapped[str | None] = mapped_column(String(16), nullable=True)  # automatisch|handmatig
    status: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    ttl_seconds: Mapped[int] = mapped_column(Integer)
    fouten_op_rij: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


# ------------------------------------------------------------------ periodieke taken van de worker
class PeriodicTask(Base):
    """Laatste uitvoering per periodieke taak (meten, tijdreeksonderhoud, alerts, meldingen)."""

    __tablename__ = "periodic_task"
    naam: Mapped[str] = mapped_column(String(48), primary_key=True)
    laatst_gestart: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatst_klaar: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    laatste_reden: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duur_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


# ------------------------------------------------------------------ tijdreeksen (B09-003)
class MetricSeries(Base):
    """Eén genormaliseerde reeks: onderwerp (nas|pool|app|gpu|interface|monitor) × metriek × bron."""

    __tablename__ = "metric_series"
    __table_args__ = (Index("ix_metric_series_onderwerp", "onderwerp_type", "onderwerp_id"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sleutel: Mapped[str] = mapped_column(String(255), unique=True)
    onderwerp_type: Mapped[str] = mapped_column(String(16))
    onderwerp_id: Mapped[str] = mapped_column(String(128))
    metriek: Mapped[str] = mapped_column(String(64), index=True)
    eenheid: Mapped[str] = mapped_column(String(16))
    bron: Mapped[str] = mapped_column(String(96))
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    retentie_ruw_s: Mapped[int] = mapped_column(Integer)
    retentie_5m_s: Mapped[int] = mapped_column(Integer)
    retentie_1u_s: Mapped[int] = mapped_column(Integer)
    laatste_waarde: Mapped[float | None] = mapped_column(Float, nullable=True)
    laatste_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)


class MetricSample(Base):
    __tablename__ = "metric_sample"
    __table_args__ = (PrimaryKeyConstraint("series_id", "ts", name="pk_metric_sample"),)
    series_id: Mapped[int] = mapped_column(ForeignKey("metric_series.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(TS)
    waarde: Mapped[float] = mapped_column(Float)


class MetricRollup(Base):
    """Aggregaat per 5 min (resolutie 300) of per uur (3600): aantal, min, max, som (gemiddelde = som/n), laatste."""

    __tablename__ = "metric_rollup"
    __table_args__ = (PrimaryKeyConstraint("series_id", "resolutie", "bucket", name="pk_metric_rollup"),)
    series_id: Mapped[int] = mapped_column(ForeignKey("metric_series.id", ondelete="CASCADE"))
    resolutie: Mapped[int] = mapped_column(Integer)
    bucket: Mapped[datetime] = mapped_column(TS)
    n: Mapped[int] = mapped_column(Integer)
    min: Mapped[float] = mapped_column(Float)
    max: Mapped[float] = mapped_column(Float)
    som: Mapped[float] = mapped_column(Float)
    laatste: Mapped[float] = mapped_column(Float)


# ------------------------------------------------------------------ alertregels en alerts (B09-003)
class AlertRule(Base):
    __tablename__ = "alert_rule"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    standaard_sleutel: Mapped[str | None] = mapped_column(String(48), unique=True, nullable=True)
    naam: Mapped[str] = mapped_column(String(120))
    metriek: Mapped[str] = mapped_column(String(64))
    onderwerp_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    onderwerp_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bron: Mapped[str | None] = mapped_column(String(96), nullable=True)
    operator: Mapped[str] = mapped_column(String(2))  # gt|ge|lt|le
    drempel: Mapped[float] = mapped_column(Float)
    herstel_drempel: Mapped[float] = mapped_column(Float)
    duur_s: Mapped[int] = mapped_column(Integer)
    herstel_duur_s: Mapped[int] = mapped_column(Integer)
    ernst: Mapped[str] = mapped_column(String(16))  # info|waarschuwing|kritiek
    herhaal_na_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kanalen: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    ingeschakeld: Mapped[bool] = mapped_column(Boolean, default=True)
    gedempt_tot: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    aangemaakt_door: Mapped[str] = mapped_column(String(64))
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    bijgewerkt_door: Mapped[str] = mapped_column(String(64))
    bijgewerkt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class AlertInstance(Base):
    """Toestand van één regel voor één onderwerp (ok → pending → firing → ok), met hysterese en dempen."""

    __tablename__ = "alert_instance"
    __table_args__ = (
        UniqueConstraint("rule_id", "onderwerp_type", "onderwerp_id", name="uq_alert_instance_onderwerp"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alert_rule.id", ondelete="CASCADE"), index=True)
    onderwerp_type: Mapped[str] = mapped_column(String(16))
    onderwerp_id: Mapped[str] = mapped_column(String(128))
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("metric_series.id", ondelete="SET NULL"), nullable=True, index=True
    )
    toestand: Mapped[str] = mapped_column(String(16), default="ok")  # ok|pending|firing
    sinds: Mapped[datetime] = mapped_column(TS, default=utcnow)
    pending_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    firing_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    herstel_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_waarde: Mapped[float | None] = mapped_column(Float, nullable=True)
    laatste_sample_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_eval_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    gegevens_verouderd: Mapped[bool] = mapped_column(Boolean, default=False)
    gedempt_tot: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    gedempt_door: Mapped[str | None] = mapped_column(String(64), nullable=True)
    melding_teller: Mapped[int] = mapped_column(Integer, default=0)
    laatst_gemeld_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatst_opgelost_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)


# ------------------------------------------------------------------ meldingskanalen en meldingen (Gotify)
class NotificationChannel(Base):
    __tablename__ = "notification_channel"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    soort: Mapped[str] = mapped_column(String(16))  # gotify
    naam: Mapped[str] = mapped_column(String(64))
    basis_url: Mapped[str] = mapped_column(String(512))
    token_ref: Mapped[str] = mapped_column(String(200))
    min_ernst: Mapped[str] = mapped_column(String(16))
    stille_uren: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    max_per_venster: Mapped[int] = mapped_column(Integer)
    venster_s: Mapped[int] = mapped_column(Integer)
    ingeschakeld: Mapped[bool] = mapped_column(Boolean, default=True)
    laatste_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    laatste_reden: Mapped[str | None] = mapped_column(String(64), nullable=True)
    laatste_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_versie: Mapped[str | None] = mapped_column(String(64), nullable=True)
    onderdrukt_teller: Mapped[int] = mapped_column(Integer, default=0)
    onderdrukt_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    aangemaakt_door: Mapped[str] = mapped_column(String(64))
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    bijgewerkt_door: Mapped[str] = mapped_column(String(64))
    bijgewerkt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Notification(Base):
    """Melding in de wachtrij of verstuurd. ``dedupe_sleutel`` is uniek per kanaal: één overgang → één melding."""

    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint("kanaal_id", "dedupe_sleutel", name="uq_notification_dedupe"),
        Index("ix_notification_status_volgende", "status", "volgende_poging_op"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kanaal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notification_channel.id", ondelete="CASCADE"))
    dedupe_sleutel: Mapped[str] = mapped_column(String(255))
    bron: Mapped[str] = mapped_column(String(16))  # alert|handmatig|test|samenvatting
    alert_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("alert_instance.id", ondelete="SET NULL"), nullable=True, index=True
    )
    soort: Mapped[str] = mapped_column(String(16), default="bericht")  # actief|hersteld|herhaling|bericht
    ernst: Mapped[str] = mapped_column(String(16))
    titel: Mapped[str] = mapped_column(String(160))
    bericht: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # wachtrij|uitgesteld|verzonden|onderdrukt|mislukt
    reden: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pogingen: Mapped[int] = mapped_column(Integer, default=0)
    volgende_poging_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    aangemaakt_door: Mapped[str] = mapped_column(String(64), default="system")
    verzonden_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    extern_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incident.id", ondelete="SET NULL"), nullable=True, index=True
    )


# ------------------------------------------------------------------ monitoringbronnen (B09-002)
class MonitorSource(Base):
    """Uptime Kuma of Beszel als alleen-lezen bron. Geheimen alleen als vault-referentie (``geheim_ref``)."""

    __tablename__ = "monitor_source"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    soort: Mapped[str] = mapped_column(String(16))  # uptime_kuma|beszel
    naam: Mapped[str] = mapped_column(String(64))
    basis_url: Mapped[str] = mapped_column(String(512))
    geheim_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    identiteit: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Beszel-gebruiker (geen geheim)
    opties: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    koppelingen: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # monitor-sleutel → app-uuid|"geen"
    ingeschakeld: Mapped[bool] = mapped_column(Boolean, default=True)
    laatste_poging: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_ok: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ok|fout
    laatste_reden: Mapped[str | None] = mapped_column(String(64), nullable=True)
    laatste_versie: Mapped[str | None] = mapped_column(String(64), nullable=True)
    laatste_detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    aangemaakt_door: Mapped[str] = mapped_column(String(64))
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    bijgewerkt_door: Mapped[str] = mapped_column(String(64))
    bijgewerkt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


# ------------------------------------------------------------------ incidenten (B01-005, B09-004…006)
class Incident(Base):
    """Eén doorlopend probleem per ``vingerafdruk`` (soort × bron × onderwerp). Hooguit één niet-opgelost incident per
    vingerafdruk (partiële unieke index); herhaling binnen het heropenvenster heropent hetzelfde incident."""

    __tablename__ = "incident"
    __table_args__ = (
        Index(
            "uq_incident_actief",
            "vingerafdruk",
            unique=True,
            postgresql_where=text("status <> 'opgelost'"),
        ),
        Index("ix_incident_status_laatste", "status", "laatste_op"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vingerafdruk: Mapped[str] = mapped_column(String(255), index=True)
    soort: Mapped[str] = mapped_column(String(64), index=True)
    titel: Mapped[str] = mapped_column(String(200))
    ernst: Mapped[str] = mapped_column(String(16))  # info|waarschuwing|kritiek
    status: Mapped[str] = mapped_column(String(16))  # open|erkend|gesnoozed|opgelost
    bron: Mapped[str] = mapped_column(String(64))
    onderwerp_type: Mapped[str] = mapped_column(String(64), default="")
    onderwerp_id: Mapped[str] = mapped_column(String(200), default="")
    onderwerp_naam: Mapped[str] = mapped_column(String(200), default="")
    eerste_op: Mapped[datetime] = mapped_column(TS)
    laatste_op: Mapped[datetime] = mapped_column(TS)
    geopend_op: Mapped[datetime] = mapped_column(TS)
    aantal: Mapped[int] = mapped_column(Integer, default=1)
    heropend: Mapped[int] = mapped_column(Integer, default=0)
    heropeningen: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    erkend_door: Mapped[str | None] = mapped_column(String(80), nullable=True)
    erkend_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    erkend_tot: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    gesnoozed_door: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gesnoozed_tot: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    opgelost_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    opgelost_door: Mapped[str | None] = mapped_column(String(80), nullable=True)
    oplos_reden: Mapped[str | None] = mapped_column(String(300), nullable=True)
    hypothese: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    oorzaak_sleutel: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    runbook_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    veilige_modus: Mapped[bool] = mapped_column(Boolean, default=False)
    veilige_modus_sinds: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    trace_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    correlatie_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    meldt: Mapped[bool] = mapped_column(Boolean, default=True)
    melding_teller: Mapped[int] = mapped_column(Integer, default=0)
    laatst_gemeld_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    escalaties: Mapped[int] = mapped_column(Integer, default=0)
    classificatie: Mapped[str] = mapped_column(String(16), default="internal")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    bijgewerkt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class IncidentEvent(Base):
    """Onderliggende gebeurtenis van een incident (probleem, herstel, info, gecorreleerd, status of notitie).
    ``bron_ref`` is uniek: dezelfde bron-gebeurtenis wordt nooit twee keer verwerkt."""

    __tablename__ = "incident_event"
    __table_args__ = (Index("ix_incident_event_incident_op", "incident_id", "op"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incident.id", ondelete="CASCADE"))
    bron_ref: Mapped[str] = mapped_column(String(200), unique=True)
    soort: Mapped[str] = mapped_column(String(16))  # probleem|herstel|info|gecorreleerd|status|notitie
    op: Mapped[datetime] = mapped_column(TS)
    ontvangen_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    event_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bron: Mapped[str] = mapped_column(String(64), default="")
    samenvatting: Mapped[str] = mapped_column(String(500), default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    classificatie: Mapped[str] = mapped_column(String(16), default="internal")
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(160), nullable=True)


# ------------------------------------------------------------------ log-index (B09-004): alleen geschoond en begrensd
class LogEntry(Base):
    __tablename__ = "log_entry"
    __table_args__ = (Index("ix_log_entry_bron_op", "bron", "op"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    op: Mapped[datetime] = mapped_column(TS, index=True)
    ontvangen_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    bron: Mapped[str] = mapped_column(String(64))  # hub-api|hub-worker|<app_id van een dienst>
    niveau: Mapped[str] = mapped_column(String(8))  # debug|info|warning|error|critical
    logger: Mapped[str] = mapped_column(String(96), default="")
    bericht: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    velden: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


# ------------------------------------------------------------------ OIDC (B01-006, Hub-kant van B13)
class OidcConfig(Base):
    """Eén rij (id=1): issuer, client, scopes, groep→rol-koppelingen en de laatst gemeten discovery/JWKS. Het
    clientgeheim staat alleen als vault-referentie. ``config_versie`` stijgt bij elke wijziging die een nieuwe testlogin
    vereist (issuer, client, redirect, koppelingen)."""

    __tablename__ = "oidc_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    ingeschakeld: Mapped[bool] = mapped_column(Boolean, default=False)
    verplicht: Mapped[bool] = mapped_column(Boolean, default=False)
    issuer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_secret_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scopes: Mapped[str] = mapped_column(String(256), default="openid profile email")
    groepen_claim: Mapped[str] = mapped_column(String(64), default="groups")
    rolkoppelingen: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    sessie_minuten: Mapped[int] = mapped_column(Integer, default=480)
    discovery: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    discovery_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    jwks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    jwks_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    laatste_test: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    laatste_test_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    config_versie: Mapped[int] = mapped_column(Integer, default=1)
    bijgewerkt_door: Mapped[str] = mapped_column(String(80), default="system")
    bijgewerkt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class OidcTransaction(Base):
    """Eén lopende aanmelding (state/nonce/PKCE), eenmalig en hooguit 10 minuten geldig; gebonden aan de browser via
    een apart cookie (alleen de SHA-256 staat hier)."""

    __tablename__ = "oidc_transaction"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    browser_hash: Mapped[str] = mapped_column(String(64))
    nonce_hash: Mapped[str] = mapped_column(String(64))
    code_verifier: Mapped[str] = mapped_column(String(128))
    doel: Mapped[str] = mapped_column(String(8))  # login|test
    gestart_door: Mapped[str | None] = mapped_column(String(80), nullable=True)
    terug: Mapped[str] = mapped_column(String(256), default="/")
    config_versie: Mapped[int] = mapped_column(Integer)
    bron_ip: Mapped[str] = mapped_column(String(64), default="")
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
    verloopt_op: Mapped[datetime] = mapped_column(TS, index=True)
    gebruikt_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)


class OidcIdentity(Base):
    """Koppeling (issuer, sub) → Hub-gebruiker. Nooit automatisch gekoppeld aan een bestaand lokaal account."""

    __tablename__ = "oidc_identity"
    __table_args__ = (UniqueConstraint("issuer", "sub", name="uq_oidc_identity_issuer_sub"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    issuer: Mapped[str] = mapped_column(String(512))
    sub: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), unique=True)
    gebruikersnaam: Mapped[str] = mapped_column(String(255), default="", index=True)
    groepen: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    laatste_login_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    ingetrokken_op: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    aangemaakt_op: Mapped[datetime] = mapped_column(TS, default=utcnow)
