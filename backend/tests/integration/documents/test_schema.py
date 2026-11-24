"""DOC-01, DOC-07, PIPE-01, EXT-13, VINC-02: document schema (migration 0003) on real PostgreSQL."""

import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.test_scoring_repositories import make_activity

NEW_TABLES = {
    "documents",
    "extraction_runs",
    "document_pages",
    "processing_jobs",
    "activity_evidences",
}
NEW_ENUMS = {"document_status", "extraction_run_status", "text_method", "job_status"}


def insert_document(conn, process, user_id, sha256=None) -> uuid.UUID:
    document_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO documents (id, process_id, original_name, internal_name, mime, "
            "size_bytes, sha256, page_count, status, uploaded_by, version) VALUES "
            "(:id, :process, 'a.pdf', :internal, 'application/pdf', 10, :sha, 1, 'PENDENTE', "
            ":user, 1)"
        ),
        {
            "id": document_id,
            "process": process.id,
            "internal": f"{uuid.uuid4().hex}.pdf",
            "sha": sha256 or uuid.uuid4().hex + uuid.uuid4().hex,
            "user": user_id,
        },
    )
    return document_id


def insert_run(conn, document_id) -> uuid.UUID:
    run_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO extraction_runs (id, document_id, status, model, duration_ms, raw_json, "
            "warnings) VALUES (:id, :doc, 'ATIVA', 'modelo-a', 100, '{\"a\": 1}', '[\"X\"]')"
        ),
        {"id": run_id, "doc": document_id},
    )
    return run_id


def insert_job(conn, document_id, status) -> None:
    conn.execute(
        text(
            "INSERT INTO processing_jobs (id, document_id, status, attempts) "
            "VALUES (:id, :doc, :status, 0)"
        ),
        {"id": uuid.uuid4(), "doc": document_id, "status": status},
    )


def insert_page(conn, document_id, run_id, number) -> None:
    conn.execute(
        text(
            "INSERT INTO document_pages (id, document_id, run_id, page_number, method, "
            "char_count, text) VALUES (:id, :doc, :run, :n, 'TEXTO', 3, 'abc')"
        ),
        {"id": uuid.uuid4(), "doc": document_id, "run": run_id, "n": number},
    )


def insert_evidence(conn, activity_id, document_id, user_id, page) -> None:
    conn.execute(
        text(
            "INSERT INTO activity_evidences (id, activity_id, document_id, page_number, excerpt, "
            "created_by) VALUES (:id, :act, :doc, :page, 'trecho', :user)"
        ),
        {"id": uuid.uuid4(), "act": activity_id, "doc": document_id, "page": page, "user": user_id},
    )


def _snapshot(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        columns = {c["name"] for c in insp.get_columns("activities")}
        with eng.connect() as conn:
            enums = set(
                conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars()
            )
            functions = set(conn.execute(text("SELECT proname FROM pg_proc")).scalars())
        return set(insp.get_table_names()), columns, enums, functions
    finally:
        eng.dispose()


def test_downgrade_one_revision_and_upgrade_again(migrated_url):
    cfg = alembic_config(migrated_url)
    tables, columns, enums, functions = _snapshot(migrated_url)
    assert NEW_TABLES <= tables
    assert "extraction_run_id" in columns
    assert NEW_ENUMS <= enums

    command.downgrade(cfg, "0002")
    tables, columns, enums, functions = _snapshot(migrated_url)
    assert not NEW_TABLES & tables
    assert "extraction_run_id" not in columns
    assert not NEW_ENUMS & enums
    assert "extraction_runs_content_immutable" not in functions
    assert "scoring_tables" in tables

    command.upgrade(cfg, "head")
    tables, columns, enums, functions = _snapshot(migrated_url)
    assert NEW_TABLES <= tables
    assert "extraction_run_id" in columns
    assert NEW_ENUMS <= enums
    assert "extraction_runs_content_immutable" in functions


def test_same_hash_twice_in_one_process_is_refused(engine, process, base):
    user_id = base["admin"].id
    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_document(conn, process, user_id, sha256="a" * 64)
        insert_document(conn, process, user_id, sha256="a" * 64)


def test_same_hash_in_different_processes_is_accepted(engine, process, other_process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_document(conn, process, user_id, sha256="b" * 64)
        insert_document(conn, other_process, user_id, sha256="b" * 64)


def test_activity_document_page_link_is_unique(engine, uow_factory, process, base):
    user_id = base["admin"].id
    activity = make_activity(process, base)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    with engine.begin() as conn:
        document_id = insert_document(conn, process, user_id)
        insert_evidence(conn, activity.id, document_id, user_id, page=1)
        insert_evidence(conn, activity.id, document_id, user_id, page=2)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_evidence(conn, activity.id, document_id, user_id, page=1)


def test_page_number_is_unique_per_run(engine, process, base):
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)
        run_id = insert_run(conn, document_id)
        insert_page(conn, document_id, run_id, 1)
    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_page(conn, document_id, run_id, 1)


@pytest.mark.parametrize("active", ["PENDENTE", "PROCESSANDO"])
def test_only_one_active_job_per_document(engine, process, base, active):
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)
        insert_job(conn, document_id, active)
    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_job(conn, document_id, "PENDENTE")


