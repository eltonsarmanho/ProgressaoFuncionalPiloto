"""REL-01, REL-07: report template and draft entities."""

import dataclasses
from uuid import uuid4

import pytest

from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.report import (
    DraftEntry,
    DraftSection,
    EntrySource,
    EntrySpec,
    GroupBy,
    MatchRule,
    ReportDraft,
    ReportTemplate,
    TemplateSection,
)


def entry(text="Texto-modelo.", source=EntrySource.MODELO, **kw) -> DraftEntry:
    return DraftEntry(activity_id=uuid4(), text=text, source=source, **kw)


def test_the_source_admits_exactly_model_ai_and_user():
    assert [s.value for s in EntrySource] == ["MODELO", "IA", "USUARIO"]


def test_a_draft_entry_keeps_activity_text_source_and_warnings():
    activity_id = uuid4()
    warning = GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, "NUMERO")

    item = DraftEntry(activity_id, "Orientação concluída.", EntrySource.IA, (warning,))

    assert item.activity_id == activity_id
    assert item.text == "Orientação concluída."
    assert item.source is EntrySource.IA
    assert item.warnings == (warning,)


def test_a_draft_entry_without_warnings_has_an_empty_tuple():
    assert entry().warnings == ()


def test_a_source_string_of_the_three_values_becomes_the_enum_member():
    assert entry(source="USUARIO").source is EntrySource.USUARIO


@pytest.mark.parametrize("source", ["", "ia", "OUTRO", None])
def test_any_other_source_is_refused(source):
    with pytest.raises(ValueError):
        entry(source=source)


def test_a_template_section_has_match_group_by_entry_and_order_items():
    section = TemplateSection(
        key="1.3",
        title="Atividades de orientação",
        match=(MatchRule(group=2), MatchRule(group=3, item=2)),
        group_by=GroupBy.ITEM,
        entry=EntrySpec(line="{title}"),
        order_items=True,
    )

    assert section.match == (MatchRule(2, None), MatchRule(3, 2))
    assert section.group_by is GroupBy.ITEM
    assert section.entry.line == "{title}"
    assert section.order_items is True
    plain = TemplateSection("5", "Outras", (), GroupBy.NONE, EntrySpec(line="{title}"))
    assert plain.order_items is False


def test_the_three_grouping_modes_of_the_configuration_exist():
    assert {g.value for g in GroupBy} == {"academic_period", "item", "none"}


def test_an_entry_spec_has_a_line_or_fields_but_not_both_or_neither():
    fields = (("Carga horária", "{course_hours}"), ("Período", "{period}"))

    assert EntrySpec(fields=fields).fields == fields
    with pytest.raises(ValueError):
        EntrySpec()
    with pytest.raises(ValueError):
        EntrySpec(line="{title}", fields=fields)


def test_a_template_finds_a_section_by_key():
    line = EntrySpec(line="{title}")
    one = TemplateSection("1.1", "Ensino", (MatchRule(1, 1),), GroupBy.ACADEMIC_PERIOD, line)
    two = TemplateSection("2", "Pesquisa", (MatchRule(5),), GroupBy.NONE, line)

    template = ReportTemplate(id="ufpa-modelo-2", version=1, sections=(one, two))

    assert [s.key for s in template.sections] == ["1.1", "2"]
    assert template.section("2") is two
    assert template.section("9") is None


def test_the_draft_is_immutable_and_replace_gives_a_new_copy():
    process_id = uuid4()
    section = DraftSection(key="1.1", title="Ensino", free_text="", entries=(entry(),))
    draft = ReportDraft(process_id, "ufpa-modelo-2", 1, (section,), version=1)

    edited = dataclasses.replace(
        draft, sections=(dataclasses.replace(section, free_text="Nota."),), version=2
    )

    assert draft.sections[0].free_text == "" and draft.version == 1
    assert edited.sections[0].free_text == "Nota." and edited.version == 2
    assert (edited.process_id, edited.template_id, edited.template_version) == (
        process_id, "ufpa-modelo-2", 1,
    )  # fmt: skip
    with pytest.raises(dataclasses.FrozenInstanceError):
        draft.version = 3  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        section.entries = ()  # type: ignore[misc]


def test_a_draft_section_keeps_key_title_free_text_entries_and_warnings():
    warning = GenerationAlert(GenerationAlertCode.REDACAO_INDISPONIVEL)
    items = (entry("A."), entry("B.", EntrySource.USUARIO))

    section = DraftSection("6", "Participação em bancas", "Livre", items, (warning,))

    assert (section.key, section.free_text) == ("6", "Livre")
    assert section.title == "Participação em bancas"
    assert [e.text for e in section.entries] == ["A.", "B."]
    assert section.warnings == (warning,)
    assert DraftSection("2", "Pesquisa").entries == ()
