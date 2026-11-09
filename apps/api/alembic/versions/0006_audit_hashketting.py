"""Auditspoor append-only met hash-ketting (ADR-0022)

- ``audit_event``: ``ketting_nr`` (doorlopend, gatloos), ``prev_hash`` en ``hash`` (SHA-256 over de vorige hash en de
  canonieke JSON van de rij, versie 1). Bestaande rijen worden hier in id-volgorde verzegeld.
- Trigger ``audit_event_append_only``: ``DELETE`` altijd geweigerd; ``UPDATE`` alleen om een nog niet verzegelde rij
  één keer te verzegelen (alle andere kolommen gelijk).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-09 22:00:00
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

GENESIS = "0" * 64

TRIGGER_FN = """
CREATE OR REPLACE FUNCTION audit_event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'audit_event is append-only: verwijderen is niet toegestaan'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF OLD.hash IS NOT NULL
     OR NEW.hash IS NULL OR NEW.prev_hash IS NULL OR NEW.ketting_nr IS NULL
     OR NEW.id IS DISTINCT FROM OLD.id
     OR NEW.at IS DISTINCT FROM OLD.at
     OR NEW.actor_type IS DISTINCT FROM OLD.actor_type
     OR NEW.actor_id IS DISTINCT FROM OLD.actor_id
     OR NEW.action IS DISTINCT FROM OLD.action
     OR NEW.target_type IS DISTINCT FROM OLD.target_type
     OR NEW.target_id IS DISTINCT FROM OLD.target_id
     OR NEW.details IS DISTINCT FROM OLD.details
     OR NEW.trace_id IS DISTINCT FROM OLD.trace_id THEN
    RAISE EXCEPTION 'audit_event is append-only: alleen eenmalig verzegelen is toegestaan'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;
"""


def _canonical_v1(nr: int, row: Any) -> bytes:
    """Bevroren kopie van ``hub.audit.canonical_v1`` (versie 1); nooit wijzigen."""
    at: datetime = row.at
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    data = {
        "v": 1,
        "nr": nr,
        "op": at.astimezone(UTC).isoformat(timespec="microseconds"),
        "actor_type": row.actor_type,
        "actor_id": row.actor_id,
        "actie": row.action,
        "doel_type": row.target_type,
        "doel_id": row.target_id,
        "details": row.details,
        "trace_id": row.trace_id,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def upgrade() -> None:
    op.add_column("audit_event", sa.Column("ketting_nr", sa.BigInteger(), nullable=True))
    op.add_column("audit_event", sa.Column("prev_hash", sa.String(length=64), nullable=True))
    op.add_column("audit_event", sa.Column("hash", sa.String(length=64), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, at, actor_type, actor_id, action, target_type, target_id, details, trace_id "
            "FROM audit_event ORDER BY id"
        )
    ).fetchall()
    prev = GENESIS
    for nr, row in enumerate(rows, start=1):
        h = hashlib.sha256(prev.encode("ascii") + b"\n" + _canonical_v1(nr, row)).hexdigest()
        conn.execute(
            sa.text("UPDATE audit_event SET ketting_nr = :nr, prev_hash = :p, hash = :h WHERE id = :id"),
            {"nr": nr, "p": prev, "h": h, "id": row.id},
        )
        prev = h
    op.create_unique_constraint("audit_event_ketting_nr_key", "audit_event", ["ketting_nr"])
    op.execute(TRIGGER_FN)
    op.execute(
        "CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON audit_event "
        "FOR EACH ROW EXECUTE FUNCTION audit_event_append_only()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_event_append_only ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit_event_append_only()")
    op.drop_constraint("audit_event_ketting_nr_key", "audit_event", type_="unique")
    op.drop_column("audit_event", "hash")
    op.drop_column("audit_event", "prev_hash")
    op.drop_column("audit_event", "ketting_nr")
