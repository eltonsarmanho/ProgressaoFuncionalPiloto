"""Professor (docente) entity (DOC-01, DOC-04)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Titration(StrEnum):
    GRADUACAO = "GRADUACAO"
    ESPECIALIZACAO = "ESPECIALIZACAO"
    MESTRADO = "MESTRADO"
    DOUTORADO = "DOUTORADO"


class WorkRegime(StrEnum):
    H20 = "20H"
    H40 = "40H"
    DE = "DE"


@dataclass
class Professor:
    id: UUID
    full_name: str
    siape: str
    titration: Titration
    position: str
    career_structure_id: UUID
    unit_id: UUID
    faculty: str
    campus: str
    work_regime: WorkRegime
    archived: bool = False
    version: int = 1
