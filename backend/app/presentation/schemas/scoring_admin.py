"""Scoring table administration schemas (ADM-01..11)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.scoring_admin import (
    TableDeletePreview,
    TableHistory,
    VersionDeletePreview,
)
from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.entities.scoring import TableStatus
from app.presentation.schemas.scoring import VersionSummaryOut


class TableCreateIn(BaseModel):
    name: str
    unit_ids: list[UUID] = []
    valid_from: date
    valid_to: date | None = None
    norm_reference: str
    version_name: str | None = None
    status: TableStatus = TableStatus.PENDENTE_VALIDACAO
    base_version_id: UUID | None = None


class TableDuplicateIn(BaseModel):
    new_name: str
    unit_ids: list[UUID] = []


class VersionCreateIn(BaseModel):
    source_version_id: UUID
    valid_from: date
    valid_to: date | None = None
    norm_reference: str
    version_name: str | None = None
    status: TableStatus = TableStatus.PENDENTE_VALIDACAO


class CriterionChangeIn(BaseModel):
    change_reference: str
    changes: dict[str, Any]


class UnitsIn(BaseModel):
    unit_ids: list[UUID]


class UnitDefaultIn(BaseModel):
    version_id: UUID


class UnitDefaultOut(BaseModel):
    unit_id: UUID
    version_id: UUID


class BlockerOut(BaseModel):
    """Why an operation is refused: the stable code, the text ready to show, and the facts."""

    code: str
    message: str
    count: int | None = None  # processes, when the blocker is about their use
    acronyms: list[str] = []  # units, when the blocker is about the version in use


class VersionDeletePreviewOut(BaseModel):
    name: str
    criteria: int
    blocked: list[BlockerOut]

    @classmethod
    def of(cls, preview: VersionDeletePreview) -> "VersionDeletePreviewOut":
        return cls(
            name=preview.name,
            criteria=preview.criteria,
            blocked=[
                BlockerOut(code=b.code, message=b.message, count=b.count, acronyms=list(b.acronyms))
                for b in preview.blocked
            ],
        )


class PreviewUnitOut(BaseModel):
    id: UUID
    acronym: str


class TableDeletePreviewOut(BaseModel):
    name: str
    versions: int
    criteria: int
    units: list[PreviewUnitOut]
    blocked: list[BlockerOut]

    @classmethod
    def of(cls, preview: TableDeletePreview) -> "TableDeletePreviewOut":
        return cls(
            name=preview.name,
            versions=preview.versions,
            criteria=preview.criteria,
            units=[PreviewUnitOut(id=u.id, acronym=u.acronym) for u in preview.units],
            blocked=[
                BlockerOut(code=b.code, message=b.message, count=b.count, acronyms=list(b.acronyms))
                for b in preview.blocked
            ],
        )


class AuditEntryOut(BaseModel):
    id: int
    occurred_at: datetime
    user_id: UUID | None
    entity: str
    entity_id: str
    action: AuditAction
    changes: dict[str, dict]
    justification: str | None

    @classmethod
    def of(cls, e: AuditEvent) -> "AuditEntryOut":
        return cls(**{name: getattr(e, name) for name in cls.model_fields})


class TableHistoryOut(BaseModel):
    versions: list[VersionSummaryOut]
    events: list[AuditEntryOut]

    @classmethod
    def of(cls, history: TableHistory) -> "TableHistoryOut":
        return cls(
            versions=[VersionSummaryOut.of(v) for v in history.versions],
            events=[AuditEntryOut.of(e) for e in history.events],
        )
