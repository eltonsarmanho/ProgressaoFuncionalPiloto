"""SEG-01, SEG-02, SEG-03: which activities go in the documents, and in which order."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.rules.activity_order import eligible_activities, table_order
from app.domain.rules.activity_validity import InvalidReason, Validity, ValidityState

VALID = Validity(ValidityState.VALIDA)
NOT_VALID = Validity(ValidityState.NAO_VALIDA, InvalidReason.FORA_DO_INTERSTICIO)
NEEDS_CATEGORY = Validity(ValidityState.VALIDA, needs_category=True)


def act(group=2, item=7, status=ActivityStatus.VALIDADA, **kwargs) -> Activity:
    defaults = {
        "title": "Atividade",
        "event_date": date(2025, 1, 1),
        "created_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=group,
        item_number=item, status=status, **defaults,
    )  # fmt: skip


def test_a_validated_valid_activity_with_group_and_item_enters():
    a = act()

    assert eligible_activities([a], {a.id: VALID}) == [a]


def test_a_validated_activity_that_is_not_valid_does_not_enter():
    a = act()

    assert eligible_activities([a], {a.id: NOT_VALID}) == []


def test_an_activity_awaiting_review_does_not_enter_even_if_valid():
    a = act(status=ActivityStatus.AGUARDANDO_REVISAO)

    assert eligible_activities([a], {a.id: VALID}) == []


def test_a_rejected_activity_does_not_enter():
    a = act(status=ActivityStatus.REJEITADA)

    assert eligible_activities([a], {a.id: VALID}) == []


def test_an_activity_without_category_does_not_enter():
    no_group = act(group=None, item=None)
    no_item = act(item=None)
    unlisted = act()

    found = eligible_activities(
        [no_group, no_item, unlisted],
        {no_group.id: NEEDS_CATEGORY, no_item.id: NEEDS_CATEGORY, unlisted.id: NEEDS_CATEGORY},
    )

    assert found == []


def test_an_activity_with_no_validity_entry_does_not_enter():
    assert eligible_activities([act()], {}) == []


def test_only_the_valid_ones_of_a_mixed_list_enter_and_keep_the_given_order():
    first, out, last = act(title="A"), act(title="B"), act(title="C")
    validity = {first.id: VALID, out.id: NOT_VALID, last.id: VALID}

    assert eligible_activities([first, out, last], validity) == [first, last]


def test_table_order_is_group_item_then_date_undated_last_then_creation():
    late = act(group=2, item=7, event_date=date(2025, 6, 1))
    early = act(group=2, item=7, event_date=date(2025, 1, 1))
    undated = act(group=2, item=7, event_date=None)
    other_item = act(group=2, item=3, event_date=date(2025, 12, 1))
    other_group = act(group=1, item=9)

    ordered = sorted([late, undated, other_group, early, other_item], key=table_order)

    assert ordered == [other_group, other_item, early, late, undated]
