"""Moves a synthetic process to CONCLUIDO in tests (DEL-14).

The generic status route refuses CONCLUIDO: a process only concludes through the conclusion that
purges the input documents. Tests that only need a concluded process (read-only rules) use this.
"""

import dataclasses
from collections.abc import Callable
from uuid import UUID

from app.domain.entities.process import ProcessStatus
from app.domain.repositories.ports import UnitOfWork


def conclude_for_test(uow_factory: Callable[[], UnitOfWork], process_id: UUID | str) -> None:
    """Sets the process to CONCLUIDO straight through the unit of work, as stored (no audit)."""
    with uow_factory() as uow:
        current = uow.processes.get(UUID(str(process_id)))
        uow.processes.update(
            dataclasses.replace(current, status=ProcessStatus.CONCLUIDO), current.version
        )
        uow.commit()
