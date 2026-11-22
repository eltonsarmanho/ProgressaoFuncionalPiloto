"""VER-04, VER-08, REL-14 (T81), PORT-01, PORT-07, DOS-04 (T34): the application wires the
generation and board use cases and hands the runners (generation, wording, ordinance) and the
recoverers to the executor."""

import threading
import time
import uuid
from datetime import date
from types import SimpleNamespace

from app.application.use_cases.board import (
    DownloadOrdinanceFile,
    GetBoard,
    RereadOrdinance,
    SaveOpinion,
    SaveOrdinanceData,
    SaveRequestSettings,
    UploadOrdinance,
)
from app.application.use_cases.comprovante_layout import (
    GetComprovanteLayout,
    SaveComprovanteLayout,
)
from app.application.use_cases.conclusion import ConcludeProcess, GetConclusionPreview
from app.application.use_cases.dossier import GetDossier, SetDossierDelivery
from app.application.use_cases.generated_documents import (
    DownloadGeneratedFile,
    GetGeneratedDocument,
    ListGeneratedDocuments,
    RecoverInterruptedGenerations,
    RequestGeneration,
    RunGeneration,
)
from app.application.use_cases.ordinance_reading import RunOrdinanceReading
from app.application.use_cases.report_draft import (
    GetReportDraft,
    ListWordingJobs,
    MoveReportEntry,
    RequestSectionWording,
    RunWording,
    SaveReportEntry,
    SaveReportSection,
)
from app.domain.entities.board import (
    BoardOrdinance,
    OrdinanceFile,
    OrdinanceReadingCode,
    ReadingState,
    ValueSource,
)
from app.domain.entities.generated import DocumentKind, GenerationCode, GenerationState
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from app.infrastructure.ai.ordinance_extractor import MariTalkOrdinanceExtractor
from tests.integration.doc_usecases.board_support import FakeOrdinanceExtractor
from tests.integration.documents.generated_support import (
    T0,
    make_generation,
    make_wording_job,
)
from tests.unit.application.analyzer_fakes import FakeTextExtractor, text_page

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
    "get_board": GetBoard,
    "upload_ordinance": UploadOrdinance,
    "reread_ordinance": RereadOrdinance,
    "save_ordinance_data": SaveOrdinanceData,
    "download_ordinance_file": DownloadOrdinanceFile,
    "save_opinion": SaveOpinion,
    "save_request_settings": SaveRequestSettings,
    "run_ordinance_reading": RunOrdinanceReading,
    "get_dossier": GetDossier,
    "set_dossier_delivery": SetDossierDelivery,
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


# --- the ordinance reading in the executor (PORT-01, PORT-07) ---------------------------------

PAGE = "PORTARIA Nº 77/2025. Belém, 10/03/2025. Presidente: Ana Souza Lima."
ANSWER = OrdinanceAi(
    "77/2025",
    1,
    date(2025, 3, 10),
    1,
    (OrdinanceAiMember("Ana Souza Lima", "PRESIDENTE", 1),),
)


def queue_ordinance(uow_factory, process, user_id, claim=False):
    """A stored ordinance with a file, `PENDENTE`; `claim` takes it as the executor would."""
    process_id = uuid.UUID(process["id"])
    file = OrdinanceFile("a" * 32 + ".pdf", "portaria.pdf", "application/pdf", 10, "b" * 64, 1)
    with uow_factory() as uow:
        uow.board.create(BoardOrdinance(process_id), user_id, 0)
        uow.board.set_file(process_id, file, user_id, 1, T0)
        if claim:
            assert uow.board.claim_next_pending(T0) is not None
        uow.commit()
    return process_id


def stored_ordinance(uow_factory, process_id):
    with uow_factory() as uow:
        return uow.board.get(process_id)


def test_the_runners_are_the_generation_then_the_wording_then_the_ordinance(client):
    container = client.app.state.container

    owners = [runner.__self__ for runner in container.worker_runners()]

    assert [type(owner) for owner in owners] == [RunGeneration, RunWording, RunOrdinanceReading]


def test_the_recoverers_include_the_one_of_the_ordinance_reading(client):
    container = client.app.state.container

    assert container.run_ordinance_reading.recover_interrupted in container.worker_recoverers()
    assert container.recover_generations.execute in container.worker_recoverers()


def test_a_reading_left_running_by_a_restart_is_closed_as_interrupted_at_the_start(
    make_client, admin, process, uow_factory
):
    process_id = queue_ordinance(uow_factory, process, admin[0].id, claim=True)
    assert stored_ordinance(uow_factory, process_id).reading_state is ReadingState.LENDO

    make_client(worker_enabled=True)

    closed = stored_ordinance(uow_factory, process_id)
    assert (closed.reading_state, closed.reading_code) == (
        ReadingState.FALHOU,
        OrdinanceReadingCode.INTERROMPIDA,
    )


def test_the_executor_reads_a_queued_ordinance_with_the_injected_extractor(
    make_client, admin, process, uow_factory
):
    process_id = queue_ordinance(uow_factory, process, admin[0].id)
    extractor = FakeOrdinanceExtractor(answer=ANSWER)

    make_client(
        worker_enabled=True,
        text_extractor=FakeTextExtractor(text_page(1, PAGE)),
        ordinance_extractor=extractor,
    )

    def read():
        row = stored_ordinance(uow_factory, process_id)
        return row if row.reading_state is ReadingState.LIDA else None

    row = wait_until(read)
    assert row is not None
    assert (row.number, row.number_page, row.number_source) == ("77/2025", 1, ValueSource.EXTRAIDO)
    assert [m.name for m in row.members] == ["Ana Souza Lima"]
    assert len(extractor.received) == 1 and "[PÁGINA 1]" in extractor.received[0]


def test_without_an_injected_extractor_the_application_uses_the_maritalk_one(client):
    extractor = client.app.state.container.run_ordinance_reading._extractor

    assert isinstance(extractor, MariTalkOrdinanceExtractor)


def test_an_ordinance_reading_waiting_is_not_run_when_the_executor_is_off(
    make_client, admin, process, uow_factory
):
    process_id = queue_ordinance(uow_factory, process, admin[0].id)

    make_client(worker_enabled=False, ordinance_extractor=FakeOrdinanceExtractor(answer=ANSWER))
    time.sleep(0.3)

    assert stored_ordinance(uow_factory, process_id).reading_state is ReadingState.PENDENTE
