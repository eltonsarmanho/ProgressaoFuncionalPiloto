"""REQ-02 to REQ-08: the text of the Requerimento built from the PROGEP model."""

import inspect
from dataclasses import fields
from datetime import date

from app.domain.entities.career import Modality
from app.domain.rules import request_document
from app.domain.rules.request_document import build_request
from tests.unit.domain.board_document_support import PAGE, PROFESSOR, UNIT, process

# The fixed phrases, copied from the public PROGEP model (docs/referencias/normas).
MODEL_HEADER = (
    "MINISTÉRIO DA EDUCAÇÃO",
    "UNIVERSIDADE FEDERAL DO PARÁ",
    "PRÓ-REITORIA DE DESENVOLVIMENTO E GESTÃO DE PESSOAL",
)
MODEL_TITLE = "REQUERIMENTO DE PROGRESSÃO/PROMOÇÃO/REVISÃO - DOCENTES (MAGISTÉRIO SUPERIOR E EBTT)"
MODEL_GREETING = "Prezado Sr. Presidente da CPPD,"
MODEL_OPTION = "(X) PROGRESSÃO FUNCIONAL POR DESEMPENHO ACADÊMICA/PROMOÇÃO"
MODEL_CLOSING = "Nestes termos, pede deferimento."
MODEL_CAPTION = "Assinatura do (a) requerente"
MODEL_LGPD = (
    "De acordo com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018), "
    "deve-se restringir o acesso a este documento por conter informações pessoais."
)


def build(
    *, proc=None, career="MAGISTERIO_SUPERIOR", city="Belém", last_opinion=date(2025, 4, 2)
):
    return build_request(proc or process(), PROFESSOR, UNIT, career, city, last_opinion, PAGE)


def texts(document) -> list[str]:
    """Every text of the document in the order the fields are declared (the model order)."""
    found = []
    for field in fields(document):
        value = getattr(document, field.name)
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, tuple):
            found.extend(value)
    return found


# --- fixed phrases of the model (REQ-02) ----------------------------------------------------


def test_the_header_the_title_the_greeting_and_the_option_are_the_ones_of_the_model():
    document = build()

    assert document.header_lines == MODEL_HEADER
    assert document.title == MODEL_TITLE
    assert document.greeting == MODEL_GREETING
    assert document.option == MODEL_OPTION


def test_the_page_is_the_one_given():
    assert build().page is PAGE


# --- the paragraph of the request (REQ-03) --------------------------------------------------


def test_a_promotion_from_level_4_of_class_b_to_level_1_of_class_c_fills_the_paragraph():
    assert build().request_paragraph == (
        "Eu, Maria Docente da Silva, Matrícula SIAPE 1234567, docente do (X) Magistério "
        "Superior/ (  ) Ensino Básico e Tecnológico, atualmente lotado no (a) "
        "Faculdade de Testes Sintéticos, solicito promoção funcional, do nível 4 da classe B "
        "(Adjunto) para o nível 1 da classe C (Associado), referente ao interstício "
        "23/11/2022 a 23/11/2024."
    )


def test_a_progression_says_progressao_in_the_paragraph():
    paragraph = build(proc=process(Modality.PROGRESSAO)).request_paragraph

    assert "solicito progressão funcional" in paragraph
    assert "promoção" not in paragraph


def test_levels_classes_and_denominations_are_the_typed_ones_with_nothing_deduced():
    proc = process(
        current_class="D", current_denomination="Denominação Antiga", current_level=2,
        target_class="E", target_denomination="Titular-Livre", target_level=3,
    )  # fmt: skip

    paragraph = build(proc=proc).request_paragraph

    assert (
        "do nível 2 da classe D (Denominação Antiga) para o nível 3 da classe E (Titular-Livre)"
        in paragraph
    )


def test_an_unknown_career_code_leaves_both_options_unmarked():
    paragraph = build(career="OUTRA_CARREIRA").request_paragraph

    assert "(  ) Magistério Superior/ (  ) Ensino Básico e Tecnológico" in paragraph
    assert "(X)" not in paragraph


# --- performance evaluation line (REQ-04) ---------------------------------------------------


def test_the_evaluation_line_carries_the_date_of_the_last_opinion():
    assert build().evaluation_line == (
        "Em conformidade com a avaliação de desempenho em anexo, realizada na data de 02/04/2025."
    )


def test_without_an_opinion_the_evaluation_date_is_a_blank():
    assert build(last_opinion=None).evaluation_line == (
        "Em conformidade com a avaliação de desempenho em anexo, realizada na data de ___/___/___."
    )


# --- place and date (REQ-05, REQ-06) --------------------------------------------------------


def test_the_closing_line_has_the_city_and_the_opening_date_in_words():
    assert build().place_date_line == "Belém, 10 de março de 2025."


def test_without_a_city_the_line_starts_with_a_blank():
    assert build(city=None).place_date_line == "__________, 10 de março de 2025."


def test_a_city_with_only_spaces_counts_as_not_informed():
    assert build(city="   ").place_date_line == "__________, 10 de março de 2025."


# --- ending of the model (REQ-05) -----------------------------------------------------------


def test_the_ending_has_the_closing_the_signature_the_siape_and_the_lgpd_note():
    document = build()

    assert document.closing == MODEL_CLOSING
    assert document.signature_line == "__________________________________________"
    assert document.signature_caption == MODEL_CAPTION
    assert document.siape_line == "Matrícula SIAPE: 1234567"
    assert document.lgpd_heading == "Observação"
    assert document.lgpd_text == MODEL_LGPD


def test_the_texts_follow_the_order_of_the_model():
    found = texts(build())

    ordered = [
        MODEL_TITLE,
        MODEL_GREETING,
        MODEL_OPTION,
        build().request_paragraph,
        build().evaluation_line,
        "Belém, 10 de março de 2025.",
        MODEL_CLOSING,
        MODEL_CAPTION,
        "Matrícula SIAPE: 1234567",
        MODEL_LGPD,
    ]
    positions = [found.index(text) for text in ordered]
    assert positions == sorted(positions)


# --- no review part (REQ-07) ----------------------------------------------------------------


def test_the_review_part_and_its_instructions_are_not_in_the_document():
    found = [text for text in texts(build()) if text != MODEL_TITLE]

    assert not any("REVISÃO" in text.upper() for text in found)
    assert not any("SIPAC" in text or "Processo 23073" in text for text in found)


# --- no clock, no AI (REQ-08) ---------------------------------------------------------------


def test_the_same_input_gives_the_same_document():
    assert build() == build()


def test_the_module_reads_no_clock_and_calls_no_ai():
    source = inspect.getsource(request_document).lower()

    for forbidden in ("now(", "today(", "utcnow(", "maritalk", "import time", "app.infrastructure"):
        assert forbidden not in source
