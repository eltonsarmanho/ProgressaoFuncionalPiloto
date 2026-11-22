"""Process schemas (PROC-01, PROC-02, PROC-04, PROC-14)."""

from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.processes import ProcessResult
from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.entities.career import Modality
from app.domain.entities.norm import NormCitation
from app.domain.entities.process import ProcessStatus
from app.domain.rules.process_verification import Alert, Severity
from app.presentation.schemas.norms import file_url


class ProcessFields(BaseModel):
    modality: Modality
    current_class: str
    current_denomination: str
    current_level: int
    target_class: str
    target_denomination: str
    target_level: int
    start_date: date
    end_date: date
    opening_date: date
    notes: str | None = None
    resp_name: str | None = None
    resp_position: str | None = None
    resp_appointment: str | None = None
    resp_admin_unit: str | None = None


class ProcessCreate(ProcessFields):
    professor_id: UUID
    unit_id: UUID


class ProcessUpdate(ProcessFields):
    expected_version: int
    justificativa: str | None = None


class StatusChange(BaseModel):
    status: ProcessStatus
    expected_version: int
    justificativa: str | None = None


class HistoryEventOut(BaseModel):
    id: int
    occurred_at: datetime
    user_id: UUID | None
    action: AuditAction
    changes: dict[str, dict]
    justification: str | None

    @classmethod
    def of(cls, e: AuditEvent) -> "HistoryEventOut":
        return cls(
            id=e.id,
            occurred_at=e.occurred_at,
            user_id=e.user_id,
            action=e.action,
            changes=e.changes,
            justification=e.justification,
        )


class IntersticeOut(BaseModel):
    months: int
    days: int


class AlertOut(BaseModel):
    code: str
    severity: Severity
    message: str
    norm_reference: str
    # NLINK-06: all null (norm_archived false) when the rule cites no registered norm (NLINK-05)
    norm_code: str | None = None
    norm_title: str | None = None
    norm_url: str | None = None
    norm_file_url: str | None = None
    norm_archived: bool = False

    @classmethod
    def of(cls, alert: Alert, norms: Mapping[str, NormCitation] | None = None) -> "AlertOut":
        cited = (norms or {}).get(alert.norm_code) if alert.norm_code else None
        return cls(
            code=alert.code,
            severity=alert.severity,
            message=alert.message,
            norm_reference=alert.norm_reference,
            norm_code=cited.code if cited else None,
            norm_title=cited.title if cited else None,
            norm_url=cited.source_url if cited else None,
            norm_file_url=file_url(cited.id) if cited and cited.has_file else None,
            norm_archived=cited.archived if cited else False,
        )


class ProcessOut(ProcessCreate):
    id: UUID
    status: ProcessStatus
    version: int
    created_at: datetime | None
    updated_at: datetime | None
    interstice: IntersticeOut
    alerts: list[AlertOut]

    @classmethod
    def of(cls, r: ProcessResult) -> "ProcessOut":
        p = r.process
        return cls(
            **{name: getattr(p, name) for name in ProcessCreate.model_fields},
            id=p.id,
            status=p.status,
            version=p.version,
            created_at=p.created_at,
            updated_at=p.updated_at,
            interstice=IntersticeOut(months=r.interstice_months, days=r.interstice_days),
            alerts=[AlertOut.of(a, r.norms) for a in r.alerts],
        )


class DeletePreviewOut(BaseModel):
    """What a deletion removes: numbers only, no personal data."""

    documents: int
    activities: int
    generated_documents: int


class ProcessSummary(BaseModel):
    id: UUID
    status: ProcessStatus
    version: int
    professor_id: UUID
    professor_name: str
    unit_id: UUID
    modality: Modality
    start_date: date
    end_date: date
    interstice: IntersticeOut
    alert_counts: dict[Severity, int]

    @classmethod
    def of(cls, r: ProcessResult) -> "ProcessSummary":
        p = r.process
        counts = {s: 0 for s in Severity}
        for alert in r.alerts:
            counts[alert.severity] += 1
        return cls(
            id=p.id,
            status=p.status,
            version=p.version,
            professor_id=p.professor_id,
            professor_name=r.professor_name,
            unit_id=p.unit_id,
            modality=p.modality,
            start_date=p.start_date,
            end_date=p.end_date,
            interstice=IntersticeOut(months=r.interstice_months, days=r.interstice_days),
            alert_counts=counts,
        )
