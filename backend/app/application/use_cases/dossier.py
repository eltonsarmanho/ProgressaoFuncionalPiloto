"""The checklist of the dossier of a process (DOS-02 to DOS-06, BNAV-02, BNAV-03).

The order and the origin of each item come from the versioned file, injected as a callable like
`Container.dossier_order`. The state of each item is derived by the pure `dossier_checklist` from
what the process has: the last `PRONTO` version of each generated kind, the board ordinance and the
marks "Entregue". Access follows the process (AccessPolicy): anything outside it is NotFound; a
concluded or archived process refuses the marks with 409 `PROCESSO_SOMENTE_LEITURA` but is still
read. A mark is audited with the item key and no justification (regra 5).
"""

from collections.abc import Callable
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.generated_documents import _EditUseCase
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.report import DossierItem, DossierSource
from app.domain.entities.user import User
from app.domain.errors import ValidationFailed
from app.domain.repositories.ports import Clock, UnitOfWork
from app.domain.rules.dossier_checklist import ChecklistItem, dossier_checklist

DELIVERY_ENTITY = "dossier_delivery"
KEY_FIELD = "key"


def _checklist(
    uow: UnitOfWork, process: FunctionalProcess, order: tuple[DossierItem, ...]
) -> list[ChecklistItem]:
    return dossier_checklist(
        order,
        uow.generations.latest_ready_by_kind(process.id),
        uow.board.get(process.id),
        uow.dossier_deliveries.keys(process.id),
        process.scoring_table_version_id,
    )


class GetDossier(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        dossier_order: Callable[[], tuple[DossierItem, ...]],
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._order = dossier_order

    def execute(self, actor: User, process_id: UUID) -> list[ChecklistItem]:
        """The items in the order of the file, each with its state. A read never writes."""
        order = self._order()
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            return _checklist(uow, process, order)


class SetDossierDelivery(_EditUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        dossier_order: Callable[[], tuple[DossierItem, ...]],
        clock: Clock,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._order = dossier_order
        self._clock = clock

    def execute(
        self, actor: User, process_id: UUID, key: str, delivered: bool
    ) -> list[ChecklistItem]:
        """Marks or unmarks "Entregue" on an item the system does not produce and returns the new
        checklist (DOS-04). Only a `MANUAL` key is accepted (422 on `key`); repeating a mark or an
        unmark changes nothing and writes no event."""
        order = self._order()
        with self._uow_factory() as uow:
            process = self._editable(uow, actor, process_id)
            item = next((i for i in order if i.key == key), None)
            if item is None or item.source is not DossierSource.MANUAL:
                raise ValidationFailed(
                    KEY_FIELD, "Só um item que o sistema não produz pode ser marcado"
                )
            if delivered:
                changed = uow.dossier_deliveries.mark(process.id, key, actor.id, self._clock.now())
            else:
                changed = uow.dossier_deliveries.unmark(process.id, key)
            if changed:
                self._audit.record(
                    uow,
                    actor.id,
                    DELIVERY_ENTITY,
                    process.id,
                    AuditAction.UPDATE,
                    {"item_key": None if delivered else key, "delivered": not delivered},
                    {"item_key": key if delivered else None, "delivered": delivered},
                )
            uow.commit()
            return _checklist(uow, process, order)
