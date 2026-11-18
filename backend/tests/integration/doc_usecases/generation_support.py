"""Builders for the generation use case tests: activities, documents and page links inserted
straight in the database, with made-up names only."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.document import DocAlertCode
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.documents.factories import make_document

MOMENT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def add_activity(world, process=None, **kwargs) -> Activity:
    """A validated activity of group II item 7, dated inside the interstice, unless told."""
    process = process or world.process
    fields = dict(
        id=uuid.uuid4(),
        process_id=process.id,
        title=f"Atividade {uuid.uuid4().hex[:6]}",
        created_by=world.admin.id,
        group_number=2,
        item_number=7,
        event_date=date(2023, 5, 10),
        quantity=Decimal("1"),
        status=ActivityStatus.VALIDADA,
        created_at=MOMENT,
    )
    fields.update(kwargs)
    activity = Activity(**fields)
    with world.uow_factory() as uow:
        uow.activities.add(activity)
        uow.commit()
    return activity


def add_document(world, process=None, **kwargs):
    """A document row of the process (no file); `outside=True` marks it as out of the interstice."""
    process = process or world.process
    if kwargs.pop("outside", False):
        kwargs["status_code"] = DocAlertCode.DOCUMENTO_FORA_DO_INTERSTICIO.value
    document = make_document(process, world.admin.id, **kwargs)
    with world.uow_factory() as uow:
        uow.documents.add(document)
        uow.commit()
    return document


def link(world, activity, document, page=1) -> ActivityEvidence:
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


class FixedClock:
    def now(self) -> datetime:
        return MOMENT
