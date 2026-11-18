"""Users and sessions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "ADMIN"
    SECRETARIA = "SECRETARIA"
    DOCENTE = "DOCENTE"


@dataclass
class User:
    id: UUID
    email: str
    name: str
    role: Role
    password_hash: str
    professor_id: UUID | None = None
    active: bool = True
    unit_ids: frozenset[UUID] = field(default_factory=frozenset)
    created_at: datetime | None = None


@dataclass
class Session:
    id: UUID
    user_id: UUID
    token_hash: str
    csrf_token: str
    created_at: datetime
    last_seen_at: datetime
