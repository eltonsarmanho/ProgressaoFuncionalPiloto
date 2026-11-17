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


def image_coverage(path: Path, page_number: int) -> float:
    """Share of the page area (0 to 1) covered by images; overlaps are counted once at most."""
    with pymupdf.open(path, filetype="pdf") as doc:
        page = doc[page_number - 1]
        page_area = page.rect.get_area()
        if page_area <= 0:
            return 0.0
        boxes = (pymupdf.Rect(info["bbox"]) & page.rect for info in page.get_image_info())
        covered = sum(box.get_area() for box in boxes)
    return min(1.0, covered / page_area)
