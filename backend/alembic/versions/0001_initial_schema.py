"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-16 22:00:28.893007

AUD-02: audit_logs rows cannot be updated or deleted (trigger below).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ENUM_TYPES = (
    "unit_kind",
    "titration",
    "work_regime",
    "user_role",
    "audit_action",
    "modality",
    "process_status",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.create_table(
        "academic_units",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("acronym", sa.String(length=50), nullable=False),
        sa.Column(
            "kind", sa.Enum("CAMPUS", "INSTITUTO", "FACULDADE", name="unit_kind"), nullable=False
        ),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["academic_units.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "career_structures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_login_attempts_email_attempted_at",
        "login_attempts",
        ["email", "attempted_at"],
        unique=False,
    )
    op.create_table(
        "career_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("structure_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("norm_reference", sa.Text(), nullable=False),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["structure_id"],
            ["career_structures.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "professors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("siape", sa.CHAR(length=7), nullable=False),
        sa.Column(
            "titration",
            sa.Enum("GRADUACAO", "ESPECIALIZACAO", "MESTRADO", "DOUTORADO", name="titration"),
            nullable=False,
        ),
        sa.Column("position", sa.String(length=255), nullable=False),
        sa.Column("career_structure_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("faculty", sa.String(length=255), nullable=False),
        sa.Column("campus", sa.String(length=255), nullable=False),
        sa.Column("work_regime", sa.Enum("20H", "40H", "DE", name="work_regime"), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["career_structure_id"],
            ["career_structures.id"],
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["academic_units.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("siape"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "role", sa.Enum("ADMIN", "SECRETARIA", "DOCENTE", name="user_role"), nullable=False
        ),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("professor_id", sa.UUID(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["professor_id"],
            ["professors.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("professor_id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column(
            "action",
            sa.Enum("CREATE", "UPDATE", "ARCHIVE", "STATUS", name="audit_action"),
            nullable=False,
        ),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity", "entity_id"], unique=False)
    op.create_table(
        "functional_processes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("professor_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("modality", sa.Enum("PROGRESSAO", "PROMOCAO", name="modality"), nullable=False),
        sa.Column("current_class", sa.String(length=20), nullable=False),
        sa.Column("current_denomination", sa.String(length=100), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("target_class", sa.String(length=20), nullable=False),
        sa.Column("target_denomination", sa.String(length=100), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("opening_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("RASCUNHO", "EM_ANDAMENTO", "CONCLUIDO", "ARQUIVADO", name="process_status"),
            nullable=False,
        ),
        sa.Column("resp_name", sa.String(length=255), nullable=True),
        sa.Column("resp_position", sa.String(length=255), nullable=True),
        sa.Column("resp_appointment", sa.String(length=255), nullable=True),
        sa.Column("resp_admin_unit", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["professor_id"],
            ["professors.id"],
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["academic_units.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "user_units",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["academic_units.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "unit_id"),
    )
    # SPEC_DEVIATION: design.md asks for REVOKE UPDATE, DELETE on audit_logs for the app role.
    # Reason: the application connects as the table owner, and an owner keeps its privileges
    # after a REVOKE. A trigger rejects UPDATE/DELETE for every role, owner included.
    op.execute(
        """
        CREATE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER audit_logs_no_update_delete BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update_delete ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable()")
    op.drop_table("user_units")
    op.drop_table("sessions")
    op.drop_table("functional_processes")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("professors")
    op.drop_table("career_versions")
    op.drop_index("ix_login_attempts_email_attempted_at", table_name="login_attempts")
    op.drop_table("login_attempts")
    op.drop_table("career_structures")
    op.drop_table("academic_units")
    for name in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {name}")
