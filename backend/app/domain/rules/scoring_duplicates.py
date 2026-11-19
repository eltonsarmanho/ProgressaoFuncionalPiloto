"""Duplicate activity detection (VERIF-05..VERIF-07, SEG-04).

Overlapping inclusive date ranges and the same normalized title, or, for the same item, titles
whose sets of words are alike (Jaccard of 0.8 or more) and do not differ by a proper name (the
name of a student or of a board member makes another activity, TER-08): the activity created
later is reported as a duplicate, unless it carries a justification that it is distinct. The AI
writes the title of a repeated certificate differently each time, so an exact comparison alone
misses it.
Two activities of the same item and overlapping dates that come from two different documents
with the same text (the same certificate saved as two files) are duplicates as well (SEG-05).
Activities without dates never duplicate; rejected ones do not take part.
"""

import hashlib
from collections.abc import Iterable, Mapping, Sequence, Set
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.scoring_periods import activity_interval, normalize_title
from app.domain.rules.title_similarity import similar_titles

MIN_READABLE_CHARS = 50  # below this the text says nothing: two unreadable files look alike

ContentKey = tuple[UUID, str]  # (document id, hash of its normalized text)


def has_readable_text(pages: Sequence[str]) -> bool:
    """Whether the normalized text has at least 50 characters (TER-09).

    A document whose pages are empty or almost empty (the OCR found nothing) is never "the same
    text" as another one, so it gets no content hash.
    """
    return sum(len(normalize_title(page)) for page in pages) >= MIN_READABLE_CHARS


def content_hash(pages: Sequence[str]) -> str:
    """SHA-256 of the page texts, normalized (case, accents, spacing), in page order."""
    normalized = "\n".join(normalize_title(page) for page in pages)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _shares_content(one: Set[ContentKey], two: Set[ContentKey]) -> bool:
    """Same text in a different document."""
    return any(
        text == other_text and document != other_document
        for document, text in one
        for other_document, other_text in two
    )


def _creation_order(activity: Activity):
    return (activity.created_at is not None, activity.created_at, str(activity.id))


def _same_item(one: Activity, two: Activity) -> bool:
    item = (one.group_number, one.item_number)
    return None not in item and item == (two.group_number, two.item_number)


def duplicate_pairs(
    activities: Iterable[Activity], contents: Mapping[UUID, Set[ContentKey]] | None = None
) -> list[tuple[UUID, UUID]]:
    """`(duplicate, original)` for each duplicate, in creation order of the duplicate.

    The original is the first earlier activity that matches it. `contents` maps an activity id
    to the (document, text hash) pairs of its evidences.
    """
    contents = contents or {}
    dated = [
        a
        for a in activities
        if a.status is not ActivityStatus.REJEITADA and activity_interval(a) is not None
    ]
    ordered = sorted(dated, key=_creation_order)
    titles = {a.id: normalize_title(a.title) for a in ordered}

    pairs: list[tuple[UUID, UUID]] = []
    for index, later in enumerate(ordered):
        if (later.distinct_justification or "").strip():
            continue
        start, end = activity_interval(later)
        for earlier in ordered[:index]:
            other_start, other_end = activity_interval(earlier)
            if not (other_start <= end and start <= other_end):
                continue
            same_title = titles[earlier.id] == titles[later.id]
            same_item = _same_item(earlier, later)
            if (
                same_title
                or (same_item and similar_titles(earlier.title, later.title))
                or (
                    same_item
                    and _shares_content(contents.get(earlier.id, ()), contents.get(later.id, ()))
                )
            ):
                pairs.append((later.id, earlier.id))
                break
    return pairs


def find_duplicates(
    activities: Iterable[Activity], contents: Mapping[UUID, Set[ContentKey]] | None = None
) -> set[UUID]:
    """`contents` maps an activity id to the (document, text hash) pairs of its evidences."""
    return {duplicate for duplicate, _ in duplicate_pairs(activities, contents)}


def duplicate_groups(
    activities: Iterable[Activity], contents: Mapping[UUID, Set[ContentKey]] | None = None
) -> list[tuple[Activity, ...]]:
    """The activities that are duplicates of one another, a chain A~B, B~C in one group (DUP-01).

    Each group lists its activities in creation order, and the groups come ordered by the
    creation of their first activity.
    """
    activities = list(activities)
    pairs = duplicate_pairs(activities, contents)
    parent = {a.id: a.id for a in activities}

    def root(activity_id: UUID) -> UUID:
        while parent[activity_id] != activity_id:
            parent[activity_id] = parent[parent[activity_id]]
            activity_id = parent[activity_id]
        return activity_id

    for duplicate, original in pairs:
        parent[root(duplicate)] = root(original)

    members = {activity_id for pair in pairs for activity_id in pair}
    grouped: dict[UUID, list[Activity]] = {}
    for activity in sorted(activities, key=_creation_order):
        if activity.id in members:
            grouped.setdefault(root(activity.id), []).append(activity)
    return sorted((tuple(group) for group in grouped.values()), key=lambda g: _creation_order(g[0]))
