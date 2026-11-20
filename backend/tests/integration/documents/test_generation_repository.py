"""VER-01, VER-02, VER-04, VER-05, VER-08, DEL-01: the generated document repository on real
PostgreSQL."""

import uuid
from datetime import timedelta

import pytest

from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
)
from app.domain.errors import Conflict, NotFound
from app.infrastructure.database.repositories import SqlGenerationRepository
from tests.integration.documents.generated_support import T0, make_file, make_generation

LATER = T0 + timedelta(minutes=5)


def add(session_factory, *generations):
    with session_factory() as session:
        repo = SqlGenerationRepository(session)
        for generation in generations:
            repo.add(generation)
        session.commit()


def finish_ready(session_factory, generation, **kwargs):
    args = dict(
        now=LATER, files=[make_file()], snapshot={"total": "10.00"}, alerts=(), plan_hash=None
    )
    args.update(kwargs)
    with session_factory() as session:
        done = SqlGenerationRepository(session).finish_ready(generation.id, **args)
        session.commit()
    return done


def get(session_factory, generation_id):
    with session_factory() as session:
        return SqlGenerationRepository(session).get(generation_id)


def test_a_generating_row_round_trips(session_factory, process, base):
    generation = make_generation(process, base["admin"].id, DocumentKind.RELATORIO)
    add(session_factory, generation)

    assert get(session_factory, generation.id) == generation


def test_get_of_an_unknown_row_returns_none(session_factory):
    assert get(session_factory, uuid.uuid4()) is None


def test_a_second_request_of_the_same_kind_in_the_process_conflicts_with_the_code(
    session_factory, process, base
):
    user_id = base["admin"].id
    add(session_factory, make_generation(process, user_id, DocumentKind.TABELA))

    with pytest.raises(Conflict) as refused:
        add(session_factory, make_generation(process, user_id, DocumentKind.TABELA))

    assert refused.value.code == "GERACAO_EM_ANDAMENTO"


def test_other_kinds_and_other_processes_generate_at_the_same_time(
    session_factory, process, other_process, base
):
    user_id = base["admin"].id
    add(
        session_factory,
        make_generation(process, user_id, DocumentKind.TABELA),
        make_generation(process, user_id, DocumentKind.RELATORIO),
        make_generation(other_process, user_id, DocumentKind.TABELA),
    )

    with session_factory() as session:
        rows = SqlGenerationRepository(session).list_for_process(process.id)
    assert {row.kind for row in rows} == {DocumentKind.TABELA, DocumentKind.RELATORIO}


def test_two_generations_of_a_kind_that_end_ready_get_versions_1_and_2(
    session_factory, process, base
):
    user_id = base["admin"].id
    first = make_generation(process, user_id)
    add(session_factory, first)
    first_done = finish_ready(session_factory, first)
    second = make_generation(process, user_id)
    add(session_factory, second)
    second_done = finish_ready(session_factory, second)

    assert (first_done.version_number, second_done.version_number) == (1, 2)
    assert get(session_factory, first.id).version_number == 1
    assert get(session_factory, second.id).version_number == 2


def test_a_generation_that_fails_does_not_spend_a_version_number(session_factory, process, base):
    user_id = base["admin"].id
    failed = make_generation(process, user_id)
    add(session_factory, failed)
    with session_factory() as session:
        SqlGenerationRepository(session).finish_failed(
            failed.id, LATER, GenerationCode.ERRO_INTERNO, "A geração falhou."
        )
        session.commit()
    retry = make_generation(process, user_id)
    add(session_factory, retry)

    done = finish_ready(session_factory, retry)

    assert done.version_number == 1
    row = get(session_factory, failed.id)
    assert row.version_number is None


def test_versions_count_separately_per_kind_and_per_process(
    session_factory, process, other_process, base
):
    user_id = base["admin"].id
    versions = {}
    for proc, kind in (
        (process, DocumentKind.TABELA),
        (process, DocumentKind.TABELA),
        (process, DocumentKind.RELATORIO),
        (other_process, DocumentKind.TABELA),
    ):
        generation = make_generation(proc, user_id, kind)
        add(session_factory, generation)
        versions.setdefault((proc.id, kind), []).append(
            finish_ready(session_factory, generation).version_number
        )

    assert versions[(process.id, DocumentKind.TABELA)] == [1, 2]
    assert versions[(process.id, DocumentKind.RELATORIO)] == [1]
    assert versions[(other_process.id, DocumentKind.TABELA)] == [1]


