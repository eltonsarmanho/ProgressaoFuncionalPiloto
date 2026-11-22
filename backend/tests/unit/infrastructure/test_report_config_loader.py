"""ORD-02, REL-01: the report template and the dossier order are read from versioned files and
validated; a broken file stops the loading naming the file and the field."""

import copy
import json
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity
from app.domain.entities.generated import DocumentKind
from app.domain.entities.report import DossierSource, GroupBy, MatchRule
from app.domain.rules.report_draft import ENTRY_MARKERS, GroupTarget, activity_fields
from app.infrastructure.documents.config_loader import (
    ConfigError,
    ReportConfigLoader,
    load_dossier_order,
    load_report_config,
)

TEMPLATE = {
    "version": 2,
    "entry_style": "campos",
    "page": {
        "size": "A4",
        "margins_mm": {"left": 30, "right": 30, "top": 25, "bottom": 20},
        "font": "Times New Roman",
        "font_size": 9,
    },
    "header_lines": ["Serviço Público Federal", "{unit_name}"],
    "title": "RELATÓRIO DE ATIVIDADES",
    "identification": ["Nome: {professor_name}", "Período: {interstice}"],
    "body_heading": "ATIVIDADES DESENVOLVIDAS",
    "group_map": [
        {"group": 1, "item": 1, "section": "1.1"},
        {"group": 2, "section": "1.3"},
        {"group": 3, "section": "2", "subtitle": "Bancas"},
    ],
    "sections": [
        {
            "key": "1.1",
            "title": "Ensino de graduação",
            "group_by": "academic_period",
            "entry": {
                "fields": [
                    {"label": "Disciplina", "text": "{title}"},
                    {"label": "Carga horária", "text": "{course_hours}"},
                ]
            },
        },
        {
            "key": "1.3",
            "title": "Orientações",
            "group_by": "item",
            "order_items": True,
            "entry": {"line": "{title}[, {dates}]"},
        },
        {"key": "2", "title": "Outras", "entry": {"line": "{title}"}},
    ],
    "allowed_terms": ["UFPA"],
    "formal_vocabulary": ["realizou", "participou"],
    "forbidden_words": ["objetivo", "resultado"],
    "max_new_words": 3,
}
REPORTS = {"default": "modelo-a", "templates": {"modelo-a": TEMPLATE}}
DOSSIER = {
    "items": [
        {"order": 1, "key": "LATTES", "title": "Currículo", "source": "MANUAL"},
        {
            "order": 2,
            "key": "RELATORIO",
            "title": "Relatório",
            "source": "GERADO",
            "generated_by": "RELATORIO",
        },
        {
            "order": 3,
            "key": "TABELA",
            "title": "Tabela",
            "source": "GERADO",
            "generated_by": "TABELA",
        },
        {
            "order": 4,
            "key": "COMPROVANTE",
            "title": "Comprovante",
            "source": "GERADO",
            "generated_by": "COMPROVANTE",
        },
        {"order": 5, "key": "PORTARIA_BANCA", "title": "Portaria", "source": "PORTARIA_BANCA"},
    ]
}


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def reports_with(mutate):
    data = copy.deepcopy(REPORTS)
    mutate(data["templates"]["modelo-a"])
    return data


def failure(tmp_path, data, **kwargs):
    path = write(tmp_path, "report_templates.json", data)
    with pytest.raises(ConfigError) as error:
        load_report_config(path, **kwargs)
    return str(error.value)


def test_a_valid_file_gives_template_group_map_vocabulary_and_layout(tmp_path):
    config = load_report_config(write(tmp_path, "report_templates.json", REPORTS))

    assert (config.template.id, config.template.version) == ("modelo-a", 2)
    assert [s.key for s in config.template.sections] == ["1.1", "1.3", "2"]
    first, second, third = config.template.sections
    assert first.group_by is GroupBy.ACADEMIC_PERIOD
    assert first.entry.fields == (("Disciplina", "{title}"), ("Carga horária", "{course_hours}"))
    assert second.entry.line == "{title}[, {dates}]"
    assert second.order_items is True
    assert third.group_by is GroupBy.NONE
    assert config.group_map == {
        MatchRule(1, 1): GroupTarget("1.1"),
        MatchRule(2): GroupTarget("1.3"),
        MatchRule(3): GroupTarget("2", "Bancas"),
    }
    assert config.vocabulary.max_new_words == 3
    assert config.vocabulary.allowed_terms == ("UFPA",)
    assert config.vocabulary.formal_vocabulary == ("realizou", "participou")
    assert config.vocabulary.forbidden_words == ("objetivo", "resultado")
    layout = config.layout
    assert (layout.page.size, layout.page.font_name, layout.page.font_size_pt) == (
        "A4", "Times New Roman", 9,
    )  # fmt: skip
    assert (layout.page.margin_left_mm, layout.page.margin_top_mm) == (30, 25)
    assert layout.header_lines == ("Serviço Público Federal", "{unit_name}")
    assert layout.identification == ("Nome: {professor_name}", "Período: {interstice}")
    assert (layout.title, layout.body_heading) == (
        "RELATÓRIO DE ATIVIDADES",
        "ATIVIDADES DESENVOLVIDAS",
    )
    assert layout.entry_style == "campos"


