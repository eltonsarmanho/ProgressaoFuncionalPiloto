"""Document text extractor: text layer when usable, OCR otherwise (PIPE-04..08).

Implements the `TextExtractor` port. A PDF page uses its text layer (`TEXTO`) when
`is_text_layer_usable` accepts it and OCR (`OCR`) when it does not; images always use OCR.
The whole document has a time limit measured with an injected clock: when it is exceeded the
pages already read are returned with `timed_out=True`. Whether the text is legible enough
(`TEXTO_ILEGIVEL`) is decided by the analyzer from the returned pages.
"""

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from PIL import Image

from app.domain.entities.document import TextMethod
from app.domain.repositories.ports import Clock, ExtractedPage, TextExtraction
from app.domain.rules.text_quality import is_text_layer_usable
from app.domain.rules.upload_validation import FileKind
from app.infrastructure.ocr.pdf_text import extract_pdf_page, pdf_page_count
from app.infrastructure.ocr.render import load_image, render_page
from app.infrastructure.ocr.tesseract import PAGE_TIMEOUT_SECONDS, OcrResult, ocr_image

DOCUMENT_TIMEOUT_SECONDS = 600

OcrFunction = Callable[..., OcrResult]  # (image, timeout_seconds=...) -> OcrResult


class DocumentTextExtractor:
    def __init__(
        self,
        clock: Clock,
        ocr: OcrFunction = ocr_image,
        document_timeout_seconds: float = DOCUMENT_TIMEOUT_SECONDS,
        page_timeout_seconds: float = PAGE_TIMEOUT_SECONDS,
    ) -> None:
        self._clock = clock
        self._ocr = ocr
        self._document_timeout = timedelta(seconds=document_timeout_seconds)
        self._page_timeout = page_timeout_seconds

    def extract(self, path: Path, kind: FileKind) -> TextExtraction:
        started = self._clock.now()
        if kind is FileKind.PDF:
            return self._extract_pdf(path, started)
        if kind in (FileKind.JPEG, FileKind.PNG):
            return self._extract_image(path, started)
        raise ValueError(f"cannot extract text from a {kind} file")

    def _remaining_seconds(self, started) -> float:
        return (self._document_timeout - (self._clock.now() - started)).total_seconds()

    def _ocr_page(self, image: Image.Image, number: int, started) -> ExtractedPage | None:
        """OCR of one page, or None when the page or the document time ran out."""
        remaining = self._remaining_seconds(started)
        result = self._ocr(image, timeout_seconds=min(self._page_timeout, remaining))
        if result.code is not None:
            return None
        return _page(number, TextMethod.OCR, result.text, result.confidence)

    def _extract_pdf(self, path: Path, started) -> TextExtraction:
        pages: list[ExtractedPage] = []
        for number in range(1, pdf_page_count(path) + 1):
            if self._remaining_seconds(started) < 0:
                return TextExtraction(tuple(pages), timed_out=True)
            layer = extract_pdf_page(path, number).text
            if is_text_layer_usable(layer):
                pages.append(_page(number, TextMethod.TEXTO, layer, None))
                continue
            page = self._ocr_page(render_page(path, number), number, started)
            if page is None:
                return TextExtraction(tuple(pages), timed_out=True)
            pages.append(page)
        return TextExtraction(tuple(pages))

    def _extract_image(self, path: Path, started) -> TextExtraction:
        page = self._ocr_page(load_image(path), 1, started)
        if page is None:
            return TextExtraction((), timed_out=True)
        return TextExtraction((page,))


def _page(number: int, method: TextMethod, text: str, confidence: Decimal | None) -> ExtractedPage:
    return ExtractedPage(
        page_number=number,
        method=method,
        char_count=len(text),
        ocr_confidence=confidence,
        text=text,
    )
