"""GP-DEL-03, GP-DEL-07, GP-DEL-09, GP-D2, GP-D4: the process purge repository on real
PostgreSQL."""

import uuid

import pytest
from sqlalchemy import event, text

from app.domain.entities.document import PageText, TextMethod
from app.domain.entities.generated import DocumentFormat, DocumentKind, GenerationState
from app.domain.errors import NotFound
from app.domain.repositories.ports import (
    BusyReason,
    JobStatus,
    ProcessDeletionCounts,
    StoredFile,
    StoredFileArea,
)
from app.infrastructure.database.repositories import (
    SqlGenerationRepository,
    SqlLayoutRepository,
    SqlProcessPurgeRepository,
    SqlReportDraftRepository,
    SqlWordingJobRepository,
)
from tests.integration.documents.factories import make_document, make_run
from tests.integration.documents.generated_support import (
    T0,
    make_draft,
    make_file,
    make_generation,
    make_layout,
    make_wording_job,
)
from tests.integration.documents.test_repositories import add_documents, make_evidence, make_job
from tests.integration.test_scoring_repositories import make_activity

# Tables whose rows belong to a process, directly or through documents/activities/generations.
PROCESS_TABLES = (
    "activities",
    "activity_candidates",
    "activity_evidences",
    "documents",
    "extraction_runs",
    "document_pages",
    "processing_jobs",
    "generated_documents",
    "generated_files",
    "report_wording_jobs",
    "report_drafts",
    "comprovante_layouts",
)
HANDLED_DIRECT = {
    "activities",
    "documents",
    "generated_documents",
    "report_wording_jobs",
    "report_drafts",
    "comprovante_layouts",
}


def populate(uow_factory, process, base, session_factory, finished_job=True):
    """Every kind of dependent of the process; returns the stored files it owns."""
    user_id = base["admin"].id
    doc_a = make_document(process, user_id, original_name="a.pdf", page_count=2)
    doc_b = make_document(process, user_id, original_name="b.pdf", page_count=1)
    add_documents(uow_factory, doc_a, doc_b)
    run_a, run_b = make_run(doc_a.id), make_run(doc_b.id)
    activity = make_activity(process, base, title="Atividade 1")
    other_activity = make_activity(process, base, title="Atividade 2")
    with uow_factory() as uow:
        uow.activities.add(activity)
        uow.activities.add(other_activity)
        uow.extractions.add_run(run_a)
        uow.extractions.add_run(run_b)
        for doc, run, pages in ((doc_a, run_a, 2), (doc_b, run_b, 1)):
            uow.extractions.replace_pages(
                doc.id,
                [
                    PageText(doc.id, run.id, n, TextMethod.TEXTO, 5, None, f"texto {n}")
                    for n in range(1, pages + 1)
                ],
            )
        uow.evidences.add(make_evidence(activity, doc_a, user_id, page=1))
        uow.evidences.add(make_evidence(other_activity, doc_b, user_id, page=1))
        job = make_job(doc_a.id, status=JobStatus.CONCLUIDA if finished_job else JobStatus.PENDENTE)
        uow.jobs.add(job)
        uow.commit()
    files = [make_file(DocumentFormat.PDF), make_file(DocumentFormat.DOCX)]
    first = make_generation(process, user_id, DocumentKind.TABELA)
    second = make_generation(process, user_id, DocumentKind.RELATORIO)
    with session_factory() as session:
        generations = SqlGenerationRepository(session)
        generations.add(first)
        generations.add(second)
        generations.finish_ready(first.id, T0, files, {"total": "1"}, (), None)
        generations.finish_ready(second.id, T0, [make_file()], {"total": "1"}, (), None)
        wording = SqlWordingJobRepository(session)
        finished = make_wording_job(process, user_id, "1.1")
        wording.add(finished)
        wording.finish(finished.id, T0, GenerationState.PRONTO)
        SqlReportDraftRepository(session).create(make_draft(process), user_id, 0)
        SqlLayoutRepository(session).create(make_layout(process), user_id, 0)
        session.commit()
    return {"input": [doc_a, doc_b], "generated_names": {f.internal_name for f in files}}


def rows(engine, process_id=None):
    """Row count of every process table; with `process_id` only the rows of that process."""
    scoped = {
        "activities": "process_id = :p",
        "documents": "process_id = :p",
        "generated_documents": "process_id = :p",
        "report_wording_jobs": "process_id = :p",
        "report_drafts": "process_id = :p",
        "comprovante_layouts": "process_id = :p",
        "activity_candidates": "activity_id IN (SELECT id FROM activities WHERE process_id = :p)",
        "activity_evidences": "activity_id IN (SELECT id FROM activities WHERE process_id = :p)",
        "extraction_runs": "document_id IN (SELECT id FROM documents WHERE process_id = :p)",
        "document_pages": "document_id IN (SELECT id FROM documents WHERE process_id = :p)",
        "processing_jobs": "document_id IN (SELECT id FROM documents WHERE process_id = :p)",
        "generated_files": (
            "generated_document_id IN (SELECT id FROM generated_documents WHERE process_id = :p)"
        ),
    }
    out = {}
    with engine.connect() as conn:
        for table in PROCESS_TABLES:
            where = f" WHERE {scoped[table]}" if process_id else ""
            out[table] = conn.execute(
                text(f"SELECT count(*) FROM {table}{where}"), {"p": process_id}
            ).scalar_one()
    return out


