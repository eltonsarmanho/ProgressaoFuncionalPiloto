"""QUA-04: one test per boundary that the fourth verification found unpinned (FT-32).

Mutants T02, T03, T04, T06 and S16 survived because no test sat on their side of the boundary.
The values below are design choices of TER-07, TER-08 and SEG-07 that the spec words as
"parecido" and "poucas palavras"; each test states the side it fixes.

Mutant S11 (dropping "departamento" from the unit nouns of `suggestion_rules`) is equivalent:
"Departamento de Extensão" never matches the nature wording either way, so it cannot be told
apart by behavior and has no test.
"""

from difflib import SequenceMatcher

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_research_coordination
from app.domain.rules.title_similarity import (
    differ_by_proper_name,
    jaccard,
    repeated_titles,
)

BASE = (
    "Banca examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos "
    "do aluno"
)


def titled(name):
    return f"{BASE} {name}"


def test_titles_with_a_jaccard_between_0_5_and_0_6_are_not_repeated():
    """T02: the threshold is 0.6, not 0.5 (5 of 9 words in common is 0.56)."""
    one = "curso alfa beta gama delta epsilon zeta"
    two = "curso alfa beta gama delta theta iota"
    assert 0.5 < jaccard(one, two) < 0.6
    assert repeated_titles(one, two) is False


def test_titles_with_a_jaccard_of_exactly_0_6_are_repeated():
    one, two = "curso alfa beta gama", "curso alfa beta delta"
    assert jaccard(one, two) == pytest.approx(0.6)
    assert repeated_titles(one, two) is True


def test_a_name_of_three_letters_is_a_proper_name():
    """T03: "Ana" and "Eva" are names, so the two bancas are different activities."""
    assert differ_by_proper_name(titled("Ana"), titled("Eva")) is True
    assert repeated_titles(titled("Ana"), titled("Eva")) is False


def test_a_capitalized_word_of_two_letters_is_not_a_proper_name():
    """T04: "Jo" and "Ze" have two letters: not names, the titles stay alike."""
    assert differ_by_proper_name(titled("Jo"), titled("Ze")) is False
    assert repeated_titles(titled("Jo"), titled("Ze")) is True


def test_two_names_that_are_only_a_little_alike_are_different_names():
    """T06: "Carlos" and "Carla" (ratio 0.73) are two people, not one typo of the OCR."""
    assert 0.7 < SequenceMatcher(None, "carlos", "carla").ratio() < 0.8
    assert differ_by_proper_name(titled("Carlos"), titled("Carla")) is True


@pytest.mark.parametrize("taxonomy", [T.PESQUISA_PROJETO_COORDENACAO, T.PESQUISA_GRUPO_COORDENACAO])
def test_a_vice_coordinator_is_not_the_coordinator(taxonomy):
    """S16: "vice" between the name and the role is another role (SEG-07)."""
    text = "Projeto de pesquisa Dados Abertos. Fulana de Tal Exemplo, vice coordenadora do projeto."
    assert confirm_research_coordination(taxonomy, text, "Fulana de Tal Exemplo") is T.OUTRA
