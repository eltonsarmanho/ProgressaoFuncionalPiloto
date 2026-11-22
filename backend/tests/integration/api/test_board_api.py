"""PORT-02, PORT-05, PORT-06, PORT-11, PORT-12, PAR-01, PAR-12, PAR-13, BNAV-02, BNAV-03: the
routes of the board, of the opinion and of the city (synthetic data only)."""

import uuid

import pytest

from app.domain.entities.process import ProcessStatus
from tests.integration.api.board_support import (
    as_user,
    board_url,
    set_status,
    settings_url,
)

MEMBERS = [
    {"name": "Ana Presidente Souza", "role": "PRESIDENTE"},
    {"name": "Bruno Membro Lima", "role": "MEMBRO"},
    {"name": "Carla Suplente Reis", "role": "SUPLENTE"},
]
ORDINANCE = {
    "number": "77/2025",
    "ordinance_date": "2025-03-10",
    "members": MEMBERS,
    "expected_version": 0,
}
OPINION = {
    "conclusion": "FAVORAVEL",
    "opinion_date": "2025-04-01",
    "place": "Belém",
    "notes": "Sem ressalvas.",
    "expected_version": 0,
}


def put_ordinance(client, process, headers, **changes):
    return client.put(
        board_url(process, "/ordinance"), json={**ORDINANCE, **changes}, headers=headers
    )


def put_opinion(client, process, headers, **changes):
    return client.put(board_url(process, "/opinion"), json={**OPINION, **changes}, headers=headers)


def put_city(client, process, headers, city="Belém", version=0, **extra):
    return client.put(
        settings_url(process),
        json={"city": city, "expected_version": version, **extra},
        headers=headers,
    )


def field_of(response) -> str:
    return response.json()["detail"][0]["field"]


# --- GET /board ---------------------------------------------------------------------------------


def test_a_new_process_has_an_empty_board_with_every_version_zero(client, process, headers):
    response = client.get(board_url(process))

    assert response.status_code == 200
    body = response.json()
    ordinance = body["ordinance"]
    assert (ordinance["reading_state"], ordinance["version"]) == ("SEM_ARQUIVO", 0)
    assert (ordinance["number"], ordinance["ordinance_date"], ordinance["members"]) == (
        None,
        None,
        [],
    )
    assert (ordinance["file"], ordinance["reading_code"], ordinance["warnings"]) == (None, None, [])
    assert body["opinion"] == {
        "conclusion": None,
        "opinion_date": None,
        "place": None,
        "notes": None,
        "version": 0,
    }
    assert body["request_settings"] == {"city": None, "version": 0}


def test_a_read_writes_nothing(client, process, headers, uow_factory):
    client.get(board_url(process))
    client.get(board_url(process))

    with uow_factory() as uow:
        pid = uuid.UUID(process["id"])
        assert (uow.board.get(pid), uow.opinions.get(pid), uow.request_settings.get(pid)) == (
            None,
            None,
            None,
        )


# --- PUT /board/ordinance -------------------------------------------------------------------------


def test_the_ordinance_is_saved_with_the_typed_members_as_informed_by_the_person(
    client, process, headers
):
    response = put_ordinance(client, process, headers)

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 1
    assert (body["number"], body["number_source"]) == ("77/2025", "INFORMADO")
    assert (body["ordinance_date"], body["date_source"]) == ("2025-03-10", "INFORMADO")
    assert [(m["name"], m["role"], m["source"], m["page"]) for m in body["members"]] == [
        ("Ana Presidente Souza", "PRESIDENTE", "INFORMADO", None),
        ("Bruno Membro Lima", "MEMBRO", "INFORMADO", None),
        ("Carla Suplente Reis", "SUPLENTE", "INFORMADO", None),
    ]
    assert body["reading_state"] == "SEM_ARQUIVO"
    assert client.get(board_url(process)).json()["ordinance"] == body


def test_a_saved_ordinance_is_edited_with_the_next_version(client, process, headers):
    first = put_ordinance(client, process, headers).json()

    second = put_ordinance(
        client, process, headers, number="78/2025", expected_version=first["version"]
    )

    assert second.status_code == 200
    assert (second.json()["version"], second.json()["number"]) == (2, "78/2025")


def test_the_ordinance_can_be_saved_with_nothing_filled(client, process, headers):
    response = client.put(
        board_url(process, "/ordinance"), json={"expected_version": 0}, headers=headers
    )

    assert response.status_code == 200
    assert (response.json()["number"], response.json()["members"]) == (None, [])


