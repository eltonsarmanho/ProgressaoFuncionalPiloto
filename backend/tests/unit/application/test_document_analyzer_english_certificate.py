"""CER-02, CER-04: a one-page english certificate of participation with a workload.

Synthetic text (invented person and policy brief) in the shape of the real case: the PDF text
lost the "ti" glyphs, "CERTIFICATE" comes last, the AI returns a project taxonomy with the role
"participant" and "six weeks (18 hours)" as the term. The document is a certificate with hours,
so it is the short course VII.10, flagged for review; it carries no date and none is derived.
"""

from decimal import Decimal

import pytest

from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import DocumentType
from tests.unit.application.analyzer_fakes import (
    FakeAi,
    FakeTextExtractor,
    activity,
    analyzer,
    payload,
    run,
    text_page,
)

NAME = "Maria Exemplo Silva"
TERM = "six weeks (18 hours)"
CERTIFICATE = (
    "This is to cerfy, for all due purposes, that Maria Exemplo Silva, from the Universidade "
    'Federal Exemplar, parcipated in the development of the policy brief "Open Data for '
    f'Cities", dedicang {TERM} to this acvity as part of the iniaves of the Example Chair on '
    "Open Data.\nChair Coordinator\nCERTIFICATE"
)


def participation(**changes):
    base = {
        "taxonomy": "PESQUISA_PROJETO_COORDENACAO",
        "title": "Open Data for Cities",
        "role": "participant",
        "event_date": None,
        "start_date": None,
        "end_date": None,
        "term": TERM,
        "hours": 18,
        "evidence_text": "parcipated in the development of the policy brief",
    }
    return activity(**(base | changes))


def analyze(item, text=CERTIFICATE, document_type="OUTRO"):
    ai = FakeAi(payload(item, name=NAME, document_type=document_type))
    result = run(analyzer(FakeTextExtractor(text_page(1, text)), ai), professor=NAME)
    return result, ai


def codes(result):
    return [a.code for a in result.alerts]


@pytest.mark.parametrize(
    "taxonomy",
    [
        "PESQUISA_PROJETO_COORDENACAO",
        "PESQUISA_GRUPO_COORDENACAO",
        "EXTENSAO_PROJETO_COORDENACAO",
        "EXTENSAO_PROJETO_PARTICIPACAO",
    ],
)
def test_the_english_certificate_is_one_short_course_flagged_for_review(taxonomy):
    result, _ = analyze(participation(taxonomy=taxonomy))
    [found] = result.activities
    assert (found.group_number, found.item_number) == (7, 10)
    assert found.needs_review is True
    assert found.quantity == Decimal(1)
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO in codes(result)
    assert (DocAlertCode.ENQUADRADO_COMO_CAPACITACAO, 0) in [
        (a.code, a.activity_index) for a in result.alerts
    ]
    assert DocAlertCode.SEM_ITEM_DE_PONTUACAO not in codes(result)


def test_the_text_is_typed_as_a_certificate_before_the_ai_is_asked():
    result, ai = analyze(participation())
    assert result.document_type is DocumentType.CERTIFICADO
    assert ai.calls[0][0] is DocumentType.CERTIFICADO


def test_the_workload_stays_on_the_activity():
    result, _ = analyze(participation())
    [found] = result.activities
    assert found.extracted.hours == Decimal(18)


def test_no_date_is_invented_from_six_weeks():
    result, _ = analyze(participation())
    [found] = result.activities
    extracted = found.extracted
    assert (extracted.start_date, extracted.end_date, extracted.event_date) == (None, None, None)
    assert DocAlertCode.DATA_FIM_DERIVADA not in codes(result)


def test_six_weeks_does_not_derive_an_end_date_even_with_a_start():
    result, _ = analyze(participation(start_date="2025-03-03"), text=CERTIFICATE + " 2025-03-03")
    assert all(a.extracted.end_date is None for a in result.activities)
    assert DocAlertCode.DATA_FIM_DERIVADA not in codes(result)


def test_without_stated_hours_the_activity_stays_without_item():
    result, _ = analyze(participation(hours=None))
    assert result.activities == ()
    assert DocAlertCode.SEM_ITEM_DE_PONTUACAO in codes(result)
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)


def test_hours_that_the_page_does_not_carry_do_not_count():
    """The grounding drops an invented workload, so the certificate has no hours (AD-009)."""
    result, _ = analyze(participation(hours=40))
    assert result.activities == ()
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)


def test_another_document_type_with_the_same_answer_keeps_no_item():
    text = "Project report. " + CERTIFICATE.replace("This is to cerfy", "It is said").replace(
        "CERTIFICATE", ""
    )
    result, _ = analyze(participation(), text=text)
    assert result.document_type is DocumentType.OUTRO
    assert result.activities == ()
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)


def test_real_coordination_keeps_its_item_and_has_no_capacitation_alert():
    text = (
        f"Certificamos que {NAME} foi coordenadora do projeto de pesquisa Dados Abertos para "
        "Cidades, com carga horaria de 18 horas."
    )
    result, _ = analyze(
        participation(
            role="coordenadora",
            title="Dados Abertos para Cidades",
            term=None,
            evidence_text="foi coordenadora do projeto de pesquisa Dados Abertos para Cidades",
        ),
        text=text,
    )
    [found] = result.activities
    assert (found.group_number, found.item_number) == (5, 1)
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)


def test_a_real_extension_nature_keeps_the_extension_item():
    text = (
        f"Certificamos que {NAME} participou do projeto de extensao Dados Abertos para "
        "Cidades, com carga horaria de 18 horas."
    )
    result, _ = analyze(
        participation(
            taxonomy="EXTENSAO_PROJETO_PARTICIPACAO",
            title="Dados Abertos para Cidades",
            term=None,
            evidence_text="participou do projeto de extensao Dados Abertos para Cidades",
        ),
        text=text,
    )
    [found] = result.activities
    assert (found.group_number, found.item_number) == (4, 2)
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)


def test_another_taxonomy_that_fell_to_no_item_is_not_reclassified():
    result, _ = analyze(participation(taxonomy="ARTIGO_NAO_INDEXADO"))
    assert DocAlertCode.ENQUADRADO_COMO_CAPACITACAO not in codes(result)
