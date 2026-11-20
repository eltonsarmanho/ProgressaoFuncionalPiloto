"""REL-10, CMP-09, CMP-10, CMP-13, DEL-11: requests that cannot succeed are refused with a code
and no row."""

import io

import pytest
from PIL import Image

from app.application.use_cases.generated_documents import GenerationLimits
from app.domain.entities.generated import DocumentKind, GenerationCode
from app.domain.errors import GenerationRefused
from app.domain.rules.comprovante_plan import ComprovanteRefused
from tests.integration.doc_usecases.generation_support import (
    MOMENT,
    add_activity,
    add_document,
    link,
    link_pages,
    store_original,
)
from tests.support import synthetic_docs as synth

MB = 1024 * 1024


def rows(world):
    with world.uow_factory() as uow:
        return list(uow.generations.list_for_process(world.process.id))


def ask(gen, kind, **kwargs):
    return gen.request(**kwargs).execute(gen.world.admin, gen.world.process.id, kind)


def refused(gen, kind, **kwargs) -> GenerationRefused:
    with pytest.raises(GenerationRefused) as error:
        ask(gen, kind, **kwargs)
    assert rows(gen.world) == []
    return error.value


def tiny_pdf() -> bytes:
    return synth.pdf_with_text(["pagina"])


def image(fmt: str, size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("L", size).save(buffer, format=fmt)
    return buffer.getvalue()


def test_an_activity_with_no_title_and_no_description_refuses_the_report_naming_it(gen):
    world = gen.world
    add_activity(world, title="Boa atividade")
    blank = add_activity(world, title="  ", description="")

    error = refused(gen, DocumentKind.RELATORIO)

    assert error.code == GenerationCode.ATIVIDADE_SEM_DESCRICAO
    assert str(blank.id) in error.message


def test_a_title_alone_or_a_description_alone_is_enough_for_the_report(gen):
    world = gen.world
    add_activity(world, title="Só título", description="")
    add_activity(world, title="", description="Só descrição")

    assert ask(gen, DocumentKind.RELATORIO).kind is DocumentKind.RELATORIO


def test_the_table_does_not_need_a_description(gen):
    add_activity(gen.world, title="", description="")

    assert ask(gen, DocumentKind.TABELA).kind is DocumentKind.TABELA


def test_401_attached_pages_refuse_the_comprovante(gen):
    world = gen.world
    activity = add_activity(world)
    document = store_original(gen, world.process, tiny_pdf(), page_count=401)
    link_pages(world, activity, document, range(1, 402))

    error = refused(gen, DocumentKind.COMPROVANTE)

    assert error.code == GenerationCode.COMPROVANTE_GRANDE_DEMAIS


def test_400_attached_pages_are_accepted(gen):
    world = gen.world
    activity = add_activity(world)
    document = store_original(gen, world.process, tiny_pdf(), page_count=400)
    link_pages(world, activity, document, range(1, 401))

    assert ask(gen, DocumentKind.COMPROVANTE).kind is DocumentKind.COMPROVANTE


def test_a_missing_original_refuses_the_comprovante_naming_the_document_and_the_page(gen):
    world = gen.world
    activity = add_activity(world)
    document = add_document(world)  # its file was never stored
    link(world, activity, document, 2)

    error = refused(gen, DocumentKind.COMPROVANTE)

    assert isinstance(error, ComprovanteRefused)
    assert error.code == GenerationCode.ORIGINAL_INDISPONIVEL
    assert (error.document_id, error.page) == (document.id, 2)


def test_a_png_above_12_megapixels_is_refused_naming_the_document(gen):
    world = gen.world
    activity = add_activity(world)
    big = store_original(gen, world.process, image("PNG", (4001, 3000)), "png", page_count=1)
    link(world, activity, big, 1)

    error = refused(gen, DocumentKind.COMPROVANTE)

    assert error.code == GenerationCode.IMAGEM_GRANDE_DEMAIS
    assert error.document_id == big.id


def test_a_png_of_exactly_12_megapixels_is_accepted(gen):
    world = gen.world
    activity = add_activity(world)
    exact = store_original(gen, world.process, image("PNG", (4000, 3000)), "png", page_count=1)
    link(world, activity, exact, 1)

    assert ask(gen, DocumentKind.COMPROVANTE).kind is DocumentKind.COMPROVANTE


def test_a_jpeg_of_the_same_size_as_a_refused_png_is_accepted(gen):
    world = gen.world
    activity = add_activity(world)
    jpeg = store_original(gen, world.process, image("JPEG", (4001, 3000)), "jpg", page_count=1)
    link(world, activity, jpeg, 1)

    assert ask(gen, DocumentKind.COMPROVANTE).kind is DocumentKind.COMPROVANTE


def test_a_deleted_input_document_refuses_the_comprovante_but_not_the_table(gen):
    world = gen.world
    activity = add_activity(world)
    document = add_document(world)
    link(world, activity, document, 1)
    with world.uow_factory() as uow:
        uow.documents.mark_file_deleted(document.id, MOMENT)
        uow.commit()

    error = refused(gen, DocumentKind.COMPROVANTE)
    assert error.code == GenerationCode.ORIGINAIS_EXCLUIDOS

    assert ask(gen, DocumentKind.TABELA).kind is DocumentKind.TABELA


def test_a_link_to_a_document_outside_the_interstice_does_not_refuse_the_comprovante(gen):
    world = gen.world
    activity = add_activity(world)
    outside = add_document(world, outside=True)  # no file, no page can be attached from it
    link(world, activity, outside, 1)

    assert ask(gen, DocumentKind.COMPROVANTE).kind is DocumentKind.COMPROVANTE


class FreeSpace:
    """A storage that only knows how much room is left."""

    def __init__(self, free: int) -> None:
        self._free = free

    def free_bytes(self) -> int:
        return self._free


def test_less_than_the_minimum_free_space_refuses_every_kind(gen):
    add_activity(gen.world)
    limits = GenerationLimits(min_free_bytes=200 * MB)

    for kind in DocumentKind:
        error = refused(gen, kind, storage=FreeSpace(200 * MB - 1), limits=limits)
        assert error.code == GenerationCode.ESPACO_INSUFICIENTE


def test_exactly_the_minimum_free_space_is_enough(gen):
    add_activity(gen.world)
    limits = GenerationLimits(min_free_bytes=200 * MB)

    generation = ask(gen, DocumentKind.TABELA, storage=FreeSpace(200 * MB), limits=limits)

    assert generation.kind is DocumentKind.TABELA
