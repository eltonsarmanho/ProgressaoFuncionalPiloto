"""VERIF-05, VERIF-06, VERIF-07: duplicate detection."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity, ActivityStatus, PeriodPrecision
from app.domain.rules.scoring_duplicates import duplicate_groups, duplicate_pairs, find_duplicates


def _activity(title="Comissão de Avaliação", created=1, **kwargs) -> Activity:
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        title=title,
        created_by=uuid4(),
        created_at=datetime(2025, 1, created, tzinfo=UTC),
        **kwargs,
    )


def _period(start, end, **kwargs):
    return {"period_start": start, "period_end": end, **kwargs}


def test_same_title_and_overlapping_periods_excludes_the_newer_activity():
    older = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    newer = _activity(created=2, **_period(date(2023, 5, 1), date(2023, 12, 31)))

    assert find_duplicates([newer, older]) == {newer.id}


def test_distinct_justification_releases_the_newer_activity():
    older = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    newer = _activity(
        created=2,
        distinct_justification="Outra comissão, mesmo nome",
        **_period(date(2023, 5, 1), date(2023, 12, 31)),
    )

    assert find_duplicates([older, newer]) == set()


def test_member_and_president_of_the_same_commission_are_a_duplicate():
    member = _activity(
        "Comissão de Avaliação - membro",
        created=1,
        group_number=6,
        item_number=6,
        **_period(date(2023, 1, 1), date(2023, 12, 31)),
    )
    president = _activity(
        "comissão  de avaliação - MEMBRO",
        created=2,
        group_number=6,
        item_number=7,
        **_period(date(2023, 3, 1), date(2023, 9, 30)),
    )

    assert find_duplicates([member, president]) == {president.id}


def test_same_title_without_dates_is_never_a_duplicate():
    assert find_duplicates([_activity(created=1), _activity(created=2)]) == set()


def test_one_dated_and_one_undated_activity_are_not_duplicates():
    dated = _activity(created=1, event_date=date(2023, 3, 1))

    assert find_duplicates([dated, _activity(created=2)]) == set()


def test_same_title_in_separate_periods_is_not_a_duplicate():
    first = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    second = _activity(created=2, **_period(date(2023, 7, 1), date(2023, 12, 31)))

    assert find_duplicates([first, second]) == set()


def test_periods_touching_on_a_single_day_overlap():
    first = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    second = _activity(created=2, **_period(date(2023, 6, 30), date(2023, 12, 31)))

    assert find_duplicates([first, second]) == {second.id}


def test_same_event_date_is_a_duplicate():
    first = _activity("Palestra", created=1, event_date=date(2023, 5, 10))
    second = _activity("PALESTRA", created=2, event_date=date(2023, 5, 10))

    assert find_duplicates([first, second]) == {second.id}


def test_different_titles_are_not_duplicates():
    first = _activity("Palestra A", created=1, event_date=date(2023, 5, 10))
    second = _activity("Palestra B", created=2, event_date=date(2023, 5, 10))

    assert find_duplicates([first, second]) == set()


def test_rejected_activity_does_not_take_part():
    rejected = _activity(
        created=1, status=ActivityStatus.REJEITADA, **_period(date(2023, 1, 1), date(2023, 6, 30))
    )
    other = _activity(created=2, **_period(date(2023, 2, 1), date(2023, 3, 1)))

    assert find_duplicates([rejected, other]) == set()


def test_month_precision_periods_overlap_by_whole_month():
    first = _activity(
        "Curso",
        created=1,
        period_precision=PeriodPrecision.MONTH,
        **_period(date(2023, 5, 1), date(2023, 5, 1)),
    )
    second = _activity("Curso", created=2, event_date=date(2023, 5, 31))

    assert find_duplicates([first, second]) == {second.id}


def test_creation_time_tie_is_broken_by_id():
    a = _activity(created=1, event_date=date(2023, 5, 10))
    b = _activity(created=1, event_date=date(2023, 5, 10))
    expected_newer = max(a, b, key=lambda x: str(x.id))

    assert find_duplicates([a, b]) == {expected_newer.id}


# DUP-01: the pairs and the groups of the merge follow the rule of find_duplicates.


def _chain():
    """A touches B on 31/03 and B touches C on 30/06, but A and C are apart: A~B, B~C."""
    a = _activity("Orientação", created=1, **_period(date(2023, 1, 1), date(2023, 3, 31)))
    b = _activity("Orientação", created=2, **_period(date(2023, 3, 31), date(2023, 6, 30)))
    c = _activity("Orientação", created=3, **_period(date(2023, 6, 30), date(2023, 9, 30)))
    return a, b, c


def _scenarios():
    older = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    newer = _activity(created=2, **_period(date(2023, 5, 1), date(2023, 12, 31)))
    released = _activity(
        created=2,
        distinct_justification="Outra comissão",
        **_period(date(2023, 5, 1), date(2023, 12, 31)),
    )
    rejected = _activity(
        created=1, status=ActivityStatus.REJEITADA, **_period(date(2023, 1, 1), date(2023, 6, 30))
    )
    same_day_a = _activity("Palestra", created=1, event_date=date(2023, 5, 10))
    same_day_b = _activity("PALESTRA", created=2, event_date=date(2023, 5, 10))
    undated = [_activity(created=1), _activity(created=2)]
    return {
        "overlap": [newer, older],
        "justified": [older, released],
        "rejected": [rejected, newer],
        "same_day": [same_day_b, same_day_a],
        "undated": undated,
        "chain": list(_chain()),
        "none": [],
    }


@pytest.mark.parametrize("name", list(_scenarios()))
def test_the_duplicates_of_the_pairs_are_the_same_as_find_duplicates(name):
    activities = _scenarios()[name]

    assert {duplicate for duplicate, _ in duplicate_pairs(activities)} == find_duplicates(
        activities
    )


def test_a_pair_is_the_duplicate_then_the_original():
    older = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    newer = _activity(created=2, **_period(date(2023, 5, 1), date(2023, 12, 31)))

    assert duplicate_pairs([newer, older]) == [(newer.id, older.id)]


def test_a_chain_of_three_makes_one_group_of_three_in_creation_order():
    a, b, c = _chain()

    assert duplicate_pairs([c, a, b]) == [(b.id, a.id), (c.id, b.id)]
    groups = duplicate_groups([c, a, b])
    assert [[x.id for x in group] for group in groups] == [[a.id, b.id, c.id]]


def test_activities_with_a_distinct_justification_form_no_pair_and_no_group():
    older = _activity(created=1, **_period(date(2023, 1, 1), date(2023, 6, 30)))
    released = _activity(
        created=2,
        distinct_justification="Outra comissão, mesmo nome",
        **_period(date(2023, 5, 1), date(2023, 12, 31)),
    )

    assert duplicate_pairs([older, released]) == []
    assert duplicate_groups([older, released]) == []


def test_groups_come_ordered_by_the_creation_of_their_first_activity():
    late_a = _activity("Palestra", created=5, event_date=date(2023, 5, 10))
    late_b = _activity("Palestra", created=6, event_date=date(2023, 5, 10))
    early_a = _activity("Curso", created=1, event_date=date(2023, 7, 1))
    early_b = _activity("Curso", created=2, event_date=date(2023, 7, 1))
    alone = _activity("Sozinha", created=3, event_date=date(2023, 8, 1))

    groups = duplicate_groups([late_b, alone, early_b, late_a, early_a])

    assert [[x.id for x in group] for group in groups] == [
        [early_a.id, early_b.id],
        [late_a.id, late_b.id],
    ]


def test_two_unrelated_pairs_stay_in_two_groups():
    pairs = {"x": ("Palestra", date(2023, 5, 10)), "y": ("Curso", date(2023, 7, 1))}
    made = {
        k: (_activity(t, created=1, event_date=d), _activity(t, created=2, event_date=d))
        for k, (t, d) in pairs.items()
    }

    groups = duplicate_groups([a for pair in made.values() for a in pair])

    assert sorted(len(g) for g in groups) == [2, 2]
