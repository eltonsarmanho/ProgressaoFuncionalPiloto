"""QUA-03: common wordings of an extension project confirm it (FT-29).

TER-04 asks for "extensão" as the nature of the activity. Wordings that name the nature in
another shape count as well; the name of a unit and a list of missions still do not.
"""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_extension_course, confirm_extension_project

COURSE = T.CURSO_EXTENSAO_CONCLUIDO
PROJECTS = [T.EXTENSAO_PROJETO_COORDENACAO, T.EXTENSAO_PROJETO_PARTICIPACAO]

NATURE_WORDINGS = [
    "Projeto Institucional de Extensão Dados Abertos",
    "Programa institucional de extensão Cidadania Digital",
    "Projeto de pesquisa e extensão Dados Abertos",
    "Projeto de ensino, pesquisa e extensão Dados Abertos",
    "Projeto de pesquisa, ensino e extensão Dados Abertos",
    "Extensão: projeto Dados Abertos",
    "Atividade extensionista Dados Abertos",
    "Projeto extensionista Dados Abertos",
]

NOT_NATURE = [
    "Pró-Reitoria de Pesquisa e Extensão certifica a formação.",
    "Universidade Federal Exemplo - Ensino, Pesquisa e Extensão. Projeto Dados Abertos.",
    "A instituição cumpre as missões de ensino, pesquisa e extensão: projeto de dados.",
    "Diretoria de Extensão certifica o projeto Dados Abertos.",
    "Atividades de ensino, pesquisa e extensão da universidade; projeto de dados.",
]


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize("text", NATURE_WORDINGS)
def test_a_common_wording_of_the_nature_confirms_the_project(taxonomy, text):
    assert confirm_extension_project(taxonomy, text) is taxonomy


@pytest.mark.parametrize("text", NATURE_WORDINGS)
def test_a_common_wording_of_the_nature_confirms_the_course(text):
    assert confirm_extension_course(COURSE, text) is COURSE


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize("text", NOT_NATURE)
def test_a_unit_name_or_a_list_of_missions_still_confirms_no_project(taxonomy, text):
    assert confirm_extension_project(taxonomy, text) is T.OUTRA


@pytest.mark.parametrize("text", NOT_NATURE)
def test_a_unit_name_or_a_list_of_missions_still_confirms_no_course(text):
    assert confirm_extension_course(COURSE, text) is T.CURSO_CONCLUIDO
