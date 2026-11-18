"""Begrensde catalogusmomentopname en leeslimiet per dienst (M3)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("binding", sa.String(64), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("catalog", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_catalog_snapshot_singleton"),
    )
    op.create_table(
        "catalog_read_window",
        sa.Column("service_id", sa.Uuid(), sa.ForeignKey("service.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("requests", postgresql.ARRAY(sa.DateTime(timezone=True)), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("catalog_read_window")
    op.drop_table("catalog_snapshot")
