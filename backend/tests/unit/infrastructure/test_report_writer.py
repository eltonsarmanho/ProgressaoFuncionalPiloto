"""REL-03, REL-05, REL-06: the MariTalk adapter that words a report section, against a simulated
HTTP transport (no network, no real key)."""

import json
from uuid import uuid4

import httpx
import pytest

from app.domain.entities.generated import GenerationAlertCode
from app.domain.repositories.ports import AiWritingError
from app.domain.rules.report_wording import WordingItem
from app.infrastructure.ai.report_writer import MariTalkReportWriter
from tests.unit.infrastructure.test_maritalk_client import API_KEY, settings

FIRST, SECOND = uuid4(), uuid4()
ITEMS = [
    WordingItem(
        FIRST,
        {
            "tipo": "Orientação de trabalho de conclusão de curso",
            "titulo": "Estudo de redes",
            "datas": "10/03/2024",
            "carga_horaria": "40 h",
        },
    ),
    WordingItem(SECOND, {"titulo": "Projeto de extensão", "periodo_letivo": "2024.1"}),
]


def reply(items):
    content = json.dumps({"items": items})
    choice = {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
    return httpx.Response(200, json={"choices": [choice]})


GOOD = reply(
    [
        {"id": str(FIRST), "texto": "Orientou o trabalho."},
        {"id": str(SECOND), "texto": "Executou."},
    ]
)


class Fixture:
    def __init__(self, *outcomes, **overrides):
        self.outcomes = list(outcomes)
        self.requests: list[httpx.Request] = []
        self.sleeps: list[float] = []
        self.now = 0.0
        self.writer = MariTalkReportWriter(
            settings(**overrides),
            transport=httpx.MockTransport(self._serve),
            sleep=self.sleeps.append,
            monotonic=lambda: self.now,
        )

    def _serve(self, request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if callable(outcome):
            outcome = outcome(self)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def body(self, index=0):
        return json.loads(self.requests[index].content)

    def unavailable(self) -> AiWritingError:
        with pytest.raises(AiWritingError) as info:
            self.writer.draft("Ensino", ITEMS)
        return info.value


def test_a_valid_answer_gives_the_text_of_each_activity_by_id():
    fx = Fixture(GOOD)

    texts = fx.writer.draft("Ensino", ITEMS)

    assert texts == {FIRST: "Orientou o trabalho.", SECOND: "Executou."}


def test_the_request_is_strict_json_at_temperature_zero_with_4000_tokens():
    fx = Fixture(GOOD)

    fx.writer.draft("Ensino", ITEMS)

    body = fx.body()
    assert body["temperature"] == 0
    assert body["max_tokens"] == 4000
    schema = body["response_format"]
    assert schema["type"] == "json_schema" and schema["json_schema"]["strict"] is True
    inner = schema["json_schema"]["schema"]
    assert inner["required"] == ["items"] and inner["additionalProperties"] is False
    item = inner["properties"]["items"]["items"]
    assert item["required"] == ["id", "texto"] and item["additionalProperties"] is False
    assert len(fx.requests) == 1


@pytest.mark.parametrize(
    "outcome",
    [
        httpx.Response(500, text="erro"),
        httpx.Response(429, text="limite"),
        httpx.Response(401, text="sem permissão"),
        httpx.Response(404, text="não achou"),
        httpx.ConnectError("sem rede"),
        httpx.ReadTimeout("lento"),
    ],
)
def test_a_provider_error_is_redacao_indisponivel_with_no_repetition(outcome):
    fx = Fixture(outcome)

    error = fx.unavailable()

    assert error.code is GenerationAlertCode.REDACAO_INDISPONIVEL
    assert len(fx.requests) == 1  # no second try, no wait
    assert fx.sleeps == []
    assert API_KEY not in str(error) and API_KEY not in repr(error)


@pytest.mark.parametrize(
    "items",
    [
        "texto",
        None,
        [{"id": str(FIRST)}],
        [{"id": str(FIRST), "texto": 7}],
        [{"id": "não é um id", "texto": "Texto."}],
        ["solto"],
    ],
)
def test_an_answer_out_of_the_schema_is_redacao_indisponivel(items):
    fx = Fixture(reply(items))

    assert fx.unavailable().code is GenerationAlertCode.REDACAO_INDISPONIVEL
    assert len(fx.requests) == 1


def test_an_answer_that_is_not_json_or_was_cut_short_is_not_repeated():
    choice = {"message": {"content": '{"items": ['}, "finish_reason": "length"}
    cut = httpx.Response(200, json={"choices": [choice]})
    fx = Fixture(cut)

    assert fx.unavailable().code is GenerationAlertCode.REDACAO_INDISPONIVEL
    assert len(fx.requests) == 1


def test_the_backup_model_is_the_only_repetition():
    fx = Fixture(httpx.Response(400, text="model not found"), GOOD)

    texts = fx.writer.draft("Ensino", ITEMS)

    assert texts[FIRST] == "Orientou o trabalho."
    assert [fx.body(i)["model"] for i in range(2)] == ["sabiazinho-4", "sabia-4-br-sp"]


def test_the_call_gives_up_at_the_deadline_of_60_seconds():
    def slow_then_model_error(fx):
        fx.now += 61
        return httpx.Response(400, text="model not found")

    fx = Fixture(slow_then_model_error, GOOD)

    assert fx.unavailable().code is GenerationAlertCode.REDACAO_INDISPONIVEL
    assert len(fx.requests) == 1  # the backup try would have been the second request


def test_the_deadline_is_the_one_of_the_settings():
    def slow(fx):
        fx.now += 6
        return httpx.Response(400, text="model not found")

    fx = Fixture(slow, GOOD, wording_timeout_seconds=5)

    assert fx.unavailable().code is GenerationAlertCode.REDACAO_INDISPONIVEL
    assert len(fx.requests) == 1


def test_only_the_fields_of_the_items_are_sent():
    fx = Fixture(GOOD)

    fx.writer.draft("Ensino", ITEMS)

    messages = fx.body()["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]
    sent = json.loads(messages[1]["content"])
    assert set(sent) == {"secao", "itens"}
    assert sent["secao"] == "Ensino"
    assert sent["itens"] == [item.payload() for item in ITEMS]
    allowed = {"id", "tipo", "titulo", "datas", "carga_horaria", "carga_horaria_curso"}
    allowed |= {"periodo_letivo", "quantidade", "descricao"}
    assert all(set(item) <= allowed for item in sent["itens"])


def test_the_prompt_forbids_objectives_results_and_methodologies_and_new_facts():
    fx = Fixture(GOOD)

    fx.writer.draft("Ensino", ITEMS)

    system = fx.body()["messages"][0]["content"]
    assert "Não escreva objetivos, resultados, metodologias" in system
    assert "somente" in system and "campos" in system
    assert "Não acrescente" in system


def test_a_section_with_no_item_to_word_makes_no_call():
    fx = Fixture()

    assert fx.writer.draft("Ensino", []) == {}
    assert fx.requests == []
