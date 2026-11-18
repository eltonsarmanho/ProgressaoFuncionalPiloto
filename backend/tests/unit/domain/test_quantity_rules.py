"""CLS-06: quantity and hours derived by rule from the extracted fields, never points."""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import Level
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.interstice import Interstice
from app.domain.rules.quantity_rules import QuantityResult, derive_quantity

D = Decimal

BANCAS = [t for t in T if t.value.startswith("BANCA_")]
ORIENTACOES = [t for t in T if "ORIENTACAO" in t.value]
HOUR_BASED = [T.ESTAGIO_CAPACITACAO]
PER_DOCUMENT_WITH_HOURS = [
    T.EXTENSAO_CURSO_COORDENACAO,
    T.EXTENSAO_CURSO_MINISTRANTE,
    T.EXTENSAO_EVENTO_COORDENACAO,
    T.EXTENSAO_EVENTO_MINISTRANTE,
]
# VER-12: IV.1 and IV.2 are "por ação" in the official table (one each); V.1, VI.10 and VI.12
# are "por ano de exercício".
PER_YEAR = [
    T.PESQUISA_PROJETO_COORDENACAO,
    T.COMISSAO_ADMINISTRACAO_SUPERIOR,
    T.COMISSAO_NDE_MEMBRO,
    T.COMISSAO_UNIDADE,
    T.PESQUISA_GRUPO_COORDENACAO,
    T.PESQUISA_GRUPO_MEMBRO,
    T.PESQUISA_BOLSA_PRODUTIVIDADE,
    T.FUNCAO_DIRETOR_FACULDADE,
    T.FUNCAO_VICE_DIRETOR_FACULDADE,
    T.FUNCAO_COORDENADOR_CURSO_GRADUACAO,
    T.COLEGIADO_MEMBRO,
    T.CONSULTORIA_AD_HOC,
]
ONE_UNIT = [
    T.EXTENSAO_PROJETO_COORDENACAO,
    T.EXTENSAO_PROJETO_PARTICIPACAO,
    T.CURSO_ESPECIALIZACAO_CONCLUIDO,
    T.CURSO_APERFEICOAMENTO_CONCLUIDO,
    T.CURSO_EXTENSAO_CONCLUIDO,
    T.CURSO_CONCLUIDO,
    T.PARTICIPACAO_EVENTO,
    T.TREINAMENTO_INTERNO,
    T.LIVRO_COM_PARECERISTAS,
    T.ARTIGO_NAO_INDEXADO,
    T.PALESTRA,
    T.PATENTE_CONCEDIDA,
    T.REGISTRO_SOFTWARE,
    T.OUTRA,
]


def extracted(taxonomy: T, **fields) -> ExtractedActivity:
    return ExtractedActivity(
        taxonomy=taxonomy, page=1, evidence_text="trecho", confidence=D("0.9"), **fields
    )


@pytest.mark.parametrize("taxonomy", BANCAS + ORIENTACOES)
def test_banca_and_orientacao_have_quantity_one(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy, event_date=date(2025, 3, 10)))
    assert result.quantity == D(1)
    assert result.hours is None
    assert result.warnings == ()


@pytest.mark.parametrize("taxonomy", ONE_UNIT)
def test_everything_else_has_quantity_one(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy, hours=D("40")))
    assert result.quantity == D(1)
    assert result.hours is None
    assert result.warnings == ()


@pytest.mark.parametrize("taxonomy", HOUR_BASED)
def test_only_the_training_internship_is_hour_based(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy, hours=D("60")))
    assert result.hours == D("60")
    assert result.quantity is None
    assert result.warnings == ()


@pytest.mark.parametrize("taxonomy", PER_DOCUMENT_WITH_HOURS)
def test_courses_and_events_count_one_per_document_and_keep_the_hours(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy, hours=D("21")))
    assert result.quantity == D(1)
    assert result.hours == D("21")
    assert result.warnings == ()


def test_course_of_21_hours_gives_quantity_1_and_hours_21():
    result = derive_quantity(
        T.EXTENSAO_CURSO_MINISTRANTE, extracted(T.EXTENSAO_CURSO_MINISTRANTE, hours=D("21"))
    )
    assert (result.quantity, result.hours) == (D(1), D("21"))


def test_coordinated_event_counts_one_without_hours_being_required():
    result = derive_quantity(
        T.EXTENSAO_EVENTO_COORDENACAO, extracted(T.EXTENSAO_EVENTO_COORDENACAO)
    )
    assert (result.quantity, result.hours) == (D(1), None)


@pytest.mark.parametrize("taxonomy", PER_DOCUMENT_WITH_HOURS)
def test_course_or_event_without_hours_still_counts_one_and_leaves_hours_empty(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy))
    assert (result.quantity, result.hours) == (D(1), None)


def test_internship_without_hours_leaves_hours_and_quantity_empty():
    result = derive_quantity(T.ESTAGIO_CAPACITACAO, extracted(T.ESTAGIO_CAPACITACAO))
    assert result.hours is None
    assert result.quantity is None


def test_course_hours_are_not_taken_from_the_course_workload_of_a_discipline():
    activity = extracted(T.EXTENSAO_EVENTO_MINISTRANTE, hours=D("3"), course_hours=D("60"))
    assert derive_quantity(T.EXTENSAO_EVENTO_MINISTRANTE, activity).hours == D("3")


def test_discipline_hours_are_the_teaching_workload_with_level_and_period_preserved():
    activity = extracted(
        T.DISCIPLINA_MINISTRADA,
        hours=D("60"),
        course_hours=D("90"),
        level=Level.POS_GRADUACAO,
        academic_period="2025.1",
    )
    result = derive_quantity(T.DISCIPLINA_MINISTRADA, activity)
    assert result.hours == D("60")
    assert result.level is Level.POS_GRADUACAO
    assert result.academic_period == "2025.1"
    assert result.quantity is None
    assert result.warnings == ()


