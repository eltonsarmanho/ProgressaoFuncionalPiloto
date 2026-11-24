"""TAB-01, PMOD-04, PMOD-05: Liberation Serif and Sans are versioned with their license and the
PDFs write accents correctly, with the font embedded as a subset."""

import re
from pathlib import Path

import pymupdf
import pytest
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.domain.entities.report import PageSetup
from app.infrastructure.documents import pdf_styles
from app.infrastructure.documents.pdf_styles import (
    FONT_BOLD,
    FONT_BOLD_ITALIC,
    FONT_ITALIC,
    FONT_REGULAR,
    FONT_SANS,
    FONT_SANS_BOLD,
    PdfCanvas,
    build_styles,
    margins_from_page,
    register_fonts,
)

TEXT = "Ação, Ñandú, Zoë, ç, ü, ª"
FONTS_DIR = Path(pdf_styles.__file__).parent / "fonts"
SUBSET = re.compile(r"^[A-Z]{6}\+LiberationSerif")
SANS_SUBSET = re.compile(r"^[A-Z]{6}\+LiberationSans")
SANS_FILES = ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf")


def one_page(tmp_path, draw) -> pymupdf.Page:
    path = tmp_path / "teste.pdf"
    canvas = PdfCanvas(str(path))
    draw(canvas)
    canvas.showPage()
    canvas.save()
    return pymupdf.open(path)[0]


def test_the_four_ttf_files_and_the_license_text_are_in_the_fonts_folder():
    names = {p.name for p in FONTS_DIR.iterdir()}
    assert {
        "LiberationSerif-Regular.ttf",
        "LiberationSerif-Bold.ttf",
        "LiberationSerif-Italic.ttf",
        "LiberationSerif-BoldItalic.ttf",
    } <= names
    license_text = (FONTS_DIR / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in license_text
    assert "Liberation" in license_text


def test_the_two_sans_ttf_files_are_in_the_fonts_folder_and_open_as_fonts():
    names = {p.name for p in FONTS_DIR.iterdir()}
    assert set(SANS_FILES) <= names
    assert len(list(FONTS_DIR.glob("*.ttf"))) == 6
    for file in SANS_FILES:
        TTFont(file, str(FONTS_DIR / file))


def test_the_license_text_names_liberation_sans_as_well():
    license_text = (FONTS_DIR / "OFL.txt").read_text(encoding="utf-8")

    assert "Liberation Sans" in license_text
    assert "Liberation Serif" in license_text


def test_text_with_accents_comes_back_from_the_pdf_exactly_as_written(tmp_path):
    register_fonts()

    def draw(canvas):
        canvas.setFont(FONT_REGULAR, 12)
        canvas.drawString(72, 700, TEXT)

    page = one_page(tmp_path, draw)

    assert page.get_text().strip() == TEXT


def test_the_font_is_embedded_as_a_subset_not_the_whole_file(tmp_path):
    register_fonts()

    def draw(canvas):
        canvas.setFont(FONT_REGULAR, 12)
        canvas.drawString(72, 700, TEXT)

    page = one_page(tmp_path, draw)

    fonts = page.get_fonts()
    assert len(fonts) == 1
    assert SUBSET.match(fonts[0][3])
    assert (tmp_path / "teste.pdf").stat().st_size < (
        FONTS_DIR / "LiberationSerif-Regular.ttf"
    ).stat().st_size


def test_bold_and_italic_tags_in_a_paragraph_use_the_other_three_faces(tmp_path):
    path = tmp_path / "estilos.pdf"
    styles = build_styles(9)
    document = SimpleDocTemplate(str(path))
    document.build(
        canvasmaker=PdfCanvas,
        flowables=[
            Paragraph("normal <b>negrito</b> <i>itálico</i> <b><i>ambos</i></b>", styles.body)
        ],
    )

    names = {font[3].split("+")[-1] for font in pymupdf.open(path)[0].get_fonts()}

    assert names == {FONT_REGULAR, FONT_BOLD, FONT_ITALIC, FONT_BOLD_ITALIC}


def test_register_fonts_can_be_called_again_without_error():
    register_fonts()
    register_fonts()


def test_register_fonts_registers_the_two_sans_faces():
    register_fonts()

    registered = pdfmetrics.getRegisteredFontNames()
    assert FONT_SANS in registered
    assert FONT_SANS_BOLD in registered


def test_a_pdf_written_in_sans_bold_lists_only_the_sans_subset_and_no_base_14_font(tmp_path):
    def draw(canvas):
        canvas.setFont(FONT_SANS_BOLD, 14)
        canvas.drawString(72, 700, TEXT)

    page = one_page(tmp_path, draw)

    names = [font[3] for font in page.get_fonts()]
    assert page.get_text().strip() == TEXT
    assert len(names) == 1
    assert SANS_SUBSET.match(names[0])
    assert names[0].endswith("LiberationSans-Bold")
    assert not any(base in names[0] for base in ("Helvetica", "Times", "Courier"))


def test_the_regular_sans_face_is_a_subset_of_its_own(tmp_path):
    def draw(canvas):
        canvas.setFont(FONT_SANS, 12)
        canvas.drawString(72, 700, TEXT)

    names = [font[3] for font in one_page(tmp_path, draw).get_fonts()]

    assert len(names) == 1
    assert names[0].endswith("LiberationSans")


def test_the_margins_follow_the_page_setup_of_the_model_in_points():
    page = PageSetup(31.75, 31.75, 25.4, 25.4, "Times New Roman", 9)

    margins = margins_from_page(page)

    assert margins.left == pytest.approx(31.75 * mm)
    assert margins.right == pytest.approx(31.75 * mm)
    assert margins.top == pytest.approx(25.4 * mm)
    assert margins.bottom == pytest.approx(25.4 * mm)


def test_the_styles_use_liberation_serif_at_the_size_asked_and_the_body_is_justified():
    styles = build_styles(9)

    assert styles.body.fontName == FONT_REGULAR
    assert styles.body.fontSize == 9
    assert styles.body.alignment == TA_JUSTIFY
    assert styles.title.alignment == TA_CENTER
    assert styles.title.fontName == FONT_BOLD
    assert styles.cell_header.fontName == FONT_BOLD
