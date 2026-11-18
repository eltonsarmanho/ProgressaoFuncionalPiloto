"""UIM-21: activities.unit_points_override (migration 0005) on real PostgreSQL."""

from alembic import command
from sqlalchemy import create_engine, inspect

from tests.integration.conftest import alembic_config


def _column(url: str):
    eng = create_engine(url)
    try:
        columns = {c["name"]: c for c in inspect(eng).get_columns("activities")}
        return columns.get("unit_points_override")
    finally:
        eng.dispose()


def test_unit_points_override_is_a_nullable_numeric_9_2_column(migrated_url):
    column = _column(migrated_url)

    assert column is not None
    assert column["nullable"] is True
    assert (column["type"].precision, column["type"].scale) == (9, 2)


def test_downgrade_one_revision_drops_the_column_and_upgrade_restores_it(migrated_url):
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0004")  # below 0005, whichever revision is the head
        assert _column(migrated_url) is None
    finally:
        command.upgrade(cfg, "head")

    assert _column(migrated_url) is not None
