"""Ports implemented by the infrastructure layer (AD-001)."""

from collections.abc import Sequence
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.audit import AuditEvent
from app.domain.entities.career import CareerVersion
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.user import Session, User


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


class AuditRepository(Protocol):
    def add(self, event: AuditEvent) -> None: ...

    def list_for(self, entity: str, entity_id: str) -> Sequence[AuditEvent]: ...


class UnitOfWork(Protocol):
    users: UserRepository
    sessions: SessionRepository
    login_attempts: LoginAttemptRepository
    professors: ProfessorRepository
    processes: ProcessRepository
    units: AcademicUnitRepository
    career_versions: CareerVersionRepository
    audit: AuditRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
