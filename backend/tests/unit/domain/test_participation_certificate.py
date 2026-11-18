"""CER-02: a certificate with hours whose project nature or coordination role is missing.

The AI reads "participated in the development of ... six weeks (18 hours)" as a research or
extension project; the confirmations rightly refuse it (no coordination role, no extension
nature) and the activity falls to OUTRA. A certificate with stated hours is a short course
(VII.10) instead of nothing, and the system, not the document, chose the item.
"""

from decimal import Decimal

import pytest

from app.domain.entities.extraction import DocumentType as D
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import (
    Item,
    reclassify_participation_certificate,
    suggest_item,
)

REFUSED_ORIGINS = [
    T.PESQUISA_PROJETO_COORDENACAO,
    T.PESQUISA_GRUPO_COORDENACAO,
    T.EXTENSAO_PROJETO_COORDENACAO,
    T.EXTENSAO_PROJETO_PARTICIPACAO,
]
EIGHTEEN = Decimal(18)


@pytest.mark.parametrize("claimed", REFUSED_ORIGINS)
def test_a_certificate_with_hours_and_a_refused_project_becomes_a_short_course(claimed):
    assert reclassify_participation_certificate(claimed, T.OUTRA, D.CERTIFICADO, EIGHTEEN) is (
        T.CURSO_CONCLUIDO
    )


def test_the_short_course_is_item_vii_10():
    assert suggest_item(T.CURSO_CONCLUIDO).principal == Item(7, 10)


def test_a_fraction_of_an_hour_is_still_hours():
    result = reclassify_participation_certificate(
        T.PESQUISA_PROJETO_COORDENACAO, T.OUTRA, D.CERTIFICADO, Decimal("0.5")
    )
    assert result is T.CURSO_CONCLUIDO


@pytest.mark.parametrize("hours", [None, Decimal(0)])
@pytest.mark.parametrize("claimed", REFUSED_ORIGINS)
def test_without_hours_the_activity_stays_without_item(claimed, hours):
    assert reclassify_participation_certificate(claimed, T.OUTRA, D.CERTIFICADO, hours) is T.OUTRA


@pytest.mark.parametrize("document_type", [d for d in D if d is not D.CERTIFICADO])
def test_only_a_certificate_is_reclassified(document_type):
    result = reclassify_participation_certificate(
        T.PESQUISA_PROJETO_COORDENACAO, T.OUTRA, document_type, EIGHTEEN
    )
    assert result is T.OUTRA


@pytest.mark.parametrize(
    "claimed",
    [t for t in T if t not in REFUSED_ORIGINS and t is not T.OUTRA],
)
def test_a_taxonomy_that_was_not_a_refused_project_is_left_as_it_was(claimed):
    """Bancas, articles and portaria functions that fell to OUTRA keep no item."""
    assert reclassify_participation_certificate(claimed, T.OUTRA, D.CERTIFICADO, EIGHTEEN) is (
        T.OUTRA
    )


@pytest.mark.parametrize("claimed", REFUSED_ORIGINS)
def test_a_confirmation_that_kept_the_taxonomy_is_not_overridden(claimed):
    """Real coordination or a real extension nature: the confirmed taxonomy stays."""
    assert reclassify_participation_certificate(claimed, claimed, D.CERTIFICADO, EIGHTEEN) is (
        claimed
    )


def test_a_downgrade_to_another_item_is_not_overridden():
    """The extension course that fell to VII.10 by itself, or any non-OUTRA result, stays."""
    result = reclassify_participation_certificate(
        T.EXTENSAO_CURSO_COORDENACAO, T.CURSO_CONCLUIDO, D.CERTIFICADO, EIGHTEEN
    )
    assert result is T.CURSO_CONCLUIDO
    kept = reclassify_participation_certificate(
        T.ARTIGO_INTERNACIONAL_INDEXADO, T.ARTIGO_NAO_INDEXADO, D.CERTIFICADO, EIGHTEEN
    )
    assert kept is T.ARTIGO_NAO_INDEXADO
