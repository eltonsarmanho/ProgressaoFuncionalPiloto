"""QUA-01: a label list in one paragraph must not make a member the coordinator.

TER-03 lets a line break stay inside the paragraph, so "Coordenador: A\\nEquipe: B" is one
paragraph. Another role word ("equipe", "pesquisador(a)", "autor(a)", "orientando(a)") or the
full name of another person between the coordination word and the professor refuses the
coordination. A plural role ("coordenadores", "coordenaram") names several people at once.
"""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_research_coordination

PROFESSOR = "Maria de Souza Lima"
HEADER = "Projeto de pesquisa Dados Abertos.\n"
COORDINATION = [T.PESQUISA_PROJETO_COORDENACAO, T.PESQUISA_GRUPO_COORDENACAO]


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        "Coordenador: Pedro Alves\nEquipe: Maria de Souza Lima",
        "Coordenadora: Ana Beltrao\nPesquisadores: Maria de Souza Lima",
        "Coordenadora: Ana Beltrao\nPesquisadora: Maria de Souza Lima",
        "Coordenador: Pedro Alves\nAutores: Maria de Souza Lima",
        "Coordenador: Pedro Alves\nAutora: Maria de Souza Lima",
        "Coordenador: Pedro Alves\nOrientanda: Maria de Souza Lima",
        "Coordenador: Pedro Alves\nOrientando(a): Maria de Souza Lima",
        "Pesquisador(a): Maria de Souza Lima\nCoordenador: Pedro Alves",
    ],
)
def test_another_role_word_between_the_coordinator_and_the_professor_refuses(taxonomy, text):
    assert confirm_research_coordination(taxonomy, HEADER + text, PROFESSOR) is T.OUTRA


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        # no label at all: the full name of another person sits between role and professor
        "Coordenador: Pedro Alves\nMaria de Souza Lima",
        "Coordenador Pedro Alves Maria de Souza Lima",
        "Maria de Souza Lima e Pedro Alves, coordenador do projeto",
        "Coordenadora: Ana Beltrao de Oliveira\nMaria de Souza Lima",
    ],
)
def test_the_full_name_of_another_person_between_them_refuses(taxonomy, text):
    assert confirm_research_coordination(taxonomy, HEADER + text, PROFESSOR) is T.OUTRA


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        "Maria de Souza Lima, da Universidade Federal do Pará, coordenou o projeto.",
        "Maria de Souza Lima, professora do Instituto de Ciências Exatas e Naturais, coordena "
        "o projeto.",
        "Coordenadora: Profa. Dra. Maria de Souza Lima",
        "Coordenadora Prof. Dr. Maria de Souza Lima",
        "Coordenação: Núcleo de Estudos Amazônicos, Maria de Souza Lima",
        "Maria de Souza Lima e Pedro Alves, coordenadores do projeto",
        "Maria de Souza Lima e Pedro Alves coordenaram o projeto",
        "Coordenadores: Pedro Alves e Maria de Souza Lima",
        "Maria de Souza Lima coordenou o projeto, com a Equipe do Núcleo",
    ],
)
def test_institution_names_titles_and_plural_roles_do_not_refuse(taxonomy, text):
    assert confirm_research_coordination(taxonomy, HEADER + text, PROFESSOR) is taxonomy
