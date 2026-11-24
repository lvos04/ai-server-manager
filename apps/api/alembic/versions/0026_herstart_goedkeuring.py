"""Laat openstaande herstarts van vóór het nieuwe beleid opnieuw beoordelen."""

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE action_request SET status = 'wacht_op_goedkeuring', bijgewerkt_op = CURRENT_TIMESTAMP "
        "WHERE action_id = 'app.restart' AND status = 'klaar'"
    )


def downgrade() -> None:
    # Ook bij terugmigratie mag een wachtend voorstel niet vanzelf uitvoerbaar worden.
    pass
