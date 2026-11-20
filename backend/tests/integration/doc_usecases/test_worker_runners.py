"""VER-04, VER-08, REL-14: the executor runs several kinds of jobs (generation, wording, OCR) in
one thread, in that order, and a runner that fails never takes the thread down."""

import logging
import time

from app.application.use_cases.document_processing import RecoverStuckJobs
from app.domain.entities.document import DocumentStatus
from app.infrastructure.jobs.worker import DocumentWorker
from tests.integration.doc_usecases.test_process_document import banca_payload, banca_text
from tests.integration.doc_usecases.test_worker import document_status, submit, wait_until
from tests.unit.application.analyzer_fakes import FakeAi, FakeTextExtractor, text_page


class FakeRunner:
    """A runner with `jobs` pieces of work; each call that has work records its name."""

    def __init__(self, name, log, jobs=1, error=None):
        self.name, self.log, self.jobs, self.error = name, log, jobs, error

    def __call__(self) -> bool:
        if self.jobs == 0:
            return False
        self.jobs -= 1
        self.log.append(self.name)
        if self.error is not None:
            raise self.error
        return True


def worker_with(docs, runners=(), recoverers=(), poll_seconds=0.05):
    w = docs.world
    return DocumentWorker(
        w.uow_factory,
        docs.processor(FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w))),
        RecoverStuckJobs(w.uow_factory, docs.audit, docs.clock),
        docs.clock,
        poll_seconds=poll_seconds,
        runners=runners,
        recoverers=recoverers,
    )


def test_generation_runs_first_then_wording_then_the_ocr_job(docs):
    document = submit(docs, "ocr")
    log = []
    worker = worker_with(docs, [FakeRunner("geracao", log), FakeRunner("redacao", log)])

    assert [worker.run_once() for _ in range(3)] == [True, True, True]
    assert log == ["geracao", "redacao"]
    assert document_status(docs, document) is DocumentStatus.PROCESSADO


def test_a_generation_waiting_is_taken_before_a_document_waiting(docs):
    document = submit(docs, "espera")
    log = []
    worker = worker_with(docs, [FakeRunner("geracao", log, jobs=1)])

    assert worker.run_once() is True
    assert log == ["geracao"]
    assert document_status(docs, document) is DocumentStatus.PENDENTE  # the OCR waited

    assert worker.run_once() is True
    assert document_status(docs, document) is DocumentStatus.PROCESSADO


def test_run_once_is_false_when_no_runner_and_no_job_has_work(docs):
    log = []
    worker = worker_with(docs, [FakeRunner("geracao", log, jobs=0), FakeRunner("redacao", log, 0)])

    assert worker.run_once() is False
    assert log == []


def test_a_runner_that_raises_does_not_stop_the_thread_and_the_log_has_only_the_type(docs, caplog):
    document = submit(docs, "segue")
    log = []
    broken = FakeRunner("geracao", log, error=RuntimeError("texto sigiloso do documento"))
    worker = worker_with(docs, [broken])

    with caplog.at_level(logging.ERROR, logger="app.documents.worker"):
        worker.start()
        try:
            assert wait_until(lambda: document_status(docs, document) is DocumentStatus.PROCESSADO)
        finally:
            worker.stop()

    assert log == ["geracao"]
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "RuntimeError" in messages
    assert "sigiloso" not in messages
    assert all(r.exc_info is None for r in caplog.records)


def test_a_runner_that_raises_counts_as_having_run(docs):
    log = []
    worker = worker_with(docs, [FakeRunner("redacao", log, error=ValueError("x"))])

    assert worker.run_once() is True
    assert worker.run_once() is False  # nothing left: the failed one was not taken again


def test_start_calls_every_recoverer_and_a_failing_one_does_not_stop_the_rest(docs, caplog):
    called = []

    def broken():
        called.append("quebrado")
        raise RuntimeError("segredo")

    def fine():
        called.append("ok")

    worker = worker_with(docs, recoverers=[broken, fine])
    with caplog.at_level(logging.ERROR, logger="app.documents.worker"):
        worker.start()
        try:
            assert wait_until(lambda: called == ["quebrado", "ok"], timeout=5)
            time.sleep(0.1)
        finally:
            worker.stop()

    assert called == ["quebrado", "ok"]  # once each, in order
    assert "segredo" not in " ".join(r.getMessage() for r in caplog.records)