def test_the_sections_match_is_what_the_group_map_sends_to_them(tmp_path):
    config = load_report_config(write(tmp_path, "report_templates.json", REPORTS))

    by_key = {s.key: s.match for s in config.template.sections}
    assert by_key == {"1.1": (MatchRule(1, 1),), "1.3": (MatchRule(2),), "2": (MatchRule(3),)}


def test_template_id_chooses_another_template_and_an_unknown_one_stops_the_loading(tmp_path):
    data = copy.deepcopy(REPORTS)
    data["templates"]["modelo-b"] = {**TEMPLATE, "version": 9}
    path = write(tmp_path, "report_templates.json", data)

    assert load_report_config(path, template_id="modelo-b").template.version == 9
    with pytest.raises(ConfigError) as error:
        load_report_config(path, template_id="nao-existe")
    assert "report_templates.json" in str(error.value)
    assert "nao-existe" in str(error.value)


def test_invalid_json_names_the_file(tmp_path):
    path = write(tmp_path, "report_templates.json", '{"default": ')
    with pytest.raises(ConfigError) as error:
        load_report_config(path)
    assert "report_templates.json" in str(error.value)
    assert "JSON" in str(error.value)


def test_a_section_without_key_names_the_file_and_the_field(tmp_path):
    def drop_key(template):
        del template["sections"][1]["key"]

    message = failure(tmp_path, reports_with(drop_key))

    assert "report_templates.json" in message
    assert "sections[1].key" in message


def test_a_group_map_pointing_at_a_section_that_does_not_exist_names_file_and_field(tmp_path):
    def point_nowhere(template):
        template["group_map"][2]["section"] = "9"

    message = failure(tmp_path, reports_with(point_nowhere))

    assert "report_templates.json" in message
    assert "group_map[2].section" in message
    assert "9" in message


def test_the_default_must_be_a_template_of_the_file(tmp_path):
    message = failure(tmp_path, {**REPORTS, "default": "outro"})
    assert "report_templates.json" in message
    assert "default" in message


@pytest.mark.parametrize(
    "line",
    ["{titulo}", "{title}, {inexistente}", "{title"],
)
def test_an_entry_marker_that_the_activity_does_not_have_or_that_is_malformed_is_refused(
    tmp_path, line
):
    def change(template):
        template["sections"][1]["entry"] = {"line": line}

    message = failure(tmp_path, reports_with(change))

    assert "report_templates.json" in message
    assert "sections[1].entry" in message


def test_an_unbalanced_optional_part_is_refused(tmp_path):
    def change(template):
        template["sections"][1]["entry"] = {"line": "{title}[, {dates}"}

    assert "sections[1].entry" in failure(tmp_path, reports_with(change))


def test_an_entry_has_a_line_or_fields_and_not_both_or_neither(tmp_path):
    def both(template):
        template["sections"][1]["entry"] = {
            "line": "{title}",
            "fields": [{"label": "A", "text": "{title}"}],
        }

    def neither(template):
        template["sections"][1]["entry"] = {}

    assert "sections[1].entry" in failure(tmp_path, reports_with(both))
    assert "sections[1].entry" in failure(tmp_path, reports_with(neither))


def test_a_marker_of_the_field_text_is_checked_like_the_line(tmp_path):
    def change(template):
        template["sections"][0]["entry"]["fields"][1]["text"] = "{horas}"

    assert "sections[0].entry.fields[1]" in failure(tmp_path, reports_with(change))


def test_the_header_and_identification_markers_are_checked(tmp_path):
    def header(template):
        template["header_lines"] = ["{faculdade}"]

    def identification(template):
        template["identification"] = ["Nome: {nome}"]

    assert "header_lines[0]" in failure(tmp_path, reports_with(header))
    assert "identification[0]" in failure(tmp_path, reports_with(identification))


def test_the_markers_of_an_entry_are_the_fields_the_activity_writes():
    activity = Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=1, item_number=1,
        title="Curso de teste em Química", description="Descrição", quantity=Decimal("1"),
        event_date=date(2023, 1, 2), hours=Decimal("10"), course_hours=Decimal("60"),
        academic_period="2023.1",
    )  # fmt: skip
    assert set(activity_fields(activity)) == ENTRY_MARKERS


def test_duplicate_section_keys_and_duplicate_rules_are_refused(tmp_path):
    def duplicate_section(template):
        template["sections"][2]["key"] = "1.1"

    def duplicate_rule(template):
        template["group_map"].append({"group": 2, "section": "2"})

    assert "sections[2].key" in failure(tmp_path, reports_with(duplicate_section))
    assert "group_map[3]" in failure(tmp_path, reports_with(duplicate_rule))


