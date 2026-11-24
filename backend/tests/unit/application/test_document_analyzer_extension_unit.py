"""SEG-06: the Pró-Reitoria de Extensão in a header does not make a training an extension course."""

from app.domain.entities.extraction import TaxonomyCode
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

HEADER = "Formação oferecida entre a Pró-Reitoria de Extensão e as faculdades."


def analyze(body):
    item = activity(
        taxonomy="CURSO_EXTENSAO_CONCLUIDO",
        title="Formacao em Dados Abertos",
        event_date=None,
        hours=8,
        evidence_text="concluiu a formacao",
    )
    text = f"{HEADER}\nCertificamos que {PROFESSOR} concluiu a formacao em Dados Abertos. {body}"
    ai = FakeAi(payload(item, document_type="CERTIFICADO"))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai)).activities[0]


def test_a_training_of_8_hours_from_the_pro_reitoria_is_item_vii_10():
    found = analyze("Carga horária: 8 horas.")
    assert found.taxonomy is TaxonomyCode.CURSO_CONCLUIDO
    assert (found.group_number, found.item_number) == (7, 10)


def test_the_same_certificate_that_calls_itself_an_extension_course_is_item_vii_9():
    found = analyze("Curso de extensão, carga horária: 8 horas.")
    assert found.taxonomy is TaxonomyCode.CURSO_EXTENSAO_CONCLUIDO
    assert (found.group_number, found.item_number) == (7, 9)
