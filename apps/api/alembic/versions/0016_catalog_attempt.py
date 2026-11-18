"""Onafhankelijke meetpogingen voor de tijdgrens van de catalogus (contract §4.4, M3)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_attempt",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Behoud het startinterval. Voor een bestaande momentopname ontbreekt bewijs van een tijdige commit.
    op.execute("INSERT INTO catalog_attempt (started_at) SELECT started_at FROM catalog_snapshot")


def downgrade() -> None:
    op.drop_table("catalog_attempt")
