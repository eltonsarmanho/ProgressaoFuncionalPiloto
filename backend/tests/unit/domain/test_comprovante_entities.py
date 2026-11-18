"""ARR-01, CMP-04: layout and plan entities of the Comprovante."""

import dataclasses
from uuid import uuid4

import pytest

from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
    PageKind,
    PlanPage,
    Staleness,
)


@pytest.mark.parametrize("blank", [None, "", "   ", "\n"])
def test_a_blank_justification_is_stored_as_none(blank):
    assert LayoutPage(uuid4(), 3, blank).repeat_justification is None


def test_a_justification_with_text_is_kept():
    page = LayoutPage(uuid4(), 3, "Prova da carga horária")

    assert page.repeat_justification == "Prova da carga horária"


def test_the_justification_defaults_to_none():
    assert LayoutPage(uuid4(), 1).repeat_justification is None


@pytest.mark.parametrize("number", [0, -1])
def test_a_page_below_one_is_refused(number):
    with pytest.raises(ValueError):
        LayoutPage(uuid4(), number)


def test_page_one_is_accepted_and_the_page_keeps_document_and_number():
    document_id = uuid4()

    page = LayoutPage(document_id, 1)

    assert (page.document_id, page.page) == (document_id, 1)


def test_a_layout_keeps_activities_in_order_with_their_pages_and_its_version():
    process_id, first, second = uuid4(), uuid4(), uuid4()
    pages = (LayoutPage(uuid4(), 2), LayoutPage(uuid4(), 1, "Repetida"))
    key = EvidenceKey(first, pages[0].document_id, 2)

    layout = ComprovanteLayout(
        process_id,
        (LayoutActivity(first, pages), LayoutActivity(second)),
        base_evidence_keys=(key,),
        version=3,
    )

    assert [a.activity_id for a in layout.activities] == [first, second]
    assert layout.activities[0].pages == pages
    assert layout.activities[1].pages == ()
    assert layout.base_evidence_keys == (key,)
    assert (layout.process_id, layout.version) == (process_id, 3)


def test_a_layout_that_was_never_saved_has_version_zero_and_no_base_keys():
    layout = ComprovanteLayout(uuid4(), ())

    assert (layout.version, layout.base_evidence_keys) == (0, ())


def test_the_four_page_kinds_exist():
    assert [k.value for k in PageKind] == ["CAPA", "SUMARIO", "SEPARADOR", "ORIGINAL"]


def test_a_plan_keeps_the_ordered_numbered_pages_and_the_hash():
    document_id = uuid4()
    pages = (
        PlanPage(PageKind.CAPA, 1),
        PlanPage(PageKind.SUMARIO, 2),
        PlanPage(PageKind.SEPARADOR, 3, group_number=2),
        PlanPage(PageKind.ORIGINAL, 4, group_number=2, document_id=document_id, source_page=7),
    )

    plan = ComprovantePlan(pages, plan_hash="a" * 64)

    assert [(p.kind, p.number) for p in plan.pages] == [
        (PageKind.CAPA, 1), (PageKind.SUMARIO, 2), (PageKind.SEPARADOR, 3), (PageKind.ORIGINAL, 4),
    ]  # fmt: skip
    assert (plan.pages[3].document_id, plan.pages[3].source_page) == (document_id, 7)
    assert plan.plan_hash == "a" * 64


def test_the_plan_numbers_continue_from_the_cover():
    with pytest.raises(ValueError):
        ComprovantePlan((PlanPage(PageKind.CAPA, 1), PlanPage(PageKind.SUMARIO, 3)), "h")
    with pytest.raises(ValueError):
        ComprovantePlan((PlanPage(PageKind.CAPA, 2),), "h")


def test_the_plan_and_the_layout_are_immutable():
    plan = ComprovantePlan((PlanPage(PageKind.CAPA, 1),), "h")
    layout = ComprovanteLayout(uuid4(), ())

    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.plan_hash = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        layout.version = 9  # type: ignore[misc]


def test_staleness_is_set_by_any_of_its_three_causes_and_clear_when_empty():
    activity_id = uuid4()

    assert Staleness().is_stale is False
    assert Staleness(left_activity_ids=(activity_id,)).is_stale is True
    assert Staleness(moved_activity_ids=(activity_id,)).is_stale is True
    assert Staleness(new_link_activity_ids=(activity_id,)).is_stale is True
