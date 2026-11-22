"""Builders for the board use case tests: the ordinance use cases bound to the temp storage of the
`docs` fixture, and readers of what they stored. Synthetic data only."""

from datetime import UTC, date, datetime

from app.application.use_cases.board import RereadOrdinance, UploadOrdinance
from app.domain.entities.board import (
    BoardMember,
    BoardOrdinance,
    BoardRole,
    ReadingState,
    ValueSource,
)

BOARD_ENTITY = "board_ordinance"
MEMBERS = (
    BoardMember("Ana Presidente Souza", BoardRole.PRESIDENTE, 1, ValueSource.EXTRAIDO),
    BoardMember("Bruno Membro Lima", BoardRole.MEMBRO, 1, ValueSource.EXTRAIDO),
    BoardMember("Carla Suplente Reis", BoardRole.SUPLENTE, 2, ValueSource.EXTRAIDO),
)


def upload_uc(world, docs) -> UploadOrdinance:
    return UploadOrdinance(
        world.uow_factory, world.audit, world.policy, docs.storage, docs.inspector, docs.clock
    )


def reread_uc(world, docs) -> RereadOrdinance:
    return RereadOrdinance(world.uow_factory, world.audit, world.policy, docs.clock)


def stored_board(world, process=None) -> BoardOrdinance | None:
    with world.uow_factory() as uow:
        return uow.board.get((process or world.process).id)


def board_events(world, process=None) -> list:
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(BOARD_ENTITY, str((process or world.process).id)))


def add_typed_ordinance(world, process=None, **changes) -> BoardOrdinance:
    """A saved ordinance with the data typed by the person and no file (version 1)."""
    process = process or world.process
    data = {
        "process_id": process.id,
        "number": "77/2025",
        "number_source": ValueSource.INFORMADO,
        "ordinance_date": date(2025, 3, 10),
        "date_source": ValueSource.INFORMADO,
        "members": MEMBERS,
    }
    data.update(changes)
    with world.uow_factory() as uow:
        saved = uow.board.create(BoardOrdinance(**data), world.admin.id, 0)
        uow.commit()
    return saved


def set_reading_state(world, state, process=None, code=None) -> None:
    """Brings the stored (`PENDENTE`) ordinance to `state` the way the executor does."""
    now = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)
    process = process or world.process
    with world.uow_factory() as uow:
        if state is ReadingState.LENDO:
            assert uow.board.claim_next_pending(now) is not None
        elif state in (ReadingState.LIDA, ReadingState.FALHOU):
            assert uow.board.claim_next_pending(now) is not None
            current = uow.board.lock(process.id)
            if state is ReadingState.LIDA:
                uow.board.finish_read(current, {}, now)
            else:
                uow.board.finish_failed(process.id, code, now)
        uow.commit()
