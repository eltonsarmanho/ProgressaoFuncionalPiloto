"""The Parecer as DOCX, written with python-docx (PAR-03).

A4 portrait with the margins and the font of the page of the model; the institutional header and
the title centered, then each section in the order the model has it: a bold heading, its lines,
the table of the points by group closed by the Total geral, and, at the end, one signature line
for each member of the board. The numbers and the text are the ones of the `OpinionDocument`;
nothing is summed or written here.
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from app.domain.rules.opinion_document import OpinionDocument, OpinionSection
from app.infrastructure.documents.docx_support import add_page_footer, set_default_font, shade
from app.infrastructure.documents.text_safety import xml_safe

_SPACE_AFTER_PT = 6
_SIGNATURE_GAP_PT = 30
_SIGNATURE_RULE = "_" * 42
_VALUE_MM = 30
_GREY = "E6E6E6"
_JUSTIFIED = {"conclusao", "observacoes"}


def _centered(document, text: str, size: float | None = None) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(xml_safe(text))
    run.bold = True
    if size:
        run.font.size = Pt(size)


def _points_table(document, section: OpinionSection, usable_mm: float) -> None:
    rows = list(section.rows)
    if section.total is not None:
        rows.append(section.total)
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = (usable_mm - _VALUE_MM, _VALUE_MM)
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Mm(width)
    for number, row in enumerate(rows):
        cells = table.add_row().cells
        closing = section.total is not None and number == len(rows) - 1
        for cell, width, text in zip(cells, widths, (row.label, row.value), strict=True):
            cell.width = Mm(width)
            run = cell.paragraphs[0].add_run(xml_safe(text))
            run.bold = closing
            if closing:
                shade(cell, _GREY)
        cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _section(document, section: OpinionSection, size: float, usable_mm: float) -> None:
    if section.heading:
        heading = document.add_paragraph()
        heading.paragraph_format.space_before = Pt(size)
        heading.paragraph_format.keep_with_next = True
        heading.add_run(xml_safe(section.heading)).bold = True
    for text in section.lines:
        for line in xml_safe(text).split("\n"):
            paragraph = document.add_paragraph(line)
            if section.key in _JUSTIFIED:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if section.rows or section.total is not None:
        _points_table(document, section, usable_mm)


def _signature(document, name: str, role: str) -> None:
    rule = document.add_paragraph(_SIGNATURE_RULE)
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rule.paragraph_format.space_before = Pt(_SIGNATURE_GAP_PT)
    rule.paragraph_format.space_after = Pt(0)
    rule.paragraph_format.keep_with_next = True
    person = document.add_paragraph()
    person.alignment = WD_ALIGN_PARAGRAPH.CENTER
    person.paragraph_format.space_after = Pt(0)
    person.paragraph_format.keep_with_next = True
    person.add_run(xml_safe(name)).bold = True
    caption = document.add_paragraph(xml_safe(role))
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER


def write_opinion_docx(model: OpinionDocument, target: Path) -> None:
    """Writes the DOCX to `target` (a path, never a stream)."""
    page = model.page
    document = Document()
    set_default_font(document, page.font_name, page.font_size_pt, _SPACE_AFTER_PT)
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(page.margin_left_mm), Mm(page.margin_right_mm)
    section.top_margin, section.bottom_margin = Mm(page.margin_top_mm), Mm(page.margin_bottom_mm)
    usable_mm = 210 - page.margin_left_mm - page.margin_right_mm
    for line in model.header_lines:
        _centered(document, line)
    _centered(document, model.title, page.font_size_pt + 2)
    for part in model.sections:
        _section(document, part, page.font_size_pt, usable_mm)
    for signature in model.signatures:
        _signature(document, signature.name, signature.role)
    add_page_footer(document)
    document.core_properties.title = model.title
    document.save(str(target))
