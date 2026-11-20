"""TER-04: the name of an extension unit confirms neither an extension course nor a project.

"extensão" must describe the nature of the activity; inside the name of the unit that issues
the document it only says who signs. The same rule holds for VII.9 (course) and IV.1/IV.2.
"""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_extension_course, confirm_extension_project

COURSE = T.CURSO_EXTENSAO_CONCLUIDO
PROJECTS = [T.EXTENSAO_PROJETO_COORDENACAO, T.EXTENSAO_PROJETO_PARTICIPACAO]

# Each text has a unit name with "extensão" and nothing that says what the activity is.
UNIT_ONLY = [
    "Coordenadoria de Ações de Extensão certifica a oficina de dados.",
    "Coordenação de Ações de Extensão certifica a oficina de dados.",
    "Diretoria de Extensão certifica a formação.",
    "Diretoria de Ações de Extensão certifica a formação.",
    "Pró-Reitoria de Extensão certifica a formação.",
    "Pró-Reitoria Adjunta de Extensão certifica a formação.",
    "Pró-Reitoria de Pesquisa e Extensão certifica a formação.",
    "Centro de Extensão certifica a formação.",
    "Núcleo de Extensão certifica a formação.",
    "Departamento de Extensão certifica a formação.",
    "Instituto de Extensão certifica a formação.",
    "Instituto de Ações de Extensão certifica a formação.",
    "Universidade Federal Exemplo - Extensão. Certificado de formação.",
    "UNIVERSIDADE FEDERAL EXEMPLO DO NORTE EXTENSÃO UNIVERSITÁRIA certifica a formação.",
    "PROEX - Extensão Universitária certifica a formação.",
    "PROEX/UFPA - Extensão certifica a formação.",
]


@pytest.mark.parametrize("text", UNIT_ONLY)
def test_a_unit_name_does_not_confirm_an_extension_course(text):
    assert confirm_extension_course(COURSE, text) is T.CURSO_CONCLUIDO


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize("text", UNIT_ONLY)
def test_a_unit_name_does_not_confirm_an_extension_project(taxonomy, text):
    assert confirm_extension_project(taxonomy, text) is T.OUTRA


@pytest.mark.parametrize("text", UNIT_ONLY)
def test_a_unit_name_with_the_nature_of_a_course_still_confirms_the_course(text):
    assert confirm_extension_course(COURSE, text + " Curso de extensão Dados Abertos.") is COURSE


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize("text", UNIT_ONLY)
def test_a_unit_name_with_the_nature_of_a_project_still_confirms_the_project(taxonomy, text):
    assert confirm_extension_project(taxonomy, text + " Projeto de extensão Dados Abertos.") is (
        taxonomy
    )


@pytest.mark.parametrize("taxonomy", PROJECTS)
@pytest.mark.parametrize(
    "text",
    [
        "Projeto de Extensão Dados Abertos",
        "Programa de extensão Cidadania Digital",
        "Ação de extensão Governo Digital",
        "Atividade de extensão universitária",
        "Categoria: Extensão",
        "Universidade Federal Exemplo certifica o projeto de extensão Dados Abertos.",
        "Coordenadoria de Ações de Extensão certifica a participação no projeto de extensão X.",
    ],
)
def test_extension_as_the_nature_of_a_project_keeps_it(taxonomy, text):
    assert confirm_extension_project(taxonomy, text) is taxonomy


def test_the_university_name_does_not_swallow_a_course_nature_that_follows_it():
    text = "Universidade Federal Exemplo do Norte curso de extensão Dados Abertos."
    assert confirm_extension_course(COURSE, text) is COURSE
