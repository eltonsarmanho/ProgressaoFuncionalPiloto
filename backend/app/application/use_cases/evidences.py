"""Links between an activity and the document page that proves it (VINC-02, VINC-03, VINC-05).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
Audit events carry identifiers and the justification only, never the document text.
"""

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.use_cases.document_processing import MAX_EXCERPT_CHARS
from app.application.use_cases.documents import EVIDENCE_ENTITY, active_run
from app.domain.entities.activity import Activity
from app.domain.entities.audit import AuditAction
from app.domain.entities.document import Document
from app.domain.entities.user import User
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.repositories.ports import ActivityEvidence, UnitOfWork

ACTIVITY_NOT_FOUND = "Atividade não encontrada"
DOCUMENT_NOT_FOUND = "Documento não encontrado"
EVIDENCE_NOT_FOUND = "Vínculo não encontrado"


class _EvidenceUseCase:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
    ):
        self._uow_factory = uow_factory
        self._audit = audit
        self._policy = policy

    def _activity(self, uow: UnitOfWork, actor: User, activity_id: UUID) -> Activity:
        """The activity of a process the actor can change: 404 outside access, 409 if closed."""
        activity = uow.activities.get(activity_id)
        process = uow.processes.get(activity.process_id) if activity else None
        if activity is None or process is None or not self._policy.can_read_process(actor, process):
            raise NotFound(ACTIVITY_NOT_FOUND)
        if process.status.is_read_only:
            raise Conflict("Processo concluído ou arquivado não pode ser alterado")
        return activity

    def _record(
        self,
        uow: UnitOfWork,
        actor: User,
        evidence: ActivityEvidence,
        action: AuditAction,
        before: dict,
        after: dict,
        justification: str | None = None,
    ) -> None:
        self._audit.record(
            uow, actor.id, EVIDENCE_ENTITY, evidence.id, action, before, after, justification
        )


def _page_excerpt(uow: UnitOfWork, document: Document, page_number: int) -> str:
    """The start of the page text of the active run, or empty when it was not read."""
    run = active_run(uow, document.id)
    if run is None:
        return ""
    for page in uow.extractions.list_pages(document.id):
        if page.run_id == run.id and page.page_number == page_number:
            return " ".join(page.text.split())[:MAX_EXCERPT_CHARS]
    return ""


def _link_view(evidence: ActivityEvidence) -> dict:
    return {
        "activity_id": evidence.activity_id,
        "document_id": evidence.document_id,
        "page_number": evidence.page_number,
    }


class LinkEvidence(_EvidenceUseCase):
    def execute(
        self,
        actor: User,
        activity_id: UUID,
        document_id: UUID,
        page: int,
        justification: str | None = None,
    ) -> ActivityEvidence:
        """Links an activity to a page of a document of the same process.

        The justification is optional, also for a document already linked to ANOTHER activity
        (VINC-03 relaxed by UIM-16); the same (activity, document, page) twice is a Conflict
        (VINC-02).
        """
        with self._uow_factory() as uow:
            activity = self._activity(uow, actor, activity_id)
            document = uow.documents.get(document_id)
            process = uow.processes.get(document.process_id) if document else None
            if document is None or process is None or not self._policy.can_read_process(
                actor, process
            ):
                raise NotFound(DOCUMENT_NOT_FOUND)
            if document.process_id != activity.process_id:
                raise ValidationFailed("documento", "O documento pertence a outro processo")
            if not 1 <= page <= document.page_count:
                raise ValidationFailed("pagina", "Página fora do documento")
            justification = (justification or "").strip() or None
            evidence = ActivityEvidence(
                id=uuid.uuid4(),
                activity_id=activity.id,
                document_id=document.id,
                page_number=page,
                excerpt=_page_excerpt(uow, document, page),
                created_by=actor.id,
            )
            uow.evidences.add(evidence)
            self._record(
                uow,
                actor,
                evidence,
                AuditAction.CREATE,
                {},
                {**_link_view(evidence), "operation": "LINK"},
                justification,
            )
            uow.commit()
            return evidence


class UnlinkEvidence(_EvidenceUseCase):
    def execute(self, actor: User, activity_id: UUID, evidence_id: UUID) -> None:
        """Removes the link and keeps the activity (VINC-05)."""
        with self._uow_factory() as uow:
            activity = self._activity(uow, actor, activity_id)
            evidence = next(
                (e for e in uow.evidences.list_for_activity(activity.id) if e.id == evidence_id),
                None,
            )
            if evidence is None:
                raise NotFound(EVIDENCE_NOT_FOUND)
            uow.evidences.remove(evidence.id)
            self._record(
                uow,
                actor,
                evidence,
                AuditAction.UPDATE,
                _link_view(evidence),
                {"operation": "UNLINK"},
            )
            uow.commit()


@dataclass(frozen=True)
class EvidenceView:
    """A link with the display name of its document."""

    evidence: ActivityEvidence
    document_name: str


class ListEvidences:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    def execute(self, activity_ids: Sequence[UUID]) -> dict[UUID, list[EvidenceView]]:
        """The links of each activity, for presenting activities the caller already read.

        It checks no access: the ids must come from a use case that did.
        """
        names: dict[UUID, str] = {}
        found: dict[UUID, list[EvidenceView]] = {}
        with self._uow_factory() as uow:
            for activity_id in activity_ids:
                views = []
                for evidence in uow.evidences.list_for_activity(activity_id):
                    if evidence.document_id not in names:
                        document = uow.documents.get(evidence.document_id)
                        names[evidence.document_id] = document.original_name if document else ""
                    views.append(EvidenceView(evidence, names[evidence.document_id]))
                found[activity_id] = views
        return found
