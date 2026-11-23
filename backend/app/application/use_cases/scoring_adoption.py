"""The new scoring table version takes over from the one it supersedes (GI-07, GI-10, AD-023)."""

from uuid import UUID

from app.application.services.audit_service import AuditService
from app.application.use_cases.scoring_defaults import UNIT_DEFAULT_ENTITY
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.repositories.ports import UnitOfWork

PROCESS_ENTITY = "process"
ADOPTION_JUSTIFICATION = "AD-023: Grupo I no total"
EDITABLE = (ProcessStatus.RASCUNHO, ProcessStatus.EM_ANDAMENTO)


class AdoptSupersedingVersion:
    """Marks the previous version as superseded and moves the editable processes to the new one.

    It works on the caller's unit of work and never commits: the seed commits the new version,
    the mark and the moves together, so a failure in the middle changes nothing. Idempotent: a
    second run finds the mark in place and no process left on the previous version. Processes
    that are concluded or archived keep their version, and so do the documents already generated
    (AD-012). Each move is audited as a change made by the system (no actor). The units that had
    the previous version in use lose that mark in the same transaction (GTAB-09), each with a
    system audit event; the other units keep theirs.
    """

    def __init__(self, audit: AuditService):
        self._audit = audit

    def execute(
        self, uow: UnitOfWork, table_id: UUID, superseded_name: str | None, new_name: str
    ) -> int:
        """Returns how many processes were moved; 0 when there is nothing to take over."""
        if not superseded_name or superseded_name == new_name:
            return 0
        versions = {v.name: v for v in uow.scoring_tables.list_versions(table_id)}
        previous, new = versions.get(superseded_name), versions.get(new_name)
        if previous is None or new is None:
            return 0
        if previous.superseded_by_id not in (None, new.id):
            return 0  # another version already replaced it
        if previous.superseded_by_id is None:
            uow.scoring_tables.set_superseded(previous.id, new.id)
        self._clear_unit_marks(uow, previous.id)
        moved = 0
        for process in uow.processes.list_using_version(previous.id, EDITABLE):
            uow.processes.set_scoring_table_version(process.id, new.id)
            self._audit.record(
                uow,
                None,
                PROCESS_ENTITY,
                process.id,
                AuditAction.UPDATE,
                {"scoring_table_version_id": previous.id},
                {"scoring_table_version_id": new.id},
                ADOPTION_JUSTIFICATION,
            )
            moved += 1
        return moved

    def _clear_unit_marks(self, uow: UnitOfWork, version_id: UUID) -> None:
        for unit_id in uow.scoring_tables.unit_ids_defaulting_to(version_id):
            uow.scoring_tables.clear_unit_default(unit_id)
            self._audit.record(
                uow,
                None,
                UNIT_DEFAULT_ENTITY,
                unit_id,
                AuditAction.DELETE,
                {"version_id": version_id},
                {"version_id": None},
            )
