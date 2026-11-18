"""Order and eligibility of the activities that go in the generated documents.

One place for the order of the table (group, item, date) and for the activities that enter the
Comprovante and the Relatório, so the documents and the screen list them alike.
"""

from collections.abc import Sequence
from datetime import date

from app.domain.entities.activity import Activity, ActivityStatus


def eligible_activities(activities: Sequence[Activity]) -> list[Activity]:
    """The activities that go in the documents: validated, with group and item."""
    return [
        a
        for a in activities
        if a.status is ActivityStatus.VALIDADA
        and a.group_number is not None
        and a.item_number is not None
    ]


def table_order(activity: Activity):
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
