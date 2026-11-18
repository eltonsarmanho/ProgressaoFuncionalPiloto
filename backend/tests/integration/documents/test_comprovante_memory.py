"""CMP-11: the Comprovante of 400 scanned pages is assembled with a peak under 320 MB.

400 synthetic scanned pages (JPEG 1240x1754, about 224 KB each) in 10 PDFs are assembled in a
separate process and its peak resident memory (`VmHWM`) is read. Run alone with
`pytest -m memory`; it also runs in the full gate.
"""

import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from tests.support.scanned_pdfs import write_scanned_pdf

pytestmark = pytest.mark.memory

BACKEND = Path(__file__).resolve().parents[3]
DOCUMENTS = 10
PAGES_PER_DOCUMENT = 40
PEAK_LIMIT_MB = 320
EXPECTED_PAGES = 1 + 2 + 8 + 400  # cover, table of contents, separators, originals


@pytest.fixture(scope="module")
def assembled(tmp_path_factory) -> dict:
    folder = tmp_path_factory.mktemp("memory")
    paths = []
    for index in range(DOCUMENTS):
        path = folder / f"scan_{index}.pdf"
        write_scanned_pdf(path, PAGES_PER_DOCUMENT, index * PAGES_PER_DOCUMENT)
        paths.append(str(path))
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps({"documents": paths, "pages_per_document": PAGES_PER_DOCUMENT}))
    output = folder / "comprovante.pdf"
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.support.comprovante_memory_runner",
            str(manifest),
            str(output),
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(done.stdout.strip().splitlines()[-1])
    report["output"] = output
    report["source_pages"] = DOCUMENTS * PAGES_PER_DOCUMENT
    report["average_page_kb"] = sum(Path(p).stat().st_size for p in paths) / 400 / 1024
    return report


def test_the_peak_of_the_process_stays_under_320_mb_with_400_scanned_pages(assembled):
    assert 200 <= assembled["average_page_kb"] <= 250  # the pages weigh what the spec says
    assert assembled["peak_mb"] < PEAK_LIMIT_MB
    assert assembled["pages"] == EXPECTED_PAGES
    assert len(pymupdf.open(assembled["output"])) == EXPECTED_PAGES


def test_the_411_pages_are_numbered_in_sequence_and_the_index_points_to_its_pages(assembled):
    pdf = pymupdf.open(assembled["output"])

    feet = [page.get_text().strip().splitlines()[-1] for page in pdf[1:]]
    assert feet == [f"Comprovante p. {n}" for n in range(2, EXPECTED_PAGES + 1)]
    first_pages = assembled["first_pages"]  # the first page of each of the 16 activities
    assert first_pages == sorted(first_pages)
    for number in first_pages:
        assert pdf[number - 1].get_images(full=True)  # an activity starts at an original page
