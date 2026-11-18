"""SEG-07: an 18 hour participation certificate is not research coordination (V.1)."""

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


def analyze(text, hours=18):
    item = activity(
        taxonomy="PESQUISA_PROJETO_COORDENACAO",
        title="Policy Brief sobre Dados Abertos",
        event_date="2025-03-12",
        hours=hours,
        evidence_text="participou do desenvolvimento de um policy brief",
    )
    ai = FakeAi(payload(item, document_type="CERTIFICADO"))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai))


def test_a_participation_certificate_creates_no_research_coordination():
    """SEG-07 still holds (no V.1); CER-02 makes the certificate with hours VII.10 instead."""
    result = analyze(
        f"Certificamos que {PROFESSOR} participou do desenvolvimento de um policy brief "
        "sobre Dados Abertos, em 12 de março de 2025, com carga horária de 18 horas."
    )
    [found] = result.activities
    assert (found.group_number, found.item_number) == (7, 10)
    assert found.needs_review is True
    assert [a.code for a in result.alerts if a.activity_index == 0] == [
        DocAlertCode.ENQUADRADO_COMO_CAPACITACAO
    ]


def test_a_participation_certificate_without_hours_has_no_item():
    result = analyze(
        f"Certificamos que {PROFESSOR} participou do desenvolvimento de um policy brief "
        "sobre Dados Abertos, em 12 de março de 2025.",
        hours=None,
    )
    assert result.activities == ()
    assert [a.code for a in result.alerts if a.activity_index == 0] == [
        DocAlertCode.SEM_ITEM_DE_PONTUACAO
    ]


def test_a_declaration_of_coordination_keeps_item_v_1():
    result = analyze(
        f"Declaramos que {PROFESSOR} é coordenadora do projeto de pesquisa Policy Brief sobre "
        "Dados Abertos, 12 de março de 2025, 18 horas. Foi desenvolvido um policy brief."
    )
    [suggested] = result.activities
    assert (suggested.group_number, suggested.item_number) == (5, 1)
