"""The Requerimento as DOCX, written with python-docx (REQ-02, REQ-03, REQ-05).

A4 portrait with the margins and the font of the page of the model. The paragraphs follow the
public PROGEP model in the order of the `RequestDocument`: institutional header and title
centered, the greeting, the marked option, the justified paragraph of the request, the line of
the performance evaluation, place and date, the closing, the signature line with its caption, the
SIAPE and the LGPD note. Nothing is written here that the model does not carry.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from app.domain.rules.request_document import RequestDocument
from app.infrastructure.documents.docx_support import add_emblem, set_default_font
from app.infrastructure.documents.text_safety import xml_safe

_SPACE_AFTER_PT = 8
_SIGNATURE_GAP_PT = 36
_LGPD_SIZE_PT = 9


def _paragraph(document, text: str, alignment=None, *, bold: bool = False, size=None):
    paragraph = document.add_paragraph()
    if alignment is not None:
        paragraph.alignment = alignment
    run = paragraph.add_run(xml_safe(text))
    run.bold = bold
    if size:
        run.font.size = Pt(size)
    return paragraph


def write_request_docx(model: RequestDocument, target: Path) -> None:
    """Writes the DOCX to `target` (a path, never a stream)."""
    page = model.page
    document = Document()
    set_default_font(document, page.font_name, page.font_size_pt, _SPACE_AFTER_PT)
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(page.margin_left_mm), Mm(page.margin_right_mm)
    section.top_margin, section.bottom_margin = Mm(page.margin_top_mm), Mm(page.margin_bottom_mm)
    add_emblem(document)
    center, justify = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY
    for line in model.header_lines:
        _paragraph(document, line, center, bold=True).paragraph_format.space_after = Pt(0)
    title = _paragraph(document, model.title, center, bold=True)
    title.paragraph_format.space_before = Pt(page.font_size_pt)
    title.paragraph_format.space_after = Pt(page.font_size_pt)
    _paragraph(document, model.greeting)
    _paragraph(document, model.option, bold=True)
    _paragraph(document, model.request_paragraph, justify)
    _paragraph(document, model.evaluation_line, justify)
    _paragraph(document, model.place_date_line)
    _paragraph(document, model.closing)
    rule = _paragraph(document, model.signature_line, center)
    rule.paragraph_format.space_before = Pt(_SIGNATURE_GAP_PT)
    rule.paragraph_format.space_after = Pt(0)
    rule.paragraph_format.keep_with_next = True
    caption = _paragraph(document, model.signature_caption, center)
    caption.paragraph_format.space_after = Pt(0)
    caption.paragraph_format.keep_with_next = True
    _paragraph(document, model.siape_line, center)
    heading = _paragraph(document, model.lgpd_heading, bold=True, size=_LGPD_SIZE_PT)
    heading.paragraph_format.space_before = Pt(page.font_size_pt)
    heading.paragraph_format.space_after = Pt(2)
    heading.paragraph_format.keep_with_next = True
    _paragraph(document, model.lgpd_text, justify, size=_LGPD_SIZE_PT)
    document.core_properties.title = model.title
    document.save(str(target))
