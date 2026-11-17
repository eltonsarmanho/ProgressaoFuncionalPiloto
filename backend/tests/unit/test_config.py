"""INFRA-06 / INFRA-07: environment settings."""

import pytest

from app.core.config import Settings, load_settings

ALL_VARS = [
    "DATABASE_URL",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "COOKIE_SECURE",
    "MARITALK_API_KEY",
    "MARITALK_API_BASE",
    "MARITALK_MODEL",
    "MARITALK_FALLBACK_MODEL",
]

DB_URL = "postgresql+psycopg://app:db-pass-123@db:5432/app"
ADMIN_PASS = "admin-secret-value-987"
API_KEY = "mk-real-looking-secret-key-555"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ALL_VARS:
        monkeypatch.delenv(name, raising=False)


def set_required(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@ufpa.br")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASS)


def test_missing_required_variable_exits_naming_it_without_other_values(monkeypatch):
    set_required(monkeypatch)
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("MARITALK_API_KEY", API_KEY)

    with pytest.raises(SystemExit) as exc:
        load_settings()

    message = str(exc.value.code)
    assert "DATABASE_URL" in message
    assert ADMIN_PASS not in message
    assert API_KEY not in message
    assert "admin@ufpa.br" not in message


def test_each_missing_required_variable_is_named(monkeypatch):
    with pytest.raises(SystemExit) as exc:
        load_settings()

    message = str(exc.value.code)
    for name in ("DATABASE_URL", "ADMIN_EMAIL", "ADMIN_PASSWORD"):
        assert name in message


def test_maritalk_key_not_exposed_by_repr_or_dump(monkeypatch):
    set_required(monkeypatch)
    monkeypatch.setenv("MARITALK_API_KEY", API_KEY)

    settings = load_settings()

    assert API_KEY not in repr(settings)
    assert API_KEY not in str(settings)
    assert API_KEY not in str(settings.model_dump())
    assert API_KEY not in settings.model_dump_json()
    assert ADMIN_PASS not in repr(settings)
    assert ADMIN_PASS not in str(settings.model_dump())
    # the backend itself can still read the key
    assert settings.maritalk_api_key.get_secret_value() == API_KEY


def test_maritalk_variables_are_optional_with_fallback_model(monkeypatch):
    set_required(monkeypatch)

    settings = load_settings()

    assert settings.maritalk_api_key is None
    assert settings.maritalk_api_base is None
    assert settings.maritalk_model is None
    assert settings.maritalk_fallback_model == "sabia-4-br-sp"


def test_cookie_secure_defaults_true_and_is_configurable(monkeypatch):
    set_required(monkeypatch)
    assert load_settings().cookie_secure is True

    monkeypatch.setenv("COOKIE_SECURE", "false")
    assert load_settings().cookie_secure is False


def test_unrelated_environment_variables_are_ignored(monkeypatch):
    set_required(monkeypatch)
    monkeypatch.setenv("CHATWOOT_TOKEN", "unrelated")

    settings = load_settings()

    assert isinstance(settings, Settings)
    assert settings.database_url == DB_URL