def test_finish_ready_keeps_files_snapshot_alerts_hash_and_end_time(session_factory, process, base):
    generation = make_generation(process, base["admin"].id, DocumentKind.COMPROVANTE)
    add(session_factory, generation)
    pdf, docx = make_file(DocumentFormat.PDF, 60_000_000), make_file(DocumentFormat.DOCX)
    alert = GenerationAlert(GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE, "sem página")

    done = finish_ready(
        session_factory,
        generation,
        files=[pdf, docx],
        snapshot={"total": "211.00", "activities": [{"item": "I.1"}]},
        alerts=[alert],
        plan_hash="f" * 64,
    )

    loaded = get(session_factory, generation.id)
    assert loaded == done
    assert loaded.state is GenerationState.PRONTO
    assert loaded.finished_at == LATER
    assert loaded.snapshot == {"total": "211.00", "activities": [{"item": "I.1"}]}
    assert loaded.alerts == (alert,)
    assert loaded.plan_hash == "f" * 64
    assert loaded.files == (docx, pdf)
    assert loaded.files[1].size_bytes == 60_000_000


def test_finish_failed_keeps_the_code_message_and_end_time(session_factory, process, base):
    generation = make_generation(process, base["admin"].id)
    add(session_factory, generation)

    with session_factory() as session:
        SqlGenerationRepository(session).finish_failed(
            generation.id, LATER, GenerationCode.ESPACO_INSUFICIENTE, "Sem espaço em disco."
        )
        session.commit()

    loaded = get(session_factory, generation.id)
    assert loaded.state is GenerationState.FALHOU
    assert loaded.error_code is GenerationCode.ESPACO_INSUFICIENTE
    assert loaded.error_message == "Sem espaço em disco."
    assert (loaded.finished_at, loaded.version_number, loaded.files) == (LATER, None, ())


def test_a_finished_generation_cannot_be_finished_again(session_factory, process, base):
    generation = make_generation(process, base["admin"].id)
    add(session_factory, generation)
    finish_ready(session_factory, generation)

    with pytest.raises(Conflict):
        finish_ready(session_factory, generation)
    with pytest.raises(Conflict), session_factory() as session:
        SqlGenerationRepository(session).finish_failed(
            generation.id, LATER, GenerationCode.ERRO_INTERNO, "x"
        )

    assert get(session_factory, generation.id).version_number == 1


def test_finishing_an_unknown_generation_is_not_found(session_factory):
    with pytest.raises(NotFound), session_factory() as session:
        SqlGenerationRepository(session).finish_failed(
            uuid.uuid4(), LATER, GenerationCode.ERRO_INTERNO, "x"
        )


def test_claim_next_takes_the_oldest_row_not_started_and_marks_it_started(
    session_factory, process, other_process, base
):
    user_id = base["admin"].id
    newer = make_generation(process, user_id, DocumentKind.TABELA, requested_at=T0 + timedelta(1))
    older = make_generation(other_process, user_id, DocumentKind.TABELA, requested_at=T0)
    add(session_factory, newer, older)

    with session_factory() as session:
        claimed = SqlGenerationRepository(session).claim_next(LATER)
        session.commit()
    with session_factory() as session:
        second = SqlGenerationRepository(session).claim_next(LATER)
        session.commit()
        third = SqlGenerationRepository(session).claim_next(LATER)

    assert claimed.id == older.id
    assert (claimed.state, claimed.started_at) == (GenerationState.GERANDO, LATER)
    assert second.id == newer.id
    assert third is None


def test_two_concurrent_claims_never_take_the_same_row(session_factory, process, base):
    user_id = base["admin"].id
    only = make_generation(process, user_id, DocumentKind.TABELA)
    add(session_factory, only)

    with session_factory() as first, session_factory() as second:
        claim_a = SqlGenerationRepository(first).claim_next(LATER)  # holds the row lock
        claim_b = SqlGenerationRepository(second).claim_next(LATER)

        assert claim_a.id == only.id
        assert claim_b is None


