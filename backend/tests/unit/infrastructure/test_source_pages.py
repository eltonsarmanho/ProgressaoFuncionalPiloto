"""CMP-03: an original page goes into the Comprovante with its content unchanged, in a sheet
with a foot strip added below that carries the number of the Comprovante page."""

import pymupdf
import pytest

from app.infrastructure.documents.source_pages import STRIP_HEIGHT, attach
from tests.support.pdf_pages import A4, image_bytes, render, reopened, source_pdf


def attached(src: pymupdf.Document, pno: int = 0, number: int = 7) -> pymupdf.Document:
    out = pymupdf.open()
    attach(out, src, pno, number)
    return reopened(out)


def original_area(page: pymupdf.Page) -> pymupdf.Rect:
    return pymupdf.Rect(0, 0, page.rect.width, page.rect.height - STRIP_HEIGHT)


def test_the_original_area_is_identical_to_the_source_page_pixel_by_pixel():
    src = reopened(source_pdf())

    out = attached(src, 0)

    assert render(out[0], clip=original_area(out[0])) == render(src[0])


def test_the_sheet_is_the_page_plus_a_strip_of_24_points():
    src = reopened(source_pdf())

    out = attached(src, 0)

    assert (out[0].rect.width, out[0].rect.height) == (A4[0], A4[1] + 24)
    assert STRIP_HEIGHT == 24


def test_the_text_is_the_same_and_the_strip_carries_the_number():
    src = reopened(source_pdf())

    out = attached(src, 0, number=12)

    area = original_area(out[0])
    assert out[0].get_text(clip=area) == src[0].get_text()
    strip = pymupdf.Rect(0, area.y1, out[0].rect.width, out[0].rect.height)
    assert out[0].get_text(clip=strip).strip() == "Comprovante p. 12"


def test_the_images_are_embedded_with_the_same_bytes():
    src = reopened(source_pdf())

    out = attached(src, 1)

    assert image_bytes(out, 0) == image_bytes(src, 1)
    assert image_bytes(out, 0)  # the page does have a picture


def test_the_page_asked_for_is_the_one_attached_and_pages_pile_up_in_order():
    src = reopened(source_pdf(pages=3))
    out = pymupdf.open()

    attach(out, src, 2, 5)
    attach(out, src, 0, 6)
    out = reopened(out)

    assert [page.get_text(clip=original_area(page)).split("\n")[0] for page in out] == [
        "Origem pagina 3",
        "Origem pagina 1",
    ]
    strips = [
        page.get_text(clip=pymupdf.Rect(0, page.rect.height - 24, 595, page.rect.height)).strip()
        for page in out
    ]
    assert strips == ["Comprovante p. 5", "Comprovante p. 6"]


@pytest.mark.parametrize("size", [(842.0, 595.0), (300.0, 400.0)])
def test_a_page_of_another_size_keeps_its_own_size_and_pixels(size):
    src = reopened(source_pdf(pages=1, size=size))

    out = attached(src, 0)

    assert (out[0].rect.width, out[0].rect.height) == (size[0], size[1] + STRIP_HEIGHT)
    assert render(out[0], clip=original_area(out[0])) == render(src[0])
