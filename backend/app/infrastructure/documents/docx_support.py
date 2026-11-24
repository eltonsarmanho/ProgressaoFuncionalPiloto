"""Helpers shared by the DOCX writers: the default font, shading, the footer with the page
fields (`Página N de M`) and the emblem of the UFPA on top of the first page."""

from docx.document import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from docx.text.paragraph import Paragraph

from app.infrastructure.documents.emblem import (
    EMBLEM_GAP_MM,
    emblem_path,
    emblem_size_mm,
)

_FOOTER_SIZE = 8
EMBLEM_ALT_TEXT = "Brasão da Universidade Federal do Pará"


def set_default_font(
    document: DocxDocument, name: str, size_pt: float, space_after_pt: float = 0
) -> None:
    """The font and the spacing of the Normal style; `eastAsia` too, or Word falls back for some
    characters."""
    style = document.styles["Normal"]
    style.font.name = name
    style.font.size = Pt(size_pt)
    style.paragraph_format.space_after = Pt(space_after_pt)
    style.paragraph_format.line_spacing = 1.0
    fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attribute), name)


def shade(cell, fill: str) -> None:
    """Background of a table cell, as a hex color such as `E6E6E6`."""
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _field(paragraph: Paragraph, instruction: str, placeholder: str = "1") -> None:
    """A complex field (`fldChar` begin, instruction, separate, result, end) in `paragraph`."""

    def run_with(element) -> None:
        run = paragraph.add_run()
        run.font.size = Pt(_FOOTER_SIZE)
        run._r.append(element)

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    run_with(begin)
    code = OxmlElement("w:instrText")
    code.set(qn("xml:space"), "preserve")
    code.text = f" {instruction} "
    run_with(code)
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    run_with(separate)
    paragraph.add_run(placeholder).font.size = Pt(_FOOTER_SIZE)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run_with(end)


def add_page_footer(document: DocxDocument) -> None:
    """`Página N de M` centered, with the fields `PAGE` and `NUMPAGES`."""
    paragraph = document.sections[0].footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run("Página ").font.size = Pt(_FOOTER_SIZE)
    _field(paragraph, "PAGE")
    paragraph.add_run(" de ").font.size = Pt(_FOOTER_SIZE)
    _field(paragraph, "NUMPAGES")


def add_emblem(document: DocxDocument) -> None:
    """The emblem as the first paragraph of the body: centered, 20 mm wide, the height in
    proportion, 3 mm of space below (BRAS-06). Call it before any other content. A missing or
    invalid file raises `EmblemUnavailable` before anything is written (BRAS-10)."""
    path = emblem_path()
    width_mm, height_mm = emblem_size_mm()
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Mm(EMBLEM_GAP_MM)
    paragraph.paragraph_format.keep_with_next = True
    picture = paragraph.add_run().add_picture(str(path), width=Mm(width_mm), height=Mm(height_mm))
    picture._inline.docPr.set("descr", EMBLEM_ALT_TEXT)
