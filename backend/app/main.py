"""FastAPI application factory. Run with: uvicorn --factory app.main:create_app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, load_settings
from app.domain.repositories.ports import Clock
from app.infrastructure.clock import SystemClock
from app.infrastructure.database.session import make_engine
from app.presentation.api import auth, health, units, users
from app.presentation.csrf import install_auth_middleware
from app.presentation.dependencies import build_container
from app.presentation.errors import install_error_handlers


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or load_settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Progressão Funcional", lifespan=lifespan)
    app.state.container = build_container(settings, engine, clock or SystemClock())
    install_error_handlers(app)
    install_auth_middleware(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(units.router)
    return app
