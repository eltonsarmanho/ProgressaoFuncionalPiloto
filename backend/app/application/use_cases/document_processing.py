"""Background processing of a document: analyze, store the run and create the suggestions.

The analysis (OCR and AI) runs without a database connection. The result is stored in one unit
of work; the activities are then created through the scoring use case, as the uploader, with
origin `SUGERIDA_IA` and status `AGUARDANDO_REVISAO`, and each is linked to the document page
and excerpt it came from (PIPE-01, PIPE-02, PIPE-10, PIPE-11, VINC-01, CLS-08).

Logs carry identifiers, methods, durations, page counts and codes only (PIPE-10).
"""

import logging
import re
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.services.document_analyzer import (
    AnalysisResult,
    DocAlert,
    DocumentAnalyzer,
    SuggestedActivity,
)
from app.application.use_cases.documents import DOCUMENT_ENTITY, EVIDENCE_ENTITY
from app.application.use_cases.scoring import ActivityData, CreateActivity
from app.domain.entities.activity import Activity, ActivitySource
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import (
    DocAlertCode,
    Document,
    DocumentStatus,
    ExtractionRun,
    PageText,
    RunStatus,
    can_transition,
)
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.entities.user import User
from app.domain.errors import NotFound, ValidationFailed
from app.domain.repositories.ports import (
    DEFAULT_MAX_JOB_ATTEMPTS,
    ActivityEvidence,
    Clock,
    FileStorage,
    JobStatus,
    UnitOfWork,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.upload_validation import FileKind

logger = logging.getLogger("app.documents.processing")

INTERNAL_ERROR = "ERRO_INTERNO"
NO_ITEM_CATEGORY = DocAlertCode.SEM_ITEM_DE_PONTUACAO.value
MAX_EXCERPT_CHARS = 300
MAX_TITLE_CHARS = 300
_KIND_BY_MIME = {
    "application/pdf": FileKind.PDF,
    "image/jpeg": FileKind.JPEG,
    "image/png": FileKind.PNG,
}
_PERIOD = re.compile(r"^(\d{4})\s*[/.\-]\s*(\d)$")


@dataclass(frozen=True)
class _Job:
    document: Document
    process: FunctionalProcess
    professor: Professor
    table_version: ScoringTableVersion | None
    uploader: User


def _alert_dict(alert: DocAlert) -> dict:
    return {
        "code": alert.code.value,
        "field": alert.field,
        "activity_index": alert.activity_index,
    }


def _academic_period(value: str | None) -> str | None:
    """The AI writes `2025/1`; the activity wants `2025.1`; anything else is dropped."""
    found = _PERIOD.match((value or "").strip())
    return f"{found.group(1)}.{found.group(2)}" if found else None


def _fallback_title(suggested: SuggestedActivity) -> str:
    return suggested.taxonomy.value.replace("_", " ").capitalize()


def _activity_data(suggested: SuggestedActivity) -> ActivityData:
    extracted = suggested.extracted
    title = (extracted.title or "").strip() or _fallback_title(suggested)
    return ActivityData(
        title=title[:MAX_TITLE_CHARS],
        group_number=suggested.group_number,
        item_number=suggested.item_number,
        event_date=extracted.event_date,
        period_start=extracted.start_date,
        period_end=extracted.end_date,
        academic_period=_academic_period(suggested.academic_period),
        level=suggested.level,
        quantity=suggested.quantity,
        hours=suggested.hours,
        course_hours=suggested.course_hours,
        candidates=suggested.candidates,
        period_precision=suggested.period_precision,
    )


class ProcessDocument:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        storage: FileStorage,
        analyzer: DocumentAnalyzer,
        create_activity: CreateActivity,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._storage = storage
        self._analyzer = analyzer
        self._create_activity = create_activity

    def execute(self, job_id: UUID, now: datetime) -> None:
        """Runs one claimed job to its end; never raises for a failure of the document itself.

        An unexpected exception ends the document as FALHOU with `ERRO_INTERNO`; only the
        exception type is logged.
        """
        job = self._load(job_id)
        document_id = job.document.id
        try:
            result = self._analyzer.analyze(
                self._storage.path(job.document.process_id, job.document.internal_name),
                _KIND_BY_MIME[job.document.mime],
                job.professor.full_name,
                job.professor.siape,
                Interstice(job.process.start_date, job.process.end_date),
                job.table_version,
            )
            run = self._store(job.document, result, now)
            if run is None:  # deleted while it was processed: nothing is left to finish
                return
            self._create_suggestions(job, result, run)
            self._finish(job_id, result.status, result.status_code, now)
            logger.info(
                "document_id=%s job_id=%s status=%s code=%s pages=%d methods=%s "
                "duration_ms=%d activities=%d",
                document_id,
                job_id,
                result.status.value,
                result.status_code,
                len(result.pages),
                dict(Counter(p.method.value for p in result.pages)),
                result.duration_ms,
                len(result.activities),
            )
        except Exception as error:
            logger.error(
                "document_id=%s job_id=%s code=%s error_type=%s",
                document_id,
                job_id,
                INTERNAL_ERROR,
                type(error).__name__,
            )
            self._fail(job_id, document_id, now)

    def _load(self, job_id: UUID) -> _Job:
        """Reads everything the analysis needs and moves the document to PROCESSANDO."""
        with self._uow_factory() as uow:
            job = uow.jobs.get(job_id)
            if job is None:
                raise NotFound("Tarefa não encontrada")
            document = uow.documents.get(job.document_id)
            process = uow.processes.get(document.process_id)
            version = None
            if process.scoring_table_version_id is not None:
                version = uow.scoring_tables.get_version(process.scoring_table_version_id)
            loaded = _Job(
                document,
                process,
                uow.professors.get(process.professor_id),
                version,
                uow.users.get(document.uploaded_by),
            )
            if document.status is DocumentStatus.PENDENTE:
                running = replace(document, status=DocumentStatus.PROCESSANDO)
                uow.documents.update(running, document.version)
                uow.commit()
                loaded = replace(loaded, document=running)
            return loaded

    def _store(
        self, document: Document, result: AnalysisResult, now: datetime
    ) -> ExtractionRun | None:
        """Run, pages and the document outcome in one unit of work; None if it was deleted."""
        with self._uow_factory() as uow:
            current = uow.documents.get(document.id)
            if current is None:
                return None
            for old in uow.extractions.list_runs(current.id):
                if old.status is RunStatus.ATIVA:
                    uow.extractions.mark_run_status(old.id, RunStatus.SUBSTITUIDA)
            run = ExtractionRun(
                id=uuid.uuid4(),
                document_id=current.id,
                model=result.model or "",
                duration_ms=result.duration_ms,
                raw_json=result.raw_json or {},
                warnings=tuple(_alert_dict(a) for a in result.alerts),
                created_at=now,
            )
            uow.extractions.add_run(run)
            uow.extractions.replace_pages(
                current.id,
                [
                    PageText(
                        current.id,
                        run.id,
                        p.page_number,
                        p.method,
                        p.char_count,
                        p.ocr_confidence,
                        p.text,
                    )
                    for p in result.pages
                ],
            )
            if not can_transition(current.status, result.status):
                raise ValueError("transition")
            uow.documents.update(
                self._outcome(current, result), current.version
            )
            uow.commit()
            return run

    @staticmethod
    def _outcome(document: Document, result: AnalysisResult) -> Document:
        """Status, code, suggested type and category, and the lowest activity confidence."""
        read_text = result.status is not DocumentStatus.FALHOU and (
            result.status_code != DocAlertCode.TEXTO_ILEGIVEL.value
        )
        category = None
        if result.activities:
            category = result.activities[0].taxonomy.value
        elif result.status is DocumentStatus.PROCESSADO:
            category = NO_ITEM_CATEGORY
        confidence: Decimal | None = min(
            (a.confidence for a in result.activities), default=None
        )
        return replace(
            document,
            status=result.status,
            status_code=result.status_code,
            suggested_type=result.document_type.value if read_text else None,
            suggested_category=category,
            confidence=confidence,
        )

    def _create_suggestions(self, job: _Job, result: AnalysisResult, run: ExtractionRun) -> None:
        for suggested in result.activities:
            activity = self._create(job, suggested, run)
            if activity is None:
                continue
            with self._uow_factory() as uow:
                evidence = ActivityEvidence(
                    id=uuid.uuid4(),
                    activity_id=activity.id,
                    document_id=job.document.id,
                    page_number=suggested.page,
                    excerpt=suggested.excerpt[:MAX_EXCERPT_CHARS],
                    created_by=job.uploader.id,
                    run_id=run.id,
                )
                uow.evidences.add(evidence)
                self._audit.record(
                    uow,
                    job.uploader.id,
                    EVIDENCE_ENTITY,
                    evidence.id,
                    AuditAction.CREATE,
                    {},
                    {
                        "activity_id": evidence.activity_id,
                        "document_id": evidence.document_id,
                        "page_number": evidence.page_number,
                        "operation": "LINK",
                    },
                )
                uow.commit()

    def _create(
        self, job: _Job, suggested: SuggestedActivity, run: ExtractionRun
    ) -> Activity | None:
        """The draft activity; a suggestion the scoring rules refuse is kept without its item.

        The suggested item, level or period may not satisfy the activity rules (ATV-02). The
        reviewer still gets the draft, linked to the document, to classify by hand.
        """
        data = _activity_data(suggested)
        for attempt in (data, ActivityData(title=data.title, event_date=data.event_date)):
            try:
                return self._create_activity.execute(
                    job.uploader,
                    job.process.id,
                    attempt,
                    source=ActivitySource.SUGERIDA_IA,
                    extraction_run_id=run.id,
                )
            except ValidationFailed:
                continue
        return None

    def _finish(
        self, job_id: UUID, status: DocumentStatus, code: str | None, now: datetime
    ) -> None:
        with self._uow_factory() as uow:
            if status is DocumentStatus.FALHOU:
                uow.jobs.finish(job_id, JobStatus.FALHOU, now, code)
            else:
                uow.jobs.finish(job_id, JobStatus.CONCLUIDA, now)
            uow.commit()

    def _fail(self, job_id: UUID, document_id: UUID, now: datetime) -> None:
        with self._uow_factory() as uow:
            document = uow.documents.get(document_id)
            if document is not None and document.status in (
                DocumentStatus.PENDENTE,
                DocumentStatus.PROCESSANDO,
            ):
                failed = replace(
                    document, status=DocumentStatus.FALHOU, status_code=INTERNAL_ERROR
                )
                uow.documents.update(failed, document.version)
            uow.jobs.finish(job_id, JobStatus.FALHOU, now, INTERNAL_ERROR)
            uow.commit()


class RecoverStuckJobs:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        clock: Clock,
        max_attempts: int = DEFAULT_MAX_JOB_ATTEMPTS,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._clock = clock
        self._max_attempts = max_attempts

    def execute(self) -> int:
        """Run at startup: puts the jobs a restart left PROCESSANDO back to PENDENTE.

        A job already claimed `max_attempts` times is closed instead: job FALHOU and document
        FALHOU with `TENTATIVAS_ESGOTADAS`, audited, never requeued (VER-04). Returns how many
        jobs went back to the queue.
        """
        with self._uow_factory() as uow:
            exhausted = uow.jobs.exhaust_stuck(self._max_attempts, self._clock.now())
            for job in exhausted:
                self._fail_document(uow, job.document_id)
            recovered = uow.jobs.recover_stuck(self._max_attempts)
            uow.commit()
        logger.info("recovered_jobs=%d exhausted_jobs=%d", recovered, len(exhausted))
        return recovered

    def _fail_document(self, uow: UnitOfWork, document_id: UUID) -> None:
        document = uow.documents.get(document_id)
        if document is None or document.status not in (
            DocumentStatus.PENDENTE,
            DocumentStatus.PROCESSANDO,
        ):
            return
        failed = replace(
            document,
            status=DocumentStatus.FALHOU,
            status_code=DocAlertCode.TENTATIVAS_ESGOTADAS.value,
        )
        uow.documents.update(failed, document.version)
        self._audit.record(
            uow,
            None,
            DOCUMENT_ENTITY,
            document.id,
            AuditAction.STATUS,
            {"status": document.status, "status_code": document.status_code},
            {"status": failed.status, "status_code": failed.status_code},
        )
