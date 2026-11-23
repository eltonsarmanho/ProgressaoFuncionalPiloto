"""The Parecer as DOCX, written with python-docx (PMOD-01, PMOD-02, PMOD-04 to PMOD-07).

A4 portrait with the margins and the font name of the page of the model, at 12 pt (the 9 pt of the
Relatório is too small for a Parecer). In the order of the `OpinionDocument`: the institutional
header centered with a horizontal rule under it, the title and the place and date line in Arial,
the justified paragraph with its bold runs, and the member lines centered. No table and no page
footer. The text is the one of the model; nothing is composed here.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt
from docx.text.paragraph import Paragraph

from app.domain.rules.opinion_document import OpinionDocument
from app.infrastructure.documents.docx_support import set_default_font
from app.infrastructure.documents.text_safety import xml_safe

_BODY_PT = 12
_SANS = "Arial"
_FIRST_LINE_INDENT_CM = 1.25
_LINE_SPACING = 1.5
_RULE_SIZE_EIGHTHS_PT = 6  # 0.75 pt


def _sans(run) -> None:
    """Arial on a run, `eastAsia` and `cs` too, as `set_default_font` does for the Normal style."""
    run.font.name = _SANS
    fonts = run._r.get_or_add_rPr().get_or_add_rFonts()
    for attribute in ("w:eastAsia", "w:cs"):
        fonts.set(qn(attribute), _SANS)


def _bottom_rule(paragraph: Paragraph) -> None:
    """A single line under the paragraph, across the text width."""
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(_RULE_SIZE_EIGHTHS_PT))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "auto")
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().append(borders)


def _header(document, lines: tuple[str, ...]) -> None:
    for number, line in enumerate(lines):
        paragraph = document.add_paragraph(xml_safe(line))
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        if number == len(lines) - 1:
            paragraph.paragraph_format.space_after = Pt(_BODY_PT)
            _bottom_rule(paragraph)


def write_opinion_docx(model: OpinionDocument, target: Path) -> None:
    """Writes the DOCX to `target` (a path, never a stream)."""
    page = model.page
    document = Document()
    set_default_font(document, page.font_name, _BODY_PT, _BODY_PT / 2)
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(page.margin_left_mm), Mm(page.margin_right_mm)
    section.top_margin, section.bottom_margin = Mm(page.margin_top_mm), Mm(page.margin_bottom_mm)
    usable_mm = 210 - page.margin_left_mm - page.margin_right_mm
    _header(document, model.header_lines)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(_BODY_PT)
    title.paragraph_format.space_after = Pt(2 * _BODY_PT)
    title_run = title.add_run(xml_safe(model.title))
    title_run.bold = True
    _sans(title_run)
    line = document.add_paragraph()
    line.paragraph_format.left_indent = Mm(usable_mm / 2)
    line.paragraph_format.space_after = Pt(2 * _BODY_PT)
    _sans(line.add_run(xml_safe(model.place_date_line)))
    body = document.add_paragraph()
    body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    body.paragraph_format.first_line_indent = Cm(_FIRST_LINE_INDENT_CM)
    body.paragraph_format.line_spacing = _LINE_SPACING
    body.paragraph_format.space_after = Pt(3 * _BODY_PT)
    for part in model.paragraph:
        body.add_run(xml_safe(part.text)).bold = part.bold or None
    for member_line in model.member_lines:
        paragraph = document.add_paragraph(xml_safe(member_line))
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.core_properties.title = model.title
    document.save(str(target))
