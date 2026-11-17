"""Scoring schemas: tables, versions and criteria (TAB-08). Decimals leave as 2-place text."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, PlainSerializer

from app.application.use_cases.scoring_admin import TableView, VersionView
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    TableStatus,
)

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


class VersionSummaryOut(BaseModel):
    id: UUID
    table_id: UUID
    name: str
    valid_from: date
    valid_to: date | None
    norm_reference: str
    status: TableStatus
    in_use: bool

    @classmethod
    def of(cls, view: VersionView) -> "VersionSummaryOut":
        v = view.version
        return cls(
            id=v.id,
            table_id=v.table_id,
            name=v.name,
            valid_from=v.valid_from,
            valid_to=v.valid_to,
            norm_reference=v.norm_reference,
            status=v.status,
            in_use=view.in_use,
        )


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
