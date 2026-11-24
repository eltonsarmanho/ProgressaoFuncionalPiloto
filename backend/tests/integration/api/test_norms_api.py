"""NBASE-01..10, NLIST-01, NLIST-02: the /api/norms routes, with synthetic norms and PDFs."""

import pytest

from app.domain.entities.user import Role
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import pdf

MB = 1024 * 1024
SEEDED = {
    "LEI-12772-2012",
    "RES-4644-2015-CONSEPE",
    "RES-4074-2010-CONSEPE",
    "IN-01-2026-IFCH",
    "MANUAL-PROGEP-PROGRESSAO",
    "CORRELACAO-PROGEP-2025",
    "TABELA-OFICIAL-UFPA",
}
BODY = {
    "code": "RES-SINTETICA-2020",
    "title": "Resolução sintética de teste",
    "kind": "RESOLUCAO",
    "issuer": "Órgão sintético",
    "published_on": "2020-03-04",
}


@pytest.fixture
def admin(act_as):
    return act_as("admin@ufpa.br", Role.ADMIN)


@pytest.fixture
def created(client, admin):
    response = client.post("/api/norms", json=BODY, headers=admin[1])
    assert response.status_code == 201, response.text
    return response.json()


def as_docente(client, make_user):
    make_user("docente@ufpa.br", role=Role.DOCENTE)
    return {"X-CSRF-Token": login(client, "docente@ufpa.br")}


def attach(client, headers, norm, content=None, name="norma.pdf", version=None):
    return client.put(
        f"/api/norms/{norm['id']}/file",
        files={"file": (name, pdf("norma") if content is None else content, "application/pdf")},
        data={"expected_version": norm["version"] if version is None else version},
        headers=headers,
    )


# NBASE-01
def test_the_admin_creates_a_norm_that_comes_back_active_with_no_file(client, admin):
    response = client.post(
        "/api/norms",
        json=BODY | {"source_url": "https://exemplo.invalido/n", "valid_from": "2020-04-01"},
        headers=admin[1],
    )

    assert response.status_code == 201
    body = response.json()
    assert {k: v for k, v in body.items() if k != "id"} == BODY | {
        "source_url": "https://exemplo.invalido/n",
        "valid_from": "2020-04-01",
        "valid_to": None,
        "notes": None,
        "archived": False,
        "version": 1,
        "file": None,
        "linked_rules": [],
    }
    assert client.get(f"/api/norms/{body['id']}").json() == body


# NLIST-01
def test_a_docente_lists_the_seven_seeded_norms_with_their_linked_rules(
    client, make_user, reference
):
    as_docente(client, make_user)

    response = client.get("/api/norms")

    assert response.status_code == 200
    by_code = {n["code"]: n for n in response.json()}
    assert set(by_code) == SEEDED
    assert by_code["IN-01-2026-IFCH"]["linked_rules"] == []
    assert {r["kind"] for r in by_code["LEI-12772-2012"]["linked_rules"]} == {"CARREIRA"}
    assert {r["kind"] for r in by_code["MANUAL-PROGEP-PROGRESSAO"]["linked_rules"]} == {
        "TITULACAO"
    }
    assert all(n["file"] is None and n["archived"] is False for n in by_code.values())
    one = client.get(f"/api/norms/{by_code['LEI-12772-2012']['id']}")
    assert one.status_code == 200
    assert one.json() == by_code["LEI-12772-2012"]


def test_requests_without_a_session_are_401(client, created):
    client.cookies.clear()
    assert client.get("/api/norms").status_code == 401
    assert client.get(f"/api/norms/{created['id']}").status_code == 401
    assert client.get(f"/api/norms/{created['id']}/file").status_code == 401
    assert client.post("/api/norms", json=BODY).status_code == 401


