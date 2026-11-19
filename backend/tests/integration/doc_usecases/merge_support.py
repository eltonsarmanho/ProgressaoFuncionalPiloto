"""Builders for the merge tests: duplicate activities with page links, made-up data only."""

import uuid
from datetime import UTC, date, datetime

from app.domain.entities.activity import ActivityStatus
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.doc_usecases.generation_support import add_activity, add_document


def created(day: int) -> datetime:
    return datetime(2026, 11, day, 9, 0, tzinfo=UTC)


def duplicate(world, day: int, title="Visão Computacional com OpenCV", **kwargs):
    """An activity of group II item 7, 10/05/2023, created on 2026-11-<day>; same title and
    date make two of them duplicates (VERIF-05)."""
    fields = dict(
        title=title,
        event_date=date(2023, 5, 10),
        created_at=created(day),
        status=ActivityStatus.AGUARDANDO_REVISAO,
    )
    fields.update(kwargs)
    return add_activity(world, **fields)


def page_link(world, activity, document, page=1) -> ActivityEvidence:
    evidence = ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt="trecho",
        created_by=world.admin.id,
    )
    with world.uow_factory() as uow:
        uow.evidences.add(evidence)
        uow.commit()
    return evidence


def documents(world, count):
    return [add_document(world) for _ in range(count)]


def pages_of(world, activity) -> dict:
    """(document id, page) -> link of the activity."""
    with world.uow_factory() as uow:
        found = uow.evidences.list_for_activity(activity.id)
    return {(e.document_id, e.page_number): e for e in found}


def load(world, activity):
    with world.uow_factory() as uow:
        return uow.activities.get(activity.id)


def merge_events(world, activity) -> list:
    with world.uow_factory() as uow:
        return [
            e
            for e in uow.audit.list_for("activity", str(activity.id))
            if "operation" in e.changes
        ]
