"""Arrangement and plan of the Comprovante (ARR-01 to ARR-08, CMP-01 to CMP-13).

Pure functions over activities, links and document metadata: nothing here opens a file. The
arrangement is what the user orders; the plan is the numbered list of pages the PDF will have.
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
)
from app.domain.repositories.ports import ActivityEvidence


def eligible_activities(activities: Sequence[Activity]) -> list[Activity]:
    """The activities that go in the Comprovante: validated, with group and item."""
    return [
        a
        for a in activities
        if a.status is ActivityStatus.VALIDADA
        and a.group_number is not None
        and a.item_number is not None
    ]


def _table_order(activity: Activity):
    """Group, item, then the date of the activity (undated last) and its creation."""
    day = activity.event_date or activity.period_start or activity.period_end
    return (
        activity.group_number,
        activity.item_number,
        day is None,
        day or date.min,
        activity.created_at is None,
        activity.created_at,
    )


def derive_layout(
    process_id: UUID, activities: Sequence[Activity], evidences: Sequence[ActivityEvidence]
) -> ComprovanteLayout:
    """The layout of a process with no saved arrangement (ARR-01, ARR-05).

    Groups and items follow the table; inside an item activities follow their date; the pages
    of an activity follow the order of its links.
    """
    arranged = sorted(eligible_activities(activities), key=_table_order)
    pages: dict[UUID, list[LayoutPage]] = {a.id: [] for a in arranged}
    keys: list[EvidenceKey] = []
    for found in evidences:
        if found.activity_id in pages:
            pages[found.activity_id].append(LayoutPage(found.document_id, found.page_number))
            keys.append(EvidenceKey(found.activity_id, found.document_id, found.page_number))
    return ComprovanteLayout(
        process_id,
        tuple(
            LayoutActivity(a.id, tuple(pages[a.id]), a.group_number, a.item_number)
            for a in arranged
        ),
        base_evidence_keys=tuple(keys),
    )
