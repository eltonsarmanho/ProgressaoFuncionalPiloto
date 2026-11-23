"""Scoring table administration schemas (ADM-01..11)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.scoring_admin import TableHistory
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
