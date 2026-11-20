"""DEL-02, DEL-05, DEL-06: purge methods and bulk reads on real PostgreSQL."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event

from app.domain.entities.document import DocumentStatus, PageText, TextMethod
from app.domain.errors import NotFound
from app.domain.repositories.ports import JobStatus
from tests.integration.documents.factories import make_document, make_run
from tests.integration.documents.test_repositories import add_documents, make_evidence, make_job
from tests.integration.test_scoring_repositories import make_activity

DELETED_AT = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)
AGAIN = DELETED_AT + timedelta(days=1)


def _page(document_id, run_id, number):
    text = f"texto da página {number}"
    return PageText(document_id, run_id, number, TextMethod.TEXTO, len(text), None, text)


@pytest.fixture
def purgeable(uow_factory, process, base):
    """A document with two pages and two links, another document with one page and one link."""
    user_id = base["admin"].id
    target = make_document(process, user_id, original_name="alvo.pdf", page_count=2)
    other = make_document(process, user_id, original_name="outro.pdf", page_count=1)
    add_documents(uow_factory, target, other)
    run_t, run_o = make_run(target.id), make_run(other.id)
    activities = [make_activity(process, base, title=f"Atividade {n}") for n in range(2)]
    links = [
        make_evidence(activities[0], target, user_id, page=1),
        make_evidence(activities[1], target, user_id, page=2),
        make_evidence(activities[0], other, user_id, page=1),
    ]
    with uow_factory() as uow:
        for activity in activities:
            uow.activities.add(activity)
        uow.extractions.add_run(run_t)
        uow.extractions.add_run(run_o)
        uow.extractions.replace_pages(
            target.id, [_page(target.id, run_t.id, 1), _page(target.id, run_t.id, 2)]
        )
        uow.extractions.replace_pages(other.id, [_page(other.id, run_o.id, 1)])
        for link in links:
            uow.evidences.add(link)
        uow.commit()
    return {"target": target, "other": other, "activities": activities, "links": links}


def purge(uow_factory, document_id, now=DELETED_AT):
    with uow_factory() as uow:
        uow.extractions.delete_pages(document_id)
        uow.evidences.clear_excerpts_for_document(document_id)
        uow.documents.mark_file_deleted(document_id, now)
        uow.commit()


def test_after_the_three_methods_the_document_keeps_metadata_and_the_mark_but_loses_text(
    uow_factory, purgeable
):
    target, other = purgeable["target"], purgeable["other"]

    purge(uow_factory, target.id)

    with uow_factory() as uow:
        loaded = uow.documents.get(target.id)
        assert loaded.file_deleted_at == DELETED_AT
        assert (loaded.original_name, loaded.sha256, loaded.size_bytes, loaded.page_count) == (
            target.original_name,
            target.sha256,
            target.size_bytes,
            target.page_count,
        )
        assert uow.extractions.list_pages(target.id) == []
        links = uow.evidences.list_for_document(target.id)
        assert sorted((link.document_id, link.page_number, link.excerpt) for link in links) == [
            (target.id, 1, ""),
            (target.id, 2, ""),
        ]
        # The other document is untouched.
        assert uow.documents.get(other.id).file_deleted_at is None
        assert len(uow.extractions.list_pages(other.id)) == 1
        assert uow.evidences.list_for_document(other.id)[0].excerpt != ""


def test_repeating_the_three_methods_is_harmless_and_keeps_the_first_mark(uow_factory, purgeable):
    target = purgeable["target"]
    purge(uow_factory, target.id)

    purge(uow_factory, target.id, AGAIN)

    with uow_factory() as uow:
        assert uow.documents.get(target.id).file_deleted_at == DELETED_AT
        assert uow.extractions.list_pages(target.id) == []
        assert [link.excerpt for link in uow.evidences.list_for_document(target.id)] == ["", ""]


def test_a_document_that_was_never_marked_has_no_file_deleted_at(uow_factory, purgeable):
    with uow_factory() as uow:
        assert uow.documents.get(purgeable["target"].id).file_deleted_at is None


def test_an_update_of_a_stale_copy_does_not_clear_the_mark(uow_factory, purgeable):
    target = purgeable["target"]
    with uow_factory() as uow:
        stale_copy = uow.documents.get(target.id)
    purge(uow_factory, target.id)

    with uow_factory() as uow:
        stale_copy.status = DocumentStatus.PROCESSADO
        uow.documents.update(stale_copy, expected_version=stale_copy.version)
        uow.commit()

    with uow_factory() as uow:
        assert uow.documents.get(target.id).file_deleted_at == DELETED_AT


def test_marking_an_unknown_document_is_not_found(uow_factory):
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.documents.mark_file_deleted(uuid.uuid4(), DELETED_AT)


def test_list_for_activities_returns_the_links_of_several_activities_in_one_query(
    uow_factory, engine, purgeable
):
    first, second = purgeable["activities"]
    unlinked = uuid.uuid4()
    statements = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        with uow_factory() as uow:
            links = uow.evidences.list_for_activities([first.id, second.id, unlinked])
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert {link.id for link in links} == {link.id for link in purgeable["links"]}
    assert {link.activity_id for link in links} == {first.id, second.id}
    assert len([s for s in statements if "activity_evidences" in s]) == 1


def test_list_for_activities_without_ids_returns_nothing(uow_factory, purgeable):
    with uow_factory() as uow:
        assert uow.evidences.list_for_activities([]) == []


def test_active_for_process_returns_only_pending_or_processing_jobs_of_its_documents(
    uow_factory, process, other_process, base
):
    user_id = base["admin"].id
    pending, running, done, failed = (make_document(process, user_id) for _ in range(4))
    elsewhere = make_document(other_process, user_id)
    add_documents(uow_factory, pending, running, done, failed, elsewhere)
    jobs = {
        "pending": make_job(pending.id),
        "running": make_job(running.id, status=JobStatus.PROCESSANDO),
        "done": make_job(done.id, status=JobStatus.CONCLUIDA),
        "failed": make_job(failed.id, status=JobStatus.FALHOU),
        "elsewhere": make_job(elsewhere.id),
    }
    with uow_factory() as uow:
        for job in jobs.values():
            uow.jobs.add(job)
        uow.commit()

    with uow_factory() as uow:
        active = uow.jobs.active_for_process(process.id)
        none = uow.jobs.active_for_process(uuid.uuid4())

    assert {job.id for job in active} == {jobs["pending"].id, jobs["running"].id}
    assert none == []
