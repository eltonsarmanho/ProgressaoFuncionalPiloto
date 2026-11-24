"""BRAS-06, BRAS-07, BRAS-10: the emblem in the PDFs, as the first flowable of a document and drawn
on a canvas for the cover of the Comprovante: centered, 20 mm wide, the height in proportion and
3 mm of space below, and a failure when the file is not there."""

import pymupdf
import pytest
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from app.infrastructure.documents import emblem
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.pdf_styles import (
    PdfCanvas,
    build_styles,
    draw_emblem,
    emblem_flowables,
)

WIDTH_PT = 20 * mm  # 56.69
HEIGHT_PT = WIDTH_PT * 351 / 279
LEFT, RIGHT = 25 * mm, 15 * mm  # asymmetric on purpose: the center is of the text, not the page
TEXT = "Primeira linha do documento"


def build(path, size=A4, extra=()):
    styles = build_styles(11)
    story = [*emblem_flowables(), Paragraph(TEXT, styles.body), *extra]
    SimpleDocTemplate(
        str(path), pagesize=size, leftMargin=LEFT, rightMargin=RIGHT, topMargin=20 * mm,
        bottomMargin=20 * mm,
    ).build(story, canvasmaker=PdfCanvas)  # fmt: skip
    return pymupdf.open(path)


def emblem_rect(page) -> pymupdf.Rect:
    images = page.get_images(full=True)
    assert len(images) == 1
    rects = page.get_image_rects(images[0][0])
    assert len(rects) == 1
    return rects[0]


def test_the_emblem_is_20_mm_wide_with_the_proportional_height_and_centered_on_the_text(tmp_path):
    page = build(tmp_path / "a.pdf")[0]
    rect = emblem_rect(page)
    assert rect.width == pytest.approx(WIDTH_PT, abs=0.5)
    assert rect.height == pytest.approx(HEIGHT_PT, abs=0.5)
    text_center = (LEFT + (page.rect.width - RIGHT)) / 2
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(text_center, abs=0.5)


def test_the_emblem_is_above_the_first_line_with_at_least_3_mm_of_space(tmp_path):
    page = build(tmp_path / "a.pdf")[0]
    rect = emblem_rect(page)
    first_word = min(page.get_text("words"), key=lambda word: word[1])
    assert rect.y1 <= first_word[1] - 3 * mm
    assert rect.y0 < first_word[1]


def test_the_space_below_the_emblem_is_exactly_3_mm(tmp_path):
    # BRAS-06: the Spacer after the image is 3 mm, and in the page the first line starts no more
    # than the 3 mm plus the leading of its own paragraph below the image (a 12 mm gap fails)
    image, spacer = emblem_flowables()
    assert spacer.height == pytest.approx(3 * mm)

    page = build(tmp_path / "a.pdf")[0]
    gap = min(page.get_text("words"), key=lambda word: word[1])[1] - emblem_rect(page).y1
    assert 3 * mm <= gap <= 3 * mm + build_styles(11).body.leading


def test_on_a_landscape_page_it_is_centered_on_the_landscape_text_area(tmp_path):
    page = build(tmp_path / "paisagem.pdf", size=landscape(A4))[0]
    rect = emblem_rect(page)
    assert page.rect.width > page.rect.height
    text_center = (LEFT + (page.rect.width - RIGHT)) / 2
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(text_center, abs=0.5)
    assert rect.width == pytest.approx(WIDTH_PT, abs=0.5)


def test_only_the_first_page_has_the_emblem(tmp_path):
    styles = build_styles(11)
    extra = [PageBreak(), Paragraph("Segunda página", styles.body)]
    document = build(tmp_path / "duas.pdf", extra=extra)
    assert document.page_count == 2
    assert len(document[0].get_images()) == 1
    assert document[1].get_images() == []


def test_the_emblem_adds_no_font_to_the_pdf(tmp_path):
    document = build(tmp_path / "fontes.pdf")
    names = {font[3] for font in document[0].get_fonts()}
    assert names
    assert all("LiberationSerif" in name for name in names)


def test_draw_emblem_puts_the_picture_with_the_asked_center_and_top(tmp_path):
    path = tmp_path / "capa.pdf"
    canvas = PdfCanvas(str(path), pagesize=A4)
    draw_emblem(canvas, center_x=A4[0] / 2, top_y=A4[1] - 30 * mm)
    canvas.showPage()
    canvas.save()
    page = pymupdf.open(path)[0]
    rect = emblem_rect(page)
    assert (rect.x0 + rect.x1) / 2 == pytest.approx(A4[0] / 2, abs=0.5)
    assert rect.y0 == pytest.approx(30 * mm, abs=0.5)  # pymupdf counts y from the top
    assert rect.width == pytest.approx(WIDTH_PT, abs=0.5)
    assert rect.height == pytest.approx(HEIGHT_PT, abs=0.5)


def test_without_the_file_both_helpers_raise(monkeypatch, tmp_path):
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    with pytest.raises(EmblemUnavailable, match="ufpa.png"):
        emblem_flowables()
    canvas = PdfCanvas(str(tmp_path / "x.pdf"), pagesize=A4)
    with pytest.raises(EmblemUnavailable, match="ufpa.png"):
        draw_emblem(canvas, 100, 700)
