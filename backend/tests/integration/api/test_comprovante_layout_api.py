"""ARR-01, ARR-02, ARR-06, ARR-07, UIG-03 (T85): the Comprovante arrangement routes."""

import uuid

import pytest

from app.domain.entities.document import DocumentStatus
from app.domain.entities.user import Role
from tests.integration.api.factories import process_payload
from tests.integration.api.generated_support import (
    add_activity,
    add_document_row,
    link_page,
    process_url,
)
from tests.support.process_status import conclude_for_test


def layout_url(process) -> str:
    return process_url(process, "comprovante-layout")


@pytest.fixture
def linked(scenario, uow_factory):
    """The activity of the scenario linked to pages 1 and 2 of one document, and to page 1 of
    another one; `scenario.first` and `scenario.second` are the documents."""
    first = add_document_row(uow_factory, scenario.process, scenario.user, pages=3)
    second = add_document_row(uow_factory, scenario.process, scenario.user, pages=2)
    for document, page in ((first, 1), (first, 2), (second, 1)):
        link_page(uow_factory, scenario.user, scenario.activity, document, page)
    scenario.first, scenario.second = first, second
    return scenario


def page_body(document, page, justification=None):
    body = {"document_id": str(document.id), "page": page}
    if justification:
        body["repeat_justification"] = justification
    return body


def save_body(scenario, pages, expected_version=0, **extra):
    return {
        "expected_version": expected_version,
        "activities": [{"activity_id": scenario.activity["id"], "pages": pages, **extra}],
    }


def source_pages(body):
    [entry] = body["layout"]["activities"]
    return [(p["document_id"], p["page"]) for p in entry["pages"]]


def test_reading_without_a_saved_arrangement_gives_the_derived_one_with_version_0_and_the_plan(
    client, linked
):
    first, second = linked.first, linked.second

    response = client.get(layout_url(linked.process))

    assert response.status_code == 200
    body = response.json()
    assert (body["saved"], body["layout"]["version"], body["stale"]) == (False, 0, False)
    assert source_pages(body) == [
        (str(first.id), 1),
        (str(first.id), 2),
        (str(second.id), 1),
    ]
    assert body["invalid"] == []
    pages = body["plan"]["pages"]
    assert [p["number"] for p in pages] == list(range(1, len(pages) + 1))
    assert [p["kind"] for p in pages[:2]] == ["CAPA", "SUMARIO"]
    originals = [p for p in pages if p["kind"] == "ORIGINAL"]
    assert [(p["document_id"], p["source_page"]) for p in originals] == [
        (str(first.id), 1),
        (str(first.id), 2),
        (str(second.id), 1),
    ]
    assert client.get(layout_url(linked.process)).json()["saved"] is False  # a read never saves


def test_the_first_save_keeps_the_order_the_user_sent_and_the_numbering_follows_it(client, linked):
    first, second = linked.first, linked.second
    pages = [page_body(second, 1), page_body(first, 2)]  # reordered, and page 1 of `first` left out

    response = client.put(
        layout_url(linked.process), json=save_body(linked, pages), headers=linked.headers
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["saved"], body["layout"]["version"]) == (True, 1)
    assert source_pages(body) == [(str(second.id), 1), (str(first.id), 2)]
    originals = [p for p in body["plan"]["pages"] if p["kind"] == "ORIGINAL"]
    assert [(p["document_id"], p["source_page"]) for p in originals] == source_pages(body)
    assert client.get(layout_url(linked.process)).json()["layout"]["version"] == 1
    # taking a page out of the arrangement does not take the link out of the activity
    activity = client.get(f"/api/activities/{linked.activity['id']}").json()
    assert len(activity["evidences"]) == 3


def test_a_repeated_page_keeps_its_justification(client, linked):
    first = linked.first
    pages = [page_body(first, 1), page_body(first, 1, "Comprova duas atividades")]

    response = client.put(
        layout_url(linked.process), json=save_body(linked, pages), headers=linked.headers
    )

    assert response.status_code == 200
    [entry] = response.json()["layout"]["activities"]
    assert [p["repeat_justification"] for p in entry["pages"]] == [None, "Comprova duas atividades"]


