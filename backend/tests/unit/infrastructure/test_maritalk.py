"""EXT-01..06, EXT-09: the MariTalk adapter against a simulated HTTP transport (no network)."""

import json
import logging

import httpx
import pytest

from app.core.config import Settings
from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import DocumentType
from app.domain.repositories.ports import AiExtractionError
from app.infrastructure.ai.maritalk import MariTalkExtractor
from app.infrastructure.ai.schemas import response_format

API_KEY = "mk-super-secret-key-0123456789"
BASE = "https://chat.example.test/api"
TEXT = "[PÁGINA 1]\nDeclaramos que Fulana de Tal Exemplo participou de banca."
PAYLOAD = {"document_type": "DECLARACAO_BANCA", "docente_nome": None, "activities": []}


def settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://u:p@h/db",
        "admin_email": "admin@example.test",
        "admin_password": "admin-pass-for-tests",
        "maritalk_api_key": API_KEY,
        "maritalk_api_base": BASE,
        "maritalk_model": "sabiazinho-4",
        "ai_timeout_seconds": 60,
        "ai_max_tokens": 8000,
    }
    return Settings(_env_file=None, **(values | overrides))


def ok(content=None, finish="stop", **message):
    body = PAYLOAD if content is None else content
    text = body if isinstance(body, str) else json.dumps(body)
    choice = {"message": {"role": "assistant", "content": text, **message}, "finish_reason": finish}
    return httpx.Response(200, json={"choices": [choice]})


def empty_content(finish="stop"):
    message = {"content": "", "reasoning_content": "{}"}
    return httpx.Response(200, json={"choices": [{"message": message, "finish_reason": finish}]})