def test_two_concurrent_claims_with_two_rows_take_one_each(session_factory, process, base):
    user_id = base["admin"].id
    add(
        session_factory,
        make_generation(process, user_id, DocumentKind.TABELA),
        make_generation(process, user_id, DocumentKind.RELATORIO, requested_at=T0 + timedelta(1)),
    )

    with session_factory() as first, session_factory() as second:
        claim_a = SqlGenerationRepository(first).claim_next(LATER)
        claim_b = SqlGenerationRepository(second).claim_next(LATER)

        assert claim_a is not None and claim_b is not None
        assert claim_a.id != claim_b.id


def test_recovery_fails_only_the_rows_that_had_started(session_factory, process, base):
    user_id = base["admin"].id
    started = make_generation(process, user_id, DocumentKind.TABELA, started_at=T0)
    waiting = make_generation(process, user_id, DocumentKind.RELATORIO)
    ready = make_generation(process, user_id, DocumentKind.COMPROVANTE)
    add(session_factory, started, waiting, ready)
    finish_ready(session_factory, ready)

    with session_factory() as session:
        recovered = SqlGenerationRepository(session).recover_interrupted(LATER)
        session.commit()

    assert [row.id for row in recovered] == [started.id]
    closed = get(session_factory, started.id)
    assert closed.state is GenerationState.FALHOU
    assert closed.error_code is GenerationCode.INTERROMPIDA
    assert closed.finished_at == LATER
    assert closed.error_message
    assert get(session_factory, waiting.id).state is GenerationState.GERANDO
    assert get(session_factory, ready.id).state is GenerationState.PRONTO


def test_a_row_not_started_before_the_restart_is_still_claimable_after_the_recovery(
    session_factory, process, base
):
    waiting = make_generation(process, base["admin"].id)
    add(session_factory, waiting)
    with session_factory() as session:
        SqlGenerationRepository(session).recover_interrupted(LATER)
        session.commit()

    with session_factory() as session:
        claimed = SqlGenerationRepository(session).claim_next(LATER)

    assert claimed.id == waiting.id


def test_the_latest_ready_version_per_kind_ignores_failed_and_generating_rows(
    session_factory, process, base
):
    user_id = base["admin"].id
    ids = {}
    for kind, outcome in (
        (DocumentKind.TABELA, "ready"),
        (DocumentKind.TABELA, "ready"),
        (DocumentKind.TABELA, "failed"),
        (DocumentKind.RELATORIO, "failed"),
        (DocumentKind.COMPROVANTE, "generating"),
    ):
        generation = make_generation(process, user_id, kind)
        add(session_factory, generation)
        if outcome == "ready":
            finish_ready(session_factory, generation)
            ids[kind] = generation.id
        elif outcome == "failed":
            with session_factory() as session:
                SqlGenerationRepository(session).finish_failed(
                    generation.id, LATER, GenerationCode.ERRO_INTERNO, "x"
                )
                session.commit()

    with session_factory() as session:
        latest = SqlGenerationRepository(session).latest_ready_by_kind(process.id)

    assert set(latest) == {DocumentKind.TABELA}
    assert latest[DocumentKind.TABELA].id == ids[DocumentKind.TABELA]
    assert latest[DocumentKind.TABELA].version_number == 2


def test_a_process_without_ready_versions_has_no_latest(session_factory, process, base):
    add(session_factory, make_generation(process, base["admin"].id))

    with session_factory() as session:
        assert SqlGenerationRepository(session).latest_ready_by_kind(process.id) == {}


def test_the_listing_puts_generating_first_then_the_newest_request_and_filters_by_kind(
    session_factory, process, base
):
    user_id = base["admin"].id
    old = make_generation(process, user_id, DocumentKind.TABELA, requested_at=T0)
    add(session_factory, old)
    finish_ready(session_factory, old)
    new = make_generation(process, user_id, DocumentKind.TABELA, requested_at=T0 + timedelta(1))
    add(session_factory, new)
    finish_ready(session_factory, new)
    running = make_generation(process, user_id, DocumentKind.TABELA, requested_at=T0 + timedelta(2))
    report = make_generation(process, user_id, DocumentKind.RELATORIO)
    add(session_factory, running, report)

    with session_factory() as session:
        repo = SqlGenerationRepository(session)
        tables = repo.list_for_process(process.id, DocumentKind.TABELA)
        everything = repo.list_for_process(process.id)

    assert [row.id for row in tables] == [running.id, new.id, old.id]
    assert len(everything) == 4
    assert {row.id for row in everything[:2]} == {running.id, report.id}
    assert all(row.files for row in tables[1:])
