"""Document use cases: upload, read, download, replace, delete, classify and reprocess.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
Audit events carry identifiers, the file name, the hash and the status only, never the content
(DOC-13). The `operation` of each event is recorded in its changes, because the audit action
enum has no download or delete value.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.scoring import ChangeActivityStatus
from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import (
    Document,
    DocumentStatus,
    ExtractionRun,
    PageText,
    RunStatus,
    can_transition,
)
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import (
    ActivityEvidence,
    Clock,
    FileInspector,
    FileStorage,
    ProcessingJob,
    UnitOfWork,
)
from app.domain.rules.upload_validation import (
    FileKind,
    UploadLimits,
    extension_of,
    safe_display_name,
    validate_upload,
)

DOCUMENT_ENTITY = "document"
EVIDENCE_ENTITY = "activity_evidence"
PROCESS_NOT_FOUND = "Processo não encontrado"
DOCUMENT_NOT_FOUND = "Documento não encontrado"
LIMIT_FIELD = "limite"
FILE_FIELD = "arquivo"
MIME_BY_KIND = {
    FileKind.PDF: "application/pdf",
    FileKind.JPEG: "image/jpeg",
    FileKind.PNG: "image/png",
}
_RATE_WINDOW = timedelta(minutes=1)


@dataclass(frozen=True)
class DocumentLimits:
    """Upload limits (DOC-03, DOC-04, DOC-14); the defaults are the spec values."""

    max_file_bytes: int = 20 * 1024 * 1024
    max_pages: int = 100
    max_megapixels: int = 100
    max_documents_per_process: int = 200
    max_uploads_per_minute: int = 60

    def for_validation(self) -> UploadLimits:
        return UploadLimits(self.max_file_bytes, self.max_pages, self.max_megapixels)


@dataclass(frozen=True)
class IncomingFile:
    """A file already on disk in a temporary path; the caller computed size and SHA-256.

    `original_name` is display text only and never forms a path.
    """

    path: Path
    original_name: str
    declared_mime: str | None
    size_bytes: int
    sha256: str


class UploadRejected(ValidationFailed):
    """A file refused on replacement: 422 on `arquivo` with the rejection code (DOC-02..04)."""

    def __init__(self, code: str, message: str):
        super().__init__(FILE_FIELD, message)
        self.code = code


class DuplicateDocument(Conflict):
    """The same hash is already in the process: 409 carrying the existing id (DOC-07)."""

    def __init__(self, existing_id: UUID | None):
        super().__init__("Este arquivo já foi enviado neste processo")
        self.existing_id = existing_id


@dataclass(frozen=True)
class UploadResult:
    """Outcome of one file of an upload request: 201, 409, 422 or 429 (DOC-01)."""

    original_name: str
    status_code: int
    document: Document | None = None  # 201: the stored document
    existing_document_id: UUID | None = None  # 409: the document with the same hash
    field: str | None = None  # 422: "arquivo" or "limite"
    code: str | None = None
    message: str | None = None


def document_audit_view(document: Document) -> dict:
    """Metadata only: name, hash and status."""
    return {
        "original_name": document.original_name,
        "sha256": document.sha256,
        "status": document.status,
    }


class _DocumentUseCase:
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
            raise NotFound(PROCESS_NOT_FOUND)
        return process

    def _writable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = self._readable(uow, actor, process_id)
        if process.status.is_read_only:
            raise Conflict("Processo concluído ou arquivado não pode ser alterado")
        return process

    def _document(self, uow: UnitOfWork, actor: User, document_id: UUID) -> Document:
        """The document, or NotFound when it does not exist or the process is out of reach."""
        document = uow.documents.get(document_id)
        if document is None:
            raise NotFound(DOCUMENT_NOT_FOUND)
        self._readable(uow, actor, document.process_id)
        return document

    def _record(
        self,
        uow: UnitOfWork,
        actor: User,
        document_id: UUID,
        action: AuditAction,
        operation: str,
        before: dict,
        after: dict,
        justification: str | None = None,
    ) -> None:
        self._audit.record(
            uow,
            actor.id,
            DOCUMENT_ENTITY,
            document_id,
            action,
            before,
            {**after, "operation": operation},
            justification,
        )


class UploadDocuments(_DocumentUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
        inspector: FileInspector,
        clock: Clock,
        limits: DocumentLimits | None = None,
    ):
        super().__init__(uow_factory, audit, policy)
        self._storage = storage
        self._inspector = inspector
        self._clock = clock
        self._limits = limits or DocumentLimits()

    def execute(
        self, actor: User, process_id: UUID, files: Sequence[IncomingFile]
    ) -> list[UploadResult]:
        """One result per file, in order; a failing file never stops the others (DOC-01).

        A process without access is NotFound and a closed one is Conflict, for the whole request.
        """
        with self._uow_factory() as uow:
            self._writable(uow, actor, process_id)
        return [self._upload_one(actor, process_id, file) for file in files]

    def _upload_one(self, actor: User, process_id: UUID, file: IncomingFile) -> UploadResult:
        name = safe_display_name(file.original_name)
        extension = extension_of(file.original_name)
        facts = self._inspector.inspect(file.path)
        rejections = validate_upload(
            facts, file.declared_mime, extension, self._limits.for_validation()
        )
        if rejections:
            first = rejections[0]
            return UploadResult(
                name, 422, field=first.field, code=first.code, message=first.message
            )

        stored: str | None = None
        try:
            with self._uow_factory() as uow:
                refusal = self._refusal(uow, actor, process_id, file, name)
                if refusal is not None:
                    return refusal
                stored = self._storage.save(process_id, extension, file.path.read_bytes())
                document = Document(
                    id=uuid.uuid4(),
                    process_id=process_id,
                    original_name=name,
                    internal_name=stored,
                    mime=MIME_BY_KIND[facts.kind],
                    size_bytes=file.size_bytes,
                    sha256=file.sha256,
                    page_count=facts.page_count or 1,
                    uploaded_by=actor.id,
                    uploaded_at=self._clock.now(),
                )
                uow.documents.add(document)
                uow.jobs.add(ProcessingJob(id=uuid.uuid4(), document_id=document.id))
                self._record(
                    uow,
                    actor,
                    document.id,
                    AuditAction.CREATE,
                    "UPLOAD",
                    {},
                    document_audit_view(document),
                )
                uow.commit()
                return UploadResult(name, 201, document=uow.documents.get(document.id))
        except Conflict:
            # Lost a race for the same hash: the other upload won.
            self._discard(process_id, stored)
            with self._uow_factory() as uow:
                existing = uow.documents.exists_hash(process_id, file.sha256)
            return UploadResult(name, 409, existing_document_id=existing, message="Já enviado")
        except Exception:
            self._discard(process_id, stored)
            raise

    def _refusal(
        self, uow: UnitOfWork, actor: User, process_id: UUID, file: IncomingFile, name: str
    ) -> UploadResult | None:
        existing = uow.documents.exists_hash(process_id, file.sha256)
        if existing is not None:
            return UploadResult(
                name,
                409,
                existing_document_id=existing,
                message="Este arquivo já foi enviado neste processo",
            )
        if uow.documents.count_for_process(process_id) >= self._limits.max_documents_per_process:
            return UploadResult(
                name,
                422,
                field=LIMIT_FIELD,
                message="O processo já tem o número máximo de documentos",
            )
        recent = uow.documents.count_uploads_by_user_since(
            actor.id, self._clock.now() - _RATE_WINDOW
        )
        if recent >= self._limits.max_uploads_per_minute:
            return UploadResult(
                name, 429, message="Muitos envios em um minuto; aguarde e tente novamente"
            )
        return None

    def _discard(self, process_id: UUID, internal_name: str | None) -> None:
        if internal_name is not None:
            self._storage.delete(process_id, internal_name)



@dataclass(frozen=True)
class LinkedActivity:
    """An activity that cites the document, with the links (page and excerpt) to it."""

    activity: Activity
    evidences: tuple[ActivityEvidence, ...]


@dataclass(frozen=True)
class DocumentDetail:
    """What the review screen needs (REV-01).

    `run` is the ACTIVE extraction: its raw JSON is read only and its `warnings` are the
    alerts (a list of `{code, field, activity_index}` dicts). `pages` belong to that run.
    """

    document: Document
    run: ExtractionRun | None
    pages: tuple[PageText, ...]
    activities: tuple[LinkedActivity, ...]

    @property
    def alerts(self) -> tuple:
        return self.run.warnings if self.run else ()


def active_run(uow: UnitOfWork, document_id: UUID) -> ExtractionRun | None:
    runs = [r for r in uow.extractions.list_runs(document_id) if r.status is RunStatus.ATIVA]
    return runs[-1] if runs else None


class GetDocument(_DocumentUseCase):
    def execute(self, actor: User, document_id: UUID) -> DocumentDetail:
        with self._uow_factory() as uow:
            document = self._document(uow, actor, document_id)
            run = active_run(uow, document.id)
            pages = tuple(
                p for p in uow.extractions.list_pages(document.id) if run and p.run_id == run.id
            )
            by_activity: dict[UUID, list[ActivityEvidence]] = {}
            for evidence in uow.evidences.list_for_document(document.id):
                by_activity.setdefault(evidence.activity_id, []).append(evidence)
            linked = [
                LinkedActivity(activity, tuple(evidences))
                for activity_id, evidences in by_activity.items()
                if (activity := uow.activities.get(activity_id)) is not None
            ]
            return DocumentDetail(document, run, pages, tuple(linked))


class ListDocuments(_DocumentUseCase):
    def execute(
        self,
        actor: User,
        process_id: UUID,
        status: DocumentStatus | None = None,
        type: str | None = None,
    ) -> list[Document]:
        """In upload order, with suggested category and confidence (DOC-15).

        The type filter matches the manual type, else the suggested one.
        """
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            return list(uow.documents.list_for_process(process_id, status, type))


@dataclass(frozen=True)
class DownloadedFile:
    path: Path
    name: str  # original name, display text only
    mime: str
    inline: bool


class DownloadDocument(_DocumentUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
    ):
        super().__init__(uow_factory, audit, policy)
        self._storage = storage

    def execute(self, actor: User, document_id: UUID, inline: bool) -> DownloadedFile:
        """The stored original, as attachment or inline (PDF and images only); audited (DOC-08)."""
        with self._uow_factory() as uow:
            document = self._document(uow, actor, document_id)
            if inline and document.mime not in MIME_BY_KIND.values():
                raise ValidationFailed("visualizar", "Só PDF e imagem podem ser visualizados")
            path = self._storage.path(document.process_id, document.internal_name)
            if not path.is_file():
                raise NotFound("Arquivo não encontrado")
            self._record(
                uow,
                actor,
                document.id,
                AuditAction.UPDATE,
                "VIEW" if inline else "DOWNLOAD",
                {},
                {},
            )
            uow.commit()
            return DownloadedFile(path, document.original_name, document.mime, inline)


REPROCESS_JUSTIFICATION = "Substituída por reprocessamento do documento"
_IN_QUEUE = (DocumentStatus.PENDENTE, DocumentStatus.PROCESSANDO)


class _NewRunUseCase(_DocumentUseCase):
    """Replacement and reprocessing both retire the active run and queue a new one (PIPE-09).

    The steps shared by both live here so they behave the same way.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        change_status: ChangeActivityStatus,
    ):
        super().__init__(uow_factory, audit, policy)
        self._change_status = change_status

    def _restartable(self, uow: UnitOfWork, actor: User, document_id: UUID) -> Document:
        """The document of a writable process that is not waiting or running (else 409)."""
        document = self._document(uow, actor, document_id)
        self._writable(uow, actor, document.process_id)
        if not can_transition(document.status, DocumentStatus.PENDENTE):
            raise Conflict("O documento está na fila ou em processamento")
        return document

    @staticmethod
    def _retire_runs_and_queue(uow: UnitOfWork, document: Document) -> list[UUID]:
        """Marks the active runs SUBSTITUIDA and adds the new job; returns the retired run ids.

        A second simultaneous request hits the unique active job and gets Conflict.
        """
        retired = []
        for run in uow.extractions.list_runs(document.id):
            if run.status is RunStatus.ATIVA:
                uow.extractions.mark_run_status(run.id, RunStatus.SUBSTITUIDA)
                retired.append(run.id)
        uow.jobs.add(ProcessingJob(id=uuid.uuid4(), document_id=document.id))
        return retired

    def _reject_untouched_drafts(self, actor: User, process_id: UUID, run_ids: list[UUID]) -> None:
        """Rejects the activities of the retired runs that are still `AGUARDANDO_REVISAO` and
        were never edited (version 1); validated or edited ones stay (PIPE-09)."""
        with self._uow_factory() as uow:
            drafts = [
                a
                for a in uow.activities.list_for_process(
                    process_id, status=ActivityStatus.AGUARDANDO_REVISAO
                )
                if a.extraction_run_id in run_ids and a.version == 1
            ]
        for draft in drafts:
            try:
                self._change_status.execute(
                    actor,
                    draft.id,
                    ActivityStatus.REJEITADA,
                    draft.version,
                    REPROCESS_JUSTIFICATION,
                )
            except StaleVersion:
                continue  # edited meanwhile: it is no longer an untouched draft


