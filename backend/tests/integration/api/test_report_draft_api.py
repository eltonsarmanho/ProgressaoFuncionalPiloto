"""REL-03, REL-07, REL-08, REL-13, UIG-02, UIG-08 (T84): the report draft and wording routes."""

import logging
import uuid

from app.domain.entities.user import Role
from tests.integration.api.conftest import login
from tests.integration.api.generated_support import process_url
from tests.support.process_status import conclude_for_test

TEACHING_SECTION = "1.3"  # where the template puts group II
OTHER_SECTION = "6"


def draft_url(process, tail: str = "") -> str:
    return process_url(process, "report-draft" + tail)


def entry_url(scenario, tail: str = "") -> str:
    return draft_url(scenario.process, f"/entries/{scenario.activity['id']}{tail}")


def section_of(body: dict, key: str) -> dict:
    return next(s for s in body["sections"] if s["key"] == key)


def test_reading_proposes_the_draft_and_never_saves_it(client, scenario):
    first = client.get(draft_url(scenario.process))
    second = client.get(draft_url(scenario.process))

    assert first.status_code == 200
    body = first.json()
    assert (body["saved"], body["version"]) == (False, 0)
    [entry] = section_of(body, TEACHING_SECTION)["entries"]
    assert entry["activity_id"] == scenario.activity["id"]
    assert (entry["source"], entry["text"] != "") == ("MODELO", True)
    assert [a["id"] for a in body["activities"]] == [scenario.activity["id"]]
    assert "1.1" in body["empty_sections"] and TEACHING_SECTION not in body["empty_sections"]
    assert second.json()["version"] == 0 and second.json()["saved"] is False


def test_the_first_save_creates_version_1_and_marks_the_entry_as_the_users(client, scenario):
    response = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "Orientei o trabalho de conclusão."},
        headers=scenario.headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    [entry] = section_of(body, TEACHING_SECTION)["entries"]
    assert (entry["text"], entry["source"]) == ("Orientei o trabalho de conclusão.", "USUARIO")
    read = client.get(draft_url(scenario.process)).json()
    assert (read["saved"], read["version"]) == (True, 1)


def test_the_free_text_of_a_section_is_saved_with_the_next_version(client, scenario):
    client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "Texto."},
        headers=scenario.headers,
    )

    response = client.put(
        draft_url(scenario.process, f"/sections/{TEACHING_SECTION}"),
        json={"expected_version": 1, "free_text": "Observação da seção."},
        headers=scenario.headers,
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert section_of(response.json(), TEACHING_SECTION)["free_text"] == "Observação da seção."


def test_a_stale_version_is_409_with_the_code_and_the_newer_text_stays(client, scenario):
    client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "Primeiro."},
        headers=scenario.headers,
    )

    stale = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "Atrasado."},
        headers=scenario.headers,
    )

    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSAO_DESATUALIZADA"
    [entry] = section_of(client.get(draft_url(scenario.process)).json(), TEACHING_SECTION)[
        "entries"
    ]
    assert entry["text"] == "Primeiro."


def test_more_than_20000_characters_is_422_and_exactly_20000_is_saved(client, scenario):
    too_long = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "a" * 20_001},
        headers=scenario.headers,
    )
    exact = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "a" * 20_000},
        headers=scenario.headers,
    )

    assert too_long.status_code == 422
    assert too_long.json()["detail"][0]["field"] == "text"
    assert exact.status_code == 200


def test_an_unknown_activity_and_an_unknown_field_are_refused(client, scenario):
    unknown = client.put(
        draft_url(scenario.process, f"/entries/{uuid.uuid4()}"),
        json={"expected_version": 0, "text": "x"},
        headers=scenario.headers,
    )
    extra = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "x", "source": "IA"},
        headers=scenario.headers,
    )

    assert unknown.status_code == 404
    assert extra.status_code == 422


def test_moving_an_activity_puts_it_at_the_end_of_the_other_section(client, scenario):
    moved = client.post(
        entry_url(scenario, "/move"),
        json={"expected_version": 0, "section_key": OTHER_SECTION},
        headers=scenario.headers,
    )
    unknown = client.post(
        entry_url(scenario, "/move"),
        json={"expected_version": 1, "section_key": "9.9"},
        headers=scenario.headers,
    )

    assert moved.status_code == 200
    body = moved.json()
    assert [e["activity_id"] for e in section_of(body, OTHER_SECTION)["entries"]] == [
        scenario.activity["id"]
    ]
    assert section_of(body, TEACHING_SECTION)["entries"] == []
    assert unknown.status_code == 422


