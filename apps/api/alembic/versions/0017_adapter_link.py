"""Afzonderlijke koppelingen en contactmetingen voor bestaande apps (S-P3-020)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adapter_link",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("catalog_app_id", sa.Uuid(), sa.ForeignKey("catalog_app.id"), nullable=False, unique=True),
        sa.Column("basis_url", sa.String(512), nullable=False),
        sa.Column("peer_addresses", JSONB(), nullable=False),
        sa.Column("geheim_ref", sa.String(200), nullable=False, unique=True),
        sa.Column("laatste4", sa.String(8), nullable=False),
        sa.Column("ingevoerd_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("laatste_status", sa.String(16)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("max_age_s", sa.Integer()),
        sa.Column("laatste_fout", sa.String(64)),
        sa.Column("version", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM vault_secret WHERE ref LIKE 'vault://adapters/%' AND ref IN (SELECT geheim_ref FROM adapter_link)"
    )
    op.drop_table("adapter_link")
