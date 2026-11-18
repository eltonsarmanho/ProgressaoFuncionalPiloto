"""Duplicate activity detection (VERIF-05..VERIF-07, SEG-04).

Overlapping inclusive date ranges and the same normalized title, or, for the same item, titles
whose sets of words are alike (Jaccard of 0.8 or more): the activity created later is reported
as a duplicate, unless it carries a justification that it is distinct. The AI writes the title
of a repeated certificate differently each time, so an exact comparison alone misses it.
Activities without dates never duplicate; rejected ones do not take part.
"""

import re
from collections.abc import Iterable
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.scoring_periods import activity_interval, normalize_title

SIMILAR_TITLE_JACCARD = 0.8


def _creation_order(activity: Activity):
    return (activity.created_at is not None, activity.created_at, str(activity.id))


def _words(title: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", normalize_title(title)))


def _similar(one: frozenset[str], two: frozenset[str]) -> bool:
    union = one | two
    return bool(union) and len(one & two) / len(union) >= SIMILAR_TITLE_JACCARD


def _same_item(one: Activity, two: Activity) -> bool:
    item = (one.group_number, one.item_number)
    return None not in item and item == (two.group_number, two.item_number)


def find_duplicates(activities: Iterable[Activity]) -> set[UUID]:
    dated = [
        a
        for a in activities
        if a.status is not ActivityStatus.REJEITADA and activity_interval(a) is not None
    ]
    ordered = sorted(dated, key=_creation_order)
    titles = {a.id: normalize_title(a.title) for a in ordered}
    words = {a.id: _words(a.title) for a in ordered}

    duplicates: set[UUID] = set()
    for index, later in enumerate(ordered):
        if (later.distinct_justification or "").strip():
            continue
        start, end = activity_interval(later)
        for earlier in ordered[:index]:
            other_start, other_end = activity_interval(earlier)
            if not (other_start <= end and start <= other_end):
                continue
            same_title = titles[earlier.id] == titles[later.id]
            if same_title or (
                _same_item(earlier, later) and _similar(words[earlier.id], words[later.id])
            ):
                duplicates.add(later.id)
                break
    return duplicates
