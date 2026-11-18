"""The `DocumentWriter` port: picks the writer of the file format (TAB-01, REL-09)."""

from pathlib import Path

from app.domain.entities.generated import DocumentFormat
from app.domain.entities.report import ReportDocument
from app.domain.rules.table_document import TableDocument
from app.infrastructure.documents.report_docx import write_report_docx
from app.infrastructure.documents.report_pdf import write_report_pdf
from app.infrastructure.documents.table_docx import write_table_docx
from app.infrastructure.documents.table_pdf import write_table_pdf


class FileDocumentWriter:
    def write_table(self, model: TableDocument, fmt: DocumentFormat, target: Path) -> None:
        {DocumentFormat.PDF: write_table_pdf, DocumentFormat.DOCX: write_table_docx}[fmt](
            model, target
        )

    def write_report(self, model: ReportDocument, fmt: DocumentFormat, target: Path) -> None:
        {DocumentFormat.PDF: write_report_pdf, DocumentFormat.DOCX: write_report_docx}[fmt](
            model, target
        )
