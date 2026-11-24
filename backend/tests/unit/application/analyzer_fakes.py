"""Fake ports and payload builders shared by the analyzer tests (no OCR, no network)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.application.services.document_analyzer import DocumentAnalyzer
from app.domain.entities.document import TextMethod
from app.domain.entities.extraction import DocumentType
from app.domain.repositories.ports import (
    AiExtraction,
    AiExtractionError,
    ExtractedPage,
    TextExtraction,
)
from app.domain.rules.upload_validation import FileKind

PROFESSOR = "Fulana de Tal Exemplo"
SIAPE = "0000000"

BANCA_TEXT = (
    "DECLARACAO DE BANCA EXAMINADORA\n"
    f"Declaramos que {PROFESSOR}, matricula SIAPE {SIAPE}, participou como membro da banca "
    "examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos, "
    "realizada em 12 de marco de 2025, na Faculdade Exemplo de Testes."
)


def text_page(number: int, text: str = BANCA_TEXT) -> ExtractedPage:
    return ExtractedPage(number, TextMethod.TEXTO, len(text), None, text)


def ocr_page(number: int, text: str, confidence: str | None) -> ExtractedPage:
    score = None if confidence is None else Decimal(confidence)
    return ExtractedPage(number, TextMethod.OCR, len(text), score, text)


class FakeTextExtractor:
    def __init__(self, *pages: ExtractedPage, timed_out: bool = False):
        self.result = TextExtraction(tuple(pages), timed_out=timed_out)
        self.calls: list[tuple[Path, FileKind]] = []

    def extract(self, path: Path, kind: FileKind) -> TextExtraction:
        self.calls.append((path, kind))
        return self.result


class FakeAi:
    """Plays the queued answers (AiExtraction or AiExtractionError) and records the calls."""

    def __init__(
        self, *answers: AiExtraction | AiExtractionError | dict, model: str = "fake-model"
    ):
        self.answers = list(answers)
        self.model = model
        self.calls: list[tuple[DocumentType, str, str | None]] = []

    def extract(
        self, document_type: DocumentType, text: str, professor_name: str | None = None
    ) -> AiExtraction:
        self.calls.append((document_type, text, professor_name))
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, AiExtractionError):
            raise answer
        if isinstance(answer, dict):
            return AiExtraction(raw_json=answer, model=self.model, duration_ms=1)
        return answer


class StepClock:
    """Each reading moves the clock forward by a fixed step."""

    def __init__(self, step_ms: int = 1500):
        self._moment = datetime(2026, 1, 1, tzinfo=UTC)
        self._step = timedelta(milliseconds=step_ms)

    def now(self) -> datetime:
        current = self._moment
        self._moment += self._step
        return current


def activity(**changes) -> dict:
    base = {
        "taxonomy": "BANCA_TCC_GRADUACAO",
        "title": "Estudo Ficticio sobre Dados Abertos",
        "role": "membro",
        "start_date": None,
        "end_date": None,
        "term": None,
        "event_date": "2025-03-12",
        "hours": None,
        "course_hours": None,
        "level": None,
        "academic_period": None,
        "identifier": None,
        "page": 1,
        "evidence_text": "participou como membro da banca examinadora",
        "confidence": 0.95,
    }
    return base | changes


def payload(*activities: dict, name: str | None = PROFESSOR, document_type="DECLARACAO_BANCA"):
    return {
        "document_type": document_type,
        "docente_nome": name,
        "activities": list(activities),
    }


def analyzer(extractor: FakeTextExtractor, ai: FakeAi, clock: StepClock | None = None):
    return DocumentAnalyzer(extractor, ai, clock or StepClock())


def run(
    analyzer_: DocumentAnalyzer,
    professor: str = PROFESSOR,
    siape: str | None = SIAPE,
    interstice=None,
    table_version=None,
):
    return analyzer_.analyze(
        Path("/tmp/documento.pdf"), FileKind.PDF, professor, siape, interstice, table_version
    )
