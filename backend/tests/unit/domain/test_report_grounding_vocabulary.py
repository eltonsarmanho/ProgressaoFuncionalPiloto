"""REL-04, REL-12: names, new words, length and forbidden words of the wording from the AI."""

import pytest

from app.domain.rules.report_grounding import (
    WordingReason,
    WordingVocabulary,
    check_wording,
)

FACTS = {
    "tipo": "Orientação de trabalho de conclusão de curso",
    "titulo": "Orientação de Maria Oliveira no curso de Computação",
    "datas": "01/03/2023 a 15/07/2023",
}
MODEL_TEXT = "Orientação de Maria Oliveira no curso de Computação, 01/03/2023 a 15/07/2023"
FORBIDDEN = (
    "objetivo",
    "resultado",
    "metodologia",
    "excelente",
    "relevante",
    "visando",
    "contribuindo",
)


def vocabulary(max_new_words=2, **kwargs) -> WordingVocabulary:
    defaults = {
        "allowed_terms": ("UFPA", "Universidade Federal do Pará", "unidade"),
        "formal_vocabulary": ("realizou", "ministrou", "concluída", "estudante"),
        "forbidden_words": FORBIDDEN,
    }
    defaults.update(kwargs)
    return WordingVocabulary(max_new_words=max_new_words, **defaults)


def check(wording, facts=None, vocab=None, model_text=MODEL_TEXT):
    return check_wording(
        wording, FACTS if facts is None else facts, vocab or vocabulary(), model_text
    )


def test_a_name_that_is_not_in_the_fields_is_refused_with_the_reason_name():
    result = check("Orientação de Maria Oliveira e de Carlos Mendes no curso de Computação.")

    assert result.accepted is False
    assert result.reasons == (WordingReason.NOME,)


def test_an_acronym_that_is_not_in_the_fields_is_refused_with_the_reason_name():
    result = check("Orientação de Maria Oliveira no curso de Computação do IFPA.")

    assert result.reasons == (WordingReason.NOME,)


def test_an_acronym_at_the_start_of_a_sentence_is_also_checked():
    assert check("SIGAA registra a orientação de Maria Oliveira.").reasons == (WordingReason.NOME,)


@pytest.mark.parametrize(
    "wording",
    [
        "Orientação de Maria Oliveira no curso de Computação.",
        "Orientação de Maria Oliveira na UFPA, no curso de Computação.",
        "Orientação de Maria Oliveira na Universidade Federal do Pará.",
        "Orientação de Maria Oliveira na Unidade, no curso de Computação.",
        "MARIA OLIVEIRA concluiu a orientação.",
    ],
)
def test_names_and_acronyms_of_the_fields_or_of_the_allowed_terms_are_accepted(wording):
    result = check(wording)

    assert result.accepted is True
    assert result.reasons == ()


def test_a_capitalized_word_at_the_start_of_a_sentence_is_not_taken_for_a_name():
    wording = "Orientação concluída. Trabalho de Maria Oliveira."

    assert check(wording).accepted is True


def test_a_capitalized_word_in_the_middle_of_a_sentence_is_taken_for_a_name():
    assert check("Orientação concluída. Estudante Joana Pereira.").reasons == (WordingReason.NOME,)


def test_more_new_content_words_than_the_limit_are_refused_with_the_reason_vocabulary():
    wording = "Orientação de Maria Oliveira com mentoria constante, acompanhamento quinzenal."

    result = check(wording, vocab=vocabulary(max_new_words=2))

    assert result.accepted is False
    assert result.reasons == (WordingReason.VOCABULARIO,)


def test_exactly_the_limit_of_new_content_words_is_accepted():
    wording = "Orientação de Maria Oliveira com mentoria constante."

    assert check(wording, vocab=vocabulary(max_new_words=2)).accepted is True
    assert check(wording, vocab=vocabulary(max_new_words=1)).reasons == (WordingReason.VOCABULARIO,)


def test_short_words_the_fields_the_template_text_and_the_formal_vocabulary_are_not_new():
    wording = "O estudante realizou a orientação de Maria Oliveira no curso de Computação."

    assert check(wording, vocab=vocabulary(max_new_words=0)).accepted is True


def test_a_new_word_repeated_counts_once():
    wording = "Orientação de Maria Oliveira. Mentoria, mentoria e mentoria."

    assert check(wording, vocab=vocabulary(max_new_words=1)).accepted is True


def test_a_wording_longer_than_twice_the_template_plus_120_characters_is_refused():
    limit = 2 * len(MODEL_TEXT) + 120
    filler = "curso " * ((limit + 1) // 6)
    wording = (filler + "x" * (limit + 1 - len(filler)))[: limit + 1]
    assert len(wording) == limit + 1

    result = check(wording, vocab=vocabulary(max_new_words=100))

    assert result.accepted is False
    assert WordingReason.COMPRIMENTO in result.reasons


def test_a_wording_with_exactly_the_length_limit_is_accepted():
    limit = 2 * len(MODEL_TEXT) + 120
    wording = ("curso " * (limit // 6 + 1))[:limit]
    assert len(wording) == limit

    result = check(wording, vocab=vocabulary(max_new_words=100))

    assert WordingReason.COMPRIMENTO not in result.reasons


@pytest.mark.parametrize("word", FORBIDDEN)
def test_each_forbidden_word_is_refused_with_the_reason_forbidden_word(word):
    wording = f"Orientação de Maria Oliveira com {word}."

    result = check(wording, vocab=vocabulary(max_new_words=100))

    assert result.accepted is False
    assert result.reasons == (WordingReason.PALAVRA_PROIBIDA,)


def test_a_forbidden_word_is_found_in_the_plural_and_in_capitals():
    vocab = vocabulary(max_new_words=100)

    assert check("Orientação com resultados.", vocab=vocab).reasons == (
        WordingReason.PALAVRA_PROIBIDA,
    )
    assert (
        WordingReason.PALAVRA_PROIBIDA in check("Orientação com METODOLOGIA.", vocab=vocab).reasons
    )


def test_a_forbidden_word_the_fields_already_have_is_not_something_the_ai_added():
    facts = {"titulo": "Metodologia da Pesquisa Científica", "datas": "01/03/2023"}

    result = check("Disciplina Metodologia da Pesquisa Científica.", facts, vocabulary(100))

    assert result.accepted is True


def test_a_refused_wording_returns_the_template_text():
    result = check("Orientação de Maria Oliveira com resultados excelentes.")

    assert result.accepted is False
    assert result.text == MODEL_TEXT


def test_a_faithful_wording_is_accepted_and_returned_as_it_came():
    wording = "Orientação de Maria Oliveira no curso de Computação, de 01/03/2023 a 15/07/2023."

    result = check(wording)

    assert (result.accepted, result.text) == (True, wording)


def test_the_reasons_come_in_a_fixed_order():
    wording = "Orientação de Joana Pereira com 40 horas, mentoria constante, resultado."

    result = check(wording, vocab=vocabulary(max_new_words=0))

    assert result.reasons == (
        WordingReason.NUMERO,
        WordingReason.NOME,
        WordingReason.VOCABULARIO,
        WordingReason.PALAVRA_PROIBIDA,
    )


def test_a_month_name_or_a_particle_in_capitals_is_not_taken_for_a_name():
    wording = "Orientação de Maria Oliveira até NOVEMBRO DE 2023 E EM Dezembro."

    assert WordingReason.NOME not in check(wording, vocab=vocabulary(max_new_words=100)).reasons
