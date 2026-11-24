"""SEG-08: a partial name from the AI is the professor only with text support."""

import pytest

from app.domain.rules.grounding import same_person

PROFESSOR = "Maria Aparecida de Souza"
SIAPE = "1234567"


@pytest.mark.parametrize("name", ["Maria Souza", "Maria Aparecida", "Aparecida Souza"])
def test_a_partial_name_without_support_in_the_text_is_not_the_professor(name):
    text = "Banca composta por Maria Souza (presidente) e Joao Lima."
    assert same_person(name, PROFESSOR, SIAPE, text) is False


def test_a_partial_name_is_not_the_professor_with_no_text_at_all():
    assert same_person("Maria Souza", PROFESSOR, SIAPE, "") is False


def test_a_partial_name_is_the_professor_when_the_siape_is_in_the_text():
    text = "Maria Souza, matricula SIAPE 1234567, participou da banca."
    assert same_person("Maria Souza", PROFESSOR, SIAPE, text) is True


def test_a_partial_name_is_the_professor_when_the_full_name_is_in_the_text():
    text = "A professora Maria Aparecida de Souza participou da banca como Maria Souza."
    assert same_person("Maria Souza", PROFESSOR, SIAPE, text) is True


def test_the_complete_name_returned_by_the_ai_is_still_the_professor():
    assert same_person("MARIA APARECIDA DE SOUZA", PROFESSOR, SIAPE, "") is True
    assert same_person("Maria Aparecida de Souza Lima", PROFESSOR, SIAPE, "") is True
