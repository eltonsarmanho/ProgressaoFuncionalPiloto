"""ACC-04: opt-in contract test against the real MariTalk API (marker `maritalk_live`).

Not part of the default suite: it needs RUN_LIVE_MARITALK=1 and the credentials
MARITALK_API_KEY and MARITALK_API_BASE (MARITALK_MODEL is optional) in the environment or in the
repository `.env`. Run it with:

    RUN_LIVE_MARITALK=1 .venv/bin/pytest tests/live -m maritalk_live -q

It sends one request per model (the configured one and `sabia-4-thinking`, which share a request
when they are the same) with a synthetic text and the strict json_schema the application uses, and
checks the contract the adapter depends on. The key and the prompt are never logged or asserted
into a failure message.
"""

import json
import os
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.domain.entities.extraction import DocumentType
from app.infrastructure.ai.maritalk import MariTalkExtractor
from app.infrastructure.ai.schemas import ACTIVITY_FIELD_NAMES
from tests.support.corpus_script import REPO_ROOT, load

FLAG = "RUN_LIVE_MARITALK"
THINKING_MODEL = "sabia-4-thinking"
REQUEST_TIMEOUT_SECONDS = 180
# The datum the text lacks: no date and no hours are written anywhere in it.
SYNTHETIC_PAGE = (
    "[PÁGINA 1]\n"
    "DECLARACAO DE BANCA EXAMINADORA\n"
    "Declaramos que Fulana de Tal Exemplo participou como membro da banca examinadora do "
    "trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos, na Faculdade Exemplo "
    "de Testes."
)

pytestmark = [
    pytest.mark.maritalk_live,
    pytest.mark.skipif(os.environ.get(FLAG) != "1", reason=f"opt-in: set {FLAG}=1"),
]


def _environment() -> dict[str, str]:
    return {**load().load_env_file(REPO_ROOT / ".env"), **os.environ}


def _models() -> list[str]:
    configured = _environment().get("MARITALK_MODEL", "").strip() or "sabia-4-br-sp"
    return list(dict.fromkeys([configured, THINKING_MODEL]))


@pytest.fixture(scope="module")
def settings() -> Settings:
    env = _environment()
    key, base = (env.get("MARITALK_API_KEY") or "").strip(), (env.get("MARITALK_API_BASE") or "")
    if not key or not base.strip():
        pytest.skip("MARITALK_API_KEY and MARITALK_API_BASE are required")
    return Settings(
        database_url="postgresql+psycopg://unused",
        admin_email="live@test.invalid",
        admin_password=SecretStr("not-used-by-this-test"),
        maritalk_api_key=SecretStr(key),
        maritalk_api_base=base.strip(),
        maritalk_model=env.get("MARITALK_MODEL", "").strip() or None,
    )


@pytest.fixture(scope="module", params=_models())
def answer(request, settings: Settings) -> dict[str, Any]:
    """One real request per model, shared by the assertions below."""
    # The body is the one the adapter sends: same system prompt, schema and token budget.
    body = MariTalkExtractor._body(
        DocumentType.DECLARACAO_BANCA, SYNTHETIC_PAGE, request.param, settings.ai_max_tokens
    )
    assert settings.maritalk_api_key is not None
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = client.post(
            f"{(settings.maritalk_api_base or '').rstrip('/')}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {settings.maritalk_api_key.get_secret_value()}"},
        )
    result: dict[str, Any] = {"model": request.param, "status": response.status_code}
    if response.status_code == 200:
        choice = response.json()["choices"][0]
        result["finish_reason"] = choice.get("finish_reason")
        result["content"] = choice["message"].get("content")
    return result


def test_strict_json_schema_request_is_accepted(answer):
    assert answer["status"] == 200, f"model {answer['model']}"


def test_max_tokens_leaves_room_for_the_answer_after_the_reasoning(answer):
    assert answer["status"] == 200
    assert answer["finish_reason"] != "length", f"model {answer['model']}"
    assert isinstance(answer["content"], str) and answer["content"].strip() != ""


def test_synthetic_text_is_extracted_with_the_strict_shape_and_null_for_the_missing_datum(answer):
    assert answer["status"] == 200
    parsed = json.loads(answer["content"])

    assert set(parsed) == {"document_type", "docente_nome", "activities"}
    assert len(parsed["activities"]) >= 1
    for found in parsed["activities"]:
        assert set(found) == set(ACTIVITY_FIELD_NAMES)
        for missing in ("start_date", "end_date", "event_date", "hours", "course_hours"):
            assert found[missing] is None, f"{missing} was not null (model {answer['model']})"
