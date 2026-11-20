"""CMP-05, CMP-06, CMP-07: shared page, justified repeat and an activity with no page."""

from uuid import uuid4

from app.domain.entities.comprovante import (
    ComprovanteLayout,
    LayoutActivity,
    LayoutPage,
    PageKind,
    TocLevel,
)
from app.domain.entities.generated import GenerationAlertCode
from app.domain.rules.comprovante_plan import (
    NO_VOUCHER_NOTE,
    plan_comprovante,
    remission_text,
)
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity

DOC_A, DOC_B = uuid4(), uuid4()


def layout_of(*entries):
    return ComprovanteLayout(
        PROCESS_ID,
        tuple(
            LayoutActivity(a.id, tuple(pages), a.group_number, a.item_number)
            for a, pages in entries
        ),
    )


def activity_entries(plan):
    return [e for e in plan.toc if e.level is TocLevel.ATIVIDADE]


def originals(plan):
    return [p for p in plan.pages if p.kind is PageKind.ORIGINAL]


def shared_case():
    first, second = make_activity(2, 7), make_activity(2, 7)
    shared = LayoutPage(DOC_A, 3)
    layout = layout_of((first, [shared]), (second, [shared]))
    return first, second, plan_comprovante(layout, [first, second], 8)


# --- the same page in more than one activity (CMP-05) ---------------------------------------


def test_the_first_activity_attaches_the_page_and_the_second_points_to_it():
    first, second, plan = shared_case()

    entries = activity_entries(plan)
    assert [(p.document_id, p.source_page, p.number) for p in originals(plan)] == [(DOC_A, 3, 4)]
    assert [(r.remission, r.comprovante_page) for r in entries[0].sources] == [(False, 4)]
    assert [(r.remission, r.comprovante_page) for r in entries[1].sources] == [(True, 4)]


def test_the_remission_reads_ver_comprovante_with_the_page_of_the_copy_and_the_source_page():
    _, _, plan = shared_case()

    remission = activity_entries(plan)[1].sources[0]

    assert remission_text(remission) == "ver comprovante nº 4, p. 3"


def test_a_remission_takes_no_page_of_its_own_and_the_next_page_continues_the_numbers():
    first, second, third = make_activity(2, 7), make_activity(2, 7), make_activity(2, 7)
    layout = layout_of(
        (first, [LayoutPage(DOC_A, 1)]),
        (second, [LayoutPage(DOC_A, 1)]),
        (third, [LayoutPage(DOC_A, 2)]),
    )

    plan = plan_comprovante(layout, [first, second, third], 8)

    assert [p.number for p in originals(plan)] == [4, 5]
    assert [p.number for p in plan.pages] == [1, 2, 3, 4, 5]


def test_an_activity_with_only_a_remission_has_the_page_of_the_copy_as_its_range():
    _, _, plan = shared_case()

    second = activity_entries(plan)[1]

    assert (second.first_page, second.last_page) == (4, 4)


def test_the_range_of_an_activity_counts_only_the_pages_attached_for_it():
    first, second = make_activity(2, 7), make_activity(2, 7)
    layout = layout_of(
        (first, [LayoutPage(DOC_A, 1)]),
        (second, [LayoutPage(DOC_A, 1), LayoutPage(DOC_A, 2), LayoutPage(DOC_B, 1)]),
    )

    plan = plan_comprovante(layout, [first, second], 8)

    entry = activity_entries(plan)[1]
    assert [r.remission for r in entry.sources] == [True, False, False]
    assert (entry.first_page, entry.last_page) == (5, 6)


def test_a_page_of_another_document_with_the_same_number_is_not_shared():
    first, second = make_activity(2, 7), make_activity(2, 7)
    layout = layout_of((first, [LayoutPage(DOC_A, 1)]), (second, [LayoutPage(DOC_B, 1)]))

    plan = plan_comprovante(layout, [first, second], 8)

    assert len(originals(plan)) == 2
    assert [r.remission for e in activity_entries(plan) for r in e.sources] == [False, False]


def test_the_same_page_twice_in_one_activity_is_attached_once():
    a = make_activity(2, 7)
    layout = layout_of((a, [LayoutPage(DOC_A, 1), LayoutPage(DOC_A, 1)]))

    plan = plan_comprovante(layout, [a], 8)

    assert len(originals(plan)) == 1
    assert [r.remission for r in activity_entries(plan)[0].sources] == [False, True]


def test_a_shared_page_raises_no_alert():
    _, _, plan = shared_case()

    assert plan.alerts == ()


# --- a repeat with justification (CMP-06) ---------------------------------------------------


