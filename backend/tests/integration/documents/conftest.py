"""Fixtures for document schema and repository tests: units, admin, a professor and processes."""

import dataclasses
import uuid

import pytest

from app.domain.entities.process import FunctionalProcess
from app.infrastructure.database.session import make_session_factory
from tests.integration.test_scoring_repositories import add_process, base  # noqa: F401


@pytest.fixture
def process(uow_factory, base) -> FunctionalProcess:  # noqa: F811
    return add_process(uow_factory, base)


@pytest.fixture
def other_process(uow_factory, process) -> FunctionalProcess:
    """A second process of the same professor."""
    other = dataclasses.replace(process, id=uuid.uuid4())
    with uow_factory() as uow:
        uow.processes.add(other)
        uow.commit()
    return other


@pytest.fixture
def session_factory(engine):
    """Sessions bound to the test database, for the repositories that take a session."""
    return make_session_factory(engine)
