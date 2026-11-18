"""TAB-04, TAB-05, TAB-06: totals, counters, PIT hours and alerts of the scoring table document."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.scoring import ScoringCriterion, ScoringMode
from app.domain.rules.process_verification import Alert, Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.table_document import TableHeader, build_table_document
from tests.unit.domain.scenario_211 import (
    INTERSTICE,
    activity,
    official_like_table,
    per_unit,
    scenario_result,
)

HEADER = TableHeader(
    professor_name="Maria Docente da Silva",
    current_class="Adjunto",
    current_level=2,
    target_class="Associado",
    target_level=1,
    unit_name="Faculdade de Testes",
    interstice=INTERSTICE,
)


def build(activities=None, version=None, listed=None, process_alerts=()):
    version, activities, result = scenario_result(activities, version)
    shown = activities if listed is None else listed
    document = build_table_document(HEADER, version, result, shown, {}, process_alerts)
    return document, result


def without_pit_group():
    version = official_like_table()
    plain = replace(version.groups[0], counts_in_total=True, criteria=(per_unit(1, 1, "1"),))
    return replace(version, groups=(plain, *version.groups[1:]))


# --- total and counters (TAB-04) ------------------------------------------------------------


def test_the_total_of_the_211_scenario_is_the_engine_total():
    document, result = build()

    assert result.total == Decimal("211")
    assert document.total == "211,00"


def test_the_counters_are_the_ones_of_the_engine_result():
    pending = activity(2, 7, title="Sugerida", status=ActivityStatus.AGUARDANDO_REVISAO)
    late = activity(2, 7, title="Antiga", event_date=date(2019, 1, 1))
    bare = activity(3, 2, title="Sem prova", evidence_note=None)
    validated = [activity(2, 3), bare]

    document, result = build(
        activities=validated + [pending, late], version=official_like_table(), listed=validated
    )

    assert document.counters == result.counters
    assert (result.counters.pending, result.counters.not_scored) == (1, 1)
    assert document.counters.activities == 4


# --- PIT hours in a separate section (TAB-05) -----------------------------------------------


def test_the_pit_hours_of_the_scenario_are_24_24_24_and_20_with_a_total_of_92():
    document, _ = build()

    hours = document.pit_hours

    assert [h.hours for h in hours.periods] == ["24,00", "24,00", "24,00", "20,00"]
    assert hours.total == "92,00"


def test_each_pit_period_is_written_as_the_academic_period():
    document, _ = build()

    assert [h.label for h in document.pit_hours.periods] == [
        "1º Período de 2023",
        "2º Período de 2023",
        "3º Período de 2023",
        "4º Período de 2023",
    ]


def test_the_pit_hours_are_not_added_to_the_points():
    document, result = build()

    assert document.total == "211,00"
    assert sum(Decimal(b.subtotal.replace(",", ".")) for b in document.bands) == result.total


def test_a_table_without_a_pit_group_has_no_hours_section():
    document, _ = build(activities=[activity(2, 3)], version=without_pit_group())

    assert document.pit_hours is None


def test_a_pit_table_with_no_offer_has_a_section_with_zero_hours():
    document, _ = build(activities=[activity(2, 3)])

    assert document.pit_hours.periods == ()
    assert document.pit_hours.total == "0,00"


# --- alerts of the scoring (TAB-06) ---------------------------------------------------------


def limited_table():
    version = official_like_table()
    capped = replace(version.groups[1].criteria[1], max_points=Decimal("40"))
    group_two = replace(version.groups[1], criteria=(version.groups[1].criteria[0], capped))
    return replace(version, groups=(version.groups[0], group_two, *version.groups[2:]))


def test_a_limit_applied_appears_with_the_text_of_the_engine():
    a = activity(2, 7, "10", title="Muitas orientações")

    document, result = build(activities=[a], version=limited_table())

    engine_texts = [adj.alert.message for adj in result.limit_adjustments]
    shown = [x.message for x in document.alerts if x.code == "LIMITE_APLICADO"]
    assert engine_texts == ["Limite aplicado em critério 2.7: 160 pontos reduzidos para 40."]
    assert shown == engine_texts


def test_an_activity_limit_is_written_once_not_twice():
    capped = ScoringCriterion(
        2, 7, "Valor informado", "unidade", ScoringMode.VALOR_INFORMADO, max_points=Decimal("10")
    )
    version = official_like_table()
    group_two = replace(version.groups[1], criteria=(version.groups[1].criteria[0], capped))
    table = replace(version, groups=(version.groups[0], group_two, *version.groups[2:]))
    a = activity(2, 7, informed_points=Decimal("25"), title="Pontos informados")

    document, result = build(activities=[a], version=table)

    texts = [x.message for x in document.alerts if x.code == "LIMITE_APLICADO"]
    assert [adj.scope for adj in result.limit_adjustments] == ["ATIVIDADE"]
    assert texts == [result.limit_adjustments[0].alert.message]


def test_a_group_limit_appears_with_the_text_of_the_engine():
    version = official_like_table()
    group_three = replace(version.groups[2], max_points=Decimal("5"))
    table = replace(version, groups=(*version.groups[:2], group_three, *version.groups[3:]))

    document, result = build(activities=[activity(3, 2)], version=table)

    assert [x.message for x in document.alerts] == [
        "Limite aplicado em grupo 3: 7 pontos reduzidos para 5."
    ]
    assert result.limit_adjustments[0].scope == "GRUPO"


def test_an_end_date_missing_appears_with_the_text_of_the_engine():
    yearly = ScoringCriterion(
        6, 6, "Coordenação", "por ano de exercício", ScoringMode.POR_UNIDADE,
        unit_points=Decimal("10"),
    )  # fmt: skip
    version = official_like_table()
    group_six = replace(version.groups[5], criteria=(yearly,))
    table = replace(version, groups=(*version.groups[:5], group_six, *version.groups[6:]))
    open_ended = activity(
        6, 6, "5", title="Coordenação de curso", event_date=None, period_start=date(2022, 12, 1)
    )

    document, result = build(activities=[open_ended], version=table)

    row = result.rows[0]
    assert [a.code for a in row.alerts] == [ScoringAlertCode.DATA_FIM_AUSENTE]
    shown = [x for x in document.alerts if x.code == "DATA_FIM_AUSENTE"]
    assert [x.message for x in shown] == [row.alerts[0].message]
    assert shown[0].subject == "Coordenação de curso"


def test_an_insufficient_course_load_appears_with_the_text_of_the_screen():
    course = ScoringCriterion(
        4, 4, "Curso de extensão", "por bloco", ScoringMode.POR_UNIDADE,
        unit_points=Decimal("2"), min_hours=Decimal("30"),
    )  # fmt: skip
    version = official_like_table()
    group_four = replace(version.groups[3], criteria=(course,))
    table = replace(version, groups=(*version.groups[:3], group_four, *version.groups[4:]))
    short = activity(4, 4, title="Curso curto", hours=Decimal("10"))

    document, _ = build(activities=[short], version=table)

    shown = [x for x in document.alerts if x.code == "CARGA_HORARIA_INSUFICIENTE"]
    assert [(x.message, x.subject) for x in shown] == [
        ("Carga horária abaixo do mínimo do item", "Curso curto")
    ]


def test_an_activity_out_of_the_interstice_is_explained_by_its_reason():
    late = activity(2, 7, title="Antiga", event_date=date(2019, 1, 1))

    document, _ = build(activities=[late])

    assert [(x.code, x.message, x.subject) for x in document.alerts] == [
        ("FORA_DO_INTERSTICIO", "Fora do interstício", "Antiga")
    ]


def test_alerts_of_activities_left_out_of_the_document_are_not_listed():
    late = activity(2, 7, title="Antiga", event_date=date(2019, 1, 1))
    kept = activity(3, 2, title="Na lista")

    document, _ = build(activities=[late, kept], listed=[kept])

    assert document.alerts == ()


def test_a_clean_scenario_has_no_alerts():
    document, _ = build()

    assert document.alerts == ()


def test_the_alerts_of_the_process_are_listed_with_the_text_of_the_screen():
    given = Alert(
        ScoringAlertCode.TABELA_PENDENTE_VALIDACAO,
        Severity.ALERTA,
        "A tabela escolhida ainda não foi validada.",
        "Res. de teste",
    )

    document, _ = build(activities=[activity(3, 2)], process_alerts=[given])

    assert [(x.code, x.message, x.subject) for x in document.alerts] == [
        ("TABELA_PENDENTE_VALIDACAO", "A tabela escolhida ainda não foi validada.", None)
    ]
