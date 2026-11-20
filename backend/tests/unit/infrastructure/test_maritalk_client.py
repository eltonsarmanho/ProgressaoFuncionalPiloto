"""REL-03, REL-05: the shared MariTalk transport against a simulated HTTP transport (no network)."""

import json
import logging

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.ai.maritalk import ChatError, ChatFailure, MariTalkClient

API_KEY = "mk-super-secret-key-0123456789"
BASE = "https://chat.example.test/api"
MESSAGES = [{"role": "system", "content": "regra"}, {"role": "user", "content": "texto"}]
FORMAT = {"type": "json_schema", "json_schema": {"name": "x", "schema": {"type": "object"}}}
PAYLOAD = {"items": [{"id": "a", "texto": "Texto."}]}


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


def ok(body=None):
    text = json.dumps(PAYLOAD if body is None else body)
    choice = {"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
    return httpx.Response(200, json={"choices": [choice]})


class Fixture:
    """Plays the queued outcomes; the fake clock moves only when the client sleeps."""

    def __init__(self, *outcomes, config: Settings | None = None):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []
        self.sleeps: list[float] = []
        self.now = 0.0
        self.client = MariTalkClient(
            config or settings(),
            transport=httpx.MockTransport(self._serve),
            sleep=self._sleep,
            monotonic=lambda: self.now,
        )

    def _serve(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def _sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def body(self, index: int = 0) -> dict:
        return json.loads(self.requests[index].content)

    @property
    def models(self):
        return [self.body(i)["model"] for i in range(len(self.requests))]

    def failure(self, **kwargs) -> ChatFailure:
        with pytest.raises(ChatError) as info:
            self.client.chat(MESSAGES, FORMAT, **kwargs)
        return info.value.failure


def test_chat_posts_the_messages_and_the_schema_with_the_bearer_and_returns_the_content():
    fx = Fixture(ok())

    result = fx.client.chat(MESSAGES, FORMAT, max_tokens=4000)

    request = fx.requests[0]
    assert (request.method, str(request.url)) == ("POST", f"{BASE}/chat/completions")
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert fx.body() == {
        "model": "sabiazinho-4",
        "temperature": 0,
        "max_tokens": 4000,
        "messages": MESSAGES,
        "response_format": FORMAT,
    }
    assert (result.content, result.model) == (PAYLOAD, "sabiazinho-4")


def test_chat_uses_the_configured_token_budget_when_none_is_given():
    fx = Fixture(ok())

    fx.client.chat(MESSAGES, FORMAT)

    assert fx.body()["max_tokens"] == 8000


@pytest.mark.parametrize("status", [400, 404])
def test_a_model_error_repeats_once_with_the_fallback_model(status):
    error = httpx.Response(status, json={"error": {"message": "The model `x` does not exist"}})
    fx = Fixture(error, ok())

    result = fx.client.chat(MESSAGES, FORMAT)

    assert fx.models == ["sabiazinho-4", "sabia-4-br-sp"]
    assert result.model == "sabia-4-br-sp"
    assert fx.sleeps == []


def test_a_second_model_error_is_not_repeated():
    error = httpx.Response(404, json={"error": {"message": "model not found"}})
    fx = Fixture(error, error)

    assert fx.failure() is ChatFailure.UNAVAILABLE
    assert fx.models == ["sabiazinho-4", "sabia-4-br-sp"]


def test_without_a_deadline_a_transient_status_repeats_twice_with_2_and_6_seconds():
    fx = Fixture(*[httpx.Response(503)] * 3)

    assert fx.failure() is ChatFailure.UNAVAILABLE
    assert len(fx.requests) == 3
    assert fx.sleeps == [2, 6]


def test_the_total_deadline_stops_the_repetitions_that_would_not_fit():
    fx = Fixture(*[httpx.Response(503)] * 3)

    assert fx.failure(deadline_seconds=5) is ChatFailure.UNAVAILABLE
    assert len(fx.requests) == 2  # the 6 s wait after the second failure would pass 5 s
    assert fx.sleeps == [2]


def test_a_deadline_already_spent_makes_no_request():
    fx = Fixture(ok())

    assert fx.failure(deadline_seconds=0) is ChatFailure.UNAVAILABLE
    assert fx.requests == []


def test_each_request_waits_at_most_what_is_left_of_the_deadline():
    fx = Fixture(httpx.Response(503), ok())

    fx.client.chat(MESSAGES, FORMAT, deadline_seconds=10)

    reads = [request.extensions["timeout"]["read"] for request in fx.requests]
    assert reads == [10, 8]  # 60 s configured, 2 s spent waiting before the second request


def test_without_a_deadline_the_configured_timeout_applies():
    fx = Fixture(ok())

    fx.client.chat(MESSAGES, FORMAT)

    assert fx.requests[0].extensions["timeout"]["read"] == 60


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_credential_is_not_repeated(status):
    fx = Fixture(httpx.Response(status, json={"error": "denied"}))

    assert fx.failure() is ChatFailure.CREDENTIAL_REFUSED
    assert len(fx.requests) == 1


def test_an_invalid_content_repeats_once_with_a_doubled_budget_then_fails():
    cut = httpx.Response(
        200, json={"choices": [{"message": {"content": "{"}, "finish_reason": "length"}]}
    )
    fx = Fixture(cut, cut)

    assert fx.failure() is ChatFailure.INVALID_RESPONSE
    assert [fx.body(i)["max_tokens"] for i in range(2)] == [8000, 16000]


@pytest.mark.parametrize("missing", ["maritalk_api_key", "maritalk_api_base"])
def test_missing_credentials_are_unavailable_without_any_request(missing):
    fx = Fixture(config=settings(**{missing: None}))

    assert fx.failure() is ChatFailure.UNAVAILABLE
    assert fx.requests == []


def test_the_key_never_appears_in_the_error_the_repr_or_the_logs(caplog):
    caplog.set_level(logging.DEBUG)
    fx = Fixture(httpx.Response(401, text=f"bad key {API_KEY}"))

    with pytest.raises(ChatError) as info:
        fx.client.chat(MESSAGES, FORMAT)

    seen = [str(info.value), repr(info.value), repr(info.value.__context__), repr(fx.client)]
    assert API_KEY not in "\n".join(seen + [caplog.text])
    assert "model=sabiazinho-4" in caplog.text
