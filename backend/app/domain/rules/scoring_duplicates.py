"""Duplicate activity detection (VERIF-05..VERIF-07).

Same normalized title and overlapping inclusive date ranges: the activity created later is
reported as a duplicate, unless it carries a justification that it is distinct. Activities
without dates never duplicate; rejected ones do not take part.
"""

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.scoring_periods import activity_interval, normalize_title


def _creation_order(activity: Activity):
    return (activity.created_at is not None, activity.created_at, str(activity.id))


def find_duplicates(activities: Iterable[Activity]) -> set[UUID]:
    by_title: dict[str, list[Activity]] = defaultdict(list)
    for activity in activities:
        if activity.status is ActivityStatus.REJEITADA:
            continue
        if activity_interval(activity) is None:
            continue
        by_title[normalize_title(activity.title)].append(activity)

    duplicates: set[UUID] = set()
    for group in by_title.values():
        ordered = sorted(group, key=_creation_order)
        for index, later in enumerate(ordered):
            if (later.distinct_justification or "").strip():
                continue
            start, end = activity_interval(later)
            for earlier in ordered[:index]:
                other_start, other_end = activity_interval(earlier)
                if other_start <= end and start <= other_end:
                    duplicates.add(later.id)
                    break
    return duplicates
