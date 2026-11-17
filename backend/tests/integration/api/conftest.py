"""API fixtures: app factory bound to the test database, users and logged-in clients."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.entities.user import Role, User
from app.infrastructure.security.argon2_hasher import Argon2PasswordHasher
from app.main import create_app

PASSWORD = "senha-correta-1"


class FakeClock:
    def __init__(self, now: datetime):
        self.current = now

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def clock():
    return FakeClock(datetime(2026, 11, 16, 9, 0, tzinfo=UTC))


@pytest.fixture
def make_client(migrated_url, engine, clock):
    """Factory for TestClients; https base URL so Secure cookies are sent back."""
    clients = []

    def make(cookie_secure: bool = True) -> TestClient:
        settings = Settings(
            database_url=migrated_url,
            admin_email="admin@ufpa.br",
            admin_password="admin-password-1",
            cookie_secure=cookie_secure,
        )
        scheme = "https" if cookie_secure else "http"
        client = TestClient(create_app(settings, clock), base_url=f"{scheme}://testserver")
        client.__enter__()
        clients.append(client)
        return client

    yield make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def make_user(uow_factory):
    hasher = Argon2PasswordHasher()

    def make(email: str = "docente@ufpa.br", role: Role = Role.DOCENTE, **kw) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=kw.pop("name", "Docente"),
            role=role,
            password_hash=hasher.hash(kw.pop("password", PASSWORD)),
            **kw,
        )
        with uow_factory() as uow:
            uow.users.add(user)
            uow.commit()
        return user

    return make


def login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    """Log in and return the CSRF token from /api/auth/me."""
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    me = client.get("/api/auth/me")
    assert me.status_code == 200, me.text
    return me.json()["csrf_token"]


@pytest.fixture
def act_as(client, make_user):
    """Create a user with the given role, log the client in as them; return (user, headers)."""

    def act(email: str, role: Role = Role.DOCENTE, **kw) -> tuple[User, dict[str, str]]:
        user = make_user(email, role=role, **kw)
        return user, {"X-CSRF-Token": login(client, email)}

    return act


@pytest.fixture
def reference(uow_factory):
    """Seeded career versions and units (UNIT-03); returns units by acronym."""
    from app.infrastructure.database.seed import seed_reference_data

    seed_reference_data(
        uow_factory(), "seed-admin@ufpa.br", "seed-password-1", Argon2PasswordHasher()
    )
    with uow_factory() as uow:
        return {u.acronym: u for u in uow.units.list()}