def test_sixteen_members_are_a_422_on_members_and_fifteen_are_saved(client, process, headers):
    many = [{"name": f"Membro {n}", "role": "MEMBRO"} for n in range(16)]

    refused = put_ordinance(client, process, headers, members=many)
    saved = put_ordinance(client, process, headers, members=many[:15])

    assert refused.status_code == 422 and field_of(refused) == "members"
    assert saved.status_code == 200 and len(saved.json()["members"]) == 15


@pytest.mark.parametrize("name", ["", "   ", "n" * 201])
def test_an_empty_or_too_long_member_name_is_a_422_on_that_member(client, process, headers, name):
    members = [MEMBERS[0], {"name": name, "role": "MEMBRO"}]

    response = put_ordinance(client, process, headers, members=members)

    assert response.status_code == 422
    assert field_of(response) == "members[1].name"
    assert client.get(board_url(process)).json()["ordinance"]["version"] == 0


def test_a_number_of_51_characters_is_a_422_on_number_and_50_are_saved(client, process, headers):
    refused = put_ordinance(client, process, headers, number="9" * 51)
    saved = put_ordinance(client, process, headers, number="9" * 50)

    assert refused.status_code == 422 and field_of(refused) == "number"
    assert saved.status_code == 200 and len(saved.json()["number"]) == 50


def test_the_same_member_twice_is_a_422_with_the_code_member_repeated(client, process, headers):
    members = [MEMBERS[0], {"name": "ANA PRESIDENTE SOUZA", "role": "MEMBRO"}]

    response = put_ordinance(client, process, headers, members=members)

    assert response.status_code == 422
    [entry] = response.json()["detail"]
    assert (entry["field"], entry["code"]) == ("members[1].name", "MEMBRO_REPETIDO")


def test_two_saves_from_the_same_version_give_200_and_409_with_the_code(client, process, headers):
    first = put_ordinance(client, process, headers)
    second = put_ordinance(client, process, headers, number="99/2025", expected_version=1)
    stale = put_ordinance(client, process, headers, number="88/2025", expected_version=1)

    assert (first.status_code, second.status_code, stale.status_code) == (200, 200, 409)
    assert stale.json()["code"] == "VERSAO_DESATUALIZADA"
    assert client.get(board_url(process)).json()["ordinance"]["number"] == "99/2025"


def test_a_first_save_that_expects_a_version_above_zero_is_a_409(client, process, headers):
    response = put_ordinance(client, process, headers, expected_version=3)

    assert response.status_code == 409
    assert response.json()["code"] == "VERSAO_DESATUALIZADA"


# --- PUT /board/opinion ---------------------------------------------------------------------------


def test_the_opinion_is_saved_without_a_conclusion_and_the_conclusion_stays_empty(
    client, process, headers
):
    response = put_opinion(client, process, headers, conclusion=None)

    assert response.status_code == 200
    body = response.json()
    assert body["conclusion"] is None
    assert (body["opinion_date"], body["place"], body["notes"], body["version"]) == (
        "2025-04-01",
        "Belém",
        "Sem ressalvas.",
        1,
    )
    assert client.get(board_url(process)).json()["opinion"]["conclusion"] is None


def test_choosing_the_conclusion_and_taking_it_back(client, process, headers):
    chosen = put_opinion(client, process, headers)
    cleared = put_opinion(client, process, headers, conclusion=None, expected_version=1)

    assert chosen.json()["conclusion"] == "FAVORAVEL"
    assert (cleared.json()["conclusion"], cleared.json()["version"]) == (None, 2)


def test_a_conclusion_out_of_the_two_values_is_a_422_on_conclusion(client, process, headers):
    response = put_opinion(client, process, headers, conclusion="TALVEZ")

    assert response.status_code == 422 and field_of(response) == "conclusion"


def test_notes_of_5001_characters_are_a_422_on_notes_and_5000_are_saved(client, process, headers):
    refused = put_opinion(client, process, headers, notes="n" * 5001)
    saved = put_opinion(client, process, headers, notes="n" * 5000)

    assert refused.status_code == 422 and field_of(refused) == "notes"
    assert saved.status_code == 200 and len(saved.json()["notes"]) == 5000


def test_a_place_of_101_characters_is_a_422_on_place(client, process, headers):
    response = put_opinion(client, process, headers, place="p" * 101)

    assert response.status_code == 422 and field_of(response) == "place"


def test_a_stale_opinion_version_is_a_409_with_the_code(client, process, headers):
    put_opinion(client, process, headers)

    response = put_opinion(client, process, headers, conclusion="DESFAVORAVEL")

    assert response.status_code == 409 and response.json()["code"] == "VERSAO_DESATUALIZADA"
    assert client.get(board_url(process)).json()["opinion"]["conclusion"] == "FAVORAVEL"


