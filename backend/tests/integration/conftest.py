"""Integration fixtures on a real PostgreSQL (AD-004).

Uses TEST_DATABASE_URL when set; otherwise starts a throwaway postgres:16-alpine
container on a free host port and removes it at session end.
"""

import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

BACKEND_DIR = Path(__file__).resolve().parents[2]
IMAGE = "postgres:16-alpine"


def pytest_collection_modifyitems(config, items):
    for item in items:
        if Path(str(item.fspath)).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.integration)


def _wait_ready(url: str, timeout: float = 60.0) -> None:
    dsn = url.replace("postgresql+psycopg://", "postgresql://")
    deadline = time.monotonic() + timeout
    while True:
        try:
            with psycopg.connect(dsn, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.5)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        _wait_ready(url)
        yield url
        return
    container = subprocess.run(
        [
            "docker", "run", "-d", "--rm",
            "-e", "POSTGRES_USER=test",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=test",
            "-p", "127.0.0.1::5432",
            IMAGE,
        ],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    try:
        port = subprocess.run(
            ["docker", "port", container, "5432/tcp"],
            check=True, capture_output=True, text=True,
        ).stdout.split()[0].rsplit(":", 1)[1]
        url = f"postgresql+psycopg://test:test@127.0.0.1:{port}/test"
        _wait_ready(url)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True)


def alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def migrated_url(database_url: str) -> str:
    command.upgrade(alembic_config(database_url), "head")
    return database_url


@pytest.fixture(scope="session")
def engine(migrated_url: str) -> Iterator[Engine]:
    eng = create_engine(migrated_url)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(request) -> Iterator[None]:
    """Truncate every application table after each test that used the database."""
    yield
    if "engine" not in request.fixturenames:
        return
    eng: Engine = request.getfixturevalue("engine")
    with eng.begin() as conn:
        tables = conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename <> 'alembic_version'"
            )
        ).scalars().all()
        if tables:
            conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def uow_factory(engine: Engine):
    """Builds a fresh SqlUnitOfWork per call, bound to the test database."""
    from app.infrastructure.database.repositories import SqlUnitOfWork
    from app.infrastructure.database.session import make_session_factory

    factory = make_session_factory(engine)
    return lambda: SqlUnitOfWork(factory)
