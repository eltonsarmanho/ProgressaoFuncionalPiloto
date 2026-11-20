"""The Tabela de Pontuação as DOCX, written with python-docx (TAB-01, TAB-03 to TAB-06, GTAB-04).

A4 landscape. The column widths are written in `tblGrid` and in every cell with `tblLayout fixed`
(with autofit, python-docx ignores the widths and LibreOffice splits the columns evenly); the
first row is a header row that repeats on every page; each group is a band of merged cells;
the footer carries the `PAGE` and `NUMPAGES` fields. The content is the one of the PDF.
"""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Mm, Pt

from app.domain.rules.table_document import TableDocument
from app.infrastructure.documents.docx_support import add_page_footer, set_default_font, shade
from app.infrastructure.documents.table_text import (
    ALERTS_HEADING,
    COLUMNS,
    PIT_COLUMNS,
    PIT_TOTAL_LABEL,
    TITLE,
    alert_line,
    band_subtotal,
    band_title,
    counters_line,
    identification_lines,
    pit_heading,
    total_line,
)
from app.infrastructure.documents.text_safety import xml_safe

FONT_NAME = "Times New Roman"
FONT_SIZE = 8
MARGIN_MM = 15
PAGE_MM = (297, 210)
# Fixed widths in mm; the activity column takes the rest of the line.
_FIXED_MM = (14, None, 26, 30, 26)
_GREY = "E6E6E6"
_LIGHT = "F5F5F5"


def _widths() -> list[float]:
    usable = PAGE_MM[0] - 2 * MARGIN_MM
    fixed = sum(w for w in _FIXED_MM if w is not None)
    return [usable - fixed if w is None else w for w in _FIXED_MM]


def _write_cell(cell, text: str, *, bold: bool = False, align=None) -> None:
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(xml_safe(text))
    run.bold = bold
    if align is not None:
        paragraph.alignment = align


def _set_widths(table, widths_mm: list[float]) -> None:
    """`tblGrid` and each cell with the same widths, and the fixed layout Word obeys."""
    table.autofit = False
    for column, width in zip(table.columns, widths_mm, strict=True):
        column.width = Mm(width)
    for row in table.rows:
        for cell, width in zip(row.cells, widths_mm, strict=True):
            cell.width = Mm(width)


def _mark_header_row(row) -> None:
    properties = row._tr.get_or_add_trPr()
    properties.append(OxmlElement("w:tblHeader"))
    properties.append(OxmlElement("w:cantSplit"))


def _band(table, widths: list[float], title: str, subtotal: str, fill: str, bold=True) -> None:
    row = table.add_row()
    for cell, width in zip(row.cells, widths, strict=True):
        cell.width = Mm(width)
    left = row.cells[0].merge(row.cells[2])
    right = row.cells[3].merge(row.cells[4])
    _write_cell(left, title, bold=bold)
    _write_cell(right, subtotal, bold=bold)
    for cell in (left, right):
        shade(cell, fill)


def _main_table(document, model: TableDocument) -> None:
    widths = _widths()
    table = document.add_table(rows=1, cols=len(COLUMNS))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, name in zip(table.rows[0].cells, COLUMNS, strict=True):
        _write_cell(cell, name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        shade(cell, _GREY)
    _mark_header_row(table.rows[0])
    for band in model.bands:
        _band(table, widths, band_title(band), band_subtotal(band), _LIGHT)
        for item in band.rows:
            row = table.add_row()
            cells = (item.item, item.title, item.quantity, item.unit_points, item.points)
            for cell, text in zip(row.cells, cells, strict=True):
                _write_cell(cell, text)
    row = table.add_row()
    total = row.cells[0].merge(row.cells[4])
    _write_cell(total, total_line(model), bold=True)
    shade(total, _GREY)
    _set_widths(table, widths)


def _pit_table(document, model: TableDocument) -> None:
    pit = model.pit_hours
    document.add_paragraph().add_run(pit_heading(pit)).bold = True
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    for cell, name in zip(table.rows[0].cells, PIT_COLUMNS, strict=True):
        _write_cell(cell, name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        shade(cell, _GREY)
    _mark_header_row(table.rows[0])
    for period in pit.periods:
        row = table.add_row()
        _write_cell(row.cells[0], period.label)
        _write_cell(row.cells[1], period.hours)
    row = table.add_row()
    _write_cell(row.cells[0], PIT_TOTAL_LABEL, bold=True)
    _write_cell(row.cells[1], pit.total, bold=True)
    _set_widths(table, [60, 30])


def write_table_docx(model: TableDocument, target: Path) -> None:
    """Writes the DOCX to `target` (a path, never a stream)."""
    document = Document()
    set_default_font(document, FONT_NAME, FONT_SIZE)
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Mm(PAGE_MM[0]), Mm(PAGE_MM[1])
    section.left_margin = section.right_margin = Mm(MARGIN_MM)
    section.top_margin, section.bottom_margin = Mm(MARGIN_MM), Mm(20)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(TITLE)
    run.bold = True
    run.font.size = Pt(FONT_SIZE + 3)
    for line in identification_lines(model):
        document.add_paragraph(xml_safe(line))
    document.add_paragraph()
    _main_table(document, model)
    document.add_paragraph()
    document.add_paragraph(counters_line(model))
    if model.pit_hours is not None:
        _pit_table(document, model)
    if model.alerts:
        document.add_paragraph().add_run(ALERTS_HEADING).bold = True
        for alert in model.alerts:
            document.add_paragraph(xml_safe(alert_line(alert)))
    add_page_footer(document)
    document.core_properties.title = "Tabela de Pontuação"
    document.save(str(target))
