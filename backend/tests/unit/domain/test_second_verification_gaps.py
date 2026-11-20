"""SEG-11: assertions the second verification showed to be weak (D04, R03, I05, K08, R09)."""

from datetime import date

import pytest

from app.domain.entities.extraction import DocumentType as D
from app.domain.rules.document_type import detect_document_type
from app.domain.rules.grounding import date_in_text, same_person
from app.domain.rules.masking import mask_identifiers
from app.domain.rules.text_quality import is_text_layer_thin

# D04: both roles are written; the one that comes first decides (REAL-20).
BOARD_THEN_ADVISING = (
    "DECLARAÇÃO\n"
    "Declaro que Ana Ficticia Lima participou da banca examinadora do trabalho de Pedro Teste "
    "e foi orientadora do discente Marcos Exemplo em 2023.\n"
)
ADVISING_THEN_BOARD = (
    "DECLARAÇÃO\n"
    "Declaro que Ana Ficticia Lima foi orientadora do discente Marcos Exemplo e participou da "
    "banca examinadora do trabalho de Pedro Teste em 2023.\n"
)


def test_the_declared_board_comes_first_and_decides():
    assert detect_document_type(BOARD_THEN_ADVISING) is D.DECLARACAO_BANCA


def test_the_declared_advising_comes_first_and_decides():
    assert detect_document_type(ADVISING_THEN_BOARD) is D.DECLARACAO_ORIENTACAO


# R03: more initials than given names takes an initial from the surname.
def test_more_initials_than_given_names_is_not_the_professor():
    text = "Assinado por M. S. Souza, membro da banca."
    assert same_person("M. S. Souza", "Maria Souza", "1234567", text) is False
    assert same_person("M. Souza", "Maria Souza", "1234567", text + " M. Souza") is True


# I05: words of one or two letters are not distinct words of a text layer.
def test_a_layer_made_of_short_words_is_thin_on_an_image_heavy_page():
    short_words = " ".join(f"{a}{b}" for a in "abcdefgh" for b in "abcdefgh")  # 64 distinct
    assert len(set(short_words.split())) >= 60
    assert is_text_layer_thin(short_words, 0.9) is True


def test_a_layer_with_enough_distinct_long_words_is_not_thin():
    words = " ".join(f"palavra{'x' * n}" for n in range(1, 70))
    assert is_text_layer_thin(words.replace("x", "q"), 0.9) is False


# K08: a CPF-shaped group followed by a separator and a digit is part of a longer number.
@pytest.mark.parametrize(
    "text",
    [
        "processo 123 456 789 09/2025",
        "protocolo 123 456 789 09-5",
        "numero 123 456 789 09.1",
        "codigo 123.456.789 09.12",
    ],
)
def test_a_longer_number_that_starts_like_a_spaced_cpf_is_not_masked(text):
    assert mask_identifiers(text).text == text


def test_the_same_group_without_a_follower_is_still_masked():
    assert "[CPF]" in mask_identifiers("CPF 123 456 789 09 do docente").text


# R09: a comma does not link a stray number to a day (page 3, 12 de março de 2026).
def test_a_comma_does_not_make_a_stray_number_the_start_of_a_date_range():
    text = "Ver páginas 3, 12 de março de 2026."
    assert date_in_text(date(2026, 3, 12), text) is True
    assert date_in_text(date(2026, 3, 3), text) is False
