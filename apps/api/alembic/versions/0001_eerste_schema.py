"""Eerste schema: gebruikers, sessies, diensten, besluiten, inventaris, back-ups, events

Revision ID: 0001
Revises: -
Create Date: 2026-11-09 09:24:30.251498
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "audit_event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_event_at"), "audit_event", ["at"], unique=False)
    op.create_table(
        "decision",
        sa.Column("id", sa.String(length=8), nullable=False),
        sa.Column("titel", sa.String(length=128), nullable=False),
        sa.Column("wat_vastleggen", sa.Text(), nullable=False),
        sa.Column("gate", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("waarde", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("schema_versie", sa.Integer(), nullable=False),
        sa.Column("bewijs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reden", sa.Text(), nullable=False),
        sa.Column("waarde_bron", sa.String(length=16), nullable=True),
        sa.Column("laatste_meting", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ingevuld_door", sa.String(length=64), nullable=True),
        sa.Column("ingevuld_op", sa.DateTime(timezone=True), nullable=True),
        sa.Column("getest_door", sa.String(length=64), nullable=True),
        sa.Column("getest_op", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "enrollment_grant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by_service", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("secret_hash"),
    )
    op.create_index(op.f("ix_enrollment_grant_app_id"), "enrollment_grant", ["app_id"], unique=False)
    op.create_table(
        "event_inbox",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("source_app", sa.String(length=64), nullable=False),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=200), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("actor", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classification", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_ref", sa.String(length=512), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_from_service", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("seq"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("source_app", "source_event_id", name="uq_inbox_source_event"),
    )
    op.create_index(op.f("ix_event_inbox_event_type"), "event_inbox", ["event_type"], unique=False)
    op.create_table(
        "event_outbox",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=200), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.Uuid(), nullable=False),
        sa.Column("classification", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("seq"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_table(
        "idempotency_record",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("scope", sa.String(length=128), nullable=False),
        sa.Column("key", sa.Uuid(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )
    op.create_index(op.f("ix_idempotency_record_created_at"), "idempotency_record", ["created_at"], unique=False)
    op.create_table(
        "inventory_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("nas_version", sa.String(length=128), nullable=True),
        sa.Column("capability_source", sa.String(length=32), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("key_scope", sa.String(length=32), nullable=True),
        sa.Column("target_url", sa.String(length=512), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_run_started_at"), "inventory_run", ["started_at"], unique=False)
    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_kind"), "job", ["kind"], unique=False)
    op.create_index(op.f("ix_job_status"), "job", ["status"], unique=False)
    op.create_table(
        "login_attempt",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_login_attempt_attempted_at"), "login_attempt", ["attempted_at"], unique=False)
    op.create_index(op.f("ix_login_attempt_key"), "login_attempt", ["key"], unique=False)
    op.create_table(
        "restore_test",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=True),
        sa.Column("dataset", sa.String(length=512), nullable=True),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("resultaat", sa.String(length=16), nullable=False),
        sa.Column("omgeving", sa.String(length=256), nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=False),
        sa.Column("referentie", sa.String(length=512), nullable=False),
        sa.Column("duur_minuten", sa.Integer(), nullable=True),
        sa.Column("uitgevoerd_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vastgelegd_door", sa.String(length=64), nullable=False),
        sa.Column("vastgelegd_op", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_restore_test_app_id"), "restore_test", ["app_id"], unique=False)
    op.create_table(
        "self_backup",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=256), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("toc_entries", sa.Integer(), nullable=True),
        sa.Column("schema_revision", sa.String(length=64), nullable=True),
        sa.Column("tool_version", sa.String(length=128), nullable=True),
        sa.Column("verification", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_self_backup_started_at"), "self_backup", ["started_at"], unique=False)
    op.create_table(
        "service",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("public_key_jwk", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("enrolled_via", sa.String(length=16), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_id"),
    )
    op.create_table(
        "truenas_connection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("api_key_ref", sa.String(length=200), nullable=True),
        sa.Column("pinned_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("pinned_for_url", sa.String(length=512), nullable=True),
        sa.Column("pinned_by", sa.String(length=64), nullable=True),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_url", sa.String(length=512), nullable=True),
        sa.Column("last_test_status", sa.String(length=16), nullable=True),
        sa.Column("last_test_reason", sa.String(length=64), nullable=True),
        sa.Column("last_test_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("api_key_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("api_key_set_by", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vault_secret",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ref", sa.String(length=200), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("last4", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ref"),
    )
    op.create_table(
        "worker_heartbeat",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("beat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "inventory_snapshot",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("method", sa.String(length=96), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["inventory_run.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_snapshot_kind_observed", "inventory_snapshot", ["kind", "observed_at"], unique=False)
    op.create_index(op.f("ix_inventory_snapshot_run_id"), "inventory_snapshot", ["run_id"], unique=False)
    op.create_table(
        "service_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("last4", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["service.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_service_token_service_id"), "service_token", ["service_id"], unique=False)
    op.create_table(
        "web_session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_web_session_user_id"), "web_session", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_web_session_user_id"), table_name="web_session")
    op.drop_table("web_session")
    op.drop_index(op.f("ix_service_token_service_id"), table_name="service_token")
    op.drop_table("service_token")
    op.drop_index(op.f("ix_inventory_snapshot_run_id"), table_name="inventory_snapshot")
    op.drop_index("ix_inventory_snapshot_kind_observed", table_name="inventory_snapshot")
    op.drop_table("inventory_snapshot")
    op.drop_table("worker_heartbeat")
    op.drop_table("vault_secret")
    op.drop_table("truenas_connection")
    op.drop_table("service")
    op.drop_index(op.f("ix_self_backup_started_at"), table_name="self_backup")
    op.drop_table("self_backup")
    op.drop_index(op.f("ix_restore_test_app_id"), table_name="restore_test")
    op.drop_table("restore_test")
    op.drop_index(op.f("ix_login_attempt_key"), table_name="login_attempt")
    op.drop_index(op.f("ix_login_attempt_attempted_at"), table_name="login_attempt")
    op.drop_table("login_attempt")
    op.drop_index(op.f("ix_job_status"), table_name="job")
    op.drop_index(op.f("ix_job_kind"), table_name="job")
    op.drop_table("job")
    op.drop_index(op.f("ix_inventory_run_started_at"), table_name="inventory_run")
    op.drop_table("inventory_run")
    op.drop_index(op.f("ix_idempotency_record_created_at"), table_name="idempotency_record")
    op.drop_table("idempotency_record")
    op.drop_table("event_outbox")
    op.drop_index(op.f("ix_event_inbox_event_type"), table_name="event_inbox")
    op.drop_table("event_inbox")
    op.drop_index(op.f("ix_enrollment_grant_app_id"), table_name="enrollment_grant")
    op.drop_table("enrollment_grant")
    op.drop_table("decision")
    op.drop_index(op.f("ix_audit_event_at"), table_name="audit_event")
    op.drop_table("audit_event")
    op.drop_table("app_user")