# --- PUT /request-settings ------------------------------------------------------------------------


def test_the_city_is_saved_up_to_100_characters_and_101_are_a_422_on_city(client, process, headers):
    refused = put_city(client, process, headers, city="c" * 101)
    saved = put_city(client, process, headers, city="c" * 100)

    assert refused.status_code == 422 and field_of(refused) == "city"
    assert saved.status_code == 200
    assert (len(saved.json()["city"]), saved.json()["version"]) == (100, 1)
    assert client.get(board_url(process)).json()["request_settings"]["city"] == "c" * 100


def test_a_stale_city_version_is_a_409_with_the_code(client, process, headers):
    put_city(client, process, headers)

    response = put_city(client, process, headers, city="Santarém", version=0)

    assert response.status_code == 409 and response.json()["code"] == "VERSAO_DESATUALIZADA"


# --- bodies and session ---------------------------------------------------------------------------


def test_an_unknown_field_is_a_422_on_the_three_writes(client, process, headers):
    on_ordinance = put_ordinance(client, process, headers, justificativa="x")
    on_opinion = put_opinion(client, process, headers, sugestao="FAVORAVEL")
    on_city = put_city(client, process, headers, extra="x")

    assert [r.status_code for r in (on_ordinance, on_opinion, on_city)] == [422, 422, 422]
    assert field_of(on_ordinance) == "justificativa"


def test_a_member_with_a_field_other_than_name_and_role_is_a_422(client, process, headers):
    members = [{"name": "Ana", "role": "MEMBRO", "source": "EXTRAIDO"}]

    response = put_ordinance(client, process, headers, members=members)

    assert response.status_code == 422


def test_a_body_without_the_expected_version_is_a_422(client, process, headers):
    response = client.put(board_url(process, "/opinion"), json={"place": "Belém"}, headers=headers)

    assert response.status_code == 422 and field_of(response) == "expected_version"


def test_without_a_session_every_route_is_401(make_client, process):
    anonymous = make_client()

    assert anonymous.get(board_url(process)).status_code == 401
    assert anonymous.put(board_url(process, "/ordinance"), json=ORDINANCE).status_code == 401
    assert anonymous.put(board_url(process, "/opinion"), json=OPINION).status_code == 401
    assert anonymous.put(settings_url(process), json={"expected_version": 0}).status_code == 401


# --- BNAV-02 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_three_writes_with_409_and_still_reads(
    client, process, headers, uow_factory, status
):
    saved = put_ordinance(client, process, headers).json()
    set_status(uow_factory, process, status)

    responses = [
        put_ordinance(client, process, headers, number="1/2025", expected_version=saved["version"]),
        put_opinion(client, process, headers),
        put_city(client, process, headers),
    ]

    for response in responses:
        assert response.status_code == 409
        assert response.json()["code"] == "PROCESSO_SOMENTE_LEITURA"
    read = client.get(board_url(process))
    assert read.status_code == 200
    body = read.json()
    assert body["ordinance"]["number"] == "77/2025"
    assert (body["opinion"]["version"], body["request_settings"]["version"]) == (0, 0)


# --- BNAV-03 --------------------------------------------------------------------------------------


def test_without_access_to_the_process_the_four_routes_are_404(client, process, actors):
    for outsider in (actors.other_docente, actors.other_secretaria):
        outsider_headers = as_user(client, outsider)

        assert client.get(board_url(process)).status_code == 404
        assert put_ordinance(client, process, outsider_headers).status_code == 404
        assert put_opinion(client, process, outsider_headers).status_code == 404
        assert put_city(client, process, outsider_headers).status_code == 404

    as_user(client, actors.owner)
    body = client.get(board_url(process)).json()
    assert (body["ordinance"]["version"], body["opinion"]["version"]) == (0, 0)
    assert body["request_settings"]["version"] == 0


@pytest.mark.parametrize("who", ["owner", "secretaria"])
def test_the_owner_and_the_secretary_of_the_unit_read_and_save(client, process, actors, who):
    user_headers = as_user(client, getattr(actors, who))

    assert client.get(board_url(process)).status_code == 200
    assert put_ordinance(client, process, user_headers).status_code == 200
    assert put_opinion(client, process, user_headers).status_code == 200
    assert put_city(client, process, user_headers).status_code == 200


def test_the_admin_reads_and_saves(client, process, headers):
    assert client.get(board_url(process)).status_code == 200
    assert put_ordinance(client, process, headers).status_code == 200
