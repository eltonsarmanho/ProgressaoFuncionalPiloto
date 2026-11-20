"""Order and eligibility of the activities that go in the generated documents.

One place for the order of the table (group, item, date) and for the activities that enter the
Tabela, the Comprovante and the Relatório, so the documents and the screen list them alike.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.activity_validity import Validity


def validated_activities(activities: Sequence[Activity]) -> list[Activity]:
    """The validated activities with group and item.

    The layout and the report draft start from the activities `eligible_activities` already
    chose (`load_generation_inputs` is the one place that decides validity); they use this to
    drop what is no longer validated or classified since a saved arrangement was made.
    """
    return [
        a
        for a in activities
        if a.status is ActivityStatus.VALIDADA
        and a.group_number is not None
        and a.item_number is not None
    ]


def eligible_activities(
    activities: Sequence[Activity], validity: Mapping[UUID, Validity]
) -> list[Activity]:
    """The activities that go in the documents: validated, with group and item, and valid.

    An activity outside the interstice, a duplicate, a rejected one or one below the minimum
    hours is not valid and stays out of the Tabela, the Relatório and the Comprovante (SEG-01);
    one the validity does not know is left out too.
    """
    eligible = []
    for activity in validated_activities(activities):
        found = validity.get(activity.id)
        if found is not None and found.is_valid and not found.needs_category:
            eligible.append(activity)
    return eligible


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
