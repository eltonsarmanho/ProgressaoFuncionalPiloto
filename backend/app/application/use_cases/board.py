"""The board of a process: the ordinance (file, reading and data), the draft of the Parecer and the
city of the Requerimento (PORT-01 to PORT-12, PAR-01, PAR-12, PAR-13, REQ-05, BNAV-02, BNAV-03).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden; a
concluded or archived process refuses every write with 409 `PROCESSO_SOMENTE_LEITURA`. The
ordinance is not a `Document`: it creates no row in `documents` and never reaches the activities,
the score or the Comprovante (PORT-09). Audit events carry identifiers, states, counts and codes,
never the name of a board member (third party) and never a justification (regra 5).
"""

from collections.abc import Callable
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.documents import (
    FILE_FIELD,
    MIME_BY_KIND,
    DocumentLimits,
    IncomingFile,
    UploadRejected,
)
from app.application.use_cases.generated_documents import _EditUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import BoardOrdinance, OrdinanceFile, ReadingState
from app.domain.entities.generated import GenerationCode
from app.domain.entities.user import User
from app.domain.errors import Conflict, StaleVersion, ValidationFailed
from app.domain.repositories.ports import Clock, FileInspector, FileStorage, UnitOfWork
from app.domain.rules.upload_validation import extension_of, safe_display_name, validate_upload

BOARD_ENTITY = "board_ordinance"
_IN_PROGRESS = (ReadingState.PENDENTE, ReadingState.LENDO)


def _stale() -> StaleVersion:
    return StaleVersion(
        "A portaria foi alterada por outro usuário; recarregue",
        GenerationCode.VERSAO_DESATUALIZADA.value,
    )


def _file_view(file: OrdinanceFile | None) -> dict:
    """Name, hash and size of the file; the audit never carries what is inside it."""
    if file is None:
        return {}
    return {
        "original_name": file.original_name,
        "sha256": file.sha256,
        "size_bytes": file.size_bytes,
    }


def _state_view(ordinance: BoardOrdinance | None) -> dict:
    if ordinance is None:
        return {}
    return {
        "version": ordinance.version,
        "reading_state": ordinance.reading_state,
        **_file_view(ordinance.file),
    }


class _BoardUseCase(_EditUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        clock: Clock,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock

    def _record(
        self,
        uow: UnitOfWork,
        actor: User,
        process_id: UUID,
        action: AuditAction,
        operation: str,
        before: dict,
        after: dict,
    ) -> None:
        self._audit.record(
            uow,
            actor.id,
            BOARD_ENTITY,
            process_id,
            action,
            before,
            {**after, "operation": operation},
        )


class UploadOrdinance(_BoardUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
        inspector: FileInspector,
        clock: Clock,
        limits: DocumentLimits | None = None,
    ) -> None:
        super().__init__(uow_factory, audit, policy, clock)
        self._storage = storage
        self._inspector = inspector
        self._limits = limits or DocumentLimits()

    def execute(
        self,
        actor: User,
        process_id: UUID,
        incoming: IncomingFile,
        expected_version: int,
        replace: bool,
    ) -> BoardOrdinance:
        """Stores the file, queues the reading and audits (PORT-01).

        An ordinance that already has a file asks for `replace` (409 `PORTARIA_EXISTENTE`), and
        the old file leaves the disk only after the commit (PORT-08); an ordinance with only typed
        data takes the first file without it. `expected_version` is 0 when there is no ordinance.
        """
        stored: str | None = None
        try:
            with self._uow_factory() as uow:
                self._editable(uow, actor, process_id)
                facts = self._inspector.inspect(incoming.path)
                extension = extension_of(incoming.original_name)
                rejections = validate_upload(
                    facts, incoming.declared_mime, extension, self._limits.for_validation()
                )
                if rejections:
                    raise UploadRejected(rejections[0].code, rejections[0].message)
                current = uow.board.get(process_id)
                if (current.version if current else 0) != expected_version:
                    raise _stale()
                has_file = current is not None and (
                    current.file is not None and current.file.deleted_at is None
                )
                if has_file and not replace:
                    raise Conflict(
                        "O processo já tem uma portaria da banca enviada; confirme a substituição",
                        GenerationCode.PORTARIA_EXISTENTE.value,
                    )
                stored = self._storage.save(process_id, extension, incoming.path.read_bytes())
                file = OrdinanceFile(
                    internal_name=stored,
                    original_name=safe_display_name(incoming.original_name),
                    mime=MIME_BY_KIND[facts.kind],
                    size_bytes=incoming.size_bytes,
                    sha256=incoming.sha256,
                    page_count=facts.page_count or 1,
                )
                with self._versioned():
                    version = expected_version
                    if current is None:
                        version = uow.board.create(
                            BoardOrdinance(process_id), actor.id, expected_version
                        ).version
                    previous = uow.board.set_file(
                        process_id, file, actor.id, version, self._clock.now()
                    )
                result = uow.board.get(process_id)
                self._record(
                    uow,
                    actor,
                    process_id,
                    AuditAction.UPDATE if current else AuditAction.CREATE,
                    "REPLACE" if has_file else "UPLOAD",
                    _state_view(current),
                    _state_view(result),
                )
                uow.commit()
        except Exception:
            if stored is not None:
                self._storage.delete(process_id, stored)
            raise
        if previous is not None:
            self._storage.delete(process_id, previous.internal_name)
        return result


class RereadOrdinance(_BoardUseCase):
    def execute(self, actor: User, process_id: UUID, expected_version: int) -> BoardOrdinance:
        """"Ler de novo": a finished reading goes back to the queue (PORT-07). Without a file it
        is a 422 on `arquivo`; while the reading is queued or running it is a 409
        `OPERACAO_EM_ANDAMENTO`."""
        with self._uow_factory() as uow:
            self._editable(uow, actor, process_id)
            current = uow.board.get(process_id)
            if current is None or current.file is None or current.file.deleted_at is not None:
                raise ValidationFailed(FILE_FIELD, "A portaria não tem arquivo para ler")
            if current.version != expected_version:
                raise _stale()
            busy = Conflict(
                "A leitura da portaria já está em andamento",
                GenerationCode.OPERACAO_EM_ANDAMENTO.value,
            )
            if current.reading_state in _IN_PROGRESS:
                raise busy
            try:
                with self._versioned():
                    uow.board.request_reading(process_id, expected_version, self._clock.now())
            except StaleVersion:
                raise
            except Conflict:
                raise busy from None  # it was queued between the read and the lock
            result = uow.board.get(process_id)
            self._record(
                uow,
                actor,
                process_id,
                AuditAction.UPDATE,
                "REREAD",
                _state_view(current),
                _state_view(result),
            )
            uow.commit()
        return result