class Server:
    """Plays the queued responses (or raises the queued exceptions) and records requests."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)

    @property
    def models(self):
        return [self.body(i)["model"] for i in range(len(self.requests))]

    @property
    def budgets(self):
        return [self.body(i)["max_tokens"] for i in range(len(self.requests))]


class Fixture:
    def __init__(self, server: Server, config: Settings | None = None):
        self.server = server
        self.sleeps: list[float] = []
        clock = iter(range(0, 1000, 3))  # 3 s between the two reads
        self.extractor = MariTalkExtractor(
            config or settings(),
            transport=httpx.MockTransport(server),
            sleep=self.sleeps.append,
            monotonic=lambda: next(clock),
        )

    def extract(self, document_type=DocumentType.DECLARACAO_BANCA, text=TEXT, professor=None):
        return self.extractor.extract(document_type, text, professor)


def run(*outcomes, config=None):
    return Fixture(Server(*outcomes), config)


def failure_code(fx: Fixture) -> DocAlertCode:
    with pytest.raises(AiExtractionError) as info:
        fx.extract()
    return info.value.code


def test_posts_to_chat_completions_with_bearer_and_configured_model():
    fx = run(ok())
    fx.extract()
    request = fx.server.requests[0]
    assert request.method == "POST"
    assert str(request.url) == f"{BASE}/chat/completions"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert fx.server.body()["model"] == "sabiazinho-4"


def test_base_with_trailing_slash_does_not_double_the_slash():
    fx = run(ok(), config=settings(maritalk_api_base=BASE + "/"))
    fx.extract()
    assert str(fx.server.requests[0].url) == f"{BASE}/chat/completions"


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_empty_model_setting_uses_sabia_4_br_sp(empty):
    fx = run(ok(), config=settings(maritalk_model=empty))
    fx.extract()
    assert fx.server.models == ["sabia-4-br-sp"]


def test_request_body_has_temperature_zero_tokens_messages_and_schema():
    fx = run(ok())
    fx.extract(DocumentType.ATA_DEFESA)
    body = fx.server.body()
    assert body["temperature"] == 0
    assert body["max_tokens"] == 8000
    assert body["response_format"] == response_format(DocumentType.ATA_DEFESA)
    system, user = body["messages"]
    assert (system["role"], user["role"]) == ("system", "user")
    assert user["content"] == TEXT
    assert "null" in system["content"]
    assert "somente o que está" in system["content"]
    assert "JSON" in system["content"]


def test_returns_parsed_json_model_and_duration():
    fx = run(ok())
    result = fx.extract()
    assert result.raw_json == PAYLOAD
    assert result.model == "sabiazinho-4"
    assert result.duration_ms == 3000


@pytest.mark.parametrize("status", [400, 404])
def test_model_error_retries_once_with_the_fallback_model(status):
    error = httpx.Response(status, json={"error": {"message": "The model `x` does not exist"}})
    fx = run(error, ok())
    result = fx.extract()
    assert fx.server.models == ["sabiazinho-4", "sabia-4-br-sp"]
    assert result.model == "sabia-4-br-sp"
    assert fx.sleeps == []


def test_model_error_on_the_fallback_model_itself_is_not_retried():
    error = httpx.Response(400, json={"error": {"message": "invalid model"}})
    fx = run(error, config=settings(maritalk_model=""))
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert len(fx.server.requests) == 1


def test_model_error_is_retried_only_once():
    error = httpx.Response(404, json={"error": {"message": "model not found"}})
    fx = run(error, error)
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert fx.server.models == ["sabiazinho-4", "sabia-4-br-sp"]


def test_400_that_is_not_about_the_model_is_not_retried():
    fx = run(httpx.Response(400, json={"error": {"message": "messages is too long"}}))
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert len(fx.server.requests) == 1


@pytest.mark.parametrize("status", [401, 403])
def test_credential_refused_is_not_retried(status):
    fx = run(httpx.Response(status, json={"error": "denied"}))
    assert failure_code(fx) is DocAlertCode.IA_CREDENCIAL_RECUSADA
    assert len(fx.server.requests) == 1
    assert fx.sleeps == []


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_status_retries_twice_with_2_and_6_seconds_then_fails(status):
    fx = run(*[httpx.Response(status)] * 3)
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert len(fx.server.requests) == 3
    assert fx.sleeps == [2, 6]


def test_transient_failure_then_success_returns_the_result():
    fx = run(httpx.Response(503), httpx.Response(429), ok())
    assert fx.extract().raw_json == PAYLOAD
    assert fx.sleeps == [2, 6]


def test_timeout_retries_twice_then_fails():
    timeout = httpx.ReadTimeout("slow")
    fx = run(timeout, timeout, timeout)
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert fx.sleeps == [2, 6]
    assert len(fx.server.requests) == 3


def test_connection_error_retries_twice_then_fails():
    error = httpx.ConnectError("refused")
    fx = run(error, error, error)
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert fx.sleeps == [2, 6]


def test_other_4xx_is_unavailable_without_retry():
    fx = run(httpx.Response(422, json={"error": "bad"}))
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert len(fx.server.requests) == 1
    assert fx.sleeps == []


def test_timeout_setting_is_passed_to_the_http_client():
    fx = run(ok(), config=settings(ai_timeout_seconds=17))
    assert fx.extractor._client.timeout == httpx.Timeout(17)


@pytest.mark.parametrize("first", ["empty", "none", "length"])
def test_empty_or_cut_response_retries_with_a_doubled_token_budget(first):
    responses = {
        "empty": empty_content(),
        "none": httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
        "length": ok(finish="length"),
    }
    fx = run(responses[first], ok())
    result = fx.extract()
    assert fx.server.budgets == [8000, 16000]
    assert result.raw_json == PAYLOAD
    assert fx.sleeps == []


def test_invalid_response_twice_raises_resposta_invalida():
    fx = run(empty_content(), empty_content("length"))
    assert failure_code(fx) is DocAlertCode.RESPOSTA_INVALIDA
    assert fx.server.budgets == [8000, 16000]


@pytest.mark.parametrize("content", ["isto nao e json", "[1, 2]", '"texto"', "{"])
def test_content_that_is_not_a_json_object_is_an_invalid_response(content):
    fx = run(ok(content), ok(content))
    assert failure_code(fx) is DocAlertCode.RESPOSTA_INVALIDA


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{}]}, {"choices": [None]}])
def test_malformed_body_is_an_invalid_response(body):
    fx = run(httpx.Response(200, json=body), httpx.Response(200, json=body))
    assert failure_code(fx) is DocAlertCode.RESPOSTA_INVALIDA


def test_response_that_is_not_json_is_an_invalid_response():
    fx = run(httpx.Response(200, text="<html>"), httpx.Response(200, text="<html>"))
    assert failure_code(fx) is DocAlertCode.RESPOSTA_INVALIDA


def test_reasoning_content_is_never_read():
    reasoning = {"document_type": "OUTRO", "docente_nome": "do raciocinio", "activities": []}
    result = run(ok(reasoning_content=json.dumps(reasoning))).extract()
    assert result.raw_json == PAYLOAD
    assert "raciocinio" not in json.dumps(result.raw_json)


def test_empty_content_is_invalid_even_when_reasoning_content_has_json():
    fx = run(empty_content(), empty_content())
    assert failure_code(fx) is DocAlertCode.RESPOSTA_INVALIDA


def test_retry_kinds_are_counted_independently():
    model_error = httpx.Response(400, json={"error": "unknown model"})
    fx = run(httpx.Response(500), model_error, empty_content(), ok())
    result = fx.extract()
    assert fx.server.models == ["sabiazinho-4", "sabiazinho-4", "sabia-4-br-sp", "sabia-4-br-sp"]
    assert fx.server.budgets == [8000, 8000, 8000, 16000]
    assert fx.sleeps == [2]
    assert result.model == "sabia-4-br-sp"


@pytest.mark.parametrize("missing", ["maritalk_api_key", "maritalk_api_base"])
def test_missing_credentials_are_unavailable_without_any_request(missing):
    fx = run(config=settings(**{missing: None}))
    assert failure_code(fx) is DocAlertCode.IA_INDISPONIVEL
    assert fx.server.requests == []


SCENARIOS = {
    "success": [ok()],
    "credential": [httpx.Response(401, text=f"bad key {API_KEY}")],
    "unavailable": [httpx.Response(503, text=f"oops {API_KEY}")] * 3,
    "timeout": [httpx.ReadTimeout("slow")] * 3,
    "invalid": [empty_content(), empty_content()],
    "other_4xx": [httpx.Response(422, text=API_KEY)],
}


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_the_key_never_appears_in_errors_repr_logs_or_output(scenario, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    fx = run(*SCENARIOS[scenario])
    seen = []
    try:
        fx.extract()
    except AiExtractionError as error:
        seen += [str(error), repr(error), repr(error.__cause__), repr(error.__context__)]
        seen += [error.code.value]
    seen += [repr(fx.extractor), repr(settings()), str(settings())]
    out = capsys.readouterr()
    haystack = "\n".join(seen + [caplog.text, out.out, out.err])
    assert API_KEY not in haystack
    assert "mk-super-secret" not in haystack


def test_logs_carry_the_model_and_status_but_no_document_text(caplog):
    caplog.set_level(logging.DEBUG)
    run(ok()).extract()
    assert "model=sabiazinho-4" in caplog.text
    assert "status=200" in caplog.text
    assert "Fulana" not in caplog.text


# --- the professor goes in the prompt (REAL-01) -------------------------------------------


def test_prompt_names_the_professor_of_the_process():
    fx = run(ok())
    fx.extract(professor="Fulana  de Tal Exemplo")
    system = fx.server.body()["messages"][0]["content"]
    assert "O docente deste processo se chama Fulana de Tal Exemplo." in system
    assert "discentes" in system and "não são o docente" in system


@pytest.mark.parametrize("name", [None, "", "   "])
def test_prompt_without_a_professor_name_has_no_professor_sentence(name):
    fx = run(ok())
    fx.extract(professor=name)
    assert "O docente deste processo" not in fx.server.body()["messages"][0]["content"]


def test_professor_name_with_braces_is_sent_literally():
    fx = run(ok())
    fx.extract(professor="Fulana {x} Exemplo")
    assert "se chama Fulana {x} Exemplo." in fx.server.body()["messages"][0]["content"]


def test_professor_name_is_only_in_the_system_prompt_and_nothing_else_is_added():
    fx = run(ok())
    fx.extract(professor="Fulana de Tal Exemplo")
    body = fx.server.body()
    assert body["messages"][1]["content"] == TEXT
    assert API_KEY not in json.dumps(body)


def test_prompt_tells_the_model_not_to_return_dismissals_as_activities():
    fx = run(ok())
    fx.extract()
    system = fx.server.body()["messages"][0]["content"]
    assert "dispensam, exoneram ou destituem" in system
    assert "não são atividades" in system
