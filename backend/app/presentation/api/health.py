"""Health check with database probe (INFRA-01, INFRA-03)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.presentation.dependencies import Container, get_container

router = APIRouter(prefix="/api", tags=["health"])


def _database_ok(container: Container) -> bool:
    try:
        with container.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


@router.get("/health")
async def health(container: Annotated[Container, Depends(get_container)]) -> JSONResponse:
    if await run_in_threadpool(_database_ok, container):
        return JSONResponse({"status": "ok", "database": "ok"})
    return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)
