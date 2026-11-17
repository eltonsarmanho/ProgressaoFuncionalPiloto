"""VERIF-05, VERIF-06, VERIF-07: duplicate detection."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus, PeriodPrecision
from app.domain.rules.scoring_duplicates import find_duplicates


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
