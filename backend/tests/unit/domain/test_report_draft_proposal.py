"""REL-01, REL-02, REL-11: the draft proposed from the validated activities."""

from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.report import EntrySource
from app.domain.rules.report_draft import (
    document_sections,
    empty_sections,
    group_target,
    propose_draft,
)
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity
from tests.unit.domain.report_support import BANCAS, group_map, template


def propose(*activities):
    return propose_draft(template(), list(activities), group_map(), process_id=PROCESS_ID)


def keys_of(draft, key):
    section = next(s for s in draft.sections if s.key == key)
    return [e.activity_id for e in section.entries]


@pytest.mark.parametrize(
    ("group", "item", "section"),
    [
        (1, 1, "1.1"),
        (1, 2, "1.2"),
        (2, 3, "1.3"),
        (3, 2, "6"),
        (4, 4, "3"),
        (5, 1, "2"),
        (6, 6, "4"),
        (7, 1, "6"),
        (8, 9, "6"),
    ],
)
def test_each_group_goes_to_the_section_of_the_group_map(group, item, section):
    activity = make_activity(group, item)

    draft = propose(activity)

    assert keys_of(draft, section) == [activity.id]
    others = [s.key for s in draft.sections if s.key != section and s.entries]
    assert others == []


def test_the_section_5_receives_only_what_is_moved_to_it():
    everything = [make_activity(g, 1) for g in (1, 2, 3, 4, 5, 6, 7, 8)]

    draft = propose(*everything)

    assert keys_of(draft, "5") == []


def test_the_sections_come_in_the_order_and_with_the_titles_of_the_template():
    draft = propose()

    assert [(s.key, s.title) for s in draft.sections] == [
        (s.key, s.title) for s in template().sections
    ]
    assert [s.key for s in draft.sections] == ["1.1", "1.2", "1.3", "2", "3", "4", "5", "6"]


def test_the_proposal_is_an_unsaved_draft_of_the_process_and_the_template_version():
    draft = propose()

    assert (draft.process_id, draft.template_id, draft.template_version, draft.version) == (
        PROCESS_ID,
        "modelo-sintetico",
        3,
        0,
    )


def test_every_proposed_entry_comes_from_the_template_and_has_no_warnings():
    draft = propose(make_activity(1, 1), make_activity(4, 4))

    entries = [e for s in draft.sections for e in s.entries]
    assert len(entries) == 2
    assert {e.source for e in entries} == {EntrySource.MODELO}
    assert [e.warnings for e in entries] == [(), ()]


def test_the_group_3_and_the_group_7_carry_their_subtitles_in_the_section_6():
    banca = make_activity(3, 2)
    training = make_activity(7, 1)
    admin = make_activity(8, 9)
    group = group_map()

    assert group_target(group, banca).subtitle == BANCAS
    assert group_target(group, training).subtitle == "Capacitação"
    assert group_target(group, admin).subtitle is None


def test_the_section_6_lists_the_groups_in_the_order_of_the_table():
    admin = make_activity(8, 9)
    training = make_activity(7, 1)
    banca = make_activity(3, 2)

    draft = propose(admin, training, banca)

    assert keys_of(draft, "6") == [banca.id, training.id, admin.id]


def test_a_section_without_activity_is_listed_empty_and_left_out_of_the_document():
    draft = propose(make_activity(1, 1), make_activity(5, 1))

    assert empty_sections(draft) == ("1.2", "1.3", "3", "4", "5", "6")
    assert [s.key for s in document_sections(draft)] == ["1.1", "2"]


def test_a_section_with_only_typed_text_is_not_empty():
    draft = propose()
    sections = tuple(
        replace(s, free_text="Texto digitado.") if s.key == "5" else s for s in draft.sections
    )
    typed = replace(draft, sections=sections)

    assert "5" not in empty_sections(typed)
    assert "5" in [s.key for s in document_sections(typed)]


def test_the_sections_1_1_and_1_2_follow_the_academic_period_and_then_the_date():
    late = make_activity(1, 1, academic_period="2023.2", event_date=date(2023, 9, 1))
    early_b = make_activity(1, 1, academic_period="2023.1", event_date=date(2023, 3, 20))
    early_a = make_activity(1, 1, academic_period="2023.1", event_date=date(2023, 3, 1))
    first_year = make_activity(1, 1, academic_period="2022.4", event_date=date(2022, 12, 1))

    draft = propose(late, early_b, early_a, first_year)

    assert keys_of(draft, "1.1") == [first_year.id, early_a.id, early_b.id, late.id]


def test_an_activity_without_academic_period_comes_after_the_dated_periods():
    none = make_activity(1, 2, academic_period=None)
    dated = make_activity(1, 2, academic_period="2023.1")

    draft = propose(none, dated)

    assert keys_of(draft, "1.2") == [dated.id, none.id]


def test_the_section_1_3_groups_by_item_and_puts_the_ended_before_the_ongoing():
    ongoing_a = make_activity(
        2, 3, event_date=None, period_start=date(2023, 3, 1), period_end=None
    )
    ended_a = make_activity(
        2, 3, event_date=None, period_start=date(2023, 1, 1), period_end=date(2023, 6, 1)
    )
    ended_b = make_activity(2, 7, event_date=date(2023, 8, 1))
    ongoing_b = make_activity(
        2, 7, event_date=None, period_start=date(2022, 12, 1), period_end=None
    )

    draft = propose(ongoing_b, ended_b, ongoing_a, ended_a)

    assert keys_of(draft, "1.3") == [ended_a.id, ongoing_a.id, ended_b.id, ongoing_b.id]


def test_a_section_without_the_item_split_keeps_ongoing_and_ended_by_date():
    ongoing = make_activity(
        4, 4, event_date=None, period_start=date(2022, 12, 1), period_end=None
    )
    ended = make_activity(4, 4, event_date=date(2023, 8, 1))

    draft = propose(ended, ongoing)

    assert keys_of(draft, "3") == [ongoing.id, ended.id]


@pytest.mark.parametrize("status", [ActivityStatus.AGUARDANDO_REVISAO, ActivityStatus.REJEITADA])
def test_an_activity_that_is_not_validated_stays_out_of_the_draft(status):
    draft = propose(make_activity(4, 4, status=status))

    assert empty_sections(draft)[:5] == ("1.1", "1.2", "1.3", "2", "3")
    assert keys_of(draft, "3") == []


def test_an_activity_without_group_or_with_a_group_outside_the_map_stays_out():
    unclassified = make_activity(1, 1, group_number=None, item_number=None)
    outside_map = make_activity(1, 5)

    draft = propose(unclassified, outside_map)

    assert [s for s in draft.sections if s.entries] == []


def test_the_whole_group_rule_serves_an_item_without_its_own_rule():
    activity = make_activity(2, 9)

    assert group_target(group_map(), activity).section_key == "1.3"
