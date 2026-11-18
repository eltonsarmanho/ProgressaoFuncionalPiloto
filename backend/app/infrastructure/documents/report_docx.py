"""The activities report as DOCX, written with python-docx (REL-09, REL-11, REL-12).

A4 portrait with the margins, the font and the size of the template; the institutional header
centered, the identification, and the sections that have activity in the order of the template.
Every entry is the text of the draft: a justified bullet paragraph for its first line and one
paragraph for each following line.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from app.domain.entities.report import DocumentSection, ReportDocument
from app.infrastructure.documents.docx_support import add_page_footer, set_default_font, xml_safe

_SPACE_AFTER_PT = 4
_BULLET_TEXT_INDENT = Mm(6.35)  # where the text of a `List Bullet` paragraph starts


def _centered(document, text: str, *, bold: bool = True, size: float | None = None) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(xml_safe(text))
    run.bold = bold
    if size:
        run.font.size = Pt(size)


def _entry(document, text: str) -> None:
    """The first line is a bullet; the other lines follow as paragraphs under its text (a manual
    line break would stretch the justified lines)."""
    lines = xml_safe(text).split("\n")
    for number, line in enumerate(lines):
        if number == 0:
            paragraph = document.add_paragraph(line, style="List Bullet")
        else:
            paragraph = document.add_paragraph(line)
            paragraph.paragraph_format.left_indent = _BULLET_TEXT_INDENT
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        paragraph.paragraph_format.keep_with_next = number < len(lines) - 1
        if number < len(lines) - 1:
            paragraph.paragraph_format.space_after = Pt(0)


def _section(document, section: DocumentSection, size: float) -> None:
    heading = document.add_paragraph()
    heading.paragraph_format.space_before = Pt(size)
    heading.paragraph_format.keep_with_next = True
    heading.add_run(xml_safe(f"{section.key} {section.title}")).bold = True
    if section.free_text:
        for line in section.free_text.split("\n"):
            paragraph = document.add_paragraph(xml_safe(line))
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for group in section.groups:
        if group.subtitle:
            subtitle = document.add_paragraph()
            subtitle.paragraph_format.keep_with_next = True
            run = subtitle.add_run(xml_safe(group.subtitle))
            run.bold = run.italic = True
        for entry in group.entries:
            _entry(document, entry)


def write_report_docx(model: ReportDocument, target: Path) -> None:
    """Writes the DOCX to `target` (a path, never a stream)."""
    page = model.layout.page
    document = Document()
    set_default_font(document, page.font_name, page.font_size_pt, _SPACE_AFTER_PT)
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(page.margin_left_mm), Mm(page.margin_right_mm)
    section.top_margin, section.bottom_margin = Mm(page.margin_top_mm), Mm(page.margin_bottom_mm)
    for line in model.header_lines:
        _centered(document, line)
    _centered(document, model.title, size=page.font_size_pt + 2)
    for line in model.identification:
        document.add_paragraph(xml_safe(line))
    _centered(document, model.body_heading)
    for part in model.sections:
        _section(document, part, page.font_size_pt)
    add_page_footer(document)
    document.core_properties.title = model.title
    document.save(str(target))
