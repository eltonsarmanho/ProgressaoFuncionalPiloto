"""Removal of the input documents of a process (DEL-05, DEL-06, DEL-08, DEL-09)."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories.ports import Clock, FileStorage, UnitOfWork

logger = logging.getLogger("app.conclusion")


@dataclass(frozen=True)
class PurgeOutcome:
    """Documents closed in this run, documents still pending and the bytes of the closed ones."""

    removed: int
    pending: int
    bytes_freed: int


class PurgeInputDocuments:
    """Removes, one document at a time, the stored file, the extracted page texts and the
    evidence excerpts, and marks the document `file_deleted_at`. The metadata, the links and the
    generated documents stay.

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
        removed = pending = freed = 0
        for document in documents:
            if self._purge(process_id, document.id, document.internal_name):
                removed += 1
                freed += document.size_bytes
            else:
                pending += 1
        return PurgeOutcome(removed, pending, freed)

    def _purge(self, process_id: UUID, document_id: UUID, internal_name: str) -> bool:
        try:
            self._storage.delete(process_id, internal_name)
            if self._storage.path(process_id, internal_name).exists():
                raise OSError("o arquivo continua no armazenamento")
            with self._uow_factory() as uow:
                uow.extractions.delete_pages(document_id)
                uow.evidences.clear_excerpts_for_document(document_id)
                uow.documents.mark_file_deleted(document_id, self._clock.now())
                uow.commit()
        except OSError:
            logger.warning("purge: could not remove the file of document_id=%s", document_id)
            return False
        return True
