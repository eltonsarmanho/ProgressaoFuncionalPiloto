"""VER-01, VER-04: generated documents schema and immutability triggers (migration 0006) on real
PostgreSQL."""

import json
import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.conftest import alembic_config

GENERATED_TABLES = {"generated_documents", "generated_files"}
GENERATED_ENUMS = {"generated_kind", "generated_state", "generated_format"}
GENERATED_FUNCTIONS = {"generated_documents_immutable", "generated_files_immutable"}


def insert_generation(
    conn, process, user_id, kind="TABELA", state="GERANDO", version_number=None
) -> uuid.UUID:
    generation_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO generated_documents (id, process_id, kind, state, version_number, "
            "requested_by) VALUES (:id, :process, :kind, :state, :version, :user)"
        ),
        {
            "id": generation_id,
            "process": process.id,
            "kind": kind,
            "state": state,
            "version": version_number,
            "user": user_id,
        },
    )
    return generation_id


def insert_file(conn, generation_id, fmt="PDF", internal_name=None) -> uuid.UUID:
    file_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO generated_files (id, generated_document_id, format, internal_name, "
            "sha256, size_bytes) VALUES (:id, :gen, :fmt, :name, :sha, 1024)"
        ),
        {
            "id": file_id,
            "gen": generation_id,
            "fmt": fmt,
            "name": internal_name or f"{uuid.uuid4().hex}.{fmt.lower()}",
            "sha": "c" * 64,
        },
    )
    return file_id


def _snapshot(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        scoring_columns = {c["name"] for c in insp.get_columns("scoring_criteria")}
        activity_columns = {c["name"] for c in insp.get_columns("activities")}
        with eng.connect() as conn:
            enums = set(
                conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars()
            )
            functions = set(conn.execute(text("SELECT proname FROM pg_proc")).scalars())
        return set(insp.get_table_names()), enums, functions, scoring_columns, activity_columns
    finally:
        eng.dispose()


def test_downgrade_to_0005_removes_the_tables_and_keeps_the_earlier_schema(migrated_url):
    cfg = alembic_config(migrated_url)
    tables, enums, functions, _, _ = _snapshot(migrated_url)
    assert GENERATED_TABLES <= tables
    assert GENERATED_ENUMS <= enums
    assert GENERATED_FUNCTIONS <= functions

    try:
        command.downgrade(cfg, "0005")
        tables, enums, functions, scoring_columns, activity_columns = _snapshot(migrated_url)
        assert not GENERATED_TABLES & tables
        assert not GENERATED_ENUMS & enums
        assert not GENERATED_FUNCTIONS & functions
        # 0004 (min_hours), 0005 (unit_points_override) and 0003 (documents) stay intact.
        assert "min_hours" in scoring_columns
        assert "unit_points_override" in activity_columns
        assert "documents" in tables
    finally:
        command.upgrade(cfg, "head")

    tables, enums, functions, _, _ = _snapshot(migrated_url)
    assert GENERATED_TABLES <= tables
    assert GENERATED_ENUMS <= enums
    assert GENERATED_FUNCTIONS <= functions


def test_two_generating_rows_of_the_same_process_and_kind_are_refused(engine, process, base):
    user_id = base["admin"].id
    with pytest.raises(IntegrityError, match="uq_generated_documents_generating"):
        with engine.begin() as conn:
            insert_generation(conn, process, user_id, "TABELA")
            insert_generation(conn, process, user_id, "TABELA")


def test_different_kinds_of_the_same_process_generate_at_the_same_time(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        for kind in ("TABELA", "RELATORIO", "COMPROVANTE"):
            insert_generation(conn, process, user_id, kind)

    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM generated_documents WHERE state = 'GERANDO'")
        ).scalar_one()
    assert count == 3


def test_the_same_kind_generates_at_the_same_time_in_different_processes(
    engine, process, other_process, base
):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_generation(conn, process, user_id, "TABELA")
        insert_generation(conn, other_process, user_id, "TABELA")


def test_a_new_generation_may_start_after_the_previous_one_finished(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
        insert_generation(conn, process, user_id, "TABELA", "FALHOU")
        insert_generation(conn, process, user_id, "TABELA", "GERANDO")


def test_the_version_number_is_unique_per_process_and_kind(engine, process, base):
    user_id = base["admin"].id
    with pytest.raises(IntegrityError, match="uq_generated_documents_version"):
        with engine.begin() as conn:
            insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
            insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)


def test_the_same_version_number_is_accepted_for_another_kind(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
        insert_generation(conn, process, user_id, "RELATORIO", "PRONTO", 1)


def test_a_generating_row_goes_to_ready_with_its_version_snapshot_and_alerts(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE generated_documents SET state = 'PRONTO', version_number = 1, "
                "finished_at = now(), snapshot = CAST(:snap AS jsonb), "
                "alerts = CAST(:alerts AS jsonb), plan_hash = :hash WHERE id = :id"
            ),
            {
                "id": generation_id,
                "snap": json.dumps({"total": "10.00"}),
                "alerts": json.dumps([{"code": "ATIVIDADE_SEM_COMPROVANTE", "message": ""}]),
                "hash": "d" * 64,
            },
        )

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT state, version_number, snapshot, plan_hash FROM generated_documents")
        ).one()
    assert (row.state, row.version_number) == ("PRONTO", 1)
    assert row.snapshot == {"total": "10.00"}
    assert row.plan_hash == "d" * 64


