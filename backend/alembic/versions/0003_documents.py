"""documents, extraction runs, pages, processing jobs and activity evidences

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_TYPES = ("document_status", "extraction_run_status", "text_method", "job_status")

TIMESTAMP = sa.DateTime(timezone=True)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    document_status = _enum(
        "document_status",
        "PENDENTE",
        "PROCESSANDO",
        "PROCESSADO",
        "REQUER_REVISAO",
        "EXTRAIDO_SEM_IA",
        "FALHOU",
    )
    run_status = _enum("extraction_run_status", "ATIVA", "SUBSTITUIDA")
    text_method = _enum("text_method", "TEXTO", "OCR")
    job_status = _enum("job_status", "PENDENTE", "PROCESSANDO", "CONCLUIDA", "FALHOU")
    for enum in (document_status, run_status, text_method, job_status):
        enum.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("process_id", sa.UUID(), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("internal_name", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.String(length=40), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("page_count", sa.SmallInteger(), nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("status_code", sa.String(length=40), nullable=True),
        sa.Column("manual_type", sa.String(length=40), nullable=True),
        sa.Column("manual_category", sa.String(length=60), nullable=True),
        sa.Column("suggested_type", sa.String(length=40), nullable=True),
        sa.Column("suggested_category", sa.String(length=60), nullable=True),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
        sa.Column("uploaded_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["functional_processes.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_name"),
        sa.UniqueConstraint("process_id", "sha256", name="uq_documents_process_sha256"),
    )
    op.create_index("ix_documents_process_id", "documents", ["process_id"], unique=False)

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("model", sa.String(length=60), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_runs_document_id", "extraction_runs", ["document_id"])
    # EXT-13: only `status` may change. Same approach as the audit_logs trigger in 0001.
    op.execute(
        """
        CREATE FUNCTION extraction_runs_content_immutable() RETURNS trigger AS $$
        BEGIN
            IF (NEW.id, NEW.document_id, NEW.model, NEW.duration_ms, NEW.raw_json,
                NEW.warnings, NEW.created_at)
               IS DISTINCT FROM
               (OLD.id, OLD.document_id, OLD.model, OLD.duration_ms, OLD.raw_json,
                OLD.warnings, OLD.created_at) THEN
                RAISE EXCEPTION 'extraction_runs content is immutable; only status may change';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER extraction_runs_only_status_update BEFORE UPDATE ON extraction_runs "
        "FOR EACH ROW EXECUTE FUNCTION extraction_runs_content_immutable()"
    )

    op.create_table(
        "document_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("page_number", sa.SmallInteger(), nullable=False),
        sa.Column("method", text_method, nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("ocr_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "page_number", name="uq_document_pages_run_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", TIMESTAMP, nullable=True),
        sa.Column("finished_at", TIMESTAMP, nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_processing_jobs_active_document",
        "processing_jobs",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDENTE', 'PROCESSANDO')"),
    )

    op.create_table(
        "activity_evidences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("activity_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("page_number", sa.SmallInteger(), nullable=False),
        sa.Column("excerpt", sa.String(length=300), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["extraction_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_id", "document_id", "page_number", name="uq_activity_evidences_page"
        ),
    )
    op.create_index("ix_activity_evidences_activity_id", "activity_evidences", ["activity_id"])
    op.create_index("ix_activity_evidences_document_id", "activity_evidences", ["document_id"])

    op.add_column("activities", sa.Column("extraction_run_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_activities_extraction_run",
        "activities",
        "extraction_runs",
        ["extraction_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_activities_extraction_run", "activities", type_="foreignkey")
    op.drop_column("activities", "extraction_run_id")
    op.drop_index("ix_activity_evidences_document_id", table_name="activity_evidences")
    op.drop_index("ix_activity_evidences_activity_id", table_name="activity_evidences")
    op.drop_table("activity_evidences")
    op.drop_index("uq_processing_jobs_active_document", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
    op.execute("DROP TRIGGER IF EXISTS extraction_runs_only_status_update ON extraction_runs")
    op.execute("DROP FUNCTION IF EXISTS extraction_runs_content_immutable()")
    op.drop_index("ix_extraction_runs_document_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")
    op.drop_index("ix_documents_process_id", table_name="documents")
    op.drop_table("documents")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
