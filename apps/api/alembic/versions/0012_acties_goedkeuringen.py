"""Acties en goedkeuringen (B01-007, contract 1.3 §8, ADR-0030).

- ``action_request``: voorstel voor een getypte actie met de eigen risicoklasse van de Hub, de preview (+ hash), de
  ETag van het doel en de uitkomst. ``id`` = ``Idempotency-Key`` van het voorstel = ``request_id`` bij de executor.
- ``approval``: gebonden goedkeuring (preview_hash, resource_etag, policy_hash, ≤ 15 min, eenmalige nonce).

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-11 09:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def _jsonb() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "action_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("geldig_tot", TS, nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.String(length=80), nullable=False),
        sa.Column("action_id", sa.String(length=96), nullable=False),
        sa.Column("target", _jsonb(), nullable=False),
        sa.Column("parameters", _jsonb(), nullable=False),
        sa.Column("reden", sa.Text(), nullable=False),
        sa.Column("evidence_ids", _jsonb(), nullable=False),
        sa.Column("risk_claim", sa.String(length=16), nullable=True),
        sa.Column("risk_class", sa.String(length=4), nullable=False),
        sa.Column("rule_ids", _jsonb(), nullable=False),
        sa.Column("policy_hash", sa.String(length=80), nullable=False),
        sa.Column("uitvoerder", sa.String(length=64), nullable=True),
        sa.Column("doel_sleutel", sa.String(length=300), nullable=False),
        sa.Column("resource_etag", sa.String(length=300), nullable=False),
        sa.Column("preview", _jsonb(), nullable=False),
        sa.Column("preview_hash", sa.String(length=80), nullable=False),
        sa.Column("blokkades", _jsonb(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("resultaat", _jsonb(), nullable=True),
        sa.Column("gestart_op", TS, nullable=True),
        sa.Column("uitgevoerd_op", TS, nullable=True),
        sa.Column("execution_nonce", sa.Uuid(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_request_status", "action_request", ["status", "aangemaakt_op"])
    op.create_index("ix_action_request_doel", "action_request", ["action_id", "doel_sleutel", "gestart_op"])
    op.create_table(
        "approval",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("preview_hash", sa.String(length=80), nullable=False),
        sa.Column("resource_etag", sa.String(length=300), nullable=False),
        sa.Column("policy_hash", sa.String(length=80), nullable=False),
        sa.Column("risk_class", sa.String(length=4), nullable=False),
        sa.Column("approved_by", sa.String(length=80), nullable=False),
        sa.Column("approved_at", TS, nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("one_time_nonce", sa.Uuid(), nullable=False),
        sa.Column("backup_checkpoint_id", sa.String(length=80), nullable=True),
        sa.Column("action_scope", _jsonb(), nullable=False),
        sa.Column("used_at", TS, nullable=True),
        sa.Column("vervallen_op", TS, nullable=True),
        sa.Column("vervallen_reden", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["action_request.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("one_time_nonce"),
    )
    op.create_index(op.f("ix_approval_request_id"), "approval", ["request_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_approval_request_id"), table_name="approval")
    op.drop_table("approval")
    op.drop_index("ix_action_request_doel", table_name="action_request")
    op.drop_index("ix_action_request_status", table_name="action_request")
    op.drop_table("action_request")
