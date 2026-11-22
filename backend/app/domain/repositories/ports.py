"""Ports implemented by the infrastructure layer (AD-001)."""

from collections.abc import Callable, Collection, Mapping, Sequence
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
from app.domain.entities.comprovante import ComprovanteLayout, ComprovantePlan
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
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
    WordingJob,
)
from app.domain.entities.norm import Norm
from app.domain.entities.process import FunctionalProcess, ProcessStatus
from app.domain.entities.professor import Professor
from app.domain.entities.report import DraftEntry, DraftSection, ReportDocument, ReportDraft
from app.domain.entities.scoring import ScoringCriterion, ScoringTableVersion
from app.domain.entities.user import Session, User
from app.domain.rules.report_draft import ReportConfig
from app.domain.rules.report_wording import WordingItem
from app.domain.rules.table_document import TableDocument, TableHeader
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

    def list_using_version(
        self, version_id: UUID, statuses: Sequence[ProcessStatus]
    ) -> Sequence[FunctionalProcess]:
        """The processes that chose the version and are in one of the statuses, oldest first."""
        ...


class AcademicUnitRepository(Protocol):
    def get(self, unit_id: UUID) -> AcademicUnit | None: ...

    def add(self, unit: AcademicUnit) -> None: ...

    def update(self, unit: AcademicUnit) -> None: ...

    def list(self) -> Sequence[AcademicUnit]: ...


class NormRepository(Protocol):
    def get(self, norm_id: UUID) -> Norm | None: ...

    def get_by_code(self, code: str) -> Norm | None: ...

    def list(self, include_archived: bool = False) -> Sequence[Norm]: ...

    def by_codes(self, codes: Collection[str]) -> Mapping[str, Norm]:
        """The norms found for the codes, by code, in one query; a missing code is left out."""
        ...

    def add(self, norm: Norm) -> None: ...

    def update(self, norm: Norm, expected_version: int) -> None:
        """Saves every field but the code; StaleVersion if the row moved past expected_version."""
        ...


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

    def set_table_archived(self, table_id: UUID, archived: bool) -> None: ...

    def list_versions(self, table_id: UUID) -> Sequence[ScoringTableVersion]: ...

    def list_versions_for_unit(self, unit_id: UUID) -> Sequence[ScoringTableVersion]: ...

    def get_version(self, version_id: UUID) -> ScoringTableVersion | None: ...

    def add_version(self, version: ScoringTableVersion) -> None: ...

    def update_version(self, version: ScoringTableVersion) -> None: ...

    def set_superseded(self, version_id: UUID, superseded_by_id: UUID | None) -> None:
        """Marks the version as replaced by another one (None clears the mark)."""
        ...

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
        include_merged: bool = False,
    ) -> Sequence[Activity]:
        """The activities of the process in creation order; the ones merged into another are
        left out unless `include_merged` (DUP-03)."""
        ...

    def list_merged_into(self, activity_id: UUID) -> Sequence[Activity]:
        """The activities merged into this one, in creation order (DUP-07)."""
        ...

    def set_merged_into(
        self, activity: Activity, target_id: UUID | None, expected_version: int
    ) -> None:
        """Marks the activity as merged into `target_id` (None unmerges it), bumps its version
        and raises StaleVersion when `expected_version` is old (DUP-02)."""
        ...


class AuditRepository(Protocol):
    def add(self, event: AuditEvent) -> None: ...

    def list_for(self, entity: str, entity_id: str) -> Sequence[AuditEvent]: ...


DEFAULT_MAX_JOB_ATTEMPTS = 3
EXHAUSTED_CODE = "TENTATIVAS_ESGOTADAS"


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
    origin_activity_id: UUID | None = None  # the merged activity this link came from (DUP-02)


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

    def mark_file_deleted(self, document_id: UUID, now: datetime) -> None:
        """Sets `file_deleted_at` (DEL-05); the first mark stays, so repeating it is harmless."""
        ...

    def count_uploads_by_user_since(self, user_id: UUID, since: datetime) -> int: ...


