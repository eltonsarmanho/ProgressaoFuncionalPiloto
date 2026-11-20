"""VER-04, VER-08, REL-14 (T81): the application wires the generation use cases and hands the
runners and the recoverers of the generation and of the wording to the executor."""

import threading
import time
import uuid
from types import SimpleNamespace

from app.application.use_cases.comprovante_layout import (
    GetComprovanteLayout,
    SaveComprovanteLayout,
)
from app.application.use_cases.conclusion import ConcludeProcess, GetConclusionPreview
from app.application.use_cases.generated_documents import (
    DownloadGeneratedFile,
    GetGeneratedDocument,
    ListGeneratedDocuments,
    RecoverInterruptedGenerations,
    RequestGeneration,
    RunGeneration,
)
from app.application.use_cases.report_draft import (
    GetReportDraft,
    ListWordingJobs,
    MoveReportEntry,
    RequestSectionWording,
    RunWording,
    SaveReportEntry,
    SaveReportSection,
)
from app.domain.entities.generated import DocumentKind, GenerationCode, GenerationState
from tests.integration.documents.generated_support import (
    T0,
    make_generation,
    make_wording_job,
)

NEW_USE_CASES = {
    "request_generation": RequestGeneration,
    "run_generation": RunGeneration,
    "recover_generations": RecoverInterruptedGenerations,
    "list_generated_documents": ListGeneratedDocuments,
    "get_generated_document": GetGeneratedDocument,
    "download_generated_file": DownloadGeneratedFile,
    "get_report_draft": GetReportDraft,
    "save_report_entry": SaveReportEntry,
    "save_report_section": SaveReportSection,
    "move_report_entry": MoveReportEntry,
    "request_wording": RequestSectionWording,
    "list_wording_jobs": ListWordingJobs,
    "run_wording": RunWording,
    "get_comprovante_layout": GetComprovanteLayout,
    "save_comprovante_layout": SaveComprovanteLayout,
    "conclusion_preview": GetConclusionPreview,
    "conclude_process": ConcludeProcess,
}


def worker_threads():
    return [t for t in threading.enumerate() if t.name == "document-worker" and t.is_alive()]


def wait_until(condition, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = condition()
        if found:
            return found
        time.sleep(0.05)
    return None


def test_the_container_exposes_every_new_use_case(client):
    container = client.app.state.container

    for name, kind in NEW_USE_CASES.items():
        assert isinstance(getattr(container, name), kind), name


def test_the_application_starts_with_the_executor_on_and_off(make_client):
    off = make_client(worker_enabled=False)
    assert off.get("/api/health").status_code == 200
    assert worker_threads() == []

    on = make_client(worker_enabled=True)
    assert on.get("/api/health").status_code == 200
    assert len(worker_threads()) == 1


def test_a_generation_started_before_the_start_is_closed_as_interrupted_at_the_start(
    make_client, admin, process, uow_factory
):
    owner = SimpleNamespace(id=uuid.UUID(process["id"]))
    row = make_generation(owner, admin[0].id, DocumentKind.TABELA)
    with uow_factory() as uow:
        uow.generations.add(row)
        assert uow.generations.claim_next(T0).id == row.id
        uow.commit()

    make_client(worker_enabled=True)

    with uow_factory() as uow:
        closed = uow.generations.get(row.id)
    assert (closed.state, closed.error_code) == (
        GenerationState.FALHOU,
        GenerationCode.INTERROMPIDA,
    )


def test_the_executor_runs_a_waiting_generation_and_a_waiting_wording(
    make_client, admin, process, uow_factory
):
    owner = SimpleNamespace(id=uuid.UUID(process["id"]))
    generation = make_generation(owner, admin[0].id, DocumentKind.TABELA)
    wording = make_wording_job(owner, admin[0].id, "1.1")
    with uow_factory() as uow:
        uow.generations.add(generation)
        uow.wording_jobs.add(wording)
        uow.commit()

    make_client(worker_enabled=True)

    def closed():
        with uow_factory() as uow:
            g, w = uow.generations.get(generation.id), uow.wording_jobs.get(wording.id)
        done = g.state is not GenerationState.GERANDO and w.state is not GenerationState.GERANDO
        return (g, w) if done else None

    g, w = wait_until(closed)
    # no table was chosen and no draft exists: both runners ran and closed their own row
    assert (g.state, g.error_code) == (GenerationState.FALHOU, GenerationCode.TABELA_NAO_ESCOLHIDA)
    assert (w.state, w.error_code) == (GenerationState.FALHOU, GenerationCode.ERRO_INTERNO)
