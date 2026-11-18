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

    op.create_table(
        "report_wording_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("section_key", sa.String(length=20), nullable=False),
        sa.Column("state", state, nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("requested_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("finished_at", TIMESTAMP, nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        # [{code, reason?}]: the warnings the wording gave the section.
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # REL-13: one wording per process and section at a time, without a race.
    op.create_index(
        "uq_report_wording_jobs_generating",
        "report_wording_jobs",
        ["process_id", "section_key"],
        unique=True,
        postgresql_where=sa.text("state = 'GERANDO'"),
    )
    op.create_index(
        "ix_report_wording_jobs_history",
        "report_wording_jobs",
        ["process_id", "section_key", sa.text("requested_at DESC")],
    )

    op.create_table(
        "report_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.String(length=60), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", name="uq_report_drafts_process"),
    )

    op.create_table(
        "comprovante_layouts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", name="uq_comprovante_layouts_process"),
    )

    # DEL-05, DEL-06: set when the conclusion removed the file; existing documents stay NULL.
    op.add_column("documents", sa.Column("file_deleted_at", TIMESTAMP, nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "file_deleted_at")
    op.drop_table("comprovante_layouts")
    op.drop_table("report_drafts")
    op.drop_index("ix_report_wording_jobs_history", table_name="report_wording_jobs")
    op.drop_index("uq_report_wording_jobs_generating", table_name="report_wording_jobs")
    op.drop_table("report_wording_jobs")
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
