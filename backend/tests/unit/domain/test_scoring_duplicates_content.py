"""SEG-05: two activities of the same item from two documents with the same text."""

from datetime import UTC, date, datetime
from uuid import uuid4

from app.domain.entities.activity import Activity
from app.domain.rules.scoring_duplicates import content_hash, find_duplicates

DAY = date(2025, 5, 10)


def activity(title, created=1, item=(7, 10), **kwargs) -> Activity:
    kwargs.setdefault("event_date", DAY)
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        title=title,
        created_by=uuid4(),
        group_number=item[0],
        item_number=item[1],
        created_at=datetime(2025, 6, created, tzinfo=UTC),
        **kwargs,
    )


def test_the_hash_ignores_case_accents_and_spacing_but_not_words():
    assert content_hash(["Certificamos que a Docente  concluiu\no curso"]) == content_hash(
        ["certificamos que a docente concluiu o curso"]
    )
    assert content_hash(["Certificamos que concluiu"]) != content_hash(["Certificamos que não"])
    assert content_hash(["pagina um", "pagina dois"]) != content_hash(["pagina dois", "pagina um"])


def test_same_item_and_date_from_documents_with_the_same_text_are_duplicates():
    older = activity("Oficina de dados abertos")
    newer = activity("Certificado de participacao no evento", created=2)
    doc_a, doc_b, text = uuid4(), uuid4(), content_hash(["o mesmo certificado"])
    contents = {older.id: {(doc_a, text)}, newer.id: {(doc_b, text)}}

    assert find_duplicates([older, newer], contents) == {newer.id}


def test_two_activities_of_the_same_document_are_never_content_duplicates():
    first = activity("Oficina de dados abertos")
    second = activity("Certificado de participacao no evento", created=2)
    doc, text = uuid4(), content_hash(["um documento com duas atividades"])
    contents = {first.id: {(doc, text)}, second.id: {(doc, text)}}

    assert find_duplicates([first, second], contents) == set()


def test_documents_with_different_text_do_not_make_duplicates():
    older = activity("Oficina de dados abertos")
    newer = activity("Certificado de participacao no evento", created=2)
    contents = {
        older.id: {(uuid4(), content_hash(["texto um"]))},
        newer.id: {(uuid4(), content_hash(["texto dois"]))},
    }

    assert find_duplicates([older, newer], contents) == set()


def test_the_same_text_with_another_item_or_date_is_not_a_duplicate():
    base = activity("Oficina de dados abertos")
    other_item = activity("Certificado de participacao", created=2, item=(7, 9))
    other_day = activity("Certificado de evento", created=3, event_date=date(2025, 9, 1))
    text = content_hash(["o mesmo certificado"])
    contents = {a.id: {(uuid4(), text)} for a in (base, other_item, other_day)}

    assert find_duplicates([base, other_item, other_day], contents) == set()


def test_without_contents_nothing_changes():
    older = activity("Oficina de dados abertos")
    newer = activity("Certificado de participacao no evento", created=2)
    assert find_duplicates([older, newer]) == set()
