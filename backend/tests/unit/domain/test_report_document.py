"""REL-09, REL-11, REL-12: the report document is the draft, the header and the layout; nothing
else is written in it."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.report import (
    DraftEntry,
    EntrySource,
    PageSetup,
    ReportDraft,
    ReportLayout,
)
from app.domain.rules.report_document import build_report_document
from app.domain.rules.report_draft import ReportConfig, propose_draft
from app.domain.rules.report_grounding import WordingVocabulary
from app.domain.rules.table_document import TableHeader
from tests.unit.domain.report_support import BANCAS, group_map, template
from tests.unit.domain.scenario_211 import INTERSTICE, activity

HEADER = TableHeader(
    professor_name="Maria Docente da Silva",
    current_class="Adjunto",
    current_level=2,
    target_class="Associado",
    target_level=1,
    unit_name="Faculdade de Testes",
    interstice=INTERSTICE,
)
LAYOUT = ReportLayout(
    page=PageSetup(31.75, 31.75, 25.4, 25.4, "Times New Roman", 9),
    header_lines=("Serviço Público Federal", "Universidade Federal do Pará", "{unit_name}"),
    title="RELATÓRIO DE ATIVIDADES",
    identification=(
        "Nome: {professor_name}",
        "Professor {current_class}, nível {current_level}",
        "Período de interstício: {interstice}",
    ),
    body_heading="ATIVIDADES DESENVOLVIDAS",
    entry_style="campos",
)
CONFIG = ReportConfig(template(), group_map(), WordingVocabulary(max_new_words=3), LAYOUT)


def draft_of(activities) -> ReportDraft:
    return propose_draft(CONFIG.template, activities, CONFIG.group_map, process_id=uuid4())


def build(activities, draft=None, **kwargs):
    draft = draft or draft_of(activities)
    return build_report_document(CONFIG, HEADER, draft, activities, **kwargs)


def section(document, key):
    return next(s for s in document.sections if s.key == key)


def graduation(title, period, **kwargs):
    return activity(1, 1, title=title, academic_period=period, course_hours=Decimal("60"), **kwargs)


def test_the_header_and_the_identification_are_filled_with_the_process_data():
    document = build([activity(5, 1)])

    assert document.header_lines == (
        "Serviço Público Federal",
        "Universidade Federal do Pará",
        "Faculdade de Testes",
    )
    assert document.title == "RELATÓRIO DE ATIVIDADES"
    assert document.identification == (
        "Nome: Maria Docente da Silva",
        "Professor Adjunto, nível 2",
        "Período de interstício: 23/11/2022 a 23/11/2024",
    )
    assert document.body_heading == "ATIVIDADES DESENVOLVIDAS"
    assert document.layout is LAYOUT


def test_only_the_sections_with_activity_go_in_the_order_of_the_template():
    document = build([activity(5, 1), graduation("Cálculo", "2023.1"), activity(4, 4)])

    assert [s.key for s in document.sections] == ["1.1", "2", "3"]


def test_the_entry_text_is_the_text_of_the_draft_and_the_edited_text_is_kept():
    activities = [activity(5, 1, title="Projeto A"), activity(5, 1, title="Projeto B")]
    draft = draft_of(activities)
    research = draft.sections[3]
    edited = replace(
        research.entries[1],
        text="Texto digitado pelo docente.\nSegunda linha.",
        source=EntrySource.USUARIO,
    )
    ai = replace(research.entries[0], text="Redação aprovada.", source=EntrySource.IA)
    draft = replace(
        draft,
        sections=(
            *draft.sections[:3],
            replace(research, entries=(ai, edited)),
            *draft.sections[4:],
        ),
    )

    document = build(activities, draft)

    texts = [t for g in section(document, "2").groups for t in g.entries]
    assert texts == ["Redação aprovada.", "Texto digitado pelo docente.\nSegunda linha."]


def test_the_document_has_no_text_besides_the_draft_the_titles_and_the_subtitles():
    activities = [activity(5, 1, title="Projeto A"), activity(7, 1, title="Curso B")]
    draft = draft_of(activities)

    document = build(activities, draft)

    draft_texts = {e.text for s in draft.sections for e in s.entries}
    written = {t for s in document.sections for g in s.groups for t in g.entries}
    assert written == draft_texts
    subtitles = {g.subtitle for s in document.sections for g in s.groups}
    assert subtitles <= {None, "Capacitação"}


def test_graduation_is_grouped_by_academic_period_in_order_and_undated_entries_come_last():
    activities = [
        graduation("Física", "2023.2"),
        graduation("Cálculo", "2023.1"),
        graduation("Sem período", None),
        graduation("Álgebra", "2023.1"),
    ]

    document = build(activities)

    groups = section(document, "1.1").groups
    assert [g.subtitle for g in groups] == ["1º Período de 2023", "2º Período de 2023", None]
    assert [len(g.entries) for g in groups] == [2, 1, 1]
    assert "Cálculo" in groups[0].entries[0] and "Álgebra" in groups[0].entries[1]


def test_orientations_are_grouped_by_item_with_the_ongoing_ones_marked_and_last():
    done = activity(2, 3, title="Dissertação defendida")
    ongoing = activity(
        2, 3, title="Dissertação em curso", event_date=None, period_start=date(2024, 3, 1)
    )
    other = activity(2, 7, title="Monografia")
    names = {(2, 3): "Orientação de mestrado", (2, 7): "Orientação de graduação"}

    document = build([ongoing, other, done], item_names=names)

    groups = section(document, "1.3").groups
    assert [g.subtitle for g in groups] == [
        "Orientação de mestrado",
        "Orientação de mestrado (em andamento)",
        "Orientação de graduação",
    ]


def test_without_item_names_the_subtitle_is_the_numeral_of_the_item():
    document = build([activity(2, 3)])

    assert [g.subtitle for g in section(document, "1.3").groups] == ["II.3"]


def test_a_section_that_gathers_groups_has_one_subtitle_per_source_group():
    activities = [
        activity(8, 9, title="Produção"),
        activity(7, 1, title="Capacitação X"),
        activity(3, 2, title="Banca Y"),
    ]

    document = build(activities)

    groups = section(document, "6").groups
    assert [g.subtitle for g in groups] == [BANCAS, "Capacitação", None]


def test_an_activity_moved_to_another_section_keeps_no_subtitle_of_the_old_one():
    banca = activity(3, 2, title="Banca Y")
    draft = draft_of([banca])
    entry = draft.sections[7].entries[0]
    moved_to_2 = replace(draft.sections[3], entries=(entry,))
    emptied = replace(draft.sections[7], entries=())
    draft = replace(
        draft, sections=(*draft.sections[:3], moved_to_2, *draft.sections[4:7], emptied)
    )

    document = build([banca], draft)

    assert [s.key for s in document.sections] == ["2"]
    assert [g.subtitle for g in section(document, "2").groups] == [None]


def test_a_section_with_only_typed_text_goes_in_the_document_and_blank_entries_are_skipped():
    draft = draft_of([])
    cultural = replace(draft.sections[6], free_text="Atividade digitada pelo docente.")
    blank = DraftEntry(uuid4(), "   ", EntrySource.USUARIO)
    other = replace(draft.sections[4], entries=(blank,))
    draft = replace(
        draft, sections=(*draft.sections[:4], other, draft.sections[5], cultural, draft.sections[7])
    )

    document = build([], draft)

    assert [s.key for s in document.sections] == ["5"]
    assert section(document, "5").free_text == "Atividade digitada pelo docente."
    assert section(document, "5").groups == ()
