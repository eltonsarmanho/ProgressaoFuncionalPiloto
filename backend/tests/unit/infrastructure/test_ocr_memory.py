"""SEG-12: reading a long scanned PDF does not make the memory grow page after page.

MuPDF keeps every decoded page image in a global cache of up to 256 MB. Without releasing it a
scanned PDF of 25 pages was killed at the 384 MB limit of the VM backend (measured in
`docker run -m 384m`); the cache is now emptied after each rendered page.
"""

import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.rules.upload_validation import FileKind
from app.infrastructure.ocr.extractor import DocumentTextExtractor
from app.infrastructure.ocr.render import render_page
from app.infrastructure.ocr.tesseract import OcrResult
from tests.support import synthetic_docs as docs

PAGES = 10
MAX_GROWTH_MB = 40  # before the fix: about 17 MB per page, 150 MB over 10 pages
STATUS = Path("/proc/self/status")

pytestmark = pytest.mark.skipif(not STATUS.exists(), reason="needs /proc (Linux)")


def rss_mb() -> float:
    return int(re.search(r"VmRSS:\s+(\d+)", STATUS.read_text()).group(1)) / 1024


class FixedClock:
    def now(self):
        from datetime import UTC, datetime

        return datetime(2026, 11, 17, tzinfo=UTC)


@pytest.fixture(scope="module")
def scanned_pdf(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("scan") / "scan.pdf"
    path.write_bytes(
        docs.pdf_scanned([f"Pagina {n}. " + docs.SAMPLE_PAGES[0] for n in range(PAGES)])
    )
    return path


def test_rendering_every_page_keeps_the_memory_flat(scanned_pdf):
    render_page(scanned_pdf, 1)  # warm up the libraries before measuring
    start = rss_mb()
    for number in range(1, PAGES + 1):
        image = render_page(scanned_pdf, number)
        image.close()
    assert rss_mb() - start < MAX_GROWTH_MB


def test_extracting_a_long_scanned_pdf_keeps_the_memory_flat(scanned_pdf):
    def fake_ocr(image, timeout_seconds=60):
        return OcrResult(text="texto da pagina lido pelo ocr", confidence=Decimal("90"))

    extractor = DocumentTextExtractor(FixedClock(), ocr=fake_ocr)
    render_page(scanned_pdf, 1)
    start = rss_mb()

    result = extractor.extract(scanned_pdf, FileKind.PDF)

    assert [page.page_number for page in result.pages] == list(range(1, PAGES + 1))
    assert rss_mb() - start < MAX_GROWTH_MB
