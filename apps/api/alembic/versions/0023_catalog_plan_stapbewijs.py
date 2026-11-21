"""Stapbewijs voor plannen uit de oorspronkelijke 0022 (R-HARDE-EIS-1; S-P2-050d).

De oorspronkelijke 0022 kende ``stap_sha256`` niet. Een database daarop zag geen open migratie en kon haar plannen niet
meer lezen. Deze migratie voegt de kolom toe als zij ontbreekt (nullable: een oude rij heeft geen betrouwbaar
stapbewijs), zet oude open plannen zonder stapbewijs op opnieuw voorvertonen en houdt van de controles alleen de
openbare velden over (R-VEILIG-1). Registraties blijven ongewijzigd. De terugweg laat alles staan: 0022 kent de kolom
ook en bewaart een gevulde tabel.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

CONTROLE_KEYS = ("id", "soort", "beschrijving_nl")


def upgrade() -> None:
    op.execute("ALTER TABLE catalog_plan ADD COLUMN IF NOT EXISTS stap_sha256 varchar(71)")
    op.execute("ALTER TABLE catalog_plan ALTER COLUMN stap_sha256 DROP NOT NULL")
    op.execute(
        "UPDATE catalog_plan SET status = 'geblokkeerd', reden = 'opnieuw_voorvertonen', updated_at = now() "
        "WHERE stap_sha256 IS NULL AND status IN ('klaar_voor_voorstel', 'voorgesteld')"
    )
    bind = op.get_bind()
    tabel = sa.table("catalog_plan", sa.column("id", sa.Uuid()), sa.column("controles_na_installatie", sa.JSON()))
    for plan_id, controles in bind.execute(sa.select(tabel.c.id, tabel.c.controles_na_installatie)).all():
        if not isinstance(controles, list):
            continue
        schoon = [{k: c.get(k) for k in CONTROLE_KEYS} if isinstance(c, dict) else c for c in controles]
        if schoon != controles:
            bind.execute(tabel.update().where(tabel.c.id == plan_id).values(controles_na_installatie=schoon))


def downgrade() -> None:
    # Bewust niets: de kolom hoort ook bij 0022 en niets mag hier verloren gaan.
    pass
