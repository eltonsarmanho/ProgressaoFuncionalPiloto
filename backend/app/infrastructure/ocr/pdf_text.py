"""Text layer of a PDF, page by page, with PyMuPDF (PIPE-04)."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class PdfPageText:
    page_number: int  # 1-based
    text: str
    char_count: int


def pdf_page_count(path: Path) -> int:
    with pymupdf.open(path, filetype="pdf") as doc:
        return doc.page_count


def extract_pdf_page(path: Path, page_number: int) -> PdfPageText:
    """Text layer of one page (1-based); empty for a scanned page."""
    with pymupdf.open(path, filetype="pdf") as doc:
        text = doc[page_number - 1].get_text("text")
    return PdfPageText(page_number, text, len(text))


def extract_pdf_pages(path: Path) -> list[PdfPageText]:
    """Text layer of every page, with its number and character count."""
    with pymupdf.open(path, filetype="pdf") as doc:
        texts = [page.get_text("text") for page in doc]
    return [PdfPageText(number, text, len(text)) for number, text in enumerate(texts, start=1)]
