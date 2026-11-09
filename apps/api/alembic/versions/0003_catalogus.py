"""Centrale appcatalogus (B01-002) en gezondheidswaarnemingen (B09-002)

- ``catalog_app``: één rij per TrueNAS-app (identiteit = ``runtime_id``, stabiel over een NAS-herstart), met
  adaptertype, installatiewijze, image/tag/digest (+ geschiedenis), poorten, opslag, portals, koppeling met een
  ingeschreven dienst en de appstore, aanwezigheid en herkomst.
- ``health_observation``: laatste waarneming per bron (Uptime Kuma-monitor, heartbeat, connector-health) met TTL.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "catalog_app",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("runtime_id", sa.String(length=128), nullable=False),
        sa.Column("naam", sa.String(length=128), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=True),
        sa.Column("adaptertype", sa.String(length=32), nullable=False),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("installatiewijze", sa.String(length=16), nullable=False),
        sa.Column("catalogus", JSONB, nullable=False),
        sa.Column("image_repository", sa.String(length=256), nullable=True),
        sa.Column("image_tag", sa.String(length=128), nullable=True),
        sa.Column("image_digest", sa.String(length=80), nullable=True),
        sa.Column("images", JSONB, nullable=False),
        sa.Column("image_historie", JSONB, nullable=False),
        sa.Column("poorten", JSONB, nullable=False),
        sa.Column("opslag", JSONB, nullable=False),
        sa.Column("portals", JSONB, nullable=False),
        sa.Column("runtime_staat", sa.String(length=16), nullable=True),
        sa.Column("service_id", sa.Uuid(), nullable=True),
        sa.Column("appstore", JSONB, nullable=False),
        sa.Column("bron", JSONB, nullable=False),
        sa.Column("aanwezig", sa.Boolean(), nullable=False),
        sa.Column("eerst_gezien", TS, nullable=False),
        sa.Column("laatst_gezien", TS, nullable=False),
        sa.Column("verdwenen_sinds", TS, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["service.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("runtime_id"),
    )
    op.create_index(op.f("ix_catalog_app_app_id"), "catalog_app", ["app_id"], unique=False)
    op.create_index(op.f("ix_catalog_app_service_id"), "catalog_app", ["service_id"], unique=False)

    op.create_table(
        "health_observation",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("bron_type", sa.String(length=16), nullable=False),
        sa.Column("bron_id", sa.String(length=64), nullable=False),
        sa.Column("sleutel", sa.String(length=200), nullable=False),
        sa.Column("naam", sa.String(length=200), nullable=False),
        sa.Column("subject_app_id", sa.Uuid(), nullable=True),
        sa.Column("koppeling", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("observed_at", TS, nullable=True),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("fouten_op_rij", sa.Integer(), nullable=False),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.ForeignKeyConstraint(["subject_app_id"], ["catalog_app.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bron_type", "bron_id", "sleutel", name="uq_health_observation_bron"),
    )
    op.create_index(op.f("ix_health_observation_bron_id"), "health_observation", ["bron_id"], unique=False)
    op.create_index(
        op.f("ix_health_observation_subject_app_id"), "health_observation", ["subject_app_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_health_observation_subject_app_id"), table_name="health_observation")
    op.drop_index(op.f("ix_health_observation_bron_id"), table_name="health_observation")
    op.drop_table("health_observation")
    op.drop_index(op.f("ix_catalog_app_service_id"), table_name="catalog_app")
    op.drop_index(op.f("ix_catalog_app_app_id"), table_name="catalog_app")
    op.drop_table("catalog_app")
