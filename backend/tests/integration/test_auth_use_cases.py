"""AUTH-02, AUTH-04, AUTH-05, AUTH-11: authentication use cases with an injected clock."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.application.use_cases.auth import (
    GetCurrentSession,
    InvalidCredentials,
    Login,
    Logout,
    TooManyAttempts,
    Unauthenticated,
)
from app.domain.entities.user import Role, User
from app.infrastructure.security import tokens
from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher

T0 = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
EPS = timedelta(microseconds=1)
EMAIL = "docente@ufpa.br"
PASSWORD = "senha-correta-1"
WRONG = "senha-errada-99"


class FakeClock:
    def __init__(self, now: datetime):
        self.current = now

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def clock():
    return FakeClock(T0)


@pytest.fixture
def auth(uow_factory, clock):
    hasher = Argon2PasswordHasher()
    user = User(
        id=uuid.uuid4(),
        email=EMAIL,
        name="Docente",
        role=Role.DOCENTE,
        password_hash=hasher.hash(PASSWORD),
    )
    with uow_factory() as uow:
        uow.users.add(user)
        uow.commit()
    return {
        "user": user,
        "login": Login(uow_factory, hasher, tokens, clock),
        "logout": Logout(uow_factory, tokens),
        "current": GetCurrentSession(uow_factory, tokens, clock),
    }


def test_login_with_valid_credentials_creates_server_side_session(auth, uow_factory):
    result = auth["login"].execute(EMAIL, PASSWORD)

    assert result.user.id == auth["user"].id
    assert result.user.role is Role.DOCENTE
    with uow_factory() as uow:
        stored = uow.sessions.get_by_token_hash(tokens.hash_token(result.token))
    assert stored == result.session
    assert stored.token_hash != result.token
    assert stored.csrf_token
    session, user = auth["current"].execute(result.token)
    assert (session.id, user.id) == (result.session.id, auth["user"].id)


def test_wrong_password_and_unknown_user_give_the_same_message(auth):
    with pytest.raises(InvalidCredentials) as wrong_password:
        auth["login"].execute(EMAIL, WRONG)
    with pytest.raises(InvalidCredentials) as unknown_user:
        auth["login"].execute("ninguem@ufpa.br", PASSWORD)

    assert str(wrong_password.value) == "Usuário ou senha inválidos"
    assert str(unknown_user.value) == "Usuário ou senha inválidos"


def _fail(auth, times: int) -> None:
    for _ in range(times):
        with pytest.raises(InvalidCredentials):
            auth["login"].execute(EMAIL, WRONG)


def test_fifth_failure_is_still_401_and_sixth_attempt_is_blocked(auth):
    _fail(auth, 5)  # the 5th attempt is answered as invalid credentials, not blocked

    with pytest.raises(TooManyAttempts):
        auth["login"].execute(EMAIL, PASSWORD)


def test_four_failures_do_not_block(auth):
    _fail(auth, 4)

    assert auth["login"].execute(EMAIL, PASSWORD).user.id == auth["user"].id


def test_block_lasts_until_the_end_of_the_15_minute_window(auth, clock):
    _fail(auth, 5)

    clock.current = T0 + timedelta(minutes=15) - EPS
    with pytest.raises(TooManyAttempts):
        auth["login"].execute(EMAIL, PASSWORD)

    clock.current = T0 + timedelta(minutes=15)
    assert auth["login"].execute(EMAIL, PASSWORD).user.id == auth["user"].id


def test_block_applies_only_to_the_same_email(auth):
    _fail(auth, 5)

    with pytest.raises(InvalidCredentials):
        auth["login"].execute("outro@ufpa.br", WRONG)


def test_session_valid_just_before_30_minutes_idle(auth, clock):
    token = auth["login"].execute(EMAIL, PASSWORD).token

    clock.current = T0 + timedelta(minutes=30) - EPS
    session, _ = auth["current"].execute(token)
    assert session.last_seen_at == clock.current


def test_session_expires_after_30_minutes_idle(auth, clock):
    token = auth["login"].execute(EMAIL, PASSWORD).token

    clock.current = T0 + timedelta(minutes=30)
    with pytest.raises(Unauthenticated):
        auth["current"].execute(token)

    clock.current = T0 + timedelta(minutes=31)
    with pytest.raises(Unauthenticated):
        auth["current"].execute(token)


def test_activity_resets_idle_timer(auth, clock):
    token = auth["login"].execute(EMAIL, PASSWORD).token

    clock.current = T0 + timedelta(minutes=20)
    auth["current"].execute(token)
    clock.current = T0 + timedelta(minutes=49)
    session, _ = auth["current"].execute(token)
    assert session.last_seen_at == T0 + timedelta(minutes=49)


def _keep_alive_until(auth, clock, token, end: datetime) -> None:
    moment = T0
    while moment + timedelta(minutes=20) < end:
        moment += timedelta(minutes=20)
        clock.current = moment
        auth["current"].execute(token)


def test_session_valid_just_before_8_hours(auth, clock):
    token = auth["login"].execute(EMAIL, PASSWORD).token
    _keep_alive_until(auth, clock, token, T0 + timedelta(hours=8))

    clock.current = T0 + timedelta(hours=8) - EPS
    session, user = auth["current"].execute(token)
    assert user.id == auth["user"].id


def test_session_expires_at_8_hours_even_when_active(auth, clock):
    token = auth["login"].execute(EMAIL, PASSWORD).token
    _keep_alive_until(auth, clock, token, T0 + timedelta(hours=8))

    clock.current = T0 + timedelta(hours=8)
    with pytest.raises(Unauthenticated):
        auth["current"].execute(token)


def test_logout_invalidates_session_on_server(auth, uow_factory):
    token = auth["login"].execute(EMAIL, PASSWORD).token

    auth["logout"].execute(token)

    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash(tokens.hash_token(token)) is None
    with pytest.raises(Unauthenticated):
        auth["current"].execute(token)


def test_unknown_token_is_unauthenticated(auth):
    with pytest.raises(Unauthenticated):
        auth["current"].execute("token-inexistente")
