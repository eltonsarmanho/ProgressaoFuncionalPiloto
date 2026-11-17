"""Ports implemented by the infrastructure layer (AD-001)."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO, Protocol, Self
from uuid import UUID

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.audit import AuditEvent
from app.domain.entities.career import CareerVersion
from app.domain.entities.document import (
    DocAlertCode,
    Document,
    DocumentStatus,
    ExtractionRun,
    PageText,
    RunStatus,
    TextMethod,
)
from app.domain.entities.extraction import DocumentType
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import ScoringCriterion, ScoringTableVersion
from app.domain.entities.user import Session, User
from app.domain.rules.upload_validation import FileFacts, FileKind


class Clock(Protocol):
    def now(self) -> datetime: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class UserRepository(Protocol):
    def get(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def add(self, user: User) -> None: ...

    def list(self) -> Sequence[User]: ...


class SessionRepository(Protocol):
    def get_by_token_hash(self, token_hash: str) -> Session | None: ...

    def add(self, session: Session) -> None: ...

    def touch(self, session_id: UUID, last_seen_at: datetime) -> None: ...

    def delete(self, session_id: UUID) -> None: ...


class LoginAttemptRepository(Protocol):
    def record(self, email: str, attempted_at: datetime, success: bool) -> None: ...

    def count_failures_since(self, email: str, since: datetime) -> int: ...


class ProfessorRepository(Protocol):
    def get(self, professor_id: UUID) -> Professor | None: ...

    def add(self, professor: Professor) -> None: ...

    def update(self, professor: Professor, expected_version: int) -> None: ...

    def list(self) -> Sequence[Professor]: ...


class ProcessRepository(Protocol):
    def get(self, process_id: UUID) -> FunctionalProcess | None: ...

    def add(self, process: FunctionalProcess) -> None: ...

    def update(self, process: FunctionalProcess, expected_version: int) -> None: ...

    def list(self) -> Sequence[FunctionalProcess]: ...

    def set_scoring_table_version(self, process_id: UUID, version_id: UUID | None) -> None: ...


class AcademicUnitRepository(Protocol):
    def get(self, unit_id: UUID) -> AcademicUnit | None: ...

    def add(self, unit: AcademicUnit) -> None: ...

    def update(self, unit: AcademicUnit) -> None: ...

    def list(self) -> Sequence[AcademicUnit]: ...


class CareerVersionRepository(Protocol):
    def structure_id(self, structure_code: str) -> UUID | None: ...

    def structure_code(self, structure_id: UUID) -> str | None: ...

    def list_versions(self, structure_code: str) -> Sequence[CareerVersion]: ...

    def add(self, structure_code: str, version: CareerVersion) -> None: ...

    def update(self, version: CareerVersion) -> None: ...


@dataclass
class ScoringTableRecord:
    """A named scoring table and the academic units it is associated with."""

    id: UUID
    name: str
    archived: bool = False
    unit_ids: tuple[UUID, ...] = field(default=())


class ScoringTableRepository(Protocol):
    def list_tables(self) -> Sequence[ScoringTableRecord]: ...

    def get_table(self, table_id: UUID) -> ScoringTableRecord | None: ...

    def add_table(self, table: ScoringTableRecord) -> None: ...

    def set_table_units(self, table_id: UUID, unit_ids: Sequence[UUID]) -> None: ...

    def list_versions(self, table_id: UUID) -> Sequence[ScoringTableVersion]: ...

    def list_versions_for_unit(self, unit_id: UUID) -> Sequence[ScoringTableVersion]: ...

    def get_version(self, version_id: UUID) -> ScoringTableVersion | None: ...

    def add_version(self, version: ScoringTableVersion) -> None: ...

    def update_version(self, version: ScoringTableVersion) -> None: ...

    def update_criterion(self, version_id: UUID, criterion: ScoringCriterion) -> None: ...

    def version_in_use(self, version_id: UUID) -> bool: ...

    def version_in_use_ending_from(self, version_id: UUID, moment: date) -> bool:
        """A process that chose the version has an interstice end date on or after `moment`."""
        ...


class ActivityRepository(Protocol):
    def get(self, activity_id: UUID) -> Activity | None: ...

    def add(self, activity: Activity) -> None: ...

    def update(self, activity: Activity, expected_version: int) -> None: ...

    def list_for_process(
        self,
        process_id: UUID,
        group_number: int | None = None,
        status: ActivityStatus | None = None,
    ) -> Sequence[Activity]: ...


class AuditRepository(Protocol):
    def add(self, event: AuditEvent) -> None: ...

    def list_for(self, entity: str, entity_id: str) -> Sequence[AuditEvent]: ...


class JobStatus(StrEnum):
    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDA = "CONCLUIDA"
    FALHOU = "FALHOU"


@dataclass
class ProcessingJob:
    """A persisted unit of work for the background executor (PIPE-01)."""

    id: UUID
    document_id: UUID
    status: JobStatus = JobStatus.PENDENTE
    attempts: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class ActivityEvidence:
    """Link between an activity and the document page that proves it (VINC-01, VINC-02)."""

    id: UUID
    activity_id: UUID
    document_id: UUID
    page_number: int
    excerpt: str
    created_by: UUID
    run_id: UUID | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ExtractedPage:
    """Text of one page as read by the text extractor, before it belongs to a run."""

    page_number: int
    method: TextMethod
    char_count: int
    ocr_confidence: Decimal | None
    text: str


@dataclass(frozen=True)
class TextExtraction:
    """Pages read so far; `timed_out` keeps the pages extracted before the limit (PIPE-08)."""

    pages: tuple[ExtractedPage, ...]
    timed_out: bool = False


@dataclass(frozen=True)
class AiExtraction:
    """Raw JSON returned by the AI provider and the model that produced it."""

    raw_json: dict[str, Any]
    model: str
    duration_ms: int


class AiExtractionError(Exception):
    """The provider could not answer; `code` is the document alert to record (EXT-04, EXT-05)."""

    def __init__(self, code: DocAlertCode) -> None:
        super().__init__(code.value)
        self.code = code


class DocumentRepository(Protocol):
    def add(self, document: Document) -> None:
        """Raises `Conflict` carrying the existing id when the hash is already in the process."""
        ...

    def get(self, document_id: UUID) -> Document | None: ...

    def list_for_process(
        self,
        process_id: UUID,
        status: DocumentStatus | None = None,
        document_type: str | None = None,
    ) -> Sequence[Document]:
        """In upload order; the type filter matches the manual type, else the suggested one."""
        ...

    def update(self, document: Document, expected_version: int) -> None: ...

    def delete(self, document_id: UUID) -> None:
        """Physical removal with its pages, runs, jobs and links; the activities stay."""
        ...

    def exists_hash(self, process_id: UUID, sha256: str) -> UUID | None:
        """Id of the document with this hash in the process, or None."""
        ...

    def count_for_process(self, process_id: UUID) -> int: ...

    def count_uploads_by_user_since(self, user_id: UUID, since: datetime) -> int: ...


class ExtractionRepository(Protocol):
    def add_run(self, run: ExtractionRun) -> None: ...

    def mark_run_status(self, run_id: UUID, status: RunStatus) -> None: ...

    def list_runs(self, document_id: UUID) -> Sequence[ExtractionRun]: ...

    def replace_pages(self, document_id: UUID, pages: Sequence[PageText]) -> None:
        """Drops the pages stored for the document and stores `pages` in their place."""
        ...

    def list_pages(self, document_id: UUID) -> Sequence[PageText]: ...


class JobRepository(Protocol):
    def add(self, job: ProcessingJob) -> None: ...

    def claim_next(self, now: datetime) -> ProcessingJob | None:
        """Oldest PENDENTE job, marked PROCESSANDO; two concurrent claims never share one."""
        ...

    def finish(
        self, job_id: UUID, status: JobStatus, now: datetime, error_code: str | None = None
    ) -> None: ...

    def recover_stuck(self) -> int:
        """Puts PROCESSANDO jobs back to PENDENTE and returns how many (PIPE-03)."""
        ...

    def active_for_document(self, document_id: UUID) -> ProcessingJob | None: ...


class EvidenceRepository(Protocol):
    def add(self, evidence: ActivityEvidence) -> None: ...

    def remove(self, evidence_id: UUID) -> None: ...

    def list_for_activity(self, activity_id: UUID) -> Sequence[ActivityEvidence]: ...

    def list_for_document(self, document_id: UUID) -> Sequence[ActivityEvidence]: ...

    def counts_for_activities(self, activity_ids: Sequence[UUID]) -> dict[UUID, int]: ...


class FileStorage(Protocol):
    def save(self, process_id: UUID, extension: str, content: bytes) -> str:
        """Stores the bytes under a random name and returns the internal name."""
        ...

    def open(self, process_id: UUID, internal_name: str) -> BinaryIO: ...

    def path(self, process_id: UUID, internal_name: str) -> Path: ...

    def delete(self, process_id: UUID, internal_name: str) -> None: ...


class FileInspector(Protocol):
    def inspect(self, path: Path) -> FileFacts: ...


class TextExtractor(Protocol):
    def extract(self, path: Path, kind: FileKind) -> TextExtraction: ...


class AiExtractor(Protocol):
    def extract(self, document_type: DocumentType, text: str) -> AiExtraction:
        """Raises `AiExtractionError` when the provider refuses or is unavailable."""
        ...


class UnitOfWork(Protocol):
    users: UserRepository
    sessions: SessionRepository
    login_attempts: LoginAttemptRepository
    professors: ProfessorRepository
    processes: ProcessRepository
    units: AcademicUnitRepository
    career_versions: CareerVersionRepository
    scoring_tables: ScoringTableRepository
    activities: ActivityRepository
    audit: AuditRepository
    documents: DocumentRepository
    extractions: ExtractionRepository
    jobs: JobRepository
    evidences: EvidenceRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
