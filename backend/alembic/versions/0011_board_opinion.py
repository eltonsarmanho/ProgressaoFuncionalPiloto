"""board ordinances, opinions, request settings and dossier deliveries, and the REQUERIMENTO and
PARECER kinds of generated documents

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-22 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_TYPES = ("board_role", "value_source", "ordinance_reading_state", "opinion_conclusion")

TIMESTAMP = sa.DateTime(timezone=True)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    # PAR-02, REQ-01: the two new kinds of generated documents. PostgreSQL runs the ADD VALUE in
    # the migration transaction but cannot use the values before it commits, so nothing below
    # uses them, and a downgrade cannot take them out (as in 0007).
    op.execute("ALTER TYPE generated_kind ADD VALUE IF NOT EXISTS 'REQUERIMENTO'")
    op.execute("ALTER TYPE generated_kind ADD VALUE IF NOT EXISTS 'PARECER'")

    role = _enum("board_role", "PRESIDENTE", "MEMBRO", "SUPLENTE")
    source = _enum("value_source", "EXTRAIDO", "INFORMADO")
    reading = _enum("ordinance_reading_state", "SEM_ARQUIVO", "PENDENTE", "LENDO", "LIDA", "FALHOU")
    conclusion = _enum("opinion_conclusion", "FAVORAVEL", "DESFAVORAVEL")
    for enum in (role, source, reading, conclusion):
        enum.create(op.get_bind(), checkfirst=False)

    # PORT-01, PORT-05, PORT-07: one ordinance per process, outside `documents` (PORT-09). The
    # members are a JSONB list `[{name, role, page, source}]` replaced whole on each save.
    op.create_table(
        "board_ordinances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.String(length=50), nullable=True),
        sa.Column("number_page", sa.Integer(), nullable=True),
        sa.Column("number_source", source, nullable=True),
        sa.Column("ordinance_date", sa.Date(), nullable=True),
        sa.Column("date_page", sa.Integer(), nullable=True),
        sa.Column("date_source", source, nullable=True),
        sa.Column(
            "members",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("original_name", sa.String(length=255), nullable=True),
        sa.Column("internal_name", sa.String(length=64), nullable=True),
        sa.Column("mime", sa.String(length=50), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.CHAR(length=64), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("file_deleted_at", TIMESTAMP, nullable=True),
        sa.Column("reading_state", reading, server_default="SEM_ARQUIVO", nullable=False),
        sa.Column("reading_code", sa.String(length=40), nullable=True),
        sa.Column("reading_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reading_requested_at", TIMESTAMP, nullable=True),
        sa.Column("reading_started_at", TIMESTAMP, nullable=True),
        sa.Column("reading_finished_at", TIMESTAMP, nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", name="uq_board_ordinances_process"),
        sa.UniqueConstraint("internal_name", name="uq_board_ordinances_internal_name"),
    )
    # PORT-07: the worker picks the queued ordinances in order.
    op.create_index(
        "ix_board_ordinances_pending",
        "board_ordinances",
        ["reading_requested_at"],
        postgresql_where=sa.text("reading_state = 'PENDENTE'"),
    )

    # PAR-01, PAR-12, PAR-13: the fields of the Parecer; the conclusion has no default.
    op.create_table(
        "board_opinions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("conclusion", conclusion, nullable=True),
        sa.Column("opinion_date", sa.Date(), nullable=True),
        sa.Column("place", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(notes) <= 5000", name="ck_board_opinions_notes"),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", name="uq_board_opinions_process"),
    )

    # REQ-05: the city of the Requerimento, apart from the process (rule 5, no justification).
    op.create_table(
        "request_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", name="uq_request_settings_process"),
    )

    # DOS-04: the "Entregue" marks of the items the system does not produce.
    op.create_table(
        "dossier_deliveries",
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("item_key", sa.String(length=40), nullable=False),
        sa.Column("marked_by", sa.UUID(), nullable=True),
        sa.Column("marked_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("process_id", "item_key"),
    )


def downgrade() -> None:
    # PostgreSQL cannot drop a value from an enum; the unused REQUERIMENTO and PARECER stay in
    # generated_kind.
    op.drop_table("dossier_deliveries")
    op.drop_table("request_settings")
    op.drop_table("board_opinions")
    op.drop_index("ix_board_ordinances_pending", table_name="board_ordinances")
    op.drop_table("board_ordinances")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
