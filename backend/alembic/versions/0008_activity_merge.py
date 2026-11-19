"""mark an activity as merged into another and remember where a moved evidence came from

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-19 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # DUP-02: both foreign keys are NO ACTION, checked at the end of the statement, so the one
    # DELETE of the process purge (0007) still removes every activity at once.
    op.add_column(
        "activities",
        sa.Column("merged_into_id", sa.UUID(), sa.ForeignKey("activities.id"), nullable=True),
    )
    op.create_index(
        "ix_activities_merged_into",
        "activities",
        ["merged_into_id"],
        postgresql_where=sa.text("merged_into_id IS NOT NULL"),
    )
    op.add_column(
        "activity_evidences",
        sa.Column("origin_activity_id", sa.UUID(), sa.ForeignKey("activities.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activity_evidences", "origin_activity_id")
    op.drop_index("ix_activities_merged_into", table_name="activities")
    op.drop_column("activities", "merged_into_id")
