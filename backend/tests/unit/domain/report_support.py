"""Synthetic template, group map and activities of the report draft tests."""

from app.domain.entities.report import (
    EntrySpec,
    GroupBy,
    MatchRule,
    ReportTemplate,
    TemplateSection,
)
from app.domain.rules.report_draft import GroupTarget

FIELDS_ENTRY = EntrySpec(
    fields=(("Disciplina", "{title}"), ("Carga horária", "{course_hours}"), ("Período", "{period}"))
)
LINE_ENTRY = EntrySpec(line="{title}[, {dates}][, {hours}]")


def _section(key, title, group_by=GroupBy.NONE, entry=LINE_ENTRY, order_items=False):
    return TemplateSection(key, title, (), group_by, entry, order_items)


def template() -> ReportTemplate:
    return ReportTemplate(
        id="modelo-sintetico",
        version=3,
        sections=(
            _section("1.1", "Ensino de graduação", GroupBy.ACADEMIC_PERIOD, FIELDS_ENTRY),
            _section("1.2", "Ensino de pós-graduação", GroupBy.ACADEMIC_PERIOD, FIELDS_ENTRY),
            _section("1.3", "Orientações", GroupBy.ITEM, order_items=True),
            _section("2", "Pesquisa"),
            _section("3", "Extensão"),
            _section("4", "Administração"),
            _section("5", "Outras atividades"),
            _section("6", "Participações"),
        ),
    )


BANCAS = "Participação em bancas e comissões examinadoras"


def group_map() -> dict[MatchRule, GroupTarget]:
    return {
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
