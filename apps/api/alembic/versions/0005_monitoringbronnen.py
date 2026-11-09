"""Monitoringbronnen (B09-002): Uptime Kuma en Beszel als alleen-lezen bron

- ``monitor_source``: adres, vault-referentie van het geheim (API-key of wachtwoord), opties (statuspagina's,
  NAS-systeem), handmatige koppelingen monitor → app en de laatste poging met versie en reden.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-09 20:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "monitor_source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("naam", sa.String(length=64), nullable=False),
        sa.Column("basis_url", sa.String(length=512), nullable=False),
        sa.Column("geheim_ref", sa.String(length=200), nullable=True),
        sa.Column("identiteit", sa.String(length=128), nullable=True),
        sa.Column("opties", JSONB, nullable=False),
        sa.Column("koppelingen", JSONB, nullable=False),
        sa.Column("ingeschakeld", sa.Boolean(), nullable=False),
        sa.Column("laatste_poging", TS, nullable=True),
        sa.Column("laatste_ok", TS, nullable=True),
        sa.Column("laatste_status", sa.String(length=16), nullable=True),
        sa.Column("laatste_reden", sa.String(length=64), nullable=True),
        sa.Column("laatste_versie", sa.String(length=64), nullable=True),
        sa.Column("laatste_detail", JSONB, nullable=False),
        sa.Column("aangemaakt_door", sa.String(length=64), nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("bijgewerkt_door", sa.String(length=64), nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("monitor_source")