# NBASE-02..04
@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"code": "RES-SINTETICA-2020"}, "code"),  # repeated
        ({"code": ""}, "code"),
        ({"code": "res minuscula"}, "code"),
        ({"title": ""}, "title"),
        ({"issuer": ""}, "issuer"),
        ({"valid_from": "2021-01-10", "valid_to": "2021-01-09"}, "valid_to"),
        ({"source_url": "ftp://exemplo.invalido/n"}, "source_url"),
        ({"kind": "DECRETO"}, "kind"),
        ({"published_on": None}, "published_on"),
    ],
)
def test_an_invalid_norm_is_422_on_the_field(client, admin, created, change, field):
    response = client.post(
        "/api/norms", json=BODY | {"code": "RES-OUTRA-2021"} | change, headers=admin[1]
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == field
    codes = {n["code"] for n in client.get("/api/norms").json()}
    assert codes == {"RES-SINTETICA-2020"}


def test_a_missing_required_field_is_422_on_that_field(client, admin):
    for field in ("code", "title", "kind", "issuer", "published_on"):
        body = {k: v for k, v in BODY.items() if k != field}
        response = client.post("/api/norms", json=body, headers=admin[1])
        assert response.status_code == 422
        assert response.json()["detail"][0]["field"] == field


# NBASE-07
def test_the_admin_edits_a_norm_and_the_code_does_not_change(client, admin, created):
    response = client.put(
        f"/api/norms/{created['id']}",
        json={
            "code": "OUTRO-CODIGO",
            "title": "Título novo",
            "kind": "LEI",
            "issuer": "Outro órgão",
            "published_on": "2021-05-06",
            "notes": "Observação",
            "expected_version": created["version"],
        },
        headers=admin[1],
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["code"], body["title"], body["kind"], body["issuer"]) == (
        "RES-SINTETICA-2020",
        "Título novo",
        "LEI",
        "Outro órgão",
    )
    assert (body["published_on"], body["notes"], body["version"]) == ("2021-05-06", "Observação", 2)


# NBASE-08, NLIST-02
def test_archiving_hides_the_norm_from_the_default_list_and_the_filter_shows_it(
    client, admin, created
):
    response = client.post(
        f"/api/norms/{created['id']}/archive",
        json={"expected_version": created["version"]},
        headers=admin[1],
    )

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert [n["code"] for n in client.get("/api/norms").json()] == []
    listed = client.get("/api/norms", params={"include_archived": "true"}).json()
    assert [(n["code"], n["archived"]) for n in listed] == [("RES-SINTETICA-2020", True)]


# NBASE-05, NBASE-06, download
def test_the_admin_attaches_a_pdf_and_any_role_opens_it_in_a_sandbox(
    client, admin, created, make_user
):
    content = pdf("norma anexada")
    response = attach(client, admin[1], created, content, "Resolução ç.pdf")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["file"] == {
        "original_name": "Resolução ç.pdf",
        "size_bytes": len(content),
        "url": f"/api/norms/{created['id']}/file",
    }
    as_docente(client, make_user)
    opened = client.get(body["file"]["url"])
    assert opened.status_code == 200
    assert opened.content == content
    assert opened.headers["content-type"] == "application/pdf"
    assert opened.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in opened.headers["content-security-policy"]
    assert "filename*=UTF-8''Resolu%C3%A7%C3%A3o%20%C3%A7.pdf" in opened.headers[
        "content-disposition"
    ]


def test_a_second_pdf_replaces_the_first_one(client, admin, created):
    first = attach(client, admin[1], created, pdf("primeiro")).json()
    second = attach(client, admin[1], first, pdf("segundo")).json()

    assert client.get(second["file"]["url"]).content == pdf("segundo")
    assert second["version"] == 3


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("nota.txt", b"texto"),
        ("imagem.png", b"\x89PNG\r\n\x1a\n" + b"0" * 50),
        ("falso.pdf", b"\x89PNG\r\n\x1a\n" + b"0" * 50),
    ],
)
def test_a_file_that_is_not_a_pdf_is_422_on_the_file(client, admin, created, name, content):
    response = attach(client, admin[1], created, content, name)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "arquivo"
    assert client.get(f"/api/norms/{created['id']}").json()["file"] is None


def test_a_pdf_over_20_mb_is_422_with_the_limit(client, admin, created):
    big = b"%PDF-1.4\n" + b"0" * (20 * MB)

    response = attach(client, admin[1], created, big, "grande.pdf")

    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["field"] == "arquivo"
    assert "20 MB" in detail["message"]


# NBASE-09
def test_a_docente_cannot_write_and_the_norm_stays_as_it_was(client, admin, created, make_user):
    headers = as_docente(client, make_user)
    url = f"/api/norms/{created['id']}"
    edit = {k: v for k, v in BODY.items() if k != "code"} | {"expected_version": 1}

    new = client.post("/api/norms", json=BODY | {"code": "RES-NOVA-1"}, headers=headers)
    edited = client.put(url, json=edit | {"title": "Outro"}, headers=headers)
    archived = client.post(f"{url}/archive", json={"expected_version": 1}, headers=headers)
    attached = attach(client, headers, created)

    assert [r.status_code for r in (new, edited, archived, attached)] == [403, 403, 403, 403]

    stored = client.get(url).json()
    assert stored == created


# NBASE-10
def test_a_stale_version_is_409_on_edit_archive_and_attach(client, admin, created):
    url = f"/api/norms/{created['id']}"
    edit = {k: v for k, v in BODY.items() if k != "code"}
    first = client.put(
        url, json=edit | {"title": "Primeira", "expected_version": 1}, headers=admin[1]
    )
    assert first.status_code == 200

    second = client.put(
        url, json=edit | {"title": "Segunda", "expected_version": 1}, headers=admin[1]
    )
    archive = client.post(f"{url}/archive", json={"expected_version": 1}, headers=admin[1])
    file = attach(client, admin[1], created, version=1)

    assert (second.status_code, archive.status_code, file.status_code) == (409, 409, 409)
    stored = client.get(url).json()
    assert (stored["title"], stored["archived"], stored["file"]) == ("Primeira", False, None)


# 404
def test_an_unknown_norm_is_404_on_every_route(client, admin):
    unknown = "00000000-0000-4000-8000-000000000000"
    edit = {k: v for k, v in BODY.items() if k != "code"} | {"expected_version": 1}

    assert client.get(f"/api/norms/{unknown}").status_code == 404
    assert client.put(f"/api/norms/{unknown}", json=edit, headers=admin[1]).status_code == 404
    archived = client.post(
        f"/api/norms/{unknown}/archive", json={"expected_version": 1}, headers=admin[1]
    )
    assert archived.status_code == 404
    assert attach(client, admin[1], {"id": unknown, "version": 1}).status_code == 404
    assert client.get(f"/api/norms/{unknown}/file").status_code == 404


def test_a_norm_without_a_file_is_404_on_the_file_route(client, admin, created):
    assert client.get(f"/api/norms/{created['id']}/file").status_code == 404


def test_a_stored_file_that_left_the_disk_is_404_not_a_server_error(
    client, admin, created, tmp_path
):
    attach(client, admin[1], created)
    for stored in (tmp_path / "storage" / "norms").glob("*.pdf"):
        stored.unlink()

    assert client.get(f"/api/norms/{created['id']}/file").status_code == 404
