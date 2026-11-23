"""REQ-02, REQ-03, REQ-05: the Requerimento written as PDF with reportlab, with the same phrases
in the same order as the DOCX of the same model (AD-011)."""

import re
from dataclasses import replace
from datetime import date

import pymupdf
import pytest
from reportlab.lib.units import mm

from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.request_docx import write_request_docx
from app.infrastructure.documents.request_pdf import write_request_pdf
from tests.unit.domain.board_document_support import PROFESSOR
from tests.unit.infrastructure.board_writer_support import request_model
from tests.unit.infrastructure.test_request_docx import PARAGRAPH, texts

FOOTER = re.compile(r"Página \d+ de \d+")


def render(tmp_path, model) -> pymupdf.Document:
    target = tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension
    write_request_pdf(model, target)
    return pymupdf.open(target, filetype="pdf")


def normalized(text: str) -> str:
    return " ".join(text.split())


def pdf_text(pdf) -> str:
    return normalized(FOOTER.sub(" ", " ".join(page.get_text() for page in pdf)))


def docx_text(tmp_path, model) -> str:
    target = tmp_path / "requerimento.docx"
    write_request_docx(model, target)
    return normalized(" ".join(texts(target)))


def test_the_file_is_a_pdf_on_a4_written_at_the_given_path(tmp_path):
    target = tmp_path / ".tmp-0123456789abcdef"
    write_request_pdf(request_model(), target)

    assert target.read_bytes().startswith(b"%PDF")
    page = pymupdf.open(target, filetype="pdf")[0]
    assert (round(page.rect.width), round(page.rect.height)) == (595, 842)


def test_the_pdf_has_the_same_phrases_in_the_same_order_as_the_docx(tmp_path):
    model = request_model(last_opinion=date(2025, 4, 2))

    assert pdf_text(render(tmp_path, model)) == docx_text(tmp_path, model)


def test_the_whole_request_paragraph_and_the_closing_line_are_written(tmp_path):
    text = pdf_text(render(tmp_path, request_model()))

    assert normalized(PARAGRAPH) in text
    assert "Belém, 10 de março de 2025." in text
    positions = [
        text.index(phrase)
        for phrase in (
            "Belém, 10 de março de 2025.",
            "Nestes termos, pede deferimento.",
            "Assinatura do (a) requerente",
            "Matrícula SIAPE: 1234567",
        )
    ]
    assert positions == sorted(positions)


def test_the_blank_city_and_the_blank_evaluation_date_are_written_as_they_are(tmp_path):
    text = pdf_text(render(tmp_path, request_model(city=None, last_opinion=None)))

    assert "__________, 10 de março de 2025." in text
    assert "realizada na data de ___/___/___." in text


def test_a_control_character_does_not_come_out_as_a_box_and_markup_is_written_as_typed(tmp_path):
    professor = replace(PROFESSOR, full_name="Maria\x00 <b>Docente</b> &\x0b da Silva")

    text = pdf_text(render(tmp_path, request_model(professor=professor)))

    assert "Eu, Maria <b>Docente</b> & da Silva, Matrícula SIAPE" in text
    assert "\x00" not in text and "\x0b" not in text


def test_only_the_liberation_serif_faces_are_listed(tmp_path):
    pdf = render(tmp_path, request_model())

    names = {font[3].split("+")[-1] for page in pdf for font in page.get_fonts()}
    assert names
    assert names <= {
        "LiberationSerif", "LiberationSerif-Bold", "LiberationSerif-Italic",
        "LiberationSerif-BoldItalic",
    }  # fmt: skip


def test_the_letter_has_no_page_footer_just_as_the_docx_has_none(tmp_path):
    pdf = render(tmp_path, request_model())

    assert len(pdf) == 1
    assert not FOOTER.search(pdf[0].get_text())


def test_the_first_page_has_the_emblem_centered_on_the_text_above_the_ministry(tmp_path):
    # BRAS-05, BRAS-06
    page = render(tmp_path, request_model())[0]

    images = page.get_images(full=True)
    assert len(images) == 1
    (rect,) = page.get_image_rects(images[0][0])
    text_center = (30 * mm + (page.rect.width - 20 * mm)) / 2  # margins of the model: 30 and 20
    assert rect.width == pytest.approx(20 * mm, abs=0.5)
    assert rect.height == pytest.approx(20 * mm * 351 / 279, abs=0.5)
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(text_center, abs=0.5)
    ministry = page.search_for("MINISTÉRIO DA EDUCAÇÃO")[0]
    assert rect.y1 + 3 * mm <= ministry.y0


def test_the_request_with_the_emblem_is_still_one_page_and_the_sans_is_not_listed(tmp_path):
    # BRAS-08: the emblem adds no page and no font
    pdf = render(tmp_path, request_model(last_opinion=date(2025, 4, 2)))

    assert len(pdf) == 1
    names = {font[3].split("+")[-1] for page in pdf for font in page.get_fonts()}
    assert names and all(name.startswith("LiberationSerif") for name in names)


def test_without_the_emblem_file_the_writer_raises_and_writes_nothing(monkeypatch, tmp_path):
    # BRAS-10
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "requerimento.pdf"

    with pytest.raises(EmblemUnavailable):
        write_request_pdf(request_model(), target)
    assert not target.exists()
