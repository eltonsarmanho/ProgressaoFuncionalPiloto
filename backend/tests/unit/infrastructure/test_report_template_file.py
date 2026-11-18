"""REL-01, REL-02, REL-12: the institutional report template that ships with the system."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity
from app.domain.entities.report import GroupBy, MatchRule
from app.domain.rules.report_draft import GroupTarget, group_target, template_text
from app.infrastructure.documents.config_loader import REPORT_TEMPLATES, load_report_config

SEED = Path(__file__).parents[3] / "app/infrastructure/database/seed_data/ufpa.json"
BANCAS = "Participação em bancas e comissões examinadoras"


@pytest.fixture(scope="module")
def config():
    return load_report_config()


def test_the_loader_accepts_the_file_and_the_template_is_the_default_one(config):
    assert json.loads(REPORT_TEMPLATES.read_text(encoding="utf-8"))["default"] == "ufpa-modelo-2"
    assert config.template.id == "ufpa-modelo-2"
    assert config.template.version == 1
    assert config.layout.entry_style == "campos"


def test_the_eight_sections_come_in_the_order_of_the_model(config):
    assert [s.key for s in config.template.sections] == [
        "1.1", "1.2", "1.3", "2", "3", "4", "5", "6",
    ]  # fmt: skip
    by_key = {s.key: s for s in config.template.sections}
    assert by_key["1.1"].group_by is GroupBy.ACADEMIC_PERIOD
    assert by_key["1.2"].group_by is GroupBy.ACADEMIC_PERIOD
    assert by_key["1.3"].group_by is GroupBy.ITEM
    assert by_key["1.3"].order_items is True


def test_the_group_map_is_the_one_of_the_spec(config):
    assert config.group_map == {
        MatchRule(1, 1): GroupTarget("1.1"),
        MatchRule(1, 2): GroupTarget("1.2"),
        MatchRule(2): GroupTarget("1.3"),
        MatchRule(3): GroupTarget("6", BANCAS),
        MatchRule(4): GroupTarget("3"),
        MatchRule(5): GroupTarget("2"),
        MatchRule(6): GroupTarget("4"),
        MatchRule(7): GroupTarget("6", "Capacitação"),
        MatchRule(8): GroupTarget("6"),
    }
    assert not any(t.section_key == "5" for t in config.group_map.values())


def test_every_item_of_the_official_table_has_a_section(config):
    table = json.loads(SEED.read_text(encoding="utf-8"))
    pairs = [(g["number"], c["item_number"]) for g in table["groups"] for c in g["criteria"]]
    assert pairs
    for group, item in pairs:
        activity = Activity(
            id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=group,
            item_number=item, title="t", quantity=Decimal("1"),
        )  # fmt: skip
        assert group_target(config.group_map, activity) is not None, (group, item)


def test_the_page_is_a4_with_the_margins_and_the_font_of_the_model(config):
    page = config.layout.page
    assert (page.size, page.font_name, page.font_size_pt) == ("A4", "Times New Roman", 9)
    assert (page.margin_left_mm, page.margin_right_mm) == (31.75, 31.75)
    assert (page.margin_top_mm, page.margin_bottom_mm) == (25.4, 25.4)


def test_the_header_is_institutional_and_the_identification_names_professor_and_interstice(config):
    layout = config.layout
    assert layout.header_lines == (
        "Serviço Público Federal",
        "Universidade Federal do Pará",
        "{unit_name}",
    )
    assert layout.title == "RELATÓRIO DE ATIVIDADES"
    assert layout.body_heading == "ATIVIDADES DESENVOLVIDAS"
    joined = "\n".join(layout.identification)
    for marker in ("{professor_name}", "{current_class}", "{current_level}", "{unit_name}"):
        assert marker in joined
    assert "{interstice}" in joined


def test_the_forbidden_words_cover_goals_results_and_judgments_of_value(config):
    forbidden = set(config.vocabulary.forbidden_words)
    assert {
        "objetivo", "resultado", "metodologia", "excelente", "relevante", "visando", "contribuindo",
    } <= forbidden  # fmt: skip


def test_the_vocabulary_is_broad_and_the_limit_of_new_words_is_small(config):
    vocabulary = config.vocabulary
    assert len(vocabulary.formal_vocabulary) >= 100
    assert {"realizou", "ministrou", "participou", "concluída"} <= set(vocabulary.formal_vocabulary)
    assert not set(vocabulary.formal_vocabulary) & set(vocabulary.forbidden_words)
    assert "UFPA" in vocabulary.allowed_terms
    assert 0 < vocabulary.max_new_words <= 3


def test_the_entry_of_the_graduation_section_writes_the_fields_the_activity_has(config):
    section = config.template.section("1.1")
    activity = Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=1, item_number=1,
        title="Cálculo Diferencial", quantity=Decimal("1"), course_hours=Decimal("60"),
        academic_period="2023.1",
    )  # fmt: skip

    assert template_text(section.entry, activity) == (
        "Disciplina: Cálculo Diferencial\nCarga horária: 60 h\nPeríodo: 1º Período de 2023"
    )
