"""Rules of concluding a process (DEL-01, DEL-02): which generated documents are still missing
and whether an operation is running. Pure: the caller reads the database and passes the facts.
"""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from app.domain.entities.conclusion import ConclusionCheck, ConclusionPreview, ConclusionResult
from app.domain.entities.generated import (
    DocumentKind,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
)
from app.domain.entities.process import ProcessStatus

# The order the refusal lists the missing kinds in.
_KIND_ORDER = (DocumentKind.TABELA, DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)


def check_conclusion(
    ready_kinds: Iterable[DocumentKind], active_operations: int
) -> ConclusionCheck:
    """`ARTEFATOS_PENDENTES` while a kind has no PRONTO version (DEL-01), then
    `OPERACAO_EM_ANDAMENTO` while a generation, a wording or a document processing runs (DEL-02).

    `active_operations` counts the running operations of the process.
    """
    ready = set(ready_kinds)
    missing = tuple(kind for kind in _KIND_ORDER if kind not in ready)
    if missing:
        return ConclusionCheck(GenerationCode.ARTEFATOS_PENDENTES, missing)
    if active_operations > 0:
        return ConclusionCheck(GenerationCode.OPERACAO_EM_ANDAMENTO)
    return ConclusionCheck()


class PurgeableDocument(Protocol):
    """What the purge needs of an input document: its size and whether the file is gone."""

    size_bytes: int
    file_deleted_at: datetime | None


def summarize_purge(
    documents: Iterable[PurgeableDocument], ready_kinds: Iterable[DocumentKind] = ()
) -> ConclusionPreview:
    """Files and bytes the conclusion would remove: only the documents that still have a file
    (DEL-03). `ready_kinds` marks the generated kinds that have a PRONTO version."""
    remaining = [doc for doc in documents if doc.file_deleted_at is None]
    ready = set(ready_kinds)
    return ConclusionPreview(
        files=len(remaining),
        bytes=sum(doc.size_bytes for doc in remaining),
        artifacts={kind: kind in ready for kind in DocumentKind},
    )


def purge_outcome(removed: int, failed: int, bytes_freed: int) -> ConclusionResult:
    """CONCLUIDO when no file is pending (DEL-07), otherwise the process stays EM_ANDAMENTO with
    the `EXCLUSAO_PARCIAL` alert and the counts (DEL-08). Nothing to remove gives zeros and
    CONCLUIDO, so repeating a concluded process changes nothing (DEL-09)."""
    if failed == 0:
        return ConclusionResult(ProcessStatus.CONCLUIDO, removed, 0, bytes_freed)
    alert = GenerationAlert(
        GenerationAlertCode.EXCLUSAO_PARCIAL,
        f"{removed} arquivo(s) removido(s) e {failed} pendente(s); repita a conclusão.",
    )
    return ConclusionResult(ProcessStatus.EM_ANDAMENTO, removed, failed, bytes_freed, (alert,))
