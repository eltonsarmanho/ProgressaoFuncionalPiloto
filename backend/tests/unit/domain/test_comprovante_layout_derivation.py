"""ARR-01, ARR-05: the layout derived from the activity-page links when none was saved."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import EvidenceKey, LayoutPage
from app.domain.rules.comprovante_plan import derive_layout
from tests.unit.domain.comprovante_support import PROCESS_ID, link, make_activity

DOC_A, DOC_B = uuid4(), uuid4()


def ids(layout):
    return [a.activity_id for a in layout.activities]


def test_without_a_saved_layout_activities_come_by_group_item_and_date():
    late = make_activity(2, 7, event_date=date(2023, 9, 1))
    early = make_activity(2, 7, event_date=date(2023, 2, 1))
    other_item = make_activity(2, 3, event_date=date(2023, 12, 1))
    other_group = make_activity(1, 9, event_date=date(2024, 1, 1))

    layout = derive_layout(PROCESS_ID, [late, other_group, early, other_item], [])

    assert ids(layout) == [other_group.id, other_item.id, early.id, late.id]


def test_the_pages_of_an_activity_follow_the_order_of_its_links():
    a = make_activity(2, 7)
    links = [link(a, DOC_B, 4), link(a, DOC_A, 9), link(a, DOC_A, 2)]

    layout = derive_layout(PROCESS_ID, [a], links)

    assert layout.activities[0].pages == (
        LayoutPage(DOC_B, 4),
        LayoutPage(DOC_A, 9),
        LayoutPage(DOC_A, 2),
    )


def test_two_activities_with_the_same_title_in_one_item_appear_each_with_its_pages():
    one = make_activity(3, 2, title="Banca de TCC")
    two = make_activity(3, 2, title="Banca de TCC")
    links = [link(one, DOC_A, 1), link(two, DOC_A, 5), link(two, DOC_B, 1)]

    layout = derive_layout(PROCESS_ID, [one, two], links)

    assert [(a.activity_id, [p.page for p in a.pages]) for a in layout.activities] == [
        (one.id, [1]),
        (two.id, [5, 1]),
    ]


def test_an_activity_without_links_is_in_the_layout_with_no_pages():
    a = make_activity(4, 4)

    layout = derive_layout(PROCESS_ID, [a], [])

    assert [(x.activity_id, x.pages) for x in layout.activities] == [(a.id, ())]


def test_only_validated_activities_with_group_and_item_are_arranged():
    kept = make_activity(2, 7)
    waiting = make_activity(2, 7, status=ActivityStatus.AGUARDANDO_REVISAO)
    rejected = make_activity(2, 7, status=ActivityStatus.REJEITADA)
    no_item = make_activity(2, 7, item_number=None)
    no_group = make_activity(2, 7, group_number=None)

    layout = derive_layout(PROCESS_ID, [waiting, rejected, no_item, kept, no_group], [])

    assert ids(layout) == [kept.id]


def test_the_links_of_activities_left_out_are_ignored():
    kept = make_activity(2, 7)
    rejected = make_activity(2, 7, status=ActivityStatus.REJEITADA)

    layout = derive_layout(PROCESS_ID, [kept, rejected], [link(rejected, DOC_A, 1)])

    assert layout.activities[0].pages == ()
    assert layout.base_evidence_keys == ()


def test_the_derived_layout_is_version_zero_and_belongs_to_the_process():
    layout = derive_layout(PROCESS_ID, [make_activity(2, 7)], [])

    assert (layout.version, layout.process_id) == (0, PROCESS_ID)


def test_the_base_keys_are_the_links_the_layout_was_built_from():
    a, b = make_activity(2, 7), make_activity(3, 2)
    links = [link(a, DOC_A, 1), link(b, DOC_B, 3)]

    layout = derive_layout(PROCESS_ID, [a, b], links)

    assert set(layout.base_evidence_keys) == {
        EvidenceKey(a.id, DOC_A, 1),
        EvidenceKey(b.id, DOC_B, 3),
    }


def test_each_layout_activity_remembers_the_item_of_the_scoring():
    a = make_activity(4, 5)

    layout = derive_layout(PROCESS_ID, [a], [])

    assert (layout.activities[0].group_number, layout.activities[0].item_number) == (4, 5)


def test_an_undated_activity_goes_after_the_dated_ones_of_its_item():
    undated = make_activity(2, 7, event_date=None)
    dated = make_activity(2, 7, event_date=date(2023, 3, 1))

    layout = derive_layout(PROCESS_ID, [undated, dated], [])

    assert ids(layout) == [dated.id, undated.id]


def test_the_period_start_orders_an_activity_without_an_event_date():
    by_period = make_activity(2, 7, event_date=None, period_start=date(2023, 1, 10))
    by_event = make_activity(2, 7, event_date=date(2023, 5, 1))

    layout = derive_layout(PROCESS_ID, [by_event, by_period], [])

    assert ids(layout) == [by_period.id, by_event.id]


def test_activities_on_the_same_day_keep_the_order_they_were_created():
    first = make_activity(2, 7, created_at=datetime(2025, 1, 1, tzinfo=UTC))
    second = make_activity(2, 7, created_at=datetime(2025, 1, 2, tzinfo=UTC))

    layout = derive_layout(PROCESS_ID, [second, first], [])

    assert ids(layout) == [first.id, second.id]
