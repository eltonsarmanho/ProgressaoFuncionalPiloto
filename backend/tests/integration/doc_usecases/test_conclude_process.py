"""DEL-01, DEL-02, DEL-04, DEL-05, DEL-07 to DEL-10, DEL-15: ConcludeProcess checks, purges the
input documents and moves the process to CONCLUIDO."""

import json
import uuid

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments
from app.application.use_cases.conclusion import ConcludeProcess
from app.domain.entities.audit import AuditAction
from app.domain.entities.conclusion import ConclusionResult
from app.domain.entities.generated import (
    DocumentKind,
    GenerationAlertCode,
    GenerationState,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, GenerationRefused, NotFound, StaleVersion
from app.domain.repositories.ports import JobStatus, ProcessingJob
from tests.integration.doc_usecases.conclusion_support import (
    add_all_ready,
    add_generation,
    add_input_document,
    add_stored_generation,
    file_of,
    state_of,
)
from tests.integration.doc_usecases.draft_support import set_status
from tests.integration.doc_usecases.generation_support import add_document
from tests.integration.doc_usecases.test_purge_inputs import FixedClock, FlakyStorage
from tests.integration.documents.generated_support import make_wording_job

S = ProcessStatus
K = DocumentKind
EM_ANDAMENTO_VERSION = 2  # RASCUNHO is version 1; set_status bumps it once


def conclude_uc(gen, storage=None) -> ConcludeProcess:
    world = gen.world
    purge = PurgeInputDocuments(world.uow_factory, storage or gen.originals, FixedClock())
    return ConcludeProcess(world.uow_factory, world.audit, world.policy, purge)


def conclude(gen, actor=None, version=None, confirm=True, justification=None, storage=None):
    world = gen.world
    return conclude_uc(gen, storage).execute(
        actor or world.admin,
        world.process.id,
        version if version is not None else stored(gen).version,
        confirm,
        justification,
    )


def stored(gen):
    with gen.world.uow_factory() as uow:
        return uow.processes.get(gen.world.process.id)


def events(gen):
    with gen.world.uow_factory() as uow:
        return list(uow.audit.list_for("process", str(gen.world.process.id)))


@pytest.fixture
def ready(gen):
    """An EM_ANDAMENTO process with three input documents (100, 200 and 300 bytes) and a
    PRONTO version of each generated kind."""
    set_status(gen.world, S.EM_ANDAMENTO)
    documents = [add_input_document(gen, size=100 * n)[0] for n in (1, 2, 3)]
    add_all_ready(gen.world)
    return documents


def assert_nothing_removed(gen, documents):
    assert stored(gen).status is S.EM_ANDAMENTO
    for document in documents:
        after = state_of(gen, document)
        assert (after.file_exists, after.row.file_deleted_at) == (True, None)
        assert (after.pages, after.links) == ([1, 2], [(1, "trecho")])


# --- refusals: nothing is removed --------------------------------------------------------


def test_without_the_confirmation_it_is_422_and_nothing_is_removed(gen, ready):
    before = len(events(gen))

    with pytest.raises(GenerationRefused) as error:
        conclude(gen, confirm=False)

    assert error.value.code == "CONFIRMACAO_OBRIGATORIA"
    assert_nothing_removed(gen, ready)
    assert len(events(gen)) == before


@pytest.mark.parametrize(
    ("ready_kinds", "missing"),
    [
        ([K.TABELA, K.RELATORIO], [K.COMPROVANTE]),
        ([K.RELATORIO], [K.TABELA, K.COMPROVANTE]),
        ([], [K.TABELA, K.RELATORIO, K.COMPROVANTE]),
    ],
)
def test_without_the_three_ready_versions_it_is_422_naming_the_missing_kinds(
    gen, ready_kinds, missing
):
    set_status(gen.world, S.EM_ANDAMENTO)
    documents = [add_input_document(gen)[0]]
    for kind in ready_kinds:
        add_generation(gen.world, kind)

    with pytest.raises(GenerationRefused) as error:
        conclude(gen)

    assert error.value.code == "ARTEFATOS_PENDENTES"
    assert all(kind.value in error.value.message for kind in missing)
    assert not any(k.value in error.value.message for k in K if k not in missing)
    assert_nothing_removed(gen, documents)


def test_a_failed_version_does_not_count_as_ready(gen):
    set_status(gen.world, S.EM_ANDAMENTO)
    add_generation(gen.world, K.TABELA)
    add_generation(gen.world, K.RELATORIO)
    add_generation(gen.world, K.COMPROVANTE, GenerationState.FALHOU)

    with pytest.raises(GenerationRefused) as error:
        conclude(gen)

    assert error.value.code == "ARTEFATOS_PENDENTES"


def running_generation(gen, documents):
    add_generation(gen.world, K.TABELA, GenerationState.GERANDO)


def running_wording(gen, documents):
    with gen.world.uow_factory() as uow:
        uow.wording_jobs.add(make_wording_job(gen.world.process, gen.world.admin.id))
        uow.commit()


def running_processing(gen, documents):
    with gen.world.uow_factory() as uow:
        uow.jobs.add(ProcessingJob(uuid.uuid4(), documents[0].id, JobStatus.PROCESSANDO))
        uow.commit()


@pytest.mark.parametrize("start", [running_generation, running_wording, running_processing])
def test_an_operation_in_progress_is_409_and_nothing_is_removed(gen, ready, start):
    start(gen, ready)

    with pytest.raises(Conflict) as error:
        conclude(gen)

    assert error.value.code == "OPERACAO_EM_ANDAMENTO"
    assert_nothing_removed(gen, ready)


def test_outside_the_access_it_is_404_and_nothing_is_removed(gen, ready):
    world = gen.world
    for actor in (world.other_docente, world.other_secretaria):
        with pytest.raises(NotFound):
            conclude(gen, actor=actor)

    assert_nothing_removed(gen, ready)


def test_a_stale_version_is_409_and_nothing_is_removed(gen, ready):
    with pytest.raises(StaleVersion):
        conclude(gen, version=EM_ANDAMENTO_VERSION - 1)

    assert_nothing_removed(gen, ready)


@pytest.mark.parametrize("status", [S.RASCUNHO, S.ARQUIVADO])
def test_a_process_that_is_not_em_andamento_is_409_and_nothing_is_removed(gen, status):
    world = gen.world
    document, _ = add_input_document(gen)
    add_all_ready(world)
    set_status(world, status)

    with pytest.raises(Conflict):
        conclude(gen)

    after = state_of(gen, document)
    assert (after.file_exists, after.row.file_deleted_at) == (True, None)
    assert stored(gen).status is status


# --- the conclusion -----------------------------------------------------------------------


def test_with_everything_ready_the_files_go_and_the_generated_ones_stay(gen, ready):
    kept = {kind: add_stored_generation(gen, kind) for kind in K}

    result = conclude(gen)

    assert result == ConclusionResult(S.CONCLUIDO, 3, 0, 600)
    process = stored(gen)
    assert (process.status, process.version) == (S.CONCLUIDO, EM_ANDAMENTO_VERSION + 1)
    for document in ready:
        after = state_of(gen, document)
        assert (after.file_exists, after.pages, after.links) == (False, [], [(1, "")])
        assert after.row.file_deleted_at is not None
    for name, content in kept.values():  # DEL-06: the generated files are untouched
        assert gen.generated.path(gen.world.process.id, name).read_bytes() == content
    with gen.world.uow_factory() as uow:
        versions = uow.generations.list_for_process(gen.world.process.id)
    assert len([g for g in versions if g.state is GenerationState.PRONTO]) == 6


def test_the_events_carry_counts_and_no_file_names(gen, ready):
    names = [d.original_name for d in ready] + [d.internal_name for d in ready]
    before = len(events(gen))

    conclude(gen, justification="  Entrega feita  ")

    new = events(gen)[before:]
    purge = [e for e in new if e.changes.get("operation", {}).get("after") == "PURGE"]
    status = [e for e in new if "status" in e.changes]
    assert len(purge) == len(status) == 1 and len(new) == 2
    assert purge[0].action is AuditAction.UPDATE
    assert {k: v["after"] for k, v in purge[0].changes.items()} == {
        "operation": "PURGE",
        "files_removed": 3,
        "files_pending": 0,
        "bytes_removed": 600,
        "bytes_pending": 0,
    }
    assert status[0].action is AuditAction.STATUS
    assert status[0].changes == {"status": {"before": "EM_ANDAMENTO", "after": "CONCLUIDO"}}
    assert status[0].justification == "Entrega feita"
    assert all(e.user_id == gen.world.admin.id for e in new)
    dumped = json.dumps([e.changes for e in new])
    assert not any(name in dumped for name in names)


def test_a_document_outside_the_interstice_is_purged_by_the_conclusion(gen):
    set_status(gen.world, S.EM_ANDAMENTO)
    inside, _ = add_input_document(gen, size=10)
    outside, _ = add_input_document(gen, size=25, outside=True)
    add_all_ready(gen.world)

    result = conclude(gen)

    assert result == ConclusionResult(S.CONCLUIDO, 2, 0, 35)
    for document in (inside, outside):
        after = state_of(gen, document)
        assert (after.file_exists, after.pages) == (False, [])
        assert after.row.file_deleted_at is not None


def test_a_process_without_documents_concludes_with_zero_files(gen):
    set_status(gen.world, S.EM_ANDAMENTO)
    add_all_ready(gen.world)

    result = conclude(gen)

    assert result == ConclusionResult(S.CONCLUIDO, 0, 0, 0)
    assert stored(gen).status is S.CONCLUIDO


@pytest.mark.parametrize("who", ["docente", "secretaria"])
def test_the_owner_docente_and_the_unit_secretaria_can_conclude(gen, ready, who):
    result = conclude(gen, actor=getattr(gen.world, who))

    assert result.status is S.CONCLUIDO


# --- partial failure and repetition ------------------------------------------------------


def test_a_removal_that_fails_keeps_the_process_em_andamento_with_exclusao_parcial(gen, ready):
    stuck = ready[1]
    storage = FlakyStorage(gen.originals, failing={stuck.internal_name})
    before = len(events(gen))

    result = conclude(gen, storage=storage)

    assert (result.status, result.files_removed, result.files_pending) == (S.EM_ANDAMENTO, 2, 1)
    assert result.bytes_freed == 400
    assert [a.code for a in result.alerts] == [GenerationAlertCode.EXCLUSAO_PARCIAL]
    assert stored(gen).status is S.EM_ANDAMENTO
    assert state_of(gen, stuck).file_exists is True
    for done in (ready[0], ready[2]):  # the ones already removed stay removed
        assert state_of(gen, done).row.file_deleted_at is not None
    new = events(gen)[before:]
    assert [e.changes["files_pending"]["after"] for e in new if "files_pending" in e.changes] == [1]
    assert not any("status" in e.changes for e in new)
    assert {k: v["after"] for k, v in new[0].changes.items()} == {
        "operation": "PURGE",
        "files_removed": 2,
        "files_pending": 1,
        "bytes_removed": 400,
        "bytes_pending": 200,
    }


def test_repeating_after_a_partial_failure_concludes(gen, ready):
    storage = FlakyStorage(gen.originals, failing={ready[1].internal_name})
    conclude(gen, storage=storage)

    result = conclude(gen)

    assert result == ConclusionResult(S.CONCLUIDO, 1, 0, 200)
    assert stored(gen).status is S.CONCLUIDO
    assert state_of(gen, ready[1]).row.file_deleted_at is not None


def test_repeating_on_a_concluded_process_answers_ok_and_changes_nothing(gen, ready):
    conclude(gen)
    process, count = stored(gen), len(events(gen))

    again = conclude(gen)

    assert again == ConclusionResult(S.CONCLUIDO, 0, 0, 0)
    assert stored(gen) == process
    assert len(events(gen)) == count


def test_a_document_uploaded_during_the_conclusion_stops_the_transition(gen, ready):
    class UploadsWhileRemoving(FlakyStorage):
        def delete(self, process_id, internal_name):
            super().delete(process_id, internal_name)
            if not self.deleted[1:]:  # right after the first file went
                self.late = add_input_document(gen, size=5)[0]

    storage = UploadsWhileRemoving(gen.originals)

    result = conclude(gen, storage=storage)

    assert (result.status, result.files_removed, result.files_pending) == (S.EM_ANDAMENTO, 3, 1)
    assert [a.code for a in result.alerts] == [GenerationAlertCode.EXCLUSAO_PARCIAL]
    assert stored(gen).status is S.EM_ANDAMENTO
    assert file_of(gen, storage.late).exists()
    assert conclude(gen).status is S.CONCLUIDO  # repeating closes the late document too
    assert not file_of(gen, storage.late).exists()


def test_a_blank_justification_is_stored_as_none(gen, ready):
    conclude(gen, justification="   ")

    status = [e for e in events(gen) if "status" in e.changes]
    assert [e.justification for e in status] == [None]


def test_a_row_only_document_is_closed_without_a_file(gen):
    set_status(gen.world, S.EM_ANDAMENTO)
    row_only = add_document(gen.world, size_bytes=33)
    add_all_ready(gen.world)

    result = conclude(gen)

    assert result == ConclusionResult(S.CONCLUIDO, 1, 0, 33)
    assert state_of(gen, row_only).row.file_deleted_at is not None
