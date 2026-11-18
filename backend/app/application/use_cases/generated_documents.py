"""Generated documents: the request, the run in the background, the recovery and the versions.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
Audit events carry identifiers, kinds, states and codes only, never the text of a document
(VER-07).
"""

import uuid
from collections.abc import Callable
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import load_generation_inputs
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import (
    DocumentKind,
    GeneratedDocument,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.user import User
from app.domain.errors import GenerationRefused
from app.domain.repositories.ports import Clock, UnitOfWork

GENERATED_ENTITY = "generated_document"


class RequestGeneration(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        clock: Clock,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock

    def execute(self, actor: User, process_id: UUID, kind: DocumentKind) -> GeneratedDocument:
        """Stores a GERANDO row for the executor to pick up (TAB-01, VER-04).

        A second request of the same kind while one is GERANDO is a 409 with the code
        `GERACAO_EM_ANDAMENTO`, raised by the repository without a race.
        """
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            inputs = load_generation_inputs(uow, process)
            if inputs.version is None:
                raise GenerationRefused(
                    GenerationCode.TABELA_NAO_ESCOLHIDA,
                    "Escolha a tabela de pontuação do processo antes de gerar.",
                )
            if not inputs.activities:
                raise GenerationRefused(
                    GenerationCode.SEM_ATIVIDADES_VALIDADAS,
                    "O processo não tem atividade validada.",
                )
            generation = GeneratedDocument(
                id=uuid.uuid4(),
                process_id=process.id,
                kind=kind,
                state=GenerationState.GERANDO,
                version_number=None,
                requested_by=actor.id,
                requested_at=self._clock.now(),
            )
            uow.generations.add(generation)
            self._audit.record(
                uow,
                actor.id,
                GENERATED_ENTITY,
                generation.id,
                AuditAction.CREATE,
                {},
                {"kind": kind, "state": generation.state},
            )
            uow.commit()
            return generation
