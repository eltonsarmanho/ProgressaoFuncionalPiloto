"""DEL-12, DEL-06: the links to a document whose file the conclusion removed stay listed with the
document and the page only, and the page text is not read again."""

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments
from app.application.use_cases.evidences import LinkEvidence, ListEvidences
from app.domain.errors import Gone
from tests.integration.doc_usecases.conclusion_support import add_input_document
from tests.integration.doc_usecases.generation_support import add_activity, link
from tests.integration.doc_usecases.test_purge_inputs import FixedClock


def purge(gen) -> None:
    PurgeInputDocuments(gen.world.uow_factory, gen.originals, FixedClock()).execute(
        gen.world.process.id
    )


def link_uc(gen) -> LinkEvidence:
    return LinkEvidence(gen.world.uow_factory, gen.world.audit, gen.world.policy)


def listed(gen, activity):
    return ListEvidences(gen.world.uow_factory).execute([activity.id])[activity.id]


def links_of(gen, activity):
    with gen.world.uow_factory() as uow:
        found = uow.evidences.list_for_activity(activity.id)
    return [(e.document_id, e.page_number) for e in found]


@pytest.fixture
def case(gen):
    """A document with two pages of text and an activity linked to both pages."""
    document, first = add_input_document(gen)
    with gen.world.uow_factory() as uow:
        activity = uow.activities.get(first.activity_id)
    link(gen.world, activity, document, page=2)
    return document, activity


def test_a_link_to_a_common_document_keeps_the_excerpt_of_the_page_text(gen):
    document, _ = add_input_document(gen)
    other = add_activity(gen.world)

    created = link_uc(gen).execute(gen.world.admin, other.id, document.id, 2)

    assert created.excerpt == "texto da pagina 2"


def test_the_links_of_a_deleted_document_stay_listed_with_document_and_page_and_no_excerpt(
    gen, case
):
    document, activity = case
    before = listed(gen, activity)
    assert [v.evidence.excerpt for v in before] == ["trecho", "trecho"]

    purge(gen)
    after = listed(gen, activity)

    assert [(v.evidence.document_id, v.evidence.page_number) for v in after] == [
        (document.id, 1),
        (document.id, 2),
    ]
    assert [v.evidence.excerpt for v in after] == ["", ""]
    assert [v.document_name for v in after] == [document.original_name] * 2


def test_an_excerpt_left_behind_is_not_listed_once_the_document_is_marked(gen, case):
    document, activity = case
    with gen.world.uow_factory() as uow:
        uow.documents.mark_file_deleted(document.id, FixedClock().now())
        uow.commit()

    assert [v.evidence.excerpt for v in listed(gen, activity)] == ["", ""]


def test_a_new_link_to_a_page_of_a_deleted_document_is_refused(gen, case):
    document, _ = case
    other = add_activity(gen.world)
    purge(gen)

    with pytest.raises(Gone) as error:
        link_uc(gen).execute(gen.world.admin, other.id, document.id, 1)

    assert error.value.code == "ARQUIVO_EXCLUIDO"
    assert links_of(gen, other) == []


def test_a_link_is_refused_for_a_deleted_document_even_when_the_page_does_not_exist(gen, case):
    document, _ = case
    other = add_activity(gen.world)
    purge(gen)

    with pytest.raises(Gone):
        link_uc(gen).execute(gen.world.admin, other.id, document.id, 99)


def test_the_existing_links_are_not_touched_by_a_refused_new_one(gen, case):
    document, activity = case
    purge(gen)

    with pytest.raises(Gone):
        link_uc(gen).execute(gen.world.admin, activity.id, document.id, 1)

    assert links_of(gen, activity) == [(document.id, 1), (document.id, 2)]
