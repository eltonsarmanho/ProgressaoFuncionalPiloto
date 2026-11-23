"""PMOD-01 to PMOD-19: the text of the Parecer, built after the official model."""

import inspect
from datetime import date
from uuid import uuid4

import pytest

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.board import BoardRole, OpinionConclusion
from app.domain.entities.career import Modality
from app.domain.rules import opinion_document
from app.domain.rules.opinion_document import build_opinion
from tests.unit.domain.board_document_support import (
    CAMPUS,
    PAGE,
    PROFESSOR,
    UNIT,
    member,
    opinion,
    ordinance,
    process,
)

MEMBERS = (
    member("Ana Presidente Souza", BoardRole.PRESIDENTE),
    member("Bruno Membro Lima"),
    member("Carla Membro Reis"),
    member("Davi Suplente Rocha", BoardRole.SUPLENTE),
)
INSTITUTE = AcademicUnit(uuid4(), "Instituto Sintético", "INS", UnitKind.INSTITUTO)
DAY = date(2025, 5, 27)


def build(*, proc=None, members=MEMBERS, number="123/2025", opinion_=None, parent=CAMPUS):
    return build_opinion(
        proc or process(),
        PROFESSOR,
        UNIT,
        parent,
        ordinance(members=members, number=number),
        opinion_ or opinion(opinion_date=DAY, place="Belém"),
        PAGE,
    )


def paragraph(document) -> str:
    return "".join(run.text for run in document.paragraph)


def bold_runs(document) -> list[str]:
    return [run.text for run in document.paragraph if run.bold]


def on(day: date, **changes):
    return build(opinion_=opinion(opinion_date=day, place="Belém", **changes))


def all_text(document) -> str:
    return "\n".join(
        [
            *document.header_lines,
            document.title,
            document.place_date_line,
            paragraph(document),
            *document.member_lines,
        ]
    )


# --- the paragraph of the model (PMOD-06, PMOD-10, PMOD-12) ----------------------------------


def test_the_paragraph_is_the_text_of_the_model_filled_with_the_synthetic_process():
    assert paragraph(build()) == (
        "Aos vinte e sete dias do mês de maio de dois mil e vinte e cinco, reuniram-se os "
        "membros da Banca de Análise, nomeados pela Portaria nº 123/2025, Ana Presidente Souza "
        "(presidente), Bruno Membro Lima, Carla Membro Reis, responsáveis por analisar o "
        "Relatório de Atividades do Professor Adjunto Nível IV Maria Docente da Silva, para "
        "fins de progressão funcional do docente, referente ao interstício de 23/11/2022 a "
        "23/11/2024, para Classe C (Associado) Nível I. Após a análise, os membros APROVARAM "
        "o referido relatório."
    )


def test_only_the_date_words_and_the_current_situation_with_the_name_are_in_bold():
    document = build()

    assert bold_runs(document) == [
        "vinte e sete dias do mês de maio de dois mil e vinte e cinco",
        "Adjunto Nível IV Maria Docente da Silva",
    ]
    first, *_, last = [run for run in document.paragraph if not run.bold]
    assert first.text == "Aos "
    assert any(not run.bold and run.text.endswith("do Professor ") for run in document.paragraph)
    assert last.text.startswith(", para fins de progressão funcional do docente")


def test_progression_and_promotion_write_the_same_purpose():
    promotion = paragraph(build())
    progression = paragraph(build(proc=process(Modality.PROGRESSAO)))

    assert "para fins de progressão funcional do docente" in promotion
    assert "para fins de progressão funcional do docente" in progression
    assert "promoção" not in promotion.lower()


# --- the date by extension (PMOD-08, PMOD-09) ------------------------------------------------


