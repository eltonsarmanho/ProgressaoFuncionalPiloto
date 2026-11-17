"""Composition root for request handlers (AD-001: wiring happens only here and in main)."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import Engine

from app.application.use_cases.auth import GetCurrentSession, Login, Logout
from app.core.config import Settings
from app.domain.entities.user import Session, User
from app.domain.repositories.ports import Clock, UnitOfWork
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from app.infrastructure.security import tokens
from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher


@dataclass
class Container:
    settings: Settings
    engine: Engine
    clock: Clock
    uow_factory: Callable[[], UnitOfWork]
    login: Login
    logout: Logout
    current_session: GetCurrentSession


def build_container(settings: Settings, engine: Engine, clock: Clock) -> Container:
    session_factory = make_session_factory(engine)

    def uow_factory() -> UnitOfWork:
        return SqlUnitOfWork(session_factory)

    return Container(
        settings=settings,
        engine=engine,
        clock=clock,
        uow_factory=uow_factory,
        login=Login(uow_factory, Argon2PasswordHasher(), tokens, clock),
        logout=Logout(uow_factory, tokens),
        current_session=GetCurrentSession(uow_factory, tokens, clock),
    )


def get_container(request: Request) -> Container:
    return request.app.state.container


def current_user(request: Request) -> User:
    """Set by the auth middleware for every protected /api route."""
    return request.state.user


def current_session(request: Request) -> Session:
    return request.state.session
