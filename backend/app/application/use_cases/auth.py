"""Authentication use cases (AUTH-02, AUTH-04, AUTH-05, AUTH-11; AD-003)."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.domain.entities.user import Session, User
from app.domain.errors import DomainError
from app.domain.repositories.ports import Clock, PasswordHasher, UnitOfWork

INVALID_CREDENTIALS_MESSAGE = "Usuário ou senha inválidos"
MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=15)
IDLE_TIMEOUT = timedelta(minutes=30)
ABSOLUTE_TIMEOUT = timedelta(hours=8)


class InvalidCredentials(DomainError):
    def __init__(self) -> None:
        super().__init__(INVALID_CREDENTIALS_MESSAGE)


class TooManyAttempts(DomainError):
    def __init__(self) -> None:
        super().__init__("Muitas tentativas de login. Tente novamente mais tarde.")


class Unauthenticated(DomainError):
    def __init__(self) -> None:
        super().__init__("Sessão inválida ou expirada")


class TokenService(Protocol):
    def new_session_token(self) -> str: ...

    def new_csrf_token(self) -> str: ...

    def hash_token(self, token: str) -> str: ...


@dataclass(frozen=True)
class LoginResult:
    token: str
    session: Session
    user: User


class Login:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ):
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    def execute(self, email: str, password: str) -> LoginResult:
        now = self._clock.now()
        with self._uow_factory() as uow:
            # Window (now - 15 min, now]: a failure at T0 stops counting at exactly T0 + 15 min.
            since = now - FAILURE_WINDOW + timedelta(microseconds=1)
            if uow.login_attempts.count_failures_since(email, since) >= MAX_FAILURES:
                raise TooManyAttempts()

            user = uow.users.get_by_email(email)
            valid = (
                user is not None
                and user.active
                and self._hasher.verify(user.password_hash, password)
            )
            uow.login_attempts.record(email, now, success=valid)
            if not valid:
                uow.commit()
                raise InvalidCredentials()

            token = self._tokens.new_session_token()
            session = Session(
                id=uuid.uuid4(),
                user_id=user.id,
                token_hash=self._tokens.hash_token(token),
                csrf_token=self._tokens.new_csrf_token(),
                created_at=now,
                last_seen_at=now,
            )
            uow.sessions.add(session)
            uow.commit()
        return LoginResult(token=token, session=session, user=user)


class Logout:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], tokens: TokenService):
        self._uow_factory = uow_factory
        self._tokens = tokens

    def execute(self, token: str) -> None:
        with self._uow_factory() as uow:
            session = uow.sessions.get_by_token_hash(self._tokens.hash_token(token))
            if session is not None:
                uow.sessions.delete(session.id)
                uow.commit()


class GetCurrentSession:
    """Validate the session token, enforce idle/absolute expiry and refresh last_seen_at."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], tokens: TokenService, clock: Clock):
        self._uow_factory = uow_factory
        self._tokens = tokens
        self._clock = clock

    def execute(self, token: str) -> tuple[Session, User]:
        now = self._clock.now()
        with self._uow_factory() as uow:
            session = uow.sessions.get_by_token_hash(self._tokens.hash_token(token))
            if session is None:
                raise Unauthenticated()
            expired = (
                now - session.last_seen_at >= IDLE_TIMEOUT
                or now - session.created_at >= ABSOLUTE_TIMEOUT
            )
            user = None if expired else uow.users.get(session.user_id)
            if user is None or not user.active:
                uow.sessions.delete(session.id)
                uow.commit()
                raise Unauthenticated()
            uow.sessions.touch(session.id, now)
            uow.commit()
        session.last_seen_at = now
        return session, user
