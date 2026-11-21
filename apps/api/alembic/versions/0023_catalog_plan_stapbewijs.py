"""Stapbewijs voor plannen uit de oorspronkelijke 0022 (R-HARDE-EIS-1; S-P2-050d).

De oorspronkelijke 0022 kende ``stap_sha256`` niet. Een database daarop zag geen open migratie en kon haar plannen niet
meer lezen. Deze migratie voegt de kolom toe als zij ontbreekt (nullable: een oude rij heeft geen betrouwbaar
stapbewijs), zet oude open plannen zonder stapbewijs op opnieuw voorvertonen en bouwt de controles in bewaarde plannen
en bewaarde planantwoorden (idempotentie) opnieuw op volgens het openbare schema (R-VEILIG-1). Registraties en de
overige velden blijven ongewijzigd. De terugweg laat alles staan: 0022 kent de kolom
ook en bewaart een gevulde tabel.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from hub.catalog.plannen import idempotency_response, openbare_controles

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


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
            continue  # geen controlelijst: blijft ongewijzigd staan; lezen toont daaruit niets (openbare_controles)
        schoon = openbare_controles(controles)
        if schoon != controles:
            bind.execute(tabel.update().where(tabel.c.id == plan_id).values(controles_na_installatie=schoon))
    cache = sa.table(
        "idempotency_record",
        sa.column("id", sa.BigInteger),
        sa.column("scope", sa.String),
        sa.column("response_body", JSONB),
    )
    planroutes = cache.c.scope.like("%:/api/v1/catalog/plans/%") & cache.c.response_body.has_key(
        "controles_na_installatie"
    )
    for rij_id, antwoord in bind.execute(sa.select(cache.c.id, cache.c.response_body).where(planroutes)).all():
        schoon = idempotency_response(antwoord)
        if schoon != antwoord:
            bind.execute(cache.update().where(cache.c.id == rij_id).values(response_body=schoon))


def downgrade() -> None:
    # Bewust niets: de kolom hoort ook bij 0022 en niets mag hier verloren gaan.
    pass
