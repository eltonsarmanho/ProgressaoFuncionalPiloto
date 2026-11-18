"""scoring tables, activities and process table choice

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_TYPES = (
    "table_status",
    "scoring_mode",
    "period_precision",
    "activity_level",
    "activity_source",
    "activity_status",
)


TIMESTAMP = sa.DateTime(timezone=True)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    table_status = _enum("table_status", "OFICIAL", "PENDENTE_VALIDACAO")
    scoring_mode = _enum(
        "scoring_mode", "POR_UNIDADE", "POR_BLOCO_DE_HORAS", "CARGA_SEMANAL", "VALOR_INFORMADO"
    )
    period_precision = _enum("period_precision", "DAY", "MONTH")
    activity_level = _enum("activity_level", "GRADUACAO", "POS_GRADUACAO")
    activity_source = _enum("activity_source", "MANUAL", "SUGERIDA_IA", "IMPORTADA")
    activity_status = _enum("activity_status", "AGUARDANDO_REVISAO", "VALIDADA", "REJEITADA")
    for enum in (
        table_status,
        scoring_mode,
        period_precision,
        activity_level,
        activity_source,
        activity_status,
    ):
        enum.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "scoring_tables",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "scoring_table_units",
        sa.Column("table_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["scoring_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["academic_units.id"]),
        sa.PrimaryKeyConstraint("table_id", "unit_id"),
    )
    op.create_table(
        "scoring_table_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("table_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("norm_reference", sa.Text(), nullable=False),
        sa.Column("status", table_status, nullable=False),
        sa.Column("minimums", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["scoring_tables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scoring_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("counts_in_total", sa.Boolean(), nullable=False),
        sa.Column("max_points", sa.Numeric(9, 2), nullable=True),
        sa.CheckConstraint("number BETWEEN 1 AND 8", name="ck_scoring_groups_number"),
        sa.ForeignKeyConstraint(["version_id"], ["scoring_table_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "number", name="uq_scoring_groups_version_number"),
    )
    op.create_table(
        "scoring_criteria",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("item_number", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit_label", sa.Text(), nullable=False),
        sa.Column("mode", scoring_mode, nullable=False),
        sa.Column("unit_points", sa.Numeric(9, 2), nullable=True),
        sa.Column("hours_per_block", sa.Numeric(9, 2), nullable=True),
        sa.Column("weeks_per_semester", sa.SmallInteger(), nullable=True),
        sa.Column("prep_ratio", sa.Numeric(4, 2), nullable=True),
        sa.Column("max_points", sa.Numeric(9, 2), nullable=True),
        sa.Column("accepted_evidence", sa.Text(), nullable=False),
        sa.Column("rules", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["scoring_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "item_number", name="uq_scoring_criteria_group_item"),
    )
    op.create_table(
        "activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("group_number", sa.SmallInteger(), nullable=True),
        sa.Column("item_number", sa.SmallInteger(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("period_precision", period_precision, nullable=False),
        sa.Column("academic_period", sa.String(length=7), nullable=True),
        sa.Column("level", activity_level, nullable=True),
        sa.Column("quantity", sa.Numeric(9, 2), nullable=True),
        sa.Column("hours", sa.Numeric(9, 2), nullable=True),
        sa.Column("course_hours", sa.Numeric(9, 2), nullable=True),
        sa.Column("informed_points", sa.Numeric(9, 2), nullable=True),
        sa.Column("points_override", sa.Numeric(9, 2), nullable=True),
        sa.Column("evidence_note", sa.String(length=500), nullable=True),
        sa.Column("source", activity_source, nullable=False),
        sa.Column("status", activity_status, nullable=False),
        sa.Column("distinct_justification", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_process_id", "activities", ["process_id"], unique=False)
    op.create_table(
        "activity_candidates",
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("group_number", sa.SmallInteger(), nullable=False),
        sa.Column("item_number", sa.SmallInteger(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("activity_id", "group_number", "item_number"),
    )
    op.add_column(
        "functional_processes", sa.Column("scoring_table_version_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_functional_processes_scoring_table_version",
        "functional_processes",
        "scoring_table_versions",
        ["scoring_table_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_functional_processes_scoring_table_version", "functional_processes", type_="foreignkey"
    )
    op.drop_column("functional_processes", "scoring_table_version_id")
    op.drop_table("activity_candidates")
    op.drop_index("ix_activities_process_id", table_name="activities")
    op.drop_table("activities")
    op.drop_table("scoring_criteria")
    op.drop_table("scoring_groups")
    op.drop_table("scoring_table_versions")
    op.drop_table("scoring_table_units")
    op.drop_table("scoring_tables")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
