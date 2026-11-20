"""SEG-04: near identical titles of the same item and date are one activity counted twice."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.scoring_duplicates import find_duplicates

SHARED = "curso de formacao continuada em dados abertos e governo digital para servidores"
LONGER = SHARED + " publicos"  # 12 shared words of 13: Jaccard 0.92
DAY = date(2025, 5, 10)


def activity(title, created=1, item=(7, 10), **kwargs) -> Activity:
    kwargs.setdefault("event_date", DAY)
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        title=title,
        created_by=uuid4(),
        group_number=item[0],
        item_number=item[1],
        created_at=datetime(2025, 6, created, tzinfo=UTC),
        **kwargs,
    )


def test_two_titles_with_jaccard_above_the_limit_make_the_newer_a_duplicate():
    older, newer = activity(SHARED), activity(LONGER, created=2)
    assert find_duplicates([older, newer]) == {newer.id}


def test_the_order_of_creation_decides_not_the_order_of_the_list():
    older, newer = activity(SHARED), activity(LONGER, created=2)
    assert find_duplicates([newer, older]) == {newer.id}


def test_a_jaccard_of_exactly_point_eight_is_a_duplicate():
    # 8 shared words, 1 extra each: 8 / 10
    base = "a b c d e f g h"
    older, newer = activity(base + " x"), activity(base + " y", created=2)
    assert find_duplicates([older, newer]) == {newer.id}


def test_a_jaccard_below_point_eight_is_not_a_duplicate():
    # 15 shared words, 2 extra each: 15 / 19 = 0.789
    base = " ".join(f"w{n}" for n in range(15))
    older, newer = activity(base + " x1 x2"), activity(base + " y1 y2", created=2)
    assert find_duplicates([older, newer]) == set()


def test_similar_titles_of_another_item_stay_apart():
    older, newer = activity(SHARED), activity(LONGER, created=2, item=(7, 9))
    assert find_duplicates([older, newer]) == set()


def test_similar_titles_on_disjoint_dates_stay_apart():
    older = activity(SHARED)
    newer = activity(LONGER, created=2, event_date=date(2025, 8, 1))
    assert find_duplicates([older, newer]) == set()


def test_similar_titles_without_a_date_stay_apart():
    older, newer = activity(SHARED, event_date=None), activity(LONGER, created=2, event_date=None)
    assert find_duplicates([older, newer]) == set()


def test_a_justification_releases_the_similar_activity():
    older = activity(SHARED)
    newer = activity(LONGER, created=2, distinct_justification="Outra turma")
    assert find_duplicates([older, newer]) == set()


def test_a_rejected_activity_does_not_take_part():
    older = activity(SHARED, status=ActivityStatus.REJEITADA)
    assert find_duplicates([older, activity(LONGER, created=2)]) == set()


def test_different_titles_of_the_same_item_and_date_are_not_duplicates():
    first = activity("Banca de mestrado de Maria Silva")
    second = activity("Banca de mestrado de Joao Silva", created=2)
    assert find_duplicates([first, second]) == set()
