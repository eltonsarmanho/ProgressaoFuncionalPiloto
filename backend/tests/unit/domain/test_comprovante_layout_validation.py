"""ARR-02 to ARR-06: what a saved layout may contain."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.comprovante import ComprovanteLayout, LayoutActivity, LayoutPage
from app.domain.entities.generated import GenerationCode
from app.domain.errors import GenerationRefused, NotFound, ValidationFailed
from app.domain.rules.comprovante_plan import layout_page, validate_layout
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity, source


def entry(activity, *pages, group=None, item=None):
    return LayoutActivity(
        activity.id,
        tuple(pages),
        activity.group_number if group is None else group,
        activity.item_number if item is None else item,
    )


def layout_of(*entries):
    return ComprovanteLayout(PROCESS_ID, tuple(entries), version=3)


def setup():
    doc = source(page_count=10)
    a, b, c = make_activity(2, 3), make_activity(2, 7), make_activity(2, 7)
    return doc, a, b, c


# --- documents and pages of the process (ARR-06) --------------------------------------------


def test_a_layout_with_documents_and_pages_of_the_process_is_accepted():
    doc, a, b, c = setup()
    layout = layout_of(entry(a, LayoutPage(doc.id, 1)), entry(b, LayoutPage(doc.id, 10)))

    assert validate_layout(layout, [doc], [a, b, c]) == layout


def test_a_document_of_another_process_is_not_found():
    doc, a, _, _ = setup()
    layout = layout_of(entry(a, LayoutPage(uuid4(), 1)))

    with pytest.raises(NotFound):
        validate_layout(layout, [doc], [a])


def test_a_page_above_the_last_page_of_the_document_is_refused_with_its_code():
    doc, a, _, _ = setup()
    layout = layout_of(entry(a, LayoutPage(doc.id, 11)))

    with pytest.raises(GenerationRefused) as caught:
        validate_layout(layout, [doc], [a])

    assert caught.value.code == GenerationCode.PAGINA_FORA_DO_DOCUMENTO


def test_the_last_page_of_the_document_is_accepted():
    doc, a, _, _ = setup()

    validate_layout(layout_of(entry(a, LayoutPage(doc.id, 10))), [doc], [a])


def test_page_zero_is_refused_with_the_code_of_a_page_outside_the_document():
    doc, _, _, _ = setup()

    with pytest.raises(GenerationRefused) as caught:
        layout_page(doc.id, 0)

    assert caught.value.code == GenerationCode.PAGINA_FORA_DO_DOCUMENTO


def test_a_page_from_one_up_is_built_with_its_justification():
    doc, _, _, _ = setup()

    assert layout_page(doc.id, 3, "Prova a carga") == LayoutPage(doc.id, 3, "Prova a carga")


def test_an_activity_that_is_not_validated_in_the_process_is_not_found():
    doc, a, b, _ = setup()
    rejected = replace(b, status=ActivityStatus.REJEITADA)
    layout = layout_of(entry(a), entry(b))

    with pytest.raises(NotFound):
        validate_layout(layout, [doc], [a, rejected])


def test_an_activity_of_another_process_is_not_found():
    doc, a, _, _ = setup()
    stranger = make_activity(2, 7)

    with pytest.raises(NotFound):
        validate_layout(layout_of(entry(a), entry(stranger)), [doc], [a])


# --- the item of an activity (ARR-05) -------------------------------------------------------


def test_moving_an_activity_to_another_item_is_refused():
    doc, a, b, _ = setup()
    layout = layout_of(entry(a), entry(b, item=3))

    with pytest.raises(ValidationFailed):
        validate_layout(layout, [doc], [a, b])


def test_moving_an_activity_to_another_group_is_refused():
    doc, a, _, _ = setup()

    with pytest.raises(ValidationFailed):
        validate_layout(layout_of(entry(a, group=3)), [doc], [a])


def test_putting_the_items_out_of_the_order_of_the_table_is_refused():
    doc, a, b, _ = setup()
    layout = layout_of(entry(b), entry(a))

    with pytest.raises(ValidationFailed):
        validate_layout(layout, [doc], [a, b])


def test_an_activity_without_a_stated_item_takes_the_one_of_the_scoring():
    doc, a, _, _ = setup()
    layout = layout_of(LayoutActivity(a.id))

    validated = validate_layout(layout, [doc], [a])

    assert (validated.activities[0].group_number, validated.activities[0].item_number) == (2, 3)


# --- what may be rearranged (ARR-02 to ARR-04) ----------------------------------------------


def test_activities_inside_an_item_may_be_reordered_and_the_new_order_is_kept():
    doc, _, b, c = setup()
    layout = layout_of(entry(c, LayoutPage(doc.id, 1)), entry(b, LayoutPage(doc.id, 2)))

    validated = validate_layout(layout, [doc], [b, c])

    assert [x.activity_id for x in validated.activities] == [c.id, b.id]


def test_pages_inside_an_activity_may_be_reordered_and_the_new_order_is_kept():
    doc, a, _, _ = setup()
    pages = (LayoutPage(doc.id, 5), LayoutPage(doc.id, 2), LayoutPage(doc.id, 9))

    validated = validate_layout(layout_of(entry(a, *pages)), [doc], [a])

    assert validated.activities[0].pages == pages


def test_a_page_may_be_added_at_a_position_of_an_activity():
    doc, a, _, _ = setup()
    pages = (LayoutPage(doc.id, 1), LayoutPage(doc.id, 8), LayoutPage(doc.id, 2))

    validated = validate_layout(layout_of(entry(a, *pages)), [doc], [a])

    assert [p.page for p in validated.activities[0].pages] == [1, 8, 2]


def test_a_page_may_be_removed_from_the_layout_and_the_activity_may_end_with_none():
    doc, a, _, _ = setup()
    layout = layout_of(entry(a))

    validated = validate_layout(layout, [doc], [a])

    assert validated.activities[0].pages == ()


def test_a_justified_repeat_is_kept_with_its_justification():
    doc, a, b, _ = setup()
    layout = layout_of(
        entry(a, LayoutPage(doc.id, 1)), entry(b, LayoutPage(doc.id, 1, "Prova também a carga"))
    )

    validated = validate_layout(layout, [doc], [a, b])

    assert validated.activities[1].pages[0].repeat_justification == "Prova também a carga"


def test_the_version_and_the_process_of_the_layout_are_kept():
    doc, a, _, _ = setup()

    validated = validate_layout(layout_of(entry(a)), [doc], [a])

    assert (validated.version, validated.process_id) == (3, PROCESS_ID)
