"""TER-10: the system prompt tells the AI to return the literal term and never the end date.

The end date of a designation is derived by the code from the grounded `term` (AD-010); a
prompt that asks the AI for the end date, or that stops mentioning `term`, breaks that chain
without any other test noticing.
"""

from app.domain.entities.extraction import DocumentType
from app.infrastructure.ai.maritalk import MariTalkExtractor


def system_prompt(professor_name=None) -> str:
    text = "[PÁGINA 1]\ntexto"
    body = MariTalkExtractor._body(DocumentType.PORTARIA, text, "m", 8000, professor_name)
    return body["messages"][0]["content"]


def test_the_prompt_names_the_term_field_and_asks_for_the_literal_wording():
    prompt = system_prompt()
    assert "Em `term` copie literalmente o prazo de duração da designação" in prompt
    assert '"por 2 (dois) anos"' in prompt


def test_the_prompt_forbids_computing_the_end_date():
    prompt = system_prompt()
    assert "nunca calcule a data final" in prompt
    assert "calcule a data final" not in prompt.replace("nunca calcule a data final", "")


def test_the_prompt_still_forbids_computing_points_quantities_and_hours():
    assert "Não calcule pontos, quantidades nem horas" in system_prompt()


def test_the_professor_instruction_does_not_replace_the_term_instruction():
    prompt = system_prompt("Fulana de Tal Exemplo")
    assert "Em `term` copie literalmente" in prompt
    assert "Fulana de Tal Exemplo" in prompt


def test_the_prompt_says_the_document_may_be_in_english_and_fields_are_copied_untranslated():
    """CER-03: an english certificate must come back with its own words, not a translation."""
    for prompt in (system_prompt(), system_prompt("Fulana de Tal Exemplo")):
        assert "O documento pode estar em inglês" in prompt
        assert "copie os campos literalmente do texto, sem traduzir" in prompt
