"""Background executor of document jobs: one daemon thread inside the backend (AD-008).

Jobs and their states live in PostgreSQL; the worker claims the oldest pending job (the
repository uses `FOR UPDATE SKIP LOCKED`), runs it and goes back for the next one, sleeping
`poll_seconds` when there is none. At start it recovers the jobs a restart left `PROCESSANDO`
(PIPE-03). Logs carry the exception type and the job id only (PIPE-10).
"""

import logging
import threading
from collections.abc import Callable

from app.application.use_cases.document_processing import (
    INTERNAL_ERROR,
    ProcessDocument,
    RecoverStuckJobs,
)
from app.domain.repositories.ports import Clock, JobStatus, UnitOfWork

logger = logging.getLogger("app.documents.worker")

THREAD_NAME = "document-worker"
JOIN_TIMEOUT_SECONDS = 10.0


class DocumentWorker:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        process_document: ProcessDocument,
        recover: RecoverStuckJobs,
        clock: Clock,
        poll_seconds: float = 2.0,
    ) -> None:
        self._uow_factory = uow_factory
        self._process_document = process_document
        self._recover = recover
        self._clock = clock
        self._poll_seconds = poll_seconds
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> bool:
        """Claims and runs one job; False when none was pending.

        A job that raises is logged and closed as failed, and still counts as run.
        """
        with self._uow_factory() as uow:
            job = uow.jobs.claim_next(self._clock.now())
            uow.commit()
        if job is None:
            return False
        try:
            self._process_document.execute(job.id, self._clock.now())
        except Exception as error:
            logger.error("job_id=%s error_type=%s", job.id, type(error).__name__)
            self._close_failed(job.id)
        return True

    def _close_failed(self, job_id) -> None:
        try:
            with self._uow_factory() as uow:
                uow.jobs.finish(job_id, JobStatus.FALHOU, self._clock.now(), INTERNAL_ERROR)
                uow.commit()
        except Exception as error:
            logger.error("job_id=%s error_type=%s", job_id, type(error).__name__)

    def start(self) -> None:
        """Recovers stuck jobs, then starts the loop thread; a second call does nothing."""
        if self._thread is not None:
            return
        try:
            self._recover.execute()
        except Exception as error:
            logger.error("recover error_type=%s", type(error).__name__)
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name=THREAD_NAME, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Asks the loop to end and waits for the job in hand, if any."""
        self._stopping.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(JOIN_TIMEOUT_SECONDS)

    def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                ran = self.run_once()
            except Exception as error:  # claiming failed (database down): wait and try again
                logger.error("claim error_type=%s", type(error).__name__)
                ran = False
            if not ran:
                self._stopping.wait(self._poll_seconds)
