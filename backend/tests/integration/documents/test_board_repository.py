"""PORT-01, PORT-05, PORT-07, PORT-09, PORT-12: the board ordinance repository (PostgreSQL)."""

import dataclasses
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from app.domain.entities.board import (
    BoardMember,
    BoardOrdinance,
    BoardRole,
    OrdinanceFile,
    OrdinanceReadingCode,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ReadingState,
    ValueSource,
)
from app.domain.errors import Conflict, NotFound, StaleVersion
from app.infrastructure.database.repositories import SqlBoardRepository

T0 = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
LATER = T0 + timedelta(minutes=5)
MEMBERS = (
    BoardMember("Ana Presidente Souza", BoardRole.PRESIDENTE, 1, ValueSource.EXTRAIDO),
    BoardMember("Bruno Membro Lima", BoardRole.MEMBRO, None, ValueSource.INFORMADO),
    BoardMember("Carla Suplente Reis", BoardRole.SUPLENTE, 2, ValueSource.EXTRAIDO),
)
WARNINGS = (
    OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "number"),
    OrdinanceWarning(OrdinanceWarningCode.MEMBROS_NAO_ENCONTRADOS, "members"),
)


def make_file(name="portaria.pdf") -> OrdinanceFile:
    return OrdinanceFile(f"{uuid.uuid4().hex}.pdf", name, "application/pdf", 2048, "a" * 64, 3)


def make_ordinance(process, **changes) -> BoardOrdinance:
    data = {
        "process_id": process.id,
        "number": "123/2025",
        "number_page": 1,
        "number_source": ValueSource.EXTRAIDO,
        "ordinance_date": date(2025, 3, 10),
        "date_page": 1,
        "date_source": ValueSource.INFORMADO,
        "members": MEMBERS,
    }
    data.update(changes)
    return BoardOrdinance(**data)


def call(session_factory, action):
    """Runs `action(repository)` in its own session and commits."""
    with session_factory() as session:
        result = action(SqlBoardRepository(session))
        session.commit()
    return result


def get(session_factory, process_id):
    with session_factory() as session:
        return SqlBoardRepository(session).get(process_id)


def create(session_factory, process, base, **changes):
    ordinance = make_ordinance(process, **changes)
    return call(session_factory, lambda r: r.create(ordinance, base["admin"].id, 0))


def column(engine, name, process):
    with engine.connect() as conn:
        return conn.execute(
            text(f"SELECT {name} FROM board_ordinances WHERE process_id = :p"), {"p": process.id}
        ).scalar_one()


# --- create and read (PORT-01, PORT-05) -----------------------------------------------------


def test_a_process_without_an_ordinance_has_none(session_factory, process):
    assert get(session_factory, process.id) is None


def test_an_ordinance_without_a_file_round_trips_with_its_members(session_factory, process, base):
    created = create(session_factory, process, base)

    loaded = get(session_factory, process.id)

    assert created == dataclasses.replace(make_ordinance(process), version=1)
    assert loaded == created
    assert loaded.members == MEMBERS  # page None, EXTRAIDO and INFORMADO come back identical
    assert loaded.file is None
    assert loaded.reading_state is ReadingState.SEM_ARQUIVO


def test_an_ordinance_with_a_file_round_trips(session_factory, process, base):
    file = make_file()
    create(
        session_factory,
        process,
        base,
        file=file,
        reading_state=ReadingState.PENDENTE,
        warnings=WARNINGS,
    )

    loaded = get(session_factory, process.id)

    assert loaded.file == file
    assert loaded.reading_state is ReadingState.PENDENTE
    assert loaded.warnings == WARNINGS


def test_a_new_ordinance_row_has_no_members_by_default(session_factory, process, base):
    create(session_factory, process, base, members=())

    assert get(session_factory, process.id).members == ()


def test_create_with_a_version_other_than_0_is_stale_and_a_second_create_conflicts(
    session_factory, process, base
):
    ordinance = make_ordinance(process)

    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.create(ordinance, base["admin"].id, 3))
    assert get(session_factory, process.id) is None

    call(session_factory, lambda r: r.create(ordinance, base["admin"].id, 0))
    with pytest.raises(Conflict) as error:
        call(session_factory, lambda r: r.create(ordinance, base["admin"].id, 0))
    assert not isinstance(error.value, StaleVersion)


# --- save the data (PORT-05, PORT-12) -------------------------------------------------------


def test_save_data_with_the_right_version_stores_the_values_and_goes_to_version_2(
    session_factory, process, base
):
    create(session_factory, process, base)
    edited = make_ordinance(
        process,
        number="999/2025",
        number_page=None,
        number_source=ValueSource.INFORMADO,
        ordinance_date=None,
        date_page=None,
        date_source=None,
        members=MEMBERS[:1],
        warnings=WARNINGS[:1],
    )

    saved = call(session_factory, lambda r: r.save_data(edited, base["admin"].id, 1))

    assert saved == dataclasses.replace(edited, version=2)
    assert get(session_factory, process.id) == saved