class ExtractionRepository(Protocol):
    def add_run(self, run: ExtractionRun) -> None: ...

    def mark_run_status(self, run_id: UUID, status: RunStatus) -> None: ...

    def list_runs(self, document_id: UUID) -> Sequence[ExtractionRun]: ...

    def replace_pages(self, document_id: UUID, pages: Sequence[PageText]) -> None:
        """Drops the pages stored for the document and stores `pages` in their place."""
        ...

    def list_pages(self, document_id: UUID) -> Sequence[PageText]: ...

    def delete_pages(self, document_id: UUID) -> None:
        """Drops the extracted text of every page of the document (DEL-05); runs stay."""
        ...


class JobRepository(Protocol):
    def add(self, job: ProcessingJob) -> None: ...

    def get(self, job_id: UUID) -> ProcessingJob | None: ...

    def claim_next(self, now: datetime) -> ProcessingJob | None:
        """Oldest PENDENTE job, marked PROCESSANDO; two concurrent claims never share one."""
        ...

    def finish(
        self, job_id: UUID, status: JobStatus, now: datetime, error_code: str | None = None
    ) -> None: ...

    def recover_stuck(self, max_attempts: int = DEFAULT_MAX_JOB_ATTEMPTS) -> int:
        """Puts PROCESSANDO jobs back to PENDENTE and returns how many (PIPE-03).

        A job that was already claimed `max_attempts` times is left alone: it is closed by
        `exhaust_stuck`, never requeued (VER-04).
        """
        ...

    def exhaust_stuck(self, max_attempts: int, now: datetime) -> list[ProcessingJob]:
        """Closes the PROCESSANDO jobs claimed `max_attempts` times or more as FALHOU with the
        code TENTATIVAS_ESGOTADAS and returns them (VER-04)."""
        ...

    def active_for_document(self, document_id: UUID) -> ProcessingJob | None: ...

    def active_for_process(self, process_id: UUID) -> Sequence[ProcessingJob]:
        """PENDENTE or PROCESSANDO jobs of the documents of the process (DEL-02)."""
        ...


