"""CARR-08: ADMIN registers career versions with mandatory norm reference; used ones are frozen."""

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.user import Role
from tests.integration.api.factories import REQUERIMENTO_2024_2026, add_professor, process_payload

URL = "/api/career-structures/MAGISTERIO_SUPERIOR/versions"
LEI = "Lei 12.772/2012 com redação da Lei 15.141/2025"

NEW_VERSION = {
    "name": "Versão futura",
    "valid_from": "2031-01-01",
    "valid_to": None,
    "norm_reference": "Lei hipotética 99.999/2030, art. 1º",
    "progression_min_months": 24,
    "classes": [
        {"code": "A", "denominations": ["Assistente"], "levels": [1], "promotion_min_months": None},
        {
            "code": "B",
            "denominations": ["Adjunto"],
            "levels": [1, 2, 3, 4],
            "promotion_min_months": 36,
        },
    ],
}


@pytest.fixture
def admin(act_as, reference):
    return act_as("admin@ufpa.br", Role.ADMIN)


def versions_by_name(client):
    return {v["name"]: v for v in client.get(URL).json()}


def close_lei_version(client, headers, valid_to="2030-12-31"):
    lei = versions_by_name(client)[LEI]
    body = {k: lei[k] for k in NEW_VERSION} | {"valid_to": valid_to}
    return client.put(f"{URL}/{lei['id']}", json=body, headers=headers)


def test_lists_seeded_versions_with_references_and_usage(client, admin):
    response = client.get(URL)

    assert response.status_code == 200
    versions = response.json()
    assert [v["name"] for v in versions] == ["Res. 4.644/2015-CONSEPE", LEI]
    assert all(v["norm_reference"].strip() for v in versions)
    assert [v["in_use"] for v in versions] == [False, False]
    assert [c["code"] for c in versions[1]["classes"]] == ["A", "B", "C", "D"]


def test_admin_creates_version_after_closing_unused_validity(client, admin, uow_factory):
    actor, headers = admin
    assert close_lei_version(client, headers).status_code == 200

    response = client.post(URL, json=NEW_VERSION, headers=headers)

    assert response.status_code == 201
    body = response.json()
    # NTIT-05: every class now also reports its titration rule, none for this version
    expected = {
        **NEW_VERSION,
        "classes": [{**c, "required_titration": None} for c in NEW_VERSION["classes"]],
    }
    assert {k: body[k] for k in NEW_VERSION} == expected
    assert body["in_use"] is False
    assert [v["name"] for v in client.get(URL).json()][-1] == "Versão futura"
    with uow_factory() as uow:
        events = uow.audit.list_for("career_version", body["id"])
    assert [(e.action, e.user_id) for e in events] == [(AuditAction.CREATE, actor.id)]
    assert events[0].changes["norm_reference"] == {
        "before": None,
        "after": "Lei hipotética 99.999/2030, art. 1º",
    }


def test_editing_unused_version_is_audited_with_before_after(client, admin, uow_factory):
    actor, headers = admin
    lei_id = versions_by_name(client)[LEI]["id"]

    response = close_lei_version(client, headers)

    assert response.status_code == 200
    assert response.json()["valid_to"] == "2030-12-31"
    with uow_factory() as uow:
        event = uow.audit.list_for("career_version", lei_id)[-1]
    assert (event.action, event.user_id) == (AuditAction.UPDATE, actor.id)
    assert event.changes == {"valid_to": {"before": None, "after": "2030-12-31"}}


@pytest.mark.parametrize(
    "payload",
    [
        {k: v for k, v in NEW_VERSION.items() if k != "norm_reference"},
        {**NEW_VERSION, "norm_reference": ""},
        {**NEW_VERSION, "norm_reference": "   "},
    ],
    ids=["missing", "empty", "blank"],
)
def test_version_without_norm_reference_returns_422(client, admin, payload):
    _, headers = admin
    close_lei_version(client, headers)

    response = client.post(URL, json=payload, headers=headers)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == ["norm_reference"]


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"classes": []}, "classes"),
        ({"classes": [{**NEW_VERSION["classes"][0], "levels": []}]}, "classes"),
        ({"classes": [{**NEW_VERSION["classes"][0], "levels": [2, 1]}]}, "classes"),
        ({"classes": [{**NEW_VERSION["classes"][0], "denominations": []}]}, "classes"),
        ({"classes": [NEW_VERSION["classes"][0], NEW_VERSION["classes"][0]]}, "classes"),
        ({"progression_min_months": 0}, "progression_min_months"),
        ({"valid_to": "2030-01-01"}, "valid_to"),
        ({"name": " "}, "name"),
        ({"classes": [{"code": "A", "levels": [1]}]}, "denominations"),
    ],
    ids=[
        "no-classes",
        "no-levels",
        "unordered-levels",
        "no-denominations",
        "duplicate-code",
        "zero-interstice",
        "ends-before-start",
        "blank-name",
        "malformed-class",
    ],
)
def test_invalid_definition_returns_422(client, admin, override, field):
    _, headers = admin
    close_lei_version(client, headers)

    response = client.post(URL, json={**NEW_VERSION, **override}, headers=headers)

    assert response.status_code == 422
    assert [error["field"] for error in response.json()["detail"]] == [field]


