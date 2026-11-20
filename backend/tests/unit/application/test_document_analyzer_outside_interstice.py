"""FORA-01, FORA-05, FORA-06, FORA-09: a document whose dated activities are all outside the
interstice creates no activity and carries DOCUMENTO_FORA_DO_INTERSTICIO."""

from datetime import date

from app.domain.entities.document import DocAlertCode, DocumentStatus
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason
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
OUTSIDE = DocAlertCode.DOCUMENTO_FORA_DO_INTERSTICIO


TITLE = "Estudo Ficticio sobre Dados Abertos"


def banca_text(*entries: tuple[str, str]) -> str:
    """One sentence per (title, date written in words)."""
    sentences = [
        f"Declaramos que {PROFESSOR}, matricula SIAPE 0000000, participou como membro da banca "
        f"examinadora do trabalho de conclusao de curso {title}, realizada em {when}, "
        "na Faculdade Exemplo de Testes."
        for title, when in entries
    ]
    return "DECLARACAO DE BANCA EXAMINADORA\n" + "\n".join(sentences)


def one_banca(iso: str, title: str = TITLE) -> dict:
    return activity(event_date=iso, title=title)


def analyze(items, text, interstice=INTERSTICE):
    ai = FakeAi(payload(*items))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai), interstice=interstice)


def outside_alerts(result):
    return [a for a in result.alerts if a.code is OUTSIDE]


def test_all_activities_in_2022_create_nothing_and_flag_the_document():
    result = analyze([one_banca("2022-03-10")], banca_text((TITLE, "10 de marco de 2022")))

    assert result.activities == ()
    assert len(outside_alerts(result)) == 1
    assert result.status is DocumentStatus.PROCESSADO
    assert result.status_code == OUTSIDE.value


def test_the_alert_carries_the_document_date_and_the_interstice_dates():
    result = analyze([one_banca("2022-03-10")], banca_text((TITLE, "10 de marco de 2022")))

    [alert] = outside_alerts(result)
    assert alert.detail == {
        "document_date": "2022-03-10",
        "date_precision": "DAY",
        "interstice_start": "2024-11-23",
        "interstice_end": "2026-11-23",
    }


def test_the_document_date_is_the_most_recent_extracted_date():
    first, second = "Primeiro " + TITLE, "Segundo " + TITLE
    text = banca_text((first, "10 de marco de 2022"), (second, "02 de maio de 2023"))
    items = [one_banca("2022-03-10", first), one_banca("2023-05-02", second)]

    result = analyze(items, text)

    assert result.activities == ()
    [alert] = outside_alerts(result)
    assert alert.detail["document_date"] == "2023-05-02"


def test_a_month_only_date_is_reported_with_month_precision():
    result = analyze([one_banca("2022-03-01")], banca_text((TITLE, "marco de 2022")))

    [alert] = outside_alerts(result)
    assert alert.detail["document_date"] == "2022-03-01"
    assert alert.detail["date_precision"] == "MONTH"


def test_an_activity_without_a_scoring_item_still_counts_as_dated_and_outside():
    other = activity(taxonomy="OUTRA", event_date="2022-03-10")

    result = analyze([other], banca_text((TITLE, "10 de marco de 2022")))

    assert result.activities == ()
    assert len(outside_alerts(result)) == 1


def test_one_activity_inside_and_one_outside_are_both_created_without_the_alert():
    first, second = "Primeiro " + TITLE, "Segundo " + TITLE
    text = banca_text((first, "10 de marco de 2022"), (second, "15 de maio de 2025"))
    items = [one_banca("2022-03-10", first), one_banca("2025-05-15", second)]

    result = analyze(items, text)

    assert outside_alerts(result) == []
    assert result.status_code is None
    assert [a.reasons for a in result.activities] == [
        (NotScoredReason.FORA_DO_INTERSTICIO,),
        (),
    ]


def test_an_outside_activity_next_to_one_crossing_the_limit_keeps_the_document_processed():
    crossing = Interstice(date(2025, 3, 15), date(2027, 3, 15))
    first, second = "Primeiro " + TITLE, "Segundo " + TITLE
    text = banca_text((first, "marco de 2025"), (second, "10 de marco de 2022"))
    items = [one_banca("2025-03-01", first), one_banca("2022-03-10", second)]

    result = analyze(items, text, interstice=crossing)

    assert outside_alerts(result) == []
    assert len(result.activities) == 2


def test_without_any_usable_date_the_document_is_processed_as_usual():
    undated = activity(event_date=None)

    result = analyze([undated], banca_text((TITLE, "10 de marco de 2022")))

    assert outside_alerts(result) == []
    assert len(result.activities) == 1
    assert result.status_code is None


def test_a_date_the_page_does_not_carry_is_no_date_and_the_rule_does_not_apply():
    result = analyze([one_banca("2022-03-10")], banca_text((TITLE, "12 de marco de 2023")))

    assert outside_alerts(result) == []
    assert len(result.activities) == 1


def test_without_an_interstice_the_rule_does_not_apply():
    text = banca_text((TITLE, "10 de marco de 2022"))

    result = analyze([one_banca("2022-03-10")], text, interstice=None)

    assert outside_alerts(result) == []
    assert len(result.activities) == 1