def test_a_generating_row_goes_to_failed_with_a_code(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE generated_documents SET state = 'FALHOU', error_code = 'ERRO_INTERNO', "
                "finished_at = now() WHERE id = :id"
            ),
            {"id": generation_id},
        )

    with engine.connect() as conn:
        row = conn.execute(text("SELECT state, error_code FROM generated_documents")).one()
    assert (row.state, row.error_code) == ("FALHOU", "ERRO_INTERNO")


@pytest.mark.parametrize(
    ("state", "version"), [("PRONTO", 1), ("FALHOU", None)], ids=["ready", "failed"]
)
def test_a_finished_generation_cannot_be_updated(engine, process, base, state, version):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", state, version)

    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(
            text("UPDATE generated_documents SET error_message = 'x' WHERE id = :id"),
            {"id": generation_id},
        )

    with engine.connect() as conn:
        message = conn.execute(
            text("SELECT error_message FROM generated_documents WHERE id = :id"),
            {"id": generation_id},
        ).scalar_one()
    assert message is None


def test_a_finished_generation_cannot_change_state_back(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", "FALHOU")

    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(
            text("UPDATE generated_documents SET state = 'GERANDO' WHERE id = :id"),
            {"id": generation_id},
        )


@pytest.mark.parametrize(
    ("state", "version"),
    [("GERANDO", None), ("PRONTO", 1), ("FALHOU", None)],
    ids=["generating", "ready", "failed"],
)
def test_a_generated_document_cannot_be_deleted(engine, process, base, state, version):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", state, version)

    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_documents WHERE id = :id"), {"id": generation_id})

    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM generated_documents")).scalar_one()
    assert count == 1


def test_a_generated_file_cannot_be_updated(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
        file_id = insert_file(conn, generation_id)

    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(
            text("UPDATE generated_files SET size_bytes = 1 WHERE id = :id"), {"id": file_id}
        )

    with engine.connect() as conn:
        size = conn.execute(
            text("SELECT size_bytes FROM generated_files WHERE id = :id"), {"id": file_id}
        ).scalar_one()
    assert size == 1024


def test_a_generated_file_cannot_be_deleted(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
        file_id = insert_file(conn, generation_id)

    with pytest.raises(DBAPIError, match="cannot be deleted"), engine.begin() as conn:
        conn.execute(text("DELETE FROM generated_files WHERE id = :id"), {"id": file_id})

    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM generated_files")).scalar_one()
    assert count == 1


def test_a_version_holds_one_file_per_format_and_the_internal_name_is_unique(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        generation_id = insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)
        insert_file(conn, generation_id, "PDF")
        insert_file(conn, generation_id, "DOCX")

    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_file(conn, generation_id, "PDF")

    with pytest.raises(IntegrityError), engine.begin() as conn:
        other = insert_generation(conn, process, user_id, "RELATORIO", "PRONTO", 1)
        insert_file(conn, other, "PDF", internal_name="x.pdf")
        insert_file(conn, other, "DOCX", internal_name="x.pdf")


def test_a_process_with_generated_versions_cannot_be_deleted(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_generation(conn, process, user_id, "TABELA", "PRONTO", 1)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("DELETE FROM functional_processes WHERE id = :id"), {"id": process.id})
