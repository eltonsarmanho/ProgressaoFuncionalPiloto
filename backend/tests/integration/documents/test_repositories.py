"""PIPE-01, PIPE-03, DOC-07, DOC-14: document, extraction, job and evidence repositories."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.domain.entities.document import (
    DocumentStatus,
    PageText,
    RunStatus,
    TextMethod,
)
from app.domain.entities.user import Role, User
from app.domain.errors import Conflict, NotFound, StaleVersion
from app.domain.repositories.ports import ActivityEvidence, JobStatus, ProcessingJob
from app.domain.rules.scoring_duplicates import content_hash
from tests.integration.documents.factories import make_document, make_run
from tests.integration.test_scoring_repositories import make_activity

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)


def add_documents(uow_factory, *documents):
    with uow_factory() as uow:
        for document in documents:
            uow.documents.add(document)
        uow.commit()


def make_job(document_id, **kwargs) -> ProcessingJob:
    return ProcessingJob(id=uuid.uuid4(), document_id=document_id, **kwargs)


# --- documents -----------------------------------------------------------------------------


def test_document_round_trip(uow_factory, process, base):
    document = make_document(
        process,
        base["admin"].id,
        status_code="TEMPO_ESGOTADO",
        manual_type="CERTIFICADO",
        manual_category="Curso",
        suggested_type="DECLARACAO_BANCA",
        suggested_category="Banca",
        confidence=Decimal("0.85"),
    )
    add_documents(uow_factory, document)

    with uow_factory() as uow:
        loaded = uow.documents.get(document.id)

    assert loaded == document


def test_get_unknown_document_returns_none(uow_factory):
    with uow_factory() as uow:
        assert uow.documents.get(uuid.uuid4()) is None


def test_same_hash_in_the_same_process_conflicts_and_names_the_existing_document(
    uow_factory, process, base
):
    first = make_document(process, base["admin"].id, sha256="c" * 64)
    add_documents(uow_factory, first)

    duplicate = make_document(process, base["admin"].id, sha256="c" * 64)
    with uow_factory() as uow, pytest.raises(Conflict, match=str(first.id)):
        uow.documents.add(duplicate)

    with uow_factory() as uow:
        assert uow.documents.count_for_process(process.id) == 1
        assert uow.documents.get(duplicate.id) is None


def test_same_hash_in_another_process_is_accepted(uow_factory, process, other_process, base):
    user_id = base["admin"].id
    add_documents(
        uow_factory,
        make_document(process, user_id, sha256="d" * 64),
        make_document(other_process, user_id, sha256="d" * 64),
    )
    with uow_factory() as uow:
        assert uow.documents.count_for_process(process.id) == 1
        assert uow.documents.count_for_process(other_process.id) == 1


def test_exists_hash_returns_the_id_only_inside_the_process(
    uow_factory, process, other_process, base
):
    document = make_document(process, base["admin"].id, sha256="e" * 64)
    add_documents(uow_factory, document)

    with uow_factory() as uow:
        assert uow.documents.exists_hash(process.id, "e" * 64) == document.id
        assert uow.documents.exists_hash(process.id, "f" * 64) is None
        assert uow.documents.exists_hash(other_process.id, "e" * 64) is None


def test_count_for_process_counts_only_that_process(uow_factory, process, other_process, base):
    user_id = base["admin"].id
    add_documents(
        uow_factory,
        make_document(process, user_id),
        make_document(process, user_id),
        make_document(process, user_id),
        make_document(other_process, user_id),
    )
    with uow_factory() as uow:
        assert uow.documents.count_for_process(process.id) == 3
        assert uow.documents.count_for_process(other_process.id) == 1
        assert uow.documents.count_for_process(uuid.uuid4()) == 0


def test_count_uploads_by_user_since_uses_upload_time_and_the_user(uow_factory, process, base):
    admin_id = base["admin"].id
    other_user = uuid.uuid4()

    with uow_factory() as uow:
        uow.users.add(User(other_user, "outro@ufpa.br", "Outro", Role.ADMIN, "$argon2id$x"))
        uow.commit()
    add_documents(
        uow_factory,
        make_document(process, admin_id, uploaded_at=NOW - timedelta(seconds=10)),
        make_document(process, admin_id, uploaded_at=NOW - timedelta(seconds=59)),
        make_document(process, admin_id, uploaded_at=NOW - timedelta(seconds=61)),
        make_document(process, admin_id, uploaded_at=NOW - timedelta(hours=3)),
        make_document(process, other_user, uploaded_at=NOW - timedelta(seconds=5)),
    )
    with uow_factory() as uow:
        since = NOW - timedelta(minutes=1)
        assert uow.documents.count_uploads_by_user_since(admin_id, since) == 2
        assert uow.documents.count_uploads_by_user_since(other_user, since) == 1
        assert uow.documents.count_uploads_by_user_since(uuid.uuid4(), since) == 0


def test_list_for_process_is_in_upload_order_and_filters_by_status_and_type(
    uow_factory, process, other_process, base
):
    user_id = base["admin"].id
    first = make_document(
        process, user_id, uploaded_at=NOW - timedelta(minutes=3), suggested_type="ARTIGO"
    )
    second = make_document(
        process,
        user_id,
        uploaded_at=NOW - timedelta(minutes=2),
        status=DocumentStatus.PROCESSADO,
        suggested_type="CERTIFICADO",
        manual_type="ARTIGO",
    )
    third = make_document(
        process,
        user_id,
        uploaded_at=NOW - timedelta(minutes=1),
        status=DocumentStatus.PROCESSADO,
        suggested_type="CERTIFICADO",
    )
    elsewhere = make_document(other_process, user_id)
    add_documents(uow_factory, third, first, second, elsewhere)

    with uow_factory() as uow:
        everything = uow.documents.list_for_process(process.id)
        processed = uow.documents.list_for_process(process.id, status=DocumentStatus.PROCESSADO)
        articles = uow.documents.list_for_process(process.id, document_type="ARTIGO")
        certificates = uow.documents.list_for_process(process.id, document_type="CERTIFICADO")

    assert [d.id for d in everything] == [first.id, second.id, third.id]
    assert [d.id for d in processed] == [second.id, third.id]
    # the manual type wins over the suggested one
    assert [d.id for d in articles] == [first.id, second.id]
    assert [d.id for d in certificates] == [third.id]


def test_document_update_bumps_the_version_and_stale_updates_are_refused(
    uow_factory, process, base
):
    document = make_document(process, base["admin"].id)
    add_documents(uow_factory, document)

    with uow_factory() as uow:
        loaded = uow.documents.get(document.id)
        loaded.status = DocumentStatus.PROCESSANDO
        loaded.suggested_type = "ATA_DEFESA"
        uow.documents.update(loaded, expected_version=1)
        uow.commit()
        assert loaded.version == 2

    with uow_factory() as uow:
        again = uow.documents.get(document.id)
        assert (again.status, again.suggested_type, again.version) == (
            DocumentStatus.PROCESSANDO,
            "ATA_DEFESA",
            2,
        )
        with pytest.raises(StaleVersion):
            uow.documents.update(again, expected_version=1)


def test_updating_an_unknown_document_raises_not_found(uow_factory, process, base):
    ghost = make_document(process, base["admin"].id)
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.documents.update(ghost, expected_version=1)


# --- extraction runs and pages ---------------------------------------------------------------


def test_run_round_trip_and_status_change(uow_factory, process, base):
    document = make_document(process, base["admin"].id)
    add_documents(uow_factory, document)
    run = make_run(document.id, raw_json={"atividades": [{"titulo": "Banca"}]})
    with uow_factory() as uow:
        uow.extractions.add_run(run)
        uow.commit()

    with uow_factory() as uow:
        assert list(uow.extractions.list_runs(document.id)) == [run]
        uow.extractions.mark_run_status(run.id, RunStatus.SUBSTITUIDA)
        uow.commit()

    with uow_factory() as uow:
        (loaded,) = uow.extractions.list_runs(document.id)
    assert loaded.status is RunStatus.SUBSTITUIDA
    assert loaded.raw_json == run.raw_json
    assert loaded.warnings == ("TRUNCADO",)


def test_marking_an_unknown_run_raises_not_found(uow_factory):
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.extractions.mark_run_status(uuid.uuid4(), RunStatus.SUBSTITUIDA)


def _page(document_id, run_id, number, text="texto", method=TextMethod.TEXTO, confidence=None):
    return PageText(document_id, run_id, number, method, len(text), confidence, text)


def test_replace_pages_swaps_the_stored_pages_and_lists_them_by_page(uow_factory, process, base):
    document = make_document(process, base["admin"].id)
    add_documents(uow_factory, document)
    old_run, new_run = make_run(document.id), make_run(document.id)
    with uow_factory() as uow:
        uow.extractions.add_run(old_run)
        uow.extractions.add_run(new_run)
        uow.extractions.replace_pages(
            document.id, [_page(document.id, old_run.id, 1), _page(document.id, old_run.id, 2)]
        )
        uow.commit()

    new_pages = [
        _page(document.id, new_run.id, 2, "segunda", TextMethod.OCR, Decimal("87.50")),
        _page(document.id, new_run.id, 1, "primeira"),
    ]
    with uow_factory() as uow:
        uow.extractions.replace_pages(document.id, new_pages)
        uow.commit()

    with uow_factory() as uow:
        stored = uow.extractions.list_pages(document.id)
    assert stored == [new_pages[1], new_pages[0]]
    assert stored[1].ocr_confidence == Decimal("87.50")


def test_replace_pages_only_touches_the_given_document(uow_factory, process, base):
    first = make_document(process, base["admin"].id)
    second = make_document(process, base["admin"].id)
    add_documents(uow_factory, first, second)
    run_a, run_b = make_run(first.id), make_run(second.id)
    with uow_factory() as uow:
        uow.extractions.add_run(run_a)
        uow.extractions.add_run(run_b)
        uow.extractions.replace_pages(first.id, [_page(first.id, run_a.id, 1)])
        uow.extractions.replace_pages(second.id, [_page(second.id, run_b.id, 1)])
        uow.extractions.replace_pages(first.id, [])
        uow.commit()

    with uow_factory() as uow:
        assert uow.extractions.list_pages(first.id) == []
        assert len(uow.extractions.list_pages(second.id)) == 1


# --- jobs ------------------------------------------------------------------------------------


@pytest.fixture
def three_documents(uow_factory, process, base):
    documents = [make_document(process, base["admin"].id) for _ in range(3)]
    add_documents(uow_factory, *documents)
    return documents


def test_job_is_active_until_finished(uow_factory, three_documents):
    document = three_documents[0]
    job = make_job(document.id)
    with uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id) is None
        uow.jobs.add(job)
        uow.commit()

    with uow_factory() as uow:
        active = uow.jobs.active_for_document(document.id)
        assert (active.id, active.status, active.attempts) == (job.id, JobStatus.PENDENTE, 0)
        uow.jobs.finish(job.id, JobStatus.CONCLUIDA, NOW)
        uow.commit()

    with uow_factory() as uow:
        assert uow.jobs.active_for_document(document.id) is None


def test_second_active_job_for_the_same_document_conflicts(uow_factory, three_documents):
    document = three_documents[0]
    with uow_factory() as uow:
        uow.jobs.add(make_job(document.id))
        uow.commit()
    with uow_factory() as uow, pytest.raises(Conflict):
        uow.jobs.add(make_job(document.id))


def test_claim_takes_the_oldest_pending_job_and_marks_it_processing(uow_factory, three_documents):
    older = make_job(three_documents[0].id, created_at=NOW - timedelta(minutes=2))
    newer = make_job(three_documents[1].id, created_at=NOW - timedelta(minutes=1))
    with uow_factory() as uow:
        uow.jobs.add(newer)
        uow.jobs.add(older)
        uow.commit()

    with uow_factory() as uow:
        claimed = uow.jobs.claim_next(NOW)
        uow.commit()

    assert claimed.id == older.id
    assert claimed.status is JobStatus.PROCESSANDO
    assert claimed.attempts == 1
    assert claimed.started_at == NOW
    with uow_factory() as uow:
        active = uow.jobs.active_for_document(three_documents[0].id)
        assert (active.status, active.attempts, active.started_at) == (
            JobStatus.PROCESSANDO,
            1,
            NOW,
        )
        assert uow.jobs.active_for_document(three_documents[1].id).status is JobStatus.PENDENTE


def test_claim_returns_none_when_nothing_is_pending(uow_factory, three_documents):
    with uow_factory() as uow:
        assert uow.jobs.claim_next(NOW) is None
        uow.jobs.add(make_job(three_documents[0].id, status=JobStatus.CONCLUIDA))
        uow.commit()
    with uow_factory() as uow:
        assert uow.jobs.claim_next(NOW) is None


def test_two_concurrent_claims_never_take_the_same_job(uow_factory, three_documents):
    first = make_job(three_documents[0].id, created_at=NOW - timedelta(minutes=2))
    second = make_job(three_documents[1].id, created_at=NOW - timedelta(minutes=1))
    with uow_factory() as uow:
        uow.jobs.add(first)
        uow.jobs.add(second)
        uow.commit()

    with uow_factory() as uow_a, uow_factory() as uow_b:
        claim_a = uow_a.jobs.claim_next(NOW)  # holds its row lock: not committed yet
        claim_b = uow_b.jobs.claim_next(NOW)
        assert claim_a.id == first.id
        assert claim_b.id == second.id
        # nothing is left for a third claim
        with uow_factory() as uow_c:
            assert uow_c.jobs.claim_next(NOW) is None


def test_a_claim_skips_a_job_locked_by_another_session_instead_of_waiting(
    uow_factory, three_documents
):
    only = make_job(three_documents[0].id)
    with uow_factory() as uow:
        uow.jobs.add(only)
        uow.commit()

    with uow_factory() as uow_a, uow_factory() as uow_b:
        assert uow_a.jobs.claim_next(NOW).id == only.id
        assert uow_b.jobs.claim_next(NOW) is None


def test_finish_records_status_time_and_error_code(uow_factory, engine, three_documents):
    job = make_job(three_documents[0].id)
    with uow_factory() as uow:
        uow.jobs.add(job)
        uow.commit()
    with uow_factory() as uow:
        uow.jobs.claim_next(NOW)
        uow.jobs.finish(job.id, JobStatus.FALHOU, NOW + timedelta(seconds=30), "TEMPO_ESGOTADO")
        uow.commit()

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, error_code, finished_at FROM processing_jobs")
        ).one()
    assert row.status == "FALHOU"
    assert row.error_code == "TEMPO_ESGOTADO"
    assert row.finished_at == NOW + timedelta(seconds=30)


def test_finishing_an_unknown_job_raises_not_found(uow_factory):
    with uow_factory() as uow, pytest.raises(NotFound):
        uow.jobs.finish(uuid.uuid4(), JobStatus.CONCLUIDA, NOW)


def test_recover_stuck_puts_processing_jobs_back_to_pending(uow_factory, three_documents):
    stuck = make_job(three_documents[0].id, created_at=NOW - timedelta(minutes=2))
    waiting = make_job(three_documents[1].id, created_at=NOW - timedelta(minutes=1))
    done = make_job(three_documents[2].id, status=JobStatus.CONCLUIDA)
    with uow_factory() as uow:
        for job in (stuck, waiting, done):
            uow.jobs.add(job)
        uow.commit()
    with uow_factory() as uow:
        assert uow.jobs.claim_next(NOW).id == stuck.id
        uow.commit()

    with uow_factory() as uow:
        assert uow.jobs.recover_stuck() == 1
        uow.commit()

    with uow_factory() as uow:
        assert uow.jobs.active_for_document(three_documents[0].id).status is JobStatus.PENDENTE
        assert uow.jobs.active_for_document(three_documents[1].id).status is JobStatus.PENDENTE
        assert uow.jobs.active_for_document(three_documents[2].id) is None
        assert uow.jobs.recover_stuck() == 0


def test_recover_stuck_skips_a_job_at_the_attempt_limit_and_exhaust_stuck_fails_it(
    uow_factory, three_documents
):
    tired = make_job(three_documents[0].id, created_at=NOW - timedelta(minutes=2))
    fresh = make_job(three_documents[1].id, created_at=NOW - timedelta(minutes=1))
    with uow_factory() as uow:
        uow.jobs.add(tired)
        uow.jobs.add(fresh)
        uow.commit()
    for _ in range(3):  # the oldest job is claimed three times
        with uow_factory() as uow:
            uow.jobs.claim_next(NOW)
            uow.commit()
            uow.jobs.recover_stuck(max_attempts=99)
            uow.commit()
    with uow_factory() as uow:
        assert uow.jobs.claim_next(NOW).id == tired.id  # claimed a fourth time: attempts == 4
        uow.commit()
        assert uow.jobs.claim_next(NOW).id == fresh.id  # attempts == 1
        uow.commit()

    with uow_factory() as uow:
        exhausted = uow.jobs.exhaust_stuck(max_attempts=3, now=NOW)
        recovered = uow.jobs.recover_stuck(max_attempts=3)
        uow.commit()

    assert [job.id for job in exhausted] == [tired.id]
    assert recovered == 1
    with uow_factory() as uow:
        failed = uow.jobs.get(tired.id)
        assert (failed.status, failed.error_code, failed.finished_at) == (
            JobStatus.FALHOU,
            "TENTATIVAS_ESGOTADAS",
            NOW,
        )
        assert uow.jobs.get(fresh.id).status is JobStatus.PENDENTE
        assert uow.jobs.exhaust_stuck(max_attempts=3, now=NOW) == []


# --- evidences -------------------------------------------------------------------------------


@pytest.fixture
def linked(uow_factory, process, base):
    """Two activities and two documents of one process."""
    user_id = base["admin"].id
    activities = [make_activity(process, base), make_activity(process, base)]
    documents = [make_document(process, user_id), make_document(process, user_id)]
    with uow_factory() as uow:
        for activity in activities:
            uow.activities.add(activity)
        for document in documents:
            uow.documents.add(document)
        uow.commit()
    return activities, documents, user_id


def make_evidence(activity, document, user_id, page=1, **kwargs) -> ActivityEvidence:
    return ActivityEvidence(
        id=uuid.uuid4(),
        activity_id=activity.id,
        document_id=document.id,
        page_number=page,
        excerpt="Declaramos que o docente participou da banca.",
        created_by=user_id,
        **kwargs,
    )


def test_evidence_round_trip_by_activity_and_by_document(uow_factory, linked):
    (act1, act2), (doc1, doc2), user_id = linked
    a = make_evidence(act1, doc1, user_id, page=1)
    b = make_evidence(act1, doc2, user_id, page=3)
    c = make_evidence(act2, doc1, user_id, page=2)
    with uow_factory() as uow:
        for evidence in (a, b, c):
            uow.evidences.add(evidence)
        uow.commit()

    with uow_factory() as uow:
        by_activity = uow.evidences.list_for_activity(act1.id)
        by_document = uow.evidences.list_for_document(doc1.id)
    assert {(e.id, e.document_id, e.page_number) for e in by_activity} == {
        (a.id, doc1.id, 1),
        (b.id, doc2.id, 3),
    }
    assert {(e.id, e.activity_id, e.excerpt) for e in by_document} == {
        (a.id, act1.id, a.excerpt),
        (c.id, act2.id, c.excerpt),
    }
    assert all(e.created_at is not None for e in by_activity)


def test_duplicate_activity_document_page_link_conflicts(uow_factory, linked):
    (act1, _), (doc1, _), user_id = linked
    with uow_factory() as uow:
        uow.evidences.add(make_evidence(act1, doc1, user_id, page=1))
        uow.commit()
    with uow_factory() as uow:
        with pytest.raises(Conflict):
            uow.evidences.add(make_evidence(act1, doc1, user_id, page=1))
    with uow_factory() as uow:
        uow.evidences.add(make_evidence(act1, doc1, user_id, page=2))
        uow.commit()


def test_remove_deletes_only_that_link_and_unknown_id_raises(uow_factory, linked):
    (act1, _), (doc1, doc2), user_id = linked
    keep = make_evidence(act1, doc2, user_id)
    drop = make_evidence(act1, doc1, user_id)
    with uow_factory() as uow:
        uow.evidences.add(keep)
        uow.evidences.add(drop)
        uow.commit()

    with uow_factory() as uow:
        uow.evidences.remove(drop.id)
        with pytest.raises(NotFound):
            uow.evidences.remove(uuid.uuid4())
        uow.commit()

    with uow_factory() as uow:
        assert [e.id for e in uow.evidences.list_for_activity(act1.id)] == [keep.id]
        assert uow.activities.get(act1.id) is not None


def test_counts_for_activities_counts_links_per_activity(uow_factory, linked):
    (act1, act2), (doc1, doc2), user_id = linked
    with uow_factory() as uow:
        uow.evidences.add(make_evidence(act1, doc1, user_id, page=1))
        uow.evidences.add(make_evidence(act1, doc2, user_id, page=1))
        uow.commit()

    with uow_factory() as uow:
        counts = uow.evidences.counts_for_activities([act1.id, act2.id])
        assert counts == {act1.id: 2, act2.id: 0}
        assert uow.evidences.counts_for_activities([]) == {}


def test_content_keys_pair_each_activity_with_the_hash_of_its_documents_text(uow_factory, linked):
    (act1, act2), (doc1, doc2), user_id = linked
    run = make_run(doc1.id)
    with uow_factory() as uow:
        uow.extractions.add_run(run)
        pages = [_page(doc1.id, run.id, 2, "pagina dois"), _page(doc1.id, run.id, 1, "Pagina UM")]
        uow.extractions.replace_pages(doc1.id, pages)
        uow.evidences.add(make_evidence(act1, doc1, user_id, page=1))
        uow.evidences.add(make_evidence(act1, doc1, user_id, page=2))
        uow.evidences.add(make_evidence(act2, doc2, user_id, page=1))  # doc2 has no text stored
        uow.commit()

    with uow_factory() as uow:
        keys = uow.evidences.content_keys_for_activities([act1.id, act2.id])
        assert uow.evidences.content_keys_for_activities([]) == {}
    assert keys == {act1.id: {(doc1.id, content_hash(["pagina um", "pagina dois"]))}}