class ReplaceDocument(_NewRunUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
        inspector: FileInspector,
        clock: Clock,
        change_status: ChangeActivityStatus,
        limits: DocumentLimits | None = None,
    ):
        super().__init__(uow_factory, audit, policy, change_status)
        self._storage = storage
        self._inspector = inspector
        self._limits = limits or DocumentLimits()

    def execute(self, actor: User, document_id: UUID, file: IncomingFile) -> Document:
        """New file under the same id; the old file goes only after the commit (DOC-09)."""
        stored: str | None = None
        try:
            with self._uow_factory() as uow:
                document = self._restartable(uow, actor, document_id)
                facts = self._inspector.inspect(file.path)
                extension = extension_of(file.original_name)
                rejections = validate_upload(
                    facts, file.declared_mime, extension, self._limits.for_validation()
                )
                if rejections:
                    raise UploadRejected(rejections[0].code, rejections[0].message)
                existing = uow.documents.exists_hash(document.process_id, file.sha256)
                if existing is not None:
                    raise DuplicateDocument(existing)
                stored = self._storage.save(
                    document.process_id, extension, file.path.read_bytes()
                )
                replaced = replace(
                    document,
                    original_name=safe_display_name(file.original_name),
                    internal_name=stored,
                    mime=MIME_BY_KIND[facts.kind],
                    size_bytes=file.size_bytes,
                    sha256=file.sha256,
                    page_count=facts.page_count or 1,
                    status=DocumentStatus.PENDENTE,
                    status_code=None,
                    suggested_type=None,
                    suggested_category=None,
                    confidence=None,
                )
                retired = self._retire_runs_and_queue(uow, document)
                uow.documents.update(replaced, document.version)
                self._record(
                    uow,
                    actor,
                    document.id,
                    AuditAction.UPDATE,
                    "REPLACE",
                    document_audit_view(document),
                    document_audit_view(replaced),
                )
                uow.commit()
                result = uow.documents.get(document.id)
        except Exception:
            if stored is not None:
                self._storage.delete(document.process_id, stored)
            raise
        self._storage.delete(document.process_id, document.internal_name)
        self._reject_untouched_drafts(actor, document.process_id, retired)
        return result


class DeleteDocument(_DocumentUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: FileStorage,
    ):
        super().__init__(uow_factory, audit, policy)
        self._storage = storage

    def execute(self, actor: User, document_id: UUID, justification: str | None) -> None:
        """Physical removal of file, text and links; the activities stay (DOC-10)."""
        with self._uow_factory() as uow:
            document = self._document(uow, actor, document_id)
            self._writable(uow, actor, document.process_id)
            justification = (justification or "").strip()
            if not justification:
                raise ValidationFailed("justificativa", "Justificativa obrigatória para excluir")
            for evidence in uow.evidences.list_for_document(document.id):
                self._audit.record(
                    uow,
                    actor.id,
                    EVIDENCE_ENTITY,
                    evidence.id,
                    AuditAction.UPDATE,
                    {"activity_id": evidence.activity_id, "document_id": document.id},
                    {"operation": "UNLINK"},
                    justification,
                )
            self._record(
                uow,
                actor,
                document.id,
                AuditAction.UPDATE,
                "DELETE",
                document_audit_view(document),
                {},
                justification,
            )
            uow.documents.delete(document.id)
            uow.commit()
        self._storage.delete(document.process_id, document.internal_name)