def test_asking_for_a_wording_answers_202_at_once_and_a_second_ask_is_409(client, scenario):
    url = draft_url(scenario.process, f"/sections/{TEACHING_SECTION}/wording")

    first = client.post(url, headers=scenario.headers)
    second = client.post(url, headers=scenario.headers)

    assert first.status_code == 202
    body = first.json()
    assert (body["section_key"], body["state"], body["finished_at"]) == (
        TEACHING_SECTION,
        "GERANDO",
        None,
    )
    assert second.status_code == 409
    assert second.json()["code"] == "REDACAO_EM_ANDAMENTO"
    saved = client.get(draft_url(scenario.process)).json()
    assert (saved["saved"], saved["version"]) == (True, 1)  # the proposal was saved first


def test_the_wording_query_gives_the_state_of_each_section_until_the_executor_closes_it(
    client, scenario
):
    wording = draft_url(scenario.process, "/wording")
    assert client.get(wording).json() == []
    client.post(
        draft_url(scenario.process, f"/sections/{TEACHING_SECTION}/wording"),
        headers=scenario.headers,
    )

    [waiting] = client.get(wording).json()
    assert (waiting["section_key"], waiting["state"]) == (TEACHING_SECTION, "GERANDO")

    assert client.app.state.container.run_wording.run_next() is True

    [closed] = client.get(wording).json()
    assert (closed["section_key"], closed["state"]) == (TEACHING_SECTION, "PRONTO")
    assert [w["code"] for w in closed["warnings"]] == ["REDACAO_INDISPONIVEL"]  # no AI key here
    [entry] = section_of(client.get(draft_url(scenario.process)).json(), TEACHING_SECTION)[
        "entries"
    ]
    assert entry["source"] == "MODELO"


def test_a_section_the_template_does_not_have_is_404(client, scenario):
    response = client.post(
        draft_url(scenario.process, "/sections/9.9/wording"), headers=scenario.headers
    )

    assert response.status_code == 404


def test_a_concluded_process_is_read_only_for_the_draft_but_still_readable(
    client, scenario, uow_factory
):
    conclude_for_test(uow_factory, scenario.process["id"])

    save = client.put(
        entry_url(scenario),
        json={"expected_version": 0, "text": "x"},
        headers=scenario.headers,
    )
    wording = client.post(
        draft_url(scenario.process, f"/sections/{TEACHING_SECTION}/wording"),
        headers=scenario.headers,
    )

    assert (save.status_code, save.json()["code"]) == (409, "PROCESSO_SOMENTE_LEITURA")
    assert (wording.status_code, wording.json()["code"]) == (409, "PROCESSO_SOMENTE_LEITURA")
    assert client.get(draft_url(scenario.process)).status_code == 200


def test_without_access_to_the_process_every_route_is_404(client, scenario, act_as, reference):
    _, outsider = act_as(
        "fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )
    body = {"expected_version": 0}

    assert client.get(draft_url(scenario.process)).status_code == 404
    assert client.get(draft_url(scenario.process, "/wording")).status_code == 404
    assert (
        client.put(entry_url(scenario), json={**body, "text": "x"}, headers=outsider).status_code
        == 404
    )
    assert (
        client.put(
            draft_url(scenario.process, f"/sections/{TEACHING_SECTION}"),
            json={**body, "free_text": "x"},
            headers=outsider,
        ).status_code
        == 404
    )
    assert (
        client.post(
            entry_url(scenario, "/move"),
            json={**body, "section_key": OTHER_SECTION},
            headers=outsider,
        ).status_code
        == 404
    )
    assert (
        client.post(
            draft_url(scenario.process, f"/sections/{TEACHING_SECTION}/wording"),
            headers=outsider,
        ).status_code
        == 404
    )


def test_the_ai_key_never_reaches_a_response_or_a_log(make_client, scenario, caplog):
    secret = "chave-secreta-da-maritalk-0451"
    keyed = make_client(maritalk_api_key=secret)
    headers = {"X-CSRF-Token": login(keyed, "admin@ufpa.br")}
    caplog.set_level(logging.DEBUG)

    responses = [
        keyed.get(draft_url(scenario.process)),
        keyed.post(
            draft_url(scenario.process, f"/sections/{TEACHING_SECTION}/wording"), headers=headers
        ),
    ]
    assert keyed.app.state.container.run_wording.run_next() is True
    responses.append(keyed.get(draft_url(scenario.process, "/wording")))

    assert [r.status_code for r in responses] == [200, 202, 200]
    assert all(secret not in r.text for r in responses)
    assert secret not in caplog.text
    assert secret not in repr(keyed.app.state.container.settings)
