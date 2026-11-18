"""EXT-10, EXT-11: extracted values must appear in the cited page; same person check."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity, TaxonomyCode
from app.domain.rules.grounding import (
    DatePrecision,
    GroundingWarning,
    date_in_text,
    ground,
    hours_in_text,
    identifier_in_text,
    month_only_dates,
    name_in_text,
    professor_named_in_text,
    same_person,
    title_in_text,
)

D = DatePrecision


# ---------- dates ----------


@pytest.mark.parametrize(
    "text",
    [
        "realizada em 23/03/2026.",
        "realizada em 23.03.2026.",
        "realizada em 23-03-2026.",
        "realizada em 2026-03-23.",
        "realizada em 23 de março de 2026.",
        "realizada em 23 DE MARÇO DE 2026.",
        "realizada em 23 de marco de 2026.",
        "realizada em 23 de Março de 2026",
    ],
)
def test_full_date_in_any_accepted_format_is_grounded(text):
    assert date_in_text(date(2026, 3, 23), text) is True


def test_date_without_zero_padding_is_grounded():
    assert date_in_text(date(2024, 3, 3), "em 3/3/2024") is True
    assert date_in_text(date(2024, 3, 3), "em 03/03/2024") is True


def test_first_day_with_ordinal_mark_is_grounded():
    assert date_in_text(date(2026, 3, 1), "em 1º de março de 2026") is True


@pytest.mark.parametrize(
    "text",
    [
        "realizada em 24/03/2026",
        "realizada em 23/04/2026",
        "realizada em 23/03/2025",
        "realizada em 23 de abril de 2026",
        "sem nenhuma data",
        "",
    ],
)
def test_date_not_in_the_text_is_not_grounded(text):
    assert date_in_text(date(2026, 3, 23), text) is False


def test_day_inside_a_longer_number_is_not_a_date():
    assert date_in_text(date(2026, 3, 23), "protocolo 123/03/2026") is False


@pytest.mark.parametrize(
    "text",
    ["concluído em Mai/22", "concluído em mai/2022", "concluído em 05/2022", "em maio de 2022"],
)
def test_month_only_date_is_grounded_by_month_and_year(text):
    assert date_in_text(date(2022, 5, 1), text, D.MONTH) is True


@pytest.mark.parametrize("text", ["em Mai/23", "em 06/2022", "em Jun/22", "em 2022", ""])
def test_month_only_date_with_another_month_or_year_is_not_grounded(text):
    assert date_in_text(date(2022, 5, 1), text, D.MONTH) is False


def test_month_year_in_text_does_not_ground_a_full_date():
    assert date_in_text(date(2022, 5, 10), "concluído em Mai/22", D.DAY) is False


def test_year_alone_is_grounded_when_the_year_appears():
    assert date_in_text(date(2022, 1, 1), "no ano de 2022", D.YEAR) is True
    assert date_in_text(date(2022, 1, 1), "no ano de 2023", D.YEAR) is False
    assert date_in_text(date(2022, 1, 1), "protocolo 12022", D.YEAR) is False


# ---------- hours ----------


@pytest.mark.parametrize("text", ["CH 68", "CH 68h", "CH 68 horas", "68 h - CH Docente", "(68)"])
def test_hours_present_as_a_token_are_grounded(text):
    assert hours_in_text(Decimal("68"), text) is True


def test_decimal_hours_are_grounded_with_comma_or_point():
    assert hours_in_text(Decimal("68.5"), "carga horária de 68,5 horas") is True
    assert hours_in_text(Decimal("68.5"), "carga horária de 68.5 horas") is True


def test_thousands_separator_is_accepted():
    assert hours_in_text(Decimal("1200"), "totalizando 1.200 horas") is True
    assert hours_in_text(Decimal("1200"), "totalizando 1200 horas") is True


@pytest.mark.parametrize("text", ["CH 168", "CH 2068", "CH 68,5", "CH 69", "sem horas", ""])
def test_hours_not_present_as_a_token_are_not_grounded(text):
    assert hours_in_text(Decimal("68"), text) is False


# ---------- identifiers ----------


def test_portaria_number_ignores_dots_spaces_and_case():
    assert identifier_in_text("3686/2024", "PORTARIA Nº 3.686/2024 do Reitor") is True
    assert identifier_in_text("3686 / 2024", "Portaria 3686/2024") is True


def test_doi_and_issn_match_ignoring_punctuation_and_case():
    assert identifier_in_text("10.1016/J.JSS.2020.110000", "doi: 10.1016/j.jss.2020.110000") is True
    assert identifier_in_text("1234-5678", "ISSN 12345678") is True
    assert identifier_in_text("1234-5678", "ISSN 1234 5678") is True


@pytest.mark.parametrize("text", ["Portaria 3687/2024", "sem número", ""])
def test_identifier_not_in_the_text_is_not_grounded(text):
    assert identifier_in_text("3686/2024", text) is False


def test_identifier_without_alphanumeric_characters_is_not_grounded():
    assert identifier_in_text("--", "texto -- qualquer") is False


# ---------- titles ----------

TITLE_10 = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"


def test_title_with_all_tokens_in_the_text_is_grounded():
    assert title_in_text(TITLE_10, "O trabalho " + TITLE_10 + " foi defendido") is True


def test_title_with_exactly_90_percent_of_tokens_is_grounded():
    text = "alpha bravo charlie delta echo foxtrot golf hotel india"  # 9 of 10
    assert title_in_text(TITLE_10, text) is True


def test_title_with_80_percent_of_tokens_is_not_grounded():
    text = "alpha bravo charlie delta echo foxtrot golf hotel"  # 8 of 10
    assert title_in_text(TITLE_10, text) is False


def test_title_with_87_percent_of_8_tokens_is_not_grounded():
    title = "alpha bravo charlie delta echo foxtrot golf hotel"
    assert title_in_text(title, "alpha bravo charlie delta echo foxtrot golf") is False


def test_title_matching_ignores_case_accents_and_short_words():
    text = "ESTUDO SOBRE A EDUCAÇÃO NA AMAZÔNIA"
    assert title_in_text("Estudo sobre educação na Amazônia", text) is True
    assert (
        title_in_text("Estudo de IA na educacao da Amazonia", text) is True
    )  # short words ignored
    assert title_in_text("Estudo sobre saude na Amazonia", text) is False  # 'saude' is missing


def test_title_not_in_the_text_is_not_grounded():
    assert title_in_text("Título totalmente inventado pela máquina", "Declaração de banca") is False


# ---------- names ----------


def test_name_with_all_tokens_in_the_text_is_grounded():
    assert (
        name_in_text("Ana Ficticia Lima", "Declaramos que LIMA, Ana Fictícia, participou") is True
    )


def test_name_with_a_missing_token_is_not_grounded():
    assert name_in_text("Ana Ficticia Lima", "Declaramos que Ana Ficticia participou") is False


def test_name_particles_shorter_than_three_letters_are_ignored():
    assert name_in_text("Ana de Lima", "Ana Lima") is True


# ---------- same person ----------


def test_professor_name_contained_in_the_extracted_name_is_the_same_person():
    assert same_person("Ana Ficticia Lima Souza", "Ana Ficticia Lima", "1234567", "") is True


def test_extracted_name_contained_in_the_professor_name_needs_two_tokens():
    assert same_person("Ana Lima", "Ana Maria Lima", "1234567", "") is True
    assert same_person("Lima", "Ana Maria Lima", "1234567", "") is False


def test_case_accents_and_token_order_do_not_matter():
    assert same_person("LIMA, ANA FICTÍCIA", "Ana Ficticia Lima", "1234567", "") is True


def test_other_person_is_not_the_same_person():
    assert same_person("Carlos Imaginario", "Ana Ficticia Lima", "1234567", "texto") is False


def test_siape_in_the_text_is_the_same_person_even_with_another_name():
    assert same_person("Carlos Imaginario", "Ana Ficticia Lima", "1234567", "SIAPE 1234567") is True


def test_siape_inside_a_longer_digit_run_does_not_count():
    assert (
        same_person("Carlos Imaginario", "Ana Ficticia Lima", "1234567", "proc 12345678") is False
    )


def test_missing_extracted_name_depends_on_the_siape_only():
    assert same_person(None, "Ana Ficticia Lima", "1234567", "mat. 1234567") is True
    assert same_person(None, "Ana Ficticia Lima", "1234567", "nada") is False
    assert same_person("", "Ana Ficticia Lima", None, "nada") is False


# ---------- ground ----------

PAGE1 = (
    'Declaramos que Ana Ficticia Lima participou da banca do trabalho "Estudo de caso '
    'fictício sobre bancas" em 23/03/2026. Carga horária: 68 h. Portaria 3686/2024.'
)


def activity(**kw):
    base = {
        "taxonomy": TaxonomyCode.BANCA_TCC_GRADUACAO,
        "page": 1,
        "evidence_text": "participou da banca",
        "confidence": Decimal("0.90"),
    }
    return ExtractedActivity(**(base | kw))


def warning(field):
    return GroundingWarning(DocAlertCode.NAO_ENCONTRADO_NO_TEXTO, field)


def test_all_verifiable_fields_present_keep_their_values_with_ratio_one():
    item = activity(
        title="Estudo de caso fictício sobre bancas",
        event_date=date(2026, 3, 23),
        hours=Decimal("68"),
        identifier="3686/2024",
    )
    result = ground(item, {1: PAGE1})
    assert result.activity == item
    assert result.warnings == ()
    assert result.grounded_ratio == Decimal("1")


def test_invented_date_becomes_none_with_a_warning_naming_the_field():
    item = activity(event_date=date(2026, 3, 24), hours=Decimal("68"))
    result = ground(item, {1: PAGE1})
    assert result.activity.event_date is None
    assert result.activity.hours == Decimal("68")
    assert result.warnings == (warning("event_date"),)
    assert result.grounded_ratio == Decimal("0.5")


def test_each_invented_field_is_nulled_and_reported():
    item = activity(
        title="Título inventado sem relação alguma",
        start_date=date(2020, 1, 2),
        end_date=date(2020, 1, 3),
        event_date=date(2026, 3, 23),
        hours=Decimal("99"),
        course_hours=Decimal("98"),
        identifier="9999/2099",
    )
    result = ground(item, {1: PAGE1})
    assert result.activity.title is None
    assert result.activity.start_date is None
    assert result.activity.end_date is None
    assert result.activity.hours is None
    assert result.activity.course_hours is None
    assert result.activity.identifier is None
    assert result.activity.event_date == date(2026, 3, 23)
    assert {w.field for w in result.warnings} == {
        "title",
        "start_date",
        "end_date",
        "hours",
        "course_hours",
        "identifier",
    }
    assert all(w.code is DocAlertCode.NAO_ENCONTRADO_NO_TEXTO for w in result.warnings)
    assert result.grounded_ratio == Decimal(1) / Decimal(7)


def test_ratio_is_the_fraction_of_verifiable_fields_found():
    item = activity(
        event_date=date(2026, 3, 23),
        hours=Decimal("68"),
        identifier="3686/2024",
        course_hours=Decimal("77"),
    )
    assert ground(item, {1: PAGE1}).grounded_ratio == Decimal("0.75")


def test_only_the_cited_page_is_searched():
    item = activity(page=2, hours=Decimal("68"))
    result = ground(item, {1: PAGE1, 2: "outra página sem números"})
    assert result.activity.hours is None
    assert result.warnings == (warning("hours"),)


def test_missing_cited_page_grounds_nothing():
    result = ground(activity(page=5, hours=Decimal("68")), {1: PAGE1})
    assert result.activity.hours is None
    assert result.warnings == (warning("hours"),)


def test_fields_that_are_none_are_neither_checked_nor_reported():
    result = ground(activity(), {1: PAGE1})
    assert result.activity == activity()
    assert result.warnings == ()
    assert result.grounded_ratio == Decimal("0")


def test_month_precision_is_applied_per_field():
    item = activity(start_date=date(2022, 5, 1), end_date=date(2022, 9, 1))
    page = {1: "Período: Mai/22 a Set/22"}
    precisions = {"start_date": D.MONTH, "end_date": D.MONTH}
    result = ground(item, page, precisions=precisions)
    assert result.activity.start_date == date(2022, 5, 1)
    assert result.activity.end_date == date(2022, 9, 1)
    assert ground(item, page).activity.start_date is None


def test_ground_does_not_change_the_input_item():
    item = activity(hours=Decimal("99"))
    ground(item, {1: PAGE1})
    assert item.hours == Decimal("99")


# ---------- REAL-02, REAL-03: the professor in the page text ----------

PROFESSOR = "Maria Aparecida de Souza Exemplo"


@pytest.mark.parametrize(
    "text",
    [
        "Declaramos que Maria Aparecida de Souza Exemplo participou da banca.",
        "Presidente: MARIA APARECIDA DE SOUZA EXEMPLO (UFPA)",
        "Membro: EXEMPLO, Maria Aparecida de Souza",
        "Membro externo: Maria Aparecida Souza Exemplo",
        "docente maria aparecida de souza exemplo, orientadora",
    ],
)
def test_professor_named_in_the_text_in_any_case_accent_order_or_particles(text):
    assert professor_named_in_text(PROFESSOR, text) is True


def test_professor_named_with_accents_in_the_professor_field_matches_plain_text():
    text = "Jose Ficticio Arvore, membro"
    assert professor_named_in_text("José Fictício da Árvore", text) is True


def test_professor_tokens_scattered_across_the_text_are_not_the_professor():
    text = (
        "Maria Antonia Lima foi a presidente. Aparecida Costa e Joao de Souza assistiram. "
        "A sessão ocorreu na sala onde o Prof. Pedro Exemplo apresentou o trabalho."
    )
    assert professor_named_in_text(PROFESSOR, text) is False


def test_professor_with_a_missing_name_token_is_not_in_the_text():
    assert professor_named_in_text(PROFESSOR, "Maria Aparecida de Souza participou") is False


def test_a_single_token_name_is_never_enough():
    assert professor_named_in_text("Exemplo", "Exemplo") is False


@pytest.mark.parametrize(
    "extracted",
    ["M. A. Souza Exemplo", "EXEMPLO, M. A. S.", "Maria A. Souza Exemplo", "M. Exemplo"],
)
def test_abbreviated_name_with_the_same_initials_and_last_surname_is_the_professor(extracted):
    assert same_person(extracted, PROFESSOR, None, "") is True


@pytest.mark.parametrize(
    "extracted",
    ["J. A. Exemplo", "M. A. Silva", "A. Exemplo", "M. B. Exemplo", "Exemplo"],
)
def test_abbreviation_with_other_initials_or_surname_is_not_the_professor(extracted):
    assert same_person(extracted, PROFESSOR, None, "") is False


# ---------- REAL-04: dates written in words ----------


@pytest.mark.parametrize(
    "text",
    [
        "no vinte e um dias do mês de agosto do ano de dois mil e vinte e quatro, reuniu-se",
        "Aos vinte e um dias do mês de agosto de dois mil e vinte e quatro",
        "em vinte e um de agosto de dois mil e vinte e quatro",
        "em 21 de agosto de dois mil e vinte e quatro",
        "em vinte e um de agosto de 2024",
        "AOS VINTE E UM DIAS DO MÊS DE AGOSTO DO ANO DE DOIS MIL E VINTE E QUATRO",
    ],
)
def test_date_written_in_words_is_found(text):
    assert date_in_text(date(2024, 8, 21), text) is True


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (date(2025, 5, 1), "no primeiro dia do mês de maio de dois mil e vinte e cinco"),
        (date(2019, 12, 31), "trinta e um de dezembro de dois mil e dezenove"),
        (date(2020, 3, 3), "aos três dias do mês de março do ano de dois mil e vinte"),
        (date(2023, 2, 15), "quinze de fevereiro de dois mil e vinte e três"),
    ],
)
def test_other_dates_in_words_are_found(value, text):
    assert date_in_text(value, text) is True


@pytest.mark.parametrize(
    "text",
    [
        "vinte e dois dias do mês de agosto do ano de dois mil e vinte e quatro",
        "vinte e um dias do mês de agosto do ano de dois mil e vinte e três",
        "vinte e um dias do mês de setembro do ano de dois mil e vinte e quatro",
    ],
)
def test_a_different_day_month_or_year_in_words_is_not_found(text):
    assert date_in_text(date(2024, 8, 21), text) is False


def test_year_and_month_precision_read_words_too():
    text = "agosto do ano de dois mil e vinte e quatro"
    assert date_in_text(date(2024, 8, 1), text, D.MONTH) is True
    assert date_in_text(date(2024, 1, 1), "no ano de dois mil e vinte e quatro", D.YEAR) is True
    assert date_in_text(date(2023, 1, 1), "no ano de dois mil e vinte e quatro", D.YEAR) is False


def test_abbreviated_month_named_dez_still_matches_next_to_number_words():
    assert date_in_text(date(2024, 12, 5), "em 5 dez 2024, às dez horas") is True


def test_the_ai_date_in_words_is_kept_by_ground():
    extracted = ExtractedActivity(
        taxonomy=TaxonomyCode.BANCA_MESTRADO,
        page=1,
        evidence_text="x",
        confidence=Decimal("0.9"),
        event_date=date(2024, 8, 21),
    )
    text = "Aos vinte e um dias do mês de agosto do ano de dois mil e vinte e quatro, banca."
    result = ground(extracted, {1: text})
    assert result.activity.event_date == date(2024, 8, 21)
    assert result.warnings == ()


# ---------- REAL-05, REAL-06: date ranges and zero padded hours ----------


@pytest.mark.parametrize(
    "text",
    [
        "de 18 a 22 de maio de 2026",
        "realizado de 18 a 22 de maio de 2026, em Belém",
        "18 a 22 de Maio de 2026",
        "18 à 22 de maio de 2026",
        "18 até 22 de maio de 2026",
        "18 e 22 de maio de 2026",
        "18 - 22 de maio de 2026",
        "dezoito a vinte e dois de maio de dois mil e vinte e seis",
    ],
)
def test_first_and_last_day_of_a_range_are_found(text):
    assert date_in_text(date(2026, 5, 18), text) is True
    assert date_in_text(date(2026, 5, 22), text) is True


@pytest.mark.parametrize("day", [17, 19, 21, 23])
def test_a_day_outside_or_inside_the_range_that_is_not_an_end_is_not_found(day):
    assert date_in_text(date(2026, 5, day), "de 18 a 22 de maio de 2026") is False


def test_range_with_zero_padded_days():
    text = "03 a 05 de dezembro de 2025"
    assert date_in_text(date(2025, 12, 3), text) is True
    assert date_in_text(date(2025, 12, 5), text) is True


def test_range_across_two_months_finds_both_ends_with_the_shared_year():
    text = "de 28 de abril a 2 de maio de 2026"
    assert date_in_text(date(2026, 4, 28), text) is True
    assert date_in_text(date(2026, 5, 2), text) is True


def test_range_of_another_month_or_year_is_not_found():
    text = "18 a 22 de maio de 2026"
    assert date_in_text(date(2026, 6, 18), text) is False
    assert date_in_text(date(2025, 5, 18), text) is False


def test_the_start_date_of_a_range_is_kept_by_ground():
    extracted = ExtractedActivity(
        taxonomy=TaxonomyCode.PARTICIPACAO_EVENTO,
        page=1,
        evidence_text="x",
        confidence=Decimal("0.9"),
        start_date=date(2026, 5, 18),
        end_date=date(2026, 5, 22),
    )
    result = ground(extracted, {1: "Semana de Computação, de 18 a 22 de maio de 2026."})
    assert (result.activity.start_date, result.activity.end_date) == (
        date(2026, 5, 18),
        date(2026, 5, 22),
    )
    assert result.warnings == ()


@pytest.mark.parametrize(
    "text", ["carga horária de 08 horas", "08h", "CH: 008 h", "total 8 horas", "08,"]
)
def test_hours_with_leading_zeros_are_found(text):
    assert hours_in_text(Decimal(8), text) is True


@pytest.mark.parametrize("text", ["108 horas", "carga de 0,8 horas", "1.008 horas", "80 horas"])
def test_leading_zero_tolerance_does_not_match_other_numbers(text):
    assert hours_in_text(Decimal(8), text) is False


# ---------- VER-10: dates written with month and year only ----------


def test_a_first_of_month_date_for_a_month_only_text_is_a_month_precision_field():
    item = activity(event_date=date(2026, 5, 1))
    assert month_only_dates(item, {1: "Evento realizado em maio de 2026, em Belém."}) == {
        "event_date": D.MONTH
    }


@pytest.mark.parametrize("text", ["Evento em 01/05/2026.", "Evento em 1º de maio de 2026."])
def test_a_date_whose_day_is_in_the_text_stays_day_precision(text):
    assert month_only_dates(activity(event_date=date(2026, 5, 1)), {1: text}) == {}


def test_a_day_invented_for_a_month_only_text_is_not_a_month_precision_field():
    item = activity(event_date=date(2026, 5, 15))
    page = {1: "Evento realizado em maio de 2026."}
    assert month_only_dates(item, page) == {}
    assert ground(item, page).activity.event_date is None  # still nulled: never invent a day


def test_a_month_that_is_not_in_the_text_is_not_a_month_precision_field():
    item = activity(event_date=date(2026, 5, 1))
    assert month_only_dates(item, {1: "Evento em junho de 2026."}) == {}


def test_period_boundaries_are_month_precision_independently():
    item = activity(start_date=date(2022, 5, 1), end_date=date(2022, 9, 1))
    page = {1: "Período: Mai/22 a Set/22"}
    assert month_only_dates(item, page) == {"start_date": D.MONTH, "end_date": D.MONTH}
