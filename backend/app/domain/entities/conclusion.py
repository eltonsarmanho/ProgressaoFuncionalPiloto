"""Preview, check and result of concluding a process (DEL-03, DEL-08)."""

from dataclasses import dataclass

from app.domain.entities.generated import DocumentKind, GenerationAlert, GenerationCode
from app.domain.entities.process import ProcessStatus


@dataclass(frozen=True)
class ConclusionPreview:
    """What concluding would remove, which required documents already have a PRONTO and which
    board documents are still missing (a warning that never blocks, DOS-07)."""

    files: int
    bytes: int
    artifacts: dict[DocumentKind, bool]
    pending_board: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConclusionCheck:
    """The refusal code of the conclusion, or None when it may proceed."""

    code: GenerationCode | None = None
    missing_kinds: tuple[DocumentKind, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.code is None


@dataclass(frozen=True)
class ConclusionResult:
    status: ProcessStatus
    files_removed: int
    files_pending: int
    bytes_freed: int
    alerts: tuple[GenerationAlert, ...] = ()