def purge(session_factory, process_id):
    with session_factory() as session:
        stored = SqlProcessPurgeRepository(session).delete_all(process_id)
        session.commit()
    return stored


def test_delete_all_leaves_no_row_of_the_process_in_any_dependent_table(
    engine, uow_factory, session_factory, process, base
):
    populate(uow_factory, process, base, session_factory)
    assert all(count > 0 for count in rows(engine, process.id).values())

    purge(session_factory, process.id)

    assert rows(engine) == dict.fromkeys(PROCESS_TABLES, 0)
    with engine.connect() as conn:
        left = conn.execute(
            text("SELECT count(*) FROM functional_processes WHERE id = :p"), {"p": process.id}
        ).scalar_one()
    assert left == 0


def test_a_process_with_a_merged_activity_is_purged_without_breaking_the_merge_keys(
    engine, uow_factory, session_factory, process, base
):
    """DUP-02: merged_into_id and origin_activity_id are NO ACTION and do not block the DELETE."""
    populate(uow_factory, process, base, session_factory)
    with engine.begin() as conn:
        kept, merged = (
            conn.execute(
                text("SELECT id FROM activities WHERE title = :t"), {"t": title}
            ).scalar_one()
            for title in ("Atividade 1", "Atividade 2")
        )
        conn.execute(
            text("UPDATE activities SET merged_into_id = :k WHERE id = :m"),
            {"k": kept, "m": merged},
        )
        conn.execute(
            text("UPDATE activity_evidences SET activity_id = :k, origin_activity_id = :m "
                 "WHERE activity_id = :m"),
            {"k": kept, "m": merged},
        )  # fmt: skip

    purge(session_factory, process.id)

    assert rows(engine) == dict.fromkeys(PROCESS_TABLES, 0)


def test_delete_all_touches_nothing_of_another_process(
    engine, uow_factory, session_factory, process, other_process, base
):
    populate(uow_factory, process, base, session_factory)
    populate(uow_factory, other_process, base, session_factory)
    before = rows(engine, other_process.id)

    purge(session_factory, process.id)

    assert rows(engine, other_process.id) == before
    assert all(count > 0 for count in before.values())


def test_delete_all_returns_the_files_of_inputs_and_generated_documents(
    engine, uow_factory, session_factory, process, base
):
    world = populate(uow_factory, process, base, session_factory)
    with engine.connect() as conn:
        generated = set(conn.execute(text("SELECT internal_name FROM generated_files")).scalars())

    stored = purge(session_factory, process.id)

    inputs = {f.internal_name for f in stored if f.area is StoredFileArea.INPUT}
    outputs = {f.internal_name for f in stored if f.area is StoredFileArea.GENERATED}
    assert inputs == {d.internal_name for d in world["input"]}
    assert outputs == generated
    assert len(stored) == len(inputs) + len(outputs)
    assert {f.process_id for f in stored} == {process.id}
    assert all(isinstance(f, StoredFile) for f in stored)


def test_a_document_whose_file_the_conclusion_removed_returns_no_file(
    uow_factory, session_factory, process, base
):
    user_id = base["admin"].id
    kept = make_document(process, user_id)
    gone = make_document(process, user_id)
    add_documents(uow_factory, kept, gone)
    with uow_factory() as uow:
        uow.documents.mark_file_deleted(gone.id, T0)
        uow.commit()

    stored = purge(session_factory, process.id)

    assert [f.internal_name for f in stored] == [kept.internal_name]


def test_a_process_without_any_dependent_is_deleted_and_returns_no_file(
    engine, session_factory, process
):
    assert purge(session_factory, process.id) == []

    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM functional_processes")).scalar_one() == 0


def test_an_unknown_process_is_not_found(session_factory):
    with pytest.raises(NotFound), session_factory() as session:
        SqlProcessPurgeRepository(session).delete_all(uuid.uuid4())


def test_a_failure_in_the_middle_deletes_nothing(
    engine, uow_factory, session_factory, process, base
):
    populate(uow_factory, process, base, session_factory)
    before = rows(engine)

    def fail_on_documents(conn, cursor, statement, *args):
        if statement.lstrip().upper().startswith("DELETE FROM DOCUMENTS"):
            raise RuntimeError("forced failure")

    event.listen(engine, "before_cursor_execute", fail_on_documents)
    try:
        with pytest.raises(RuntimeError, match="forced failure"), session_factory() as session:
            SqlProcessPurgeRepository(session).delete_all(process.id)
            session.commit()
    finally:
        event.remove(engine, "before_cursor_execute", fail_on_documents)

    assert rows(engine) == before
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM functional_processes")).scalar_one() == 1


def test_delete_all_does_not_commit_by_itself(engine, uow_factory, session_factory, process, base):
    populate(uow_factory, process, base, session_factory)
    before = rows(engine)

    with session_factory() as session:
        SqlProcessPurgeRepository(session).delete_all(process.id)
        session.rollback()

    assert rows(engine) == before


