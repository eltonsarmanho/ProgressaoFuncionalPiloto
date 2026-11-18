"""Audit trail writer (AUD-01): records only changed fields, with before/after values."""

from collections.abc import Mapping
from datetime import date
from enum import Enum
from typing import Any
from uuid import UUID

from app.domain.entities.audit import AuditAction, AuditEvent
from app.domain.repositories.ports import Clock, UnitOfWork


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, frozenset | set):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Changed fields only: field -> {"before": old, "after": new} (JSON-safe values)."""
    changes = {}
    for field in sorted(set(before) | set(after)):
        old, new = _jsonable(before.get(field)), _jsonable(after.get(field))
        if old != new:
            changes[field] = {"before": old, "after": new}
    return changes


class AuditService:
    def __init__(self, clock: Clock):
        self._clock = clock

    def record(
        self,
        uow: UnitOfWork,
        actor_id: UUID | None,
        entity: str,
        entity_id: UUID | str,
        action: AuditAction,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
        justification: str | None = None,
    ) -> AuditEvent | None:
        """Add the event to the caller's unit of work (same transaction as the change).

        Returns None, writing nothing, when no field changed.
        """
        changes = diff(before, after)
        if not changes:
            return None
        event = AuditEvent(
            occurred_at=self._clock.now(),
            user_id=actor_id,
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            changes=changes,
            justification=justification or None,
        )
        uow.audit.add(event)
        return event