def test_save_data_from_an_old_version_is_stale_and_changes_nothing(session_factory, process, base):
    created = create(session_factory, process, base)
    call(session_factory, lambda r: r.save_data(make_ordinance(process, number="A"), None, 1))

    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.save_data(make_ordinance(process, number="B"), None, 1))

    loaded = get(session_factory, process.id)
    assert (loaded.number, loaded.version) == ("A", created.version + 1)


def test_save_data_of_an_unknown_ordinance_is_not_found(session_factory, process):
    with pytest.raises(NotFound):
        call(session_factory, lambda r: r.save_data(make_ordinance(process), None, 1))


# --- file (PORT-01) -------------------------------------------------------------------------


def test_set_file_queues_the_reading_and_gives_back_no_file_when_there_was_none(
    session_factory, process, base
):
    create(session_factory, process, base)
    new = make_file()

    previous = call(session_factory, lambda r: r.set_file(process.id, new, None, 1, T0))

    loaded = get(session_factory, process.id)
    assert previous is None
    assert loaded.file == new
    assert (loaded.reading_state, loaded.reading_code) == (ReadingState.PENDENTE, None)
    assert loaded.version == 2


def test_set_file_gives_back_the_previous_file_to_be_deleted_from_the_disk(
    session_factory, process, base
):
    old = make_file("antiga.pdf")
    create(session_factory, process, base, file=old, reading_state=ReadingState.LIDA)
    new = make_file("nova.pdf")

    previous = call(session_factory, lambda r: r.set_file(process.id, new, None, 1, T0))

    assert previous == old
    assert get(session_factory, process.id).file == new


def test_set_file_does_not_give_back_a_file_that_was_already_deleted(
    session_factory, process, base
):
    old = dataclasses.replace(make_file(), deleted_at=T0)
    create(session_factory, process, base, file=old, reading_state=ReadingState.LIDA)

    previous = call(session_factory, lambda r: r.set_file(process.id, make_file(), None, 1, T0))

    assert previous is None


def test_set_file_from_an_old_version_is_stale(session_factory, process, base):
    create(session_factory, process, base)

    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.set_file(process.id, make_file(), None, 5, T0))
    assert get(session_factory, process.id).file is None


# --- the reading queue (PORT-07) ------------------------------------------------------------


def test_request_reading_queues_a_finished_reading_again(session_factory, process, base):
    create(
        session_factory,
        process,
        base,
        file=make_file(),
        reading_state=ReadingState.FALHOU,
        reading_code=OrdinanceReadingCode.IA_INDISPONIVEL,
    )

    call(session_factory, lambda r: r.request_reading(process.id, 1, T0))

    loaded = get(session_factory, process.id)
    assert (loaded.reading_state, loaded.reading_code) == (ReadingState.PENDENTE, None)


@pytest.mark.parametrize("state", [ReadingState.PENDENTE, ReadingState.LENDO])
def test_request_reading_of_one_already_in_the_queue_conflicts(
    session_factory, process, base, state
):
    create(session_factory, process, base, file=make_file(), reading_state=state)

    with pytest.raises(Conflict):
        call(session_factory, lambda r: r.request_reading(process.id, 1, T0))
    assert get(session_factory, process.id).reading_state is state


def test_request_reading_without_a_file_conflicts(session_factory, process, base):
    create(session_factory, process, base)

    with pytest.raises(Conflict):
        call(session_factory, lambda r: r.request_reading(process.id, 1, T0))


def test_request_reading_from_an_old_version_is_stale(session_factory, process, base):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.LIDA)

    with pytest.raises(StaleVersion):
        call(session_factory, lambda r: r.request_reading(process.id, 9, T0))


def test_claim_takes_the_oldest_queued_ordinance_and_counts_an_attempt(
    session_factory, process, other_process, base, engine
):
    admin = base["admin"].id
    for target, when in ((process, T0 + timedelta(minutes=1)), (other_process, T0)):
        ordinance = make_ordinance(
            target, file=make_file(), reading_state=ReadingState.SEM_ARQUIVO, members=()
        )
        call(session_factory, lambda r, o=ordinance: r.create(o, admin, 0))
        call(
            session_factory, lambda r, t=target, w=when: r.set_file(t.id, make_file(), admin, 1, w)
        )

    claimed = call(session_factory, lambda r: r.claim_next_pending(LATER))
    second = call(session_factory, lambda r: r.claim_next_pending(LATER))
    third = call(session_factory, lambda r: r.claim_next_pending(LATER))

    assert claimed.process_id == other_process.id
    assert claimed.reading_state is ReadingState.LENDO
    assert second.process_id == process.id
    assert third is None
    assert column(engine, "reading_attempts", other_process) == 1
    assert column(engine, "reading_started_at", other_process) == LATER


def test_claim_skips_the_ordinances_that_are_not_queued(session_factory, process, base):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.LIDA)

    assert call(session_factory, lambda r: r.claim_next_pending(LATER)) is None


