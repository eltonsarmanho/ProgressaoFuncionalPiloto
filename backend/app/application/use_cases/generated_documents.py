"""Generated documents: the request, the run in the background, the recovery and the versions.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
Audit events carry identifiers, kinds, states and codes only, never the text of a document
(VER-07).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.comprovante import ComprovantePlan, PageKind, SourceDocument
from app.domain.entities.document import Document
from app.domain.entities.generated import (
    DocumentKind,
    GeneratedDocument,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.user import User
from app.domain.errors import GenerationRefused
from app.domain.repositories.ports import (
    Clock,
    FileInspector,
    FileStorage,
    GeneratedFileStorage,
    UnitOfWork,
)
from app.domain.rules.comprovante_plan import (
    ComprovanteRefused,
    check_comprovante,
    plan_comprovante,
)

GENERATED_ENTITY = "generated_document"
MB = 1024 * 1024
_PIXELS_PER_MEGAPIXEL = 1_000_000


@dataclass(frozen=True)
class GenerationLimits:
    """What a request may ask for (CMP-09, CMP-13, DEL-11); the defaults are the spec values."""

    max_pages: int = 400
    png_max_megapixels: int = 12
    min_free_bytes: int = 200 * MB


def _png_pixels(
    originals: FileStorage, inspector: FileInspector, document: Document
) -> int | None:
    """Width times height of a PNG original that is still stored; None when it cannot be told."""
    path = originals.path(document.process_id, document.internal_name)
    if not path.is_file():
        return None
    megapixels = inspector.inspect(path).megapixels
    return None if megapixels is None else int(megapixels * _PIXELS_PER_MEGAPIXEL)


def checked_comprovante_plan(
    inputs: GenerationInputs,
    originals: FileStorage,
    inspector: FileInspector,
    limits: GenerationLimits,
    toc_capacity: int,
) -> ComprovantePlan:
    """The plan of the Comprovante, or the refusal that says why it cannot be built (CMP-09,
    CMP-10, CMP-13, DEL-11). Used by the request and again by the run, because an original can
    go away between the two."""
    plan = plan_comprovante(inputs.layout, inputs.activities, toc_capacity)
    attached = [p for p in plan.pages if p.kind is PageKind.ORIGINAL]
    used = {p.document_id for p in attached}
    sources = [
        SourceDocument(
            id=d.id,
            original_name=d.original_name,
            page_count=d.page_count,
            mime=d.mime,
            pixels=(
                _png_pixels(originals, inspector, d)
                if d.mime == "image/png" and d.id in used and d.file_deleted_at is None
                else None
            ),
            file_deleted=d.file_deleted_at is not None,
        )
        for d in inputs.documents
    ]
    check_comprovante(
        plan,
        sources,
        max_pages=limits.max_pages,
        png_max_megapixels=limits.png_max_megapixels,
    )
    known = {d.id: d for d in inputs.documents}
    for page in attached:
        document = known[page.document_id]
        if not originals.path(document.process_id, document.internal_name).is_file():
            raise ComprovanteRefused(
                GenerationCode.ORIGINAL_INDISPONIVEL,
                f"O documento {document.original_name} não está disponível "
                f"(página {page.source_page}).",
                document.id,
                page.source_page,
            )
    return plan


class RequestGeneration(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        clock: Clock,
        storage: GeneratedFileStorage,
        originals: FileStorage,
        inspector: FileInspector,
        limits: GenerationLimits,
        toc_capacity: int,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock
        self._storage = storage
        self._originals = originals
        self._inspector = inspector
        self._limits = limits
        self._toc_capacity = toc_capacity

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
            if kind is DocumentKind.RELATORIO:
                for activity in inputs.activities:
                    if not activity.title.strip() and not activity.description.strip():
                        raise GenerationRefused(
                            GenerationCode.ATIVIDADE_SEM_DESCRICAO,
                            f"A atividade {activity.id} não tem título nem descrição.",
                        )
            if self._storage.free_bytes() < self._limits.min_free_bytes:
                raise GenerationRefused(
                    GenerationCode.ESPACO_INSUFICIENTE,
                    "Não há espaço livre suficiente no servidor para gerar o documento.",
                )
            if kind is DocumentKind.COMPROVANTE:
                checked_comprovante_plan(
                    inputs, self._originals, self._inspector, self._limits, self._toc_capacity
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
