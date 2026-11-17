"""SQLAlchemy ORM models (design.md, Data Models)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.entities.academic_unit import UnitKind
from app.domain.entities.activity import ActivitySource, ActivityStatus, Level, PeriodPrecision
from app.domain.entities.audit import AuditAction
from app.domain.entities.career import Modality
from app.domain.entities.document import DocumentStatus, RunStatus, TextMethod
from app.domain.entities.process import ProcessStatus
from app.domain.entities.professor import Titration, WorkRegime
from app.domain.entities.scoring import ScoringMode, TableStatus
from app.domain.entities.user import Role
from app.domain.repositories.ports import JobStatus


def _enum(enum_cls: type, name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Base(DeclarativeBase):
    pass


class AcademicUnitModel(Base):
    __tablename__ = "academic_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    acronym: Mapped[str] = mapped_column(String(50))
    kind: Mapped[UnitKind] = mapped_column(_enum(UnitKind, "unit_kind"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id")
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"))
    password_hash: Mapped[str] = mapped_column(Text)
    professor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professors.id"), unique=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserUnitModel(Base):
    __tablename__ = "user_units"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), primary_key=True
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttemptModel(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_email_attempted_at", "email", "attempted_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(CITEXT)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    success: Mapped[bool] = mapped_column(Boolean)


class CareerStructureModel(Base):
    __tablename__ = "career_structures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class CareerVersionModel(Base):
    __tablename__ = "career_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_structures.id")
    )
    name: Mapped[str] = mapped_column(String(255))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    norm_reference: Mapped[str] = mapped_column(Text)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProfessorModel(Base):
    __tablename__ = "professors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    siape: Mapped[str] = mapped_column(CHAR(7), unique=True)
    titration: Mapped[Titration] = mapped_column(_enum(Titration, "titration"))
    position: Mapped[str] = mapped_column(String(255))
    career_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("career_structures.id")
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic_units.id"))
    faculty: Mapped[str] = mapped_column(String(255))
    campus: Mapped[str] = mapped_column(String(255))
    work_regime: Mapped[WorkRegime] = mapped_column(_enum(WorkRegime, "work_regime"))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)


class FunctionalProcessModel(Base):
    __tablename__ = "functional_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    professor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("professors.id")
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic_units.id"))
    modality: Mapped[Modality] = mapped_column(_enum(Modality, "modality"))
    current_class: Mapped[str] = mapped_column(String(20))
    current_denomination: Mapped[str] = mapped_column(String(100))
    current_level: Mapped[int] = mapped_column(Integer)
    target_class: Mapped[str] = mapped_column(String(20))
    target_denomination: Mapped[str] = mapped_column(String(100))
    target_level: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    opening_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProcessStatus] = mapped_column(_enum(ProcessStatus, "process_status"))
    resp_name: Mapped[str | None] = mapped_column(String(255))
    resp_position: Mapped[str | None] = mapped_column(String(255))
    resp_appointment: Mapped[str | None] = mapped_column(String(255))
    resp_admin_unit: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)
    scoring_table_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_table_versions.id")
    )


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction, "audit_action"))
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    justification: Mapped[str | None] = mapped_column(Text)


class ScoringTableModel(Base):
    __tablename__ = "scoring_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class ScoringTableUnitModel(Base):
    __tablename__ = "scoring_table_units"

    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_tables.id", ondelete="CASCADE"), primary_key=True
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_units.id"), primary_key=True
    )


class ScoringTableVersionModel(Base):
    __tablename__ = "scoring_table_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scoring_tables.id"))
    name: Mapped[str] = mapped_column(String(255))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    norm_reference: Mapped[str] = mapped_column(Text)
    status: Mapped[TableStatus] = mapped_column(_enum(TableStatus, "table_status"))
    minimums: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoringGroupModel(Base):
    __tablename__ = "scoring_groups"
    __table_args__ = (
        UniqueConstraint("version_id", "number", name="uq_scoring_groups_version_number"),
        CheckConstraint("number BETWEEN 1 AND 8", name="ck_scoring_groups_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_table_versions.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(255))
    counts_in_total: Mapped[bool] = mapped_column(Boolean)
    max_points: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))


class ScoringCriterionModel(Base):
    __tablename__ = "scoring_criteria"
    __table_args__ = (
        UniqueConstraint("group_id", "item_number", name="uq_scoring_criteria_group_item"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoring_groups.id", ondelete="CASCADE")
    )
    item_number: Mapped[int] = mapped_column(SmallInteger)
    description: Mapped[str] = mapped_column(Text)
    unit_label: Mapped[str] = mapped_column(Text)
    mode: Mapped[ScoringMode] = mapped_column(_enum(ScoringMode, "scoring_mode"))
    unit_points: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    hours_per_block: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    weeks_per_semester: Mapped[int | None] = mapped_column(SmallInteger)
    prep_ratio: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    max_points: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    accepted_evidence: Mapped[str] = mapped_column(Text)
    rules: Mapped[str] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)


class ActivityModel(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("functional_processes.id"), index=True
    )
    group_number: Mapped[int | None] = mapped_column(SmallInteger)
    item_number: Mapped[int | None] = mapped_column(SmallInteger)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date)
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    period_precision: Mapped[PeriodPrecision] = mapped_column(
        _enum(PeriodPrecision, "period_precision")
    )
    academic_period: Mapped[str | None] = mapped_column(String(7))
    level: Mapped[Level | None] = mapped_column(_enum(Level, "activity_level"))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    hours: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    course_hours: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    informed_points: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    points_override: Mapped[Decimal | None] = mapped_column(Numeric(9, 2))
    evidence_note: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[ActivitySource] = mapped_column(_enum(ActivitySource, "activity_source"))
    status: Mapped[ActivityStatus] = mapped_column(_enum(ActivityStatus, "activity_status"))
    distinct_justification: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)
    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_runs.id", ondelete="SET NULL")
    )


class ActivityCandidateModel(Base):
    __tablename__ = "activity_candidates"

    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True
    )
    group_number: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    item_number: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    justification: Mapped[str] = mapped_column(Text)


class DocumentModel(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("process_id", "sha256", name="uq_documents_process_sha256"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("functional_processes.id"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    internal_name: Mapped[str] = mapped_column(String(64), unique=True)
    mime: Mapped[str] = mapped_column(String(40))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    page_count: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[DocumentStatus] = mapped_column(_enum(DocumentStatus, "document_status"))
    status_code: Mapped[str | None] = mapped_column(String(40))
    manual_type: Mapped[str | None] = mapped_column(String(40))
    manual_category: Mapped[str | None] = mapped_column(String(60))
    suggested_type: Mapped[str | None] = mapped_column(String(40))
    suggested_category: Mapped[str | None] = mapped_column(String(60))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)


class ExtractionRunModel(Base):
    """Immutable except for `status`: a trigger refuses any other change (EXT-13)."""

    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus, "extraction_run_status"))
    model: Mapped[str] = mapped_column(String(60))
    duration_ms: Mapped[int] = mapped_column(Integer)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    warnings: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentPageModel(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("run_id", "page_number", name="uq_document_pages_run_page"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_runs.id", ondelete="CASCADE")
    )
    page_number: Mapped[int] = mapped_column(SmallInteger)
    method: Mapped[TextMethod] = mapped_column(_enum(TextMethod, "text_method"))
    char_count: Mapped[int] = mapped_column(Integer)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    text: Mapped[str] = mapped_column(Text)


class ProcessingJobModel(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        Index(
            "uq_processing_jobs_active_document",
            "document_id",
            unique=True,
            postgresql_where=text("status IN ('PENDENTE', 'PROCESSANDO')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")
    )
    status: Mapped[JobStatus] = mapped_column(_enum(JobStatus, "job_status"))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(40))


class ActivityEvidenceModel(Base):
    __tablename__ = "activity_evidences"
    __table_args__ = (
        UniqueConstraint(
            "activity_id", "document_id", "page_number", name="uq_activity_evidences_page"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(SmallInteger)
    excerpt: Mapped[str] = mapped_column(String(300))
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extraction_runs.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
