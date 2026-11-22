"""DEL-03, DEL-15, DOS-07, PORT-09: GetConclusionPreview tells the files and bytes the conclusion
would free (the ordinance file included), which generated kinds have a PRONTO version and which
board documents are still missing."""

import uuid

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments
from app.application.use_cases.conclusion import GetConclusionPreview
from app.domain.entities.conclusion import ConclusionPreview
from app.domain.entities.generated import ARTIFACT_KINDS, DocumentKind, GenerationState
from app.domain.errors import NotFound
from tests.integration.doc_usecases.board_support import MEMBERS
from tests.integration.doc_usecases.conclusion_support import (
    add_all_ready,
    add_generation,
    add_input_document,
    add_ordinance,
)
from tests.integration.doc_usecases.generation_support import add_document
from tests.integration.doc_usecases.test_purge_inputs import FixedClock

K = DocumentKind
NO_BOARD_DOCUMENT = ("REQUERIMENTO", "PORTARIA_BANCA", "PARECER")


def preview_uc(world) -> GetConclusionPreview:
    return GetConclusionPreview(world.uow_factory, world.audit, world.policy)


def all_kinds(value: bool) -> dict:
    return {kind: value for kind in ARTIFACT_KINDS}


def test_three_documents_give_three_files_the_sum_of_the_sizes_and_each_kind_marked(gen):
    world = gen.world
    for size in (100, 200, 300):
        add_input_document(gen, size=size)
    add_all_ready(world)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result == ConclusionPreview(
        files=3, bytes=600, artifacts=all_kinds(True), pending_board=NO_BOARD_DOCUMENT
    )


def test_only_a_ready_version_marks_its_kind(gen):
    world = gen.world
    add_generation(world, K.TABELA)
    add_generation(world, K.RELATORIO, GenerationState.FALHOU)
    add_generation(world, K.COMPROVANTE, GenerationState.GERANDO)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result.artifacts == {K.TABELA: True, K.RELATORIO: False, K.COMPROVANTE: False}


def test_a_document_outside_the_interstice_is_counted_in_the_preview(gen):
    world = gen.world
    add_input_document(gen, size=10)
    add_input_document(gen, size=25, outside=True)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert (result.files, result.bytes) == (2, 35)


def test_after_the_conclusion_it_is_zero_files_and_zero_bytes(gen):
    world = gen.world
    add_input_document(gen, size=10)
    add_input_document(gen, size=25, outside=True)
    add_all_ready(world)
    PurgeInputDocuments(world.uow_factory, gen.originals, FixedClock()).execute(world.process.id)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result == ConclusionPreview(
        files=0, bytes=0, artifacts=all_kinds(True), pending_board=NO_BOARD_DOCUMENT
    )


def test_a_process_without_documents_gives_zeros(gen):
    result = preview_uc(gen.world).execute(gen.world.admin, gen.world.process.id)

    assert (result.files, result.bytes) == (0, 0)


def test_a_document_already_purged_is_not_counted_again(gen):
    world = gen.world
    add_input_document(gen, size=10)
    gone = add_document(world, size_bytes=99)
    with world.uow_factory() as uow:
        uow.documents.mark_file_deleted(gone.id, FixedClock().now())
        uow.commit()

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert (result.files, result.bytes) == (1, 10)


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_outside_the_access_the_process_is_not_found(gen, who):
    world = gen.world
    add_input_document(gen)

    with pytest.raises(NotFound):
        preview_uc(world).execute(getattr(world, who), world.process.id)


def test_a_missing_process_is_not_found(gen):
    with pytest.raises(NotFound):
        preview_uc(gen.world).execute(gen.world.admin, uuid.uuid4())


@pytest.mark.parametrize("who", ["docente", "secretaria"])
def test_the_owner_docente_and_the_unit_secretaria_can_read_it(gen, who):
    world = gen.world
    add_input_document(gen, size=7)

    result = preview_uc(world).execute(getattr(world, who), world.process.id)

    assert (result.files, result.bytes) == (1, 7)


# --- the ordinance (DOS-07, PORT-09) ------------------------------------------------------


def test_a_document_and_an_ordinance_file_give_two_files_and_the_bytes_of_both(gen):
    world = gen.world
    add_input_document(gen, size=100)
    add_ordinance(gen, size=40)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert (result.files, result.bytes) == (2, 140)


def test_an_ordinance_without_a_file_or_with_the_file_already_removed_is_not_counted(gen):
    world = gen.world
    add_input_document(gen, size=100)
    add_ordinance(gen, stored=False)  # only typed data

    assert preview_uc(world).execute(world.admin, world.process.id).files == 1

    with world.uow_factory() as uow:
        uow.board.mark_file_deleted(world.process.id, FixedClock().now())  # no file to mark
        uow.commit()
    assert (preview_uc(world).execute(world.admin, world.process.id).bytes) == 100


def test_the_ordinance_file_the_conclusion_removed_is_not_counted_again(gen):
    world = gen.world
    add_ordinance(gen, size=40)
    PurgeInputDocuments(world.uow_factory, gen.originals, FixedClock()).execute(world.process.id)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert (result.files, result.bytes) == (0, 0)


def test_the_pending_board_documents_leave_the_list_as_each_one_exists(gen):
    world = gen.world

    def pending():
        return preview_uc(world).execute(world.admin, world.process.id).pending_board

    assert pending() == ("REQUERIMENTO", "PORTARIA_BANCA", "PARECER")
    add_generation(world, K.REQUERIMENTO)
    assert pending() == ("PORTARIA_BANCA", "PARECER")
    add_ordinance(gen, stored=False, members=MEMBERS)  # registered with members, no file
    assert pending() == ("PARECER",)
    add_generation(world, K.PARECER)
    assert pending() == ()


def test_an_ordinance_without_members_still_counts_as_pending_even_with_a_file(gen):
    world = gen.world
    add_ordinance(gen, members=())

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result.files == 1
    assert "PORTARIA_BANCA" in result.pending_board


def test_a_failed_or_running_requerimento_or_parecer_is_still_pending(gen):
    world = gen.world
    add_generation(world, K.REQUERIMENTO, GenerationState.FALHOU)
    add_generation(world, K.PARECER, GenerationState.GERANDO)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result.pending_board == ("REQUERIMENTO", "PORTARIA_BANCA", "PARECER")
    assert set(result.artifacts) == set(ARTIFACT_KINDS)
