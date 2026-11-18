"""CMP-09, CMP-10, CMP-13, DEL-11: limits, unavailable sources and hash of the Comprovante plan."""

from dataclasses import replace

import pytest

from app.domain.entities.comprovante import (
    ComprovanteLayout,
    LayoutActivity,
    LayoutPage,
    TocLevel,
)
from app.domain.entities.generated import GenerationCode
from app.domain.errors import GenerationRefused
from app.domain.rules.comprovante_plan import check_comprovante, plan_comprovante, plan_hash
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity, source


def layout_of(*entries):
    return ComprovanteLayout(
        PROCESS_ID,
        tuple(LayoutActivity(a.id, tuple(p), a.group_number, a.item_number) for a, p in entries),
    )


def planned(document, pages, activity=None):
    a = activity or make_activity(2, 7)
    layout = layout_of((a, [LayoutPage(document.id, n) for n in pages]))
    return plan_comprovante(layout, [a], 8)


def refusal(plan, documents, **limits) -> GenerationRefused:
    with pytest.raises(GenerationRefused) as caught:
        check_comprovante(plan, documents, **limits)
    return caught.value


# --- more than 400 attached pages (CMP-09) --------------------------------------------------


def test_400_attached_pages_pass():
    document = source(page_count=500)

    check_comprovante(planned(document, range(1, 401)), [document])


def test_401_attached_pages_are_refused_with_comprovante_grande_demais():
    document = source(page_count=500)

    error = refusal(planned(document, range(1, 402)), [document])

    assert error.code == GenerationCode.COMPROVANTE_GRANDE_DEMAIS


def test_a_remission_does_not_count_as_an_attached_page():
    document = source(page_count=500)
    first, second = make_activity(2, 7), make_activity(2, 7)
    pages = [LayoutPage(document.id, n) for n in range(1, 401)]
    layout = layout_of((first, pages), (second, [LayoutPage(document.id, 1)]))
    plan = plan_comprovante(layout, [first, second], 8)

    check_comprovante(plan, [document])


def test_the_limit_of_pages_is_a_parameter():
    document = source(page_count=50)

    error = refusal(planned(document, range(1, 11)), [document], max_pages=9)

    assert error.code == GenerationCode.COMPROVANTE_GRANDE_DEMAIS


# --- a source that is not available (CMP-10) ------------------------------------------------


def test_a_document_removed_from_the_process_is_original_indisponivel_with_document_and_page():
    present, gone = source(), source(original_name="removido.pdf")
    plan = planned(gone, [3])

    error = refusal(plan, [present])

    assert error.code == GenerationCode.ORIGINAL_INDISPONIVEL
    assert (error.document_id, error.page) == (gone.id, 3)


def test_a_page_beyond_the_document_is_original_indisponivel_with_document_and_page():
    document = source(page_count=5)

    error = refusal(planned(document, [5, 6]), [document])

    assert error.code == GenerationCode.ORIGINAL_INDISPONIVEL
    assert (error.document_id, error.page) == (document.id, 6)


def test_the_last_page_of_the_document_is_available():
    document = source(page_count=5)

    check_comprovante(planned(document, [1, 5]), [document])


# --- a PNG above 12 megapixels (CMP-13) -----------------------------------------------------


def test_a_png_of_12_megapixels_passes():
    image = source(page_count=1, mime="image/png", pixels=12_000_000)

    check_comprovante(planned(image, [1]), [image])


def test_a_png_of_12_megapixels_and_one_pixel_is_refused_citing_the_document():
    image = source(page_count=1, mime="image/png", pixels=12_000_001, original_name="scan.png")

    error = refusal(planned(image, [1]), [image])

    assert error.code == GenerationCode.IMAGEM_GRANDE_DEMAIS
    assert error.document_id == image.id
    assert "scan.png" in error.message


def test_a_jpeg_of_40_megapixels_passes():
    image = source(page_count=1, mime="image/jpeg", pixels=40_000_000)

    check_comprovante(planned(image, [1]), [image])


def test_a_big_png_the_plan_does_not_use_does_not_block_the_comprovante():
    used = source()
    unused = source(page_count=1, mime="image/png", pixels=50_000_000)

    check_comprovante(planned(used, [1]), [used, unused])


def test_the_png_limit_in_megapixels_is_a_parameter():
    image = source(page_count=1, mime="image/png", pixels=6_000_001)

    error = refusal(planned(image, [1]), [image], png_max_megapixels=6)

    assert error.code == GenerationCode.IMAGEM_GRANDE_DEMAIS


# --- a deleted original (DEL-11) ------------------------------------------------------------


def test_a_document_with_its_file_deleted_refuses_the_comprovante():
    document = source(file_deleted=True)

    error = refusal(planned(document, [1]), [document])

    assert error.code == GenerationCode.ORIGINAIS_EXCLUIDOS


def test_a_deleted_file_refuses_even_when_the_plan_does_not_use_that_document():
    used, deleted = source(), source(file_deleted=True)

    error = refusal(planned(used, [1]), [used, deleted])

    assert error.code == GenerationCode.ORIGINAIS_EXCLUIDOS


def test_the_plan_of_the_tabela_is_still_computed_when_the_originals_are_gone():
    document = source(file_deleted=True)

    plan = planned(document, [1, 2])

    assert [e.first_page for e in plan.toc if e.level is TocLevel.ATIVIDADE] == [4]
    assert plan.plan_hash


def test_a_deleted_file_is_reported_before_a_missing_one():
    deleted = source(file_deleted=True)
    gone = source()

    error = refusal(planned(gone, [1]), [deleted])

    assert error.code == GenerationCode.ORIGINAIS_EXCLUIDOS


def test_the_refusal_is_a_generation_refusal_with_a_message():
    document = source(page_count=2)

    error = refusal(planned(document, [3]), [document])

    assert isinstance(error, GenerationRefused)
    assert error.message


# --- the plan hash --------------------------------------------------------------------------


def test_the_hash_is_a_sha256_in_hexadecimal():
    plan = planned(source(), [1])

    assert len(plan.plan_hash) == 64
    int(plan.plan_hash, 16)


def test_the_same_plan_has_the_same_hash():
    first, second = make_activity(2, 7), make_activity(2, 7)
    document = source()
    layout = layout_of(
        (first, [LayoutPage(document.id, 1)]), (second, [LayoutPage(document.id, 2)])
    )

    one = plan_comprovante(layout, [first, second], 8)
    two = plan_comprovante(layout, [second, first], 8)

    assert one.plan_hash == two.plan_hash
    assert plan_hash(one) == one.plan_hash


def test_the_hash_changes_when_the_order_changes():
    first, second = make_activity(2, 7), make_activity(2, 7)
    document = source()
    pages = {first.id: [LayoutPage(document.id, 1)], second.id: [LayoutPage(document.id, 2)]}

    def build(order):
        layout = layout_of(*[(a, pages[a.id]) for a in order])
        return plan_comprovante(layout, [first, second], 8).plan_hash

    assert build([first, second]) != build([second, first])


def test_the_hash_changes_when_a_page_is_removed():
    document = source()
    a = make_activity(2, 7)

    assert planned(document, [1, 2], a).plan_hash != planned(document, [1], a).plan_hash


def test_the_hash_ignores_the_wording_of_a_title():
    document = source()
    a = make_activity(2, 7, title="Antes")
    renamed = replace(a, title="Depois")

    assert planned(document, [1], a).plan_hash == planned(document, [1], renamed).plan_hash
