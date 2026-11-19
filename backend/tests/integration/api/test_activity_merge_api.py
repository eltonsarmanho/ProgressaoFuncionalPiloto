"""DUP-04, DUP-07: the merge-duplicates and separate routes."""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource
from app.domain.entities.user import Role
from tests.integration.api.test_documents_api import close_process


@pytest.fixture
def chosen(client, headers, process, scoring_tables):
    body = {"version_id": str(scoring_tables["OFICIAL"].id)}
    response = client.put(
        f"/api/processes/{process['id']}/scoring/table", json=body, headers=headers
    )
    assert response.status_code == 200, response.text
    return process


def draft(client, admin, process, title="Visão Computacional com OpenCV", day=date(2023, 5, 10)):
    """A suggested draft of item III.4; two with the same title and date are duplicates."""
    user, _ = admin
    return client.app.state.container.create_activity.execute(
        user,
        uuid.UUID(process["id"]),
        ActivityData(
            title=title, group_number=3, item_number=4, event_date=day, quantity=Decimal(1)
        ),
        source=ActivitySource.SUGERIDA_IA,
    )


def merge_url(process):
    return f"/api/processes/{process['id']}/activities/merge-duplicates"


def listed(client, process):
    response = client.get(f"/api/processes/{process['id']}/activities")
    assert response.status_code == 200, response.text
    return response.json()


def test_merge_duplicates_merges_and_answers_how_many(client, admin, headers, chosen):
    first, second = draft(client, admin, chosen), draft(client, admin, chosen)
    other = draft(client, admin, chosen, title="Outra atividade bem diferente")

    response = client.post(merge_url(chosen), headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"merged": 1}
    assert {a["id"] for a in listed(client, chosen)} == {str(first.id), str(other.id)}
    assert client.get(f"/api/activities/{second.id}").status_code == 200  # the row stays


def test_a_second_call_merges_nothing(client, admin, headers, chosen):
    draft(client, admin, chosen)
    draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)
    before = listed(client, chosen)

    response = client.post(merge_url(chosen), headers=headers)

    assert response.status_code == 200
    assert response.json() == {"merged": 0}
    assert listed(client, chosen) == before


def test_the_scoring_has_no_row_for_the_merged_activity(client, admin, headers, chosen):
    kept, merged = draft(client, admin, chosen), draft(client, admin, chosen)
    for activity in (kept, merged):
        client.post(
            f"/api/activities/{activity.id}/status",
            json={"status": "VALIDADA", "expected_version": 1},
            headers=headers,
        )

    client.post(merge_url(chosen), headers=headers)

    body = client.get(f"/api/processes/{chosen['id']}/scoring").json()
    assert {row["activity_id"] for row in body["rows"]} == {str(kept.id)}
    assert body["counters"]["activities"] == 1
    assert body["total"] != "0.00"


@pytest.mark.parametrize("final", ["CONCLUIDO", "ARQUIVADO"])
def test_a_read_only_process_answers_zero_and_changes_nothing(
    client, admin, headers, chosen, uow_factory, final
):
    draft(client, admin, chosen)
    draft(client, admin, chosen)
    before = listed(client, chosen)
    close_process(client, headers, chosen, uow_factory, final=final)

    response = client.post(merge_url(chosen), headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"merged": 0}
    assert listed(client, chosen) == before


def test_a_process_outside_the_access_is_404(client, act_as, reference, admin, chosen):
    draft(client, admin, chosen)
    draft(client, admin, chosen)
    _, other = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.post(merge_url(chosen), headers=other).status_code == 404
    assert (
        client.post(f"/api/processes/{uuid.uuid4()}/activities/merge-duplicates", headers=other)
        .status_code
        == 404
    )


def test_merge_duplicates_without_csrf_is_403_and_without_session_is_401(
    client, admin, headers, chosen
):
    draft(client, admin, chosen)
    draft(client, admin, chosen)

    assert client.post(merge_url(chosen)).status_code == 403
    assert len(listed(client, chosen)) == 2
    client.post("/api/auth/logout", headers=headers)
    assert client.post(merge_url(chosen)).status_code == 401


# --- separate ------------------------------------------------------------------------------


def separate_url(activity):
    return f"/api/activities/{activity.id}/separate"


def test_separate_restores_the_activity_and_returns_it(client, admin, headers, chosen):
    kept, merged = draft(client, admin, chosen), draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)
    assert {a["id"] for a in listed(client, chosen)} == {str(kept.id)}

    response = client.post(separate_url(merged), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(merged.id)
    assert body["title"] == merged.title
    assert body["distinct_justification"]
    assert {a["id"] for a in listed(client, chosen)} == {str(kept.id), str(merged.id)}
    assert client.post(merge_url(chosen), headers=headers).json() == {"merged": 0}


def test_separate_on_an_activity_that_is_not_merged_is_422(client, admin, headers, chosen):
    kept, _ = draft(client, admin, chosen), draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)

    response = client.post(separate_url(kept), headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "atividade"
    assert [a["id"] for a in listed(client, chosen)] == [str(kept.id)]


def test_separate_with_a_stale_version_is_409(client, admin, headers, chosen):
    draft(client, admin, chosen)
    merged = draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)
    version = client.get(f"/api/activities/{merged.id}").json()["version"]

    stale = client.post(
        separate_url(merged), json={"expected_version": version - 1}, headers=headers
    )
    current = client.post(
        separate_url(merged), json={"expected_version": version}, headers=headers
    )

    assert stale.status_code == 409
    assert current.status_code == 200


def test_separate_outside_the_access_is_404_and_unknown_is_404(
    client, act_as, reference, admin, chosen
):
    draft(client, admin, chosen)
    merged = draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=admin[1])
    _, other = act_as(
        "sec.ifch@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.post(separate_url(merged), headers=other).status_code == 404
    unknown = f"/api/activities/{uuid.uuid4()}/separate"
    assert client.post(unknown, headers=other).status_code == 404


def test_separate_without_csrf_is_403(client, admin, headers, chosen):
    draft(client, admin, chosen)
    merged = draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)

    assert client.post(separate_url(merged)).status_code == 403
    assert len(listed(client, chosen)) == 1


def test_separate_in_a_read_only_process_is_409(client, admin, headers, chosen, uow_factory):
    draft(client, admin, chosen)
    merged = draft(client, admin, chosen)
    client.post(merge_url(chosen), headers=headers)
    close_process(client, headers, chosen, uow_factory, final="ARQUIVADO")

    assert client.post(separate_url(merged), headers=headers).status_code == 409
