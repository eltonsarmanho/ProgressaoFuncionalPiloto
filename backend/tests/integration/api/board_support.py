"""Helpers of the board and dossier API tests: the URLs, the login of another user and the state
changes the API does not offer. Synthetic data only (the `actors` fixture is in conftest)."""

import dataclasses
import uuid

from app.domain.entities.process import ProcessStatus
from tests.integration.api.conftest import login


def board_url(process, tail: str = "") -> str:
    return f"/api/processes/{process['id']}/board{tail}"


def settings_url(process) -> str:
    return f"/api/processes/{process['id']}/request-settings"


def set_status(uow_factory, process, status: ProcessStatus) -> None:
    """Moves the process to `status` straight in the database (no audit)."""
    with uow_factory() as uow:
        current = uow.processes.get(uuid.UUID(process["id"]))
        uow.processes.update(dataclasses.replace(current, status=status), current.version)
        uow.commit()


def as_user(client, user) -> dict[str, str]:
    """Logs `user` in on the client and returns the CSRF headers."""
    return {"X-CSRF-Token": login(client, user.email)}
