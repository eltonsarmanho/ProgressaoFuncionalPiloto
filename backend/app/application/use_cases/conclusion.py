"""Concluding a process: the preview of what the conclusion removes (DEL-03) and the conclusion
itself, which purges the input documents (DEL-01, DEL-02, DEL-04, DEL-05, DEL-07 to DEL-10, DEL-15).

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
"""

from uuid import UUID

from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.conclusion import ConclusionPreview
from app.domain.entities.user import User
from app.domain.rules.conclusion_rules import summarize_purge


class GetConclusionPreview(_ScoringUseCase):
    def execute(self, actor: User, process_id: UUID) -> ConclusionPreview:
        """Files and bytes the conclusion frees and the generated kinds that have a PRONTO
        version (DEL-03). Every input document counts, the ones outside the interstice too."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            documents = uow.documents.list_for_process(process_id)
            ready = uow.generations.latest_ready_by_kind(process_id)
            return summarize_purge(documents, ready)
