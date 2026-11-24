"""PORT-01, PORT-05, PORT-12, PAR-01, PAR-12, PAR-13, DOS-04: migration 0011 (board ordinances,
opinions, request settings and dossier deliveries) on real PostgreSQL."""

import dataclasses
import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DataError, IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.test_scoring_repositories import (  # noqa: F401  (fixture and helpers)
    add_process,
    base,
)

TABLES = {"board_ordinances", "board_opinions", "request_settings", "dossier_deliveries"}
ENUMS = {"board_role", "value_source", "ordinance_reading_state", "opinion_conclusion"}
PENDING_INDEX = "ix_board_ordinances_pending"


@pytest.fixture
def process(uow_factory, base):  # noqa: F811
    return add_process(uow_factory, base)


def _snapshot(url: str):
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            enums = set(
                conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars()
            )
            kind_values = list(
                conn.execute(
                    text(
                        "SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                        "WHERE t.typname = 'generated_kind' ORDER BY e.enumsortorder"
                    )
                ).scalars()
            )
            indexes = set(
                conn.execute(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
                ).scalars()
            )
        return set(inspect(eng).get_table_names()), enums, kind_values, indexes
    finally:
        eng.dispose()


def _ordinance(conn, process, **values):
    columns = {"id": uuid.uuid4(), "process_id": process.id, **values}
    names = ", ".join(columns)
    marks = ", ".join(f":{name}" for name in columns)
    conn.execute(text(f"INSERT INTO board_ordinances ({names}) VALUES ({marks})"), columns)
    return columns["id"]


def _opinion(conn, process, notes=None):
    conn.execute(
        text("INSERT INTO board_opinions (id, process_id, notes) VALUES (:id, :p, :notes)"),
        {"id": uuid.uuid4(), "p": process.id, "notes": notes},
    )


def _delivery(conn, process, key="CURRICULO_LATTES"):
    conn.execute(
        text("INSERT INTO dossier_deliveries (process_id, item_key) VALUES (:p, :key)"),
        {"p": process.id, "key": key},
    )


def test_upgrade_creates_the_four_tables_the_four_enums_and_the_partial_index(migrated_url):
    tables, enums, _, indexes = _snapshot(migrated_url)

    assert TABLES <= tables
    assert ENUMS <= enums
    assert PENDING_INDEX in indexes


def test_the_pending_index_only_covers_the_queued_ordinances(engine):
    with engine.connect() as conn:
        definition = conn.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :n"), {"n": PENDING_INDEX}
        ).scalar_one()

    assert "reading_state = 'PENDENTE'" in definition


def test_two_ordinances_of_the_same_process_are_refused(engine, process):
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _ordinance(conn, process)
        _ordinance(conn, process)


def test_a_new_ordinance_has_no_members_and_no_file_and_is_in_sem_arquivo(engine, process):
    with engine.begin() as conn:
        _ordinance(conn, process)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT members, reading_state, reading_attempts, warnings, version, "
                "number, file_deleted_at FROM board_ordinances"
            )
        ).one()

    assert row.members == []
    assert row.warnings == []
    assert row.reading_state == "SEM_ARQUIVO"
    assert (row.reading_attempts, row.version) == (0, 1)
    assert (row.number, row.file_deleted_at) == (None, None)


def test_a_new_opinion_has_no_conclusion_date_place_or_notes(engine, process):
    with engine.begin() as conn:
        _opinion(conn, process)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT conclusion, opinion_date, place, notes, version FROM board_opinions")
        ).one()

    assert (row.conclusion, row.opinion_date, row.place, row.notes) == (None, None, None, None)
    assert row.version == 1


def test_notes_of_5000_characters_are_accepted_and_5001_are_refused_by_the_check(engine, process):
    with engine.begin() as conn:
        _opinion(conn, process, "x" * 5000)

    with pytest.raises(IntegrityError, match="board_opinions"), engine.begin() as conn:
        conn.execute(text("DELETE FROM board_opinions"))
        _opinion(conn, process, "x" * 5001)


def test_a_conclusion_outside_the_two_values_is_refused(engine, process):
    with pytest.raises(DataError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO board_opinions (id, process_id, conclusion) VALUES (:id, :p, 'TALVEZ')"
            ),
            {"id": uuid.uuid4(), "p": process.id},
        )


def test_the_city_of_the_request_is_one_row_per_process(engine, process):
    insert = text("INSERT INTO request_settings (id, process_id, city) VALUES (:id, :p, 'Belém')")
    with engine.begin() as conn:
        conn.execute(insert, {"id": uuid.uuid4(), "p": process.id})

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert, {"id": uuid.uuid4(), "p": process.id})


def test_the_delivery_mark_is_unique_per_process_and_item(engine, process, other_process):
    with engine.begin() as conn:
        _delivery(conn, process)
        _delivery(conn, process, "PORTARIA_ULTIMA_PROGRESSAO")
        _delivery(conn, other_process)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        _delivery(conn, process)


@pytest.fixture
def other_process(uow_factory, process):
    other = dataclasses.replace(process, id=uuid.uuid4())
    with uow_factory() as uow:
        uow.processes.add(other)
        uow.commit()
    return other


def _generation(conn, process, user_id, kind, state="GERANDO", version=None):
    conn.execute(
        text(
            "INSERT INTO generated_documents (id, process_id, kind, state, version_number, "
            "requested_by) VALUES (:id, :p, :kind, :state, :v, :u)"
        ),
        {
            "id": uuid.uuid4(),
            "p": process.id,
            "kind": kind,
            "state": state,
            "v": version,
            "u": user_id,
        },
    )


def test_a_generated_document_can_be_a_parecer_or_a_requerimento(engine, process, base):  # noqa: F811
    user_id = base["admin"].id
    with engine.begin() as conn:
        _generation(conn, process, user_id, "PARECER", "PRONTO", 1)
        _generation(conn, process, user_id, "REQUERIMENTO", "PRONTO", 1)

    with engine.connect() as conn:
        kinds = set(conn.execute(text("SELECT kind FROM generated_documents")).scalars())
    assert kinds == {"PARECER", "REQUERIMENTO"}


@pytest.mark.parametrize("kind", ["PARECER", "REQUERIMENTO"])
def test_the_new_kinds_keep_one_generating_row(engine, process, base, kind):  # noqa: F811
    user_id = base["admin"].id
    with pytest.raises(IntegrityError, match="uq_generated_documents_generating"):
        with engine.begin() as conn:
            _generation(conn, process, user_id, kind)
            _generation(conn, process, user_id, kind)


def test_downgrade_to_0010_removes_tables_and_enums_and_keeps_the_kind_values(migrated_url):
    cfg = alembic_config(migrated_url)
    try:
        command.downgrade(cfg, "0010")
        tables, enums, kind_values, indexes = _snapshot(migrated_url)
        assert not TABLES & tables
        assert not ENUMS & enums
        assert PENDING_INDEX not in indexes
        # PostgreSQL cannot drop a value from an enum (as in 0007): the two stay, unused.
        assert kind_values == ["TABELA", "RELATORIO", "COMPROVANTE", "REQUERIMENTO", "PARECER"]
        assert {"norms", "generated_documents", "report_drafts"} <= tables
    finally:
        command.upgrade(cfg, "head")

    tables, enums, kind_values, indexes = _snapshot(migrated_url)
    assert TABLES <= tables
    assert ENUMS <= enums
    assert PENDING_INDEX in indexes
    assert kind_values == ["TABELA", "RELATORIO", "COMPROVANTE", "REQUERIMENTO", "PARECER"]
