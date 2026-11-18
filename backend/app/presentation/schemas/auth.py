"""Auth request/response schemas."""

from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.user import Role


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: UUID
    name: str
    role: Role


class MeOut(UserOut):
    csrf_token: str
