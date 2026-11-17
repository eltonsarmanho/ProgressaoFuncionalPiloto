"""FastAPI application factory. Run with: uvicorn --factory app.main:create_app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, load_settings
from app.core.logging import configure_logging, install_access_log
from app.domain.repositories.ports import AiExtractor, Clock, TextExtractor
from app.infrastructure.clock import SystemClock
from app.infrastructure.database.session import make_engine
from app.infrastructure.jobs.worker import DocumentWorker
from app.presentation.api import (
    activities,
    auth,
    career,
    health,
    processes,
    professors,
    scoring,
    scoring_tables,
    scoring_tables_admin,
    units,
    users,
)
from app.presentation.csrf import install_auth_middleware
from app.presentation.dependencies import build_container
from app.presentation.errors import install_error_handlers


def create_app(
    settings: Settings | None = None,
    clock: Clock | None = None,
    ai_extractor: AiExtractor | None = None,
    text_extractor: TextExtractor | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    configure_logging()
    engine = make_engine(settings.database_url)
    container = build_container(
        settings, engine, clock or SystemClock(), ai_extractor, text_extractor
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker = None
        if settings.worker_enabled:
            worker = DocumentWorker(
                container.uow_factory,
                container.process_document,
                container.recover_stuck_jobs,
                container.clock,
            )
            worker.start()
        yield
        if worker is not None:
            worker.stop()
        engine.dispose()

    app = FastAPI(title="Progressão Funcional", lifespan=lifespan)
    app.state.container = container
    install_error_handlers(app)
    install_auth_middleware(app)
    install_access_log(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(units.router)
    app.include_router(professors.router)
    app.include_router(processes.router)
    app.include_router(career.router)
    app.include_router(scoring_tables.router)
    app.include_router(scoring_tables_admin.router)
    app.include_router(scoring.router)
    app.include_router(activities.router)
    return app
