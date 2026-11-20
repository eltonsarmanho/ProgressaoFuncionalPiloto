"""TER-03: the coordination word and the professor's name must be a few words apart (at most 8).

The spec says the name sits "a poucas palavras" of the role; the window is 8 words in the same
paragraph (a line break inside a paragraph does not separate them, a blank line or the end of a
sentence does).
"""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_research_coordination

PROFESSOR = "Fulana de Tal Exemplo"
NAME = "Fulana de Tal Exemplo"
FILLER = "alfa beta gama delta epsilon zeta eta theta iota kappa".split()
HEADER = "Projeto de pesquisa Dados Abertos.\n\n"  # speaks of research, in another paragraph
COORDINATION = [T.PESQUISA_PROJETO_COORDENACAO, T.PESQUISA_GRUPO_COORDENACAO]


def kept(text, taxonomy=T.PESQUISA_PROJETO_COORDENACAO):
    return confirm_research_coordination(taxonomy, text, PROFESSOR) is taxonomy


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        f"{NAME} coordenou o projeto de pesquisa Dados Abertos.",
        f"O projeto de pesquisa Dados Abertos teve como coordenadora a professora {NAME}.",
        f"{NAME} lidera o grupo de pesquisa Dados e Sociedade.",
        f"{NAME} liderou o grupo de pesquisa Dados e Sociedade.",
        f"A professora {NAME} é a líder do grupo de pesquisa Dados e Sociedade.",
        f"{NAME} é responsável pelo projeto de pesquisa Dados Abertos.",
        f"{NAME} é a responsável pelo grupo de pesquisa Dados e Sociedade.",
        f"{NAME} atua como coordenadora do projeto de pesquisa.",
        f"{NAME} coordena o projeto de pesquisa Dados Abertos.",
    ],
)
def test_each_coordination_word_next_to_the_name_keeps_the_item(taxonomy, text):
    assert confirm_research_coordination(taxonomy, text, PROFESSOR) is taxonomy


def test_the_window_is_eight_words_before_and_after_the_name():
    for gap, accepted in ((8, True), (9, False)):
        after = f"{NAME} {' '.join(FILLER[:gap])} coordenou o projeto."
        before = f"Coordenou {' '.join(FILLER[:gap])} {NAME}."
        assert kept(HEADER + after) is accepted, f"role after the name, {gap} words apart"
        assert kept(HEADER + before) is accepted, f"role before the name, {gap} words apart"


def test_a_line_break_inside_the_paragraph_does_not_separate_the_name_and_the_role():
    assert kept(f"{HEADER}Fulana de Tal\nExemplo coordenou\no projeto de pesquisa.")
    assert kept(f"{HEADER}Nome: {NAME}\nFunção: coordenadora\ndo projeto")


def test_a_blank_line_or_the_end_of_a_sentence_separates_them():
    assert not kept(f"{HEADER}{NAME}\n\ncoordenou o projeto de pesquisa.")
    assert not kept(f"{HEADER}{NAME} participou. Beltrana Silva coordenou o projeto.")


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        # another person coordinates in the same sentence, the professor far away
        "Beltrana Silva coordenou o projeto de pesquisa Dados Abertos que contou com dez "
        f"bolsistas e a participação de {NAME}.",
        # another person coordinates, the professor is a participant, in two sentences
        f"Beltrana Silva coordenou o projeto de pesquisa. {NAME} participou como bolsista.",
        # a label list on consecutive lines: the member is not the coordinator
        f"Projeto de pesquisa\nCoordenador: Beltrano Silva\nMembros: {NAME}",
        f"Projeto de pesquisa\nCoordenadora: Beltrana Silva\nColaboradora: {NAME}",
        # "coordenado por" names the other person
        f"O projeto de pesquisa, coordenado por Beltrana Silva, teve a participação de {NAME}.",
        # a unit is not a role
        f"A Coordenadoria de Pesquisa certifica que {NAME} participou do projeto.",
        # no research wording at all
        f"{NAME} coordenou o curso de línguas.",
    ],
)
def test_someone_else_coordinating_or_the_professor_only_taking_part_has_no_item(taxonomy, text):
    assert confirm_research_coordination(taxonomy, text, PROFESSOR) is T.OUTRA
