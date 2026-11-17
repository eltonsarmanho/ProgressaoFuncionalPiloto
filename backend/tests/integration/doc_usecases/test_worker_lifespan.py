"""PIPE-01, PIPE-03 (T35): the worker starts and stops with the application."""

import threading
import time
from dataclasses import replace

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.entities.document import DocumentStatus
from app.domain.repositories.ports import JobStatus
from app.main import create_app
from tests.integration.doc_usecases.support import pdf
from tests.integration.doc_usecases.test_process_document import banca_payload, banca_text
from tests.unit.application.analyzer_fakes import FakeAi, FakeTextExtractor, text_page


def settings_for(docs, migrated_url, **overrides):
    return Settings(
        database_url=migrated_url,
        admin_email="admin@ufpa.br",
        admin_password="admin-password-1",
        storage_dir=str(docs.storage_root),
        **overrides,
    )


def app_for(docs, migrated_url, **overrides):
    w = docs.world
    return create_app(
        settings_for(docs, migrated_url, **overrides),
        ai_extractor=FakeAi(banca_payload(w)),
        text_extractor=FakeTextExtractor(text_page(1, banca_text(w))),
    )


def worker_threads():
    return [t for t in threading.enumerate() if t.name == "document-worker" and t.is_alive()]


def wait_for_status(docs, document, status, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with docs.world.uow_factory() as uow:
            if uow.documents.get(document.id).status is status:
                return True
        time.sleep(0.05)
    return False


def test_with_the_worker_disabled_no_thread_runs_and_the_job_stays_pending(docs, migrated_url):
    document = docs.upload_one(docs.world.docente, docs.world.process, pdf("desligado"))

    with TestClient(app_for(docs, migrated_url, worker_enabled=False)):
        time.sleep(0.5)
        assert worker_threads() == []

    with docs.world.uow_factory() as uow:
        assert uow.documents.get(document.id).status is DocumentStatus.PENDENTE
        assert uow.jobs.active_for_document(document.id).status is JobStatus.PENDENTE


def test_with_the_worker_enabled_a_pending_job_is_processed_and_stopping_the_app_ends_the_thread(
    docs, migrated_url
):
    document = docs.upload_one(docs.world.docente, docs.world.process, pdf("ligado"))

    with TestClient(app_for(docs, migrated_url, worker_enabled=True)):
        assert len(worker_threads()) == 1
        assert wait_for_status(docs, document, DocumentStatus.PROCESSADO)

    assert worker_threads() == []


def test_a_job_left_processing_by_a_restart_is_processed_after_the_app_starts(docs, migrated_url):
    document = docs.upload_one(docs.world.docente, docs.world.process, pdf("reinicio"))
    with docs.world.uow_factory() as uow:
        uow.jobs.claim_next(docs.clock.now())
        current = uow.documents.get(document.id)
        uow.documents.update(replace(current, status=DocumentStatus.PROCESSANDO), current.version)
        uow.commit()

    with TestClient(app_for(docs, migrated_url, worker_enabled=True)):
        assert wait_for_status(docs, document, DocumentStatus.PROCESSADO)

    with docs.world.uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id) is None
