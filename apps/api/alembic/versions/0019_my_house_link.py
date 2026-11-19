"""Voeg identiteit, tokenverval en appgezondheid toe voor de my_house-koppeling."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("adapter_link", sa.Column("my_house_server_id", sa.Uuid()))
    op.add_column("adapter_link", sa.Column("my_house_client_id", sa.Uuid()))
    op.add_column("adapter_link", sa.Column("my_house_expires_at", sa.DateTime(timezone=True)))
    op.add_column("adapter_link", sa.Column("my_house_status", sa.String(16)))


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE idempotency_record SET response_body = jsonb_set(response_body, '{my_house}', 'null') "
            "WHERE right(scope, length(:test_scope)) = :test_scope "
            "AND response_body->'my_house' <> 'null'::jsonb"
        ).bindparams(test_scope=":POST:/api/v1/adapterkoppelingen/{link_id}/test")
    )
    # Het oude schema kan de Hub-koppeling niet gebruiken. Verwijder haar kluiswaarde mee.
    op.execute(
        sa.text(
            "DELETE FROM vault_secret WHERE ref IN "
            "(SELECT geheim_ref FROM adapter_link WHERE app_id = 'my_house' AND my_house_server_id IS NOT NULL "
            "AND geheim_ref = 'vault://adapters/my_house.' || CAST(id AS text))"
        )
    )
    op.execute(sa.text("DELETE FROM adapter_link WHERE app_id = 'my_house' AND my_house_server_id IS NOT NULL"))
    op.drop_column("adapter_link", "my_house_status")
    op.drop_column("adapter_link", "my_house_expires_at")
    op.drop_column("adapter_link", "my_house_client_id")
    op.drop_column("adapter_link", "my_house_server_id")
