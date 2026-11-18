"""VINC-02, VINC-03, VINC-05, DOC-13: LinkEvidence and UnlinkEvidence."""

import dataclasses
import uuid
from types import SimpleNamespace

import pytest

from app.application.use_cases.evidences import LinkEvidence, UnlinkEvidence
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, ValidationFailed
from tests.integration.doc_usecases.support import draft_activity, link, pdf, seed_run


@pytest.fixture
def ev(docs):
    w = docs.world
    return SimpleNamespace(
        link=LinkEvidence(w.uow_factory, docs.audit, w.policy),
        unlink=UnlinkEvidence(w.uow_factory, docs.audit, w.policy),
    )


def two_page_doc(docs, label, process=None):
    w = docs.world
    return docs.upload_one(w.docente, process or w.process, pdf(label, pages=2))


def stored_links(docs, document):
    with docs.world.uow_factory() as uow:
        return list(uow.evidences.list_for_document(document.id))


def events(docs, evidence_id):
    with docs.world.uow_factory() as uow:
        return list(uow.audit.list_for("activity_evidence", str(evidence_id)))


def close(docs, process, status):
    with docs.world.uow_factory() as uow:
        current = uow.processes.get(process.id)
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


# --- many to many (VINC-02) ----------------------------------------------------------------


def test_a_document_proves_several_activities_and_an_activity_has_several_documents(docs, ev):
    w = docs.world
    first_doc = two_page_doc(docs, "um")
    second_doc = two_page_doc(docs, "dois")
    a = draft_activity(w, w.process, "Atividade A")
    b = draft_activity(w, w.process, "Atividade B")

    ev.link.execute(w.docente, a.id, first_doc.id, 1)
    ev.link.execute(w.docente, b.id, first_doc.id, 2, "Mesmo documento comprova as duas")
    ev.link.execute(w.docente, a.id, second_doc.id, 1)

    with w.uow_factory() as uow:
        counts = uow.evidences.counts_for_activities([a.id, b.id])
    assert counts == {a.id: 2, b.id: 1}
    assert {(e.activity_id, e.page_number) for e in stored_links(docs, first_doc)} == {
        (a.id, 1),
        (b.id, 2),
    }


def test_same_activity_document_and_page_twice_gives_409_and_other_pages_are_fine(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "pagina")
    activity = draft_activity(w, w.process)
    ev.link.execute(w.docente, activity.id, document.id, 1)

    with pytest.raises(Conflict):
        ev.link.execute(w.docente, activity.id, document.id, 1)
    ev.link.execute(w.docente, activity.id, document.id, 2)

    assert sorted(e.page_number for e in stored_links(docs, document)) == [1, 2]


# --- justification when the document proves another activity (VINC-03) ----------------------


@pytest.mark.parametrize("justification", [None, "", "   "])
def test_linking_a_document_already_linked_elsewhere_needs_no_justification(
    docs, ev, justification
):
    """UIM-16: VINC-03 relaxed; the link is stored and audited without a justification."""
    w = docs.world
    document = two_page_doc(docs, "compartilhado")
    first = draft_activity(w, w.process, "Primeira")
    second = draft_activity(w, w.process, "Segunda")
    link(w, first, document)

    evidence = ev.link.execute(w.docente, second.id, document.id, 1, justification)

    assert {e.activity_id for e in stored_links(docs, document)} == {first.id, second.id}
    [event] = events(docs, evidence.id)
    assert event.action is AuditAction.CREATE
    assert event.justification is None


def test_justified_link_is_stored_and_audited_with_the_justification(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "justificado")
    first = draft_activity(w, w.process, "Primeira")
    second = draft_activity(w, w.process, "Segunda")
    link(w, first, document)
    docs.clock.advance(minutes=3)

    evidence = ev.link.execute(w.secretaria, second.id, document.id, 2, "  Mesma portaria  ")

    [event] = events(docs, evidence.id)
    assert event.user_id == w.secretaria.id
    assert event.occurred_at == docs.clock.now()
    assert event.action is AuditAction.CREATE
    assert event.justification == "Mesma portaria"
    assert event.changes == {
        "activity_id": {"before": None, "after": str(second.id)},
        "document_id": {"before": None, "after": str(document.id)},
        "page_number": {"before": None, "after": 2},
        "operation": {"before": None, "after": "LINK"},
    }


def test_first_link_of_a_document_and_further_pages_of_the_same_activity_need_no_justification(
    docs, ev
):
    w = docs.world
    document = two_page_doc(docs, "livre")
    activity = draft_activity(w, w.process)

    first = ev.link.execute(w.docente, activity.id, document.id, 1)
    second = ev.link.execute(w.docente, activity.id, document.id, 2)

    assert (first.created_by, second.created_by) == (w.docente.id, w.docente.id)
    assert events(docs, first.id)[0].justification is None


# --- consistency -----------------------------------------------------------------------------


def test_document_of_another_process_cannot_be_linked(docs, ev, add_process):
    w = docs.world
    other = add_process()
    foreign = two_page_doc(docs, "de-outro-processo", process=other)
    activity = draft_activity(w, w.process)

    with pytest.raises(ValidationFailed) as error:
        ev.link.execute(w.admin, activity.id, foreign.id, 1, "tentativa")

    assert error.value.field == "documento"
    assert stored_links(docs, foreign) == []


