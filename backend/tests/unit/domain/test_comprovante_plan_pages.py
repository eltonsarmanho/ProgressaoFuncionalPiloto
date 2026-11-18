"""CMP-01, CMP-02, CMP-04: pages, numbering and table of contents of the Comprovante plan."""

import math
from dataclasses import replace
from uuid import uuid4

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    LayoutActivity,
    LayoutPage,
    PageKind,
    TocLevel,
)
from app.domain.rules.comprovante_plan import derive_layout, plan_comprovante
from tests.unit.domain.comprovante_support import PROCESS_ID, link, make_activity

DOC_A, DOC_B, DOC_C = uuid4(), uuid4(), uuid4()


def scenario():
    """3 groups, 4 items and 5 activities, in table order."""
    a1 = make_activity(1, 1, title="Disciplina de graduação")
    a2 = make_activity(1, 1, title="Outra disciplina")
    a3 = make_activity(2, 3, title="Orientação de iniciação")
    a4 = make_activity(2, 7, title="Orientação de TCC")
    a5 = make_activity(3, 2, title="Banca de concurso")
    activities = [a1, a2, a3, a4, a5]
    links = [
        link(a1, DOC_A, 1), link(a1, DOC_A, 2), link(a2, DOC_A, 5), link(a3, DOC_B, 1),
        link(a4, DOC_B, 4), link(a4, DOC_C, 2), link(a5, DOC_C, 7),
    ]  # fmt: skip
    return activities, links


def plan_of(activities, links, capacity=8):
    layout = derive_layout(PROCESS_ID, activities, links)
    return plan_comprovante(layout, activities, capacity)


def by_kind(plan, kind):
    return [p for p in plan.pages if p.kind is kind]


def test_the_cover_is_page_one_and_the_table_of_contents_follows():
    activities, links = scenario()

    plan = plan_of(activities, links)

    assert [(p.kind, p.number) for p in plan.pages[:4]] == [
        (PageKind.CAPA, 1),
        (PageKind.SUMARIO, 2),
        (PageKind.SUMARIO, 3),
        (PageKind.SUMARIO, 4),
    ]


@pytest.mark.parametrize("capacity", [17, 16, 8, 5, 1])
def test_the_table_of_contents_takes_ceil_of_its_lines_over_the_capacity(capacity):
    activities, links = scenario()
    lines = 3 + 4 + 2 * 5  # groups, items, two lines per activity

    plan = plan_of(activities, links, capacity)

    assert len(by_kind(plan, PageKind.SUMARIO)) == math.ceil(lines / capacity)


def test_there_is_one_separator_per_group_with_an_activity_before_its_originals():
    activities, links = scenario()

    plan = plan_of(activities, links)

    separators = by_kind(plan, PageKind.SEPARADOR)
    assert [(p.group_number, p.number) for p in separators] == [(1, 5), (2, 9), (3, 13)]
    assert plan.pages[4].kind is PageKind.SEPARADOR
    assert plan.pages[5].kind is PageKind.ORIGINAL


def test_originals_follow_the_order_of_the_arrangement_and_are_numbered_in_sequence():
    activities, links = scenario()

    plan = plan_of(activities, links)

    originals = by_kind(plan, PageKind.ORIGINAL)
    assert [(p.number, p.document_id, p.source_page) for p in originals] == [
        (6, DOC_A, 1), (7, DOC_A, 2), (8, DOC_A, 5), (10, DOC_B, 1),
        (11, DOC_B, 4), (12, DOC_C, 2), (14, DOC_C, 7),
    ]  # fmt: skip
    assert [p.group_number for p in originals] == [1, 1, 1, 2, 2, 2, 3]


def test_the_numbers_run_from_the_cover_without_a_gap():
    activities, links = scenario()

    plan = plan_of(activities, links)

    assert [p.number for p in plan.pages] == list(range(1, 15))


def test_the_arrangement_order_wins_over_the_links():
    a = make_activity(2, 7)
    layout = ComprovanteLayout(
        PROCESS_ID, (LayoutActivity(a.id, (LayoutPage(DOC_B, 9), LayoutPage(DOC_A, 1))),)
    )

    plan = plan_comprovante(layout, [a], 8)

    assert [(p.document_id, p.source_page) for p in by_kind(plan, PageKind.ORIGINAL)] == [
        (DOC_B, 9),
        (DOC_A, 1),
    ]


def test_the_group_entry_has_the_page_of_its_separator():
    activities, links = scenario()

    plan = plan_of(activities, links)

    groups = [e for e in plan.toc if e.level is TocLevel.GRUPO]
    assert [(e.group_number, e.first_page) for e in groups] == [(1, 5), (2, 9), (3, 13)]


def test_the_item_entry_has_the_first_page_of_its_first_original():
    activities, links = scenario()

    plan = plan_of(activities, links)

    items = [e for e in plan.toc if e.level is TocLevel.ITEM]
    assert [(e.group_number, e.item_number, e.first_page) for e in items] == [
        (1, 1, 6), (2, 3, 10), (2, 7, 11), (3, 2, 14),
    ]  # fmt: skip


