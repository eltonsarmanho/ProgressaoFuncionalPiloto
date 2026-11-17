"""PIPE-05, PIPE-07: text layer usability and OCR review rules."""

from decimal import Decimal

import pytest

from app.domain.rules.text_quality import is_text_layer_thin, is_text_layer_usable, ocr_needs_review

GOOD = (
    "PORTARIA Nº 3686/2024. O Diretor da Faculdade resolve designar a servidora Maria Souza "
    "para integrar a comissão, a partir de 01/03/2024."
)


def _text(useful: int, symbols: int) -> str:
    """`useful` letters/digits plus `symbols` odd characters, separated by single spaces."""
    return " ".join(["a" * useful, "¬" * symbols]) if symbols else "a" * useful


def test_normal_portuguese_text_is_usable():
    assert is_text_layer_usable(GOOD) is True


def test_text_with_accents_and_digits_counts_as_useful():
    assert is_text_layer_usable("ãéíõç" * 10) is True


def test_49_useful_characters_are_unusable():
    assert is_text_layer_usable("a" * 49) is False


def test_exactly_50_useful_characters_are_usable():
    assert is_text_layer_usable("a" * 50) is True


def test_punctuation_and_spaces_are_not_useful_characters():
    text = "a" * 49 + " .,;:!?-()/\"'%º ª°§&@#+ " * 10
    assert is_text_layer_usable(text) is False


def test_empty_or_blank_text_is_unusable():
    assert is_text_layer_usable("") is False
    assert is_text_layer_usable("   \n\t ") is False


def test_exactly_30_percent_symbols_is_usable():
    # 70 letters + 30 symbols = 100 non-space characters, 30% symbols
    assert is_text_layer_usable("a" * 70 + "¬" * 30) is True


def test_more_than_30_percent_symbols_is_unusable():
    # 70 letters + 31 symbols = 101 non-space characters, 30.69% symbols
    assert is_text_layer_usable("a" * 70 + "¬" * 31) is False


def test_whitespace_does_not_count_in_the_symbol_ratio():
    assert is_text_layer_usable(" ".join(["a" * 70, "¬" * 30])) is True
    assert is_text_layer_usable(" \n ".join(["a" * 70, "¬" * 31])) is False


def test_common_punctuation_is_not_a_symbol():
    text = "a" * 60 + ".,;:!?-()/\"'%º ª°§&@#+" * 3
    assert is_text_layer_usable(text) is True


def test_ordinary_text_with_typographic_quotes_and_dashes_is_usable():
    text = "A comissão “aprovou” o relatório – conforme ‘parecer’ — em sessão… " * 3
    assert is_text_layer_usable(text) is True


def test_short_garbage_fragment_from_a_portaria_is_unusable():
    assert is_text_layer_usable("7 r:rjo;:N *P-7-44") is False


def test_long_noisy_portaria_layer_is_unusable():
    noisy = (
        "7 r:rjo;:N *P-7-44 ¬¥ ©® ¦~ ^` |{ }<> =_ \\ ¬¥©® ¦~^` |{}<> ="
        " PORTARIA Nº ¬¥©®¦~ ^`|{}<>=_\\ ¬¥©®¦~^`|{}<>=_\\ resolve ¬¥©®¦~^`|{}<>=_\\"
    )
    assert is_text_layer_usable(noisy) is False


def test_ocr_confidence_below_60_needs_review():
    assert ocr_needs_review(Decimal("59.99"), GOOD) is True


def test_ocr_confidence_of_exactly_60_does_not_need_review():
    assert ocr_needs_review(Decimal("60"), GOOD) is False


def test_ocr_confidence_above_60_does_not_need_review():
    assert ocr_needs_review(Decimal("91.5"), GOOD) is False


@pytest.mark.parametrize("text", ["", "  \n\t "])
def test_ocr_without_text_needs_review_even_with_high_confidence(text):
    assert ocr_needs_review(Decimal("99"), text) is True


def test_ocr_without_confidence_needs_review():
    assert ocr_needs_review(None, GOOD) is True


# --- REAL-13: thin text layer on an image heavy page --------------------------------------------

HEADER_FOOTER = (
    "UNIVERSIDADE FEDERAL EXEMPLAR Pro-Reitoria de Extensao Certificado "
    "Documento ficticio emitido pelo sistema de testes, validacao em endereco ficticio."
)
FULL_PAGE = " ".join(f"palavra{chr(97 + i % 26)}{chr(97 + i // 26)}x" for i in range(120))


def test_header_and_footer_over_a_large_image_is_a_thin_layer():
    assert is_text_layer_usable(HEADER_FOOTER) is True
    assert is_text_layer_thin(HEADER_FOOTER, 0.9) is True


def test_the_same_short_layer_with_a_small_image_is_not_thin():
    assert is_text_layer_thin(HEADER_FOOTER, 0.1) is False
    assert is_text_layer_thin(HEADER_FOOTER, 0.49) is False


def test_a_full_text_page_with_a_large_image_is_not_thin():
    assert is_text_layer_thin(FULL_PAGE, 0.9) is False


def test_the_coverage_boundary_counts_as_image_heavy():
    assert is_text_layer_thin(HEADER_FOOTER, 0.5) is True


def test_repeated_words_do_not_make_a_layer_look_full():
    assert is_text_layer_thin("certificado de participacao " * 40, 0.9) is True