@pytest.mark.parametrize(
    ("day", "words"),
    [
        (date(2026, 1, 2), "Aos dois dias do mês de janeiro de dois mil e vinte e seis"),
        (date(2026, 1, 21), "Aos vinte e um dias do mês de janeiro de dois mil e vinte e seis"),
        (date(2026, 1, 31), "Aos trinta e um dias do mês de janeiro de dois mil e vinte e seis"),
    ],
)
def test_the_days_two_to_thirty_one_use_the_cardinal_and_the_plural(day, words):
    assert paragraph(on(day)).startswith(f"{words}, reuniram-se")


def test_the_first_day_uses_the_singular_and_the_ordinal():
    document = on(date(2026, 1, 1))

    assert paragraph(document).startswith(
        "Ao primeiro dia do mês de janeiro de dois mil e vinte e seis, reuniram-se"
    )
    assert bold_runs(document)[0] == "primeiro dia do mês de janeiro de dois mil e vinte e seis"


@pytest.mark.parametrize(
    ("year", "words"),
    [
        (2000, "dois mil"),
        (2025, "dois mil e vinte e cinco"),
        (2100, "dois mil e cem"),
        (2101, "dois mil cento e um"),
    ],
)
def test_the_year_is_written_in_words(year, words):
    assert paragraph(on(date(year, 6, 10))).startswith(
        f"Aos dez dias do mês de junho de {words}, reuniram-se"
    )


@pytest.mark.parametrize("year", [999, 3000])
def test_a_year_out_of_one_thousand_to_2999_is_written_in_digits(year):
    document = on(date(year, 6, 10))

    assert paragraph(document).startswith(f"Aos dez dias do mês de junho de {year}, reuniram-se")
    assert document.place_date_line == f"Belém, 10 de Junho de {year}."


@pytest.mark.parametrize(
    ("month", "lower", "capital"),
    [
        (1, "janeiro", "Janeiro"),
        (2, "fevereiro", "Fevereiro"),
        (3, "março", "Março"),
        (4, "abril", "Abril"),
        (5, "maio", "Maio"),
        (6, "junho", "Junho"),
        (7, "julho", "Julho"),
        (8, "agosto", "Agosto"),
        (9, "setembro", "Setembro"),
        (10, "outubro", "Outubro"),
        (11, "novembro", "Novembro"),
        (12, "dezembro", "Dezembro"),
    ],
)
def test_the_month_is_lowercase_in_the_paragraph_and_capitalized_in_the_place_and_date_line(
    month, lower, capital
):
    document = on(date(2025, month, 27))

    assert f"dias do mês de {lower} de dois mil e vinte e cinco" in paragraph(document)
    assert document.place_date_line == f"Belém, 27 de {capital} de 2025."


def test_the_place_and_date_line_has_the_day_without_a_leading_zero():
    assert on(date(2025, 5, 7)).place_date_line == "Belém, 7 de Maio de 2025."


# --- the decision (PMOD-10, PMOD-11) ---------------------------------------------------------


def test_a_favorable_conclusion_ends_with_aprovaram():
    assert paragraph(build()).endswith("Após a análise, os membros APROVARAM o referido relatório.")


def test_an_unfavorable_conclusion_ends_with_nao_aprovaram():
    document = build(opinion_=opinion(OpinionConclusion.DESFAVORAVEL, opinion_date=DAY))

    assert paragraph(document).endswith(
        "Após a análise, os membros NÃO APROVARAM o referido relatório."
    )


def test_without_a_conclusion_the_document_is_never_written():
    with pytest.raises(ValueError):
        build(opinion_=opinion(conclusion=None))


# --- roman levels and the six fields as typed (PMOD-12, NMOV-01) ------------------------------


def test_the_levels_are_written_in_roman_numerals():
    text = paragraph(build(proc=process(current_level=1, target_level=4)))

    assert "Adjunto Nível I Maria Docente da Silva" in text
    assert "Classe C (Associado) Nível IV." in text


