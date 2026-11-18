"""Rules of concluding a process (DEL-01, DEL-02): which generated documents are still missing
and whether an operation is running. Pure: the caller reads the database and passes the facts.
"""

from collections.abc import Iterable

from app.domain.entities.conclusion import ConclusionCheck
from app.domain.entities.generated import DocumentKind, GenerationCode

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
