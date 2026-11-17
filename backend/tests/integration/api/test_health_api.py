"""INFRA-01 / INFRA-03: health endpoint with database probe."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

UNREACHABLE_DB = "postgresql+psycopg://test:test@127.0.0.1:1/test"


def test_health_is_public_and_reports_database_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable():
    settings = Settings(
        database_url=UNREACHABLE_DB,
        admin_email="admin@ufpa.br",
        admin_password="admin-password-1",
    )
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
