"""generated documents, their files, wording jobs, report drafts, comprovante layouts and the
purge mark of input documents

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_TYPES = ("generated_kind", "generated_state", "generated_format")

TIMESTAMP = sa.DateTime(timezone=True)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    kind = _enum("generated_kind", "TABELA", "RELATORIO", "COMPROVANTE")
    state = _enum("generated_state", "GERANDO", "PRONTO", "FALHOU")
    file_format = _enum("generated_format", "DOCX", "PDF")
    for enum in (kind, state, file_format):
        enum.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("kind", kind, nullable=False),
        sa.Column("state", state, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("requested_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("finished_at", TIMESTAMP, nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("error_message", sa.String(length=300), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("alerts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plan_hash", sa.CHAR(length=64), nullable=True),
        # No ON DELETE CASCADE: a generated version is the record of what was delivered.
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "process_id", "kind", "version_number", name="uq_generated_documents_version"
        ),
    )
    # VER-04: one generation per process and kind at a time, without a race.
    op.create_index(
        "uq_generated_documents_generating",
        "generated_documents",
        ["process_id", "kind"],
        unique=True,
        postgresql_where=sa.text("state = 'GERANDO'"),
    )
    op.create_index(
        "ix_generated_documents_history",
        "generated_documents",
        ["process_id", "kind", sa.text("requested_at DESC")],
    )

    op.create_table(
        "generated_files",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("generated_document_id", sa.UUID(), nullable=False),
        sa.Column("format", file_format, nullable=False),
        sa.Column("internal_name", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["generated_document_id"], ["generated_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_name"),
        sa.UniqueConstraint("generated_document_id", "format", name="uq_generated_files_format"),
    )

    # VER-01: a version never changes once it leaves GERANDO (same approach as extraction_runs).
    op.execute(
        """
        CREATE FUNCTION generated_documents_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'generated_documents cannot be deleted';
            END IF;
            IF OLD.state <> 'GERANDO' THEN
                RAISE EXCEPTION 'generated_documents is immutable once it left GERANDO';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER generated_documents_guard BEFORE UPDATE OR DELETE ON generated_documents "
        "FOR EACH ROW EXECUTE FUNCTION generated_documents_immutable()"
    )
    op.execute(
        """
        CREATE FUNCTION generated_files_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'generated_files cannot be deleted';
            END IF;
            RAISE EXCEPTION 'generated_files is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER generated_files_guard BEFORE UPDATE OR DELETE ON generated_files "
        "FOR EACH ROW EXECUTE FUNCTION generated_files_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS generated_files_guard ON generated_files")
    op.execute("DROP FUNCTION IF EXISTS generated_files_immutable()")
    op.drop_table("generated_files")
    op.execute("DROP TRIGGER IF EXISTS generated_documents_guard ON generated_documents")
    op.execute("DROP FUNCTION IF EXISTS generated_documents_immutable()")
    op.drop_index("ix_generated_documents_history", table_name="generated_documents")
    op.drop_index("uq_generated_documents_generating", table_name="generated_documents")
    op.drop_table("generated_documents")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
