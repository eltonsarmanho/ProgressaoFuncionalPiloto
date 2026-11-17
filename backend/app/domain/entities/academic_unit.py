"""Academic unit entity (UNIT-01)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class UnitKind(StrEnum):
    CAMPUS = "CAMPUS"
    INSTITUTO = "INSTITUTO"
    FACULDADE = "FACULDADE"


@dataclass
class AcademicUnit:
    id: UUID
    name: str
    acronym: str
    kind: UnitKind
    parent_id: UUID | None = None
    archived: bool = False
