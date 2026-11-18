"""SEG-01: the end of a designation derived from a term written in the page, never invented."""

from datetime import date
from decimal import Decimal

import pytest

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
TERM = "por 2 (dois) anos"
PORTARIA = (
    "PORTARIA N. 100/2024\n"
    f"Designar {PROFESSOR} para exercer a funcao de Diretor da Faculdade Exemplo, "
    f"{TERM}, a partir de 09/08/2024."
)


def director(**changes):
    base = {
        "taxonomy": "FUNCAO_DIRETOR_FACULDADE",
        "title": "Diretor da Faculdade Exemplo",
        "role": "Diretor",
        "event_date": None,
        "start_date": "2024-08-09",
        "end_date": None,
        "term": TERM,
        "evidence_text": f"Designar {PROFESSOR} para exercer a funcao de Diretor",
    }
    return activity(**(base | changes))


def analyze(item, text=PORTARIA):
    ai = FakeAi(payload(item, document_type="PORTARIA"))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai), interstice=INTERSTICE)


def alerts(result, code):
    return [(a.field, a.activity_index) for a in result.alerts if a.code is code]


def test_two_years_from_the_start_gives_the_end_date_and_the_alert():
    [suggested] = analyze(director()).activities
    assert suggested.extracted.start_date == date(2024, 8, 9)
    assert suggested.extracted.end_date == date(2026, 8, 9)
    assert suggested.quantity == Decimal(1)  # 2024-11-23 to 2026-08-09 holds one whole year
    assert (suggested.group_number, suggested.item_number) == (6, 6)


def test_the_derived_end_is_flagged_on_the_activity():
    result = analyze(director())
    assert alerts(result, DocAlertCode.DATA_FIM_DERIVADA) == [("end_date", 0)]


@pytest.mark.parametrize(
    ("term", "end"),
    [
        ("pelo periodo de um ano", date(2025, 8, 9)),
        ("24 meses", date(2026, 8, 9)),
        ("por dois anos", date(2026, 8, 9)),
    ],
)
def test_other_wordings_of_the_term_are_read(term, end):
    text = PORTARIA.replace(TERM, term)
    [suggested] = analyze(director(term=term), text).activities
    assert suggested.extracted.end_date == end


def test_a_term_that_is_not_in_the_page_is_nulled_and_derives_nothing():
    result = analyze(director(term="por 5 (cinco) anos"))
    [suggested] = result.activities
    assert suggested.extracted.term is None
    assert suggested.extracted.end_date is None
    assert alerts(result, DocAlertCode.NAO_ENCONTRADO_NO_TEXTO) == [("term", 0)]
    assert alerts(result, DocAlertCode.DATA_FIM_DERIVADA) == []


def test_a_term_that_cannot_be_read_with_certainty_derives_nothing():
    text = PORTARIA.replace(TERM, "por 3 (dois) anos")
    result = analyze(director(term="por 3 (dois) anos"), text)
    assert result.activities[0].extracted.end_date is None
    assert alerts(result, DocAlertCode.DATA_FIM_DERIVADA) == []


def test_a_start_with_month_and_year_only_derives_nothing():
    text = PORTARIA.replace("a partir de 09/08/2024", "a partir de agosto de 2024")
    result = analyze(director(start_date="2024-08-01"), text)
    [suggested] = result.activities
    assert suggested.extracted.end_date is None
    assert alerts(result, DocAlertCode.DATA_PARCIAL) == [("start_date", 0)]
    assert alerts(result, DocAlertCode.DATA_FIM_DERIVADA) == []


def test_an_end_date_found_in_the_page_wins_over_the_term():
    text = PORTARIA.replace("a partir de 09/08/2024.", "a partir de 09/08/2024 ate 08/08/2026.")
    [suggested] = analyze(director(end_date="2026-08-08"), text).activities
    assert suggested.extracted.end_date == date(2026, 8, 8)


def test_without_a_term_no_end_date_is_made_up():
    result = analyze(director(term=None))
    assert result.activities[0].extracted.end_date is None
    assert alerts(result, DocAlertCode.DATA_FIM_DERIVADA) == []


def test_the_payload_without_the_term_key_is_refused():
    item = director()
    del item["term"]
    result = analyze(item)
    assert result.activities == ()
    assert DocAlertCode.RESPOSTA_INVALIDA in [a.code for a in result.alerts]
