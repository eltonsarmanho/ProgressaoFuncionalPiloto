"""Versioned career structure entities (CARR-01, CARR-03)."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from uuid import UUID

from app.domain.entities.professor import Titration


class Modality(StrEnum):
    PROGRESSAO = "PROGRESSAO"
    PROMOCAO = "PROMOCAO"


@dataclass(frozen=True)
class CareerClass:
    code: str
    denominations: tuple[str, ...]
    levels: tuple[int, ...]
    promotion_min_months: int | None  # None: entry class, not reachable by promotion
    required_titration: Titration | None = None  # NTIT-05: None, no titration rule


@dataclass(frozen=True)
class CareerVersion:
    name: str
    valid_from: date | None
    valid_to: date | None
    norm_reference: str
    classes: tuple[CareerClass, ...]
    progression_min_months: int = 24
    norm_code: str | None = None  # NLINK-01: the norm behind the structure
    required_titration_norm_code: str | None = None  # the norm behind the titration rules
    id: UUID | None = field(default=None, compare=False)  # persistence identity only

    def covers(self, moment: date) -> bool:
        after_start = self.valid_from is None or self.valid_from <= moment
        before_end = self.valid_to is None or moment <= self.valid_to
        return after_start and before_end

    def get_class(self, code: str) -> CareerClass | None:
        return next((c for c in self.classes if c.code == code), None)

    def next_class(self, code: str) -> CareerClass | None:
        codes = [c.code for c in self.classes]
        if code not in codes:
            return None
        index = codes.index(code) + 1
        return self.classes[index] if index < len(self.classes) else None

    def min_months(self, modality: Modality, target_class: str) -> int | None:
        if modality is Modality.PROGRESSAO:
            return self.progression_min_months
        target = self.get_class(target_class)
        return target.promotion_min_months if target else None


def select_version(versions: Iterable[CareerVersion], end_date: date) -> CareerVersion | None:
    """Version whose validity contains the interstice end date (CARR-01)."""
    return next((v for v in versions if v.covers(end_date)), None)
