"""Readers of the generated files for the acceptance tests: the text of a DOCX and of a PDF, as a
reader of the document sees it (synthetic data only)."""

import io

import pymupdf
from docx import Document
from docx.table import Table


def docx_text(content: bytes) -> str:
    """The body in order (paragraphs and table cells) and then the footers, on one line."""
    document = Document(io.BytesIO(content))
    pieces: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Table):
            for row in block.rows:
                seen = []
                for cell in row.cells:
                    if cell._tc not in seen:  # a merged cell is listed once per column it covers
                        seen.append(cell._tc)
                        pieces.append(cell.text)
        else:
            pieces.append(block.text)
    for section in document.sections:
        pieces += [p.text for p in section.footer.paragraphs]
    return " ".join(" ".join(pieces).split())


def pdf_text(content: bytes) -> str:
    with pymupdf.open("pdf", content) as pdf:
        return " ".join(" ".join(page.get_text().split()) for page in pdf)


def pt(value: str) -> str:
    """A decimal of the API ("52.00") as the documents write it ("52,00")."""
    return value.replace(".", ",")
