"""User management (AUTH-10) with audit trail (AUD-01)."""

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role, User
from app.domain.errors import Forbidden, ValidationFailed
from app.domain.repositories.ports import PasswordHasher, UnitOfWork

MIN_PASSWORD_LENGTH = 10
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_admin(actor: User) -> None:
    if actor.role is not Role.ADMIN:
        raise Forbidden("Operação permitida apenas ao perfil ADMIN")


def audit_view(user: User) -> dict:
    """Audited fields of a user; the password hash is never recorded."""
    return {
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "professor_id": user.professor_id,
        "unit_ids": user.unit_ids,
        "active": user.active,
    }


@dataclass(frozen=True)
class NewUser:
    email: str
    name: str
    role: Role
    password: str
    professor_id: UUID | None = None
    unit_ids: frozenset[UUID] = field(default_factory=frozenset)


class CreateUser:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        hasher: PasswordHasher,
        audit: AuditService,
    ):
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._audit = audit

    def execute(self, actor: User, data: NewUser) -> User:
        require_admin(actor)
        email = data.email.strip()
        name = data.name.strip()
        if not _EMAIL.match(email):
            raise ValidationFailed("email", "E-mail inválido")
        if not name:
            raise ValidationFailed("name", "Nome é obrigatório")
        if len(data.password) < MIN_PASSWORD_LENGTH:
            raise ValidationFailed(
                "password", f"A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres"
            )
        with self._uow_factory() as uow:
            if uow.users.get_by_email(email) is not None:
                raise ValidationFailed("email", "E-mail já cadastrado")
            if data.professor_id is not None:
                if uow.professors.get(data.professor_id) is None:
                    raise ValidationFailed("professor_id", "Docente não encontrado")
                if any(u.professor_id == data.professor_id for u in uow.users.list()):
                    raise ValidationFailed("professor_id", "Docente já vinculado a outro usuário")
            if any(uow.units.get(unit_id) is None for unit_id in data.unit_ids):
                raise ValidationFailed("unit_ids", "Unidade acadêmica não encontrada")
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                role=data.role,
                password_hash=self._hasher.hash(data.password),
                professor_id=data.professor_id,
                unit_ids=frozenset(data.unit_ids),
            )
            uow.users.add(user)
            self._audit.record(
                uow, actor.id, "user", user.id, AuditAction.CREATE, {}, audit_view(user)
            )
            uow.commit()
        return user


class ListUsers:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, actor: User) -> Sequence[User]:
        require_admin(actor)
        with self._uow_factory() as uow:
            return uow.users.list()
