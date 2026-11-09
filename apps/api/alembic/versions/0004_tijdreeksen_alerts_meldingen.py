"""Tijdreeksen, alerts en meldingen (B09-003, Gotify)

- ``periodic_task``: laatste uitvoering per periodieke worker-taak.
- ``metric_series`` / ``metric_sample`` / ``metric_rollup``: genormaliseerde reeksen met retentie per reeks en
  aggregatie ruw → 5 min → 1 uur.
- ``alert_rule`` / ``alert_instance``: drempel + duur + hysterese, dempen, standaardregels.
- ``notification_channel`` / ``notification``: meldingskanalen (Gotify) en een wachtrij met dedupe per kanaal.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09 19:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "periodic_task",
        sa.Column("naam", sa.String(length=48), nullable=False),
        sa.Column("laatst_gestart", TS, nullable=True),
        sa.Column("laatst_klaar", TS, nullable=True),
        sa.Column("laatste_status", sa.String(length=16), nullable=True),
        sa.Column("laatste_reden", sa.String(length=64), nullable=True),
        sa.Column("duur_ms", sa.Integer(), nullable=True),
        sa.Column("details", JSONB, nullable=False),
        sa.PrimaryKeyConstraint("naam"),
    )

    op.create_table(
        "metric_series",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("sleutel", sa.String(length=255), nullable=False),
        sa.Column("onderwerp_type", sa.String(length=16), nullable=False),
        sa.Column("onderwerp_id", sa.String(length=128), nullable=False),
        sa.Column("metriek", sa.String(length=64), nullable=False),
        sa.Column("eenheid", sa.String(length=16), nullable=False),
        sa.Column("bron", sa.String(length=96), nullable=False),
        sa.Column("labels", JSONB, nullable=False),
        sa.Column("retentie_ruw_s", sa.Integer(), nullable=False),
        sa.Column("retentie_5m_s", sa.Integer(), nullable=False),
        sa.Column("retentie_1u_s", sa.Integer(), nullable=False),
        sa.Column("laatste_waarde", sa.Float(), nullable=True),
        sa.Column("laatste_op", TS, nullable=True),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sleutel"),
    )
    op.create_index("ix_metric_series_onderwerp", "metric_series", ["onderwerp_type", "onderwerp_id"], unique=False)
    op.create_index(op.f("ix_metric_series_metriek"), "metric_series", ["metriek"], unique=False)

    op.create_table(
        "metric_sample",
        sa.Column("series_id", sa.BigInteger(), nullable=False),
        sa.Column("ts", TS, nullable=False),
        sa.Column("waarde", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["metric_series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("series_id", "ts", name="pk_metric_sample"),
    )

    op.create_table(
        "metric_rollup",
        sa.Column("series_id", sa.BigInteger(), nullable=False),
        sa.Column("resolutie", sa.Integer(), nullable=False),
        sa.Column("bucket", TS, nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("min", sa.Float(), nullable=False),
        sa.Column("max", sa.Float(), nullable=False),
        sa.Column("som", sa.Float(), nullable=False),
        sa.Column("laatste", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["series_id"], ["metric_series.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("series_id", "resolutie", "bucket", name="pk_metric_rollup"),
    )

    op.create_table(
        "alert_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("standaard_sleutel", sa.String(length=48), nullable=True),
        sa.Column("naam", sa.String(length=120), nullable=False),
        sa.Column("metriek", sa.String(length=64), nullable=False),
        sa.Column("onderwerp_type", sa.String(length=16), nullable=True),
        sa.Column("onderwerp_id", sa.String(length=128), nullable=True),
        sa.Column("bron", sa.String(length=96), nullable=True),
        sa.Column("operator", sa.String(length=2), nullable=False),
        sa.Column("drempel", sa.Float(), nullable=False),
        sa.Column("herstel_drempel", sa.Float(), nullable=False),
        sa.Column("duur_s", sa.Integer(), nullable=False),
        sa.Column("herstel_duur_s", sa.Integer(), nullable=False),
        sa.Column("ernst", sa.String(length=16), nullable=False),
        sa.Column("herhaal_na_s", sa.Integer(), nullable=True),
        sa.Column("kanalen", JSONB, nullable=False),
        sa.Column("ingeschakeld", sa.Boolean(), nullable=False),
        sa.Column("gedempt_tot", TS, nullable=True),
        sa.Column("aangemaakt_door", sa.String(length=64), nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("bijgewerkt_door", sa.String(length=64), nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standaard_sleutel"),
    )

    op.create_table(
        "alert_instance",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("onderwerp_type", sa.String(length=16), nullable=False),
        sa.Column("onderwerp_id", sa.String(length=128), nullable=False),
        sa.Column("series_id", sa.BigInteger(), nullable=True),
        sa.Column("toestand", sa.String(length=16), nullable=False),
        sa.Column("sinds", TS, nullable=False),
        sa.Column("pending_sinds", TS, nullable=True),
        sa.Column("firing_sinds", TS, nullable=True),
        sa.Column("herstel_sinds", TS, nullable=True),
        sa.Column("laatste_waarde", sa.Float(), nullable=True),
        sa.Column("laatste_sample_op", TS, nullable=True),
        sa.Column("laatste_eval_op", TS, nullable=True),
        sa.Column("gegevens_verouderd", sa.Boolean(), nullable=False),
        sa.Column("gedempt_tot", TS, nullable=True),
        sa.Column("gedempt_door", sa.String(length=64), nullable=True),
        sa.Column("melding_teller", sa.Integer(), nullable=False),
        sa.Column("laatst_gemeld_op", TS, nullable=True),
        sa.Column("laatst_opgelost_op", TS, nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_id"], ["metric_series.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id", "onderwerp_type", "onderwerp_id", name="uq_alert_instance_onderwerp"),
    )
    op.create_index(op.f("ix_alert_instance_rule_id"), "alert_instance", ["rule_id"], unique=False)
    op.create_index(op.f("ix_alert_instance_series_id"), "alert_instance", ["series_id"], unique=False)

    op.create_table(
        "notification_channel",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("naam", sa.String(length=64), nullable=False),
        sa.Column("basis_url", sa.String(length=512), nullable=False),
        sa.Column("token_ref", sa.String(length=200), nullable=False),
        sa.Column("min_ernst", sa.String(length=16), nullable=False),
        sa.Column("stille_uren", JSONB, nullable=True),
        sa.Column("max_per_venster", sa.Integer(), nullable=False),
        sa.Column("venster_s", sa.Integer(), nullable=False),
        sa.Column("ingeschakeld", sa.Boolean(), nullable=False),
        sa.Column("laatste_status", sa.String(length=16), nullable=True),
        sa.Column("laatste_reden", sa.String(length=64), nullable=True),
        sa.Column("laatste_op", TS, nullable=True),
        sa.Column("laatste_versie", sa.String(length=64), nullable=True),
        sa.Column("onderdrukt_teller", sa.Integer(), nullable=False),
        sa.Column("onderdrukt_sinds", TS, nullable=True),
        sa.Column("aangemaakt_door", sa.String(length=64), nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("bijgewerkt_door", sa.String(length=64), nullable=False),
        sa.Column("bijgewerkt_op", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kanaal_id", sa.Uuid(), nullable=False),
        sa.Column("dedupe_sleutel", sa.String(length=255), nullable=False),
        sa.Column("bron", sa.String(length=16), nullable=False),
        sa.Column("alert_instance_id", sa.Uuid(), nullable=True),
        sa.Column("soort", sa.String(length=16), nullable=False),
        sa.Column("ernst", sa.String(length=16), nullable=False),
        sa.Column("titel", sa.String(length=160), nullable=False),
        sa.Column("bericht", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reden", sa.String(length=64), nullable=True),
        sa.Column("pogingen", sa.Integer(), nullable=False),
        sa.Column("volgende_poging_op", TS, nullable=False),
        sa.Column("aangemaakt_op", TS, nullable=False),
        sa.Column("aangemaakt_door", sa.String(length=64), nullable=False),
        sa.Column("verzonden_op", TS, nullable=True),
        sa.Column("extern_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["alert_instance_id"], ["alert_instance.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kanaal_id"], ["notification_channel.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kanaal_id", "dedupe_sleutel", name="uq_notification_dedupe"),
    )
    op.create_index("ix_notification_status_volgende", "notification", ["status", "volgende_poging_op"], unique=False)
    op.create_index(op.f("ix_notification_alert_instance_id"), "notification", ["alert_instance_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_alert_instance_id"), table_name="notification")
    op.drop_index("ix_notification_status_volgende", table_name="notification")
    op.drop_table("notification")
    op.drop_table("notification_channel")
    op.drop_index(op.f("ix_alert_instance_series_id"), table_name="alert_instance")
    op.drop_index(op.f("ix_alert_instance_rule_id"), table_name="alert_instance")
    op.drop_table("alert_instance")
    op.drop_table("alert_rule")
    op.drop_table("metric_rollup")
    op.drop_table("metric_sample")
    op.drop_index(op.f("ix_metric_series_metriek"), table_name="metric_series")
    op.drop_index("ix_metric_series_onderwerp", table_name="metric_series")
    op.drop_table("metric_series")
    op.drop_table("periodic_task")
