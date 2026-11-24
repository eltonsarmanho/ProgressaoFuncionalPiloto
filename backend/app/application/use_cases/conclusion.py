"""Concluding a process: the preview of what the conclusion removes (DEL-03) and the conclusion
itself, which purges the input documents (DEL-01, DEL-02, DEL-04, DEL-05, DEL-07 to DEL-10, DEL-15).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden. Audit
events carry counts and codes only, never a file name (DEL-10).
"""

from collections.abc import Callable
from dataclasses import replace
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.purge_inputs import PurgeInputDocuments, ordinance_file_view
from app.application.use_cases.processes import ENTITY, check_status_change
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.conclusion import ConclusionPreview, ConclusionResult
from app.domain.entities.generated import GenerationCode
from app.domain.entities.process import ProcessStatus
from app.domain.entities.user import User
from app.domain.errors import Conflict, GenerationRefused
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.conclusion_rules import (
    PurgeableDocument,
    check_conclusion,
    purge_outcome,
    summarize_purge,
)


class GetConclusionPreview(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> ConclusionPreview:
        """Files and bytes the conclusion frees and the generated kinds that have a PRONTO
        version (DEL-03). Every input document counts, the ones outside the interstice too, and
        so does the ordinance file; `pending_board` lists the board documents still missing
        (DOS-07)."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            documents = uow.documents.list_for_process(process_id)
            ready = uow.generations.latest_ready_by_kind(process_id)
            ordinance = uow.board.get(process_id)
            return summarize_purge(
                documents,
                ready,
                ordinance_file_view(ordinance),
                ordinance is not None and ordinance.is_registered,
            )


class ConcludeProcess(_ScoringUseCase):
    """Verifies, removes the input documents, audits the attempt and, when no file is left, moves
    the process to CONCLUIDO in the same transaction as the last check (DEL-07).

    Not a background task: every step is local and quick, and the partial state lives in the
    database and on the disk, so repeating the request finishes what is left (DEL-09).
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        purge: PurgeInputDocuments,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._purge = purge

    def execute(
        self,
        actor: User,
        process_id: UUID,
        expected_version: int,
        confirm: bool,
        justification: str | None = None,
    ) -> ConclusionResult:
        done = self._verify(actor, process_id, expected_version, confirm)
        if done is not None:
            return done
        removed = self._purge.execute(process_id)
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, process_id)
            # Takes the lock of the process row: a document sent from now on waits for this
            # transaction, so the documents read below are the ones that stay.
            uow.process_purge.busy_reasons(process_id)
            left: list[PurgeableDocument] = [
                d for d in uow.documents.list_for_process(process_id) if d.file_deleted_at is None
            ]
            ordinance_file = ordinance_file_view(uow.board.get(process_id))
            if ordinance_file is not None and ordinance_file.file_deleted_at is None:
                left.append(ordinance_file)
            outcome = purge_outcome(removed.removed, len(left), removed.bytes_freed)
            self._audit.record(
                uow,
                actor.id,
                ENTITY,
                process_id,
                AuditAction.UPDATE,
                {},
                {
                    "operation": "PURGE",
                    "files_removed": removed.removed,
                    "files_pending": len(left),
                    "bytes_removed": removed.bytes_freed,
                    "bytes_pending": sum(d.size_bytes for d in left),
                },
            )
            if outcome.status is ProcessStatus.CONCLUIDO:
                check_status_change(current, actor, ProcessStatus.CONCLUIDO, expected_version)
                concluded = replace(current, status=ProcessStatus.CONCLUIDO)
                uow.processes.update(concluded, expected_version)
                self._audit.record(
                    uow,
                    actor.id,
                    ENTITY,
                    process_id,
                    AuditAction.STATUS,
                    {"status": current.status},
                    {"status": ProcessStatus.CONCLUIDO},
                    (justification or "").strip() or None,
                )
            uow.commit()
            return outcome

    def _verify(
        self, actor: User, process_id: UUID, expected_version: int, confirm: bool
    ) -> ConclusionResult | None:
        """Raises while the conclusion must not start, nothing removed or written. Returns the
        zero result of a process that is already CONCLUIDO (DEL-09), else None."""
        with self._uow_factory() as uow:
            current = self._readable(uow, actor, process_id)
            if current.status is ProcessStatus.CONCLUIDO:
                return ConclusionResult(ProcessStatus.CONCLUIDO, 0, 0, 0)
            check_status_change(current, actor, ProcessStatus.CONCLUIDO, expected_version)
            if not confirm:
                raise GenerationRefused(
                    GenerationCode.CONFIRMACAO_OBRIGATORIA.value,
                    "Confirme a exclusão irreversível dos documentos de entrada",
                )
            ready = uow.generations.latest_ready_by_kind(process_id)
            check = check_conclusion(ready, len(uow.process_purge.busy_reasons(process_id)))
            if check.code is GenerationCode.ARTEFATOS_PENDENTES:
                kinds = ", ".join(kind.value for kind in check.missing_kinds)
                raise GenerationRefused(
                    check.code.value, f"Faltam documentos gerados prontos: {kinds}"
                )
            if check.code is GenerationCode.OPERACAO_EM_ANDAMENTO:
                raise Conflict(
                    "Há geração, redação ou processamento de documento em andamento",
                    code=check.code.value,
                )
            return None
