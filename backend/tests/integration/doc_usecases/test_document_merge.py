"""DUP-04, SEC-06: reading or reprocessing a document merges the duplicate activities."""

import logging

from app.application.services.activity_merge import MergeDuplicateActivities
from app.application.services.document_analyzer import DocumentAnalyzer
from app.application.use_cases import document_processing
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.document import DocumentStatus
from app.domain.repositories.ports import JobStatus
from app.domain.rules.activity_validity import InvalidReason, classify_activity
from app.domain.rules.interstice import Interstice
from tests.integration.doc_usecases.test_process_document import (
    banca_payload,
    banca_text,
    process_banca,
    state,
    submit,
)
from tests.unit.application.analyzer_fakes import (
    FakeAi,
    FakeTextExtractor,
    StepClock,
    activity,
    payload,
    text_page,
)

OTHER_TITLE = "Outro Trabalho de Conclusao Bem Diferente"


def live(docs):
    """The activities of the process that are not rejected (the listing leaves merged ones out)."""
    with docs.world.uow_factory() as uow:
        found = uow.activities.list_for_process(docs.world.process.id)
    return [a for a in found if a.status is not ActivityStatus.REJEITADA]


def proofs(docs, activity):
    with docs.world.uow_factory() as uow:
        found = uow.evidences.list_for_activity(activity.id)
    return {(e.document_id, e.page_number) for e in found}


def read(docs, document, answer, text=None):
    w = docs.world
    extractor = FakeTextExtractor(text_page(1, text or banca_text(w)))
    docs.run_next_job(docs.processor(extractor, FakeAi(answer)))
    return document


def test_two_documents_that_lead_to_the_same_activity_become_one_with_both_proofs(docs):
    first = process_banca(docs, "banca-a")
    second = process_banca(docs, "banca-b")

    [only] = live(docs)

    assert proofs(docs, only) == {(first.id, 1), (second.id, 1)}


def test_the_merge_leaves_the_second_row_in_the_database_marked_as_merged(docs):
    process_banca(docs, "banca-a")
    process_banca(docs, "banca-b")

    with docs.world.uow_factory() as uow:
        rows = uow.activities.list_for_process(docs.world.process.id)
        [kept] = rows
        merged = [a for a in uow.activities.list_merged_into(kept.id)]

    assert len(merged) == 1
    assert merged[0].merged_into_id == kept.id


def test_reprocessing_a_document_that_now_duplicates_another_merges_them(docs):
    w = docs.world
    first = process_banca(docs, "banca-a")
    second = submit(docs, "banca-b")
    elsewhere = activity(title=OTHER_TITLE, event_date="2023-06-20")
    read(docs, second, payload(elsewhere, name=w.professor.full_name))
    assert len(live(docs)) == 2  # another title and date: two activities

    docs.reprocess.execute(w.docente, second.id)
    read(docs, second, banca_payload(w))  # the new reading gives the title of the first

    [only] = live(docs)
    assert only.title == "Estudo Ficticio sobre Dados Abertos"
    assert proofs(docs, only) == {(first.id, 1), (second.id, 1)}


def test_an_activity_read_with_a_date_outside_the_interstice_is_created_and_not_valid(
    docs, official_chosen
):
    w = docs.world
    document = submit(docs, "duas-datas")
    answer = payload(
        activity(event_date="2023-03-12"),
        activity(event_date="2020-03-12"),
        name=w.professor.full_name,
    )
    text = banca_text(w) + "\nA mesma banca examinadora reuniu-se tambem em 12 de marco de 2020."

    read(docs, document, answer, text)

    found = state(docs, document)
    assert found.document.status is DocumentStatus.PROCESSADO
    assert sorted(a.event_date.year for a in found.activities) == [2020, 2023]
    with w.uow_factory() as uow:
        version = uow.scoring_tables.get_version(
            uow.processes.get(w.process.id).scoring_table_version_id
        )
    interstice = Interstice(w.process.start_date, w.process.end_date)
    verdicts = {
        a.event_date.year: classify_activity(a, version, interstice, set())
        for a in found.activities
    }
    assert verdicts[2020].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert verdicts[2023].is_valid


def test_a_failure_of_the_merge_keeps_the_reading_and_leaves_nothing_half_merged(
    docs, monkeypatch, caplog
):
    w = docs.world
    process_banca(docs, "banca-a")
    merger = MergeDuplicateActivities(docs.audit)
    real = merger.merge_process

    def merge_then_fail(*args, **kwargs):
        real(*args, **kwargs)  # the merge writes everything, then the step fails
        raise RuntimeError("merge failed")

    monkeypatch.setattr(merger, "merge_process", merge_then_fail)
    document = submit(docs, "banca-b")
    analyzer = DocumentAnalyzer(
        FakeTextExtractor(text_page(1, banca_text(w))), FakeAi(banca_payload(w)), StepClock()
    )
    use_case = document_processing.ProcessDocument(
        w.uow_factory, docs.audit, docs.storage, analyzer, w.create, merger
    )

    with caplog.at_level(logging.ERROR):
        job = docs.run_next_job(use_case)

    found = state(docs, document)
    assert len(found.runs) == 1 and found.pages  # the reading is not lost
    assert len(found.evidences) == 1  # the proof of the document stays linked
    with w.uow_factory() as uow:
        rows = uow.activities.list_for_process(w.process.id)
        finished = uow.jobs.get(job.id)
    assert len(rows) == 2
    assert all(not a.is_merged for a in rows)  # the merge was undone as a whole
    assert finished.status is JobStatus.FALHOU
    assert "ERRO_INTERNO" in caplog.text
