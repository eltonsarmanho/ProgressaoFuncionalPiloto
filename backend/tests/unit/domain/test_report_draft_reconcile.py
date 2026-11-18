"""REL-07, REL-08: reconciling the saved draft with the activities and moving an activity."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.generated import GenerationAlertCode
from app.domain.entities.report import EntrySource
from app.domain.errors import NotFound
from app.domain.rules.report_draft import move_entry, propose_draft, reconcile_draft
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity
from tests.unit.domain.report_support import group_map, template

STALE = GenerationAlertCode.RASCUNHO_DESATUALIZADO


def draft_of(*activities):
    return propose_draft(template(), list(activities), group_map(), process_id=PROCESS_ID)


def reconcile(draft, *activities):
    return reconcile_draft(draft, list(activities), template(), group_map())


def section(draft, key):
    return next(s for s in draft.sections if s.key == key)


def edit(draft, activity, text, source=EntrySource.USUARIO):
    sections = tuple(
        replace(
            s,
            entries=tuple(
                replace(e, text=text, source=source) if e.activity_id == activity.id else e
                for e in s.entries
            ),
        )
        for s in draft.sections
    )
    return replace(draft, sections=sections)


def test_the_text_typed_by_the_user_stays_identical_after_reconciling():
    activity = make_activity(4, 4, title="Oficina de dados")
    typed = "Texto digitado pelo usuário, com 99 itens.\nSegunda linha."
    draft = edit(draft_of(activity), activity, typed)
    changed = replace(activity, title="Título alterado depois", hours=Decimal("5"))

    result = reconcile(draft, changed)

    assert section(result, "3").entries[0].text == typed
    assert section(result, "3").entries[0].source is EntrySource.USUARIO


def test_the_text_typed_by_the_user_stays_identical_when_other_activities_come_and_go():
    kept, gone = make_activity(4, 4), make_activity(4, 4)
    typed = "Meu texto."
    draft = edit(draft_of(kept, gone), kept, typed)

    result = reconcile(draft, kept, make_activity(4, 4))

    assert [e.text for e in section(result, "3").entries if e.activity_id == kept.id] == [typed]


def test_a_new_activity_goes_to_the_end_of_its_section_with_the_template_text():
    first = make_activity(4, 4, title="Primeira")
    draft = draft_of(first)
    newest = make_activity(4, 4, title="Nova atividade", event_date=None)

    result = reconcile(draft, first, newest)

    entries = section(result, "3").entries
    assert [e.activity_id for e in entries] == [first.id, newest.id]
    assert (entries[1].text, entries[1].source) == ("Nova atividade", EntrySource.MODELO)


def test_a_new_activity_before_the_others_by_date_still_goes_to_the_end():
    later = make_activity(4, 4, title="Depois")
    draft = draft_of(later)
    earlier = make_activity(4, 4, title="Antes", event_date=later.event_date.replace(year=2020))

    result = reconcile(draft, later, earlier)

    assert [e.activity_id for e in section(result, "3").entries] == [later.id, earlier.id]


def test_a_new_activity_makes_the_draft_stale_in_its_section_only():
    first = make_activity(4, 4)
    draft = draft_of(first)

    result = reconcile(draft, first, make_activity(4, 4))

    assert [w.code for w in section(result, "3").warnings] == [STALE]
    assert [s.key for s in result.sections if s.warnings] == ["3"]


def test_a_removed_activity_leaves_the_draft_and_makes_its_section_stale():
    gone, kept = make_activity(4, 4), make_activity(5, 1)
    draft = draft_of(gone, kept)

    result = reconcile(draft, kept)

    assert section(result, "3").entries == ()
    assert [w.code for w in section(result, "3").warnings] == [STALE]
    assert [e.activity_id for e in section(result, "2").entries] == [kept.id]


@pytest.mark.parametrize("status", [ActivityStatus.REJEITADA, ActivityStatus.AGUARDANDO_REVISAO])
def test_an_activity_that_is_no_longer_validated_counts_as_removed(status):
    activity = make_activity(4, 4)
    draft = draft_of(activity)

    result = reconcile(draft, replace(activity, status=status))

    assert section(result, "3").entries == ()
    assert [w.code for w in section(result, "3").warnings] == [STALE]


def test_without_new_or_removed_activities_the_draft_comes_back_as_it_was():
    activity = make_activity(4, 4)
    draft = draft_of(activity)

    assert reconcile(draft, activity) == draft


def test_reconciling_a_reconciled_draft_has_no_duplicate_entries_and_no_alert_left():
    first = make_activity(4, 4)
    draft = draft_of(first)
    activities = [first, make_activity(4, 4)]

    once = reconcile(draft, *activities)
    twice = reconcile(once, *activities)

    assert [e.activity_id for e in section(twice, "3").entries] == [
        e.activity_id for e in section(once, "3").entries
    ]
    assert [w for s in twice.sections for w in s.warnings] == []


def test_the_entry_from_the_template_follows_the_activity_but_the_one_from_the_ai_stays():
    model, ai = make_activity(4, 4, title="Modelo"), make_activity(4, 4, title="IA")
    draft = edit(draft_of(model, ai), ai, "Texto da IA.", EntrySource.IA)

    result = reconcile(draft, replace(model, title="Modelo corrigido"), ai)

    texts = {e.activity_id: e.text for e in section(result, "3").entries}
    assert texts == {model.id: "Modelo corrigido, 01/06/2023", ai.id: "Texto da IA."}


def test_moving_an_activity_puts_it_at_the_end_of_the_chosen_section():
    moved, stay = make_activity(4, 4), make_activity(5, 1)
    draft = draft_of(moved, stay)

    result = move_entry(draft, moved.id, "2", [moved, stay], template())

    assert section(result, "3").entries == ()
    assert [e.activity_id for e in section(result, "2").entries] == [stay.id, moved.id]


def test_a_reconciled_draft_keeps_the_activity_in_the_section_it_was_moved_to():
    moved = make_activity(4, 4)
    draft = move_entry(draft_of(moved), moved.id, "5", [moved], template())

    result = reconcile(draft, moved)

    assert [e.activity_id for e in section(result, "5").entries] == [moved.id]
    assert section(result, "3").entries == ()
    assert [w for s in result.sections for w in s.warnings] == []


def test_moving_keeps_the_text_the_user_typed():
    moved = make_activity(4, 4)
    draft = edit(draft_of(moved), moved, "Meu texto.")

    result = move_entry(draft, moved.id, "6", [moved], template())

    entry = section(result, "6").entries[0]
    assert (entry.text, entry.source) == ("Meu texto.", EntrySource.USUARIO)


def test_moving_writes_the_template_text_of_the_new_section_for_entries_not_typed():
    moved = make_activity(1, 1, title="Algoritmos", course_hours=Decimal("60"), event_date=None)
    draft = draft_of(moved)
    assert section(draft, "1.1").entries[0].text.startswith("Disciplina: ")

    result = move_entry(draft, moved.id, "6", [moved], template())

    entry = section(result, "6").entries[0]
    assert (entry.text, entry.source) == ("Algoritmos", EntrySource.MODELO)


def test_moving_to_the_section_it_is_in_changes_nothing():
    activity = make_activity(4, 4)
    draft = draft_of(activity, make_activity(4, 4))

    assert move_entry(draft, activity.id, "3", [activity], template()) == draft


def test_moving_to_a_section_that_does_not_exist_is_refused():
    activity = make_activity(4, 4)

    with pytest.raises(NotFound):
        move_entry(draft_of(activity), activity.id, "9", [activity], template())


def test_moving_an_activity_that_is_not_in_the_draft_is_refused():
    in_draft, outsider = make_activity(4, 4), make_activity(4, 4)

    with pytest.raises(NotFound):
        move_entry(draft_of(in_draft), outsider.id, "2", [in_draft, outsider], template())
