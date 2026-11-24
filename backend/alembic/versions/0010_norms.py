"""norms table and the norm_code columns of career and scoring table versions

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-22 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NORM_KINDS = ("LEI", "RESOLUCAO", "INSTRUCAO_NORMATIVA", "MANUAL", "TABELA", "OUTRO")


def upgrade() -> None:
    # NBASE-01, NLINK-01: schema only, no data. norm_code has no foreign key to norms.code, so
    # the migration runs before the seed and a code with no norm reads as "no norm"; the seed
    # fills the norms and the links.
    op.create_table(
        "norms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("kind", sa.Enum(*NORM_KINDS, name="norm_kind"), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("file_internal_name", sa.String(length=64), nullable=True),
        sa.Column("file_original_name", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("file_sha256", sa.CHAR(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from",
            name="ck_norms_validity",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.add_column("career_versions", sa.Column("norm_code", sa.String(length=50), nullable=True))
    op.add_column(
        "scoring_table_versions", sa.Column("norm_code", sa.String(length=50), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scoring_table_versions", "norm_code")
    op.drop_column("career_versions", "norm_code")
    op.drop_table("norms")
    op.execute("DROP TYPE IF EXISTS norm_kind")
