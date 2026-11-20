"""Functional process use cases (PROC-01..PROC-04, PROC-12..PROC-14; AUTH-08/09; AUD-01/03)."""

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, fields, replace
from datetime import date
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.units import require_active_unit
from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.entities.career import Modality
from app.domain.entities.generated import GenerationCode
from app.domain.entities.process import FunctionalProcess, ProcessStatus, can_transition
from app.domain.entities.user import Role, User
from app.domain.errors import Conflict, Forbidden, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import (
    FileStorage,
    GeneratedFileStorage,
    ProcessDeletionCounts,
    StoredFileArea,
    UnitOfWork,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Alert, ProcessSnapshot, verify_process

logger = logging.getLogger("app.processes")

BUSY_CODE = "OPERACAO_EM_ANDAMENTO"
ENTITY = "process"
NOT_FOUND = "Processo não encontrado"
_AUDIT_EXCLUDED = {"id", "created_at", "updated_at", "version", "created_by"}


@dataclass(frozen=True)
class ProcessData:
    """Fields informed by the user in Step 1 (PROC-01); saved exactly as given (PROC-03)."""

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
    notes: str | None = None
    resp_name: str | None = None
    resp_position: str | None = None
    resp_appointment: str | None = None
    resp_admin_unit: str | None = None


@dataclass(frozen=True)
class ProcessResult:
    process: FunctionalProcess
    interstice_months: int
    interstice_days: int
    alerts: list[Alert]
    professor_name: str


def audit_view(process: FunctionalProcess) -> dict:
    return {k: v for k, v in asdict(process).items() if k not in _AUDIT_EXCLUDED}


def evaluate(uow: UnitOfWork, process: FunctionalProcess) -> ProcessResult:
    """Interstice duration and verification alerts (PROC-02, PROC-04)."""
    professor = uow.professors.get(process.professor_id)
    code = uow.career_versions.structure_code(professor.career_structure_id)
    versions = uow.career_versions.list_versions(code) if code else []
    snapshot = ProcessSnapshot(
        **{f.name: getattr(process, f.name) for f in fields(ProcessSnapshot)}
    )
    interstice = Interstice(process.start_date, process.end_date)
    return ProcessResult(
        process=process,
        interstice_months=interstice.months(),
        interstice_days=interstice.days(),
        alerts=verify_process(snapshot, versions),
        professor_name=professor.full_name,
    )


class _ProcessUseCase:
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


class CreateProcess(_ProcessUseCase):
    def execute(
        self, actor: User, professor_id: UUID, unit_id: UUID, data: ProcessData
    ) -> ProcessResult:
        with self._uow_factory() as uow:
            professor = uow.professors.get(professor_id)
            if professor is None or not self._policy.can_read_professor(actor, professor):
                raise ValidationFailed("professor_id", "Docente não encontrado")
            if professor.archived:
                raise ValidationFailed(
                    "professor_id", "Docente arquivado não pode receber novos processos"
                )
            require_active_unit(uow, unit_id)
            if actor.role is Role.SECRETARIA and not AccessPolicy.covers_unit(actor, unit_id):
                raise Forbidden("Sem permissão para abrir processo nesta unidade")
            process = FunctionalProcess(
                id=uuid.uuid4(),
                professor_id=professor_id,
                unit_id=unit_id,
                created_by=actor.id,
                **asdict(data),
            )
            uow.processes.add(process)
            self._audit.record(
                uow, actor.id, ENTITY, process.id, AuditAction.CREATE, {}, audit_view(process)
            )
            uow.commit()
            return evaluate(uow, uow.processes.get(process.id))


class GetProcess(_ProcessUseCase):
    def execute(self, actor: User, process_id: UUID) -> ProcessResult:
        with self._uow_factory() as uow:
            return evaluate(uow, self._readable(uow, actor, process_id))


class ListProcesses(_ProcessUseCase):
    def execute(self, actor: User) -> Sequence[ProcessResult]:
        with self._uow_factory() as uow:
            return [
                evaluate(uow, p)
                for p in uow.processes.list()
                if self._policy.can_read_process(actor, p)
            ]


def _check_version(process: FunctionalProcess, expected_version: int) -> None:
    if process.version != expected_version:
        raise StaleVersion("O processo foi alterado por outro usuário; recarregue")


class UpdateProcess(_ProcessUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        data: ProcessData,
        justification: str | None,
        expected_version: int,
    ) -> ProcessResult:
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, process_id)
            if current.status.is_read_only:
                raise Conflict("Processo concluído ou arquivado não pode ser alterado")
            justification = (justification or "").strip() or None
            if current.status is ProcessStatus.EM_ANDAMENTO and justification is None:
                raise ValidationFailed(
                    "justificativa", "Justificativa obrigatória para alterar processo em andamento"
                )
            _check_version(current, expected_version)
            process = replace(current, **asdict(data))
            uow.processes.update(process, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                process.id,
                AuditAction.UPDATE,
                audit_view(current),
                audit_view(process),
                justification,
            )
            uow.commit()
            return evaluate(uow, uow.processes.get(process.id))


