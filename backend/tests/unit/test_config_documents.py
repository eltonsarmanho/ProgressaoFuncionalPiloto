"""EXT-02, DOC-03: storage, upload limits, worker and AI settings."""

import pytest

from app.core.config import load_settings

DB_URL = "postgresql+psycopg://app:db-pass-123@db:5432/app"
ADMIN_PASS = "admin-secret-value-987"
API_KEY = "mk-real-looking-secret-key-555"

ENV_NAMES = [
    "DATABASE_URL",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "MARITALK_API_KEY",
    "MARITALK_API_BASE",
    "MARITALK_MODEL",
    "MARITALK_FALLBACK_MODEL",
    "STORAGE_DIR",
    "WORKER_ENABLED",
    "MAX_UPLOAD_MB",
    "MAX_REQUEST_MB",
    "MAX_PAGES",
    "MAX_MEGAPIXELS",
    "MAX_DOCUMENTS_PER_PROCESS",
    "MAX_UPLOADS_PER_MINUTE",
    "AI_TIMEOUT_SECONDS",
    "AI_MAX_TOKENS",
]


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    # the real .env must never leak into these tests
    monkeypatch.chdir(tmp_path)
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@ufpa.br")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASS)


def test_limits_have_the_defaults_of_the_spec():
    settings = load_settings()
    assert settings.max_upload_mb == 20
    assert settings.max_request_mb == 120
    assert settings.max_pages == 100
    assert settings.max_megapixels == 100
    assert settings.max_documents_per_process == 200
    assert settings.max_uploads_per_minute == 60


def test_storage_worker_and_ai_defaults():
    settings = load_settings()
    assert settings.storage_dir == "/app/storage"
    assert settings.worker_enabled is True
    assert settings.ai_timeout_seconds == 60
    assert settings.ai_max_tokens == 8000


def test_every_setting_is_read_from_its_snake_case_environment_name(monkeypatch):
    values = {
        "STORAGE_DIR": "/tmp/somewhere",
        "WORKER_ENABLED": "false",
        "MAX_UPLOAD_MB": "5",
        "MAX_REQUEST_MB": "30",
        "MAX_PAGES": "10",
        "MAX_MEGAPIXELS": "50",
        "MAX_DOCUMENTS_PER_PROCESS": "7",
        "MAX_UPLOADS_PER_MINUTE": "3",
        "AI_TIMEOUT_SECONDS": "15",
        "AI_MAX_TOKENS": "4000",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = load_settings()

    assert settings.storage_dir == "/tmp/somewhere"
    assert settings.worker_enabled is False
    assert settings.max_upload_mb == 5
    assert settings.max_request_mb == 30
    assert settings.max_pages == 10
    assert settings.max_megapixels == 50
    assert settings.max_documents_per_process == 7
    assert settings.max_uploads_per_minute == 3
    assert settings.ai_timeout_seconds == 15
    assert settings.ai_max_tokens == 4000


def test_effective_model_is_the_configured_one_when_filled(monkeypatch):
    monkeypatch.setenv("MARITALK_MODEL", "sabiazinho-4")
    assert load_settings().effective_maritalk_model == "sabiazinho-4"


def test_effective_model_is_sabia_4_br_sp_when_unset():
    assert load_settings().effective_maritalk_model == "sabia-4-br-sp"


@pytest.mark.parametrize("empty", ["", "   "])
def test_effective_model_is_sabia_4_br_sp_when_empty(monkeypatch, empty):
    monkeypatch.setenv("MARITALK_MODEL", empty)
    assert load_settings().effective_maritalk_model == "sabia-4-br-sp"


def test_no_secret_value_appears_in_repr_or_str(monkeypatch):
    monkeypatch.setenv("MARITALK_API_KEY", API_KEY)
    settings = load_settings()
    for text in (repr(settings), str(settings)):
        assert API_KEY not in text
        assert ADMIN_PASS not in text
        assert "db-pass-123" not in text