@pytest.mark.parametrize("level", [0, 4000])
def test_a_level_out_of_one_to_3999_is_written_as_typed(level):
    text = paragraph(build(proc=process(current_level=level, target_level=level)))

    assert f"Adjunto Nível {level} Maria" in text
    assert f"Classe C (Associado) Nível {level}." in text


def test_class_and_denominations_out_of_the_usual_pattern_are_copied_as_typed():
    proc = process(
        current_class="A",
        current_denomination="Titular-Livre",
        target_class="C",
        target_denomination="Denominação Nova",
    )

    text = paragraph(build(proc=proc))

    assert "Professor Titular-Livre Nível IV Maria" in text
    assert "para Classe C (Denominação Nova) Nível I." in text


# --- the members (PMOD-13, PMOD-14, PMOD-15) -------------------------------------------------


def test_the_member_lines_have_the_president_and_the_numbered_members_without_the_alternate():
    document = build()

    assert document.member_lines == (
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
        "MEMBRO 2: Carla Membro Reis",
    )
    assert "Davi Suplente Rocha" not in all_text(document)


def test_a_president_that_is_not_the_first_of_the_ordinance_comes_first():
    members = (
        member("Bruno Membro Lima"),
        member("Ana Presidente Souza", BoardRole.PRESIDENTE),
        member("Carla Membro Reis"),
    )

    document = build(members=members)

    assert document.member_lines == (
        "PRESIDENTE: Ana Presidente Souza",
        "MEMBRO 1: Bruno Membro Lima",
        "MEMBRO 2: Carla Membro Reis",
    )
    assert (
        "Ana Presidente Souza (presidente), Bruno Membro Lima, Carla Membro Reis, responsáveis"
        in (paragraph(document))
    )


def test_without_a_president_nobody_is_marked_and_the_lines_are_only_members():
    members = (member("Bruno Membro Lima"), member("Carla Membro Reis"))

    document = build(members=members)

    assert "(presidente)" not in paragraph(document)
    assert (
        "nomeados pela Portaria nº 123/2025, Bruno Membro Lima, Carla Membro Reis, responsáveis"
        in (paragraph(document))
    )
    assert document.member_lines == ("MEMBRO 1: Bruno Membro Lima", "MEMBRO 2: Carla Membro Reis")


def test_a_president_alone_gives_one_line_and_the_paragraph_names_only_him():
    document = build(members=(member("Ana Presidente Souza", BoardRole.PRESIDENTE),))

    assert "Ana Presidente Souza (presidente), responsáveis por analisar" in paragraph(document)
    assert document.member_lines == ("PRESIDENTE: Ana Presidente Souza",)


def test_two_presidents_are_both_marked_and_come_before_the_members_that_start_at_one():
    members = (
        member("Bruno Membro Lima"),
        member("Ana Presidente Souza", BoardRole.PRESIDENTE),
        member("Eva Presidente Dias", BoardRole.PRESIDENTE),
    )

    document = build(members=members)

    assert (
        "Ana Presidente Souza (presidente), Eva Presidente Dias (presidente), Bruno Membro Lima, "
        "responsáveis" in paragraph(document)
    )
    assert document.member_lines == (
        "PRESIDENTE: Ana Presidente Souza",
        "PRESIDENTE: Eva Presidente Dias",
        "MEMBRO 1: Bruno Membro Lima",
    )


def test_fifteen_members_and_names_of_two_hundred_characters_are_written_whole():
    long_name = "N" * 200
    members = (member(long_name, BoardRole.PRESIDENTE), *(member(f"Membro {n}") for n in range(14)))

    document = build(members=members)

    assert len(document.member_lines) == 15
    assert document.member_lines[0] == f"PRESIDENTE: {long_name}"
    assert document.member_lines[-1] == "MEMBRO 14: Membro 13"
    assert f"{long_name} (presidente)" in paragraph(document)
    assert "Membro 13, responsáveis" in paragraph(document)


