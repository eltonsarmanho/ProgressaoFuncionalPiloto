"""SEG-02: a function with a start date and no term or end is open ended and goes to review."""

from datetime import date
from decimal import Decimal

from app.domain.entities.document import DocAlertCode
from app.domain.rules.interstice import Interstice
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

INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))


def portaria(start_text, role="Vice-diretor"):
    return (
        "PORTARIA N. 200/2026\n"
        f"Designar {PROFESSOR} para exercer a funcao de {role} da Faculdade Exemplo, "
        f"a partir de {start_text}."
    )


def function(taxonomy, start_date, **changes):
    base = {
        "taxonomy": taxonomy,
        "title": "Funcao da Faculdade Exemplo",
        "role": "Funcao",
        "event_date": None,
        "start_date": start_date,
        "evidence_text": f"Designar {PROFESSOR} para exercer a funcao",
    }
    return activity(**(base | changes))


def analyze(item, text):
    ai = FakeAi(payload(item, document_type="PORTARIA"))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai), interstice=INTERSTICE)


# A document whose dated activities are all outside the interstice creates nothing (FORA-01),
# so the checks of an outside activity sit next to a second one that is inside it.
INSIDE_SENTENCE = (
    f"\nDeclaramos que {PROFESSOR} participou como membro da banca examinadora do trabalho de "
    "conclusao de curso Estudo Ficticio sobre Dados Abertos, realizada em 12 de marco de 2025."
)


def analyze_next_to_an_inside_activity(item, text):
    ai = FakeAi(payload(item, activity(), document_type="PORTARIA"))
    page = text_page(1, text + INSIDE_SENTENCE)
    return run(analyzer(FakeTextExtractor(page), ai), interstice=INTERSTICE)


def codes(result):
    return [(a.code, a.activity_index) for a in result.alerts]


def test_vice_director_from_inside_the_interstice_is_open_ended_with_zero_years():
    item = function("FUNCAO_VICE_DIRETOR_FACULDADE", "2026-08-09")
    result = analyze(item, portaria("09/08/2026"))
    [suggested] = result.activities
    assert suggested.extracted.end_date is None  # no end date is made up
    assert (suggested.group_number, suggested.item_number) == (6, 7)
    assert suggested.quantity == Decimal(0)  # 3.5 months to the interstice end
    assert (DocAlertCode.QUANTIDADE_ESTIMADA, 0) in codes(result)
    assert (DocAlertCode.DATA_FIM_AUSENTE, 0) in codes(result)
    assert suggested.reasons == ()  # not FORA_DO_INTERSTICIO
    assert suggested.needs_review is True


def test_director_from_before_the_interstice_counts_the_years_inside_it():
    item = function("FUNCAO_DIRETOR_FACULDADE", "2024-08-09")
    result = analyze(item, portaria("09/08/2024", "Diretor"))
    [suggested] = result.activities
    # 2024-11-23 (interstice start) to 2026-11-23 (interstice end): two complete years
    assert suggested.quantity == Decimal(2)
    assert (DocAlertCode.DATA_FIM_AUSENTE, 0) in codes(result)
    assert suggested.reasons == ()


def test_a_function_starting_after_the_interstice_is_out_of_it():
    item = function("FUNCAO_DIRETOR_FACULDADE", "2027-01-10")
    result = analyze_next_to_an_inside_activity(item, portaria("10/01/2027", "Diretor"))
    suggested = result.activities[0]
    assert [reason.name for reason in suggested.reasons] == ["FORA_DO_INTERSTICIO"]


def test_a_closed_period_does_not_get_the_missing_end_alert():
    item = function("FUNCAO_DIRETOR_FACULDADE", "2025-01-10", end_date="2026-01-09")
    text = portaria("10/01/2025 ate 09/01/2026", "Diretor")
    result = analyze(item, text)
    assert DocAlertCode.DATA_FIM_AUSENTE not in [a.code for a in result.alerts]


def test_an_item_that_is_not_yearly_keeps_the_single_day_and_no_missing_end_alert():
    item = activity(
        taxonomy="CURSO_CONCLUIDO",
        title="Curso Exemplo",
        event_date=None,
        start_date="2024-08-09",
        hours=40,
        evidence_text="concluiu o curso Exemplo",
    )
    text = f"Certificamos que {PROFESSOR} concluiu o curso Exemplo em 09/08/2024, 40 horas."
    result = analyze_next_to_an_inside_activity(item, text)
    suggested = result.activities[0]
    assert [reason.name for reason in suggested.reasons] == ["FORA_DO_INTERSTICIO"]
    assert DocAlertCode.DATA_FIM_AUSENTE not in [a.code for a in result.alerts]
