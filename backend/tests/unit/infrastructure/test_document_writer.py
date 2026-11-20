"""The DocumentWriter port: one writer that picks the file format (TAB-01, REL-09)."""

import zipfile

import pymupdf
import pytest
from docx import Document

from app.domain.entities.generated import DocumentFormat
from app.infrastructure.documents.document_writer import FileDocumentWriter
from tests.unit.infrastructure.report_model_support import report_document
from tests.unit.infrastructure.table_support import scenario_table


@pytest.fixture
def target(tmp_path):
    return tmp_path / ".tmp-0123456789abcdef"  # the storage hands out a path with no extension


def test_the_table_in_pdf_is_a_pdf_with_the_total(target):
    FileDocumentWriter().write_table(scenario_table(), DocumentFormat.PDF, target)

    assert target.read_bytes().startswith(b"%PDF")
    assert "211,00" in pymupdf.open(target)[0].get_text()


def test_the_table_in_docx_is_a_docx_with_the_total(target):
    FileDocumentWriter().write_table(scenario_table(), DocumentFormat.DOCX, target)

    assert zipfile.is_zipfile(target)
    text = " ".join(
        cell.text for t in Document(str(target)).tables for r in t.rows for cell in r.cells
    )
    assert "Pontuação geral: 211,00" in text


def test_the_report_in_pdf_is_a_pdf_with_the_title(target):
    FileDocumentWriter().write_report(report_document(), DocumentFormat.PDF, target)

    assert target.read_bytes().startswith(b"%PDF")
    assert "RELATÓRIO DE ATIVIDADES" in pymupdf.open(target)[0].get_text()


def test_the_report_in_docx_is_a_docx_with_the_title(target):
    FileDocumentWriter().write_report(report_document(), DocumentFormat.DOCX, target)

    assert "RELATÓRIO DE ATIVIDADES" in [p.text for p in Document(str(target)).paragraphs]
