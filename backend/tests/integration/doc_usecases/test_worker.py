"""PIPE-01, PIPE-03 (T35): the background worker over a real database and a fake analyzer."""

import logging
import threading
import time
from dataclasses import replace

import pytest

from app.application.use_cases.document_processing import RecoverStuckJobs
from app.domain.entities.document import DocumentStatus
from app.domain.repositories.ports import JobStatus
from app.infrastructure.jobs.worker import DocumentWorker
from tests.integration.doc_usecases.support import pdf
from tests.integration.doc_usecases.test_process_document import banca_payload, banca_text
from tests.unit.application.analyzer_fakes import FakeAi, FakeTextExtractor, text_page

WAIT_SECONDS = 15


def build_worker(docs, process_document=None, poll_seconds=0.05):
    w = docs.world
    process_document = process_document or docs.processor(
        FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w))
    )
    return DocumentWorker(
        w.uow_factory,
        process_document,
        RecoverStuckJobs(w.uow_factory),
        docs.clock,
        poll_seconds=poll_seconds,
    )


def submit(docs, label):
    """Upload a document; the job of its upload is remembered on `document.job_id`."""
    document = docs.upload_one(docs.world.docente, docs.world.process, pdf(label))
    with docs.world.uow_factory() as uow:
        document.job_id = uow.jobs.active_for_document(document.id).id
    return document


def document_status(docs, document):
    with docs.world.uow_factory() as uow:
        return uow.documents.get(document.id).status


def job_of(docs, document):
    with docs.world.uow_factory() as uow:
        return uow.jobs.get(document.job_id)


def wait_until(condition, timeout=WAIT_SECONDS):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


def test_a_pending_job_is_processed_and_ends_concluida(docs):
    document = submit(docs, "um")
    worker = build_worker(docs)

    ran = worker.run_once()

    assert ran is True
    assert document_status(docs, document) is DocumentStatus.PROCESSADO
    assert job_of(docs, document).status is JobStatus.CONCLUIDA


def test_run_once_reports_false_when_there_is_no_job(docs):
    assert build_worker(docs).run_once() is False


def test_two_jobs_are_processed_one_at_a_time_in_creation_order(docs):
    first = submit(docs, "primeiro")
    second = submit(docs, "segundo")
    worker = build_worker(docs)

    assert worker.run_once() is True
    assert document_status(docs, first) is DocumentStatus.PROCESSADO
    assert document_status(docs, second) is DocumentStatus.PENDENTE

    assert worker.run_once() is True
    assert document_status(docs, second) is DocumentStatus.PROCESSADO
    assert worker.run_once() is False


def test_a_failing_job_is_logged_by_type_and_id_and_never_stops_the_worker(docs, caplog):
    first = submit(docs, "quebra")
    second = submit(docs, "segue")
    real = docs.processor(
        FakeTextExtractor(text_page(1, banca_text(docs.world))),
        FakeAi(banca_payload(docs.world)),
    )

    class ExplodesOnce:
        def __init__(self):
            self.calls = 0

        def execute(self, job_id, now):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("conteudo sigiloso do documento")
            real.execute(job_id, now)

    worker = build_worker(docs, ExplodesOnce())
    worker.start()
    try:
        with caplog.at_level(logging.ERROR, logger="app.documents.worker"):
            assert wait_until(lambda: document_status(docs, second) is DocumentStatus.PROCESSADO)
    finally:
        worker.stop()

    failed = job_of(docs, first)
    assert failed.status is JobStatus.FALHOU
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "RuntimeError" in messages
    assert str(failed.id) in messages
    assert "sigiloso" not in messages
    assert all(r.exc_info is None for r in caplog.records)


def test_recovery_runs_at_start_and_a_stuck_job_is_processed_again(docs):
    document = submit(docs, "preso")
    with docs.world.uow_factory() as uow:  # what a crash leaves: job and document PROCESSANDO
        job = uow.jobs.claim_next(docs.clock.now())
        current = uow.documents.get(document.id)
        uow.documents.update(replace(current, status=DocumentStatus.PROCESSANDO), current.version)
        uow.commit()
    assert job_of(docs, document).status is JobStatus.PROCESSANDO

    worker = build_worker(docs)
    worker.start()
    try:
        assert wait_until(lambda: document_status(docs, document) is DocumentStatus.PROCESSADO)
    finally:
        worker.stop()

    assert job_of(docs, document).id == job.id
    assert job_of(docs, document).status is JobStatus.CONCLUIDA
    assert job_of(docs, document).attempts == 2


def test_an_idle_worker_picks_up_a_job_that_arrives_later(docs):
    worker = build_worker(docs, poll_seconds=0.05)
    worker.start()
    try:
        time.sleep(0.2)
        document = submit(docs, "tardio")
        assert wait_until(lambda: document_status(docs, document) is DocumentStatus.PROCESSADO)
    finally:
        worker.stop()


def test_stop_ends_the_thread_promptly_even_with_a_long_poll_interval(docs):
    worker = build_worker(docs, poll_seconds=60)
    worker.start()
    thread = next(t for t in threading.enumerate() if t.name == "document-worker")
    assert thread.is_alive()
    assert thread.daemon is True

    started = time.monotonic()
    worker.stop()

    assert time.monotonic() - started < 5
    assert not thread.is_alive()


def test_a_database_error_while_claiming_does_not_kill_the_thread(docs):
    w = docs.world
    real_factory = w.uow_factory
    calls = {"n": 0}

    def flaky_factory():
        calls["n"] += 1
        if calls["n"] == 1:  # the first claim fails; the thread must go on
            raise ConnectionError("banco fora")
        return real_factory()

    document = submit(docs, "banco")
    process_document = docs.processor(
        FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w))
    )
    worker = DocumentWorker(
        flaky_factory,
        process_document,
        RecoverStuckJobs(real_factory),
        docs.clock,
        poll_seconds=0.05,
    )
    worker.start()
    try:
        assert wait_until(lambda: document_status(docs, document) is DocumentStatus.PROCESSADO)
    finally:
        worker.stop()
    assert calls["n"] >= 3


def _worker_threads():
    return [t for t in threading.enumerate() if t.name == "document-worker" and t.is_alive()]


@pytest.fixture(autouse=True)
def _no_worker_thread_left_behind():
    yield
    assert wait_until(lambda: not _worker_threads(), timeout=5)
