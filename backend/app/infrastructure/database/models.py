"""SQLAlchemy ORM models (design.md, Data Models)."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.entities.academic_unit import UnitKind
from app.domain.entities.audit import AuditAction
from app.domain.entities.career import Modality
from app.domain.entities.process import ProcessStatus
from app.domain.entities.professor import Titration, WorkRegime
from app.domain.entities.user import Role


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
