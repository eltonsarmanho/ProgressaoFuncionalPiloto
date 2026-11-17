"""PIPE-04: text of each PDF page with its number and character count."""

import pytest

from app.infrastructure.ocr.pdf_text import extract_pdf_page, extract_pdf_pages, pdf_page_count
from tests.support import synthetic_docs as docs

PAGE_ONE = "Primeira pagina do documento sintetico sobre banca examinadora de teste"
PAGE_TWO = "Segunda pagina do documento sintetico sobre orientacao concluida de teste"


@pytest.fixture
def write(tmp_path):
    def run(data: bytes):
        path = tmp_path / "doc.pdf"
        path.write_bytes(data)
        return path

    return run


def test_text_pdf_returns_each_page_text_with_number_and_count(write):
    pages = extract_pdf_pages(write(docs.pdf_with_text([PAGE_ONE, PAGE_TWO])))
    assert [p.page_number for p in pages] == [1, 2]
    assert PAGE_ONE in pages[0].text.replace("\n", " ")
    assert PAGE_TWO in pages[1].text.replace("\n", " ")
    assert PAGE_ONE not in pages[1].text
    assert [p.char_count for p in pages] == [len(p.text) for p in pages]
    assert all(p.char_count >= len(PAGE_ONE) - 2 for p in pages)


def test_scanned_pdf_returns_empty_text(write):
    pages = extract_pdf_pages(write(docs.pdf_scanned(["Pagina digitalizada um", "Dois"])))
    assert [p.page_number for p in pages] == [1, 2]
    assert [p.text.strip() for p in pages] == ["", ""]
    assert [p.char_count for p in pages] == [len(p.text) for p in pages]


def test_mixed_pdf_has_text_on_the_first_page_only(write):
    pages = extract_pdf_pages(write(docs.pdf_mixed(PAGE_ONE)))
    assert len(pages) == 2
    assert pages[0].char_count > 50
    assert pages[1].text.strip() == ""


def test_single_page_extraction_matches_the_whole_document(write):
    path = write(docs.pdf_with_text([PAGE_ONE, PAGE_TWO]))
    whole = extract_pdf_pages(path)
    assert extract_pdf_page(path, 2) == whole[1]
    assert extract_pdf_page(path, 1) == whole[0]


def test_page_count(write):
    assert pdf_page_count(write(docs.pdf_with_text([PAGE_ONE, PAGE_TWO, PAGE_ONE]))) == 3


def test_extraction_does_not_alter_the_file(write):
    path = write(docs.pdf_with_text([PAGE_ONE]))
    before = path.read_bytes()
    extract_pdf_pages(path)
    assert path.read_bytes() == before
