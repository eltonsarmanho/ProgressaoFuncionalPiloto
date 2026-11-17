"""PIPE-04..08 and the mixed-PDF edge case: per-page method choice and the time limit."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.entities.document import DocAlertCode, TextMethod
from app.domain.rules.text_quality import ocr_needs_review
from app.domain.rules.upload_validation import FileKind
from app.infrastructure.ocr.extractor import DocumentTextExtractor
from app.infrastructure.ocr.tesseract import OcrResult
from tests.support import synthetic_docs as docs

TEXT_PAGE = (
    "Declaramos que Fulana de Tal Exemplo participou como membro da banca examinadora "
    "do trabalho de conclusao de curso, realizada em 12 de marco de 2025."
)


class FakeClock:
    def __init__(self):
        self.moment = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self):
        return self.moment

    def advance(self, seconds: float):
        self.moment += timedelta(seconds=seconds)


class FakeOcr:
    """Records each call; `advance` moves the fake clock by that many seconds per call."""

    def __init__(self, clock=None, advance=0.0, results=None):
        self.calls: list[tuple[tuple[int, int], float]] = []
        self._clock, self._advance = clock, advance
        self._results = list(results or [])

    def __call__(self, image, timeout_seconds):
        self.calls.append((image.size, timeout_seconds))
        if self._clock:
            self._clock.advance(self._advance)
        if self._results:
            return self._results.pop(0)
        return OcrResult(text=f"texto ocr {len(self.calls)}", confidence=Decimal("88.00"))


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def write(tmp_path):
    def run(data: bytes, name: str):
        path = tmp_path / name
        path.write_bytes(data)
        return path

    return run


def extractor(clock, ocr=None, **kwargs):
    return DocumentTextExtractor(clock, ocr=ocr or FakeOcr(), **kwargs)


def test_pdf_with_text_uses_the_text_layer_on_every_page(clock, write):
    ocr = FakeOcr()
    path = write(docs.pdf_with_text([TEXT_PAGE, TEXT_PAGE + " Segunda."]), "a.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert [p.method for p in result.pages] == [TextMethod.TEXTO, TextMethod.TEXTO]
    assert [p.page_number for p in result.pages] == [1, 2]
    assert [p.ocr_confidence for p in result.pages] == [None, None]
    assert [p.char_count for p in result.pages] == [len(p.text) for p in result.pages]
    assert "banca" in result.pages[0].text
    assert result.timed_out is False
    assert ocr.calls == []


def test_scanned_pdf_uses_ocr_and_reads_the_invented_words(clock, write):
    from app.infrastructure.ocr.tesseract import ocr_image

    path = write(docs.pdf_scanned(), "scan.pdf")

    result = DocumentTextExtractor(clock, ocr=ocr_image).extract(path, FileKind.PDF)

    assert [p.method for p in result.pages] == [TextMethod.OCR]
    text = result.pages[0].text.lower()
    assert "banca" in text and "fulana" in text and "ficticio" in text
    assert result.pages[0].ocr_confidence > Decimal(60)
    assert result.pages[0].char_count == len(result.pages[0].text)


def test_mixed_pdf_uses_text_on_the_first_page_and_ocr_on_the_rest(clock, write):
    ocr = FakeOcr()
    path = write(docs.pdf_mixed(TEXT_PAGE), "mixed.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert [(p.page_number, p.method) for p in result.pages] == [
        (1, TextMethod.TEXTO),
        (2, TextMethod.OCR),
    ]
    assert result.pages[1].text == "texto ocr 1"
    assert result.pages[1].ocr_confidence == Decimal("88.00")
    assert len(ocr.calls) == 1
    assert ocr.calls[0][0] == pytest.approx((2480, 3508), abs=2)


def test_noisy_text_layer_falls_back_to_ocr(clock, write):
    ocr = FakeOcr()
    path = write(docs.pdf_noisy_text_layer(), "n.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert [p.method for p in result.pages] == [TextMethod.OCR]
    assert result.pages[0].text == "texto ocr 1"
    assert "portaria" not in result.pages[0].text
    assert len(ocr.calls) == 1


def test_png_uses_ocr_and_reads_the_invented_words(clock, write):
    from app.infrastructure.ocr.tesseract import ocr_image

    result = DocumentTextExtractor(clock, ocr=ocr_image).extract(
        write(docs.png_with_text(), "a.png"), FileKind.PNG
    )

    assert [(p.page_number, p.method) for p in result.pages] == [(1, TextMethod.OCR)]
    assert "banca" in result.pages[0].text.lower()
    assert result.pages[0].ocr_confidence > Decimal(60)


def test_jpg_uses_ocr_and_reads_the_invented_words(clock, write):
    from app.infrastructure.ocr.tesseract import ocr_image

    result = DocumentTextExtractor(clock, ocr=ocr_image).extract(
        write(docs.jpg_with_text(), "a.jpg"), FileKind.JPEG
    )

    assert [p.method for p in result.pages] == [TextMethod.OCR]
    assert "examinadora" in result.pages[0].text.lower()


def test_blank_image_gives_a_page_the_analyzer_flags_as_illegible(clock, write):
    from PIL import Image

    from app.infrastructure.ocr.tesseract import ocr_image

    path = write(docs.png_with_text(""), "blank.png")
    assert Image.open(path).size == (2480, 3508)

    page = DocumentTextExtractor(clock, ocr=ocr_image).extract(path, FileKind.PNG).pages[0]

    assert page.text.strip() == ""
    assert page.ocr_confidence is None
    assert ocr_needs_review(page.ocr_confidence, page.text) is True


def test_document_over_10_minutes_keeps_the_pages_already_read(clock, write):
    ocr = FakeOcr(clock, advance=360)  # 6 minutes per page
    path = write(docs.pdf_scanned(["um", "dois", "tres", "quatro"]), "slow.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert result.timed_out is True
    assert [p.page_number for p in result.pages] == [1, 2]
    assert [p.text for p in result.pages] == ["texto ocr 1", "texto ocr 2"]
    assert len(ocr.calls) == 2


def test_exactly_10_minutes_is_not_over_the_limit(clock, write):
    ocr = FakeOcr(clock, advance=600)
    path = write(docs.pdf_scanned(["um", "dois"]), "edge.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert result.timed_out is False
    assert [p.page_number for p in result.pages] == [1, 2]


def test_ocr_timeout_on_a_page_stops_and_keeps_the_previous_pages(clock, write):
    timeout = OcrResult(text="", confidence=None, code=DocAlertCode.TEMPO_ESGOTADO)
    ocr = FakeOcr(results=[OcrResult("pagina um", Decimal("90")), timeout])
    path = write(docs.pdf_scanned(["um", "dois", "tres"]), "page-timeout.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert result.timed_out is True
    assert [p.text for p in result.pages] == ["pagina um"]
    assert len(ocr.calls) == 2


def test_image_whose_ocr_times_out_returns_no_pages(clock, write):
    timeout = OcrResult(text="", confidence=None, code=DocAlertCode.TEMPO_ESGOTADO)

    result = extractor(clock, FakeOcr(results=[timeout])).extract(
        write(docs.png_with_text(), "a.png"), FileKind.PNG
    )

    assert result.timed_out is True
    assert result.pages == ()


def test_page_time_limit_is_60_seconds_and_shrinks_to_the_remaining_document_time(clock, write):
    ocr = FakeOcr(clock, advance=570)  # 9.5 minutes on the first page
    path = write(docs.pdf_scanned(["um", "dois"]), "shrink.pdf")

    extractor(clock, ocr).extract(path, FileKind.PDF)

    assert [timeout for _, timeout in ocr.calls] == [60, 30]


def test_kind_without_text_support_is_refused(clock, write):
    with pytest.raises(ValueError):
        extractor(clock).extract(write(b"MZ", "x.bin"), FileKind.UNKNOWN)


def test_extraction_does_not_alter_the_original_file(clock, write):
    path = write(docs.pdf_mixed(TEXT_PAGE), "keep.pdf")
    before = path.read_bytes()

    extractor(clock).extract(path, FileKind.PDF)

    assert path.read_bytes() == before


# --- REAL-13: image heavy page with a thin text layer ----------------------------------------


def test_raster_certificate_with_only_header_and_footer_text_is_ocrd(clock, write):
    ocr = FakeOcr(results=[OcrResult(text="corpo lido por ocr " * 20, confidence=Decimal("90.00"))])
    path = write(docs.pdf_header_footer_over_image_body(), "cert.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    page = result.pages[0]
    assert page.method is TextMethod.OCR
    assert page.ocr_confidence == Decimal("90.00")
    assert "corpo lido por ocr" in page.text
    assert "Pro-Reitoria de Extensao" in page.text  # the header of the text layer is kept
    assert "validacao em endereco ficticio" in page.text
    assert page.char_count == len(page.text)
    assert len(ocr.calls) == 1


def test_thin_layer_page_keeps_the_text_layer_when_the_ocr_finds_less_text(clock, write):
    ocr = FakeOcr(results=[OcrResult(text="x", confidence=Decimal("90.00"))])
    path = write(docs.pdf_header_footer_over_image_body(), "cert.pdf")

    page = extractor(clock, ocr).extract(path, FileKind.PDF).pages[0]

    assert page.method is TextMethod.TEXTO
    assert page.ocr_confidence is None
    assert "Pro-Reitoria de Extensao" in page.text
    assert len(ocr.calls) == 1


def test_thin_layer_page_keeps_the_text_layer_when_the_ocr_is_not_confident(clock, write):
    ocr = FakeOcr(results=[OcrResult(text="lixo " * 100, confidence=Decimal("40.00"))])
    path = write(docs.pdf_header_footer_over_image_body(), "cert.pdf")

    page = extractor(clock, ocr).extract(path, FileKind.PDF).pages[0]

    assert page.method is TextMethod.TEXTO


def test_small_image_on_a_page_with_a_short_text_layer_does_not_trigger_ocr(clock, write):
    ocr = FakeOcr()
    path = write(docs.pdf_header_footer_over_image_body(image_covers_page=False), "logo.pdf")

    page = extractor(clock, ocr).extract(path, FileKind.PDF).pages[0]

    assert page.method is TextMethod.TEXTO
    assert ocr.calls == []


def test_text_page_without_images_never_triggers_the_extra_ocr(clock, write):
    ocr = FakeOcr()
    path = write(docs.pdf_with_text([TEXT_PAGE]), "t.pdf")

    extractor(clock, ocr).extract(path, FileKind.PDF)

    assert ocr.calls == []


def test_ocr_timeout_on_the_extra_pass_keeps_the_text_layer(clock, write):
    ocr = FakeOcr(results=[OcrResult(text="", confidence=None, code=DocAlertCode.TEMPO_ESGOTADO)])
    path = write(docs.pdf_header_footer_over_image_body(), "cert.pdf")

    result = extractor(clock, ocr).extract(path, FileKind.PDF)

    assert result.pages[0].method is TextMethod.TEXTO
    assert result.timed_out is False