@pytest.mark.parametrize("page", [0, -1, 3])
def test_page_outside_the_document_gives_422_on_pagina(docs, ev, page):
    w = docs.world
    document = two_page_doc(docs, "paginas")
    activity = draft_activity(w, w.process)

    with pytest.raises(ValidationFailed) as error:
        ev.link.execute(w.docente, activity.id, document.id, page)

    assert error.value.field == "pagina"


def test_manual_link_keeps_an_excerpt_of_the_page_text_up_to_300_characters(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "trecho")
    seed_run(w, document, texts=("palavra   " * 120, "segunda"))
    activity = draft_activity(w, w.process)

    evidence = ev.link.execute(w.docente, activity.id, document.id, 1)
    second = ev.link.execute(w.docente, activity.id, document.id, 2)

    assert evidence.excerpt == (" ".join(["palavra"] * 120))[:300]
    assert len(evidence.excerpt) == 300
    assert second.excerpt == "segunda"
    assert evidence.run_id is None


def test_link_to_a_document_never_read_has_an_empty_excerpt(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "nao-lido")
    activity = draft_activity(w, w.process)

    assert ev.link.execute(w.docente, activity.id, document.id, 1).excerpt == ""


# --- access and process state ----------------------------------------------------------------


def test_link_without_access_or_for_unknown_ids_is_not_found(docs, ev, add_process):
    w = docs.world
    document = two_page_doc(docs, "acesso")
    activity = draft_activity(w, w.process)

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            ev.link.execute(actor, activity.id, document.id, 1)
    with pytest.raises(NotFound):
        ev.link.execute(w.admin, uuid.uuid4(), document.id, 1)
    with pytest.raises(NotFound):
        ev.link.execute(w.admin, activity.id, uuid.uuid4(), 1)
    assert stored_links(docs, document) == []


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_link_and_unlink_on_a_closed_process_give_409(docs, ev, add_process, status):
    w = docs.world
    closed = add_process()
    document = two_page_doc(docs, "fechado", process=closed)
    activity = draft_activity(w, closed)
    existing = link(w, activity, document)
    close(docs, closed, status)

    with pytest.raises(Conflict):
        ev.link.execute(w.docente, activity.id, document.id, 2)
    with pytest.raises(Conflict):
        ev.unlink.execute(w.docente, activity.id, existing.id)

    assert [e.id for e in stored_links(docs, document)] == [existing.id]


# --- unlinking (VINC-05) ---------------------------------------------------------------------


def test_unlink_removes_the_link_audits_it_and_keeps_the_activity(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "remover")
    activity = draft_activity(w, w.process, "Mantida")
    evidence = link(w, activity, document, page=2, excerpt="trecho secreto")
    docs.clock.advance(minutes=7)

    ev.unlink.execute(w.secretaria, activity.id, evidence.id)

    assert stored_links(docs, document) == []
    with w.uow_factory() as uow:
        kept = uow.activities.get(activity.id)
        assert uow.evidences.counts_for_activities([activity.id]) == {activity.id: 0}
    assert (kept.title, kept.status) == ("Mantida", ActivityStatus.AGUARDANDO_REVISAO)
    [event] = events(docs, evidence.id)
    assert event.user_id == w.secretaria.id
    assert event.occurred_at == docs.clock.now()
    assert event.action is AuditAction.UPDATE
    assert event.changes == {
        "activity_id": {"before": str(activity.id), "after": None},
        "document_id": {"before": str(document.id), "after": None},
        "page_number": {"before": 2, "after": None},
        "operation": {"before": None, "after": "UNLINK"},
    }
    assert "secreto" not in str(event.changes)


def test_unlink_of_a_link_of_another_activity_or_unknown_is_not_found(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "alheio")
    mine = draft_activity(w, w.process, "Minha")
    other = draft_activity(w, w.process, "Outra")
    theirs = link(w, other, document)

    with pytest.raises(NotFound):
        ev.unlink.execute(w.docente, mine.id, theirs.id)
    with pytest.raises(NotFound):
        ev.unlink.execute(w.docente, mine.id, uuid.uuid4())
    with pytest.raises(NotFound):
        ev.unlink.execute(w.docente, uuid.uuid4(), theirs.id)
    assert [e.id for e in stored_links(docs, document)] == [theirs.id]


def test_unlink_without_access_is_not_found(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "sem-acesso")
    activity = draft_activity(w, w.process)
    evidence = link(w, activity, document)

    for actor in (w.other_docente, w.other_secretaria):
        with pytest.raises(NotFound):
            ev.unlink.execute(actor, activity.id, evidence.id)
    assert len(stored_links(docs, document)) == 1


def test_link_can_be_recreated_after_it_was_removed(docs, ev):
    w = docs.world
    document = two_page_doc(docs, "refazer")
    activity = draft_activity(w, w.process)
    first = ev.link.execute(w.docente, activity.id, document.id, 1)
    ev.unlink.execute(w.docente, activity.id, first.id)

    again = ev.link.execute(w.docente, activity.id, document.id, 1)

    assert again.id != first.id
    assert [e.id for e in stored_links(docs, document)] == [again.id]
