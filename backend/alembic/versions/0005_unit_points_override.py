"""unit value typed by hand on an activity (UIM-21)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("unit_points_override", sa.Numeric(9, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("activities", "unit_points_override")
