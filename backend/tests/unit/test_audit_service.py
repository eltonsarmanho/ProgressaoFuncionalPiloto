"""AUD-01: audit events carry only the changed fields, with before/after values."""

import uuid
from datetime import UTC, date, datetime

from app.application.services.audit_service import AuditService, diff
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus


def test_diff_keeps_only_changed_fields_with_json_safe_values():
    unit = uuid.uuid4()
    same = {"end_date": date(2024, 11, 23), "unit_id": unit, "notes": "igual"}
    before = {**same, "target_level": 1, "status": ProcessStatus.RASCUNHO}
    after = {**same, "target_level": 2, "status": ProcessStatus.EM_ANDAMENTO}

    assert diff(before, after) == {
        "status": {"before": "RASCUNHO", "after": "EM_ANDAMENTO"},
        "target_level": {"before": 1, "after": 2},
    }


class _Clock:
    def now(self):
        return datetime(2026, 11, 16, 12, 0, tzinfo=UTC)


class _Audit:
    def __init__(self):
        self.events = []

    def add(self, event):
        self.events.append(event)


class _Uow:
    def __init__(self):
        self.audit = _Audit()


def test_record_writes_event_with_actor_time_and_justification():
    uow, actor = _Uow(), uuid.uuid4()

    event = AuditService(_Clock()).record(
        uow, actor, "process", "p-1", AuditAction.UPDATE,
        {"target_level": 1}, {"target_level": 2}, "Correção do nível",
    )

    assert uow.audit.events == [event]
    assert (event.user_id, event.entity, event.entity_id, event.action) == (
        actor, "process", "p-1", AuditAction.UPDATE)
    assert event.occurred_at == datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
    assert event.changes == {"target_level": {"before": 1, "after": 2}}
    assert event.justification == "Correção do nível"


def test_record_without_changes_writes_nothing():
    uow = _Uow()

    event = AuditService(_Clock()).record(
        uow, None, "process", "p-1", AuditAction.UPDATE, {"notes": "a"}, {"notes": "a"}
    )

    assert event is None
    assert uow.audit.events == []
