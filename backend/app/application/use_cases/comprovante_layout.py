"""The arrangement of the Comprovante: reading it and saving it (ARR-01 to ARR-08, CMP-04).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden. A
document flagged outside the interstice is not part of the arrangement: its pages are left out
of what is read, and a save that names it is refused as a document that is not in the process
(FORA-01). Audit events carry identifiers and counts, never names or text.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    EvidenceKey,
    SourceDocument,
    Staleness,
)
from app.domain.entities.generated import GenerationAlert, GenerationAlertCode
from app.domain.entities.user import User
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.comprovante_plan import invalid_entries, layout_staleness, plan_comprovante

STALE_LAYOUT_MESSAGE = (
    "Há atividades validadas, rejeitadas, movidas de item ou com novos vínculos desde que o "
    "arranjo foi salvo."
)


@dataclass(frozen=True)
class LayoutView:
    """What the screen shows: the arrangement in force (the saved one brought up to date with
    the current activities, or the one derived from the links), whether it is saved, why it is
    stale, the pages that cannot be attached any more and the plan with the numbering the
    Comprovante will have."""

    layout: ComprovanteLayout
    saved: bool
    staleness: Staleness
    invalid: tuple[EvidenceKey, ...]
    plan: ComprovantePlan
    alerts: tuple[GenerationAlert, ...]

    @property
    def stale(self) -> bool:
        return self.staleness.is_stale


def source_documents(inputs: GenerationInputs) -> list[SourceDocument]:
    """The documents of the process that can take part in the arrangement."""
    return [
        SourceDocument(
            id=d.id,
            original_name=d.original_name,
            page_count=d.page_count,
            mime=d.mime,
            file_deleted=d.file_deleted_at is not None,
        )
        for d in inputs.documents
    ]


class GetComprovanteLayout(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        toc_capacity: int,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._toc_capacity = toc_capacity

    def execute(self, actor: User, process_id: UUID) -> LayoutView:
        """A read never writes. Without a saved arrangement the view is the derived one with
        version 0 (ARR-01); with one, `stale` and the alert say that the activities or the links
        moved on since it was saved (ARR-08)."""
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            inputs = load_generation_inputs(uow, process)
            saved = uow.comprovante_layouts.get(process.id)
        staleness = (
            Staleness()
            if saved is None
            else layout_staleness(saved, inputs.activities, inputs.evidences)
        )
        return LayoutView(
            layout=inputs.layout,
            saved=saved is not None,
            staleness=staleness,
            invalid=invalid_entries(inputs.layout, source_documents(inputs)),
            plan=plan_comprovante(inputs.layout, inputs.activities, self._toc_capacity),
            alerts=(
                (GenerationAlert(GenerationAlertCode.ARRANJO_DESATUALIZADO, STALE_LAYOUT_MESSAGE),)
                if staleness.is_stale
                else ()
            ),
        )