def test_two_concurrent_claims_never_take_the_same_ordinance(session_factory, process, base):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.SEM_ARQUIVO)
    call(session_factory, lambda r: r.set_file(process.id, make_file(), None, 1, T0))

    with session_factory() as first, session_factory() as second:
        claim_a = SqlBoardRepository(first).claim_next_pending(LATER)  # holds the row lock
        claim_b = SqlBoardRepository(second).claim_next_pending(LATER)

        assert claim_a.process_id == process.id
        assert claim_b is None


def test_finish_read_stores_the_fields_the_warnings_and_the_raw_json(
    session_factory, process, base, engine
):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.SEM_ARQUIVO)
    call(session_factory, lambda r: r.set_file(process.id, make_file(), None, 1, T0))
    claimed = call(session_factory, lambda r: r.claim_next_pending(T0))
    read = dataclasses.replace(
        claimed,
        number="777/2025",
        number_page=2,
        number_source=ValueSource.EXTRAIDO,
        members=MEMBERS[:2],
        warnings=WARNINGS,
    )

    done = call(session_factory, lambda r: r.finish_read(read, {"numero": "777/2025"}, LATER))

    loaded = get(session_factory, process.id)
    assert done == loaded
    assert loaded.reading_state is ReadingState.LIDA
    assert loaded.reading_code is None
    assert (loaded.number, loaded.number_page, loaded.members) == ("777/2025", 2, MEMBERS[:2])
    assert loaded.warnings == WARNINGS
    assert column(engine, "raw_json", process) == {"numero": "777/2025"}
    assert column(engine, "reading_finished_at", process) == LATER


def test_finish_read_of_an_ordinance_not_being_read_conflicts(session_factory, process, base):
    created = create(
        session_factory, process, base, file=make_file(), reading_state=ReadingState.LIDA
    )

    with pytest.raises(Conflict):
        call(session_factory, lambda r: r.finish_read(created, {}, LATER))


def test_lock_gives_back_the_current_values(session_factory, process, base):
    create(session_factory, process, base)
    call(session_factory, lambda r: r.save_data(make_ordinance(process, number="NOVO"), None, 1))

    with session_factory() as session:
        locked = SqlBoardRepository(session).lock(process.id)

    assert (locked.number, locked.version) == ("NOVO", 2)


def test_lock_of_an_unknown_ordinance_is_not_found(session_factory, process):
    with session_factory() as session, pytest.raises(NotFound):
        SqlBoardRepository(session).lock(process.id)


def test_finish_failed_stores_the_code(session_factory, process, base, engine):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.LENDO)

    call(
        session_factory,
        lambda r: r.finish_failed(process.id, OrdinanceReadingCode.RESPOSTA_INVALIDA, LATER),
    )

    loaded = get(session_factory, process.id)
    assert loaded.reading_state is ReadingState.FALHOU
    assert loaded.reading_code is OrdinanceReadingCode.RESPOSTA_INVALIDA
    assert loaded.members == MEMBERS  # the data of the person stays
    assert column(engine, "reading_finished_at", process) == LATER


def test_finish_failed_of_an_ordinance_not_being_read_conflicts(session_factory, process, base):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.PENDENTE)

    with pytest.raises(Conflict):
        call(
            session_factory,
            lambda r: r.finish_failed(process.id, OrdinanceReadingCode.ERRO_INTERNO, LATER),
        )


def test_recovery_fails_the_reading_in_progress_as_interrupted_and_leaves_the_queued_one(
    session_factory, process, other_process, base
):
    admin = base["admin"].id
    for target, state in ((process, ReadingState.LENDO), (other_process, ReadingState.PENDENTE)):
        ordinance = make_ordinance(target, file=make_file(), reading_state=state)
        call(session_factory, lambda r, o=ordinance: r.create(o, admin, 0))

    recovered = call(session_factory, lambda r: r.recover_interrupted(LATER))

    assert list(recovered) == [process.id]
    interrupted = get(session_factory, process.id)
    assert interrupted.reading_state is ReadingState.FALHOU
    assert interrupted.reading_code is OrdinanceReadingCode.INTERROMPIDA
    assert get(session_factory, other_process.id).reading_state is ReadingState.PENDENTE


# --- conclusion deletes only the file (PORT-07) ---------------------------------------------


def test_marking_the_file_deleted_keeps_the_number_the_date_and_the_members(
    session_factory, process, base
):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.LIDA)

    call(session_factory, lambda r: r.mark_file_deleted(process.id, T0))
    call(session_factory, lambda r: r.mark_file_deleted(process.id, LATER))  # the first mark stays

    loaded = get(session_factory, process.id)
    assert loaded.file.deleted_at == T0
    assert (loaded.number, loaded.ordinance_date, loaded.members) == (
        "123/2025",
        date(2025, 3, 10),
        MEMBERS,
    )
    assert loaded.version == 1


# --- not a document (PORT-09) ---------------------------------------------------------------


def test_the_ordinance_is_not_listed_among_the_documents_of_the_process(
    uow_factory, session_factory, process, base
):
    create(session_factory, process, base, file=make_file(), reading_state=ReadingState.PENDENTE)

    with uow_factory() as uow:
        assert uow.documents.list_for_process(process.id) == []
        assert uow.documents.count_for_process(process.id) == 0
        assert uow.board.get(process.id).file is not None
