"""Afzonderlijk poolleesrecht per MediaGuard-koppeling, standaard zonder toekenning."""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("adapter_link", sa.Column("pool_token_hash", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_adapter_link_pool_token_hash", "adapter_link", ["pool_token_hash"])


def downgrade() -> None:
    op.drop_constraint("uq_adapter_link_pool_token_hash", "adapter_link", type_="unique")
    op.drop_column("adapter_link", "pool_token_hash")
