"""Functional process entity and status transitions (PROC-01, PROC-12)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from app.domain.entities.career import Modality
from app.domain.entities.user import Role


class ProcessStatus(StrEnum):
    RASCUNHO = "RASCUNHO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    ARQUIVADO = "ARQUIVADO"

    @property
    def is_read_only(self) -> bool:
        return self in (ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO)


_FORWARD = {
    (ProcessStatus.RASCUNHO, ProcessStatus.EM_ANDAMENTO),
    (ProcessStatus.EM_ANDAMENTO, ProcessStatus.CONCLUIDO),
}


def can_transition(
    current: ProcessStatus, target: ProcessStatus, actor_role: Role, is_owner: bool
) -> bool:
    """RASCUNHO -> EM_ANDAMENTO -> CONCLUIDO; ARQUIVADO from any other status by ADMIN or owner."""
    if (current, target) in _FORWARD:
        return True
    if target is ProcessStatus.ARQUIVADO and current is not ProcessStatus.ARQUIVADO:
        return actor_role is Role.ADMIN or is_owner
    return False


@dataclass
class FunctionalProcess:
    id: UUID
    professor_id: UUID
    unit_id: UUID
    modality: Modality
    current_class: str
    current_denomination: str
    current_level: int
    target_class: str
    target_denomination: str
    target_level: int
    start_date: date
    end_date: date
    opening_date: date
    created_by: UUID
    status: ProcessStatus = ProcessStatus.RASCUNHO
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1
    scoring_table_version_id: UUID | None = None