def test_a_stale_version_is_409_with_the_code_and_the_newer_arrangement_stays(client, linked):
    first, second = linked.first, linked.second
    client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(first, 1)]),
        headers=linked.headers,
    )

    stale = client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(second, 1)], expected_version=0),
        headers=linked.headers,
    )

    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSAO_DESATUALIZADA"
    kept = client.get(layout_url(linked.process)).json()
    assert source_pages(kept) == [(str(first.id), 1)]


def test_a_page_past_the_end_of_the_document_is_422_with_the_code(client, linked):
    response = client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(linked.second, 3)]),  # the document has 2 pages
        headers=linked.headers,
    )

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "PAGINA_FORA_DO_DOCUMENTO")


def test_page_zero_an_unknown_field_and_a_move_to_another_item_are_422(client, linked):
    page_zero = client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(linked.first, 0)]),
        headers=linked.headers,
    )
    extra = client.put(
        layout_url(linked.process),
        json={**save_body(linked, []), "force": True},
        headers=linked.headers,
    )
    moved = client.put(
        layout_url(linked.process),
        json=save_body(linked, [], group_number=3, item_number=2),
        headers=linked.headers,
    )

    assert page_zero.status_code == 422
    assert extra.status_code == 422
    assert moved.status_code == 422


def test_a_document_of_another_process_is_404(client, linked, professor, admin):
    other = client.post(
        "/api/processes", json=process_payload(professor), headers=linked.headers
    ).json()
    foreign = add_document_row(client.app.state.container.uow_factory, other, linked.user)

    response = client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(foreign, 1)]),
        headers=linked.headers,
    )

    assert response.status_code == 404
    assert client.get(layout_url(linked.process)).json()["saved"] is False


def test_a_new_activity_after_the_save_makes_the_arrangement_stale_with_the_alert(client, linked):
    client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(linked.first, 1)]),
        headers=linked.headers,
    )
    newer = add_activity(client, linked.headers, linked.process, title="Outra atividade")

    body = client.get(layout_url(linked.process)).json()

    assert body["stale"] is True
    assert body["staleness"]["joined_activity_ids"] == [newer["id"]]
    assert [a["code"] for a in body["alerts"]] == ["ARRANJO_DESATUALIZADO"]


def test_a_document_flagged_outside_the_interstice_is_not_in_the_arrangement(
    client, linked, uow_factory
):
    outside = add_document_row(
        uow_factory,
        linked.process,
        linked.user,
        status=DocumentStatus.PROCESSADO,
        status_code="DOCUMENTO_FORA_DO_INTERSTICIO",
    )
    link_page(uow_factory, linked.user, linked.activity, outside, 1)

    read = client.get(layout_url(linked.process)).json()
    saved = client.put(
        layout_url(linked.process),
        json=save_body(linked, [page_body(outside, 1)]),
        headers=linked.headers,
    )

    assert str(outside.id) not in [doc for doc, _ in source_pages(read)]
    assert str(outside.id) not in str(read["plan"])
    assert saved.status_code == 404


def test_a_concluded_process_is_read_only_for_the_arrangement_but_still_readable(
    client, linked, uow_factory
):
    conclude_for_test(uow_factory, linked.process["id"])

    save = client.put(
        layout_url(linked.process), json=save_body(linked, []), headers=linked.headers
    )

    assert (save.status_code, save.json()["code"]) == (409, "PROCESSO_SOMENTE_LEITURA")
    assert client.get(layout_url(linked.process)).status_code == 200


def test_without_access_to_the_process_both_routes_are_404(client, linked, act_as, reference):
    _, outsider = act_as(
        "fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.get(layout_url(linked.process)).status_code == 404
    denied = client.put(layout_url(linked.process), json=save_body(linked, []), headers=outsider)
    assert denied.status_code == 404
    assert client.get(process_url({"id": uuid.uuid4()}, "comprovante-layout")).status_code == 404
