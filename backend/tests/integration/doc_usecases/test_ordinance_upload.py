"""PORT-01, PORT-07 to PORT-10, PORT-12, BNAV-02, BNAV-03: UploadOrdinance and RereadOrdinance."""

import hashlib
import uuid

import pytest

from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.board import UploadOrdinance
from app.application.use_cases.documents import UploadRejected
from app.application.use_cases.scoring import compute_process_score
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import OrdinanceReadingCode, ReadingState, ValueSource
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from tests.integration.doc_usecases.board_support import (
    MEMBERS,
    add_typed_ordinance,
    board_events,
    reread_uc,
    set_reading_state,
    stored_board,
    upload_uc,
)
from tests.integration.doc_usecases.draft_support import set_status
from tests.integration.doc_usecases.generation_support import add_activity
from tests.integration.doc_usecases.support import pdf
from tests.support import synthetic_docs as synth

MAX_BYTES = 20 * 1024 * 1024


def send(world, docs, content, name="portaria.pdf", version=0, replace=False, actor=None):
    mime = "application/pdf" if name.endswith(".pdf") else None
    incoming = docs.incoming(content, name, mime)
    return upload_uc(world, docs).execute(
        actor or world.docente, world.process.id, incoming, version, replace
    )


# --- UploadOrdinance: the first file ---------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "name", "mime", "pages"),
    [
        (synth.pdf_with_text(["um", "dois", "tres"]), "portaria.pdf", "application/pdf", 3),
        (synth.png_with_text(), "portaria.png", "image/png", 1),
        (synth.jpg_with_text(), "portaria.jpg", "image/jpeg", 1),
    ],
)
def test_an_upload_keeps_the_file_queues_the_reading_and_records_its_facts(
    docs, stored_files, content, name, mime, pages
):
    world = docs.world

    saved = send(world, docs, content, name)

    assert len(stored_files()) == 1
    assert stored_files()[0].read_bytes() == content
    stored = stored_board(world)
    assert stored == saved
    assert stored.reading_state is ReadingState.PENDENTE
    assert stored.reading_code is None
    assert stored.version == 2  # created empty, then the file went in
    assert stored.file.original_name == name
    assert stored.file.mime == mime
    assert stored.file.size_bytes == len(content)
    assert stored.file.sha256 == hashlib.sha256(content).hexdigest()
    assert stored.file.page_count == pages
    assert stored.file.deleted_at is None
    assert stored.members == ()


def test_the_upload_is_audited_with_the_file_and_without_a_justification(docs):
    world = docs.world

    send(world, docs, pdf("auditada"), "portaria-auditada.pdf")

    [event] = board_events(world)
    assert event.action is AuditAction.CREATE
    assert event.user_id == world.docente.id
    assert event.justification is None
    assert event.changes["operation"]["after"] == "UPLOAD"
    assert event.changes["original_name"]["after"] == "portaria-auditada.pdf"
    assert event.changes["reading_state"]["after"] == "PENDENTE"


def test_an_ordinance_with_only_typed_data_and_no_file_takes_the_upload_without_replace(docs):
    world = docs.world
    typed = add_typed_ordinance(world)

    saved = send(world, docs, pdf("depois-de-digitar"), version=typed.version)

    assert saved.reading_state is ReadingState.PENDENTE
    assert saved.file is not None
    assert saved.number == "77/2025" and saved.members == MEMBERS
    assert saved.number_source is ValueSource.INFORMADO
    assert saved.version == typed.version + 1


# --- UploadOrdinance: refusals ---------------------------------------------------------------


def test_a_file_over_20_mb_is_a_422_on_arquivo_with_the_limit_and_leaves_nothing(
    docs, stored_files
):
    world = docs.world
    content = pdf("grande")
    big = content + b"\x00" * (MAX_BYTES + 1 - len(content))

    with pytest.raises(UploadRejected) as raised:
        send(world, docs, big)

    assert raised.value.field == "arquivo"
    assert raised.value.code == "ARQUIVO_GRANDE"
    assert "tamanho máximo" in raised.value.message
    assert stored_files() == []
    assert stored_board(world) is None


