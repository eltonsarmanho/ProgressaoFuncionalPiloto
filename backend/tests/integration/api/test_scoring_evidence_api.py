"""VINC-04: the scoring route reports the linked documents of each row."""

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.entities.user import Role
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.api.factories import add_professor, process_payload
from tests.integration.api.test_scoring_process_api import add_activity, choose
from tests.integration.documents.factories import make_document


@pytest.fixture
def admin(act_as, scoring_tables):
    return act_as("admin@ufpa.br", Role.ADMIN)


@pytest.fixture
def process(client, admin, reference, uow_factory):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    response = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_scoring_rows_carry_evidence_count_and_the_counter_follows_the_links(
    client, admin, process, scoring_tables, uow_factory
):
    _, headers = admin
    choose(client, headers, process, scoring_tables["OFICIAL"])
    linked = add_activity(
        uow_factory, process, title="Com vinculo", group_number=2, item_number=7,
        event_date=date(2023, 5, 10), quantity=Decimal(1),
    )  # fmt: skip
    add_activity(
        uow_factory, process, title="Sem nada", group_number=2, item_number=8,
        event_date=date(2023, 6, 10), quantity=Decimal(1),
    )  # fmt: skip
    with uow_factory() as uow:
        admin_id = uow.users.get_by_email("admin@ufpa.br").id
        document = make_document(SimpleNamespace(id=uuid.UUID(process["id"])), admin_id)
        uow.documents.add(document)
        for page in (1, 2):
            uow.evidences.add(
                ActivityEvidence(
                    uuid.uuid4(), linked.id, document.id, page, "trecho", linked.created_by
                )
            )
        uow.commit()

    body = client.get(f"/api/processes/{process['id']}/scoring").json()

    by_title = {row["title"]: row for row in body["rows"]}
    assert by_title["Com vinculo"]["evidence_count"] == 2
    assert by_title["Sem nada"]["evidence_count"] == 0
    assert body["counters"]["with_evidence"] == 1
    assert [a["code"] for a in by_title["Com vinculo"]["alerts"]] == []
    assert [a["code"] for a in by_title["Sem nada"]["alerts"]] == ["SEM_COMPROVANTE"]