def justified_case(reason="Prova também a carga horária"):
    first, second = make_activity(2, 7), make_activity(2, 7)
    layout = layout_of((first, [LayoutPage(DOC_A, 3)]), (second, [LayoutPage(DOC_A, 3, reason)]))
    return first, second, plan_comprovante(layout, [first, second], 8)


def test_a_justified_repeat_attaches_the_page_again():
    _, _, plan = justified_case()

    assert [(p.document_id, p.source_page, p.number) for p in originals(plan)] == [
        (DOC_A, 3, 4),
        (DOC_A, 3, 5),
    ]
    second = activity_entries(plan)[1]
    assert [(r.remission, r.comprovante_page) for r in second.sources] == [(False, 5)]


def test_a_justified_repeat_leaves_the_remission_out_and_records_the_justification():
    first, second, plan = justified_case()

    assert plan.alerts[0].code is GenerationAlertCode.PAGINA_REPETIDA_JUSTIFICADA
    assert plan.alerts[0].activity_id == second.id
    assert (plan.alerts[0].document_id, plan.alerts[0].page) == (DOC_A, 3)
    assert plan.alerts[0].justification == "Prova também a carga horária"
    assert activity_entries(plan)[1].sources[0].justification == "Prova também a carga horária"


def test_a_justification_on_a_page_attached_for_the_first_time_repeats_nothing():
    a = make_activity(2, 7)
    layout = layout_of((a, [LayoutPage(DOC_A, 3, "Motivo")]))

    plan = plan_comprovante(layout, [a], 8)

    assert plan.alerts == ()
    assert len(originals(plan)) == 1


def test_a_blank_justification_is_a_plain_remission():
    _, _, plan = justified_case("   ")

    assert len(originals(plan)) == 1
    assert activity_entries(plan)[1].sources[0].remission is True


def test_a_later_remission_points_to_the_first_copy_not_to_the_repeat():
    first, second, third = make_activity(2, 7), make_activity(2, 7), make_activity(2, 7)
    layout = layout_of(
        (first, [LayoutPage(DOC_A, 3)]),
        (second, [LayoutPage(DOC_A, 3, "Motivo")]),
        (third, [LayoutPage(DOC_A, 3)]),
    )

    plan = plan_comprovante(layout, [first, second, third], 8)

    last = activity_entries(plan)[2].sources[0]
    assert (last.remission, last.comprovante_page) == (True, 4)


# --- an activity with no page (CMP-07) ------------------------------------------------------


def test_an_activity_without_a_page_enters_with_the_line_sem_comprovante_anexado():
    a = make_activity(2, 7, title="Orientação de TCC")
    layout = layout_of((a, []))

    plan = plan_comprovante(layout, [a], 8)

    entry = activity_entries(plan)[0]
    assert (entry.title, entry.note, entry.sources) == ("Orientação de TCC", NO_VOUCHER_NOTE, ())
    assert NO_VOUCHER_NOTE == "Sem comprovante anexado"


def test_an_activity_without_a_page_raises_atividade_sem_comprovante():
    a = make_activity(2, 7)

    plan = plan_comprovante(layout_of((a, [])), [a], 8)

    assert [(x.code, x.activity_id) for x in plan.alerts] == [
        (GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE, a.id)
    ]


def test_an_activity_with_a_page_has_no_note():
    _, _, plan = shared_case()

    assert [e.note for e in activity_entries(plan)] == [None, None]


def test_the_numbers_of_the_other_pages_do_not_change_when_an_activity_has_no_page():
    before, bare, after = make_activity(2, 7), make_activity(2, 7), make_activity(2, 7)
    with_bare = layout_of(
        (before, [LayoutPage(DOC_A, 1)]), (bare, []), (after, [LayoutPage(DOC_A, 2)])
    )
    without = layout_of((before, [LayoutPage(DOC_A, 1)]), (after, [LayoutPage(DOC_A, 2)]))

    plan_with = plan_comprovante(with_bare, [before, bare, after], 8)
    plan_without = plan_comprovante(without, [before, after], 8)

    assert [(p.number, p.source_page) for p in originals(plan_with)] == [
        (p.number, p.source_page) for p in originals(plan_without)
    ]


def test_an_activity_missing_from_the_layout_is_also_flagged_without_a_voucher():
    arranged, newcomer = make_activity(2, 7), make_activity(2, 7)
    layout = layout_of((arranged, [LayoutPage(DOC_A, 1)]))

    plan = plan_comprovante(layout, [arranged, newcomer], 8)

    assert [x.activity_id for x in plan.alerts] == [newcomer.id]
