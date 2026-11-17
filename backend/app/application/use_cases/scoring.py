"""Scoring use cases for a process: table choice, activities and calculation.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.process_verification import Alert
from app.domain.rules.scoring_table_choice import verify_table_choice

PROCESS_ENTITY = "process"
NOT_FOUND = "Processo não encontrado"


@dataclass(frozen=True)
class TableRef:
    table_name: str
    version: ScoringTableVersion


@dataclass(frozen=True)
class TableSuggestion:
    """Chosen version (if any), the suggestion for the professor's unit and table alerts."""

    chosen: TableRef | None
    suggested: TableRef | None
    alerts: list[Alert]


class _ScoringUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._policy = policy

    def _readable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = uow.processes.get(process_id)
        if process is None or not self._policy.can_read_process(actor, process):
            raise NotFound(NOT_FOUND)
        return process

    def _writable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = self._readable(uow, actor, process_id)
        if process.status.is_read_only:
            raise Conflict("Processo concluído ou arquivado não pode ser alterado")
        return process


def _table_ref(uow: UnitOfWork, version: ScoringTableVersion | None) -> TableRef | None:
    if version is None:
        return None
    table = uow.scoring_tables.get_table(version.table_id)
    return TableRef(table.name if table else "", version)


def suggest_version(
    uow: UnitOfWork, professor: Professor, process: FunctionalProcess
) -> ScoringTableVersion | None:
    """Latest version of a table of the professor's unit valid on the interstice end (SEL-02)."""
    candidates = [
        v
        for v in uow.scoring_tables.list_versions_for_unit(professor.unit_id)
        if v.covers(process.end_date)
    ]
    return max(candidates, key=lambda v: v.valid_from, default=None)


def table_alerts(
    uow: UnitOfWork,
    professor: Professor,
    process: FunctionalProcess,
    chosen: ScoringTableVersion | None,
    suggested: ScoringTableVersion | None,
) -> list[Alert]:
    """Alerts about the table of the process (SEL-03, SEL-05..SEL-07)."""
    if chosen is None:
        # Without a choice only the absence of any candidate is worth an alert (SEL-03).
        if suggested is None:
            return verify_table_choice(None, (), professor.unit_id, process.end_date)
        return []
    table = uow.scoring_tables.get_table(chosen.table_id)
    unit_ids = table.unit_ids if table else ()
    return verify_table_choice(chosen, unit_ids, professor.unit_id, process.end_date)


def table_state(uow: UnitOfWork, process: FunctionalProcess) -> TableSuggestion:
    professor = uow.professors.get(process.professor_id)
    chosen = None
    if process.scoring_table_version_id is not None:
        chosen = uow.scoring_tables.get_version(process.scoring_table_version_id)
    suggested = suggest_version(uow, professor, process)
    return TableSuggestion(
        chosen=_table_ref(uow, chosen),
        suggested=_table_ref(uow, suggested),
        alerts=table_alerts(uow, professor, process, chosen, suggested),
    )


class SuggestScoringTable(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> TableSuggestion:
        """Never writes: the suggestion applies only after the user confirms it (SEL-02)."""
        with self._uow_factory() as uow:
            return table_state(uow, self._readable(uow, actor, process_id))


class ChooseProcessTable(_ScoringUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        version_id: UUID,
        expected_version: int | None,
        justification: str | None,
    ) -> TableSuggestion:
        with self._uow_factory() as uow:
            process = self._writable(uow, actor, process_id)
            version = uow.scoring_tables.get_version(version_id)
            if version is None:
                raise ValidationFailed("version_id", "Versão de tabela não encontrada")
            professor = uow.professors.get(process.professor_id)
            table = uow.scoring_tables.get_table(version.table_id)
            justification = (justification or "").strip() or None
            if professor.unit_id not in (table.unit_ids if table else ()) and justification is None:
                raise ValidationFailed(
                    "justificativa",
                    "Justificativa obrigatória para tabela de outra unidade acadêmica",
                )
            if expected_version is not None and process.version != expected_version:
                raise StaleVersion("O processo foi alterado por outro usuário; recarregue")
            uow.processes.set_scoring_table_version(process.id, version.id)
            self._audit.record(
                uow,
                actor.id,
                PROCESS_ENTITY,
                process.id,
                AuditAction.UPDATE,
                {"scoring_table_version_id": process.scoring_table_version_id},
                {"scoring_table_version_id": version.id},
                justification,
            )
            uow.commit()
            return table_state(uow, uow.processes.get(process.id))
