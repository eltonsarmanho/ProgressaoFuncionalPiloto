"""Versioned scoring table entities (TAB-01, TAB-02, TAB-06)."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID


class ScoringMode(StrEnum):
    POR_UNIDADE = "POR_UNIDADE"
    POR_BLOCO_DE_HORAS = "POR_BLOCO_DE_HORAS"
    CARGA_SEMANAL = "CARGA_SEMANAL"
    VALOR_INFORMADO = "VALOR_INFORMADO"


class TableStatus(StrEnum):
    OFICIAL = "OFICIAL"
    PENDENTE_VALIDACAO = "PENDENTE_VALIDACAO"


@dataclass(frozen=True)
class ScoringCriterion:
    group_number: int
    item_number: int
    description: str
    unit_label: str
    mode: ScoringMode
    unit_points: Decimal | None = None
    hours_per_block: Decimal | None = None  # POR_BLOCO_DE_HORAS
    weeks_per_semester: int | None = None  # CARGA_SEMANAL
    prep_ratio: Decimal | None = None  # CARGA_SEMANAL
    max_points: Decimal | None = None
    accepted_evidence: str = ""
    rules: str = ""
    review_note: str | None = None
    min_hours: Decimal | None = None  # minimum course load; below it the activity does not score


@dataclass(frozen=True)
class ScoringGroup:
    number: int  # 1..8 (groups I to VIII)
    name: str
    counts_in_total: bool = True
    max_points: Decimal | None = None
    criteria: tuple[ScoringCriterion, ...] = ()


@dataclass(frozen=True)
class ScoringTableVersion:
    table_id: UUID | None
    name: str
    valid_from: date
    valid_to: date | None
    norm_reference: str
    status: TableStatus
    groups: tuple[ScoringGroup, ...] = ()
    minimums: dict[str, Any] | None = None
    notes: str | None = None
    id: UUID | None = field(default=None, compare=False)  # persistence identity only

    def covers(self, moment: date) -> bool:
        before_end = self.valid_to is None or moment <= self.valid_to
        return self.valid_from <= moment and before_end

    def get_group(self, number: int) -> ScoringGroup | None:
        return next((g for g in self.groups if g.number == number), None)

    def get_criterion(self, group: int, item: int) -> ScoringCriterion | None:
        found = self.get_group(group)
        if found is None:
            return None
        return next((c for c in found.criteria if c.item_number == item), None)
