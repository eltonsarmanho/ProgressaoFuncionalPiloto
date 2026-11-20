"""TAB-01, TAB-02, SEL-01, ATV-01: scoring schema (migration 0002) on real PostgreSQL."""

import uuid
from datetime import date

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config

SCORING_TABLES = {
    "scoring_tables",
    "scoring_table_units",
    "scoring_table_versions",
    "scoring_groups",
    "scoring_criteria",
    "activities",
    "activity_candidates",
}


def _names(url: str) -> tuple[set[str], set[str], set[str]]:
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        columns = {c["name"] for c in insp.get_columns("functional_processes")}
        with eng.connect() as conn:
            enums = set(
                conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars()
            )
        return set(insp.get_table_names()), columns, enums
    finally:
        eng.dispose()


def test_downgrade_one_revision_and_upgrade_again(migrated_url):
    cfg = alembic_config(migrated_url)
    tables, columns, enums = _names(migrated_url)
    assert SCORING_TABLES <= tables
    assert "scoring_table_version_id" in columns
    assert {"scoring_mode", "table_status", "activity_status"} <= enums

    command.downgrade(cfg, "0001")
    tables, columns, enums = _names(migrated_url)
    assert not SCORING_TABLES & tables
    assert "scoring_table_version_id" not in columns
    assert not {"scoring_mode", "table_status", "period_precision", "activity_level",
                "activity_source", "activity_status"} & enums  # fmt: skip

    command.upgrade(cfg, "head")
    tables, columns, enums = _names(migrated_url)
    assert SCORING_TABLES <= tables
    assert "scoring_table_version_id" in columns
    assert "scoring_mode" in enums


def _version(conn) -> uuid.UUID:
    table_id, version_id = uuid.uuid4(), uuid.uuid4()
    conn.execute(
        text("INSERT INTO scoring_tables (id, name, archived) VALUES (:i, :n, false)"),
        {"i": table_id, "n": f"Tabela {table_id}"},
    )
    conn.execute(
        text(
            "INSERT INTO scoring_table_versions (id, table_id, name, valid_from, norm_reference, "
            "status) VALUES (:i, :t, 'v1', :d, 'ref', 'OFICIAL')"
        ),
        {"i": version_id, "t": table_id, "d": date(2015, 3, 24)},
    )
    return version_id


def _group(conn, version_id, number) -> uuid.UUID:
    group_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO scoring_groups (id, version_id, number, name, counts_in_total) "
            "VALUES (:i, :v, :n, 'Grupo', true)"
        ),
        {"i": group_id, "v": version_id, "n": number},
    )
    return group_id


def _criterion(conn, group_id, item) -> None:
    conn.execute(
        text(
            "INSERT INTO scoring_criteria (id, group_id, item_number, description, unit_label, "
            "mode, accepted_evidence, rules) VALUES (:i, :g, :n, 'd', 'u', 'POR_UNIDADE', '', '')"
        ),
        {"i": uuid.uuid4(), "g": group_id, "n": item},
    )


def test_group_number_is_unique_per_version(engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        version_id = _version(conn)
        _group(conn, version_id, 2)
        _group(conn, version_id, 2)


@pytest.mark.parametrize("number", [0, 9])
def test_group_number_must_be_between_1_and_8(engine, number):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _group(conn, _version(conn), number)


@pytest.mark.parametrize("number", [1, 8])
def test_group_number_accepts_the_limits(engine, number):
    with engine.begin() as conn:
        _group(conn, _version(conn), number)


def test_criterion_item_is_unique_per_group(engine):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        group_id = _group(conn, _version(conn), 3)
        _criterion(conn, group_id, 4)
        _criterion(conn, group_id, 4)


def test_same_item_in_different_groups_is_accepted(engine):
    with engine.begin() as conn:
        version_id = _version(conn)
        _criterion(conn, _group(conn, version_id, 3), 4)
        _criterion(conn, _group(conn, version_id, 4), 4)
