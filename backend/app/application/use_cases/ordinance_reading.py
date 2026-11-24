"""The background reading of the board ordinance (PORT-02, PORT-03, PORT-04, PORT-07).

The executor takes the oldest queued ordinance, reads the text of its pages, masks the identifiers
and sends only that text to the AI (PORT-04); what comes back is untrusted and is checked in the
ORIGINAL text of the page each value cites (AD-009, PORT-03). The result is merged into the row
under its lock, so what the person typed, even while the reading ran, is never overwritten
(regra 1).
Any failure closes the row as `FALHOU` with a code and leaves the data editable; the log carries
the type of an unexpected error, never its message (it may hold text of the pages).
"""

import logging
from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.documents import MIME_BY_KIND
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import BoardOrdinance, OrdinanceReadingCode, ReadingState
from app.domain.entities.document import TextMethod
from app.domain.errors import Conflict
from app.domain.repositories.ports import (
    Clock,
    ExtractedPage,
    FileStorage,
    OrdinanceExtractionError,
    OrdinanceExtractor,
    TextExtractor,
    UnitOfWork,
)
from app.domain.rules.masking import mask_identifiers
from app.domain.rules.ordinance_grounding import OrdinanceAi, ground_ordinance, merge_reading
from app.domain.rules.text_quality import ocr_needs_review
from app.domain.rules.upload_validation import FileKind

logger = logging.getLogger("app.board.ordinance")

BOARD_ENTITY = "board_ordinance"
_KIND_BY_MIME = {mime: kind for kind, mime in MIME_BY_KIND.items()}


class _Illegible(Exception):
    """The pages have no text or the OCR is too weak to trust."""


def _check_legible(pages: Sequence[ExtractedPage]) -> None:
    text = "\n\n".join(page.text for page in pages)
    if not text.strip():
        raise _Illegible
    scores: list[Decimal] = [
        p.ocr_confidence
        for p in pages
        if p.method is TextMethod.OCR and p.ocr_confidence is not None
    ]
    if scores and ocr_needs_review(sum(scores) / len(scores), text):
        raise _Illegible


def _masked_text(pages: Sequence[ExtractedPage]) -> str:
    """Page-marked text with CPF, RG, e-mail and phone replaced by markers; names stay."""
    return "\n\n".join(
        f"[PÁGINA {page.page_number}]\n{mask_identifiers(page.text).text}" for page in pages
    )


def _raw_json(ai: OrdinanceAi) -> dict[str, Any]:
    """What the AI returned, as stored beside the grounded values."""
    return {
        "number": ai.number,
        "number_page": ai.number_page,
        "ordinance_date": ai.ordinance_date.isoformat() if ai.ordinance_date else None,
        "date_page": ai.date_page,
        "members": [{"name": m.name, "role": m.role, "page": m.page} for m in ai.members],
    }


class RunOrdinanceReading:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        clock: Clock,
        storage: FileStorage,
        text_extractor: TextExtractor,
        extractor: OrdinanceExtractor,
    ) -> None:
        self._uow_factory = uow_factory
        self._audit = audit
        self._clock = clock
        self._storage = storage
        self._text_extractor = text_extractor
        self._extractor = extractor

    def run_next(self) -> bool:
        """The runner of the executor: reads the oldest queued ordinance; False when none waits."""
        with self._uow_factory() as uow:
            claimed = uow.board.claim_next_pending(self._clock.now())
            uow.commit()
        if claimed is None:
            return False
        try:
            self._read(claimed)
        except OrdinanceExtractionError as error:
            self._fail(claimed.process_id, error.code)
        except _Illegible:
            self._fail(claimed.process_id, OrdinanceReadingCode.TEXTO_ILEGIVEL)
        except Exception as error:
            logger.error("ordinance reading failed: %s", type(error).__name__)
            self._fail(claimed.process_id, OrdinanceReadingCode.ERRO_INTERNO)
        return True

    def _read(self, claimed: BoardOrdinance) -> None:
        assert claimed.file is not None
        path = self._storage.path(claimed.process_id, claimed.file.internal_name)
        kind = _KIND_BY_MIME.get(claimed.file.mime, FileKind.PDF)
        pages = self._text_extractor.extract(path, kind).pages
        _check_legible(pages)
        answer = self._extractor.extract(_masked_text(pages))
        grounded = ground_ordinance(answer, {page.page_number: page.text for page in pages})
        with self._uow_factory() as uow:
            current = uow.board.lock(claimed.process_id)
            merged = merge_reading(current, grounded)
            done = uow.board.finish_read(merged, _raw_json(answer), self._clock.now())
            self._audit.record(
                uow,
                None,
                BOARD_ENTITY,
                claimed.process_id,
                AuditAction.STATUS,
                {"reading_state": ReadingState.LENDO},
                {
                    "reading_state": ReadingState.LIDA,
                    "member_count": len(done.members),
                    "warnings": [f"{w.code.value}:{w.field}" for w in done.warnings],
                },
            )
            uow.commit()

    def _fail(self, process_id: UUID, code: OrdinanceReadingCode) -> None:
        """Closes the row as FALHOU; the typed data are not touched."""
        try:
            with self._uow_factory() as uow:
                uow.board.finish_failed(process_id, code, self._clock.now())
                self._audit.record(
                    uow,
                    None,
                    BOARD_ENTITY,
                    process_id,
                    AuditAction.STATUS,
                    {"reading_state": ReadingState.LENDO},
                    {"reading_state": ReadingState.FALHOU, "reading_code": code},
                )
                uow.commit()
        except Conflict:
            logger.error("ordinance reading was no longer running when it failed: %s", code.value)

    def recover_interrupted(self) -> int:
        """Run at startup, before the executor starts: a reading a restart left `LENDO` becomes
        `FALHOU` with `INTERROMPIDA`, audited without a user; a queued one stays in the queue.
        Returns how many were closed."""
        with self._uow_factory() as uow:
            interrupted = uow.board.recover_interrupted(self._clock.now())
            for process_id in interrupted:
                self._audit.record(
                    uow,
                    None,
                    BOARD_ENTITY,
                    process_id,
                    AuditAction.STATUS,
                    {"reading_state": ReadingState.LENDO},
                    {
                        "reading_state": ReadingState.FALHOU,
                        "reading_code": OrdinanceReadingCode.INTERROMPIDA,
                    },
                )
            uow.commit()
        return len(interrupted)
