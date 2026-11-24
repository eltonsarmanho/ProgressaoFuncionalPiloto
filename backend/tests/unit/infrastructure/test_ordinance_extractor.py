"""PORT-02, PORT-04: the MariTalk adapter that reads the ordinance of the board, against a
simulated HTTP transport (no network, no real key)."""

import json
import logging
from datetime import date

import httpx
import pytest

from app.domain.entities.board import OrdinanceReadingCode
from app.domain.repositories.ports import OrdinanceExtractionError
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from app.infrastructure.ai.ordinance_extractor import MariTalkOrdinanceExtractor
from tests.unit.infrastructure.test_maritalk_client import API_KEY, settings

TEXT = "[PÁGINA 1]\nPORTARIA Nº 12/2025\n10 de março de 2025\nFulana de Tal, Presidente"

ANSWER = {
    "number": "12/2025",
    "number_page": 1,
    "ordinance_date": "2025-03-10",
    "date_page": 1,
    "members": [
        {"name": "Fulana de Tal", "role": "PRESIDENTE", "page": 1},
        {"name": "Beltrano Souza", "role": "SUPLENTE", "page": 2},
    ],
}


def reply(content, finish="stop"):
    text = content if isinstance(content, str) else json.dumps(content)
    choice = {"message": {"role": "assistant", "content": text}, "finish_reason": finish}
    return httpx.Response(200, json={"choices": [choice]})


class Fixture:
    def __init__(self, *outcomes, **overrides):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []
        self.now = 0.0
        self.extractor = MariTalkOrdinanceExtractor(
            settings(**overrides),
            transport=httpx.MockTransport(self._serve),
            sleep=self._sleep,
            monotonic=lambda: self.now,
        )

    def _serve(self, request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def _sleep(self, seconds):
        self.now += seconds

    def body(self, index=0):
        return json.loads(self.requests[index].content)

    def error(self) -> OrdinanceExtractionError:
        with pytest.raises(OrdinanceExtractionError) as info:
            self.extractor.extract(TEXT)
        return info.value


def test_a_valid_answer_becomes_the_ordinance_with_the_pages():
    fx = Fixture(reply(ANSWER))

    result = fx.extractor.extract(TEXT)

    assert result == OrdinanceAi(
        number="12/2025",
        number_page=1,
        ordinance_date=date(2025, 3, 10),
        date_page=1,
        members=(
            OrdinanceAiMember("Fulana de Tal", "PRESIDENTE", 1),
            OrdinanceAiMember("Beltrano Souza", "SUPLENTE", 2),
        ),
    )


def test_a_value_the_text_does_not_give_comes_back_null_and_stays_empty():
    nothing = {
        "number": None,
        "number_page": None,
        "ordinance_date": None,
        "date_page": None,
        "members": [],
    }
    fx = Fixture(reply(nothing))

    assert fx.extractor.extract(TEXT) == OrdinanceAi()


def test_the_request_is_strict_json_with_every_property_required_and_nothing_extra():
    fx = Fixture(reply(ANSWER))

    fx.extractor.extract(TEXT)

    body = fx.body()
    envelope = body["response_format"]
    assert envelope["type"] == "json_schema" and envelope["json_schema"]["strict"] is True
    schema = envelope["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert set(schema["properties"]) == {
        "number",
        "number_page",
        "ordinance_date",
        "date_page",
        "members",
    }
    member = schema["properties"]["members"]["items"]
    assert member["additionalProperties"] is False
    assert set(member["required"]) == {"name", "role", "page"}
    assert member["properties"]["role"]["enum"] == ["PRESIDENTE", "MEMBRO", "SUPLENTE"]
    assert body["temperature"] == 0


def test_the_user_message_is_exactly_the_text_received():
    fx = Fixture(reply(ANSWER))

    fx.extractor.extract(TEXT)

    messages = fx.body()["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[1]["content"] == TEXT


def test_the_prompt_tells_the_model_to_copy_only_what_the_text_says():
    fx = Fixture(reply(ANSWER))

    fx.extractor.extract(TEXT)

    system = fx.body()["messages"][0]["content"]
    assert "somente o que está escrito" in system
    assert "não invente" in system
    assert "null" in system
    assert "[PÁGINA n]" in system
    assert "AAAA-MM-DD" in system


@pytest.mark.parametrize(
    "answer",
    [
        {**ANSWER, "extra": 1},
        {k: v for k, v in ANSWER.items() if k != "date_page"},
        {**ANSWER, "members": [{"name": "A B", "role": "DIRETOR", "page": 1}]},
        {**ANSWER, "members": [{"name": "A B", "role": "MEMBRO"}]},
        {**ANSWER, "members": [{"name": "A B", "role": "MEMBRO", "page": 1, "x": 1}]},
        {**ANSWER, "members": [{"name": 7, "role": "MEMBRO", "page": 1}]},
        {**ANSWER, "number": 12},
        {**ANSWER, "number_page": "1"},
        {**ANSWER, "members": "ninguém"},
        {**ANSWER, "ordinance_date": "10/03/2025"},
        {**ANSWER, "ordinance_date": "2025-02-30"},
        ["não é objeto"],
    ],
)
def test_an_answer_out_of_the_schema_is_resposta_invalida(answer):
    fx = Fixture(reply(answer), reply(answer))

    error = fx.error()

    assert error.code is OrdinanceReadingCode.RESPOSTA_INVALIDA


def test_an_answer_that_is_not_json_is_resposta_invalida():
    fx = Fixture(reply("não é json"), reply("não é json"))

    assert fx.error().code is OrdinanceReadingCode.RESPOSTA_INVALIDA


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_credential_is_ia_credencial_recusada(status):
    fx = Fixture(httpx.Response(status, text="sem permissão"))

    assert fx.error().code is OrdinanceReadingCode.IA_CREDENCIAL_RECUSADA


@pytest.mark.parametrize(
    "outcome",
    [httpx.Response(500, text="erro"), httpx.ConnectError("sem rede"), httpx.ReadTimeout("lento")],
)
def test_a_network_error_a_server_error_and_a_timeout_are_ia_indisponivel(outcome):
    fx = Fixture(*[outcome] * 3)

    assert fx.error().code is OrdinanceReadingCode.IA_INDISPONIVEL


def test_without_a_key_the_ai_is_unavailable_and_no_request_goes_out():
    fx = Fixture(maritalk_api_key=None)

    assert fx.error().code is OrdinanceReadingCode.IA_INDISPONIVEL
    assert fx.requests == []


def test_the_key_is_only_in_the_authorization_header_never_in_the_error_repr_or_logs(caplog):
    caplog.set_level(logging.DEBUG)
    fx = Fixture(httpx.Response(401, text=f"bad key {API_KEY}"))

    error = fx.error()

    assert fx.requests[0].headers["Authorization"] == f"Bearer {API_KEY}"
    assert API_KEY not in fx.requests[0].content.decode()
    seen = [str(error), repr(error), repr(error.__cause__), repr(error.__context__)]
    seen += [repr(fx.extractor), caplog.text]
    assert API_KEY not in "\n".join(seen)
