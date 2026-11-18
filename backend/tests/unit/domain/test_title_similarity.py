"""TER-08: titles of one item that differ by a proper name are different activities.

Two bancas of the same item and day whose titles differ only by the name of the student or of
the board member have a Jaccard similarity of 0.82 to 0.89 (SEG-04 would call them duplicates).
A capitalized word of three letters or more on each side with no alike word on the other side
is a name: the activities are kept apart. A typo ("Academica"/"Academia"), a lowercase word or
an extra word on one side only is not.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity
from app.domain.rules.scoring_duplicates import find_duplicates
from app.domain.rules.title_similarity import differ_by_proper_name, jaccard, similar_titles

BASE = (
    "Banca examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos "
    "do aluno"
)


def titled(name):
    return f"{BASE} {name}"


def test_the_pair_of_the_verification_has_a_jaccard_between_0_8_and_0_9():
    assert 0.8 <= jaccard(titled("Joao"), titled("Maria")) < 0.9


@pytest.mark.parametrize(
    ("one", "two"),
    [
        (titled("Joao"), titled("Maria")),
        (titled("Joao Pedro"), titled("Maria Clara")),
        (titled("Joao Silva"), titled("Maria Silva")),  # one name in common is not enough
        (titled("JOAO"), titled("MARIA")),  # all capitals
        (titled("Joao"), titled("Beatriz")),
    ],
)
def test_a_proper_name_on_each_side_makes_the_titles_different(one, two):
    assert differ_by_proper_name(one, two) is True
    assert similar_titles(one, two) is False


@pytest.mark.parametrize(
    ("one", "two"),
    [
        (titled("Joao"), titled("Joao")),  # the same title
        (titled("Joao"), titled("Joaoo")),  # a typo of the OCR
        (
            "Estudo Ficticio sobre a Gestao Academica de Cursos Superiores Publicos Brasileiros",
            "Estudo Ficticio sobre a Gestao Academia de Cursos Superiores Publicos Brasileiros",
        ),
        (titled("Joao"), titled("joao pedro")),  # the extra word is on one side only
        (titled("Joao"), titled("maria")),  # lowercase: not read as a name
        (titled("Joao"), titled("Joao e")),  # a one-letter word is not a name
    ],
)
def test_alike_titles_are_still_similar(one, two):
    assert differ_by_proper_name(one, two) is False
    assert similar_titles(one, two) is True


def test_titles_below_the_threshold_are_not_similar():
    assert similar_titles("Oficina de dados abertos", "Palestra sobre inteligencia") is False


def activity(title, **fields):
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        title=title,
        created_by=uuid4(),
        group_number=3,
        item_number=4,
        event_date=date(2025, 3, 12),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        **fields,
    )


def test_two_bancas_of_the_same_item_and_day_of_different_students_are_not_duplicates():
    one, two = activity(titled("Joao")), activity(titled("Maria"))
    assert find_duplicates([one, two]) == set()


def test_a_banca_repeated_with_an_ocr_typo_is_still_a_duplicate():
    one, two = activity(titled("Joao")), activity(titled("Joaoo"))
    two = replace(two, created_at=datetime(2026, 1, 2, tzinfo=UTC))
    assert find_duplicates([one, two]) == {two.id}


def test_the_same_title_is_a_duplicate_whatever_the_names():
    one, two = activity(titled("Joao")), activity(titled("Joao"))
    two = replace(two, created_at=datetime(2026, 1, 2, tzinfo=UTC))
    assert find_duplicates([one, two]) == {two.id}
