"""Document schemas (DOC-01, DOC-15, REV-01).

`confidence` and the OCR confidence are 2-decimal strings, like every number of the scoring API.
The extracted JSON of a run is read only: no schema here accepts it back.
"""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.application.use_cases.documents import DocumentDetail, ListedDocument, UploadResult
from app.domain.entities.document import Document, DocumentStatus, PageText, TextMethod
from app.domain.repositories.ports import ActivityEvidence
from app.presentation.schemas.scoring import Money


class DocumentOut(BaseModel):
    id: UUID
    process_id: UUID
    original_name: str
    mime: str
    size_bytes: int
    sha256: str
    page_count: int
    status: DocumentStatus
    status_code: str | None
    manual_type: str | None
    manual_category: str | None
    suggested_type: str | None
    suggested_category: str | None
    confidence: Money | None
    uploaded_by: UUID
    uploaded_at: datetime | None
    updated_at: datetime | None
    version: int
    arquivo_excluido: bool  # the conclusion removed the input file (DEL-12)

    @classmethod
    def of(cls, d: Document) -> "DocumentOut":
        return cls(**_document_fields(d))


class DocumentListItemOut(DocumentOut):
    """A row of the process list: the document, how many activities came from it and, when it
    is outside the interstice, the data of its warning (FORA-02)."""

    activity_count: int
    outside_interstice: bool
    document_date: date | None
    document_date_precision: str | None  # "DAY" or "MONTH"
    interstice_start: date | None
    interstice_end: date | None

    @classmethod
    def of_listed(cls, listed: ListedDocument) -> "DocumentListItemOut":
        outside = listed.outside
        return cls(
            **_document_fields(listed.document),
            activity_count=listed.activity_count,
            outside_interstice=listed.document.outside_interstice,
            document_date=outside.document_date if outside else None,
            document_date_precision=outside.date_precision if outside else None,
            interstice_start=outside.interstice_start if outside else None,
            interstice_end=outside.interstice_end if outside else None,
        )


def _document_fields(d: Document) -> dict[str, Any]:
    fields = {name: getattr(d, name) for name in DocumentOut.model_fields if hasattr(d, name)}
    return {**fields, "arquivo_excluido": d.file_deleted_at is not None}


class ClassificationIn(BaseModel):
    """The user's own type and category; the values are checked against the enums (422)."""

    model_config = ConfigDict(extra="forbid")

    tipo: str
    categoria: str
    expected_version: int | None = None


class UploadResultOut(BaseModel):
    """What happened to one file of an upload request (201, 409, 422 or 429)."""

    original_name: str
    status_code: int
    document: DocumentOut | None
    existing_document_id: UUID | None
    field: str | None
    code: str | None
    message: str | None

    @classmethod
    def of(cls, r: UploadResult) -> "UploadResultOut":
        return cls(
            original_name=r.original_name,
            status_code=r.status_code,
            document=DocumentOut.of(r.document) if r.document is not None else None,
            existing_document_id=r.existing_document_id,
            field=r.field,
            code=r.code,
            message=r.message,
        )


class PageOut(BaseModel):
    page_number: int
    method: TextMethod
    char_count: int
    ocr_confidence: Money | None
    text: str

    @classmethod
    def of(cls, p: PageText) -> "PageOut":
        return cls(
            page_number=p.page_number,
            method=p.method,
            char_count=p.char_count,
            ocr_confidence=p.ocr_confidence,
            text=p.text,
        )


class RunOut(BaseModel):
    """The active extraction: model, duration and the raw JSON the AI returned (read only)."""

    id: UUID
    model: str
    duration_ms: int
    raw_json: dict[str, Any]
    created_at: datetime | None


class DocAlertOut(BaseModel):
    code: str
    field: str | None
    activity_index: int | None
    detail: dict[str, str] | None = None  # the date and interstice of the outside warning


class EvidenceOut(BaseModel):
    id: UUID
    document_id: UUID
    document_name: str
    page: int
    excerpt: str

    @classmethod
    def of(cls, e: ActivityEvidence, document_name: str) -> "EvidenceOut":
        return cls(
            id=e.id,
            document_id=e.document_id,
            document_name=document_name,
            page=e.page_number,
            excerpt=e.excerpt,
        )


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    page: int
    justificativa: str | None = None


class LinkedActivityOut(BaseModel):
    id: UUID
    title: str
    group_number: int | None
    item_number: int | None
    source: str
    status: str
    version: int
    evidences: list[EvidenceOut]


class DocumentDetailOut(DocumentOut):
    pages: list[PageOut]
    run: RunOut | None
    alerts: list[DocAlertOut]
    activities: list[LinkedActivityOut]

    @classmethod
    def of(cls, detail: DocumentDetail) -> "DocumentDetailOut":
        document = detail.document
        run = detail.run
        return cls(
            **_document_fields(document),
            pages=[PageOut.of(p) for p in detail.pages],
            run=RunOut(
                id=run.id,
                model=run.model,
                duration_ms=run.duration_ms,
                raw_json=run.raw_json,
                created_at=run.created_at,
            )
            if run is not None
            else None,
            alerts=[DocAlertOut(**a) for a in detail.alerts],
            activities=[
                LinkedActivityOut(
                    id=linked.activity.id,
                    title=linked.activity.title,
                    group_number=linked.activity.group_number,
                    item_number=linked.activity.item_number,
                    source=linked.activity.source,
                    status=linked.activity.status,
                    version=linked.activity.version,
                    evidences=[EvidenceOut.of(e, document.original_name) for e in linked.evidences],
                )
                for linked in detail.activities
            ],
        )
