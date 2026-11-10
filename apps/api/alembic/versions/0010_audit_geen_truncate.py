"""Auditspoor: ook ``TRUNCATE`` weigeren (ADR-0022, QA-review P1).

De rij-trigger ``audit_event_append_only`` (0006) weigert ``UPDATE`` en ``DELETE``, maar een ``TRUNCATE`` vuurt geen
rij-triggers af en kon het hele auditspoor in één opdracht leegmaken. Een statement-trigger ``BEFORE TRUNCATE`` weigert
dat nu ook. (Een database-eigenaar kan triggers nog uitschakelen; dat verraden de hash-ketting en het anker in
``/appdata/audit``.)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-10 03:00:00
"""

from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

TRUNCATE_FN = """
CREATE OR REPLACE FUNCTION audit_event_geen_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_event is append-only: leegmaken (TRUNCATE) is niet toegestaan'
    USING ERRCODE = 'insufficient_privilege';
END $$;
"""


def upgrade() -> None:
    op.execute(TRUNCATE_FN)
    op.execute(
        "CREATE TRIGGER audit_event_geen_truncate BEFORE TRUNCATE ON audit_event "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_event_geen_truncate()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_event_geen_truncate ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit_event_geen_truncate()")