def test_names_and_the_ordinance_number_are_written_as_registered_with_no_title_added():
    members = (member("Prof. Dr. Ana Presidente Souza", BoardRole.PRESIDENTE), member("Bruno"))

    document = build(members=members, number="89/2025 - CCAME")

    assert "Portaria nº 89/2025 - CCAME, Prof. Dr. Ana Presidente Souza (presidente), Bruno," in (
        paragraph(document)
    )
    assert document.member_lines[1] == "MEMBRO 1: Bruno"
    assert "Prof. Prof." not in all_text(document)
    assert "Dr. Bruno" not in all_text(document)


# --- the header and the title (PMOD-02, PMOD-03, PMOD-04) ------------------------------------


def test_with_a_campus_as_parent_the_header_has_three_lines_with_an_en_dash():
    document = build()

    assert document.header_lines == (
        "Universidade Federal do Pará",
        "Campus Universitário Sintético",
        "Faculdade de Testes Sintéticos – FATS",
    )


@pytest.mark.parametrize("parent", [None, INSTITUTE])
def test_without_a_campus_as_parent_the_header_has_two_lines(parent):
    document = build(parent=parent)

    assert document.header_lines == (
        "Universidade Federal do Pará",
        "Faculdade de Testes Sintéticos – FATS",
    )


def test_the_title_is_parecer_and_the_page_is_the_one_given():
    document = build()

    assert document.title == "PARECER"
    assert document.page is PAGE


# --- blanks (PMOD-16, PMOD-17, PMOD-18) -------------------------------------------------------


def test_without_a_date_the_paragraph_and_the_line_keep_the_blanks_and_nothing_is_refused():
    document = build(opinion_=opinion(opinion_date=None, place="Belém"))

    assert paragraph(document).startswith(
        "Aos ______ dias do mês de ________ de ________, reuniram-se"
    )
    assert document.place_date_line == "Belém, ____ de ________ de ________."


def test_without_a_place_the_line_has_the_blank_in_the_place_of_the_city():
    document = build(opinion_=opinion(opinion_date=DAY, place=None))

    assert document.place_date_line == "__________, 27 de Maio de 2025."


def test_a_place_of_only_spaces_is_a_blank_place():
    document = build(opinion_=opinion(opinion_date=DAY, place="   "))

    assert document.place_date_line == "__________, 27 de Maio de 2025."


def test_without_an_ordinance_number_the_paragraph_has_the_blank():
    document = build(number=None)

    assert "nomeados pela Portaria nº __________, Ana Presidente Souza" in paragraph(document)


# --- nothing of the old structure (PMOD-01, PMOD-19) -----------------------------------------


def test_the_document_has_none_of_the_texts_of_the_old_structure():
    text = all_text(build())

    for forbidden in (
        "Total geral",
        "Mínimo de referência",
        "Documentos analisados",
        "Pontuação por grupo",
        "Observações",
        "Identificação",
        "Portaria da banca:",
        "Conclusão",
    ):
        assert forbidden not in text


def test_the_document_has_only_the_elements_of_the_model():
    document = build()

    assert [field for field in vars(document)] == [
        "page",
        "header_lines",
        "title",
        "place_date_line",
        "paragraph",
        "member_lines",
    ]


# --- no clock, no AI (PMOD-25) ---------------------------------------------------------------


def test_the_same_input_gives_the_same_document():
    ordinance_ = ordinance(members=MEMBERS)
    opinion_ = opinion(opinion_date=DAY, place="Belém")
    args = (process(), PROFESSOR, UNIT, CAMPUS, ordinance_, opinion_, PAGE)

    assert build_opinion(*args) == build_opinion(*args)


def test_the_module_reads_no_clock_and_calls_no_ai():
    source = inspect.getsource(opinion_document)

    for forbidden in ("now(", "today(", "utcnow(", "maritalk", "import time", "app.infrastructure"):
        assert forbidden not in source.lower()
