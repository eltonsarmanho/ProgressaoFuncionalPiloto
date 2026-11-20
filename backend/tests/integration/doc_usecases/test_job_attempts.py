"""VER-04: a job that keeps killing the process ends FALHOU instead of being requeued forever."""

import pytest

from app.application.use_cases import document_processing
from app.application.use_cases.documents import DOCUMENT_ENTITY
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import DocumentStatus
from app.domain.repositories.ports import JobStatus
from tests.integration.doc_usecases.support import pdf
from tests.integration.doc_usecases.test_process_document import (
    Crash,
    Exploding,
    banca_payload,
    banca_text,
)
from tests.unit.application.analyzer_fakes import FakeAi, FakeTextExtractor, text_page

EXHAUSTED = "TENTATIVAS_ESGOTADAS"


def recover(docs, max_attempts=3):
    return document_processing.RecoverStuckJobs(
        docs.world.uow_factory, docs.audit, docs.clock, max_attempts
    ).execute()


def crash_once(docs):
    """A claim that kills the process mid-job (the job stays PROCESSANDO)."""
    with pytest.raises(Crash):
        docs.run_next_job(docs.processor(None, None, analyzer=Exploding(Crash())))


def stored(docs, document):
    with docs.world.uow_factory() as uow:
        return (
            uow.documents.get(document.id),
            uow.jobs.active_for_document(document.id),
            list(uow.audit.list_for(DOCUMENT_ENTITY, str(document.id))),
        )


def the_job(docs, document):
    """The job of the upload, whatever its state."""
    with docs.world.uow_factory() as uow:
        return uow.jobs.get(document.job_id)


@pytest.fixture
def document(docs):
    document = docs.upload_one(docs.world.docente, docs.world.process, pdf("sempre-falha"))
    with docs.world.uow_factory() as uow:
        document.job_id = uow.jobs.active_for_document(document.id).id
    return document


def test_a_job_that_always_crashes_ends_failed_after_the_attempt_limit(docs, document):
    for expected_attempts in (1, 2):
        crash_once(docs)
        assert recover(docs) == 1  # below the limit: back to PENDENTE
        _, job, _ = stored(docs, document)
        assert (job.status, job.attempts) == (JobStatus.PENDENTE, expected_attempts)

    crash_once(docs)  # third claim: the limit is reached
    assert recover(docs) == 0

    current, active, _ = stored(docs, document)
    assert active is None  # no job is waiting or running
    assert current.status is DocumentStatus.FALHOU
    assert current.status_code == EXHAUSTED
    job = the_job(docs, document)
    assert (job.status, job.error_code, job.attempts) == (JobStatus.FALHOU, EXHAUSTED, 3)
    with pytest.raises(AssertionError, match="no pending job"):
        docs.run_next_job(docs.processor(None, None))


def test_recovering_again_never_requeues_the_exhausted_job(docs, document):
    for _ in range(3):
        crash_once(docs)
        recover(docs)

    assert recover(docs) == 0
    assert recover(docs) == 0

    assert the_job(docs, document).status is JobStatus.FALHOU


def test_exhaustion_is_audited_without_document_content(docs, document):
    for _ in range(3):
        crash_once(docs)
        recover(docs)

    _, _, events = stored(docs, document)
    [event] = [e for e in events if e.changes.get("status_code", {}).get("after") == EXHAUSTED]
    assert event.action is AuditAction.STATUS
    assert event.user_id is None
    assert event.changes["status"] == {"before": "PROCESSANDO", "after": "FALHOU"}
    assert document.original_name not in str(event.changes)


def test_the_limit_comes_from_the_argument(docs, document):
    crash_once(docs)

    assert recover(docs, max_attempts=1) == 0

    current, active, _ = stored(docs, document)
    assert (current.status, current.status_code) == (DocumentStatus.FALHOU, EXHAUSTED)
    assert active is None


def test_a_manual_reprocess_starts_a_new_job_with_the_counter_at_zero(docs, document):
    w = docs.world
    for _ in range(3):
        crash_once(docs)
        recover(docs)

    docs.reprocess.execute(w.docente, document.id)

    _, job, _ = stored(docs, document)
    assert (job.status, job.attempts) == (JobStatus.PENDENTE, 0)
    docs.run_next_job(
        docs.processor(FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w)))
    )
    current, _, _ = stored(docs, document)
    assert current.status is DocumentStatus.PROCESSADO
