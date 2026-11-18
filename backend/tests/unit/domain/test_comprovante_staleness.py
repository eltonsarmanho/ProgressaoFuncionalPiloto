"""ARR-08: a saved layout out of date with the current activities, and what generation uses."""

from dataclasses import replace
from uuid import uuid4

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import ComprovanteLayout, LayoutActivity, LayoutPage
from app.domain.rules.comprovante_plan import (
    current_layout,
    derive_layout,
    invalid_entries,
    layout_staleness,
)
from tests.unit.domain.comprovante_support import PROCESS_ID, link, make_activity, source

DOC_A, DOC_B = uuid4(), uuid4()


def saved_case():
    """A layout saved from two activities, each with one page."""
    first, second = make_activity(2, 7), make_activity(3, 2)
    links = [link(first, DOC_A, 1), link(second, DOC_B, 4)]
    return first, second, links, derive_layout(PROCESS_ID, [first, second], links)


# --- stale (ARR-08) -------------------------------------------------------------------------


def test_a_layout_equal_to_the_current_activities_is_not_stale():
    first, second, links, layout = saved_case()

    staleness = layout_staleness(layout, [first, second], links)

    assert staleness.is_stale is False


def test_an_activity_rejected_after_the_layout_makes_it_stale():
    first, second, links, layout = saved_case()
    rejected = replace(first, status=ActivityStatus.REJEITADA)

    staleness = layout_staleness(layout, [rejected, second], links)

    assert staleness.is_stale is True
    assert staleness.left_activity_ids == (first.id,)


def test_an_activity_that_is_no_longer_validated_has_left_the_layout():
    first, second, links, layout = saved_case()
    waiting = replace(second, status=ActivityStatus.AGUARDANDO_REVISAO)

    staleness = layout_staleness(layout, [first, waiting], links)

    assert staleness.left_activity_ids == (second.id,)


def test_an_activity_that_was_deleted_has_left_the_layout():
    first, second, links, layout = saved_case()

    staleness = layout_staleness(layout, [second], links[1:])

    assert staleness.left_activity_ids == (first.id,)


def test_an_activity_that_changed_item_makes_it_stale():
    first, second, links, layout = saved_case()
    moved = replace(first, item_number=3)

    staleness = layout_staleness(layout, [moved, second], links)

    assert staleness.is_stale is True
    assert staleness.moved_activity_ids == (first.id,)


def test_an_activity_that_changed_group_has_moved():
    first, second, links, layout = saved_case()

    staleness = layout_staleness(layout, [first, replace(second, group_number=4)], links)

    assert staleness.moved_activity_ids == (second.id,)


def test_a_new_link_makes_the_layout_stale():
    first, second, links, layout = saved_case()
    extra = link(first, DOC_A, 9)

    staleness = layout_staleness(layout, [first, second], [*links, extra])

    assert staleness.is_stale is True
    assert staleness.new_link_activity_ids == (first.id,)


def test_an_activity_validated_after_the_layout_has_joined_it():
    first, second, links, layout = saved_case()
    late = make_activity(2, 7)

    staleness = layout_staleness(layout, [first, second, late], [*links, link(late, DOC_A, 2)])

    assert staleness.joined_activity_ids == (late.id,)
    assert staleness.new_link_activity_ids == ()


def test_a_removed_link_does_not_make_the_layout_stale():
    first, second, links, layout = saved_case()

    staleness = layout_staleness(layout, [first, second], links[:1])

    assert staleness.is_stale is False


def test_a_layout_activity_with_no_known_item_is_not_taken_as_moved():
    first, _, links, _ = saved_case()
    layout = ComprovanteLayout(
        PROCESS_ID,
        (LayoutActivity(first.id, (LayoutPage(DOC_A, 1),)),),
        base_evidence_keys=derive_layout(PROCESS_ID, [first], links).base_evidence_keys,
    )

    assert layout_staleness(layout, [first], links).is_stale is False


def test_a_change_of_date_or_title_does_not_make_the_layout_stale():
    first, second, links, layout = saved_case()
    edited = replace(first, title="Outro título", description="Texto novo")

    assert layout_staleness(layout, [edited, second], links).is_stale is False


# --- what the generation uses (ARR-08) ------------------------------------------------------


def test_the_generation_layout_keeps_only_the_current_activities_in_the_saved_order():
    first, second, links, layout = saved_case()
    third = make_activity(3, 2)
    reordered = replace(layout, activities=(layout.activities[1], layout.activities[0]))
    rejected = replace(first, status=ActivityStatus.REJEITADA)

    used = current_layout(reordered, [rejected, second, third], links)

    assert [a.activity_id for a in used.activities] == [second.id, third.id]


def test_the_generation_layout_adds_the_new_activities_after_the_saved_ones_with_their_links():
    first, second, links, layout = saved_case()
    late = make_activity(2, 7)
    new_links = [*links, link(late, DOC_B, 6)]

    used = current_layout(layout, [first, second, late], new_links)

    assert [a.activity_id for a in used.activities] == [first.id, second.id, late.id]
    assert used.activities[2].pages == (LayoutPage(DOC_B, 6),)


def test_the_generation_layout_keeps_the_pages_the_user_arranged_even_if_a_link_exists():
    first, _, links, layout = saved_case()
    trimmed = replace(layout, activities=(replace(layout.activities[0], pages=()),))

    used = current_layout(trimmed, [first], links)

    assert used.activities[0].pages == ()


def test_the_generation_layout_takes_the_current_item_of_an_activity_that_moved():
    first, second, links, layout = saved_case()
    moved = replace(first, item_number=3)

    used = current_layout(layout, [moved, second], links)

    assert (used.activities[0].group_number, used.activities[0].item_number) == (2, 3)


def test_the_generation_layout_keeps_the_version_and_the_base_keys_of_the_saved_one():
    first, second, links, layout = saved_case()
    saved = replace(layout, version=4)

    used = current_layout(saved, [first, second], links)

    assert (used.version, used.base_evidence_keys) == (4, saved.base_evidence_keys)


# --- entries that cannot be used any more ---------------------------------------------------


def test_an_entry_of_a_document_removed_from_the_process_is_invalid():
    first, second, links, layout = saved_case()
    present = source(id=DOC_B)

    invalid = invalid_entries(layout, [present])

    assert [(k.activity_id, k.document_id, k.page) for k in invalid] == [(first.id, DOC_A, 1)]


def test_an_entry_of_a_document_with_its_file_deleted_is_invalid():
    first, second, links, layout = saved_case()
    kept, purged = source(id=DOC_A), source(id=DOC_B, file_deleted=True)

    invalid = invalid_entries(layout, [kept, purged])

    assert [(k.activity_id, k.document_id) for k in invalid] == [(second.id, DOC_B)]


def test_an_entry_beyond_the_last_page_of_its_document_is_invalid():
    a = make_activity(2, 7)
    pages = (LayoutPage(DOC_A, 4), LayoutPage(DOC_A, 5))
    layout = ComprovanteLayout(PROCESS_ID, (LayoutActivity(a.id, pages, 2, 7),))

    invalid = invalid_entries(layout, [source(id=DOC_A, page_count=4)])

    assert [(k.activity_id, k.page) for k in invalid] == [(a.id, 5)]


def test_valid_entries_are_not_listed():
    first, second, links, layout = saved_case()

    assert invalid_entries(layout, [source(id=DOC_A), source(id=DOC_B, page_count=4)]) == ()
