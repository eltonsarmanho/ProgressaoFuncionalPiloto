"""CLS-01..10: suggested item, candidates, quantity, table and interstice checks."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import ActivitySource, ActivityStatus, Level, initial_status
from app.domain.entities.document import DocAlertCode, DocumentStatus
from app.domain.entities.extraction import TaxonomyCode
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason
from tests.unit.application.analyzer_fakes import (
    FakeAi,
    FakeTextExtractor,
    activity,
    analyzer,
    payload,
    run,
    text_page,
)

DISCIPLINAS_TEXT = (
    "DECLARACAO DE COMPONENTES CURRICULARES\n"
    "Declaramos que Fulana de Tal Exemplo ministrou os componentes curriculares abaixo.\n"
    "2025/1 Algoritmos e Programacao Graduacao CH Docente 60 horas\n"
    "2025/1 Mineracao de Dados Pos-Graduacao CH Docente 45 horas\n"
    "2025/2 Banco de Dados Graduacao CH Docente 30 horas"
)


def course(title, hours, period, level, **changes):
    return activity(
        taxonomy="DISCIPLINA_MINISTRADA",
        title=title,
        role=None,
        event_date=None,
        hours=hours,
        academic_period=period,
        level=level,
        evidence_text=f"{period} {title}",
        **changes,
    )


def table(*items: tuple[int, int]) -> ScoringTableVersion:
    groups = []
    for number in sorted({g for g, _ in items}):
        criteria = tuple(
            ScoringCriterion(g, i, f"item {g}.{i}", "unidade", ScoringMode.POR_UNIDADE)
            for g, i in items
            if g == number
        )
        groups.append(ScoringGroup(number, f"Grupo {number}", criteria=criteria))
    return ScoringTableVersion(
        table_id=None,
        name="Tabela de teste",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Res. teste",
        status=TableStatus.OFICIAL,
        groups=tuple(groups),
    )


def analyze(payload_, text=None, **kwargs):
    page = text_page(1, text) if text else text_page(1)
    result = run(analyzer(FakeTextExtractor(page), FakeAi(payload_)), **kwargs)
    return result


def alert_pairs(result, code):
    return [(a.code, a.activity_index) for a in result.alerts if a.code is code]


# --- CLS-02, CLS-04, CLS-08: the suggested item ---------------------------------------------


def test_tcc_committee_declaration_suggests_item_iii_4_without_candidates():
    result = analyze(payload(activity()))
    found = result.activities[0]
    assert (found.group_number, found.item_number) == (3, 4)
    assert found.candidates == ()
    assert found.reasons == ()
    assert found.source is ActivitySource.SUGERIDA_IA
    assert initial_status(found.source) is ActivityStatus.AGUARDANDO_REVISAO
    assert "Tabela oficial" in found.source_note and "Grupo III, item 4" in found.source_note
    assert found.quantity == Decimal(1)
    assert result.status is DocumentStatus.PROCESSADO


def test_alternatives_become_candidates_without_a_justification():
    text = "Declaramos que Fulana de Tal Exemplo orientou o projeto Estudo Ficticio sobre Dados."
    item = activity(
        taxonomy="ORIENTACAO_PROJETO_INSTITUCIONAL",
        title="Estudo Ficticio sobre Dados",
        event_date=None,
        evidence_text="orientou o projeto",
    )
    found = analyze(payload(item), text).activities[0]
    assert (found.group_number, found.item_number) == (2, 8)
    assert [(c.group_number, c.item_number, c.justification) for c in found.candidates] == [
        (2, 9, "")
    ]


def test_academic_period_and_level_do_not_leak_into_non_course_activities():
    found = analyze(payload(activity())).activities[0]
    assert (found.level, found.academic_period, found.hours) == (None, None, None)


# --- CLS-07: one activity per item, with Group I data ----------------------------------------


def test_course_declaration_with_three_offers_gives_three_group_i_activities():
    offers = [
        course("Algoritmos e Programacao", 60, "2025/1", "GRADUACAO"),
        course("Mineracao de Dados", 45, "2025/1", "POS_GRADUACAO"),
        course("Banco de Dados", 30, "2025/2", "GRADUACAO"),
    ]
    result = analyze(payload(*offers), DISCIPLINAS_TEXT)
    assert len(result.activities) == 3
    got = [
        (a.group_number, a.item_number, a.level, a.academic_period, a.hours, a.quantity)
        for a in result.activities
    ]
    assert got == [
        (1, 1, Level.GRADUACAO, "2025/1", Decimal(60), None),
        (1, 2, Level.POS_GRADUACAO, "2025/1", Decimal(45), None),
        (1, 1, Level.GRADUACAO, "2025/2", Decimal(30), None),
    ]
    assert [a.source_index for a in result.activities] == [0, 1, 2]
    assert result.alerts == ()
    assert all(a.candidates == () for a in result.activities)


def test_course_without_a_level_suggests_i_1_with_i_2_as_candidate():
    offer = course("Algoritmos e Programacao", 60, "2025/1", None)
    found = analyze(payload(offer), DISCIPLINAS_TEXT).activities[0]
    assert (found.group_number, found.item_number) == (1, 1)
    assert [(c.group_number, c.item_number) for c in found.candidates] == [(1, 2)]


# --- CLS-03: types without an item ------------------------------------------------------------


@pytest.mark.parametrize("taxonomy", ["COORIENTACAO_TCC_GRADUACAO", "OUTRA"])
def test_types_without_item_create_no_activity_and_warn_without_review_status(taxonomy):
    result = analyze(payload(activity(taxonomy=taxonomy)))
    assert result.activities == ()
    assert alert_pairs(result, DocAlertCode.SEM_ITEM_DE_PONTUACAO) == [
        (DocAlertCode.SEM_ITEM_DE_PONTUACAO, 0)
    ]
    assert result.status is DocumentStatus.PROCESSADO
    assert result.status_code is None
    assert DocAlertCode.NENHUMA_ATIVIDADE_ENCONTRADA not in [a.code for a in result.alerts]
    assert result.raw_json is not None


def test_only_the_activities_with_an_item_are_created_in_a_mixed_document():
    items = [
        activity(),
        activity(taxonomy="OUTRA"),
        activity(taxonomy="COORIENTACAO_TCC_GRADUACAO"),
    ]
    result = analyze(payload(*items))
    assert [a.source_index for a in result.activities] == [0]
    assert [i for _, i in alert_pairs(result, DocAlertCode.SEM_ITEM_DE_PONTUACAO)] == [1, 2]


def test_internal_training_has_its_item_vii_10():
    found = analyze(payload(activity(taxonomy="TREINAMENTO_INTERNO"))).activities[0]
    assert (found.group_number, found.item_number) == (7, 10)


def test_lecture_is_viii_24_without_alternatives():
    found = analyze(payload(activity(taxonomy="PALESTRA"))).activities[0]
    assert (found.group_number, found.item_number, found.candidates) == (8, 24, ())


# --- CLS-05: item missing from the process table ----------------------------------------------


def test_item_missing_from_the_table_version_has_no_group_or_item_and_the_reason():
    result = analyze(payload(activity()), table_version=table((3, 1), (3, 2)))
    found = result.activities[0]
    assert (found.group_number, found.item_number) == (None, None)
    assert found.reasons == (NotScoredReason.SEM_ENQUADRAMENTO,)
    assert found.extracted.title == "Estudo Ficticio sobre Dados Abertos"  # the activity is kept
    assert found.taxonomy is TaxonomyCode.BANCA_TCC_GRADUACAO


def test_item_present_in_the_table_version_is_chosen_without_a_reason():
    found = analyze(payload(activity()), table_version=table((3, 4))).activities[0]
    assert (found.group_number, found.item_number) == (3, 4)
    assert found.reasons == ()


def test_without_a_table_version_the_item_is_not_checked():
    found = analyze(payload(activity()), table_version=None).activities[0]
    assert (found.group_number, found.reasons) == (3, ())


def test_candidates_absent_from_the_table_are_dropped():
    text = "Declaramos que Fulana de Tal Exemplo orientou o projeto Estudo Ficticio sobre Dados."
    item = activity(
        taxonomy="ORIENTACAO_PROJETO_INSTITUCIONAL",
        title="Estudo Ficticio sobre Dados",
        event_date=None,
        evidence_text="orientou o projeto",
    )
    both = analyze(payload(item), text, table_version=table((2, 8), (2, 9))).activities[0]
    assert [(c.group_number, c.item_number) for c in both.candidates] == [(2, 9)]
    only_principal = analyze(payload(item), text, table_version=table((2, 8))).activities[0]
    assert (only_principal.item_number, only_principal.candidates) == (8, ())


# --- CLS-09: interstice -----------------------------------------------------------------------

INTERSTICE = Interstice(date(2026, 1, 1), date(2027, 1, 1))


def test_date_outside_the_interstice_is_flagged_and_the_activity_is_kept():
    found = analyze(payload(activity()), interstice=INTERSTICE).activities[0]  # 2025-03-12
    assert found.reasons == (NotScoredReason.FORA_DO_INTERSTICIO,)
    assert (found.group_number, found.item_number) == (3, 4)


def test_date_inside_the_interstice_is_not_flagged():
    inside = Interstice(date(2025, 1, 1), date(2025, 12, 31))
    assert analyze(payload(activity()), interstice=inside).activities[0].reasons == ()


def test_date_on_the_last_day_of_the_interstice_is_inside():
    edge = Interstice(date(2024, 3, 12), date(2025, 3, 12))
    assert analyze(payload(activity()), interstice=edge).activities[0].reasons == ()


def test_without_an_interstice_nothing_is_flagged():
    assert analyze(payload(activity()), interstice=None).activities[0].reasons == ()


def test_activity_without_a_grounded_date_is_not_flagged_as_outside():
    found = analyze(payload(activity(event_date="2031-07-04")), interstice=INTERSTICE)
    assert found.activities[0].reasons == ()


def test_a_period_entirely_outside_the_interstice_is_flagged():
    text = "Declaramos que Fulana de Tal Exemplo coordenou o projeto de 01/02/2023 a 31/01/2024."
    item = activity(
        taxonomy="EXTENSAO_PROJETO_COORDENACAO",
        title=None,
        event_date=None,
        start_date="2023-02-01",
        end_date="2024-01-31",
        evidence_text="coordenou o projeto",
    )
    found = analyze(payload(item), text, interstice=INTERSTICE).activities[0]
    assert NotScoredReason.FORA_DO_INTERSTICIO in found.reasons


def test_both_reasons_can_apply_to_the_same_activity():
    found = analyze(
        payload(activity()), interstice=INTERSTICE, table_version=table((3, 1))
    ).activities[0]
    assert found.reasons == (
        NotScoredReason.SEM_ENQUADRAMENTO,
        NotScoredReason.FORA_DO_INTERSTICIO,
    )


# --- CLS-10: extension course -------------------------------------------------------------------

CERTIFICATE = "Certificamos que Fulana de Tal Exemplo concluiu o curso Boas Praticas de Dados {}."


def certificate(extra):
    return activity(
        taxonomy="CURSO_EXTENSAO_CONCLUIDO",
        title="Boas Praticas de Dados",
        event_date=None,
        evidence_text="concluiu o curso",
    ), CERTIFICATE.format(extra)


def test_extension_course_without_the_word_falls_to_vii_10():
    item, text = certificate("com frequencia e aproveitamento")
    found = analyze(payload(item), text).activities[0]
    assert found.taxonomy is TaxonomyCode.CURSO_CONCLUIDO
    assert (found.group_number, found.item_number) == (7, 10)


@pytest.mark.parametrize("word", ["de extensão universitária", "de EXTENSAO"])
def test_extension_course_with_the_word_is_vii_9(word):
    item, text = certificate(word)
    found = analyze(payload(item), text).activities[0]
    assert found.taxonomy is TaxonomyCode.CURSO_EXTENSAO_CONCLUIDO
    assert (found.group_number, found.item_number) == (7, 9)


def test_the_word_extension_on_another_page_counts():
    item, text = certificate("sem a palavra")
    result = run(
        analyzer(
            FakeTextExtractor(text_page(1, text), text_page(2, "Programa de extensão do campus.")),
            FakeAi(payload(item)),
        )
    )
    assert result.activities[0].taxonomy is TaxonomyCode.CURSO_EXTENSAO_CONCLUIDO


# --- CLS-06: quantity and hours by rule ----------------------------------------------------------


def test_course_takes_the_hours_from_the_text_and_counts_one_per_document():
    text = "Declaramos que Fulana de Tal Exemplo ministrou o curso Oficina de Dados, 20 horas."
    item = activity(
        taxonomy="EXTENSAO_CURSO_MINISTRANTE",
        title="Oficina de Dados",
        event_date=None,
        hours=20,
        course_hours=20,
        evidence_text="ministrou o curso",
    )
    found = analyze(payload(item), text).activities[0]
    assert (found.quantity, found.hours, found.course_hours) == (1, Decimal(20), Decimal(20))
    assert (found.group_number, found.item_number) == (4, 4)


def test_per_year_item_counts_whole_years_and_warns_the_estimate():
    text = "Designamos Fulana de Tal Exemplo diretora de 01/01/2023 a 01/01/2025 por portaria."
    item = activity(
        taxonomy="FUNCAO_DIRETOR_FACULDADE",
        title=None,
        event_date=None,
        start_date="2023-01-01",
        end_date="2025-01-01",
        evidence_text="diretora de 01/01/2023",
    )
    result = analyze(payload(item), text)
    assert result.activities[0].quantity == Decimal(2)
    assert alert_pairs(result, DocAlertCode.QUANTIDADE_ESTIMADA) == [
        (DocAlertCode.QUANTIDADE_ESTIMADA, 0)
    ]


def test_quantity_never_comes_from_the_ai_payload():
    result = analyze(payload(activity(hours=999)))  # 999 is not in the text: nulled
    assert result.activities[0].hours is None
    assert result.activities[0].quantity == Decimal(1)


def test_confidence_and_review_flag_survive_classification():
    found = analyze(payload(activity(confidence=0.5))).activities[0]
    assert found.confidence == Decimal("0.50")
    assert found.needs_review is True
