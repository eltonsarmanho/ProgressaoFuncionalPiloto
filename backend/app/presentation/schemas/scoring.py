"""Scoring schemas: tables, versions and criteria (TAB-08). Decimals leave as 2-place text."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, PlainSerializer

from app.application.use_cases.scoring import ProcessScore, TableRef, TableSuggestion
from app.application.use_cases.scoring_admin import TableView, VersionView
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import RowStatus
from app.domain.rules.scoring_verification import MinimumStatus
from app.presentation.schemas.processes import AlertOut

Money = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]


class CriterionOut(BaseModel):
    group_number: int
    item_number: int
    description: str
    unit_label: str
    mode: ScoringMode
    unit_points: Money | None
    hours_per_block: Money | None
    weeks_per_semester: int | None
    prep_ratio: Money | None
    max_points: Money | None
    accepted_evidence: str
    rules: str
    review_note: str | None

    @classmethod
    def of(cls, c: ScoringCriterion) -> "CriterionOut":
        return cls(**{name: getattr(c, name) for name in cls.model_fields})


class GroupOut(BaseModel):
    number: int
    name: str
    counts_in_total: bool
    max_points: Money | None
    criteria: list[CriterionOut]

    @classmethod
    def of(cls, g: ScoringGroup) -> "GroupOut":
        return cls(
            number=g.number,
            name=g.name,
            counts_in_total=g.counts_in_total,
            max_points=g.max_points,
            criteria=[CriterionOut.of(c) for c in sorted(g.criteria, key=lambda c: c.item_number)],
        )


class VersionRefOut(BaseModel):
    id: UUID
    table_id: UUID
    name: str
    valid_from: date
    valid_to: date | None
    norm_reference: str
    status: TableStatus

    @classmethod
    def of_version(cls, v: ScoringTableVersion) -> "VersionRefOut":
        return cls(**{name: getattr(v, name) for name in VersionRefOut.model_fields})


class VersionSummaryOut(VersionRefOut):
    in_use: bool

    @classmethod
    def of(cls, view: VersionView) -> "VersionSummaryOut":
        return cls(**VersionRefOut.of_version(view.version).model_dump(), in_use=view.in_use)


class VersionOut(VersionSummaryOut):
    minimums: dict[str, Any] | None
    notes: str | None
    groups: list[GroupOut]

    @classmethod
    def of(cls, view: VersionView) -> "VersionOut":
        v = view.version
        return cls(
            **VersionSummaryOut.of(view).model_dump(),
            minimums=v.minimums,
            notes=v.notes,
            groups=[GroupOut.of(g) for g in sorted(v.groups, key=lambda g: g.number)],
        )


class TableOut(BaseModel):
    id: UUID
    name: str
    archived: bool
    unit_ids: list[UUID]
    versions: list[VersionSummaryOut]

    @classmethod
    def of(cls, view: TableView) -> "TableOut":
        t = view.table
        return cls(
            id=t.id,
            name=t.name,
            archived=t.archived,
            unit_ids=list(t.unit_ids),
            versions=[VersionSummaryOut.of(v) for v in view.versions],
        )


class TableRefOut(BaseModel):
    table_name: str
    version: VersionRefOut

    @classmethod
    def of(cls, ref: TableRef | None) -> "TableRefOut | None":
        if ref is None:
            return None
        return cls(table_name=ref.table_name, version=VersionRefOut.of_version(ref.version))


class TableStateOut(BaseModel):
    """Chosen table, suggestion for the professor's unit and table alerts (SEL-02..SEL-07)."""

    chosen: TableRefOut | None
    suggested: TableRefOut | None
    alerts: list[AlertOut]

    @classmethod
    def of(cls, state: TableSuggestion) -> "TableStateOut":
        return cls(
            chosen=TableRefOut.of(state.chosen),
            suggested=TableRefOut.of(state.suggested),
            alerts=[AlertOut.of(a) for a in state.alerts],
        )


class TableChoiceIn(BaseModel):
    version_id: UUID
    justificativa: str | None = None
    expected_version: int | None = None


class GroupSubtotalOut(BaseModel):
    group_number: int
    subtotal: Money


class CountersOut(BaseModel):
    activities: int
    with_evidence: int
    pending: int
    not_scored: int
    with_alerts: int


class ScoreRowOut(BaseModel):
    activity_id: UUID
    title: str
    activity_status: ActivityStatus
    evidence_note: str | None
    group_number: int | None
    item_number: int | None
    unit_points: Money | None
    effective_quantity: Money | None
    formula_text: str
    points: Money
    status: RowStatus
    reasons: list[NotScoredReason]
    alerts: list[AlertOut]


class LimitAdjustmentOut(BaseModel):
    scope: str
    group_number: int
    item_number: int | None
    before: Money
    after: Money
    activity_id: UUID | None
    alert: AlertOut


class MinimumOut(BaseModel):
    status: MinimumStatus
    minimum: Money | None
    total: Money


class ProcessScoreOut(BaseModel):
    process_id: UUID
    chosen: TableRefOut | None
    suggested: TableRefOut | None
    subtotals: list[GroupSubtotalOut]
    total: Money
    potential_total: Money
    group1_percent: Money | None
    counters: CountersOut
    rows: list[ScoreRowOut]
    limit_adjustments: list[LimitAdjustmentOut]
    alerts: list[AlertOut]
    minimum: MinimumOut

    @classmethod
    def of(cls, score: ProcessScore) -> "ProcessScoreOut":
        result = score.result
        activities = {a.id: a for a in score.activities}
        return cls(
            process_id=score.process_id,
            chosen=TableRefOut.of(score.chosen),
            suggested=TableRefOut.of(score.suggested),
            subtotals=[
                GroupSubtotalOut(group_number=n, subtotal=v)
                for n, v in sorted(result.group_subtotals.items())
            ],
            total=result.total,
            potential_total=result.potential_total,
            group1_percent=result.group1_percent,
            counters=CountersOut(**asdict(result.counters)),
            rows=[
                ScoreRowOut(
                    activity_id=r.activity_id,
                    title=activities[r.activity_id].title,
                    activity_status=activities[r.activity_id].status,
                    evidence_note=activities[r.activity_id].evidence_note,
                    group_number=r.group_number,
                    item_number=r.item_number,
                    unit_points=r.unit_points,
                    effective_quantity=r.effective_quantity,
                    formula_text=r.formula_text,
                    points=r.points,
                    status=r.status,
                    reasons=list(r.reasons),
                    alerts=[AlertOut.of(a) for a in r.alerts],
                )
                for r in result.rows
            ],
            limit_adjustments=[
                LimitAdjustmentOut(
                    scope=a.scope,
                    group_number=a.group_number,
                    item_number=a.item_number,
                    before=a.before,
                    after=a.after,
                    activity_id=a.activity_id,
                    alert=AlertOut.of(a.alert),
                )
                for a in result.limit_adjustments
            ],
            alerts=[AlertOut.of(a) for a in score.alerts],
            minimum=MinimumOut(
                status=score.minimum.status,
                minimum=score.minimum.minimum,
                total=score.minimum.total,
            ),
        )
