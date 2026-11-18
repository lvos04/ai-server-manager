"""Bind uitsluitend OIDC-sessies aan hun configuratie (KLEIN-107).

Bestaande OIDC-sessies blijven NULL en worden geweigerd; lokale/noodsessies veranderen niet.
Revision ID: 0013; Revises: 0012.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("web_session", sa.Column("oidc_config_versie", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("web_session", "oidc_config_versie")
