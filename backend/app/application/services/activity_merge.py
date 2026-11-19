"""Merging the duplicate activities of a process (DUP-01..DUP-07).

Two activities that the duplicate rule (`duplicate_groups`) reports become one: the validated one
that was created first stays, or the one created first when none or all are validated. The others
keep their row, marked `merged_into_id`, and give their evidences (document and page) to the one
that stays, minus the pairs it already has. Everything runs in the caller's unit of work and the
caller commits, so a failure in the middle changes nothing; running it again changes nothing.
"""

from dataclasses import dataclass
from uuid import UUID

from app.application.services.audit_service import AuditService
from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.errors import NotFound
from app.domain.repositories.ports import UnitOfWork
from app.domain.rules.scoring_duplicates import duplicate_groups

ACTIVITY_ENTITY = "activity"
MERGE = "MERGE"


@dataclass(frozen=True)
class MergedActivity:
    merged_id: UUID
    kept_id: UUID
    evidences_moved: int


@dataclass(frozen=True)
class MergeReport:
    merged: tuple[MergedActivity, ...] = ()

    @property
    def count(self) -> int:
        return len(self.merged)


def choose_kept(group: tuple[Activity, ...]) -> Activity:
    """`group` comes in creation order: the first validated one, else the first one."""
    return next((a for a in group if a.status is ActivityStatus.VALIDADA), group[0])


class MergeDuplicateActivities:
    def __init__(self, audit: AuditService):
        self._audit = audit

    def merge_process(
        self, uow: UnitOfWork, process_id: UUID, actor_id: UUID | None
    ) -> MergeReport:
        """Merges every group of duplicates; a read-only process is left as it is."""
        process = uow.processes.get(process_id)
        if process is None:
            raise NotFound("Processo não encontrado")
        if process.status.is_read_only:
            return MergeReport()
        activities = uow.activities.list_for_process(process_id)
        contents = uow.evidences.content_keys_for_activities([a.id for a in activities])
        done: list[MergedActivity] = []
        for group in duplicate_groups(activities, contents):
            kept = choose_kept(group)
            for other in group:
                if other.id != kept.id:
                    done.append(self._merge(uow, actor_id, other, kept))
        return MergeReport(tuple(done))

    def _merge(
        self, uow: UnitOfWork, actor_id: UUID | None, merged: Activity, kept: Activity
    ) -> MergedActivity:
        # What was merged into `merged` before goes to `kept`, so no chain of marks builds up.
        for earlier in uow.activities.list_merged_into(merged.id):
            uow.activities.set_merged_into(earlier, kept.id, earlier.version)
        evidence_ids = [e.id for e in uow.evidences.list_for_activity(merged.id)]
        moved = uow.evidences.move(evidence_ids, kept.id, merged.id)
        uow.activities.set_merged_into(merged, kept.id, merged.version)
        self._audit.record(
            uow,
            actor_id,
            ACTIVITY_ENTITY,
            merged.id,
            AuditAction.UPDATE,
            {},
            {
                "operation": MERGE,
                "merged_activity_id": merged.id,
                "kept_activity_id": kept.id,
                "merged_into_id": kept.id,
                "evidences_moved": len(moved),
            },
        )
        return MergedActivity(merged.id, kept.id, len(moved))
