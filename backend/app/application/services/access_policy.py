"""Who may see what (AUTH-08, AUTH-09). Denied reads surface as NotFound, never 403."""

from uuid import UUID

from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.user import Role, User


class AccessPolicy:
    @staticmethod
    def covers_unit(actor: User, unit_id: UUID) -> bool:
        """ADMIN covers every unit; SECRETARIA only its own; DOCENTE none."""
        if actor.role is Role.ADMIN:
            return True
        return actor.role is Role.SECRETARIA and unit_id in actor.unit_ids

    def can_read_professor(self, actor: User, professor: Professor) -> bool:
        if actor.role is Role.DOCENTE:
            return actor.professor_id == professor.id
        return self.covers_unit(actor, professor.unit_id)

    def can_read_process(self, actor: User, process: FunctionalProcess) -> bool:
        if actor.role is Role.DOCENTE:
            return actor.professor_id is not None and actor.professor_id == process.professor_id
        return self.covers_unit(actor, process.unit_id)
