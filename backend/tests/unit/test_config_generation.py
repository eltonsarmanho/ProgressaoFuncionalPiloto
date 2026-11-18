"""CMP-09, CMP-13, REL-05: limits and deadlines of the generated documents."""

import pytest

from app.core.config import load_settings

ENV_NAMES = [
    "DATABASE_URL",
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD",
    "GENERATION_MAX_PAGES",
    "GENERATION_MAX_OUTPUT_MB",
    "GENERATION_PNG_MAX_MEGAPIXELS",
    "GENERATION_MIN_FREE_MB",
    "WORDING_TIMEOUT_SECONDS",
    "REPORT_TEMPLATE_ID",
]


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    # the real .env must never leak into these tests
    monkeypatch.chdir(tmp_path)
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:db-pass-123@db:5432/app")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@ufpa.br")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-secret-value-987")


def test_defaults_hold_without_any_environment_variable():
    settings = load_settings()
    assert settings.generation_max_pages == 400
    assert settings.generation_max_output_mb == 60
    assert settings.generation_png_max_megapixels == 12
    assert settings.generation_min_free_mb == 200
    assert settings.wording_timeout_seconds == 60
    assert settings.report_template_id is None


def test_environment_variables_override_the_defaults(monkeypatch):
    monkeypatch.setenv("GENERATION_MAX_PAGES", "100")
    monkeypatch.setenv("GENERATION_MAX_OUTPUT_MB", "30")
    monkeypatch.setenv("GENERATION_PNG_MAX_MEGAPIXELS", "8")
    monkeypatch.setenv("GENERATION_MIN_FREE_MB", "500")
    monkeypatch.setenv("WORDING_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("REPORT_TEMPLATE_ID", "ufpa-modelo-2")

    settings = load_settings()

    assert settings.generation_max_pages == 100
    assert settings.generation_max_output_mb == 30
    assert settings.generation_png_max_megapixels == 8
    assert settings.generation_min_free_mb == 500
    assert settings.wording_timeout_seconds == 15
    assert settings.report_template_id == "ufpa-modelo-2"


@pytest.mark.parametrize("empty", ["", "   "])
def test_an_empty_template_id_means_the_one_in_the_file(monkeypatch, empty):
    monkeypatch.setenv("REPORT_TEMPLATE_ID", empty)
    assert load_settings().report_template_id is None


@pytest.mark.parametrize(
    "name",
    [
        "GENERATION_MAX_PAGES",
        "GENERATION_MAX_OUTPUT_MB",
        "GENERATION_PNG_MAX_MEGAPIXELS",
        "GENERATION_MIN_FREE_MB",
        "WORDING_TIMEOUT_SECONDS",
    ],
)
@pytest.mark.parametrize("value", ["abc", "0", "-5"])
def test_an_invalid_value_stops_the_loading_naming_the_variable_but_not_its_value(
    monkeypatch, name, value
):
    monkeypatch.setenv(name, value)

    with pytest.raises(SystemExit) as stopped:
        load_settings()

    message = str(stopped.value)
    assert name in message
    assert f"{name}={value}" not in message
