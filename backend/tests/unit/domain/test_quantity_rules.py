"""CLS-06: quantity and hours derived by rule from the extracted fields, never points."""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.activity import Level
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.quantity_rules import QuantityResult, derive_quantity

D = Decimal

BANCAS = [t for t in T if t.value.startswith("BANCA_")]
ORIENTACOES = [t for t in T if "ORIENTACAO" in t.value]
HOUR_BASED = [
    T.EXTENSAO_CURSO_COORDENACAO,
    T.EXTENSAO_CURSO_MINISTRANTE,
    T.EXTENSAO_EVENTO_COORDENACAO,
    T.EXTENSAO_EVENTO_MINISTRANTE,
    T.ESTAGIO_CAPACITACAO,
]
PER_YEAR = [
    T.EXTENSAO_PROJETO_COORDENACAO,
    T.EXTENSAO_PROJETO_PARTICIPACAO,
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
    T.PESQUISA_PROJETO_COORDENACAO,
    T.COMISSAO_ADMINISTRACAO_SUPERIOR,
    T.COMISSAO_NDE_MEMBRO,
    T.COMISSAO_UNIDADE,
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
def test_hour_based_items_carry_the_extracted_hours_and_no_quantity(taxonomy):
    result = derive_quantity(taxonomy, extracted(taxonomy, hours=D("21")))
    assert result.hours == D("21")
    assert result.quantity is None
    assert result.warnings == ()


def test_course_of_21_hours_gives_hours_21():
    result = derive_quantity(
        T.EXTENSAO_CURSO_MINISTRANTE, extracted(T.EXTENSAO_CURSO_MINISTRANTE, hours=D("21"))
    )
    assert result.hours == D("21")


def test_hour_based_item_without_hours_leaves_hours_empty():
    result = derive_quantity(T.ESTAGIO_CAPACITACAO, extracted(T.ESTAGIO_CAPACITACAO))
    assert result.hours is None
    assert result.quantity is None


def test_hour_based_item_does_not_take_the_hours_from_the_course_workload_of_a_discipline():
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
def test_period_under_one_year_counts_as_one_year_with_the_estimate_warning(taxonomy):
    activity = extracted(taxonomy, start_date=date(2022, 8, 1), end_date=date(2023, 7, 31))
    result = derive_quantity(taxonomy, activity)
    assert result.quantity == D(1)
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


def test_exactly_twelve_months_is_one_year_and_one_day_short_is_still_one():
    exact = extracted(T.COLEGIADO_MEMBRO, start_date=date(2022, 8, 15), end_date=date(2023, 8, 15))
    short = extracted(T.COLEGIADO_MEMBRO, start_date=date(2022, 8, 15), end_date=date(2023, 8, 14))
    assert derive_quantity(T.COLEGIADO_MEMBRO, exact).quantity == D(1)
    assert derive_quantity(T.COLEGIADO_MEMBRO, short).quantity == D(1)


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
def test_per_year_item_without_a_usable_period_counts_one_year_with_the_estimate_warning(fields):
    result = derive_quantity(T.PESQUISA_GRUPO_MEMBRO, extracted(T.PESQUISA_GRUPO_MEMBRO, **fields))
    assert result.quantity == D(1)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_result_never_carries_points():
    names = {f.name for f in dataclasses.fields(QuantityResult)}
    assert names == {"quantity", "hours", "level", "academic_period", "warnings"}


def test_every_taxonomy_code_gets_a_result():
    for taxonomy in T:
        assert isinstance(derive_quantity(taxonomy, extracted(taxonomy)), QuantityResult)