@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_non_admin_cannot_create_or_edit_versions(client, act_as, reference, role):
    _, headers = act_as("usuario@ufpa.br", role)
    before = client.get(URL).json()

    created = client.post(URL, json=NEW_VERSION, headers=headers)
    edited = close_lei_version(client, headers)

    assert (created.status_code, edited.status_code) == (403, 403)
    assert client.get(URL).json() == before


def test_version_used_by_a_process_cannot_be_edited(client, admin, reference, uow_factory):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    created = client.post(
        "/api/processes", json=process_payload(professor, REQUERIMENTO_2024_2026), headers=headers
    )
    assert created.status_code == 201  # ends 23/11/2026: uses the Lei 15.141/2025 version
    assert versions_by_name(client)[LEI]["in_use"] is True

    response = close_lei_version(client, headers)

    assert response.status_code == 409
    assert versions_by_name(client)[LEI]["valid_to"] is None


def test_overlapping_a_closed_version_returns_409(client, admin):
    _, headers = admin
    overlapping = {**NEW_VERSION, "valid_from": "2020-01-01", "valid_to": "2020-12-31"}

    response = client.post(URL, json=overlapping, headers=headers)  # inside Res. 4.644 validity

    assert response.status_code == 409
    assert "Versão futura" not in versions_by_name(client)


def _create_requerimento_process(client, headers, reference, uow_factory):
    professor = add_professor(uow_factory, reference["FASI"])
    created = client.post(
        "/api/processes", json=process_payload(professor, REQUERIMENTO_2024_2026), headers=headers
    )
    assert created.status_code == 201  # ends 23/11/2026: uses the open-ended Lei version


# CARR-09
def test_creating_next_version_closes_open_ended_version(client, admin, reference, uow_factory):
    actor, headers = admin
    _create_requerimento_process(client, headers, reference, uow_factory)
    lei_id = versions_by_name(client)[LEI]["id"]

    response = client.post(URL, json=NEW_VERSION, headers=headers)  # starts 01/01/2031

    assert response.status_code == 201
    versions = versions_by_name(client)
    assert versions[LEI]["valid_to"] == "2030-12-31"
    assert versions["Versão futura"]["valid_from"] == "2031-01-01"
    with uow_factory() as uow:
        event = uow.audit.list_for("career_version", lei_id)[-1]
    assert (event.action, event.user_id) == (AuditAction.UPDATE, actor.id)
    assert event.changes == {"valid_to": {"before": None, "after": "2030-12-31"}}


# CARR-10
def test_closing_that_would_move_an_existing_process_returns_409(
    client, admin, reference, uow_factory
):
    _, headers = admin
    _create_requerimento_process(client, headers, reference, uow_factory)
    early = {**NEW_VERSION, "valid_from": "2026-01-01"}  # process ends 23/11/2026, after it

    response = client.post(URL, json=early, headers=headers)

    assert response.status_code == 409
    versions = versions_by_name(client)
    assert versions[LEI]["valid_to"] is None
    assert "Versão futura" not in versions


