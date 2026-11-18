"""REL-03, REL-13, REL-14, REL-15: the wording job repository on real PostgreSQL."""

import uuid
from datetime import timedelta

import pytest

from app.domain.entities.generated import (
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
)
from app.domain.errors import Conflict, NotFound
from app.infrastructure.database.repositories import SqlWordingJobRepository
from tests.integration.documents.generated_support import T0, make_wording_job

LATER = T0 + timedelta(minutes=2)


def add(session_factory, *jobs):
    with session_factory() as session:
        repo = SqlWordingJobRepository(session)
        for job in jobs:
            repo.add(job)
        session.commit()


def get(session_factory, job_id):
    with session_factory() as session:
        return SqlWordingJobRepository(session).get(job_id)


def finish(session_factory, job, state, **kwargs):
    with session_factory() as session:
        SqlWordingJobRepository(session).finish(job.id, LATER, state, **kwargs)
        session.commit()


def test_a_generating_job_round_trips(session_factory, process, base):
    job = make_wording_job(process, base["admin"].id, "1.2")
    add(session_factory, job)

    assert get(session_factory, job.id) == job


def test_get_of_an_unknown_job_returns_none(session_factory):
    assert get(session_factory, uuid.uuid4()) is None


def test_a_second_generating_job_of_the_same_section_conflicts_with_the_code(
    session_factory, process, base
):
    user_id = base["admin"].id
    add(session_factory, make_wording_job(process, user_id, "1.1"))

    with pytest.raises(Conflict) as refused:
        add(session_factory, make_wording_job(process, user_id, "1.1"))

    assert refused.value.code == "REDACAO_EM_ANDAMENTO"


def test_another_section_and_another_process_are_worded_at_the_same_time(
    session_factory, process, other_process, base
):
    user_id = base["admin"].id
    add(
        session_factory,
        make_wording_job(process, user_id, "1.1"),
        make_wording_job(process, user_id, "1.2"),
        make_wording_job(other_process, user_id, "1.1"),
    )

    with session_factory() as session:
        latest = SqlWordingJobRepository(session).latest_by_section(process.id)
    assert set(latest) == {"1.1", "1.2"}


def test_the_section_may_be_worded_again_once_the_job_finished(session_factory, process, base):
    user_id = base["admin"].id
    first = make_wording_job(process, user_id, "1.1")
    add(session_factory, first)
    finish(session_factory, first, GenerationState.PRONTO)

    second = make_wording_job(process, user_id, "1.1", requested_at=T0 + timedelta(1))
    add(session_factory, second)

    assert get(session_factory, second.id).state is GenerationState.GERANDO


def test_finishing_ready_keeps_the_warnings_with_their_reasons(session_factory, process, base):
    job = make_wording_job(process, base["admin"].id)
    add(session_factory, job)
    warnings = (
        GenerationAlert(GenerationAlertCode.REDACAO_REJEITADA, "NUMERO,DATA"),
        GenerationAlert(GenerationAlertCode.REDACAO_INDISPONIVEL),
    )

    finish(session_factory, job, GenerationState.PRONTO, warnings=warnings)

    loaded = get(session_factory, job.id)
    assert loaded.state is GenerationState.PRONTO
    assert loaded.warnings == warnings
    assert (loaded.finished_at, loaded.error_code) == (LATER, None)


def test_finishing_failed_keeps_the_error_code_and_leaves_no_warnings(
    session_factory, process, base
):
    job = make_wording_job(process, base["admin"].id)
    add(session_factory, job)

    finish(session_factory, job, GenerationState.FALHOU, error_code=GenerationCode.ERRO_INTERNO)

    loaded = get(session_factory, job.id)
    assert loaded.state is GenerationState.FALHOU
    assert loaded.error_code is GenerationCode.ERRO_INTERNO
    assert (loaded.warnings, loaded.finished_at) == ((), LATER)


def test_a_finished_job_cannot_be_finished_again_and_an_unknown_one_is_not_found(
    session_factory, process, base
):
    job = make_wording_job(process, base["admin"].id)
    add(session_factory, job)
    finish(session_factory, job, GenerationState.PRONTO)

    with pytest.raises(Conflict):
        finish(session_factory, job, GenerationState.FALHOU, error_code=GenerationCode.ERRO_INTERNO)
    with pytest.raises(NotFound):
        finish(session_factory, make_wording_job(process, base["admin"].id), GenerationState.PRONTO)

    assert get(session_factory, job.id).state is GenerationState.PRONTO


def test_claim_next_takes_the_oldest_job_not_started_and_marks_it_started(
    session_factory, process, base
):
    user_id = base["admin"].id
    newer = make_wording_job(process, user_id, "1.2", requested_at=T0 + timedelta(1))
    older = make_wording_job(process, user_id, "1.1", requested_at=T0)
    add(session_factory, newer, older)

    with session_factory() as session:
        claimed = SqlWordingJobRepository(session).claim_next(LATER)
        session.commit()
    with session_factory() as session:
        second = SqlWordingJobRepository(session).claim_next(LATER)
        session.commit()
        third = SqlWordingJobRepository(session).claim_next(LATER)

    assert claimed.id == older.id
    assert (claimed.state, claimed.started_at) == (GenerationState.GERANDO, LATER)
    assert second.id == newer.id
    assert third is None


def test_two_concurrent_claims_never_take_the_same_job(session_factory, process, base):
    only = make_wording_job(process, base["admin"].id)
    add(session_factory, only)

    with session_factory() as first, session_factory() as second:
        claim_a = SqlWordingJobRepository(first).claim_next(LATER)  # holds the row lock
        claim_b = SqlWordingJobRepository(second).claim_next(LATER)

        assert claim_a.id == only.id
        assert claim_b is None


def test_recovery_fails_only_the_jobs_that_had_started(session_factory, process, base):
    user_id = base["admin"].id
    started = make_wording_job(process, user_id, "1.1", started_at=T0)
    waiting = make_wording_job(process, user_id, "1.2")
    done = make_wording_job(process, user_id, "1.3")
    add(session_factory, started, waiting, done)
    finish(session_factory, done, GenerationState.PRONTO)

    with session_factory() as session:
        recovered = SqlWordingJobRepository(session).recover_interrupted(LATER)
        session.commit()

    assert [job.id for job in recovered] == [started.id]
    closed = get(session_factory, started.id)
    assert closed.state is GenerationState.FALHOU
    assert closed.error_code is GenerationCode.INTERROMPIDA
    assert closed.finished_at == LATER
    assert get(session_factory, waiting.id).state is GenerationState.GERANDO
    assert get(session_factory, done.id).state is GenerationState.PRONTO


def test_latest_by_section_gives_the_newest_job_of_each_section(session_factory, process, base):
    user_id = base["admin"].id
    old = make_wording_job(process, user_id, "1.1", requested_at=T0)
    add(session_factory, old)
    finish(session_factory, old, GenerationState.FALHOU, error_code=GenerationCode.ERRO_INTERNO)
    new = make_wording_job(process, user_id, "1.1", requested_at=T0 + timedelta(1))
    other = make_wording_job(process, user_id, "1.3", requested_at=T0)
    add(session_factory, new, other)

    with session_factory() as session:
        latest = SqlWordingJobRepository(session).latest_by_section(process.id)

    assert {key: job.id for key, job in latest.items()} == {"1.1": new.id, "1.3": other.id}


def test_a_process_without_jobs_has_no_latest(session_factory, process):
    with session_factory() as session:
        assert SqlWordingJobRepository(session).latest_by_section(process.id) == {}
