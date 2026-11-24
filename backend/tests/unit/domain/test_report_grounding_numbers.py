"""REL-04: the wording from the AI keeps only the numbers and dates found in the fields sent."""

import pytest

from app.domain.rules.report_grounding import (
    WordingReason,
    WordingVocabulary,
    check_wording,
)

FACTS = {
    "titulo": "Curso de Análise de Dados",
    "datas": "23/11/2024",
    "carga_horaria": "60 h",
    "periodo_letivo": "1º Período de 2023",
}
MODEL_TEXT = "Curso de Análise de Dados, 23/11/2024, 60 h"
VOCABULARY = WordingVocabulary(max_new_words=100)


def check(wording, facts=None):
    return check_wording(wording, FACTS if facts is None else facts, VOCABULARY, MODEL_TEXT)


def test_an_invented_number_of_hours_is_refused_with_the_reason_number():
    result = check("Curso de Análise de Dados com 120 horas.")

    assert result.accepted is False
    assert result.reasons == (WordingReason.NUMERO,)


def test_an_invented_date_is_refused_with_the_reason_date():
    result = check("Curso realizado em 25/12/2024.")

    assert result.accepted is False
    assert result.reasons == (WordingReason.DATA,)


def test_an_invented_number_and_an_invented_date_give_both_reasons():
    result = check("Curso de 120 horas realizado em 25/12/2024.")

    assert result.reasons == (WordingReason.NUMERO, WordingReason.DATA)


@pytest.mark.parametrize(
    "wording",
    [
        "Curso de Análise de Dados, com 60 horas.",
        "Curso de Análise de Dados, 60h.",
        "Curso de Análise de Dados, 60 h de carga horária.",
        "Curso de Análise de Dados com sessenta horas.",
        "Curso de Análise de Dados com 60,0 horas.",
        "Curso de Análise de Dados, carga horária de 060 horas.",
    ],
)
def test_the_hours_of_the_field_are_accepted_in_their_variations(wording):
    result = check(wording)

    assert result.accepted is True
    assert result.reasons == ()


@pytest.mark.parametrize(
    "wording",
    [
        "Realizado no 1º semestre de 2023.",
        "Realizado no primeiro semestre de 2023.",
        "Realizado no 1º Período de 2023.",
        "Realizado no período 2023.1.",
    ],
)
def test_the_academic_period_of_the_field_is_accepted_in_its_variations(wording):
    assert check(wording).accepted is True


@pytest.mark.parametrize(
    "wording",
    [
        "Concluído em 23/11/2024.",
        "Concluído em 23 de novembro de 2024.",
        "Concluído em 23 DE NOVEMBRO DE 2024.",
        "Concluído em vinte e três de novembro de dois mil e vinte e quatro.",
        "Concluído em novembro de 2024.",
        "Concluído em 2024.",
    ],
)
def test_the_date_of_the_field_is_accepted_in_its_variations(wording):
    assert check(wording).accepted is True


@pytest.mark.parametrize(
    "wording",
    [
        "Realizado no segundo semestre de 2023.",
        "Realizado no 2º semestre de 2023.",
        "Realizado no 1º semestre de 2022.",
    ],
)
def test_a_period_that_is_not_in_the_fields_is_refused(wording):
    result = check(wording)

    assert result.accepted is False
    assert result.reasons == (WordingReason.NUMERO,)


def test_a_date_that_does_not_exist_in_the_calendar_is_refused_as_a_date():
    facts = {"datas": "31/02/2024"}

    result = check("Realizado em 31/02/2024.", facts)

    assert result.reasons == (WordingReason.DATA,)


def test_a_month_of_another_year_than_the_field_is_refused():
    assert check("Concluído em novembro de 2023.").reasons == (WordingReason.DATA,)


def test_a_month_of_the_period_field_is_accepted_for_the_month_and_year():
    facts = {"datas": "06/2023 a 11/2023"}

    assert check("De junho de 2023 a novembro de 2023.", facts).accepted is True
    assert check("Até dezembro de 2023.", facts).reasons == (WordingReason.DATA,)


def test_a_decimal_number_is_compared_with_the_comma_of_the_field():
    facts = {"carga_horaria": "7,5 h"}

    assert check("Oficina de 7,5 horas.", facts).accepted is True
    assert check("Oficina de 75 horas.", facts).reasons == (WordingReason.NUMERO,)


def test_a_number_with_thousands_separator_matches_the_plain_number_of_the_field():
    facts = {"carga_horaria": "1200 h"}

    assert check("Formação de 1.200 horas.", facts).accepted is True


def test_a_text_without_numbers_or_dates_is_accepted():
    assert check("Curso de Análise de Dados.").accepted is True


def test_the_article_one_is_not_read_as_the_number_one():
    facts = {"titulo": "Oficina de dados", "carga_horaria": "8 h"}

    assert check("Realizou uma oficina de dados e um curso de 8 horas.", facts).accepted is True


def test_an_accepted_wording_is_returned_as_it_came():
    wording = "Curso de Análise de Dados, com 60 horas."

    assert check(wording).text == wording


def test_a_refused_wording_returns_the_template_text():
    result = check("Curso de Análise de Dados com 120 horas.")

    assert result.text == MODEL_TEXT


def test_the_fields_with_no_numbers_refuse_any_number_in_the_wording():
    result = check("Oficina com 3 encontros.", {"titulo": "Oficina de dados"})

    assert result.reasons == (WordingReason.NUMERO,)
