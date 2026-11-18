"""SEG-06: a course is an extension course only when "extensão" names its nature."""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import Item, confirm_extension_course, suggest_item

EXTENSION = T.CURSO_EXTENSAO_CONCLUIDO


@pytest.mark.parametrize(
    "text",
    [
        "Formação de 8 horas oferecida entre a Pró-Reitoria de Extensão e as faculdades.",
        "PRÓ-REITORIA DE EXTENSÃO - PROEX. Certificamos que Fulana concluiu a formação.",
        "Diretoria de Extensão da Universidade Exemplo certifica a participação no curso.",
        "Coordenadoria de Extensão. Certificado de participação em oficina.",
        "Centro de Extensão e Núcleo de Extensão Exemplo certificam a formação.",
        "Realizado pela PROEX, com 20 horas de duração.",
        "Pró-Reitor de Extensão assina o certificado de formação docente.",
        "Atividades de ensino, pesquisa e extensão da universidade; curso de formação.",
    ],
)
def test_the_word_inside_a_unit_name_or_a_list_of_missions_is_not_an_extension_course(text):
    assert confirm_extension_course(EXTENSION, text) is T.CURSO_CONCLUIDO


@pytest.mark.parametrize(
    "text",
    [
        "Certificamos que Fulana concluiu o curso de extensão Dados Abertos, 40 horas.",
        "CURSO DE EXTENSAO EM DADOS ABERTOS",
        "Participou da atividade de extensão Governo Digital.",
        "Participou da ação de extensão Governo Digital.",
        "Programa de extensão Cidadania Digital, 60 horas.",
        "Projeto de extensão Cidadania Digital, 60 horas.",
        "Evento de extensão: Semana de Dados Abertos.",
        "Categoria: Extensão. Título: Oficina de dados.",
        "Natureza da ação - Extensão; carga horária 30 h.",
        "Tipo: EXTENSÃO",
        "Minicurso de extensão sobre dados",
    ],
)
def test_extension_in_a_course_context_keeps_the_extension_course(text):
    assert confirm_extension_course(EXTENSION, text) is EXTENSION


def test_a_unit_name_in_the_header_does_not_hide_a_course_context_in_the_body():
    text = (
        "Pró-Reitoria de Extensão - PROEX\n"
        "Certificamos que Fulana concluiu o curso de extensão Dados Abertos."
    )
    assert confirm_extension_course(EXTENSION, text) is EXTENSION


def test_a_course_coordination_that_says_extension_course_is_not_taken_for_a_unit():
    text = "Coordenação do curso de extensão Dados Abertos, 40 horas."
    assert confirm_extension_course(EXTENSION, text) is EXTENSION


def test_the_downgraded_course_gets_item_vii_10_and_the_confirmed_one_vii_9():
    downgraded = confirm_extension_course(EXTENSION, "Pró-Reitoria de Extensão certifica.")
    assert suggest_item(downgraded).principal == Item(7, 10)
    assert suggest_item(EXTENSION).principal == Item(7, 9)


@pytest.mark.parametrize("taxonomy", [t for t in T if t is not EXTENSION])
def test_every_other_type_passes_through(taxonomy):
    assert confirm_extension_course(taxonomy, "Pró-Reitoria de Extensão") is taxonomy
