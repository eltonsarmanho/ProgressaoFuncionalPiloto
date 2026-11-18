"""TER-06: the indexed article items (VIII.9, VIII.10) need proof of indexing in the text.

The official table words them "revista indexada (ISSN) ... registrada no Qualis CAPES"; the AI
chooses between them and the non-indexed item (VIII.11) on its own, and the page may never
prove the indexing. Without the evidence the item falls to the non-indexed article.
"""

import json
from pathlib import Path

import pytest

from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import Item, confirm_article_indexing, suggest_item
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

TABLE = Path(__file__).resolve().parents[3] / "app/infrastructure/database/seed_data/ufpa.json"
INDEXED = [T.ARTIGO_INTERNACIONAL_INDEXADO, T.ARTIGO_NACIONAL_INDEXADO]

ARTICLE = (
    "Revista Exemplo de Dados, v. 10, n. 2, 2025. ISSN 1234-5678. "
    f"Estudo Ficticio sobre Dados Abertos. {PROFESSOR}. Resumo: este artigo analisa dados. "
    "Palavras-chave: dados abertos; governo."
)


def descriptions():
    groups = json.loads(TABLE.read_text(encoding="utf-8"))["groups"]
    group = next(g for g in groups if g["number"] == 8)
    return {c["item_number"]: c["description"].lower() for c in group["criteria"]}


def test_the_table_words_viii_9_and_viii_10_with_indexing_and_viii_11_without_it():
    items = descriptions()
    assert "indexada" in items[9] and "qualis" in items[9]
    assert "indexada" in items[10] and "qualis" in items[10]
    assert "não indexada" in items[11]
    assert suggest_item(T.ARTIGO_INTERNACIONAL_INDEXADO).principal == Item(8, 9)
    assert suggest_item(T.ARTIGO_NACIONAL_INDEXADO).principal == Item(8, 10)
    assert suggest_item(T.ARTIGO_NAO_INDEXADO).principal == Item(8, 11)


@pytest.mark.parametrize("taxonomy", INDEXED)
@pytest.mark.parametrize(
    "evidence",
    [
        "Fonte: Scopus.",
        "Web of Science Core Collection.",
        "WoS Q1.",
        "Periódico Qualis A1 na área.",
        "JCR 2.4",
        "Fator de impacto (Journal Citation Reports) 3.1",
        "Disponível na SciELO Brasil.",
        "Directory of Open Access Journals (DOAJ)",
        "Bases: LATINDEX.",
        "Bases: PubMed.",
        "Abstracted in MEDLINE.",
        "Revista indexada em bases internacionais.",
        "Revistas indexadas.",
        "Indexação: veja a página da revista.",
        "Indexed journal.",
        "Indexing: see the journal page.",
    ],
)
def test_an_indexing_evidence_in_the_text_keeps_the_indexed_item(taxonomy, evidence):
    assert confirm_article_indexing(taxonomy, f"{ARTICLE} {evidence}") is taxonomy


@pytest.mark.parametrize("taxonomy", INDEXED)
@pytest.mark.parametrize(
    "text",
    [
        ARTICLE,  # an ISSN alone proves nothing
        f"{ARTICLE} Esta revista não é indexada.",
        f"{ARTICLE} Journal not indexed in any database.",
        f"{ARTICLE} Periódico sem indexação.",
        f"{ARTICLE} Trabalhos qualissimos e sem fim.",  # a word that only starts like "qualis"
        "",
    ],
)
def test_without_an_indexing_evidence_the_indexed_item_falls_to_the_non_indexed_article(
    taxonomy, text
):
    downgraded = confirm_article_indexing(taxonomy, text)
    assert downgraded is T.ARTIGO_NAO_INDEXADO
    assert suggest_item(downgraded).principal == Item(8, 11)


@pytest.mark.parametrize("taxonomy", [t for t in T if t not in INDEXED])
def test_every_other_type_passes_through(taxonomy):
    assert confirm_article_indexing(taxonomy, ARTICLE) is taxonomy


# --- through the analyzer ---------------------------------------------------------------------


def article_item(taxonomy):
    return activity(
        taxonomy=taxonomy,
        title="Estudo Ficticio sobre Dados Abertos",
        role="autor",
        event_date=None,
        start_date=None,
        evidence_text="Estudo Ficticio sobre Dados Abertos",
        confidence=0.95,
    )


def analyze(taxonomy, text):
    ai = FakeAi(payload(article_item(taxonomy), document_type="ARTIGO"))
    return run(analyzer(FakeTextExtractor(text_page(1, text)), ai))


def test_an_international_indexed_article_without_evidence_is_viii_11_flagged_and_reviewed():
    result = analyze("ARTIGO_INTERNACIONAL_INDEXADO", ARTICLE)
    [found] = result.activities
    assert (found.group_number, found.item_number) == (8, 11)
    assert found.needs_review is True
    alerts = [(a.code, a.activity_index) for a in result.alerts]
    assert (DocAlertCode.INDEXACAO_NAO_COMPROVADA, 0) in alerts


@pytest.mark.parametrize(
    ("taxonomy", "item"),
    [("ARTIGO_INTERNACIONAL_INDEXADO", 9), ("ARTIGO_NACIONAL_INDEXADO", 10)],
)
def test_an_indexed_article_with_evidence_keeps_its_item_without_the_alert(taxonomy, item):
    result = analyze(taxonomy, f"{ARTICLE} Periodico indexado na Scopus e Qualis A2.")
    [found] = result.activities
    assert (found.group_number, found.item_number) == (8, item)
    assert found.needs_review is False
    assert DocAlertCode.INDEXACAO_NAO_COMPROVADA not in [a.code for a in result.alerts]


def test_a_non_indexed_article_is_not_flagged():
    result = analyze("ARTIGO_NAO_INDEXADO", ARTICLE)
    [found] = result.activities
    assert (found.group_number, found.item_number) == (8, 11)
    assert DocAlertCode.INDEXACAO_NAO_COMPROVADA not in [a.code for a in result.alerts]


def test_the_evidence_may_be_on_any_page_of_the_document():
    pages = (text_page(1, ARTICLE), text_page(2, "Referências. Revista indexada no Scopus."))
    ai = FakeAi(payload(article_item("ARTIGO_INTERNACIONAL_INDEXADO"), document_type="ARTIGO"))
    result = run(analyzer(FakeTextExtractor(*pages), ai))
    assert (result.activities[0].group_number, result.activities[0].item_number) == (8, 9)

