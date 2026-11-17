"""User management schemas."""

from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.user import Role, User


class UserCreate(BaseModel):
    email: str
    name: str
    role: Role
    password: str
    professor_id: UUID | None = None
    unit_ids: list[UUID] = []


class UserAdminOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: Role
    professor_id: UUID | None
    unit_ids: list[UUID]
    active: bool

    @classmethod
    def of(cls, user: User) -> "UserAdminOut":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            professor_id=user.professor_id,
            unit_ids=sorted(user.unit_ids, key=str),
            active=user.active,
        )
