"""Incidenten-inbox en log-index (B01-005, B09-004…006; ADR-0022)

- ``incident`` (hooguit één niet-opgelost incident per vingerafdruk), ``incident_event`` (unieke ``bron_ref``),
  ``log_entry`` (alleen geschoonde, begrensde regels).
- ``event_inbox``/``event_outbox``: ``incident_verwerkt_op``; bestaande events gelden als verwerkt (incidenten
  beginnen bij deze versie, geen golf oude incidenten).
- ``notification.incident_id`` voor meldingen die bij een incident horen.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-09 23:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "incident",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vingerafdruk", sa.String(length=255), nullable=False),
        sa.Column("soort", sa.String(length=64), nullable=False),
        sa.Column("titel", sa.String(length=200), nullable=False),
        sa.Column("ernst", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("bron", sa.String(length=64), nullable=False),
        sa.Column("onderwerp_type", sa.String(length=64), nullable=False),
        sa.Column("onderwerp_id", sa.String(length=200), nullable=False),
        sa.Column("onderwerp_naam", sa.String(length=200), nullable=False),
        sa.Column("eerste_op", TS, nullable=False),
        sa.Column("laatste_op", TS, nullable=False),
        sa.Column("geopend_op", TS, nullable=False),
        sa.Column("aantal", sa.Integer(), nullable=False),
        sa.Column("heropend", sa.Integer(), nullable=False),
        sa.Column("heropeningen", JSONB, nullable=False),
        sa.Column("erkend_door", sa.String(length=80), nullable=True),
        sa.Column("erkend_op", TS, nullable=True),
        sa.Column("erkend_tot", TS, nullable=True),
        sa.Column("gesnoozed_door", sa.String(length=80), nullable=True),
        sa.Column("gesnoozed_tot", TS, nullable=True),
        sa.Column("opgelost_op", TS, nullable=True),
        sa.Column("opgelost_door", sa.String(length=80), nullable=True),
        sa.Column("oplos_reden", sa.String(length=300), nullable=True),
        sa.Column("hypothese", JSONB, nullable=False),
        sa.Column("oorzaak_sleutel", sa.String(length=96), nullable=True),
        sa.Column("runbook_id", sa.String(length=48), nullable=True),
        sa.Column("veilige_modus", sa.Boolean(), nullable=False),
        sa.Column("veilige_modus_sinds", TS, nullable=True),
        sa.Column("trace_ids", JSONB, nullable=False),
        sa.Column("correlatie_ids", JSONB, nullable=False),
        sa.Column("meldt", sa.Boolean(), nullable=False),
        sa.Column("melding_teller", sa.Integer(), nullable=False),
        sa.Column("laatst_gemeld_op", TS, nullable=True),
        sa.Column("escalaties", sa.Integer(), nullable=False),
        sa.Column("classificatie", sa.String(length=16), nullable=False),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_vingerafdruk"), "incident", ["vingerafdruk"], unique=False)
    op.create_index(op.f("ix_incident_soort"), "incident", ["soort"], unique=False)
    op.create_index(op.f("ix_incident_oorzaak_sleutel"), "incident", ["oorzaak_sleutel"], unique=False)
    op.create_index("ix_incident_status_laatste", "incident", ["status", "laatste_op"], unique=False)
    op.create_index(
        "uq_incident_actief",
        "incident",
        ["vingerafdruk"],
        unique=True,
        postgresql_where=sa.text("status <> 'opgelost'"),
    )
    op.create_table(
        "incident_event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("bron_ref", sa.String(length=200), nullable=False),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("op", TS, nullable=False),
        sa.Column("ontvangen_op", TS, nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=True),
        sa.Column("bron", sa.String(length=64), nullable=False),
        sa.Column("samenvatting", sa.String(length=500), nullable=False),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("classificatie", sa.String(length=16), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("actor", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incident.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bron_ref"),
    )
    op.create_index("ix_incident_event_incident_op", "incident_event", ["incident_id", "op"], unique=False)
    op.create_table(
        "log_entry",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("op", TS, nullable=False),
        sa.Column("ontvangen_op", TS, nullable=False),
        sa.Column("bron", sa.String(length=64), nullable=False),
        sa.Column("niveau", sa.String(length=8), nullable=False),
        sa.Column("logger", sa.String(length=96), nullable=False),
        sa.Column("bericht", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("velden", JSONB, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_log_entry_op"), "log_entry", ["op"], unique=False)
    op.create_index(op.f("ix_log_entry_trace_id"), "log_entry", ["trace_id"], unique=False)
    op.create_index("ix_log_entry_bron_op", "log_entry", ["bron", "op"], unique=False)

    for table in ("event_inbox", "event_outbox"):
        op.add_column(table, sa.Column("incident_verwerkt_op", TS, nullable=True))
        op.execute(f"UPDATE {table} SET incident_verwerkt_op = now()")  # noqa: S608 - vaste tabelnamen
        op.create_index(
            f"ix_{table}_onverwerkt",
            table,
            ["seq"],
            unique=False,
            postgresql_where=sa.text("incident_verwerkt_op IS NULL"),
        )
    op.add_column("notification", sa.Column("incident_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "notification_incident_id_fkey", "notification", "incident", ["incident_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_notification_incident_id"), "notification", ["incident_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_incident_id"), table_name="notification")
    op.drop_constraint("notification_incident_id_fkey", "notification", type_="foreignkey")
    op.drop_column("notification", "incident_id")
    for table in ("event_inbox", "event_outbox"):
        op.drop_index(f"ix_{table}_onverwerkt", table_name=table)
        op.drop_column(table, "incident_verwerkt_op")
    op.drop_table("log_entry")
    op.drop_table("incident_event")
    op.drop_table("incident")
