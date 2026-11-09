"""Partiële index op onverzegelde auditrijen (ADR-0022): het verzegelen bij commit zoekt ``hash IS NULL``.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-10 01:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_event_onverzegeld", "audit_event", ["id"], unique=False, postgresql_where=sa.text("hash IS NULL")
    )


def downgrade() -> None:
    op.drop_index("ix_audit_event_onverzegeld", table_name="audit_event")
