"""Test data for process API tests: the two real cases (PROC-10, PROC-11)."""

import uuid

from app.domain.entities.professor import Professor, Titration, WorkRegime

INSTITUTIONAL = {
    "notes": "Observação de teste",
    "resp_name": "Responsável de Teste",
    "resp_position": "Diretor",
    "resp_appointment": "Portaria 1/2025",
    "resp_admin_unit": "Faculdade de Teste",
}

# PROC-10: FASI 2022-2024
FASI_2022_2024 = {
    "modality": "PROMOCAO",
    "current_class": "C",
    "current_denomination": "Adjunto",
    "current_level": 4,
    "target_class": "D",
    "target_denomination": "Associado",
    "target_level": 1,
    "start_date": "2022-11-23",
    "end_date": "2024-11-23",
    "opening_date": "2025-03-10",
    **INSTITUTIONAL,
}

# PROC-11: Requerimento 2024-2026 as written, all optional fields filled
REQUERIMENTO_2024_2026 = {
    "modality": "PROMOCAO",
    "current_class": "D",
    "current_denomination": "Associado",
    "current_level": 4,
    "target_class": "D",
    "target_denomination": "Associado",
    "target_level": 2,
    "start_date": "2024-11-23",
    "end_date": "2026-11-23",
    "opening_date": "2026-11-16",
    **INSTITUTIONAL,
}


def add_professor(uow_factory, unit, siape="1234567", name="Maria Docente da Silva", **kw):
    """Persist a professor of the seeded Magistério Superior structure."""
    with uow_factory() as uow:
        structure_id = uow.career_versions.structure_id("MAGISTERIO_SUPERIOR")
        professor = Professor(
            id=uuid.uuid4(),
            full_name=name,
            siape=siape,
            titration=Titration.DOUTORADO,
            position="Professor do Magistério Superior",
            career_structure_id=structure_id,
            unit_id=unit.id,
            faculty=unit.name,
            campus="Campus Universitário do Tocantins/Cametá",
            work_regime=WorkRegime.DE,
            **kw,
        )
        uow.professors.add(professor)
        uow.commit()
    return professor


def process_payload(professor, case=FASI_2022_2024, **overrides):
    return {
        "professor_id": str(professor.id),
        "unit_id": str(professor.unit_id),
        **case,
        **overrides,
    }
