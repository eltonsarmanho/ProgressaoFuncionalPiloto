"""Audit event entity (AUD-01)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    ARCHIVE = "ARCHIVE"
    STATUS = "STATUS"


@dataclass(frozen=True)
class AuditEvent:
    occurred_at: datetime
    user_id: UUID | None
    entity: str
    entity_id: str
    action: AuditAction
    changes: dict[str, dict[str, Any]]  # field -> {"before": ..., "after": ...}
    justification: str | None = None
    id: int | None = None