def test_the_activity_entry_has_origin_pages_and_the_range_in_the_comprovante():
    activities, links = scenario()

    plan = plan_of(activities, links)

    entries = [e for e in plan.toc if e.level is TocLevel.ATIVIDADE]
    first, last_two = entries[0], entries[3]
    assert (first.activity_id, first.title) == (activities[0].id, "Disciplina de graduação")
    assert [(s.document_id, s.source_page, s.comprovante_page) for s in first.sources] == [
        (DOC_A, 1, 6),
        (DOC_A, 2, 7),
    ]
    assert (first.first_page, first.last_page) == (6, 7)
    assert [(s.document_id, s.source_page) for s in last_two.sources] == [
        (DOC_B, 4),
        (DOC_C, 2),
    ]
    assert (last_two.first_page, last_two.last_page) == (11, 12)


def test_the_toc_lists_each_group_then_its_items_then_their_activities():
    activities, links = scenario()

    plan = plan_of(activities, links)

    assert [(e.level.value, e.group_number, e.item_number) for e in plan.toc] == [
        ("GRUPO", 1, None), ("ITEM", 1, 1), ("ATIVIDADE", 1, 1), ("ATIVIDADE", 1, 1),
        ("GRUPO", 2, None), ("ITEM", 2, 3), ("ATIVIDADE", 2, 3),
        ("ITEM", 2, 7), ("ATIVIDADE", 2, 7),
        ("GRUPO", 3, None), ("ITEM", 3, 2), ("ATIVIDADE", 3, 2),
    ]  # fmt: skip


def test_a_group_without_an_activity_has_no_separator_and_no_entry():
    a1, a3 = make_activity(1, 1), make_activity(3, 2)

    plan = plan_of([a1, a3], [link(a1, DOC_A, 1), link(a3, DOC_B, 1)])

    assert [p.group_number for p in by_kind(plan, PageKind.SEPARADOR)] == [1, 3]
    assert [e.group_number for e in plan.toc if e.level is TocLevel.GRUPO] == [1, 3]


def test_a_group_whose_activities_have_no_page_still_has_a_separator():
    a = make_activity(2, 7)

    plan = plan_of([a], [])

    assert [p.group_number for p in by_kind(plan, PageKind.SEPARADOR)] == [2]
    assert by_kind(plan, PageKind.ORIGINAL) == []


def test_an_activity_without_pages_has_no_range_and_leaves_the_numbers_alone():
    first, bare, last = make_activity(2, 7), make_activity(2, 7), make_activity(2, 7)
    links = [link(first, DOC_A, 1), link(last, DOC_A, 2)]

    plan = plan_of([first, bare, last], links)

    entries = [e for e in plan.toc if e.level is TocLevel.ATIVIDADE]
    assert [(e.first_page, e.last_page) for e in entries] == [(4, 4), (None, None), (5, 5)]
    assert bare.id == entries[1].activity_id


def test_an_item_without_any_page_has_no_first_page():
    a = make_activity(2, 7)

    plan = plan_of([a], [])

    assert [e.first_page for e in plan.toc if e.level is TocLevel.ITEM] == [None]


def test_only_current_validated_activities_enter_the_plan():
    kept = make_activity(2, 7)
    rejected = make_activity(2, 7)
    layout = derive_layout(PROCESS_ID, [kept, rejected], [link(kept, DOC_A, 1)])
    rejected_now = replace(rejected, status=ActivityStatus.REJEITADA)

    plan = plan_comprovante(layout, [kept, rejected_now], 8)

    assert [e.activity_id for e in plan.toc if e.level is TocLevel.ATIVIDADE] == [kept.id]


def test_an_activity_in_the_layout_that_changed_item_is_planned_in_its_current_item():
    moved = make_activity(2, 3)
    layout = ComprovanteLayout(
        PROCESS_ID, (LayoutActivity(moved.id, (LayoutPage(DOC_A, 1),), 2, 7),)
    )

    plan = plan_comprovante(layout, [moved], 8)

    assert [(e.group_number, e.item_number) for e in plan.toc if e.level is TocLevel.ITEM] == [
        (2, 3)
    ]


def test_inside_an_item_the_order_of_the_layout_wins_over_the_dates():
    early = make_activity(2, 7)
    late = make_activity(2, 7)
    layout = ComprovanteLayout(
        PROCESS_ID,
        (
            LayoutActivity(late.id, (LayoutPage(DOC_A, 1),), 2, 7),
            LayoutActivity(early.id, (LayoutPage(DOC_B, 1),), 2, 7),
        ),
    )

    plan = plan_comprovante(layout, [early, late], 8)

    assert [e.activity_id for e in plan.toc if e.level is TocLevel.ATIVIDADE] == [
        late.id,
        early.id,
    ]


def test_an_activity_missing_from_the_layout_goes_after_the_arranged_ones_of_its_item():
    arranged = make_activity(2, 7)
    newcomer = make_activity(2, 7, event_date=None)
    layout = ComprovanteLayout(
        PROCESS_ID, (LayoutActivity(arranged.id, (LayoutPage(DOC_A, 1),), 2, 7),)
    )

    plan = plan_comprovante(layout, [newcomer, arranged], 8)

    assert [e.activity_id for e in plan.toc if e.level is TocLevel.ATIVIDADE] == [
        arranged.id,
        newcomer.id,
    ]


def test_a_plan_without_activities_is_just_the_cover():
    plan = plan_comprovante(ComprovanteLayout(PROCESS_ID, ()), [], 8)

    assert [(p.kind, p.number) for p in plan.pages] == [(PageKind.CAPA, 1)]
    assert plan.toc == ()
