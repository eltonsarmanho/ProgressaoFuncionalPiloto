"""The version of scoring table in use of each academic unit (GTAB-02, GTAB-03, GTAB-04).

Writes are ADMIN-only and audited (entity `unit_scoring_default`, the id of the unit as entity
id) in the same transaction. The locks always go in the order unit, table, version, and every
fact is read again after them, so two writes of the same unit, or a write and an archiving of
the table, never leave a mark that breaks a guard (GTAB-24).
"""

from collections.abc import Callable
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.users import require_admin
from app.domain.entities.audit import AuditAction
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.repositories.ports import UnitOfWork

UNIT_DEFAULT_ENTITY = "unit_scoring_default"
VERSION_SUPERSEDED = "VERSAO_SUBSTITUIDA"
TABLE_ARCHIVED = "TABELA_ARQUIVADA"
VERSION_NOT_FOUND = "Versão da tabela de pontuação não encontrada"


def _unit_problem(uow: UnitOfWork, unit_id: UUID, table_id: UUID | None) -> str | None:
    """The reason the version of the table cannot be the one in use of the unit, if any."""
    unit = uow.units.get(unit_id)
    if unit is None:
        return "Unidade acadêmica não encontrada"
    if unit.archived:
        return "A unidade acadêmica está arquivada"
    table = uow.scoring_tables.get_table(table_id) if table_id is not None else None
    if table is None or unit_id not in table.unit_ids:
        return "A tabela desta versão não está associada à unidade"
    return None


class SetUnitDefaultVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, unit_id: UUID, version_id: UUID) -> None:
        require_admin(actor)
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            version = repo.get_version(version_id)
            if version is None:
                raise NotFound(VERSION_NOT_FOUND)
            problem = _unit_problem(uow, unit_id, version.table_id)
            if problem:
                raise ValidationFailed("unit_id", problem)
            repo.lock_unit(unit_id)
            if version.table_id is None or not repo.lock_table(version.table_id):
                raise NotFound("Tabela de pontuação não encontrada")
            if not repo.lock_version(version_id):
                raise NotFound(VERSION_NOT_FOUND)
            # Read again under the locks: the table may have been archived or lost the unit.
            version = repo.get_version(version_id)
            table = repo.get_table(version.table_id) if version else None
            if version is None or table is None:
                raise NotFound(VERSION_NOT_FOUND)
            problem = _unit_problem(uow, unit_id, version.table_id)
            if problem:
                raise ValidationFailed("unit_id", problem)
            if version.is_superseded:
                raise Conflict(
                    "Esta versão da tabela foi substituída; marque a versão atual",
                    code=VERSION_SUPERSEDED,
                )
            if table.archived:
                raise Conflict(
                    "A tabela está arquivada; desarquive-a antes de marcar uma versão em uso",
                    code=TABLE_ARCHIVED,
                )
            current = repo.get_unit_default(unit_id)
            before = current.version_id if current else None
            repo.set_unit_default(unit_id, version_id)
            self._audit.record(
                uow,
                actor.id,
                UNIT_DEFAULT_ENTITY,
                unit_id,
                AuditAction.CREATE if current is None else AuditAction.UPDATE,
                {"version_id": before},
                {"version_id": version_id},
            )
            uow.commit()


class ClearUnitDefaultVersion:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], audit: AuditService):
        self._uow_factory = uow_factory
        self._audit = audit

    def execute(self, actor: User, unit_id: UUID) -> None:
        require_admin(actor)
        with self._uow_factory() as uow:
            repo = uow.scoring_tables
            repo.lock_unit(unit_id)
            current = repo.get_unit_default(unit_id)
            if current is None:
                return
            repo.clear_unit_default(unit_id)
            self._audit.record(
                uow,
                actor.id,
                UNIT_DEFAULT_ENTITY,
                unit_id,
                AuditAction.DELETE,
                {"version_id": current.version_id},
                {"version_id": None},
            )
            uow.commit()
