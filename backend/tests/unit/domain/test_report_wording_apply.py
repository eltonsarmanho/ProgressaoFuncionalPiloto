"""REL-04, REL-05, REL-07: applying the checked wording to the draft."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.report import EntrySource
from app.domain.errors import NotFound
from app.domain.rules.report_draft import propose_draft
from app.domain.rules.report_grounding import WordingVocabulary
from app.domain.rules.report_wording import (
    activities_to_word,
    apply_wording,
    build_wording_items,
)
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity
from tests.unit.domain.report_support import group_map, template

REJECTED = GenerationAlertCode.REDACAO_REJEITADA
UNAVAILABLE = GenerationAlertCode.REDACAO_INDISPONIVEL
MODEL = "Oficina de dados, 01/06/2023, 8 h"
FAITHFUL = "Oficina de dados realizada em 01/06/2023, com 8 horas."
INVENTED = "Oficina de dados realizada em 01/06/2023, com 12 horas."
VOCABULARY = WordingVocabulary(max_new_words=3)


def workshop(**kwargs):
    defaults = {"title": "Oficina de dados", "event_date": date(2023, 6, 1), "hours": Decimal("8")}
    defaults.update(kwargs)
    return make_activity(4, 4, **defaults)


def draft_of(*activities):
    return propose_draft(template(), list(activities), group_map(), process_id=PROCESS_ID)


def section(draft, key="3"):
    return next(s for s in draft.sections if s.key == key)


def entry_of(draft, activity, key="3"):
    return next(e for e in section(draft, key).entries if e.activity_id == activity.id)


def apply(draft, results, *activities, key="3"):
    return apply_wording(
        draft,
        key,
        results,
        template=template(),
        activities=list(activities),
        items=build_wording_items(list(activities)),
        vocabulary=VOCABULARY,
    )


def typed(draft, activity, text="Texto do usuário."):
    sections = tuple(
        replace(
            s,
            entries=tuple(
                replace(e, text=text, source=EntrySource.USUARIO)
                if e.activity_id == activity.id
                else e
                for e in s.entries
            ),
        )
        for s in draft.sections
    )
    return replace(draft, sections=sections)


def test_a_faithful_answer_becomes_the_text_of_the_entry_with_the_source_ai():
    activity = workshop()
    draft = draft_of(activity)

    applied = apply(draft, {activity.id: FAITHFUL}, activity)

    entry = entry_of(applied.draft, activity)
    assert (entry.text, entry.source, entry.warnings) == (FAITHFUL, EntrySource.IA, ())
    assert applied.warnings == ()
    assert section(applied.draft).warnings == ()


def test_an_answer_with_an_invented_number_becomes_the_template_text_with_the_reason():
    activity = workshop()
    draft = draft_of(activity)

    applied = apply(draft, {activity.id: INVENTED}, activity)

    entry = entry_of(applied.draft, activity)
    assert (entry.text, entry.source) == (MODEL, EntrySource.MODELO)
    assert entry.warnings == (GenerationAlert(REJECTED, "NUMERO"),)
    assert applied.warnings == (GenerationAlert(REJECTED, "NUMERO"),)


def test_the_warnings_returned_are_the_ones_written_in_the_section():
    activity = workshop()

    applied = apply(draft_of(activity), {activity.id: INVENTED}, activity)

    assert section(applied.draft).warnings == applied.warnings


def test_the_reasons_of_all_rejected_answers_are_gathered_in_the_section_warning():
    first, second = workshop(title="Primeira oficina"), workshop(title="Segunda oficina")
    results = {
        first.id: "Primeira oficina em 01/06/2023, com 99 horas.",
        second.id: "Segunda oficina de Joana Pereira em 01/06/2023.",
    }

    applied = apply(draft_of(first, second), results, first, second)

    assert applied.warnings == (GenerationAlert(REJECTED, "NUMERO,NOME"),)
    assert entry_of(applied.draft, first).warnings == (GenerationAlert(REJECTED, "NUMERO"),)
    assert entry_of(applied.draft, second).warnings == (GenerationAlert(REJECTED, "NOME"),)


def test_the_text_edited_by_the_user_stays_identical_even_when_the_answer_has_one_for_it():
    edited, other = workshop(), workshop(title="Outra oficina")
    draft = typed(draft_of(edited, other), edited)
    before = entry_of(draft, edited)

    applied = apply(
        draft, {edited.id: FAITHFUL, other.id: "Outra oficina em 01/06/2023."}, edited, other
    )

    assert entry_of(applied.draft, edited) == before
    assert entry_of(applied.draft, other).source is EntrySource.IA


def test_the_activities_to_word_leave_out_the_entries_the_user_edited():
    edited, other = workshop(), workshop(title="Outra oficina")
    draft = typed(draft_of(edited, other), edited)

    assert activities_to_word(draft, "3", [edited, other]) == [other]


def test_without_an_answer_every_entry_not_typed_gets_the_template_text_and_the_section_the_alert():
    typed_one, model_one, ai_one = workshop(), workshop(), workshop(title="Terceira oficina")
    draft = typed(draft_of(typed_one, model_one, ai_one), typed_one)
    draft = replace(
        draft,
        sections=tuple(
            replace(
                s,
                entries=tuple(
                    replace(e, text="Texto antigo da IA.", source=EntrySource.IA)
                    if e.activity_id == ai_one.id
                    else e
                    for e in s.entries
                ),
            )
            for s in draft.sections
        ),
    )

    applied = apply(draft, None, typed_one, model_one, ai_one)

    assert entry_of(applied.draft, typed_one).text == "Texto do usuário."
    assert entry_of(applied.draft, typed_one).source is EntrySource.USUARIO
    assert (entry_of(applied.draft, model_one).text, entry_of(applied.draft, model_one).source) == (
        MODEL,
        EntrySource.MODELO,
    )
    assert (entry_of(applied.draft, ai_one).text, entry_of(applied.draft, ai_one).source) == (
        "Terceira oficina, 01/06/2023, 8 h",
        EntrySource.MODELO,
    )
    assert applied.warnings == (GenerationAlert(UNAVAILABLE),)
    assert section(applied.draft).warnings == (GenerationAlert(UNAVAILABLE),)


def test_the_other_sections_and_the_version_of_the_draft_are_untouched():
    here, there = workshop(), make_activity(5, 1, title="Projeto de pesquisa")
    draft = replace(draft_of(here, there), version=7)

    applied = apply(draft, {here.id: FAITHFUL}, here, there)

    assert applied.draft.version == 7
    assert section(applied.draft, "2") == section(draft, "2")


def test_an_entry_without_an_answer_stays_as_it_was():
    answered, silent = workshop(), workshop(title="Outra oficina")
    draft = draft_of(answered, silent)

    applied = apply(draft, {answered.id: FAITHFUL}, answered, silent)

    assert entry_of(applied.draft, silent) == entry_of(draft, silent)


def test_an_answer_for_an_activity_that_was_not_sent_is_ignored():
    activity = workshop()
    draft = draft_of(activity)
    stranger = workshop(title="Estranha")

    applied = apply(draft, {stranger.id: "Texto qualquer."}, activity)

    assert applied.draft == draft


@pytest.mark.parametrize("blank", ["", "   \n "])
def test_a_blank_answer_leaves_the_entry_as_it_was(blank):
    activity = workshop()
    draft = draft_of(activity)

    applied = apply(draft, {activity.id: blank}, activity)

    assert entry_of(applied.draft, activity) == entry_of(draft, activity)


def test_a_new_answer_replaces_the_previous_wording_warnings_and_keeps_the_others():
    activity = workshop()
    stale = GenerationAlert(GenerationAlertCode.RASCUNHO_DESATUALIZADO, "x")
    first = apply(draft_of(activity), {activity.id: INVENTED}, activity).draft
    first = replace(
        first,
        sections=tuple(
            replace(s, warnings=(*s.warnings, stale)) if s.key == "3" else s for s in first.sections
        ),
    )

    second = apply(first, {activity.id: FAITHFUL}, activity)

    assert section(second.draft).warnings == (stale,)
    assert entry_of(second.draft, activity).warnings == ()
    assert second.warnings == ()


def test_a_section_that_is_not_in_the_draft_is_refused():
    activity = workshop()

    with pytest.raises(NotFound):
        apply(draft_of(activity), {}, activity, key="9")
