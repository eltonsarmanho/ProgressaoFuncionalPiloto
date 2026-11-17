"""PIPE-06: 300 dpi rendering and grayscale preprocessing, for PDF pages and images."""

import pytest
from PIL import Image

from app.infrastructure.ocr.render import load_image, preprocess, render_page
from tests.support import synthetic_docs as docs

A4_AT_300_DPI = (2480, 3508)


@pytest.fixture
def write(tmp_path):
    def run(data: bytes, name: str):
        path = tmp_path / name
        path.write_bytes(data)
        return path

    return run


def test_a4_page_at_300_dpi_is_about_2480_by_3508_pixels(write):
    image = render_page(write(docs.pdf_with_text(), "a.pdf"), 1)
    assert abs(image.width - A4_AT_300_DPI[0]) <= 2
    assert abs(image.height - A4_AT_300_DPI[1]) <= 2


def test_rendered_page_is_grayscale(write):
    assert render_page(write(docs.pdf_with_text(), "a.pdf"), 1).mode == "L"


def test_dpi_scales_the_page(write):
    path = write(docs.pdf_with_text(), "a.pdf")
    low = render_page(path, 1, dpi=150)
    assert abs(low.width - A4_AT_300_DPI[0] / 2) <= 2


def test_render_picks_the_requested_page(write):
    path = write(docs.pdf_mixed(), "mixed.pdf")
    first, second = render_page(path, 1, dpi=72), render_page(path, 2, dpi=72)
    # Text page is mostly white; the scanned page carries a full-page image with a black text.
    assert first.getextrema()[0] < 255
    assert first.tobytes() != second.tobytes()


def test_png_goes_through_the_same_preprocessing(write):
    image = load_image(write(docs.png_with_text(), "a.png"))
    assert image.mode == "L"
    assert image.size == A4_AT_300_DPI


def test_jpg_goes_through_the_same_preprocessing(write):
    image = load_image(write(docs.jpg_with_text(), "a.jpg"))
    assert image.mode == "L"
    assert image.size == A4_AT_300_DPI


def test_autocontrast_stretches_a_low_contrast_image():
    low = Image.new("L", (20, 20), 120)
    low.paste(160, (0, 0, 10, 20))
    assert preprocess(low).getextrema() == (0, 255)


def test_color_image_becomes_grayscale():
    assert preprocess(Image.new("RGB", (10, 10), (200, 30, 30))).mode == "L"


def test_transparent_background_becomes_white_not_black():
    image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    image.putpixel((0, 0), (0, 0, 0, 255))
    result = preprocess(image)
    assert result.getpixel((5, 5)) == 255
    assert result.getpixel((0, 0)) == 0


def test_preprocess_does_not_change_its_input():
    source = Image.new("RGB", (4, 4), (10, 20, 30))
    preprocess(source)
    assert source.mode == "RGB"
    assert source.getpixel((0, 0)) == (10, 20, 30)
