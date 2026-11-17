"""Document analyzer: from a stored file to verified, suggested activities (EXT-07..13).

Pure application service: it reads text through the `TextExtractor` port, asks the AI through
the `AiExtractor` port and applies the domain rules. It never touches the database. The AI
output is untrusted (AD-009): it must fit the strict payload shape, and every value it returns
is looked up in the ORIGINAL (unmasked) text of the page it cites before it is kept.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.domain.entities.activity import Level
from app.domain.entities.document import DocAlertCode, DocumentStatus, TextMethod
from app.domain.entities.extraction import DocumentType, ExtractedActivity, TaxonomyCode
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.repositories.ports import (
    AiExtraction,
    AiExtractionError,
    AiExtractor,
    Clock,
    ExtractedPage,
    TextExtractor,
)
from app.domain.rules.confidence import final_confidence, needs_review
from app.domain.rules.document_type import detect_document_type
from app.domain.rules.grounding import ground, name_in_text, same_person
from app.domain.rules.interstice import Interstice
from app.domain.rules.masking import mask_identifiers
from app.domain.rules.text_quality import ocr_needs_review
from app.domain.rules.upload_validation import FileKind

MAX_EXCERPT_CHARS = 300
_AI_ATTEMPTS = 2  # the first call and one new attempt for an invalid payload
_NO_AI_CODES = (DocAlertCode.IA_CREDENCIAL_RECUSADA, DocAlertCode.IA_INDISPONIVEL)
_ACTIVITY_KEYS = frozenset(
    {
        "taxonomy",
        "title",
        "role",
        "start_date",
        "end_date",
        "event_date",
        "hours",
        "course_hours",
        "level",
        "academic_period",
        "identifier",
        "page",
        "evidence_text",
        "confidence",
    }
)
_PAYLOAD_KEYS = frozenset({"document_type", "docente_nome", "activities"})
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class AnalyzerLimits:
    max_ai_pages: int = 6


@dataclass(frozen=True)
class DocAlert:
    code: DocAlertCode
    field: str | None = None  # the nulled field of a NAO_ENCONTRADO_NO_TEXTO warning
    activity_index: int | None = None


@dataclass(frozen=True)
class SuggestedActivity:
    """An activity read from the document, grounded in its page text, awaiting human review."""

    extracted: ExtractedActivity
    taxonomy: TaxonomyCode
    page: int
    excerpt: str
    confidence: Decimal
    needs_review: bool


@dataclass(frozen=True)
class AnalysisResult:
    pages: tuple[ExtractedPage, ...]  # unmasked text, for storage and grounding
    document_type: DocumentType
    raw_json: dict[str, Any] | None
    activities: tuple[SuggestedActivity, ...]
    alerts: tuple[DocAlert, ...]
    status: DocumentStatus
    status_code: str | None
    model: str | None
    duration_ms: int


@dataclass
class _Run:
    """Mutable state of one analysis, folded into the immutable result at the end."""

    pages: tuple[ExtractedPage, ...] = ()
    document_type: DocumentType = DocumentType.OUTRO
    raw_json: dict[str, Any] | None = None
    model: str | None = None
    activities: list[SuggestedActivity] = field(default_factory=list)
    alerts: list[DocAlert] = field(default_factory=list)


class DocumentAnalyzer:
    def __init__(
        self,
        text_extractor: TextExtractor,
        ai_extractor: AiExtractor,
        clock: Clock,
        limits: AnalyzerLimits | None = None,
    ) -> None:
        self._text_extractor = text_extractor
        self._ai = ai_extractor
        self._clock = clock
        self._limits = limits or AnalyzerLimits()

    def analyze(
        self,
        file_path: Path,
        kind: FileKind,
        professor_name: str,
        professor_siape: str | None,
        process_interstice: Interstice | None,
        table_version: ScoringTableVersion | None,
    ) -> AnalysisResult:
        started = self._clock.now()
        run = _Run()
        status, status_code = self._analyze(
            run, file_path, kind, professor_name, professor_siape
        )
        elapsed = self._clock.now() - started
        return AnalysisResult(
            pages=run.pages,
            document_type=run.document_type,
            raw_json=run.raw_json,
            activities=tuple(run.activities),
            alerts=tuple(run.alerts),
            status=status,
            status_code=status_code,
            model=run.model,
            duration_ms=int(elapsed.total_seconds() * 1000),
        )

    def _analyze(
        self,
        run: _Run,
        file_path: Path,
        kind: FileKind,
        professor_name: str,
        professor_siape: str | None,
    ) -> tuple[DocumentStatus, str | None]:
        extraction = self._text_extractor.extract(file_path, kind)
        run.pages = extraction.pages
        if extraction.timed_out:
            run.alerts.append(DocAlert(DocAlertCode.TEMPO_ESGOTADO))
            return DocumentStatus.FALHOU, DocAlertCode.TEMPO_ESGOTADO.value
        if _is_illegible(run.pages):
            run.alerts.append(DocAlert(DocAlertCode.TEXTO_ILEGIVEL))
            return DocumentStatus.REQUER_REVISAO, DocAlertCode.TEXTO_ILEGIVEL.value

        sent = run.pages[: self._limits.max_ai_pages]
        run.document_type = detect_document_type(_join(sent))
        if len(run.pages) > self._limits.max_ai_pages:
            run.alerts.append(DocAlert(DocAlertCode.TRUNCADO))

        payload, failure = self._ask_ai(run, _masked_ai_text(sent))
        if failure is not None:
            run.alerts.append(DocAlert(failure))
            if failure in _NO_AI_CODES:
                return DocumentStatus.EXTRAIDO_SEM_IA, failure.value
            return DocumentStatus.REQUER_REVISAO, failure.value
        assert payload is not None

        status = DocumentStatus.PROCESSADO
        original = {page.page_number: page.text for page in sent}
        for index, raw in enumerate(payload.activities):
            run.activities.append(self._verified(run, index, raw, original))
        if not payload.activities:
            run.alerts.append(DocAlert(DocAlertCode.NENHUMA_ATIVIDADE_ENCONTRADA))
        if not _same_professor(payload.docente_nome, professor_name, professor_siape, run.pages):
            run.alerts.append(DocAlert(DocAlertCode.DOCENTE_DIVERGENTE))
            status = DocumentStatus.REQUER_REVISAO
        return status, None

    def _ask_ai(
        self, run: _Run, text: str
    ) -> tuple["_Payload | None", DocAlertCode | None]:
        """The validated payload, or the alert code that ends the analysis."""
        for _ in range(_AI_ATTEMPTS):
            try:
                answer: AiExtraction = self._ai.extract(run.document_type, text)
            except AiExtractionError as error:
                if error.code in _NO_AI_CODES:
                    return None, error.code
                return None, DocAlertCode.RESPOSTA_INVALIDA
            run.raw_json, run.model = answer.raw_json, answer.model
            payload = _parse_payload(answer.raw_json)
            if payload is not None:
                return payload, None
        return None, DocAlertCode.RESPOSTA_INVALIDA

    def _verified(
        self, run: _Run, index: int, raw: ExtractedActivity, pages: dict[int, str]
    ) -> SuggestedActivity:
        grounded = ground(raw, pages)
        for warning in grounded.warnings:
            run.alerts.append(DocAlert(warning.code, warning.field, index))
        confidence = final_confidence(raw.confidence, grounded.grounded_ratio)
        activity = grounded.activity
        return SuggestedActivity(
            extracted=activity,
            taxonomy=activity.taxonomy,
            page=activity.page,
            excerpt=_excerpt(activity.evidence_text, pages.get(activity.page, "")),
            confidence=confidence,
            needs_review=needs_review(confidence),
        )


@dataclass(frozen=True)
class _Payload:
    docente_nome: str | None
    activities: tuple[ExtractedActivity, ...]


def _join(pages: tuple[ExtractedPage, ...] | list[ExtractedPage]) -> str:
    return "\n\n".join(page.text for page in pages)


def _masked_ai_text(pages: tuple[ExtractedPage, ...] | list[ExtractedPage]) -> str:
    """Page-marked text with CPF, RG, e-mail and phone replaced by markers (EXT-07)."""
    return "\n\n".join(
        f"[PÁGINA {page.page_number}]\n{mask_identifiers(page.text).text}" for page in pages
    )


def _is_illegible(pages: tuple[ExtractedPage, ...]) -> bool:
    """No text at all, or a mean OCR confidence below 60 (PIPE-07)."""
    text = _join(pages)
    if not text.strip():
        return True
    scores = [
        p.ocr_confidence
        for p in pages
        if p.method is TextMethod.OCR and p.ocr_confidence is not None
    ]
    if not scores:
        return False
    return ocr_needs_review(sum(scores) / len(scores), text)


def _same_professor(
    extracted_name: str | None,
    professor_name: str,
    siape: str | None,
    pages: tuple[ExtractedPage, ...],
) -> bool:
    text = _join(pages)
    if same_person(extracted_name, professor_name, siape, text):
        return True
    return extracted_name is None and name_in_text(professor_name, text)


def _excerpt(evidence_text: str, page_text: str) -> str:
    """Up to 300 characters of the REAL page text: the quoted passage, else the page start."""
    words = evidence_text.split()
    if words:
        pattern = r"\s+".join(re.escape(word) for word in words)
        found = re.search(pattern, page_text, re.IGNORECASE)
        if found:
            return " ".join(found.group(0).split())[:MAX_EXCERPT_CHARS]
    return " ".join(page_text.split())[:MAX_EXCERPT_CHARS]


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _optional_text(value: Any) -> bool:
    return value is None or isinstance(value, str)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError("date")
    return date.fromisoformat(value)


def _parse_hours(value: Any) -> Decimal | None:
    if value is None:
        return None
    if not _is_number(value) or value < 0:
        raise ValueError("hours")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError("hours") from None


def _parse_activity(raw: Any) -> ExtractedActivity:
    if not isinstance(raw, dict) or set(raw) != _ACTIVITY_KEYS:
        raise ValueError("activity")
    texts = ("title", "role", "academic_period", "identifier")
    if not all(_optional_text(raw[name]) for name in texts):
        raise ValueError("text")
    page, confidence = raw["page"], raw["confidence"]
    valid_page = isinstance(page, int) and not isinstance(page, bool) and page >= 1
    if not valid_page or not isinstance(raw["evidence_text"], str):
        raise ValueError("page")
    if not _is_number(confidence) or not 0 <= confidence <= 1:
        raise ValueError("confidence")
    level = raw["level"]
    return ExtractedActivity(
        taxonomy=TaxonomyCode(raw["taxonomy"]),
        page=page,
        evidence_text=raw["evidence_text"],
        confidence=Decimal(str(confidence)),
        title=raw["title"],
        role=raw["role"],
        start_date=_parse_date(raw["start_date"]),
        end_date=_parse_date(raw["end_date"]),
        event_date=_parse_date(raw["event_date"]),
        hours=_parse_hours(raw["hours"]),
        course_hours=_parse_hours(raw["course_hours"]),
        level=None if level is None else Level(level),
        academic_period=raw["academic_period"],
        identifier=raw["identifier"],
    )


def _parse_payload(data: Any) -> _Payload | None:
    """The payload when it fits the strict shape of the AI contract, else None (EXT-09)."""
    if not isinstance(data, dict) or set(data) != _PAYLOAD_KEYS:
        return None
    name, items = data["docente_nome"], data["activities"]
    if not _optional_text(name) or not isinstance(items, list):
        return None
    try:
        DocumentType(data["document_type"])
        return _Payload(name, tuple(_parse_activity(item) for item in items))
    except (ValueError, TypeError, KeyError):
        return None
