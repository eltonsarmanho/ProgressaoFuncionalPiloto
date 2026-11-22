"""Professor (docente) entity (DOC-01, DOC-04)."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Titration(StrEnum):
    GRADUACAO = "GRADUACAO"
    ESPECIALIZACAO = "ESPECIALIZACAO"
    MESTRADO = "MESTRADO"
    DOUTORADO = "DOUTORADO"


# NTIT-01, NTIT-03: lowest to highest
TITRATION_ORDER: tuple[Titration, ...] = (
    Titration.GRADUACAO,
    Titration.ESPECIALIZACAO,
    Titration.MESTRADO,
    Titration.DOUTORADO,
)


def titration_at_least(actual: Titration, required: Titration) -> bool:
    return TITRATION_ORDER.index(actual) >= TITRATION_ORDER.index(required)


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