def test_finished_jobs_do_not_block_a_new_active_job(engine, process, base):
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)
        insert_job(conn, document_id, "CONCLUIDA")
        insert_job(conn, document_id, "FALHOU")
        insert_job(conn, document_id, "PENDENTE")


def test_active_jobs_of_different_documents_coexist(engine, process, base):
    with engine.begin() as conn:
        first = insert_document(conn, process, base["admin"].id)
        second = insert_document(conn, process, base["admin"].id)
        insert_job(conn, first, "PENDENTE")
        insert_job(conn, second, "PENDENTE")


def test_run_status_can_change_and_the_content_stays(engine, process, base):
    with engine.begin() as conn:
        run_id = insert_run(conn, insert_document(conn, process, base["admin"].id))
        conn.execute(
            text("UPDATE extraction_runs SET status = 'SUBSTITUIDA' WHERE id = :id"),
            {"id": run_id},
        )
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, model, duration_ms, raw_json, warnings FROM extraction_runs")
        ).one()
    assert row.status == "SUBSTITUIDA"
    assert (row.model, row.duration_ms) == ("modelo-a", 100)
    assert row.raw_json == {"a": 1}
    assert row.warnings == ["X"]


@pytest.mark.parametrize(
    "assignment",
    [
        "raw_json = '{\"a\": 2}'",
        "model = 'outro-modelo'",
        "duration_ms = 999",
        "warnings = '[]'",
        "created_at = now() + interval '1 day'",
        "document_id = (SELECT id FROM documents WHERE id <> extraction_runs.document_id LIMIT 1)",
        "status = 'SUBSTITUIDA', raw_json = '{\"a\": 2}'",
    ],
)
def test_run_content_cannot_be_updated(engine, process, base, assignment):
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)
        insert_document(conn, process, base["admin"].id)
        run_id = insert_run(conn, document_id)

    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as conn:
        conn.execute(
            text(f"UPDATE extraction_runs SET {assignment} WHERE id = :id"), {"id": run_id}
        )

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, model, duration_ms, raw_json, warnings FROM extraction_runs")
        ).one()
    assert row.status == "ATIVA"
    assert (row.model, row.duration_ms, row.raw_json, row.warnings) == (
        "modelo-a",
        100,
        {"a": 1},
        ["X"],
    )


def test_deleting_a_document_removes_its_text_and_links_but_keeps_the_activity(
    engine, uow_factory, process, base
):
    user_id = base["admin"].id
    activity = make_activity(process, base)
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    with engine.begin() as conn:
        document_id = insert_document(conn, process, user_id)
        run_id = insert_run(conn, document_id)
        insert_page(conn, document_id, run_id, 1)
        insert_job(conn, document_id, "CONCLUIDA")
        insert_evidence(conn, activity.id, document_id, user_id, page=1)
        conn.execute(
            text("UPDATE activities SET extraction_run_id = :run WHERE id = :id"),
            {"run": run_id, "id": activity.id},
        )

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document_id})

    with engine.connect() as conn:
        counts = {
            table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in NEW_TABLES
        }
        run = conn.execute(
            text("SELECT extraction_run_id FROM activities WHERE id = :id"), {"id": activity.id}
        ).one()
    assert counts == {table: 0 for table in NEW_TABLES}
    assert run.extraction_run_id is None