@pytest.mark.parametrize(
    ("content", "name"),
    [
        (b"texto qualquer", "portaria.txt"),
        (b"texto que se passa por pdf", "portaria.pdf"),
        (synth.png_with_text(), "portaria.pdf"),
    ],
)
def test_a_file_that_is_not_pdf_png_or_jpeg_is_a_422_on_arquivo_and_leaves_nothing(
    docs, stored_files, content, name
):
    world = docs.world

    with pytest.raises(UploadRejected) as raised:
        send(world, docs, content, name)

    assert raised.value.field == "arquivo"
    assert stored_files() == []
    assert stored_board(world) is None
    assert board_events(world) == []


def test_a_file_exactly_at_20_mb_is_accepted(docs):
    world = docs.world
    content = pdf("no-limite")
    padded = content + b"\x00" * (MAX_BYTES - len(content))

    saved = send(world, docs, padded)

    assert saved.file.size_bytes == MAX_BYTES


def test_a_second_file_without_replace_is_a_409_and_the_first_stays(docs, stored_files):
    world = docs.world
    first = send(world, docs, pdf("primeira"))
    before = stored_files()

    with pytest.raises(Conflict) as raised:
        send(world, docs, pdf("segunda"), version=first.version)

    assert raised.value.code == "PORTARIA_EXISTENTE"
    assert stored_files() == before
    assert stored_board(world) == first


def test_a_file_with_an_outdated_version_is_a_409_with_its_code_and_stores_nothing(
    docs, stored_files
):
    world = docs.world
    typed = add_typed_ordinance(world)

    with pytest.raises(StaleVersion) as raised:
        send(world, docs, pdf("versao-velha"), version=typed.version + 3)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_files() == []
    assert stored_board(world) == typed


def test_a_first_file_that_expects_a_version_above_zero_is_stale(docs, stored_files):
    world = docs.world

    with pytest.raises(StaleVersion) as raised:
        send(world, docs, pdf("sem-linha"), version=2)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_files() == []
    assert stored_board(world) is None


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_upload_with_409_and_stores_nothing(
    docs, stored_files, status
):
    world = docs.world
    set_status(world, status)

    with pytest.raises(Conflict) as raised:
        send(world, docs, pdf("fechado"))

    assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"
    assert stored_files() == []
    assert stored_board(world) is None


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_someone_without_access_to_the_process_gets_not_found(docs, stored_files, who):
    world = docs.world

    with pytest.raises(NotFound):
        send(world, docs, pdf("alheia"), actor=getattr(world, who))

    assert stored_files() == []
    assert stored_board(world) is None


# --- UploadOrdinance: replacement ------------------------------------------------------------


def test_a_replacement_reads_the_new_file_and_removes_the_old_one_from_the_disk(
    docs, stored_files
):
    world = docs.world
    first = send(world, docs, pdf("antiga"), "antiga.pdf")
    old_path = docs.storage.path(world.process.id, first.file.internal_name)
    new_content = pdf("nova", pages=2)

    saved = send(world, docs, new_content, "nova.pdf", version=first.version, replace=True)

    assert not old_path.exists()
    assert [p.read_bytes() for p in stored_files()] == [new_content]
    assert saved.file.original_name == "nova.pdf"
    assert saved.file.sha256 == hashlib.sha256(new_content).hexdigest()
    assert saved.file.page_count == 2
    assert saved.reading_state is ReadingState.PENDENTE
    assert saved.version == first.version + 1


def test_a_replacement_over_a_finished_reading_queues_it_again_and_is_audited(docs):
    world = docs.world
    first = send(world, docs, pdf("lida"), "lida.pdf")
    set_reading_state(world, ReadingState.LIDA)
    read = stored_board(world)

    send(world, docs, pdf("outra"), "outra.pdf", version=read.version, replace=True)

    assert stored_board(world).reading_state is ReadingState.PENDENTE
    replacement = board_events(world)[-1]
    assert replacement.action is AuditAction.UPDATE
    assert replacement.changes["operation"]["after"] == "REPLACE"
    assert replacement.changes["original_name"] == {"before": "lida.pdf", "after": "outra.pdf"}
    assert replacement.justification is None
    assert replacement.changes["sha256"]["before"] == first.file.sha256


