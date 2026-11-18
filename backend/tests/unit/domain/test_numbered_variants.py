"""QUA-05: titles that differ by a numeral or a lone letter on each side are not one activity.

TER-07 merges noisy copies of an activity by Jaccard 0.6 or containment. "Curso de Python Nível 1"
and "Nível 2" have a Jaccard of 0.67 and are two courses (FT-31). A numeral, a Roman numeral or a
capital letter that stands alone on each side tells variants apart; on one side only it is noise.
"""

import pytest

from app.domain.rules.title_similarity import jaccard, repeated_titles


@pytest.mark.parametrize(
    ("one", "two"),
    [
        ("Curso de Python Nível 1", "Curso de Python Nível 2"),
        ("Ensino de Cálculo I Turma A", "Ensino de Cálculo I Turma B"),
        ("Ensino de Cálculo I Turma A", "Ensino de Cálculo II Turma A"),
        ("Oficina de Dados Abertos Módulo III", "Oficina de Dados Abertos Módulo IV"),
        ("Palestra de Gestão Acadêmica Edição 2024", "Palestra de Gestão Acadêmica Edição 2025"),
    ],
)
def test_variants_told_apart_by_a_numeral_or_letter_on_each_side_are_not_repeated(one, two):
    assert jaccard(one, two) >= 0.6  # TER-07 alone would merge them
    assert repeated_titles(one, two) is False


@pytest.mark.parametrize(
    ("one", "two"),
    [
        ("Curso de Python 2025", "Curso de Python"),  # the numeral is on one side only
        ("Curso de Python Nível 1", "Curso de Python Nível 1"),  # the same numeral
        ("RPA na Gestao W A | Academica", "RPA na Gestao Academica"),  # noise, no numeral
        ("Curso de Python Nível 1 Avançado", "Curso de Python Nível 1"),  # contained
    ],
)
def test_a_numeral_on_one_side_only_or_the_same_numeral_still_merges(one, two):
    assert repeated_titles(one, two) is True
