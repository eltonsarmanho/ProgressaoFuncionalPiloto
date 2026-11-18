"""AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-11 through the HTTP API."""

from datetime import timedelta

import pytest
from fastapi import APIRouter

from app.domain.errors import Conflict, Forbidden, NotFound, StaleVersion, ValidationFailed
from app.infrastructure.security import tokens
from tests.integration.api.conftest import PASSWORD, login

EMAIL = "docente@ufpa.br"


def _set_cookie(response) -> str:
    return response.headers["set-cookie"]


def test_login_returns_user_and_sets_hardened_session_cookie(client, make_user, uow_factory):
    user = make_user(EMAIL, name="Docente Um")

    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "name": "Docente Um", "role": "DOCENTE"}
    cookie = _set_cookie(response)
    attributes = {part.strip().lower() for part in cookie.split(";")}
    assert cookie.startswith("session=")
    assert "httponly" in attributes
    assert "samesite=strict" in attributes
    assert "secure" in attributes
    token = client.cookies["session"]
    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash(tokens.hash_token(token)) is not None


def test_cookie_is_not_secure_when_cookie_secure_is_false(make_client, make_user):
    make_user(EMAIL)
    client = make_client(cookie_secure=False)

    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    attributes = {part.strip().lower() for part in _set_cookie(response).split(";")}
    assert response.status_code == 200
    assert "secure" not in attributes
    assert "httponly" in attributes and "samesite=strict" in attributes


@pytest.mark.parametrize(
    ("email", "password"),
    [(EMAIL, "senha-errada-99"), ("ninguem@ufpa.br", PASSWORD)],
    ids=["wrong-password", "unknown-user"],
)
def test_invalid_credentials_return_401_with_single_message(client, make_user, email, password):
    make_user(EMAIL)

    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuário ou senha inválidos"}
    assert "set-cookie" not in response.headers


def test_sixth_attempt_after_five_failures_returns_429(client, make_user, clock):
    make_user(EMAIL)
    for _ in range(5):
        wrong = client.post("/api/auth/login", json={"email": EMAIL, "password": "x-wrong-123"})
        assert wrong.status_code == 401

    blocked = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert blocked.status_code == 429

    clock.current += timedelta(minutes=15)
    allowed = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert allowed.status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/auth/me"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/processes"),
        ("DELETE", "/api/qualquer/coisa"),
    ],
)
def test_api_without_session_returns_401(client, method, path):
    response = client.request(method, path)

    assert response.status_code == 401


def test_api_with_unknown_session_token_returns_401(client):
    client.cookies.set("session", "token-forjado")

    assert client.get("/api/auth/me").status_code == 401


def test_login_route_is_public(client):
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 401
    assert response.json() == {"detail": "Usuário ou senha inválidos"}


def test_me_returns_user_and_session_csrf_token(client, make_user, uow_factory):
    user = make_user(EMAIL, name="Docente Um")
    client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = client.get("/api/auth/me")

    with uow_factory() as uow:
        session = uow.sessions.get_by_token_hash(tokens.hash_token(client.cookies["session"]))
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "name": "Docente Um",
        "role": "DOCENTE",
        "csrf_token": session.csrf_token,
    }


@pytest.mark.parametrize("headers", [{}, {"X-CSRF-Token": "token-errado"}], ids=["none", "wrong"])
def test_write_without_valid_csrf_token_returns_403(client, make_user, headers):
    make_user(EMAIL)
    login(client, EMAIL)

    response = client.post("/api/auth/logout", headers=headers)

    assert response.status_code == 403
    assert client.get("/api/auth/me").status_code == 200  # session untouched


def test_logout_with_csrf_invalidates_session(client, make_user, uow_factory):
    make_user(EMAIL)
    csrf = login(client, EMAIL)
    token = client.cookies["session"]

    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    assert response.status_code == 204
    with uow_factory() as uow:
        assert uow.sessions.get_by_token_hash(tokens.hash_token(token)) is None
    client.cookies.set("session", token)  # replaying the old cookie must fail
    assert client.get("/api/auth/me").status_code == 401


def test_session_idle_for_30_minutes_gets_401(client, make_user, clock):
    make_user(EMAIL)
    login(client, EMAIL)

    clock.current += timedelta(minutes=30)

    assert client.get("/api/auth/me").status_code == 401


def test_session_older_than_8_hours_gets_401(client, make_user, clock):
    make_user(EMAIL)
    login(client, EMAIL)
    for _ in range(23):  # active every 20 minutes up to 7h40
        clock.current += timedelta(minutes=20)
        assert client.get("/api/auth/me").status_code == 200

    clock.current += timedelta(minutes=20)  # 8h after login

    assert client.get("/api/auth/me").status_code == 401


def _raise(exc: Exception):
    def endpoint():
        raise exc

    return endpoint


@pytest.mark.parametrize(
    ("exc", "status", "body"),
    [
        (NotFound("Processo não encontrado"), 404, {"detail": "Processo não encontrado"}),
        (Conflict("SIAPE já cadastrado"), 409, {"detail": "SIAPE já cadastrado"}),
        (StaleVersion("Recarregue"), 409, {"detail": "Recarregue"}),
        (Forbidden("Acesso negado"), 403, {"detail": "Acesso negado"}),
        (
            ValidationFailed("siape", "Deve conter 7 dígitos"),
            422,
            {"detail": [{"field": "siape", "message": "Deve conter 7 dígitos"}]},
        ),
    ],
)
def test_domain_errors_are_mapped_to_http(client, make_user, exc, status, body):
    router = APIRouter()
    router.add_api_route("/api/_probe", _raise(exc), methods=["GET"])
    client.app.include_router(router)
    make_user(EMAIL)
    login(client, EMAIL)

    response = client.get("/api/_probe")

    assert response.status_code == status
    assert response.json() == body


def test_request_validation_error_names_the_field(client):
    response = client.post("/api/auth/login", json={"email": EMAIL})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert [error["field"] for error in detail] == ["password"]
    assert all(error["message"] for error in detail)
