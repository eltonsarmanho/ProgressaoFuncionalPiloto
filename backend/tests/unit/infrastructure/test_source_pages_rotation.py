"""CMP-03: rotation, annotations and fields of an original page survive in the Comprovante."""

import pymupdf
import pytest

from app.infrastructure.documents.source_pages import STRIP_HEIGHT, attach
from tests.support.pdf_pages import (
    ANNOTATION_AREA,
    add_annotation,
    max_difference,
    render,
    reopened,
    source_pdf,
)


def attached(src: pymupdf.Document, number: int = 3) -> pymupdf.Document:
    out = pymupdf.open()
    attach(out, src, 0, number)
    return reopened(out)


def original_area(page: pymupdf.Page) -> pymupdf.Rect:
    return pymupdf.Rect(0, 0, page.rect.width, page.rect.height - STRIP_HEIGHT)


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_a_rotated_page_keeps_its_rotation_pixel_by_pixel(rotation):
    doc = source_pdf(pages=1)
    doc[0].set_rotation(rotation)
    src = reopened(doc)

    out = attached(src)

    assert src[0].rotation == rotation
    assert (out[0].rect.width, out[0].rect.height - STRIP_HEIGHT) == (
        src[0].rect.width,
        src[0].rect.height,
    )
    assert render(out[0], clip=original_area(out[0])) == render(src[0])


@pytest.mark.parametrize("kind", ["stamp", "freetext", "highlight", "field", "signature"])
def test_annotations_and_fields_stay_visible_within_one_gray_level(kind):
    doc = source_pdf(pages=1)
    add_annotation(doc[0], kind)
    src = reopened(doc)
    plain = reopened(source_pdf(pages=1))
    region = ANNOTATION_AREA

    out = attached(src)

    original = render(src[0], clip=region)
    assert original != render(plain[0], clip=region), "the annotation is not in the source render"
    assert max_difference(render(out[0], clip=region), original) <= 1


def test_a_rotated_page_with_an_annotation_keeps_both():
    doc = source_pdf(pages=1)
    add_annotation(doc[0], "stamp")
    doc[0].set_rotation(90)
    src = reopened(doc)

    out = attached(src)

    assert max_difference(render(out[0], clip=original_area(out[0])), render(src[0])) <= 1


def test_the_source_document_is_not_changed_by_attaching_its_page():
    doc = source_pdf(pages=1)
    add_annotation(doc[0], "stamp")
    doc[0].set_rotation(90)
    src = reopened(doc)
    before = render(src[0])

    attached(src)

    assert src[0].rotation == 90
    assert len(list(src[0].annots())) == 1
    assert render(src[0]) == before
