"""Activity entity and its status rules (ATV-02, ATV-03, ATV-04)."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ActivityStatus(StrEnum):
    AGUARDANDO_REVISAO = "AGUARDANDO_REVISAO"
    VALIDADA = "VALIDADA"
    REJEITADA = "REJEITADA"


class ActivitySource(StrEnum):
    MANUAL = "MANUAL"
    SUGERIDA_IA = "SUGERIDA_IA"
    IMPORTADA = "IMPORTADA"


class Level(StrEnum):
    GRADUACAO = "GRADUACAO"
    POS_GRADUACAO = "POS_GRADUACAO"


class PeriodPrecision(StrEnum):
    DAY = "DAY"
    MONTH = "MONTH"


@dataclass(frozen=True)
class Candidate:
    """Alternative (group, item) the activity could fit, with the reason for the choice."""

    group_number: int
    item_number: int
    justification: str


@dataclass
class Activity:
    id: UUID
    process_id: UUID
    title: str
    created_by: UUID
    group_number: int | None = None
    item_number: int | None = None
    description: str = ""
    event_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    period_precision: PeriodPrecision = PeriodPrecision.DAY
    academic_period: str | None = None
    level: Level | None = None
    quantity: Decimal | None = None
    hours: Decimal | None = None
    course_hours: Decimal | None = None
    informed_points: Decimal | None = None
    points_override: Decimal | None = None
    evidence_note: str | None = None
    source: ActivitySource = ActivitySource.MANUAL
    status: ActivityStatus = ActivityStatus.VALIDADA
    distinct_justification: str | None = None
    candidates: tuple[Candidate, ...] = ()
    created_at: datetime | None = field(default=None)
    updated_at: datetime | None = None
    version: int = 1
    extraction_run_id: UUID | None = None  # the run that suggested it (PIPE-09)


def initial_status(source: ActivitySource) -> ActivityStatus:
    """Manual entries are validated; any other origin waits for human review (ATV-03)."""
    if source is ActivitySource.MANUAL:
        return ActivityStatus.VALIDADA
    return ActivityStatus.AGUARDANDO_REVISAO


def group1_item(level: Level) -> int:
    """Group I item derived from the level: I.1 graduation, I.2 postgraduate (ATV-02)."""
    return 1 if level is Level.GRADUACAO else 2
