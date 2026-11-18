"""Document text extractor: text layer when usable, OCR otherwise (PIPE-04..08).

Implements the `TextExtractor` port. A PDF page uses its text layer (`TEXTO`) when
`is_text_layer_usable` accepts it and OCR (`OCR`) when it does not; images always use OCR. A page
that is mostly image with a thin layer (header and footer only) is OCR'd too and keeps the OCR
text when it is longer.
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
from app.domain.rules.text_quality import (
    MIN_OCR_CONFIDENCE,
    is_text_layer_thin,
    is_text_layer_usable,
)
from app.domain.rules.upload_validation import FileKind
from app.infrastructure.ocr.pdf_text import extract_pdf_page, image_coverage, pdf_page_count
from app.infrastructure.ocr.render import PageTooLarge, load_image, render_page
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

    def _layer_or_ocr(self, path: Path, number: int, layer: str, started) -> ExtractedPage:
        """The text layer page; a mostly-image page with a thin layer is also read by OCR.

        When the OCR is confident and has more useful text, the page is `OCR` and keeps the
        layer text (header and footer) after the OCR text, so nothing of either is lost.
        """
        page = _page(number, TextMethod.TEXTO, layer, None)
        if not is_text_layer_thin(layer, image_coverage(path, number)):
            return page
        try:
            image = render_page(path, number)
        except PageTooLarge:
            return page
        ocr_page = self._ocr_page(image, number, started)
        if ocr_page is None or ocr_page.ocr_confidence is None:
            return page
        if ocr_page.ocr_confidence < MIN_OCR_CONFIDENCE or _useful(ocr_page.text) <= _useful(layer):
            return page
        return _page(number, TextMethod.OCR, f"{ocr_page.text}\n{layer}", ocr_page.ocr_confidence)

    def _extract_pdf(self, path: Path, started) -> TextExtraction:
        pages: list[ExtractedPage] = []
        for number in range(1, pdf_page_count(path) + 1):
            if self._remaining_seconds(started) < 0:
                return TextExtraction(tuple(pages), timed_out=True)
            layer = extract_pdf_page(path, number).text
            if is_text_layer_usable(layer):
                pages.append(self._layer_or_ocr(path, number, layer, started))
                continue
            try:
                image = render_page(path, number)
            except PageTooLarge:  # the page fails, the document goes on (VER-02)
                pages.append(_page(number, TextMethod.OCR, "", Decimal(0)))
                continue
            page = self._ocr_page(image, number, started)
            if page is None:
                return TextExtraction(tuple(pages), timed_out=True)
            pages.append(page)
        return TextExtraction(tuple(pages))

    def _extract_image(self, path: Path, started) -> TextExtraction:
        page = self._ocr_page(load_image(path), 1, started)
        if page is None:
            return TextExtraction((), timed_out=True)
        return TextExtraction((page,))


def _useful(text: str) -> int:
    return sum(1 for char in text if char.isalnum())


def _page(number: int, method: TextMethod, text: str, confidence: Decimal | None) -> ExtractedPage:
    return ExtractedPage(
        page_number=number,
        method=method,
        char_count=len(text),
        ocr_confidence=confidence,
        text=text,
    )
