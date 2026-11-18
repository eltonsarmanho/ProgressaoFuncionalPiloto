"""REL-13, ARR-07, DEL-05, DEL-06: wording jobs, drafts, layouts and the purge mark (migration
0006) on real PostgreSQL."""

import json
import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic_config
from tests.integration.documents.test_schema import insert_document

DRAFT_TABLES = {"report_wording_jobs", "report_drafts", "comprovante_layouts"}


def insert_wording_job(conn, process, user_id, section="1.1", state="GERANDO", warnings=None):
    job_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO report_wording_jobs (id, process_id, section_key, state, requested_by, "
            "warnings) VALUES (:id, :process, :section, :state, :user, CAST(:warnings AS jsonb))"
        ),
        {
            "id": job_id,
            "process": process.id,
            "section": section,
            "state": state,
            "user": user_id,
            "warnings": None if warnings is None else json.dumps(warnings),
        },
    )
    return job_id


def insert_draft(conn, process, user_id, content=None) -> uuid.UUID:
    draft_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO report_drafts (id, process_id, template_id, template_version, content, "
            "version, created_by, updated_by) VALUES (:id, :process, 'ufpa-cppd', 1, "
            "CAST(:content AS jsonb), 1, :user, :user)"
        ),
        {
            "id": draft_id,
            "process": process.id,
            "content": json.dumps(content or {"sections": []}),
            "user": user_id,
        },
    )
    return draft_id


def insert_layout(conn, process, user_id, content=None) -> uuid.UUID:
    layout_id = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO comprovante_layouts (id, process_id, content, version, updated_by) "
            "VALUES (:id, :process, CAST(:content AS jsonb), 1, :user)"
        ),
        {
            "id": layout_id,
            "process": process.id,
            "content": json.dumps(content or {"activities": [], "base_evidence_keys": []}),
            "user": user_id,
        },
    )
    return layout_id


def _snapshot(url: str):
    eng = create_engine(url)
    try:
        insp = inspect(eng)
        document_columns = {c["name"] for c in insp.get_columns("documents")}
        criteria_columns = {c["name"] for c in insp.get_columns("scoring_criteria")}
        with eng.connect() as conn:
            enums = set(
                conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'")).scalars()
            )
        return set(insp.get_table_names()), document_columns, criteria_columns, enums
    finally:
        eng.dispose()


def test_a_second_wording_job_generating_the_same_section_is_refused(engine, process, base):
    user_id = base["admin"].id
    with pytest.raises(IntegrityError, match="uq_report_wording_jobs_generating"):
        with engine.begin() as conn:
            insert_wording_job(conn, process, user_id, "1.1")
            insert_wording_job(conn, process, user_id, "1.1")


