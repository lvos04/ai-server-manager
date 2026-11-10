"""Contract 1.3 in de Hub (ADR-0029): genegeerde ``base_url`` per dienst, beheerinstellingen en de ernst van de bron.

- ``service.base_url_genegeerd``: een ``base_url`` die niet aan §3.3 voldoet, wordt ``null`` met een waarschuwing.
- ``hub_setting``: beheerinstellingen (bv. ``noodlogin.cgnat_toestaan``, §4.1); alleen via de Hub-UI met audit.
- ``incident.ernst_bron``: het Peil-woord uit ``payload.ernst`` (§7), zodat de UI de bronwaarde toont.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-10 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service", sa.Column("base_url_genegeerd", sa.Boolean(), server_default="false", nullable=False))
    op.create_table(
        "hub_setting",
        sa.Column("sleutel", sa.String(length=64), nullable=False),
        sa.Column("waarde", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gewijzigd_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gewijzigd_door", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("sleutel"),
    )
    op.add_column("incident", sa.Column("ernst_bron", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("incident", "ernst_bron")
    op.drop_table("hub_setting")
    op.drop_column("service", "base_url_genegeerd")
