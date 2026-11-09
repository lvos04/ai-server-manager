"""OIDC-login voor de Hub (B01-006; ADR-0023)

- ``oidc_config`` (één rij), ``oidc_transaction`` (state/nonce/PKCE, eenmalig) en ``oidc_identity`` (issuer + sub →
  gebruiker).
- ``app_user.auth_bron`` en ``web_session.auth_bron`` (``lokaal`` | ``oidc``).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-10 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("app_user", sa.Column("auth_bron", sa.String(length=8), server_default="lokaal", nullable=False))
    op.add_column("web_session", sa.Column("auth_bron", sa.String(length=8), server_default="lokaal", nullable=False))
    op.create_table(
        "oidc_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingeschakeld", sa.Boolean(), nullable=False),
        sa.Column("verplicht", sa.Boolean(), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=True),
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("client_secret_ref", sa.String(length=200), nullable=True),
        sa.Column("redirect_uri", sa.String(length=512), nullable=True),
        sa.Column("scopes", sa.String(length=256), nullable=False),
        sa.Column("groepen_claim", sa.String(length=64), nullable=False),
        sa.Column("rolkoppelingen", JSONB, nullable=False),
        sa.Column("sessie_minuten", sa.Integer(), nullable=False),
        sa.Column("discovery", JSONB, nullable=False),
        sa.Column("discovery_op", TS, nullable=True),
        sa.Column("jwks", JSONB, nullable=False),
        sa.Column("jwks_op", TS, nullable=True),
        sa.Column("laatste_test", JSONB, nullable=False),
        sa.Column("laatste_test_op", TS, nullable=True),
        sa.Column("config_versie", sa.Integer(), nullable=False),
        sa.Column("bijgewerkt_door", sa.String(length=80), nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "oidc_transaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("browser_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=False),
        sa.Column("doel", sa.String(length=8), nullable=False),
        sa.Column("gestart_door", sa.String(length=80), nullable=True),
        sa.Column("terug", sa.String(length=256), nullable=False),
        sa.Column("config_versie", sa.Integer(), nullable=False),
        sa.Column("bron_ip", sa.String(length=64), nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("verloopt_op", TS, nullable=False),
        sa.Column("gebruikt_op", TS, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index(op.f("ix_oidc_transaction_verloopt_op"), "oidc_transaction", ["verloopt_op"], unique=False)
    op.create_table(
        "oidc_identity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("sub", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("gebruikersnaam", sa.String(length=255), nullable=False),
        sa.Column("groepen", JSONB, nullable=False),
        sa.Column("laatste_login_op", TS, nullable=True),
        sa.Column("ingetrokken_op", TS, nullable=True),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "sub", name="uq_oidc_identity_issuer_sub"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_oidc_identity_gebruikersnaam"), "oidc_identity", ["gebruikersnaam"], unique=False)


def downgrade() -> None:
    op.drop_table("oidc_identity")
    op.drop_table("oidc_transaction")
    op.drop_table("oidc_config")
    op.drop_column("web_session", "auth_bron")
    op.drop_column("app_user", "auth_bron")
