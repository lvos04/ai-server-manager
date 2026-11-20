"""Bewaar de reeks slechte gezondheidsmetingen per adapterkoppeling."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("adapter_link", sa.Column("health_failures", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("adapter_link", "health_failures")