# CARR-10 boundary: a process ending exactly on the new version's first day blocks the close
def test_process_ending_on_new_version_start_day_blocks_close(
    client, admin, reference, uow_factory
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    on_boundary = process_payload(
        professor, REQUERIMENTO_2024_2026, end_date="2031-01-01", opening_date="2031-01-02"
    )
    assert client.post("/api/processes", json=on_boundary, headers=headers).status_code == 201

    response = client.post(URL, json=NEW_VERSION, headers=headers)  # starts 01/01/2031

    assert response.status_code == 409
    versions = versions_by_name(client)
    assert versions[LEI]["valid_to"] is None
    assert "Versão futura" not in versions


# CARR-09 boundary: a version starting on the open version's own first day is not a successor
def test_version_starting_on_open_version_start_day_returns_409(client, admin):
    _, headers = admin
    same_start = {**NEW_VERSION, "valid_from": "2025-01-01"}

    response = client.post(URL, json=same_start, headers=headers)

    assert response.status_code == 409
    lei = versions_by_name(client)[LEI]
    assert (lei["valid_from"], lei["valid_to"]) == ("2025-01-01", None)
    assert "Versão futura" not in versions_by_name(client)


def test_unknown_structure_returns_404(client, admin):
    assert client.get("/api/career-structures/EBTT/versions").status_code == 404


# CARR-08 boundary: validities sharing exactly one day overlap
@pytest.mark.parametrize(
    "day",
    ["2024-12-31", "2025-01-01"],
    ids=["last-day-of-res-4644", "first-day-of-open-lei"],
)
def test_single_day_overlap_returns_409(client, admin, day):
    _, headers = admin
    before = client.get(URL).json()
    one_day = {**NEW_VERSION, "valid_from": day, "valid_to": day}

    response = client.post(URL, json=one_day, headers=headers)

    assert response.status_code == 409
    assert client.get(URL).json() == before


# CARR-09/CARR-10 boundary: a process ending the day before the new version starts allows the close
def test_process_ending_day_before_new_version_allows_close(
    client, admin, reference, uow_factory
):
    _, headers = admin
    professor = add_professor(uow_factory, reference["FASI"])
    last_allowed = process_payload(
        professor, REQUERIMENTO_2024_2026, end_date="2030-12-31", opening_date="2031-01-02"
    )
    assert client.post("/api/processes", json=last_allowed, headers=headers).status_code == 201

    response = client.post(URL, json=NEW_VERSION, headers=headers)  # starts 01/01/2031

    assert response.status_code == 201
    versions = versions_by_name(client)
    assert versions[LEI]["valid_to"] == "2030-12-31"
    assert versions["Versão futura"]["valid_from"] == "2031-01-01"


RES_4644 = "Res. 4.644/2015-CONSEPE"


# CARR-08: "in use" is decided per version, by the interstice end date each one covers
def test_in_use_is_decided_per_version(client, admin, reference, uow_factory):
    _, headers = admin
    _create_requerimento_process(client, headers, reference, uow_factory)  # ends 23/11/2026

    versions = versions_by_name(client)
    assert versions[RES_4644]["in_use"] is False
    assert versions[LEI]["in_use"] is True

    res = versions[RES_4644]
    unchanged = {k: res[k] for k in NEW_VERSION}
    response = client.put(f"{URL}/{res['id']}", json=unchanged, headers=headers)
    assert response.status_code == 200


# --- NLINK-01, NTIT-05, NTIT-06, NMOV-05: the norm code and the titration travel in the API ----

RES = "Res. 4.644/2015-CONSEPE"
MANUAL = "MANUAL-PROGEP-PROGRESSAO"


def class_by_code(version):
    return {c["code"]: c for c in version["classes"]}


def full_body(version, **changes):
    """The body of the PUT with every field the API returns, links included."""
    keys = (*NEW_VERSION, "norm_code", "required_titration_norm_code")
    return {k: version[k] for k in keys} | changes


def test_get_brings_the_norm_codes_and_the_titration_of_each_class(client, admin):
    versions = versions_by_name(client)

    old, new = versions[RES], versions[LEI]

    assert (old["norm_code"], old["required_titration_norm_code"]) == (
        "RES-4644-2015-CONSEPE",
        None,
    )
    assert all(c["required_titration"] is None for c in old["classes"])
    assert (new["norm_code"], new["required_titration_norm_code"]) == ("LEI-12772-2012", MANUAL)
    assert {c: v["required_titration"] for c, v in class_by_code(new).items()} == {
        "A": None,
        "B": None,
        "C": "DOUTORADO",
        "D": "DOUTORADO",
    }


def test_put_with_the_link_fields_saves_returns_and_audits_them(client, admin, uow_factory):
    _, headers = admin
    lei = versions_by_name(client)[LEI]
    classes = [
        {**c, "required_titration": "MESTRADO" if c["code"] == "B" else None}
        for c in lei["classes"]
    ]

    response = client.put(
        f"{URL}/{lei['id']}",
        json=full_body(
            lei,
            classes=classes,
            norm_code="LEI-OUTRA-2030",
            required_titration_norm_code="MANUAL-X",
        ),
        headers=headers,
    )

    assert response.status_code == 200, response.text
    for body in (response.json(), versions_by_name(client)[LEI]):
        assert (body["norm_code"], body["required_titration_norm_code"]) == (
            "LEI-OUTRA-2030",
            "MANUAL-X",
        )
        assert {c: v["required_titration"] for c, v in class_by_code(body).items()} == {
            "A": None,
            "B": "MESTRADO",
            "C": None,  # sent as null: cleared
            "D": None,
        }
    with uow_factory() as uow:
        event = uow.audit.list_for("career_version", lei["id"])[-1]
    assert event.changes["norm_code"] == {"before": "LEI-12772-2012", "after": "LEI-OUTRA-2030"}
    assert event.changes["required_titration_norm_code"] == {
        "before": MANUAL,
        "after": "MANUAL-X",
    }
    assert "classes" in event.changes


def test_put_with_an_old_body_keeps_the_stored_norm_code_and_titration(client, admin):
    _, headers = admin
    before = versions_by_name(client)[LEI]

    response = close_lei_version(client, headers)  # the body has none of the link fields

    assert response.status_code == 200, response.text
    after = versions_by_name(client)[LEI]
    assert after["valid_to"] == "2030-12-31"
    for field in ("norm_code", "required_titration_norm_code", "classes"):
        assert after[field] == before[field]
    assert class_by_code(after)["C"]["required_titration"] == "DOUTORADO"


def test_an_invalid_titration_is_422_on_the_field(client, admin):
    _, headers = admin
    lei = versions_by_name(client)[LEI]
    classes = [{**c, "required_titration": "LIVRE_DOCENCIA"} for c in lei["classes"]]

    response = client.put(
        f"{URL}/{lei['id']}", json=full_body(lei, classes=classes), headers=headers
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "required_titration"
    assert class_by_code(versions_by_name(client)[LEI])["C"]["required_titration"] == "DOUTORADO"


def test_a_new_version_is_created_with_its_norm_code_and_titration(client, admin):
    _, headers = admin
    assert close_lei_version(client, headers).status_code == 200
    body = {
        **NEW_VERSION,
        "norm_code": "LEI-SINTETICA-2030",
        "required_titration_norm_code": "MANUAL-SINTETICO",
        "classes": [
            NEW_VERSION["classes"][0],
            {**NEW_VERSION["classes"][1], "required_titration": "ESPECIALIZACAO"},
        ],
    }

    created = client.post(URL, json=body, headers=headers)

    assert created.status_code == 201, created.text
    stored = versions_by_name(client)["Versão futura"]
    assert (stored["norm_code"], stored["required_titration_norm_code"]) == (
        "LEI-SINTETICA-2030",
        "MANUAL-SINTETICO",
    )
    assert {c: v["required_titration"] for c, v in class_by_code(stored).items()} == {
        "A": None,
        "B": "ESPECIALIZACAO",
    }


# NMOV-05
def test_changing_a_denomination_shows_divergence_without_touching_the_process(
    client, admin, reference, uow_factory
):
    _, headers = admin
    assert close_lei_version(client, headers).status_code == 200
    classes = [
        *NEW_VERSION["classes"],
        {"code": "C", "denominations": ["Associado"], "levels": [1, 2], "promotion_min_months": 24},
    ]
    created = client.post(URL, json={**NEW_VERSION, "classes": classes}, headers=headers)
    assert created.status_code == 201, created.text
    version = created.json()
    renamed = [
        {**c, "denominations": ["Associado Pleno Sintético"]} if c["code"] == "C" else c
        for c in version["classes"]
    ]
    edited = client.put(
        f"{URL}/{version['id']}", json=full_body(version, classes=renamed), headers=headers
    )
    assert edited.status_code == 200, edited.text  # the version is not used yet
    professor = add_professor(uow_factory, reference["FASI"])
    case = {
        "modality": "PROMOCAO",
        "current_class": "B",
        "current_denomination": "Adjunto",
        "current_level": 4,
        "target_class": "C",
        "target_denomination": "Associado",
        "target_level": 1,
        "start_date": "2031-01-02",
        "end_date": "2033-01-02",
        "opening_date": "2033-02-01",
    }

    process = client.post(
        "/api/processes", json=process_payload(professor, case), headers=headers
    ).json()

    alerts = {a["code"]: a for a in process["alerts"]}
    assert "DENOMINACAO_DIVERGENTE" in alerts
    assert 'esperada "Associado Pleno Sintético"' in alerts["DENOMINACAO_DIVERGENTE"]["message"]
    assert alerts["DENOMINACAO_DIVERGENTE"]["severity"] == "ALERTA"
    read = client.get(f"/api/processes/{process['id']}").json()
    assert read["target_denomination"] == "Associado"  # what the user informed stays
    assert read["current_denomination"] == "Adjunto"
