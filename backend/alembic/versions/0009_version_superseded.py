"""mark a scoring table version as superseded by a newer one

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-20 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GI-07: schema only, no data. The foreign key is NO ACTION; the new version itself is
    # inserted by the seed and the old one is marked afterwards (AdoptSupersedingVersion).
    op.add_column(
        "scoring_table_versions",
        sa.Column(
            "superseded_by_id",
            sa.UUID(),
            sa.ForeignKey("scoring_table_versions.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("scoring_table_versions", "superseded_by_id")
