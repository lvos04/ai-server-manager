"""Masker historische previews in actieverzoeken en idempotentieantwoorden.

De Hub-opstart maakt en verifieert de pre-upgradeback-up vóór de migratie.
De oorspronkelijke previewhashes en de daaraan gebonden goedkeuringen blijven behouden.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects.postgresql import JSONB

from hub.actions.preview import idempotency_response, toon_bewaarde_preview

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _maskeer(
    tabel: sa.TableClause,
    kolom: sa.ColumnClause[Any],
    masker: Callable[[Any], Any],
    voorwaarde: sa.ColumnElement[bool],
) -> None:
    db = op.get_bind()
    sleutel = tabel.c.id
    selectie = sa.select(sleutel, kolom).where(voorwaarde).order_by(sleutel).limit(100)
    batch = db.execute(selectie).all()
    while batch:
        for pk, origineel in batch:
            geschoond = masker(origineel)
            if geschoond != origineel:
                db.execute(tabel.update().where(sleutel == pk).values({kolom: geschoond}))
        batch = db.execute(selectie.where(sleutel > batch[-1][0])).all()


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("De maskering van historische actiepreviews vereist een databaseverbinding.")
    verzoek = sa.table("action_request", sa.column("id", sa.Uuid), sa.column("preview", JSONB))
    _maskeer(verzoek, verzoek.c.preview, toon_bewaarde_preview, sa.func.jsonb_typeof(verzoek.c.preview) == "object")

    herhaling = sa.table(
        "idempotency_record",
        sa.column("id", sa.BigInteger),
        sa.column("scope", sa.String),
        sa.column("response_body", JSONB),
    )
    acties = herhaling.c.scope.like("%:POST:/api/v1/actions") | herhaling.c.scope.like("%:POST:/api/v1/actions/%")
    _maskeer(
        herhaling,
        herhaling.c.response_body,
        idempotency_response,
        acties & (sa.func.jsonb_typeof(herhaling.c.response_body["preview"]) == "object"),
    )


def downgrade() -> None:
    # Het oude schema kan de gemaskeerde JSON lezen. Terugzetten herintroduceert geen geheime waarden.
    pass
