"""the scoring version in use of each academic unit

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-23 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GTAB-01: at most one version in use per unit (the primary key). The version has no
    # ON DELETE, so the database refuses to delete a version that a unit has in use.
    op.create_table(
        "scoring_unit_defaults",
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["unit_id"], ["academic_units.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["scoring_table_versions.id"]),
        sa.PrimaryKeyConstraint("unit_id"),
    )


def downgrade() -> None:
    op.drop_table("scoring_unit_defaults")
