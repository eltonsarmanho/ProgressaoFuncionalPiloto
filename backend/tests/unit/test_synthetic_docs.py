"""ACC-03: the synthetic generators produce valid files of the right kind."""

import io
import re
import warnings

import pymupdf
import pytest
from PIL import Image

from app.domain.rules.text_quality import is_text_layer_usable
from tests.support import synthetic_docs as docs

PDF_SIGNATURE = b"%PDF-"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"


def open_pdf(data: bytes) -> pymupdf.Document:
    return pymupdf.open(stream=data, filetype="pdf")


def open_image(data: bytes) -> Image.Image:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        return Image.open(io.BytesIO(data))


def symbol_share(text: str) -> float:
    visible = [c for c in text if not c.isspace()]
    symbols = [c for c in visible if not (c.isalnum() or c in ".,;:!?-()/\"'%")]
    return len(symbols) / len(visible)


def test_pdf_with_text_has_signature_pages_and_text_per_page():
    data = docs.pdf_with_text(["Primeira pagina de teste " * 5, "Segunda pagina de teste " * 5])
    assert data.startswith(PDF_SIGNATURE)
    pdf = open_pdf(data)
    assert pdf.page_count == 2
    assert "Primeira pagina" in pdf[0].get_text()
    assert "Segunda pagina" in pdf[1].get_text()


def test_pdf_scanned_has_images_and_no_text_layer():
    data = docs.pdf_scanned(["Pagina digitalizada um", "Pagina digitalizada dois"])
    assert data.startswith(PDF_SIGNATURE)
    pdf = open_pdf(data)
    assert pdf.page_count == 2
    for page in pdf:
        assert page.get_text().strip() == ""
        assert len(page.get_images()) == 1


def test_png_has_png_signature_and_opens():
    data = docs.png_with_text("Texto de teste em imagem")
    assert data.startswith(PNG_SIGNATURE)
    image = open_image(data)
    assert image.format == "PNG"
    assert image.size[0] > 0


def test_jpg_has_jpeg_signature_and_opens():
    data = docs.jpg_with_text("Texto de teste em imagem")
    assert data.startswith(JPEG_SIGNATURE)
    image = open_image(data)
    assert image.format == "JPEG"
    assert image.size[0] > 0


def test_noisy_pdf_text_layer_is_more_than_30_percent_symbols_and_unusable():
    pdf = open_pdf(docs.pdf_noisy_text_layer())
    text = pdf[0].get_text()
    assert symbol_share(text) > 0.30
    assert not is_text_layer_usable(text)


def test_noisy_pdf_still_has_enough_letters_to_isolate_the_symbol_rule():
    text = open_pdf(docs.pdf_noisy_text_layer())[0].get_text()
    assert sum(c.isalnum() for c in text) >= 50


def test_pdf_with_javascript_declares_a_javascript_action():
    data = docs.pdf_with_javascript()
    assert data.startswith(PDF_SIGNATURE)
    assert b"/JavaScript" in data
    assert open_pdf(data).page_count == 1


def test_pdf_encrypted_asks_for_a_password():
    data = docs.pdf_encrypted()
    assert data.startswith(PDF_SIGNATURE)
    assert open_pdf(data).needs_pass


def test_pdf_with_embedded_file_carries_one_attachment():
    data = docs.pdf_with_embedded_file()
    assert data.startswith(PDF_SIGNATURE)
    assert open_pdf(data).embfile_count() == 1


def test_huge_png_is_above_100_megapixels_and_small_on_disk():
    data = docs.png_huge()
    assert data.startswith(PNG_SIGNATURE)
    width, height = open_image(data).size
    assert width * height > 100_000_000
    assert len(data) < 1_000_000


def test_default_pdf_with_text_uses_the_invented_sample():
    pdf = open_pdf(docs.pdf_with_text())
    assert docs.FAKE_PROFESSOR.split()[0] in pdf[0].get_text()


@pytest.mark.parametrize("text", [*docs.SAMPLE_PAGES, docs.noisy_text()])
def test_generated_texts_hold_no_real_cpf_or_siape(text):
    cpfs = re.findall(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", text)
    assert all(set(re.sub(r"\D", "", cpf)) == {"0"} for cpf in cpfs)
    siapes = re.findall(r"SIAPE\s+(\d+)", text)
    assert all(set(siape) == {"0"} for siape in siapes)


def test_fake_identity_constants_are_all_zero_numbers():
    assert set(re.sub(r"\D", "", docs.FAKE_SIAPE)) == {"0"}
    assert set(re.sub(r"\D", "", docs.FAKE_CPF)) == {"0"}