def test_every_foreign_key_to_the_process_is_handled(engine):
    """A new table that points to a process must be handled by the purge (GP-D2)."""
    with engine.connect() as conn:
        direct = set(
            conn.execute(
                text(
                    "SELECT conrelid::regclass::text FROM pg_constraint "
                    "WHERE contype = 'f' AND confrelid = 'functional_processes'::regclass"
                )
            ).scalars()
        )
        # Dependents of documents and activities must go by cascade (or SET NULL) on their own;
        # the generated files are deleted explicitly, with their document.
        below = {
            (row.child, row.parent, row.action)
            for row in conn.execute(
                text(
                    "SELECT conrelid::regclass::text AS child, confrelid::regclass::text AS parent,"
                    " confdeltype AS action FROM pg_constraint WHERE contype = 'f' AND "
                    "confrelid IN ('documents'::regclass, 'activities'::regclass, "
                    "'generated_documents'::regclass)"
                )
            )
        }

    assert direct == HANDLED_DIRECT
    # DUP-02 (migration 0008): merged_into_id and origin_activity_id point to activities with
    # NO ACTION; the purge deletes every activity of the process in one statement, so both are
    # satisfied at its end (test_a_process_with_a_merged_activity_is_purged_without_...).
    explicit = {
        ("generated_files", "generated_documents", "a"),
        ("activities", "activities", "a"),
        ("activity_evidences", "activities", "a"),
    }
    assert {t for t in below if t[2] not in ("c", "n")} == explicit


def test_busy_reasons_is_empty_for_a_quiet_process(
    uow_factory, session_factory, process, base
):
    populate(uow_factory, process, base, session_factory)

    with session_factory() as session:
        assert SqlProcessPurgeRepository(session).busy_reasons(process.id) == []


@pytest.mark.parametrize("status", [JobStatus.PENDENTE, JobStatus.PROCESSANDO])
def test_a_queued_or_running_extraction_makes_the_process_busy(
    uow_factory, session_factory, process, base, status
):
    document = make_document(process, base["admin"].id)
    add_documents(uow_factory, document)
    with uow_factory() as uow:
        uow.jobs.add(make_job(document.id, status=status))
        uow.commit()

    with session_factory() as session:
        reasons = SqlProcessPurgeRepository(session).busy_reasons(process.id)

    assert reasons == [BusyReason.DOCUMENTO_PROCESSANDO]


def test_a_generation_in_progress_makes_the_process_busy(
    session_factory, process, base
):
    with session_factory() as session:
        SqlGenerationRepository(session).add(
            make_generation(process, base["admin"].id, DocumentKind.COMPROVANTE)
        )
        session.commit()

    with session_factory() as session:
        reasons = SqlProcessPurgeRepository(session).busy_reasons(process.id)

    assert reasons == [BusyReason.GERACAO_EM_ANDAMENTO]


def test_a_wording_in_progress_makes_the_process_busy(session_factory, process, base):
    with session_factory() as session:
        SqlWordingJobRepository(session).add(make_wording_job(process, base["admin"].id))
        session.commit()

    with session_factory() as session:
        reasons = SqlProcessPurgeRepository(session).busy_reasons(process.id)

    assert reasons == [BusyReason.REDACAO_EM_ANDAMENTO]


def test_the_work_of_another_process_does_not_make_this_one_busy(
    uow_factory, session_factory, process, other_process, base
):
    document = make_document(other_process, base["admin"].id)
    add_documents(uow_factory, document)
    with uow_factory() as uow:
        uow.jobs.add(make_job(document.id, status=JobStatus.PROCESSANDO))
        uow.commit()

    with session_factory() as session:
        assert SqlProcessPurgeRepository(session).busy_reasons(process.id) == []
        assert SqlProcessPurgeRepository(session).busy_reasons(other_process.id) == [
            BusyReason.DOCUMENTO_PROCESSANDO
        ]


def test_every_busy_reason_is_reported_together(uow_factory, session_factory, process, base):
    document = make_document(process, base["admin"].id)
    add_documents(uow_factory, document)
    with uow_factory() as uow:
        uow.jobs.add(make_job(document.id, status=JobStatus.PROCESSANDO))
        uow.commit()
    with session_factory() as session:
        SqlGenerationRepository(session).add(make_generation(process, base["admin"].id))
        SqlWordingJobRepository(session).add(make_wording_job(process, base["admin"].id))
        session.commit()

    with session_factory() as session:
        reasons = SqlProcessPurgeRepository(session).busy_reasons(process.id)

    assert set(reasons) == set(BusyReason)


def test_counts_reports_documents_activities_and_generated_documents(
    uow_factory, session_factory, process, other_process, base
):
    populate(uow_factory, process, base, session_factory)
    populate(uow_factory, other_process, base, session_factory)

    with session_factory() as session:
        counts = SqlProcessPurgeRepository(session).counts(process.id)

    assert counts == ProcessDeletionCounts(documents=2, activities=2, generated_documents=2)