def test_discipline_in_graduation_keeps_its_level():
    activity = extracted(T.DISCIPLINA_MINISTRADA, hours=D("45"), level=Level.GRADUACAO)
    assert derive_quantity(T.DISCIPLINA_MINISTRADA, activity).level is Level.GRADUACAO


def test_discipline_without_level_or_period_leaves_them_empty():
    result = derive_quantity(
        T.DISCIPLINA_MINISTRADA, extracted(T.DISCIPLINA_MINISTRADA, hours=D("45"))
    )
    assert result.level is None
    assert result.academic_period is None


@pytest.mark.parametrize("taxonomy", PER_YEAR)
def test_period_under_one_year_gives_zero_years_with_the_estimate_warning(taxonomy):
    # REAL-11: a few months of exercise never round up to a full year of "por ano de exercício"
    activity = extracted(taxonomy, start_date=date(2022, 8, 1), end_date=date(2023, 7, 31))
    result = derive_quantity(taxonomy, activity)
    assert result.quantity == D(0)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


@pytest.mark.parametrize("taxonomy", PER_YEAR)
def test_two_whole_years_give_quantity_two_with_the_estimate_warning(taxonomy):
    activity = extracted(taxonomy, start_date=date(2022, 8, 1), end_date=date(2024, 8, 1))
    result = derive_quantity(taxonomy, activity)
    assert result.quantity == D(2)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_year_count_keeps_only_whole_years():
    activity = extracted(T.COLEGIADO_MEMBRO, start_date=date(2022, 8, 1), end_date=date(2025, 2, 1))
    assert derive_quantity(T.COLEGIADO_MEMBRO, activity).quantity == D(2)


def test_exactly_twelve_months_is_one_year_and_one_day_short_is_zero():
    exact = extracted(T.COLEGIADO_MEMBRO, start_date=date(2022, 8, 15), end_date=date(2023, 8, 15))
    short = extracted(T.COLEGIADO_MEMBRO, start_date=date(2022, 8, 15), end_date=date(2023, 8, 14))
    assert derive_quantity(T.COLEGIADO_MEMBRO, exact).quantity == D(1)
    assert derive_quantity(T.COLEGIADO_MEMBRO, short).quantity == D(0)


def test_three_years_and_one_day_short_gives_two():
    activity = extracted(
        T.FUNCAO_DIRETOR_FACULDADE, start_date=date(2021, 3, 10), end_date=date(2024, 3, 9)
    )
    assert derive_quantity(T.FUNCAO_DIRETOR_FACULDADE, activity).quantity == D(2)


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"start_date": date(2022, 8, 1)},
        {"end_date": date(2024, 8, 1)},
        {"start_date": date(2024, 8, 1), "end_date": date(2022, 8, 1)},
    ],
)
def test_per_year_item_without_a_usable_period_gives_zero_with_the_estimate_warning(fields):
    # REAL-11: with no usable period the quantity stays 0 for the user to inform
    result = derive_quantity(T.PESQUISA_GRUPO_MEMBRO, extracted(T.PESQUISA_GRUPO_MEMBRO, **fields))
    assert result.quantity == D(0)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_result_never_carries_points():
    names = {f.name for f in dataclasses.fields(QuantityResult)}
    assert names == {"quantity", "hours", "level", "academic_period", "warnings"}


def test_every_taxonomy_code_gets_a_result():
    for taxonomy in T:
        assert isinstance(derive_quantity(taxonomy, extracted(taxonomy)), QuantityResult)


# --- REAL-11: years of exercise inside the interstice -------------------------------------------

INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))


def test_three_months_of_a_function_in_the_interstice_give_zero_with_the_warning():
    # a designation from 09/08/2026 to the end of the interstice (real corpus shape)
    activity = extracted(
        T.FUNCAO_VICE_DIRETOR_FACULDADE, start_date=date(2026, 8, 9), end_date=date(2026, 11, 23)
    )
    result = derive_quantity(T.FUNCAO_VICE_DIRETOR_FACULDADE, activity, INTERSTICE)
    assert result.quantity == D(0)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_years_are_counted_inside_the_interstice_only():
    # four years of mandate, of which exactly the two years of the interstice count
    activity = extracted(
        T.FUNCAO_DIRETOR_FACULDADE, start_date=date(2023, 8, 9), end_date=date(2027, 8, 9)
    )
    result = derive_quantity(T.FUNCAO_DIRETOR_FACULDADE, activity, INTERSTICE)
    assert result.quantity == D(2)


def test_a_period_wholly_outside_the_interstice_gives_zero():
    activity = extracted(
        T.COLEGIADO_MEMBRO, start_date=date(2020, 1, 1), end_date=date(2023, 1, 1)
    )
    result = derive_quantity(T.COLEGIADO_MEMBRO, activity, INTERSTICE)
    assert result.quantity == D(0)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_whole_years_inside_the_interstice_are_floored():
    activity = extracted(
        T.PESQUISA_GRUPO_MEMBRO, start_date=date(2025, 2, 1), end_date=date(2026, 11, 1)
    )
    assert derive_quantity(T.PESQUISA_GRUPO_MEMBRO, activity, INTERSTICE).quantity == D(1)


def test_the_interstice_does_not_change_items_that_are_not_per_year():
    activity = extracted(T.PALESTRA, event_date=date(2025, 3, 10))
    assert derive_quantity(T.PALESTRA, activity, INTERSTICE).quantity == D(1)
