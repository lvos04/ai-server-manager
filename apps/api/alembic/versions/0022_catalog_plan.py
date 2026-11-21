"""Eigen plannen van de Hub bij de planner (contract 1.3 §8.2; S-P2-050d).

HARDE EIS: terug naar 0021 gooit geen plannen of installatieregistraties weg. Een gevulde tabel blijft bewaard als
``catalog_plan_bewaard`` (0021 kent haar niet en raakt haar niet aan) en komt bij opnieuw 0022 ongewijzigd terug.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


BEWAARD = "catalog_plan_bewaard"


def upgrade() -> None:
    if BEWAARD in sa.inspect(op.get_bind()).get_table_names():
        op.rename_table(BEWAARD, "catalog_plan")
        return
    op.create_table(
        "catalog_plan",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("soort", sa.String(16), nullable=False),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("app_name", sa.String(40), nullable=False),
        sa.Column("instance_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("planner_service_id", sa.Uuid(), nullable=False),
        sa.Column("binding", JSONB(), nullable=False),
        sa.Column("plan_etag", sa.String(122), nullable=False),
        sa.Column("step_id", sa.String(64)),
        sa.Column("stap_sha256", sa.String(71), nullable=False),
        sa.Column("controles_na_installatie", JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reden", sa.String(64)),
        sa.Column("request_id", sa.Uuid(), unique=True),
        sa.Column("registratie", JSONB()),
        sa.Column("melding", JSONB()),
        sa.Column("created_by", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM catalog_plan)")).scalar():
        op.rename_table("catalog_plan", BEWAARD)
    else:
        op.drop_table("catalog_plan")
