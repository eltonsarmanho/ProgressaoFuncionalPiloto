"""SEG-11 (I02): only the part of an image that lies on the page counts as coverage."""

import io

import pymupdf
import pytest
from PIL import Image

from app.infrastructure.ocr.pdf_text import image_coverage


@pytest.fixture
def pdf_with_image(tmp_path):
    def build(box: tuple[float, float, float, float]):
        picture = io.BytesIO()
        Image.new("L", (100, 100), 128).save(picture, format="PNG")
        doc = pymupdf.open()
        page = doc.new_page()  # A4, 595 x 842 points
        page.insert_image(pymupdf.Rect(*box), stream=picture.getvalue())
        path = tmp_path / "doc.pdf"
        doc.save(path)
        doc.close()
        return path

    return build


def test_an_image_covering_the_page_covers_all_of_it(pdf_with_image):
    assert image_coverage(pdf_with_image((0, 0, 595, 842)), 1) == pytest.approx(1.0, abs=0.01)


def test_an_image_hanging_off_the_page_counts_only_its_visible_part(pdf_with_image):
    # the box is 900 points wide; 295 of them are on the page: 295 / 595 of the page area
    coverage = image_coverage(pdf_with_image((300, 0, 1200, 842)), 1)
    assert coverage == pytest.approx(295 / 595, abs=0.01)
    assert coverage < 0.5  # below the image heavy limit, although the box is larger than the page