def test_different_sections_are_worded_at_the_same_time(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_wording_job(conn, process, user_id, "1.1")
        insert_wording_job(conn, process, user_id, "1.2")
        insert_wording_job(conn, process, user_id, "1.3")

    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM report_wording_jobs")).scalar_one()
    assert count == 3


def test_the_same_section_may_be_worded_again_after_the_job_finished(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_wording_job(conn, process, user_id, "1.1", "PRONTO")
        insert_wording_job(conn, process, user_id, "1.1", "FALHOU")
        insert_wording_job(conn, process, user_id, "1.1", "GERANDO")


def test_the_same_section_is_worded_at_the_same_time_in_different_processes(
    engine, process, other_process, base
):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_wording_job(conn, process, user_id, "1.1")
        insert_wording_job(conn, other_process, user_id, "1.1")


def test_a_wording_job_keeps_its_warnings_as_json_with_code_and_reason(engine, process, base):
    user_id = base["admin"].id
    warnings = [
        {"code": "REDACAO_REJEITADA", "reason": "NUMERO"},
        {"code": "REDACAO_INDISPONIVEL"},
    ]
    with engine.begin() as conn:
        insert_wording_job(conn, process, user_id, "1.1", "PRONTO", warnings)

    with engine.connect() as conn:
        stored = conn.execute(text("SELECT warnings FROM report_wording_jobs")).scalar_one()
    assert stored == warnings


def test_an_interrupted_wording_job_keeps_its_error_code(engine, process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        job_id = insert_wording_job(conn, process, user_id, "1.1")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE report_wording_jobs SET state = 'FALHOU', error_code = 'INTERROMPIDA', "
                "finished_at = now() WHERE id = :id"
            ),
            {"id": job_id},
        )

    with engine.connect() as conn:
        row = conn.execute(text("SELECT state, error_code FROM report_wording_jobs")).one()
    assert (row.state, row.error_code) == ("FALHOU", "INTERROMPIDA")


def test_a_process_has_at_most_one_report_draft(engine, process, other_process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_draft(conn, process, user_id)
        insert_draft(conn, other_process, user_id)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_draft(conn, process, user_id)


def test_a_report_draft_keeps_its_content_and_version(engine, process, base):
    user_id = base["admin"].id
    content = {
        "sections": [
            {
                "key": "1.1",
                "title": "Ensino",
                "free_text": "",
                "warnings": [{"code": "REDACAO_REJEITADA", "reason": "NUMERO"}],
                "entries": [
                    {"activity_id": str(uuid.uuid4()), "text": "x", "source": "IA", "warnings": []}
                ],
            }
        ]
    }
    with engine.begin() as conn:
        insert_draft(conn, process, user_id, content)

    with engine.connect() as conn:
        row = conn.execute(text("SELECT content, version, template_id FROM report_drafts")).one()
    assert row.content == content
    assert (row.version, row.template_id) == (1, "ufpa-cppd")


def test_a_process_has_at_most_one_comprovante_layout(engine, process, other_process, base):
    user_id = base["admin"].id
    with engine.begin() as conn:
        insert_layout(conn, process, user_id)
        insert_layout(conn, other_process, user_id)

    with pytest.raises(IntegrityError), engine.begin() as conn:
        insert_layout(conn, process, user_id)


def test_a_comprovante_layout_keeps_its_content_and_version(engine, process, base):
    user_id = base["admin"].id
    content = {
        "activities": [
            {
                "activity_id": str(uuid.uuid4()),
                "pages": [
                    {"document_id": str(uuid.uuid4()), "page": 2, "repeat_justification": None}
                ],
            }
        ],
        "base_evidence_keys": ["a:1"],
    }
    with engine.begin() as conn:
        insert_layout(conn, process, user_id, content)

    with engine.connect() as conn:
        row = conn.execute(text("SELECT content, version FROM comprovante_layouts")).one()
    assert row.content == content
    assert row.version == 1


def test_documents_accept_a_null_or_a_date_in_file_deleted_at(engine, process, base):
    user_id = base["admin"].id
    deleted_at = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
    with engine.begin() as conn:
        kept = insert_document(conn, process, user_id)
        purged = insert_document(conn, process, user_id)
        conn.execute(
            text("UPDATE documents SET file_deleted_at = :at WHERE id = :id"),
            {"at": deleted_at, "id": purged},
        )

    with engine.connect() as conn:
        rows = dict(conn.execute(text("SELECT id, file_deleted_at FROM documents")).all())
    assert rows[kept] is None
    assert rows[purged] == deleted_at


def test_downgrade_removes_everything_but_keeps_0004_and_the_documents(
    migrated_url, engine, process, base
):
    cfg = alembic_config(migrated_url)
    with engine.begin() as conn:
        document_id = insert_document(conn, process, base["admin"].id)

    tables, document_columns, _, enums = _snapshot(migrated_url)
    assert DRAFT_TABLES <= tables
    assert "file_deleted_at" in document_columns

    try:
        command.downgrade(cfg, "0005")
        tables, document_columns, criteria_columns, enums = _snapshot(migrated_url)
        assert not DRAFT_TABLES & tables
        assert "file_deleted_at" not in document_columns
        assert "min_hours" in criteria_columns  # migration 0004 stays
        assert "generated_state" not in enums
    finally:
        command.upgrade(cfg, "head")

    tables, document_columns, _, _ = _snapshot(migrated_url)
    assert DRAFT_TABLES <= tables
    # The document that existed before the upgrade survives with the new column empty.
    with engine.connect() as conn:
        deleted_at = conn.execute(
            text("SELECT file_deleted_at FROM documents WHERE id = :id"), {"id": document_id}
        ).one()
    assert deleted_at.file_deleted_at is None
