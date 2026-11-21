"""Appgeheimen en afgiften voor de afzonderlijke geheime overdracht (contract 1.3 §8.3, M2; S-P2-050e).

HARDE EIS: terug naar 0023 gooit niets weg. Een gevulde tabel blijft bewaard onder ``<naam>_bewaard`` (0023 kent haar
niet en raakt haar niet aan) en komt bij opnieuw 0024 ongewijzigd terug, zoals bij 0022.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

TABELLEN = ("app_geheim", "kluis_afgifte")


def upgrade() -> None:
    bestaand = set(sa.inspect(op.get_bind()).get_table_names())
    if "app_geheim_bewaard" in bestaand:
        op.rename_table("app_geheim_bewaard", "app_geheim")
    else:
        op.create_table(
            "app_geheim",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("instance_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("ref", sa.String(200), nullable=False),
            sa.Column("revision", sa.Uuid(), nullable=False, unique=True),
            sa.Column("nonce", sa.LargeBinary(), nullable=False),
            sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "kluis_afgifte_bewaard" in bestaand:
        op.rename_table("kluis_afgifte_bewaard", "kluis_afgifte")
    else:
        op.create_table(
            "kluis_afgifte",
            sa.Column("request_id", sa.Uuid(), primary_key=True),
            sa.Column("request_sha256", sa.String(71), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("claimed_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    for tabel in TABELLEN:
        if op.get_bind().execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {tabel})")).scalar():  # noqa: S608 - vaste namen
            op.rename_table(tabel, f"{tabel}_bewaard")
        else:
            op.drop_table(tabel)