class EvidenceRepository(Protocol):
    def add(self, evidence: ActivityEvidence) -> None: ...

    def remove(self, evidence_id: UUID) -> None: ...

    def list_for_activity(self, activity_id: UUID) -> Sequence[ActivityEvidence]: ...

    def list_for_document(self, document_id: UUID) -> Sequence[ActivityEvidence]: ...

    def counts_for_activities(self, activity_ids: Sequence[UUID]) -> dict[UUID, int]: ...

    def counts_for_documents(self, document_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Per document, how many distinct activities that were not rejected cite it (UIM-07)."""
        ...

    def content_keys_for_activities(
        self, activity_ids: Sequence[UUID]
    ) -> dict[UUID, set[tuple[UUID, str]]]:
        """Per activity, the (document id, hash of the normalized page text) of its evidences."""
        ...

    def list_for_activities(self, activity_ids: Sequence[UUID]) -> Sequence[ActivityEvidence]:
        """The links of several activities in one query, in creation order."""
        ...

    def clear_excerpts_for_document(self, document_id: UUID) -> None:
        """Turns the excerpt of every link of the document into '' and keeps the page numbers
        (DEL-05, DEL-06)."""
        ...

    def move(
        self, evidence_ids: Sequence[UUID], to_activity_id: UUID, origin_activity_id: UUID
    ) -> list[UUID]:
        """Moves the links to another activity, recording `origin_activity_id` on the ones that
        had no origin yet. A link whose (document, page) the target already has stays where it
        is. Returns the ids moved (DUP-01, DUP-02)."""
        ...

    def restore_from(self, origin_activity_id: UUID) -> list[UUID]:
        """Gives back to `origin_activity_id` the links that came from it and clears their
        origin. Returns the ids restored (DUP-07)."""
        ...


class FileStorage(Protocol):
    def save(self, process_id: UUID, extension: str, content: bytes) -> str:
        """Stores the bytes under a random name and returns the internal name."""
        ...

    def open(self, process_id: UUID, internal_name: str) -> BinaryIO: ...

    def path(self, process_id: UUID, internal_name: str) -> Path: ...

    def delete(self, process_id: UUID, internal_name: str) -> None: ...

    def remove_process_dir(self, process_id: UUID) -> bool:
        """Removes the directory of the process only when it is empty; returns whether it went
        away. A missing or non-empty directory is left alone."""
        ...


class FileInspector(Protocol):
    def inspect(self, path: Path) -> FileFacts: ...


class TextExtractor(Protocol):
    def extract(self, path: Path, kind: FileKind) -> TextExtraction: ...


class AiExtractor(Protocol):
    def extract(
        self, document_type: DocumentType, text: str, professor_name: str | None = None
    ) -> AiExtraction:
        """Raises `AiExtractionError` when the provider refuses or is unavailable.

        `professor_name` is the professor of the process, sent as context so the model does not
        take a student or a board member for the professor (REAL-01); never an identifier.
        """
        ...


class GenerationRepository(Protocol):
    """Generated documents: one row per request, one numbered version per PRONTO (VER-01)."""

    def add(self, generation: GeneratedDocument) -> None:
        """Stores a GERANDO row. Raises `Conflict` with the code `GERACAO_EM_ANDAMENTO` when the
        process already has one of the kind (VER-04)."""
        ...

    def get(self, generation_id: UUID) -> GeneratedDocument | None:
        """The row with its files."""
        ...

    def list_for_process(
        self, process_id: UUID, kind: DocumentKind | None = None
    ) -> Sequence[GeneratedDocument]:
        """GERANDO rows first, then the others from the newest request to the oldest."""
        ...

    def claim_next(self, now: datetime) -> GeneratedDocument | None:
        """Oldest GERANDO row without `started_at`, marked started; two concurrent claims never
        share one."""
        ...

    def finish_ready(
        self,
        generation_id: UUID,
        now: datetime,
        files: Sequence[GeneratedFile],
        snapshot: dict[str, Any],
        alerts: Sequence[GenerationAlert],
        plan_hash: str | None = None,
    ) -> GeneratedDocument:
        """GERANDO to PRONTO with the next version number of the process and kind, the files, the
        snapshot and the alerts (VER-01, VER-02)."""
        ...

    def finish_failed(
        self, generation_id: UUID, now: datetime, error_code: GenerationCode, error_message: str
    ) -> None:
        """GERANDO to FALHOU; a failed row takes no version number (VER-05)."""
        ...

    def recover_interrupted(self, now: datetime) -> Sequence[GeneratedDocument]:
        """Closes the GERANDO rows that had started as FALHOU with `INTERROMPIDA` and returns
        them; a row not started yet stays in the queue (VER-08)."""
        ...

    def latest_ready_by_kind(self, process_id: UUID) -> dict[DocumentKind, GeneratedDocument]:
        """The newest PRONTO version of each kind that has one."""
        ...


class WordingJobRepository(Protocol):
    """Background requests to word one section of the report (REL-13 to REL-15)."""

    def add(self, job: WordingJob) -> None:
        """Stores a GERANDO job. Raises `Conflict` with the code `REDACAO_EM_ANDAMENTO` when the
        section already has one (REL-13)."""
        ...

    def get(self, job_id: UUID) -> WordingJob | None: ...

    def claim_next(self, now: datetime) -> WordingJob | None:
        """Oldest GERANDO job without `started_at`, marked started."""
        ...

    def finish(
        self,
        job_id: UUID,
        now: datetime,
        state: GenerationState,
        error_code: GenerationCode | None = None,
        warnings: Sequence[GenerationAlert] = (),
    ) -> None:
        """GERANDO to PRONTO (with the warnings the section got) or to FALHOU (with the code)."""
        ...

    def recover_interrupted(self, now: datetime) -> Sequence[WordingJob]:
        """Closes the GERANDO jobs that had started as FALHOU with `INTERROMPIDA` (REL-14)."""
        ...

    def latest_by_section(self, process_id: UUID) -> dict[str, WordingJob]:
        """The newest job of each section that has one."""
        ...


class ReportDraftRepository(Protocol):
    """The saved report draft, one per process. Every edit takes the `expected_version` the
    user saw and raises `StaleVersion` when the stored one moved on (REL-07)."""

    def get(self, process_id: UUID) -> ReportDraft | None: ...

    def create(self, draft: ReportDraft, user_id: UUID, expected_version: int) -> ReportDraft:
        """The first save: `expected_version` must be 0 (`StaleVersion` otherwise) and the
        stored draft gets version 1. A second draft for the process raises `Conflict`."""
        ...

    def update_entry(
        self, process_id: UUID, expected_version: int, entry: DraftEntry, user_id: UUID
    ) -> ReportDraft:
        """Replaces the entry of the same activity where it is; the version goes up by one."""
        ...

    def update_section(
        self,
        process_id: UUID,
        expected_version: int,
        section_key: str,
        free_text: str,
        user_id: UUID,
    ) -> ReportDraft:
        """Replaces the free text of the section; the version goes up by one."""
        ...

    def move_entry(
        self,
        process_id: UUID,
        expected_version: int,
        section_key: str,
        entry: DraftEntry,
        user_id: UUID,
    ) -> ReportDraft:
        """Takes the activity of `entry` out of its section and puts `entry` at the end of
        `section_key`; the version goes up by one."""
        ...

    def edit(
        self,
        process_id: UUID,
        expected_version: int,
        change: Callable[[tuple[DraftSection, ...]], tuple[DraftSection, ...]],
        user_id: UUID,
    ) -> ReportDraft:
        """Locks the row, checks `expected_version` and saves what `change` makes of the
        sections as they are stored at that moment; the version goes up by one. It lets an edit
        bring the draft up to date (an activity validated since the last save) in the same
        write, without ever reading the sections before the lock."""
        ...

    def apply_wording_locked(self, process_id: UUID, section: DraftSection) -> ReportDraft:
        """Locks the row and replaces the entries of the section that are not from the user and
        the warnings of the section with the ones in `section`. The version does not change, so
        an edit in flight never conflicts with the wording (REL-07, REL-13)."""
        ...


class LayoutRepository(Protocol):
    """The saved arrangement of the Comprovante, one per process (ARR-07)."""

    def get(self, process_id: UUID) -> ComprovanteLayout | None: ...

    def create(
        self, layout: ComprovanteLayout, user_id: UUID, expected_version: int
    ) -> ComprovanteLayout:
        """The first save: `expected_version` must be 0 (`StaleVersion` otherwise); the stored
        layout gets version 1. A second layout for the process raises `Conflict`."""
        ...

    def update(
        self, layout: ComprovanteLayout, user_id: UUID, expected_version: int
    ) -> ComprovanteLayout:
        """Replaces the content when the stored version is `expected_version`; the version goes
        up by one. `StaleVersion` leaves the stored layout as it was."""
        ...


@dataclass(frozen=True)
class ComprovanteFront:
    """What the cover, the table of contents and the separators say besides the numbers of the
    plan: who the process is about, the names of the table and of the original files (CMP-01).

    `group_names` is by group number and `item_names` by (group, item) number, as the table of
    the chosen version names them; `document_names` is by document id.
    """

    header: TableHeader
    table_name: str
    group_names: Mapping[int, str]
    item_names: Mapping[tuple[int, int], str] = field(default_factory=dict)
    document_names: Mapping[UUID, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AssemblyResult:
    """What the assembler wrote: pages, size and the alerts it found on the way."""

    pages: int
    size_bytes: int
    alerts: tuple[GenerationAlert, ...] = ()


class AiWritingError(Exception):
    """The provider could not word the section; `code` is the alert of the section (REL-05)."""

    def __init__(self, code: GenerationAlertCode) -> None:
        super().__init__(code.value)
        self.code = code


class DocumentWriter(Protocol):
    """Writes the Tabela and the Relatório from their models, to a path (never a stream)."""

    def write_table(self, model: TableDocument, fmt: DocumentFormat, target: Path) -> None: ...

    def write_report(self, model: ReportDocument, fmt: DocumentFormat, target: Path) -> None:
        """`model` is built by `build_report_document`: the header, the identification and the
        sections of the draft that go in the document."""
        ...


class ComprovanteAssembler(Protocol):
    def assemble(
        self,
        plan: ComprovantePlan,
        front: ComprovanteFront,
        resolver: Callable[[UUID], Path],
        target: Path,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> AssemblyResult:
        """Writes the PDF of the plan to `target`; `front` has the names the cover, the table of
        contents and the separators write and `resolver` gives the path of the original of a
        document. The original pages go in unchanged (CMP-02).

        `on_progress(done, total)` is called after every page. Raises `ComprovanteRefused` with
        `ORIGINAL_INDISPONIVEL`, `IMAGEM_GRANDE_DEMAIS` or `COMPROVANTE_GRANDE_DEMAIS`; no file
        is left at `target` when it raises."""
        ...


class ReportWriter(Protocol):
    """The AI that words the entries of one section (REL-03)."""

    def draft(self, section_title: str, items: Sequence[WordingItem]) -> Mapping[UUID, str]:
        """One text per item id. Raises `AiWritingError` when the provider refuses, answers out of
        the schema or takes longer than its deadline."""
        ...


class ReportConfigProvider(Protocol):
    """The versioned template of the Relatório: sections, group map, vocabulary, layout."""

    def load(self) -> ReportConfig:
        """Raises when the configuration file is broken; the message names the file and field."""
        ...


class GeneratedFileStorage(Protocol):
    """Files of the generated documents; written to a temporary path and renamed, never loaded
    into memory."""

    def new_temp_path(self, process_id: UUID) -> Path:
        """A fresh `.tmp-*` path inside the directory of the process."""
        ...

    def commit(self, process_id: UUID, temp: Path, extension: str) -> str:
        """Renames the temporary file to a random name and returns the internal name."""
        ...

    def path(self, process_id: UUID, internal_name: str) -> Path: ...

    def delete(self, process_id: UUID, internal_name: str) -> None: ...

    def remove_process_dir(self, process_id: UUID) -> bool:
        """Removes the directory of the process only when it is empty; returns whether it went
        away. A missing or non-empty directory is left alone."""
        ...

    def free_bytes(self) -> int:
        """Free space of the volume that holds the files (ESPACO_INSUFICIENTE)."""
        ...

    def cleanup(self, referenced: Mapping[UUID, Collection[str]]) -> int:
        """Removes the `.tmp-*` files and the stored files no row refers to (`referenced` maps a
        process to the internal names that have a row); returns how many files went away."""
        ...


class StoredFileArea(StrEnum):
    INPUT = "INPUT"
    GENERATED = "GENERATED"


@dataclass(frozen=True)
class StoredFile:
    """A file on disk that belongs to a process, to be removed after its rows are gone."""

    area: StoredFileArea
    process_id: UUID
    internal_name: str
    owner_id: UUID  # the document or generated document that held it; only for logs


class BusyReason(StrEnum):
    """Work in progress that stops a process from being deleted (GP-DEL-07)."""

    DOCUMENTO_PROCESSANDO = "DOCUMENTO_PROCESSANDO"
    GERACAO_EM_ANDAMENTO = "GERACAO_EM_ANDAMENTO"
    REDACAO_EM_ANDAMENTO = "REDACAO_EM_ANDAMENTO"


@dataclass(frozen=True)
class ProcessDeletionCounts:
    """What a deletion removes, as numbers only (GP-D7)."""

    documents: int
    activities: int
    generated_documents: int


class ProcessPurgeRepository(Protocol):
    """Deletion of a whole process with everything that depends on it (GP-D2)."""

    def busy_reasons(self, process_id: UUID) -> Sequence[BusyReason]:
        """Work in progress for the process: a queued or running extraction, a generation or a
        wording. Empty when nothing runs."""
        ...

    def counts(self, process_id: UUID) -> ProcessDeletionCounts: ...

    def delete_all(self, process_id: UUID) -> Sequence[StoredFile]:
        """Deletes the process and every dependent in the open transaction (never commits) and
        returns the files to remove from the disk after the commit. Raises `NotFound` when the
        process does not exist."""
        ...


class UnitOfWork(Protocol):
    users: UserRepository
    sessions: SessionRepository
    login_attempts: LoginAttemptRepository
    professors: ProfessorRepository
    processes: ProcessRepository
    units: AcademicUnitRepository
    norms: NormRepository
    career_versions: CareerVersionRepository
    scoring_tables: ScoringTableRepository
    activities: ActivityRepository
    audit: AuditRepository
    documents: DocumentRepository
    extractions: ExtractionRepository
    jobs: JobRepository
    evidences: EvidenceRepository
    generations: GenerationRepository
    wording_jobs: WordingJobRepository
    report_drafts: ReportDraftRepository
    comprovante_layouts: LayoutRepository
    process_purge: ProcessPurgeRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
