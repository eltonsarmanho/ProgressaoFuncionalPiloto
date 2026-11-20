"""Synthetic builders of the Comprovante tests: activities, links and documents."""

from datetime import UTC, date, datetime, timedelta
from itertools import count
from uuid import UUID, uuid4

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.comprovante import SourceDocument
from app.domain.repositories.ports import ActivityEvidence

PROCESS_ID = uuid4()
_seq = count(1)
_clock = count(0)


def make_activity(group: int, item: int, **kwargs) -> Activity:
    n = next(_seq)
    defaults = {
        "title": f"Atividade {n}",
        "event_date": date(2023, 6, 1),
        "created_at": datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=n),
        "status": ActivityStatus.VALIDADA,
        "group_number": group,
        "item_number": item,
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=PROCESS_ID, created_by=uuid4(), **defaults
    )  # fmt: skip


def link(activity: Activity, document_id: UUID, page: int) -> ActivityEvidence:
    return ActivityEvidence(
        id=uuid4(),
        activity_id=activity.id,
        document_id=document_id,
        page_number=page,
        excerpt="",
        created_by=uuid4(),
        created_at=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=next(_clock)),
    )


def source(page_count: int = 10, **kwargs) -> SourceDocument:
    defaults = {"id": uuid4(), "original_name": "documento.pdf", "page_count": page_count}
    defaults.update(kwargs)
    return SourceDocument(**defaults)
