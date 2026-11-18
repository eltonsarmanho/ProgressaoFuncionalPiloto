"""OFI-12: scoring_criteria.min_hours (migration 0004) on real PostgreSQL."""

import uuid
from datetime import date

from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.integration.conftest import alembic_config


def _column(url: str):
    eng = create_engine(url)
    try:
        columns = {c["name"]: c for c in inspect(eng).get_columns("scoring_criteria")}
        return columns.get("min_hours")
    finally:
        eng.dispose()


def _insert_criterion(conn, min_hours) -> uuid.UUID:
    table_id, version_id, group_id, criterion_id = (uuid.uuid4() for _ in range(4))
    conn.execute(
        text("INSERT INTO scoring_tables (id, name, archived) VALUES (:id, :name, false)"),
        {"id": table_id, "name": f"Tabela {table_id}"},
    )
    conn.execute(
        text(
            "INSERT INTO scoring_table_versions (id, table_id, name, valid_from, norm_reference, "
            "status) VALUES (:id, :t, 'v', :d, 'ref', 'OFICIAL')"
        ),
        {"id": version_id, "t": table_id, "d": date(2015, 3, 24)},
    )
    conn.execute(
        text(
            "INSERT INTO scoring_groups (id, version_id, number, name, counts_in_total) "
            "VALUES (:id, :v, 4, 'IV', true)"
        ),
        {"id": group_id, "v": version_id},
    )
    conn.execute(
        text(
            "INSERT INTO scoring_criteria (id, group_id, item_number, description, unit_label, "
            "mode, unit_points, min_hours, accepted_evidence, rules) "
            "VALUES (:id, :g, 4, 'curso', 'curso', 'POR_UNIDADE', 5, :m, '', '')"
        ),
        {"id": criterion_id, "g": group_id, "m": min_hours},
    )
    return criterion_id


def test_min_hours_is_a_nullable_numeric_9_2_column(migrated_url):
    column = _column(migrated_url)

    assert column is not None
    assert column["nullable"] is True
    assert (column["type"].precision, column["type"].scale) == (9, 2)


def test_min_hours_stores_a_value_and_null(engine):
    with engine.begin() as conn:
        with_minimum = _insert_criterion(conn, "20")
        without = _insert_criterion(conn, None)
    with engine.connect() as conn:
        rows = dict(conn.execute(text("SELECT id, min_hours FROM scoring_criteria")).all())

    assert str(rows[with_minimum]) == "20.00"
    assert rows[without] is None


def test_downgrade_below_0004_drops_the_column_and_upgrade_restores_it(migrated_url):
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0003")  # below 0004, whichever revision is the head
        assert _column(migrated_url) is None
    finally:
        command.upgrade(cfg, "head")

    assert _column(migrated_url) is not None
