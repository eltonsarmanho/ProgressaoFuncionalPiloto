"""GTAB-01: migration 0012 (scoring_unit_defaults) on real PostgreSQL."""

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_table,
    base,
)

TABLE = "scoring_unit_defaults"


def _inspect(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        if TABLE not in insp.get_table_names():
            return None
        return {
            "primary_key": insp.get_pk_constraint(TABLE)["constrained_columns"],
            "foreign_keys": {
                tuple(fk["constrained_columns"]): (
                    fk["referred_table"],
                    fk.get("options", {}).get("ondelete"),
                )
                for fk in insp.get_foreign_keys(TABLE)
            },
            "columns": {c["name"]: c["nullable"] for c in insp.get_columns(TABLE)},
        }
    finally:
        eng.dispose()


def _insert(conn, unit_id, version_id):
    conn.execute(
        text("INSERT INTO scoring_unit_defaults (unit_id, version_id) VALUES (:u, :v)"),
        {"u": unit_id, "v": version_id},
    )


def test_upgrade_creates_the_table_keyed_by_unit_with_the_two_foreign_keys(migrated_url):
    shape = _inspect(migrated_url)

    assert shape is not None
    assert shape["primary_key"] == ["unit_id"]
    assert shape["foreign_keys"] == {
        ("unit_id",): ("academic_units", None),
        ("version_id",): ("scoring_table_versions", None),
    }
    assert shape["columns"] == {"unit_id": False, "version_id": False, "updated_at": False}


def test_a_unit_has_at_most_one_in_use_version(uow_factory, base, engine):  # noqa: F811
    _table, first = add_table(uow_factory, base, "Tabela A")
    _table, second = add_table(uow_factory, base, "Tabela B")
    unit_id = base["unit"].id
    with engine.begin() as conn:
        _insert(conn, unit_id, first.id)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, unit_id, second.id)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_id FROM scoring_unit_defaults")).scalars().all()
    assert rows == [first.id]


def test_updated_at_defaults_to_now(uow_factory, base, engine):  # noqa: F811
    _table, version = add_table(uow_factory, base)
    with engine.begin() as conn:
        _insert(conn, base["unit"].id, version.id)
    with engine.connect() as conn:
        stamped = conn.execute(
            text("SELECT updated_at IS NOT NULL FROM scoring_unit_defaults")
        ).scalar_one()
    assert stamped is True


def test_the_database_refuses_to_delete_a_version_that_a_unit_uses(
    uow_factory, base, engine  # noqa: F811
):
    _table, version = add_table(uow_factory, base)
    with engine.begin() as conn:
        _insert(conn, base["unit"].id, version.id)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text("DELETE FROM scoring_table_versions WHERE id = :i"), {"i": version.id}
        )

    with engine.connect() as conn:
        left = conn.execute(
            text("SELECT count(*) FROM scoring_table_versions WHERE id = :i"), {"i": version.id}
        ).scalar_one()
    assert left == 1


def test_downgrade_to_0011_drops_the_table_and_a_new_upgrade_recreates_it(migrated_url):
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0011")
        assert _inspect(migrated_url) is None
    finally:
        command.upgrade(cfg, "head")

    assert _inspect(migrated_url) is not None
