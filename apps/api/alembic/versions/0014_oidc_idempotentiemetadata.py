"""Verwijder laatste vier uit bestaande OIDC-idempotentieantwoorden (KLEIN-107).

Geen wijziging van verzoekhashes (O2) of antwoorden van andere routes.
Revision ID: 0014; Revises: 0013.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
        UPDATE idempotency_record
        SET response_body = response_body #- '{client_secret,laatste4}' #- '{oidc,client_secret,laatste4}'
        WHERE scope LIKE '%:PUT:/api/v1/auth/oidc'
           OR scope LIKE '%:POST:/api/v1/auth/oidc/discover'
           OR scope LIKE '%:POST:/api/v1/auth/oidc/inschakelen'
    """)
    )


def downgrade() -> None:
    # Geheime metadata bewust niet opnieuw toevoegen.
    pass
