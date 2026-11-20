"""DEL-03, DEL-15: GetConclusionPreview tells the files and bytes the conclusion would free and
which generated kinds have a PRONTO version."""

import uuid

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments
from app.application.use_cases.conclusion import GetConclusionPreview
from app.domain.entities.conclusion import ConclusionPreview
from app.domain.entities.generated import DocumentKind, GenerationState
from app.domain.errors import NotFound
from tests.integration.doc_usecases.conclusion_support import (
    add_all_ready,
    add_generation,
    add_input_document,
)
from tests.integration.doc_usecases.generation_support import add_document
from tests.integration.doc_usecases.test_purge_inputs import FixedClock

K = DocumentKind


def preview_uc(world) -> GetConclusionPreview:
    return GetConclusionPreview(world.uow_factory, world.audit, world.policy)


def all_kinds(value: bool) -> dict:
    return {kind: value for kind in K}


def test_three_documents_give_three_files_the_sum_of_the_sizes_and_each_kind_marked(gen):
    world = gen.world
    for size in (100, 200, 300):
        add_input_document(gen, size=size)
    add_all_ready(world)

    result = preview_uc(world).execute(world.admin, world.process.id)

    assert result == ConclusionPreview(files=3, bytes=600, artifacts=all_kinds(True))


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

    assert result == ConclusionPreview(files=0, bytes=0, artifacts=all_kinds(True))


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
