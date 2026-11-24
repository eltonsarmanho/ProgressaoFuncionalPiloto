"""Removal of the input files of a process: the documents and the ordinance file of the board
(DEL-05, DEL-06, DEL-08, DEL-09, DOS-07)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.board import BoardOrdinance
from app.domain.repositories.ports import Clock, FileStorage, UnitOfWork

logger = logging.getLogger("app.conclusion")


@dataclass(frozen=True)
class PurgeOutcome:
    """Documents closed in this run, documents still pending and the bytes of the closed ones."""

    removed: int
    pending: int
    bytes_freed: int


@dataclass(frozen=True)
class OrdinanceFileView:
    """The ordinance file seen as what the conclusion counts: its size and whether it is gone
    (`file_deleted_at`, the name the `PurgeableDocument` protocol of the rules uses)."""

    size_bytes: int
    file_deleted_at: datetime | None


def ordinance_file_view(ordinance: BoardOrdinance | None) -> OrdinanceFileView | None:
    """None when there is no ordinance or it has no file (typed data only)."""
    if ordinance is None or ordinance.file is None:
        return None
    return OrdinanceFileView(ordinance.file.size_bytes, ordinance.file.deleted_at)


class PurgeInputDocuments:
    """Removes, one document at a time, the stored file, the extracted page texts and the
    evidence excerpts, and marks the document `file_deleted_at`; then removes the file of the
    board ordinance and marks it, keeping its number, date and members. The metadata, the links
    and the generated documents stay.

    The file goes first and the rows go in a unit of work of their own: a crash between the two
    leaves a document without file and without mark, which the next attempt closes (a missing file
    counts as removed). A document whose file cannot be removed stays pending and the others go
    on. Every document of the process counts, including the ones outside the interstice.
    """

    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], storage: FileStorage, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._clock = clock

    def execute(self, process_id: UUID) -> PurgeOutcome:
        with self._uow_factory() as uow:
            documents = [
                d for d in uow.documents.list_for_process(process_id) if d.file_deleted_at is None
            ]
            ordinance = uow.board.get(process_id)
        removed = pending = freed = 0
        for document in documents:
            if self._purge(process_id, document.id, document.internal_name):
                removed += 1
                freed += document.size_bytes
            else:
                pending += 1
        file = ordinance.file if ordinance else None
        if file is not None and file.deleted_at is None:
            if self._purge_ordinance(process_id, file.internal_name):
                removed += 1
                freed += file.size_bytes
            else:
                pending += 1
        return PurgeOutcome(removed, pending, freed)

    def _remove_file(self, process_id: UUID, internal_name: str) -> None:
        self._storage.delete(process_id, internal_name)
        if self._storage.path(process_id, internal_name).exists():
            raise OSError("o arquivo continua no armazenamento")

    def _purge_ordinance(self, process_id: UUID, internal_name: str) -> bool:
        try:
            self._remove_file(process_id, internal_name)
            with self._uow_factory() as uow:
                uow.board.mark_file_deleted(process_id, self._clock.now())
                uow.commit()
        except OSError:
            logger.warning("purge: could not remove the ordinance file of process=%s", process_id)
            return False
        return True

    def _purge(self, process_id: UUID, document_id: UUID, internal_name: str) -> bool:
        try:
            self._remove_file(process_id, internal_name)
            with self._uow_factory() as uow:
                uow.extractions.delete_pages(document_id)
                uow.evidences.clear_excerpts_for_document(document_id)
                uow.documents.mark_file_deleted(document_id, self._clock.now())
                uow.commit()
        except OSError:
            logger.warning("purge: could not remove the file of document_id=%s", document_id)
            return False
        return True