def test_a_failure_before_the_commit_keeps_the_old_file_and_removes_the_new_one(
    docs, stored_files
):
    world = docs.world
    first = send(world, docs, pdf("mantida"))
    before = stored_files()

    class CommitFails:
        def __init__(self, inner):
            self._inner = inner

        def __enter__(self):
            uow = self._inner.__enter__()

            def fail():
                raise RuntimeError("falha simulada")

            uow.commit = fail
            return uow

        def __exit__(self, *exc):
            return self._inner.__exit__(*exc)

    broken = UploadOrdinance(
        lambda: CommitFails(world.uow_factory()),
        world.audit,
        world.policy,
        docs.storage,
        docs.inspector,
        docs.clock,
    )

    with pytest.raises(RuntimeError):
        broken.execute(
            world.docente,
            world.process.id,
            docs.incoming(pdf("perdida"), "perdida.pdf", "application/pdf"),
            first.version,
            True,
        )

    assert stored_files() == before
    assert stored_board(world) == first


# --- PORT-09: the ordinance is not a document ------------------------------------------------


def test_the_upload_creates_no_document_and_leaves_the_stage_2_to_5_reads_unchanged(
    official_chosen, docs
):
    world = official_chosen
    add_activity(world)

    def snapshot():
        with world.uow_factory() as uow:
            process = uow.processes.get(world.process.id)
            return (
                list(uow.documents.list_for_process(world.process.id)),
                load_generation_inputs(uow, process),
                compute_process_score(uow, process),
            )

    before = snapshot()

    send(world, docs, pdf("fora-das-etapas"))

    assert snapshot() == before
    assert before[0] == []


# --- RereadOrdinance -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "code"),
    [(ReadingState.LIDA, None), (ReadingState.FALHOU, OrdinanceReadingCode.IA_INDISPONIVEL)],
)
def test_reading_again_queues_a_finished_reading(docs, state, code):
    world = docs.world
    send(world, docs, pdf("reler"))
    set_reading_state(world, state, code=code)
    finished = stored_board(world)

    reread_uc(world, docs).execute(world.docente, world.process.id, finished.version)

    queued = stored_board(world)
    assert queued.reading_state is ReadingState.PENDENTE
    assert queued.reading_code is None
    assert queued.file == finished.file
    assert board_events(world)[-1].changes["operation"]["after"] == "REREAD"


def test_reading_again_without_a_file_is_a_422_on_arquivo(docs):
    world = docs.world
    typed = add_typed_ordinance(world)

    with pytest.raises(ValidationFailed) as raised:
        reread_uc(world, docs).execute(world.docente, world.process.id, typed.version)

    assert raised.value.field == "arquivo"
    assert stored_board(world) == typed


def test_reading_again_with_no_ordinance_at_all_is_a_422_on_arquivo(docs):
    world = docs.world

    with pytest.raises(ValidationFailed) as raised:
        reread_uc(world, docs).execute(world.docente, world.process.id, 0)

    assert raised.value.field == "arquivo"


@pytest.mark.parametrize("state", [ReadingState.PENDENTE, ReadingState.LENDO])
def test_reading_again_while_it_is_queued_or_running_is_a_409_operacao_em_andamento(docs, state):
    world = docs.world
    queued = send(world, docs, pdf("em-andamento"))
    set_reading_state(world, state)
    current = stored_board(world)

    with pytest.raises(Conflict) as raised:
        reread_uc(world, docs).execute(world.docente, world.process.id, current.version)

    assert raised.value.code == "OPERACAO_EM_ANDAMENTO"
    assert stored_board(world).reading_state is state
    assert queued.version == current.version


def test_reading_again_with_an_outdated_version_is_a_409_with_its_code(docs):
    world = docs.world
    send(world, docs, pdf("velha"))
    set_reading_state(world, ReadingState.LIDA)
    current = stored_board(world)

    with pytest.raises(StaleVersion) as raised:
        reread_uc(world, docs).execute(world.docente, world.process.id, current.version - 1)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_board(world).reading_state is ReadingState.LIDA


def test_reading_again_in_a_closed_process_is_a_409_and_outside_the_access_is_not_found(docs):
    world = docs.world
    send(world, docs, pdf("fechada"))
    set_reading_state(world, ReadingState.LIDA)
    current = stored_board(world)

    with pytest.raises(NotFound):
        reread_uc(world, docs).execute(world.other_docente, world.process.id, current.version)
    with pytest.raises(NotFound):
        reread_uc(world, docs).execute(world.docente, uuid.uuid4(), current.version)
    set_status(world, ProcessStatus.ARQUIVADO)
    with pytest.raises(Conflict) as raised:
        reread_uc(world, docs).execute(world.docente, world.process.id, current.version)

    assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"
    assert stored_board(world).reading_state is ReadingState.LIDA