def is_process_owner(process: FunctionalProcess, actor: User) -> bool:
    """"Dono" (spec Assumptions): the DOCENTE linked to the professor, or the creator."""
    return process.created_by == actor.id or (
        actor.professor_id is not None and actor.professor_id == process.professor_id
    )


def check_status_change(
    current: FunctionalProcess, actor: User, target: ProcessStatus, expected_version: int
) -> None:
    """Raises unless the actor may move the process to `target` now (PROC-12, DEL-15): the table
    of transitions with the roles, then the expected version. Shared by the generic status
    change and by the conclusion."""
    if not can_transition(current.status, target, actor.role, is_process_owner(current, actor)):
        if target is ProcessStatus.ARQUIVADO and current.status is not target:
            raise Forbidden("Apenas ADMIN ou o dono do processo podem arquivá-lo")
        raise Conflict(f"Transição de status não permitida: {current.status} -> {target}")
    _check_version(current, expected_version)


class ChangeProcessStatus(_ProcessUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        target: ProcessStatus,
        expected_version: int,
        justification: str | None = None,
    ) -> ProcessResult:
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, process_id)
            if target is ProcessStatus.CONCLUIDO:
                raise Conflict(
                    "Concluir o processo exclui os documentos de entrada: use a conclusão",
                    code=GenerationCode.CONCLUSAO_EXIGE_EXCLUSAO.value,
                )
            check_status_change(current, actor, target, expected_version)
            process = replace(current, status=target)
            uow.processes.update(process, expected_version)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                process.id,
                AuditAction.STATUS,
                {"status": current.status},
                {"status": target},
                (justification or "").strip() or None,
            )
            uow.commit()
            return evaluate(uow, uow.processes.get(process.id))


class GetProcessHistory(_ProcessUseCase):
    def execute(self, actor: User, process_id: UUID) -> Sequence[AuditEvent]:
        """AUD-03: audit events of the process in chronological order."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            return uow.audit.list_for(ENTITY, str(process_id))


class _DeletionUseCase(_ProcessUseCase):
    def _deletable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        """The process when the actor may delete it: ADMIN, its creator or the linked DOCENTE."""
        process = self._readable(uow, actor, process_id)
        is_owner = process.created_by == actor.id or (
            actor.professor_id is not None and actor.professor_id == process.professor_id
        )
        if actor.role is not Role.ADMIN and not is_owner:
            raise Forbidden("Apenas ADMIN ou o dono do processo podem excluí-lo")
        return process


class GetProcessDeletePreview(_DeletionUseCase):
    def execute(self, actor: User, process_id: UUID) -> ProcessDeletionCounts:
        """GP-D7: how many documents, activities and generated documents a deletion removes."""
        with self._uow_factory() as uow:
            self._deletable(uow, actor, process_id)
            return uow.process_purge.counts(process_id)


class DeleteProcess(_DeletionUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        originals: FileStorage,
        generated: GeneratedFileStorage,
    ):
        super().__init__(uow_factory, audit, policy)
        self._originals = originals
        self._generated = generated

    def execute(self, actor: User, process_id: UUID) -> None:
        """Deletes the process and all that depends on it in one transaction (GP-DEL-03), then
        the files from the disk; a file that cannot be removed only logs (GP-DEL-04)."""
        with self._uow_factory() as uow:
            process = self._deletable(uow, actor, process_id)
            if uow.process_purge.busy_reasons(process_id):
                raise Conflict(
                    "Há documento em processamento, geração ou redação em andamento neste "
                    "processo; aguarde terminar para excluí-lo",
                    code=BUSY_CODE,
                )
            self._audit.record(
                uow, actor.id, ENTITY, process.id, AuditAction.DELETE, audit_view(process), {}
            )
            stored = uow.process_purge.delete_all(process_id)
            uow.commit()
        for file in stored:
            storage = self._originals if file.area is StoredFileArea.INPUT else self._generated
            try:
                storage.delete(file.process_id, file.internal_name)
            except OSError:
                logger.warning(
                    "process delete: could not remove a %s file of owner_id=%s",
                    file.area.value,
                    file.owner_id,
                )
