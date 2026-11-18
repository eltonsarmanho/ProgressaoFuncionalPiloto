"""TER-07: noisy copies of one activity in one document become one (D4 of the third real run).

The AI sometimes lists a lecture twice with titles that differ by OCR noise ("RPA na Gestao W A |
Academica" and "RPA na Gestao Academica", Jaccard 0.67). Same page, type, level, equal or absent
dates and titles of Jaccard 0.6 or more, or one title inside the other, are one activity.
Different dates, pages, or a different proper name stay apart; courses are never merged this way.
"""

from app.domain.entities.document import DocAlertCode
from tests.unit.application.analyzer_fakes import (
    PROFESSOR,
    FakeAi,
    FakeTextExtractor,
    activity,
    analyzer,
    payload,
    run,
    text_page,
)

STEM = "Banca examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados do aluno"
PAGE = (
    f"CERTIFICADO. Certificamos que {PROFESSOR} proferiu a palestra RPA na Gestao Academica, "
    "em 12 de marco de 2025, na Faculdade Exemplo de Testes."
)


def lecture(title, **changes):
    base = {
        "taxonomy": "PALESTRA",
        "title": title,
        "role": "palestrante",
        "event_date": "2025-03-12",
        "evidence_text": "proferiu a palestra RPA na Gestao Academica",
    }
    return activity(**(base | changes))


def analyze(items, *pages, document_type="CERTIFICADO"):
    ai = FakeAi(payload(*items, document_type=document_type))
    return run(analyzer(FakeTextExtractor(*(pages or (text_page(1, PAGE),))), ai))


def repeated(result):
    return [a.activity_index for a in result.alerts if a.code is DocAlertCode.ATIVIDADE_REPETIDA]


def test_the_ocr_noisy_copy_of_the_title_collapses_into_one_activity():
    noisy, clean = lecture("RPA na Gestao W A | Academica"), lecture("RPA na Gestao Academica")
    result = analyze([noisy, clean])
    assert len(result.activities) == 1
    assert repeated(result) == [1]
    assert (result.activities[0].group_number, result.activities[0].item_number) == (8, 24)


def test_a_title_inside_the_other_collapses_whichever_comes_first():
    short = lecture("RPA na Gestao")
    long = lecture("RPA na Gestao Academica de Cursos Superiores Publicos")
    assert len(analyze([short, long]).activities) == 1
    assert len(analyze([long, short]).activities) == 1


def test_a_dated_and_an_undated_noisy_copy_collapse_and_keep_the_dated_one():
    noisy = lecture("RPA na Gestao W A | Academica", event_date=None)
    result = analyze([noisy, lecture("RPA na Gestao Academica")])
    assert len(result.activities) == 1
    assert str(result.activities[0].extracted.event_date) == "2025-03-12"


def test_alike_titles_on_different_dates_stay_apart():
    text = PAGE + " Nova edicao em 20 de marco de 2025."
    later = lecture("RPA na Gestao Academica", event_date="2025-03-20")
    result = analyze([lecture("RPA na Gestao W A | Academica"), later], text_page(1, text))
    assert len(result.activities) == 2
    assert repeated(result) == []


def test_alike_titles_on_different_pages_stay_apart():
    result = analyze(
        [lecture("RPA na Gestao W A | Academica"), lecture("RPA na Gestao Academica", page=2)],
        text_page(1, PAGE),
        text_page(2, PAGE),
    )
    assert len(result.activities) == 2


def test_overlapping_but_different_dates_do_not_merge_noisy_titles():
    one = lecture("RPA na Gestao W A | Academica", event_date=None, start_date="2025-03-10",
                  end_date="2025-03-14")  # fmt: skip
    two = lecture("RPA na Gestao Academica", event_date=None, start_date="2025-03-12",
                  end_date="2025-03-13")  # fmt: skip
    dates = "de 10/03/2025 a 14/03/2025 e de 12/03/2025 a 13/03/2025"
    text = PAGE.replace("em 12 de marco de 2025", dates)
    assert len(analyze([one, two], text_page(1, text)).activities) == 2


def test_two_board_members_declarations_with_different_names_stay_apart():
    stem = STEM
    text = f"DECLARACAO DE BANCA. {PROFESSOR} participou da banca. {stem} Joao e {stem} Maria."
    banca = {"taxonomy": "BANCA_TCC_GRADUACAO", "evidence_text": "participou da banca"}
    result = analyze(
        [activity(title=f"{stem} Joao", **banca), activity(title=f"{stem} Maria", **banca)],
        text_page(1, text),
        document_type="DECLARACAO_BANCA",
    )
    assert len(result.activities) == 2
    assert repeated(result) == []


def test_the_same_names_in_noisy_titles_still_collapse():
    stem = STEM
    text = f"DECLARACAO DE BANCA. {PROFESSOR} participou da banca. {stem} Joao."
    banca = {"taxonomy": "BANCA_TCC_GRADUACAO", "evidence_text": "participou da banca"}
    result = analyze(
        [activity(title=f"{stem} Joao", **banca), activity(title=f"{stem} Joao W A", **banca)],
        text_page(1, text),
        document_type="DECLARACAO_BANCA",
    )
    assert len(result.activities) == 1


def test_distinct_titles_that_share_few_words_stay_apart():
    one = lecture("RPA na Gestao Academica")
    two = lecture("Inteligencia Artificial na Gestao Publica")
    text = PAGE + " Inteligencia Artificial na Gestao Publica."
    assert len(analyze([one, two], text_page(1, text)).activities) == 2


def test_course_lines_that_look_alike_are_distinct_offers():
    text = f"{PROFESSOR} ministrou Algoritmos, 60 horas, e Algoritmos Avancados, 60 horas."
    base = {
        "taxonomy": "DISCIPLINA_MINISTRADA",
        "event_date": None,
        "hours": 60,
        "level": "GRADUACAO",
        "evidence_text": "Algoritmos, 60 horas",
    }
    result = analyze(
        [activity(title="Algoritmos", **base), activity(title="Algoritmos Avancados", **base)],
        text_page(1, text),
        document_type="DECLARACAO_DISCIPLINAS",
    )
    assert len(result.activities) == 2


def test_titles_with_a_jaccard_of_exactly_0_6_and_neither_inside_the_other_collapse():
    # {rpa, na, gestao, alfa} against {rpa, na, gestao, beta}: 3 of 5 words in common
    page = text_page(1, PAGE + " RPA na Gestao alfa. RPA na Gestao beta.")
    result = analyze([lecture("RPA na Gestao alfa"), lecture("RPA na Gestao beta")], page)
    assert len(result.activities) == 1


def test_titles_with_a_jaccard_below_0_6_and_neither_inside_the_other_stay_apart():
    # 3 of 7 words in common
    page = text_page(1, PAGE + " RPA na Gestao alfa gama. RPA na Gestao beta delta.")
    one, two = lecture("RPA na Gestao alfa gama"), lecture("RPA na Gestao beta delta")
    assert len(analyze([one, two], page).activities) == 2


def test_an_activity_without_a_title_is_not_merged_with_a_titled_one_by_similarity():
    result = analyze([lecture(None), lecture("RPA na Gestao Academica")])
    assert len(result.activities) == 2
