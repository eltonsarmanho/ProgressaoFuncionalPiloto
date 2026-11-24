"""GI-07: scoring_table_versions.superseded_by_id (migration 0009) on real PostgreSQL."""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_table,
    base,
)


def _column(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        column = {c["name"]: c for c in insp.get_columns("scoring_table_versions")}.get(
            "superseded_by_id"
        )
        foreign_keys = [
            fk
            for fk in insp.get_foreign_keys("scoring_table_versions")
            if fk["constrained_columns"] == ["superseded_by_id"]
        ]
        return column, foreign_keys
    finally:
        eng.dispose()


def test_upgrade_adds_a_nullable_uuid_column_with_a_foreign_key_to_the_same_table(migrated_url):
    column, foreign_keys = _column(migrated_url)

    assert column is not None and column["nullable"] is True
    assert column["type"].__class__.__name__ == "UUID"
    assert len(foreign_keys) == 1
    assert foreign_keys[0]["referred_table"] == "scoring_table_versions"
    assert foreign_keys[0]["referred_columns"] == ["id"]
    assert not foreign_keys[0].get("options", {}).get("ondelete")


def test_downgrade_one_revision_drops_the_column_and_keeps_the_versions(
    uow_factory, base, migrated_url  # noqa: F811
):
    _table, version = add_table(uow_factory, base)
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0008")
        column, foreign_keys = _column(migrated_url)
        assert (column, foreign_keys) == (None, [])
        eng = create_engine(migrated_url)
        try:
            with eng.connect() as conn:
                name = conn.execute(
                    text("SELECT name FROM scoring_table_versions WHERE id = :i"),
                    {"i": version.id},
                ).scalar_one()
        finally:
            eng.dispose()
        assert name == version.name
    finally:
        command.upgrade(cfg, "head")

    column, _foreign_keys = _column(migrated_url)
    assert column is not None


def test_the_database_refuses_a_mark_that_points_to_an_unknown_version(
    uow_factory, base, engine  # noqa: F811
):
    _table, version = add_table(uow_factory, base)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text("UPDATE scoring_table_versions SET superseded_by_id = :x WHERE id = :i"),
            {"x": uuid.uuid4(), "i": version.id},
        )
