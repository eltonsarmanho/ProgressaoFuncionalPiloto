"""Professor registration (DOC-01..DOC-05) with audit trail (AUD-01)."""

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.units import require_active_unit
from app.domain.entities.audit import AuditAction
from app.domain.entities.professor import Professor, Titration, WorkRegime
from app.domain.entities.user import Role, User
from app.domain.errors import Forbidden, NotFound, ValidationFailed
from app.domain.repositories.ports import UnitOfWork

ENTITY = "professor"
_SIAPE = re.compile(r"^\d{7}$")
_REQUIRED_TEXT = (
    ("full_name", "Nome completo"),
    ("position", "Cargo"),
    ("faculty", "Faculdade"),
    ("campus", "Campus"),
)


@dataclass(frozen=True)
class ProfessorData:
    full_name: str
    siape: str
    titration: Titration
    position: str
    career: str  # career structure code, e.g. MAGISTERIO_SUPERIOR
    unit_id: UUID
    faculty: str
    campus: str
    work_regime: WorkRegime


@dataclass(frozen=True)
class ProfessorView:
    professor: Professor
    career: str


def _audit_view(p: Professor) -> dict:
    view = asdict(p)
    view.pop("id")
    view.pop("version")
    return view


def _fields(uow: UnitOfWork, data: ProfessorData) -> dict:
    """Validated professor fields (DOC-01, DOC-02); unit checked separately."""
    values = {f: getattr(data, f).strip() for f, _ in _REQUIRED_TEXT}
    if not _SIAPE.match(data.siape):
        raise ValidationFailed("siape", "A matrícula SIAPE deve conter exatamente 7 dígitos")
    for field, label in _REQUIRED_TEXT:
        if not values[field]:
            raise ValidationFailed(field, f"{label} é obrigatório")
    structure_id = uow.career_versions.structure_id(data.career)
    if structure_id is None:
        raise ValidationFailed("career", "Carreira não cadastrada")
    return dict(
        values,
        siape=data.siape,
        titration=data.titration,
        career_structure_id=structure_id,
        unit_id=data.unit_id,
        work_regime=data.work_regime,
    )


def _require_manage_unit(actor: User, unit_id: UUID) -> None:
    if not AccessPolicy.covers_unit(actor, unit_id):
        raise Forbidden("Sem permissão para cadastrar docente nesta unidade")


class _ProfessorUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._policy = policy

    def _readable(self, uow: UnitOfWork, actor: User, professor_id: UUID) -> Professor:
        professor = uow.professors.get(professor_id)
        if professor is None or not self._policy.can_read_professor(actor, professor):
            raise NotFound("Docente não encontrado")
        return professor

    @staticmethod
    def _view(uow: UnitOfWork, professor: Professor) -> ProfessorView:
        return ProfessorView(
            professor, uow.career_versions.structure_code(professor.career_structure_id)
        )


class CreateProfessor(_ProfessorUseCase):
    def execute(self, actor: User, data: ProfessorData) -> ProfessorView:
        if actor.role is Role.DOCENTE:
            raise Forbidden("Sem permissão para cadastrar docentes")
        with self._uow_factory() as uow:
            fields = _fields(uow, data)
            require_active_unit(uow, data.unit_id)
            _require_manage_unit(actor, data.unit_id)
            professor = Professor(id=uuid.uuid4(), **fields)
            uow.professors.add(professor)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                professor.id,
                AuditAction.CREATE,
                {},
                _audit_view(professor),
            )
            view = self._view(uow, professor)
            uow.commit()
        return view


class UpdateProfessor(_ProfessorUseCase):
    def execute(
        self, actor: User, professor_id: UUID, data: ProfessorData, expected_version: int
    ) -> ProfessorView:
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, professor_id)
            fields = _fields(uow, data)
            if data.unit_id != current.unit_id:
                require_active_unit(uow, data.unit_id)
                if actor.role is not Role.DOCENTE:
                    _require_manage_unit(actor, data.unit_id)
            professor = replace(current, **fields)
            uow.professors.update(professor, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                professor.id,
                AuditAction.UPDATE,
                _audit_view(current),
                _audit_view(professor),
            )
            view = self._view(uow, professor)
            uow.commit()
        return view


class ArchiveProfessor(_ProfessorUseCase):
    def execute(self, actor: User, professor_id: UUID, expected_version: int) -> ProfessorView:
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, professor_id)
            if actor.role is Role.DOCENTE:
                raise Forbidden("Sem permissão para arquivar docentes")
            professor = replace(current, archived=True)
            uow.professors.update(professor, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                professor.id,
                AuditAction.ARCHIVE,
                _audit_view(current),
                _audit_view(professor),
            )
            view = self._view(uow, professor)
            uow.commit()
        return view


class GetProfessor(_ProfessorUseCase):
    def execute(self, actor: User, professor_id: UUID) -> ProfessorView:
        with self._uow_factory() as uow:
            return self._view(uow, self._readable(uow, actor, professor_id))


class ListProfessors(_ProfessorUseCase):
    def execute(self, actor: User) -> Sequence[ProfessorView]:
        with self._uow_factory() as uow:
            return [
                self._view(uow, p)
                for p in uow.professors.list()
                if self._policy.can_read_professor(actor, p)
            ]