@pytest.mark.parametrize("value", ["semanal", 3, None])
def test_group_by_must_be_one_of_the_known_ways(tmp_path, value):
    def change(template):
        template["sections"][0]["group_by"] = value

    assert "sections[0].group_by" in failure(tmp_path, reports_with(change))


@pytest.mark.parametrize(
    "key", ["allowed_terms", "formal_vocabulary", "forbidden_words", "max_new_words"]
)
def test_the_vocabulary_of_the_conference_cannot_be_missing(tmp_path, key):
    def drop(template):
        del template[key]

    message = failure(tmp_path, reports_with(drop))

    assert key in message


def test_the_limit_of_new_words_cannot_be_negative_and_the_lists_hold_text(tmp_path):
    def negative(template):
        template["max_new_words"] = -1

    def numbers(template):
        template["forbidden_words"] = ["ok", 3]

    assert "max_new_words" in failure(tmp_path, reports_with(negative))
    assert "forbidden_words[1]" in failure(tmp_path, reports_with(numbers))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("page", "size"), "Carta"),
        (("page", "margins_mm", "left"), -1),
        (("page", "margins_mm", "top"), "muito"),
        (("page", "font_size"), 0),
        (("page", "font"), ""),
    ],
)
def test_the_page_setup_is_checked(tmp_path, path, value):
    def change(template):
        target = template
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value

    assert ".".join(path) in failure(tmp_path, reports_with(change))


def test_the_dossier_order_is_the_order_of_the_file_with_the_generated_ones_marked(tmp_path):
    items = load_dossier_order(write(tmp_path, "dossier_order.json", DOSSIER))

    assert [(i.order, i.key, i.title, i.source, i.generated_by) for i in items] == [
        (1, "LATTES", "Currículo", DossierSource.MANUAL, None),
        (2, "RELATORIO", "Relatório", DossierSource.GERADO, DocumentKind.RELATORIO),
        (3, "TABELA", "Tabela", DossierSource.GERADO, DocumentKind.TABELA),
        (4, "COMPROVANTE", "Comprovante", DossierSource.GERADO, DocumentKind.COMPROVANTE),
        (5, "PORTARIA_BANCA", "Portaria", DossierSource.PORTARIA_BANCA, None),
    ]


def test_dossier_with_invalid_json_names_the_file(tmp_path):
    path = write(tmp_path, "dossier_order.json", "[")
    with pytest.raises(ConfigError) as error:
        load_dossier_order(path)
    assert "dossier_order.json" in str(error.value)


@pytest.mark.parametrize(
    ("index", "change", "field"),
    [
        (1, {"title": ""}, "items[1].title"),
        (1, {"generated_by": "PORTARIA"}, "items[1].generated_by"),
        (2, {"order": 2}, "items[2].order"),
        (0, {"order": "um"}, "items[0].order"),
        (2, {"key": "RELATORIO"}, "items[2].key"),
        (2, {"key": ""}, "items[2].key"),
        (1, {"source": "OUTRA"}, "items[1].source"),
        (1, {"generated_by": None}, "items[1].generated_by"),
        (0, {"generated_by": "TABELA"}, "items[0].generated_by"),
        (4, {"generated_by": "PARECER"}, "items[4].generated_by"),
    ],
)
def test_a_dossier_item_with_a_bad_title_marker_or_order_names_the_field(
    tmp_path, index, change, field
):
    data = copy.deepcopy(DOSSIER)
    data["items"][index].update(change)
    path = write(tmp_path, "dossier_order.json", data)

    with pytest.raises(ConfigError) as error:
        load_dossier_order(path)

    assert "dossier_order.json" in str(error.value)
    assert field in str(error.value)


@pytest.mark.parametrize("missing", ["key", "source"])
def test_a_dossier_item_without_key_or_source_names_the_field(tmp_path, missing):
    data = copy.deepcopy(DOSSIER)
    del data["items"][1][missing]
    path = write(tmp_path, "dossier_order.json", data)

    with pytest.raises(ConfigError) as error:
        load_dossier_order(path)

    assert "dossier_order.json" in str(error.value)
    assert f"items[1].{missing}" in str(error.value)


def test_a_dossier_without_items_is_refused(tmp_path):
    path = write(tmp_path, "dossier_order.json", {"items": []})
    with pytest.raises(ConfigError) as error:
        load_dossier_order(path)
    assert "items" in str(error.value)


def test_the_provider_gives_the_template_the_file_marks_as_default():
    config = ReportConfigLoader().load()

    assert config == load_report_config()


def test_the_provider_gives_the_template_of_the_setting_and_refuses_an_unknown_one():
    default = load_report_config()

    assert ReportConfigLoader(default.template.id).load() == default
    with pytest.raises(ConfigError):
        ReportConfigLoader("modelo-que-nao-existe").load()
