"""Activity schemas (ATV-01..ATV-14).

The public API never accepts `source` (always MANUAL): unknown fields are rejected with 422.
Dates may be `YYYY-MM-DD` or `YYYY-MM` (month precision). The field names `quantidade`,
`horas` and `justificativa` follow the spec's 422 field names.
"""

import re
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import (
    Activity,
    ActivitySource,
    ActivityStatus,
    Candidate,
    Level,
    PeriodPrecision,
)
from app.presentation.schemas.documents import EvidenceOut
from app.presentation.schemas.scoring import Money

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _parse_date(value: str | None) -> tuple[date | None, bool]:
    """Returns the date and whether it was given with month precision only."""
    if value is None:
        return None, False
    if MONTH.match(value):
        return date.fromisoformat(f"{value}-01"), True
    return date.fromisoformat(value), False


def _format_date(value: date | None, precision: PeriodPrecision) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m") if precision is PeriodPrecision.MONTH else value.isoformat()


class CandidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_number: int
    item_number: int
    justification: str = ""


class ActivityFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    group_number: int | None = None
    item_number: int | None = None
    description: str = ""
    event_date: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    academic_period: str | None = None
    level: Level | None = None
    quantidade: Decimal | None = None
    horas: Decimal | None = None
    course_hours: Decimal | None = None
    informed_points: Decimal | None = None
    points_override: Decimal | None = None
    evidence_note: str | None = None
    candidates: list[CandidateIn] = []
    justificativa: str | None = None

    @field_validator("event_date", "period_start", "period_end")
    @classmethod
    def _valid_date(cls, value: str | None) -> str | None:
        try:
            _parse_date(value)
        except ValueError:
            raise ValueError("Data inválida; use AAAA-MM-DD ou AAAA-MM") from None
        return value

    def to_data(self) -> ActivityData:
        parsed = [_parse_date(v) for v in (self.event_date, self.period_start, self.period_end)]
        (event, _), (start, _), (end, _) = parsed
        month = any(is_month for _, is_month in parsed)
        return ActivityData(
            title=self.title,
            group_number=self.group_number,
            item_number=self.item_number,
            description=self.description,
            event_date=event,
            period_start=start,
            period_end=end,
            period_precision=PeriodPrecision.MONTH if month else PeriodPrecision.DAY,
            academic_period=self.academic_period,
            level=self.level,
            quantity=self.quantidade,
            hours=self.horas,
            course_hours=self.course_hours,
            informed_points=self.informed_points,
            points_override=self.points_override,
            evidence_note=self.evidence_note,
            candidates=tuple(
                Candidate(c.group_number, c.item_number, c.justification) for c in self.candidates
            ),
        )


class ActivityCreate(ActivityFields):
    pass


class ActivityUpdate(ActivityFields):
    expected_version: int


class ActivityStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ActivityStatus
    expected_version: int
    justificativa: str | None = None


class ActivityDistinct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int
    justificativa: str | None = None


class ActivityBulkValidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_ids: list[UUID]
    justificativa: str | None = None


class CandidateOut(BaseModel):
    group_number: int
    item_number: int
    justification: str


class ActivityOut(BaseModel):
    id: UUID
    process_id: UUID
    title: str
    group_number: int | None
    item_number: int | None
    description: str
    event_date: str | None
    period_start: str | None
    period_end: str | None
    period_precision: PeriodPrecision
    academic_period: str | None
    level: Level | None
    quantidade: Money | None
    horas: Money | None
    course_hours: Money | None
    informed_points: Money | None
    points_override: Money | None
    evidence_note: str | None
    source: ActivitySource
    status: ActivityStatus
    distinct_justification: str | None
    candidates: list[CandidateOut]
    evidences: list[EvidenceOut]
    created_by: UUID
    created_at: datetime | None
    updated_at: datetime | None
    version: int

    @classmethod
    def of(cls, a: Activity, evidences: Sequence[EvidenceOut] = ()) -> "ActivityOut":
        precision = a.period_precision
        return cls(
            id=a.id,
            process_id=a.process_id,
            title=a.title,
            group_number=a.group_number,
            item_number=a.item_number,
            description=a.description,
            event_date=_format_date(a.event_date, precision),
            period_start=_format_date(a.period_start, precision),
            period_end=_format_date(a.period_end, precision),
            period_precision=precision,
            academic_period=a.academic_period,
            level=a.level,
            quantidade=a.quantity,
            horas=a.hours,
            course_hours=a.course_hours,
            informed_points=a.informed_points,
            points_override=a.points_override,
            evidence_note=a.evidence_note,
            source=a.source,
            status=a.status,
            distinct_justification=a.distinct_justification,
            candidates=[
                CandidateOut(
                    group_number=c.group_number,
                    item_number=c.item_number,
                    justification=c.justification,
                )
                for c in a.candidates
            ],
            evidences=list(evidences),
            created_by=a.created_by,
            created_at=a.created_at,
            updated_at=a.updated_at,
            version=a.version,
        )
