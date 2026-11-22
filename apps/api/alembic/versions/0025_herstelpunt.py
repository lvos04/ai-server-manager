"""Herstelpunten per app voor de pre-update-gate (B12-006; S-P2-090).

HARDE EIS: terug naar 0024 gooit niets weg. Een gevulde tabel blijft bewaard onder ``herstelpunt_bewaard`` (0024 kent
haar niet en raakt haar niet aan) en komt bij opnieuw 0025 ongewijzigd terug, zoals bij 0022 en 0024.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "herstelpunt_bewaard" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.rename_table("herstelpunt_bewaard", "herstelpunt")
        return
    op.create_table(
        "herstelpunt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("app", sa.String(128), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(80), nullable=False),
        sa.Column("gemaakt_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("db_export", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("reden", sa.String(64), nullable=True),
        sa.Column("vastgelegd_op", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("checkpoint_id", "app", name="uq_herstelpunt_checkpoint_app"),
    )


def downgrade() -> None:
    # Eerst het exclusieve slot in deze transactie: een gelijktijdige schrijver commit vóór de leegtecontrole of wacht
    # tot na de terugweg (R-HARDE-EIS-1); zonder slot kon een net bevestigde rij met de tabel verdwijnen.
    op.execute("LOCK TABLE herstelpunt IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM herstelpunt)")).scalar():
        op.rename_table("herstelpunt", "herstelpunt_bewaard")
    else:
        op.drop_table("herstelpunt")
