"""Synthetic process, professor, unit and ordinance for the Parecer and Requerimento tests."""

from datetime import date
from uuid import uuid4

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.board import (
    BoardMember,
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
    ValueSource,
)
from app.domain.entities.career import Modality
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.report import PageSetup

PAGE = PageSetup(30.0, 20.0, 30.0, 20.0, "Liberation Serif", 12.0)
UNIT = AcademicUnit(uuid4(), "Faculdade de Testes Sintéticos", "FATS", UnitKind.FACULDADE)
PROFESSOR = Professor(
    id=uuid4(),
    full_name="Maria Docente da Silva",
    siape="1234567",
    titration=Titration.DOUTORADO,
    position="Professor",
    career_structure_id=uuid4(),
    unit_id=UNIT.id,
    faculty="Faculdade de Testes Sintéticos",
    campus="Campus Sintético",
    work_regime=WorkRegime.DE,
)


def process(modality=Modality.PROMOCAO, **changes) -> FunctionalProcess:
    """A promotion that jumps from level 4 of class B to level 1 of class C (NMOV-01)."""
    fields = {
        "id": uuid4(),
        "professor_id": PROFESSOR.id,
        "unit_id": UNIT.id,
        "modality": modality,
        "current_class": "B",
        "current_denomination": "Adjunto",
        "current_level": 4,
        "target_class": "C",
        "target_denomination": "Associado",
        "target_level": 1,
        "start_date": date(2022, 11, 23),
        "end_date": date(2024, 11, 23),
        "opening_date": date(2025, 3, 10),
        "created_by": uuid4(),
    }
    fields.update(changes)
    return FunctionalProcess(**fields)


def member(name: str, role=BoardRole.MEMBRO, page=1, source=ValueSource.EXTRAIDO) -> BoardMember:
    return BoardMember(name, role, page, source)


MEMBERS = (
    member("Ana Presidente Souza", BoardRole.PRESIDENTE),
    member("Bruno Membro Lima"),
    member("Carla Suplente Reis", BoardRole.SUPLENTE),
)


def ordinance(members=MEMBERS, number="123/2025", when=date(2025, 3, 10)) -> BoardOrdinance:
    return BoardOrdinance(
        process_id=uuid4(),
        number=number,
        ordinance_date=when,
        members=tuple(members),
    )


def opinion(conclusion=OpinionConclusion.FAVORAVEL, **changes) -> BoardOpinion:
    fields = {
        "process_id": uuid4(),
        "conclusion": conclusion,
        "opinion_date": date(2025, 4, 2),
        "place": "Belém",
        "notes": "Sem observações adicionais.",
    }
    fields.update(changes)
    return BoardOpinion(**fields)
