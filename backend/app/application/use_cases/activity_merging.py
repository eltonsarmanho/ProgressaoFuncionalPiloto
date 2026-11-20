"""The merge-duplicates and separate use cases behind the routes (DUP-04, DUP-07).

Access follows the process: outside it, NotFound. Both commit; the merge itself lives in
`MergeDuplicateActivities` and runs here in the unit of work this use case opens.
"""

from collections.abc import Callable
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.activity_merge import MergeDuplicateActivities
from app.application.services.audit_service import AuditService
from app.application.use_cases.scoring import ACTIVITY_NOT_FOUND, _ScoringUseCase
from app.domain.entities.activity import Activity
from app.domain.entities.user import User
from app.domain.errors import NotFound
from app.domain.repositories.ports import UnitOfWork


class MergeProcessDuplicates(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        merger: MergeDuplicateActivities,
    ):
        super().__init__(uow_factory, audit, policy)
        self._merger = merger

    def execute(self, actor: User, process_id: UUID) -> int:
        """Merges the duplicates of the process and returns how many were merged; a read-only
        process answers 0 and is left as it is."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            report = self._merger.merge_process(uow, process_id, actor.id)
            uow.commit()
            return report.count


class SeparateActivity(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        merger: MergeDuplicateActivities,
    ):
        super().__init__(uow_factory, audit, policy)
        self._merger = merger

    def execute(
        self, actor: User, activity_id: UUID, expected_version: int | None = None
    ) -> Activity:
        with self._uow_factory() as uow:
            found = uow.activities.get(activity_id)
            if found is None:
                raise NotFound(ACTIVITY_NOT_FOUND)
            self._writable(uow, actor, found.process_id)
            restored = self._merger.separate(uow, actor.id, activity_id, expected_version)
            uow.commit()
            return restored
