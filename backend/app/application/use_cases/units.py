"""Academic unit management (UNIT-01, UNIT-02) with audit trail (AUD-01)."""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.users import require_admin
from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.audit import AuditAction
from app.domain.entities.user import User
from app.domain.errors import NotFound, ValidationFailed
from app.domain.repositories.ports import UnitOfWork

ENTITY = "academic_unit"


def require_active_unit(uow: UnitOfWork, unit_id: UUID, field: str = "unit_id") -> AcademicUnit:
    """UNIT-02: a new professor or process may only reference an existing, active unit."""
    unit = uow.units.get(unit_id)
    if unit is None:
        raise ValidationFailed(field, "Unidade acadêmica não encontrada")
    if unit.archived:
        raise ValidationFailed(field, "Unidade acadêmica arquivada não pode ser selecionada")
    return unit


@dataclass(frozen=True)
class UnitData:
    name: str
    acronym: str
    kind: UnitKind
    parent_id: UUID | None = None


def _audit_view(unit: AcademicUnit) -> dict:
    view = asdict(unit)
    view.pop("id")
    return view


def _validated(uow: UnitOfWork, data: UnitData, unit_id: UUID | None = None) -> UnitData:
    name, acronym = data.name.strip(), data.acronym.strip()
    if not name:
        raise ValidationFailed("name", "Nome é obrigatório")
    if not acronym:
        raise ValidationFailed("acronym", "Sigla é obrigatória")
    if data.parent_id is not None and (
        data.parent_id == unit_id or uow.units.get(data.parent_id) is None
    ):
        raise ValidationFailed("parent_id", "Unidade-mãe inválida")
    return replace(data, name=name, acronym=acronym)


class ListUnits:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self) -> Sequence[AcademicUnit]:
        with self._uow_factory() as uow:
            return uow.units.list()


class CreateUnit:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, data: UnitData) -> AcademicUnit:
        require_admin(actor)
        with self._uow_factory() as uow:
            data = _validated(uow, data)
            unit = AcademicUnit(id=uuid.uuid4(), **asdict(data))
            uow.units.add(unit)
            self._audit.record(
                uow, actor.id, ENTITY, unit.id, AuditAction.CREATE, {}, _audit_view(unit)
            )
            uow.commit()
        return unit


class UpdateUnit:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, unit_id: UUID, data: UnitData) -> AcademicUnit:
        require_admin(actor)
        with self._uow_factory() as uow:
            current = uow.units.get(unit_id)
            if current is None:
                raise NotFound("Unidade não encontrada")
            data = _validated(uow, data, unit_id)
            unit = replace(current, **asdict(data))
            uow.units.update(unit)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                unit.id,
                AuditAction.UPDATE,
                _audit_view(current),
                _audit_view(unit),
            )
            uow.commit()
        return unit


class ArchiveUnit:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, unit_id: UUID) -> AcademicUnit:
        require_admin(actor)
        with self._uow_factory() as uow:
            current = uow.units.get(unit_id)
            if current is None:
                raise NotFound("Unidade não encontrada")
            unit = replace(current, archived=True)
            uow.units.update(unit)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                unit.id,
                AuditAction.ARCHIVE,
                _audit_view(current),
                _audit_view(unit),
            )
            uow.commit()
        return unit
