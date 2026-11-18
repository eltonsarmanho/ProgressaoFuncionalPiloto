"""SEG-05: documents of one process with the same text count their activity once."""

from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import RowStatus
from tests.integration.doc_usecases.support import seed_run
from tests.integration.scoring.test_process_score_evidence import (
    add,
    link,
    new_document,
    row,
    score,
)

CERTIFICATE = "Certificamos que a docente concluiu o curso Dados Abertos, 40 horas."


def document_with_text(world, *pages):
    document = new_document(world)
    seed_run(world, document, texts=pages)
    return document


def test_the_later_activity_of_an_identical_document_is_a_duplicate(official_chosen):
    world = official_chosen
    # two files with different bytes but the same text; the AI titled the activities apart
    doc_a = document_with_text(world, CERTIFICATE)
    doc_b = document_with_text(
        world, "  CERTIFICAMOS que a docente\nconcluiu o curso Dados Abertos, 40 horas. "
    )
    first = add(world, "Curso de Dados Abertos concluido")
    second = add(world, "Certificado de conclusao: dados abertos e governo digital")
    link(world, first, doc_a)
    link(world, second, doc_b)

    result = score(world).result

    assert row(result, first).status is not RowStatus.NAO_PONTUADA
    assert row(result, second).status is RowStatus.NAO_PONTUADA
    assert row(result, second).reasons == (NotScoredReason.DUPLICIDADE,)


def test_documents_with_different_text_keep_both_activities(official_chosen):
    world = official_chosen
    doc_a = document_with_text(world, CERTIFICATE)
    doc_b = document_with_text(
        world, "Certificamos que a docente ministrou a palestra Governo Digital."
    )
    first = add(world, "Curso de Dados Abertos concluido")
    second = add(world, "Palestra sobre governo digital")
    link(world, first, doc_a)
    link(world, second, doc_b)

    result = score(world).result

    assert row(result, first).reasons == ()
    assert row(result, second).reasons == ()


def test_two_activities_of_one_document_are_not_content_duplicates(official_chosen):
    world = official_chosen
    document = document_with_text(world, CERTIFICATE)
    first = add(world, "Curso de Dados Abertos concluido")
    second = add(world, "Certificado de conclusao: dados abertos e governo digital")
    link(world, first, document)
    link(world, second, document, page=2)

    result = score(world).result

    assert row(result, second).reasons == ()


def test_documents_without_readable_text_are_not_content_duplicates(official_chosen):
    world = official_chosen
    # two unreadable files (OCR found nothing) are not "the same text" (TER-09)
    doc_a = document_with_text(world, "", "")
    doc_b = document_with_text(world, "", "")
    first = add(world, "Curso de Dados Abertos concluido")
    second = add(world, "Certificado de conclusao: dados abertos e governo digital")
    link(world, first, doc_a)
    link(world, second, doc_b)

    result = score(world).result

    assert row(result, first).reasons == ()
    assert row(result, second).reasons == ()
