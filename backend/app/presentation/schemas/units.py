"""Academic unit schemas."""

from uuid import UUID

from pydantic import BaseModel

from app.domain.entities.academic_unit import UnitKind


class UnitIn(BaseModel):
    name: str
    acronym: str
    kind: UnitKind
    parent_id: UUID | None = None


class UnitOut(UnitIn):
    id: UUID
    archived: bool
