"""Contract 1.2: toegestane enroll-herhaling, rotatie na eerste gebruik, TrueNAS-appnaam en noodaccount

- ``enrollment_grant.used_with_key_thumbprint``: herhaling alleen met dezelfde identiteitssleutel (§3.6).
- ``service_token.grant_id``/``first_used_at``/``superseded_at``: oud token vervalt 10 min na het eerste gebruik van
  het nieuwe, hooguit 24 uur na de rotatie (§3.8).
- ``service.rotation_requested_*``: rotatie aangevraagd door een beheerder (202, ``Hub-Token-Rotation``).
- ``service.truenas_app_name*``: werkelijke TrueNAS-appnaam naast de vaste ``app_id`` (H14).
- ``app_user.break_glass``/``totp_*``/``break_glass_*`` en ``web_session.break_glass``: noodlogin (§4.1).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09 15:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("enrollment_grant", sa.Column("used_with_key_thumbprint", sa.String(length=64), nullable=True))

    op.add_column("service_token", sa.Column("grant_id", sa.Uuid(), nullable=True))
    op.add_column("service_token", sa.Column("first_used_at", TS, nullable=True))
    op.add_column("service_token", sa.Column("superseded_at", TS, nullable=True))
    op.create_index(op.f("ix_service_token_grant_id"), "service_token", ["grant_id"], unique=False)
    op.create_foreign_key(
        "service_token_grant_id_fkey", "service_token", "enrollment_grant", ["grant_id"], ["id"], ondelete="SET NULL"
    )
    # Bestaande tokens die al gebruikt zijn: het eerste gebruik is niet exact bekend, het laatste gebruik wel (ondergrens).
    op.execute("UPDATE service_token SET first_used_at = last_used_at WHERE last_used_at IS NOT NULL")

    op.add_column("service", sa.Column("rotation_requested_at", TS, nullable=True))
    op.add_column("service", sa.Column("rotation_requested_by", sa.String(length=64), nullable=True))
    op.add_column("service", sa.Column("truenas_app_name", sa.String(length=64), nullable=True))
    op.add_column("service", sa.Column("truenas_app_name_confirmed_by", sa.String(length=64), nullable=True))
    op.add_column("service", sa.Column("truenas_app_name_confirmed_at", TS, nullable=True))

    op.add_column("app_user", sa.Column("break_glass", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("app_user", sa.Column("totp_secret_ref", sa.String(length=200), nullable=True))
    op.add_column("app_user", sa.Column("totp_confirmed_at", TS, nullable=True))
    op.add_column("app_user", sa.Column("totp_last_step", sa.BigInteger(), nullable=True))
    op.add_column("app_user", sa.Column("break_glass_session_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "app_user", sa.Column("break_glass_rotation_required", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column("app_user", sa.Column("break_glass_reconfirmed_at", TS, nullable=True))
    op.add_column("app_user", sa.Column("break_glass_last_used_at", TS, nullable=True))

    op.add_column("web_session", sa.Column("break_glass", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("web_session", "break_glass")
    for col in (
        "break_glass_last_used_at",
        "break_glass_reconfirmed_at",
        "break_glass_rotation_required",
        "break_glass_session_minutes",
        "totp_last_step",
        "totp_confirmed_at",
        "totp_secret_ref",
        "break_glass",
    ):
        op.drop_column("app_user", col)
    for col in (
        "truenas_app_name_confirmed_at",
        "truenas_app_name_confirmed_by",
        "truenas_app_name",
        "rotation_requested_by",
        "rotation_requested_at",
    ):
        op.drop_column("service", col)
    op.drop_constraint("service_token_grant_id_fkey", "service_token", type_="foreignkey")
    op.drop_index(op.f("ix_service_token_grant_id"), table_name="service_token")
    for col in ("superseded_at", "first_used_at", "grant_id"):
        op.drop_column("service_token", col)
    op.drop_column("enrollment_grant", "used_with_key_thumbprint")
