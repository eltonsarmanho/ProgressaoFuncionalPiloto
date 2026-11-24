"""Conclusion routes (DEL-01, DEL-02, DEL-03, DEL-04, DEL-15): the preview of what concluding the
process removes, and the conclusion that removes the input documents and moves the process to
CONCLUIDO.

Access follows the process: outside it, 404; the roles are those of the status transition. The
removal is irreversible, so the body must carry `confirmar: true`. A process version that is not
the stored one is a 409 with the code `VERSAO_DESATUALIZADA`. When some file cannot be removed the
answer is still 200, with `arquivos_pendentes` and the alert `EXCLUSAO_PARCIAL`, and repeating the
request finishes what is left.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.domain.entities.generated import GenerationCode
from app.domain.entities.user import User
from app.domain.errors import StaleVersion
from app.presentation.dependencies import Container, current_user, get_container
from app.presentation.schemas.generated import ConclusionIn, ConclusionOut, ConclusionPreviewOut

router = APIRouter(prefix="/api/processes", tags=["conclusion"])

ContainerDep = Annotated[Container, Depends(get_container)]
UserDep = Annotated[User, Depends(current_user)]


@router.get("/{process_id}/conclusion", response_model=ConclusionPreviewOut)
async def conclusion_preview(
    process_id: UUID, actor: UserDep, container: ContainerDep
) -> ConclusionPreviewOut:
    preview = await run_in_threadpool(container.conclusion_preview.execute, actor, process_id)
    return ConclusionPreviewOut.of(preview)


@router.post("/{process_id}/conclusion", response_model=ConclusionOut)
async def conclude(
    process_id: UUID, body: ConclusionIn, actor: UserDep, container: ContainerDep
) -> ConclusionOut:
    try:
        result = await run_in_threadpool(
            container.conclude_process.execute,
            actor,
            process_id,
            body.expected_version,
            body.confirmar,
            body.justificativa,
        )
    except StaleVersion as error:
        raise StaleVersion(
            str(error), error.code or GenerationCode.VERSAO_DESATUALIZADA.value
        ) from None
    return ConclusionOut.of(result)
