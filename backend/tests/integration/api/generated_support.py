"""Helpers of the generated-document API tests: a process with the table chosen and a validated
activity, the executor run by hand, and the URLs."""

import hashlib
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.domain.entities.generated import ARTIFACT_KINDS
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.documents.factories import make_document
from tests.integration.documents.generated_support import T0, make_file, make_generation


def process_url(process, tail: str) -> str:
    return f"/api/processes/{process['id']}/{tail}"


def generations_url(process) -> str:
    return process_url(process, "generated-documents")


def choose_table(client, headers, process, version) -> None:
    response = client.put(
        process_url(process, "scoring/table"),
        json={"version_id": str(version.id)},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def add_activity(client, headers, process, **fields) -> dict:
    """A manual activity, which is validated at once; group II item 7 inside the interstice."""
    body = {
        "title": "Orientação de trabalho de conclusão",
        "group_number": 2,
        "item_number": 7,
        "quantidade": 1,
        "event_date": "2023-05-10",
        "evidence_note": "Declaração",
        **fields,
    }
    response = client.post(process_url(process, "activities"), json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def ask(client, headers, process, kind: str = "TABELA"):
    return client.post(generations_url(process), json={"kind": kind}, headers=headers)


def run_executor(client) -> bool:
    """What the executor does for a waiting row, in the test thread."""
    return client.app.state.container.run_generation.run_next()


def generate(client, headers, process, kind: str = "TABELA") -> dict:
    """Asks, runs the executor and returns the row as PRONTO."""
    response = ask(client, headers, process, kind)
    assert response.status_code == 202, response.text
    assert run_executor(client) is True
    row = client.get(f"/api/generated-documents/{response.json()['id']}")
    assert row.status_code == 200, row.text
    assert row.json()["state"] == "PRONTO", row.json()
    return row.json()


def file_url(row: dict, extension: str) -> str:
    return f"/api/generated-documents/{row['id']}/files/{extension}"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def add_document_row(uow_factory, process, user, pages: int = 3, **fields):
    """A document of the process, with `pages` pages and no file, inserted straight."""
    document = make_document(
        SimpleNamespace(id=uuid.UUID(process["id"])), user.id, page_count=pages, **fields
    )
    with uow_factory() as uow:
        uow.documents.add(document)
        uow.commit()
    return document


def link_page(uow_factory, user, activity, document, page: int) -> None:
    with uow_factory() as uow:
        uow.evidences.add(
            ActivityEvidence(
                id=uuid.uuid4(),
                activity_id=uuid.UUID(activity["id"]),
                document_id=document.id,
                page_number=page,
                excerpt="trecho",
                created_by=user.id,
            )
        )
        uow.commit()


def add_ready(uow_factory, process, user, kind) -> None:
    """A PRONTO version of `kind` stored straight in the database (no file on the disk)."""
    row = make_generation(SimpleNamespace(id=uuid.UUID(process["id"])), user.id, kind)
    with uow_factory() as uow:
        uow.generations.add(row)
        uow.generations.finish_ready(row.id, T0, [make_file()], {"total": "1.00"}, ())
        uow.commit()


def add_all_ready(uow_factory, process, user) -> None:
    for kind in ARTIFACT_KINDS:
        add_ready(uow_factory, process, user, kind)


def link_deleted_original(uow_factory, process, user, activity) -> None:
    """A document of the process whose file the conclusion removed, linked to the activity."""
    document = make_document(SimpleNamespace(id=uuid.UUID(process["id"])), user.id)
    with uow_factory() as uow:
        uow.documents.add(document)
        uow.documents.mark_file_deleted(document.id, datetime(2026, 11, 17, 9, 0, tzinfo=UTC))
        uow.evidences.add(
            ActivityEvidence(
                id=uuid.uuid4(),
                activity_id=uuid.UUID(activity["id"]),
                document_id=document.id,
                page_number=1,
                excerpt="",
                created_by=user.id,
            )
        )
        uow.commit()


@pytest.fixture
def scenario(client, admin, process, scoring_tables):
    """The FASI process of the API tests with the official table chosen and one validated
    activity: `scenario.process`, `.headers`, `.user`, `.activity`."""
    choose_table(client, admin[1], process, scoring_tables["OFICIAL"])
    activity = add_activity(client, admin[1], process)
    return SimpleNamespace(process=process, headers=admin[1], user=admin[0], activity=activity)
