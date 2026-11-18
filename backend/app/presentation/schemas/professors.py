"""Professor schemas (DOC-01, DOC-04)."""

from uuid import UUID

from pydantic import BaseModel

from app.application.use_cases.professors import ProfessorView
from app.domain.entities.professor import Titration, WorkRegime


class ProfessorIn(BaseModel):
    full_name: str
    siape: str
    titration: Titration
    position: str
    career: str = "MAGISTERIO_SUPERIOR"
    unit_id: UUID
    faculty: str
    campus: str
    work_regime: WorkRegime


class ProfessorUpdate(ProfessorIn):
    expected_version: int


class VersionIn(BaseModel):
    expected_version: int


class ProfessorOut(BaseModel):
    id: UUID
    full_name: str
    siape: str
    titration: Titration
    position: str
    career: str
    unit_id: UUID
    faculty: str
    campus: str
    work_regime: WorkRegime
    archived: bool
    version: int

    @classmethod
    def of(cls, view: ProfessorView) -> "ProfessorOut":
        p = view.professor
        return cls(
            id=p.id,
            full_name=p.full_name,
            siape=p.siape,
            titration=p.titration,
            position=p.position,
            career=view.career,
            unit_id=p.unit_id,
            faculty=p.faculty,
            campus=p.campus,
            work_regime=p.work_regime,
            archived=p.archived,
            version=p.version,
        )
