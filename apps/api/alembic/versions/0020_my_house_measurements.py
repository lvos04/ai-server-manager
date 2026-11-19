"""Scheid woningmetingen van herhaalbevestigingen en bewaar de bronmeettijden."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def _clear_legacy_measurements() -> None:
    # Ook bevestigingen waarvan de koppeling in 0019 al is verwijderd.
    op.execute(
        sa.text(
            "UPDATE idempotency_record SET response_body = jsonb_set(response_body, '{my_house}', 'null') "
            "WHERE right(scope, length(:test_scope)) = :test_scope "
            "AND response_body->'my_house' <> 'null'::jsonb"
        ).bindparams(test_scope=":POST:/api/v1/adapterkoppelingen/{link_id}/test")
    )


def upgrade() -> None:
    _clear_legacy_measurements()
    op.drop_column("adapter_link", "my_house_status")
    op.add_column("adapter_link", sa.Column("my_house_checks", JSONB()))
    op.create_table(
        "adapter_house_snapshot",
        sa.Column("receipt_scope", sa.String(128), primary_key=True),
        sa.Column("receipt_key", sa.Uuid(), primary_key=True),
        sa.Column("link_id", sa.Uuid(), sa.ForeignKey("adapter_link.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measurement", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ("receipt_scope", "receipt_key"),
            ("idempotency_record.scope", "idempotency_record.key"),
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_adapter_house_snapshot_link_id", "adapter_house_snapshot", ["link_id"])


def downgrade() -> None:
    _clear_legacy_measurements()
    op.drop_table("adapter_house_snapshot")
    op.drop_column("adapter_link", "my_house_checks")
    op.add_column("adapter_link", sa.Column("my_house_status", sa.String(16)))
