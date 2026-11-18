"""REL-03, REL-04, REL-05, REL-07, REL-09, REL-13 (T92): the report wording flow through the API
with a simulated MariTalk (no network, no real key).

The adapter, the grounding check and the template fallback are the real ones; only the HTTP
transport is simulated. Two orientations of the section 1.3 are answered, one faithfully and one
with an invented number.
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.ai.report_writer import MariTalkReportWriter
from tests.integration.api.generated_readers import docx_text, pdf_text
from tests.integration.api.generated_support import (
    add_activity,
    choose_table,
    file_url,
    generate,
    process_url,
)

SECTION = "1.3"
FAITHFUL = "Orientação da monografia sobre redes, concluída em 10/05/2023."
INVENTED = "Orientação da monografia sobre bancos com 40 horas, em 10/05/2023."
EDITED = "Texto escrito pelo docente sobre a monografia de redes."


class FakeMariTalk:
    """The HTTP side of the provider: answers each request from `answer(items)`, which maps the
    items the adapter sent to the texts, or fails with the exception it returns."""

    def __init__(self, answer):
        self.answer = answer
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        user = json.loads(body["messages"][-1]["content"])
        self.requests.append(user)
        outcome = self.answer(user["itens"])
        if isinstance(outcome, Exception):
            raise outcome
        content = json.dumps({"items": [{"id": i, "texto": t} for i, t in outcome.items()]})
        choice = {"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        return httpx.Response(200, json={"choices": [choice]})


def connect(client, fake: FakeMariTalk) -> None:
    """Puts the simulated provider under the real adapter of the wording runner."""
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://u:p@h/db",
        admin_email="admin@example.test",
        admin_password="admin-pass-for-tests",
        maritalk_api_key="chave-sintetica-de-teste",
        maritalk_api_base="https://maritalk.invalid/api",
        maritalk_model="sabiazinho-4",
    )
    client.app.state.container.run_wording._writer = MariTalkReportWriter(
        settings, transport=httpx.MockTransport(fake), sleep=lambda _: None
    )


def by_title(items: list[dict], title: str) -> dict:
    return next(i for i in items if i["titulo"] == title)


@pytest.fixture
def world(client, admin, process, scoring_tables):
    headers = admin[1]
    choose_table(client, headers, process, scoring_tables["OFICIAL"])
    redes = add_activity(client, headers, process, title="Monografia sobre redes", item_number=7)
    bancos = add_activity(client, headers, process, title="Monografia sobre bancos", item_number=8)
    return SimpleNamespace(process=process, headers=headers, redes=redes, bancos=bancos)


def draft_url(world, tail=""):
    return process_url(world.process, "report-draft" + tail)


def ask_wording(client, world):
    response = client.post(draft_url(world, f"/sections/{SECTION}/wording"), headers=world.headers)
    assert response.status_code == 202, response.text
    return response.json()


def wait_wording(client, world) -> dict:
    """What the executor does for the waiting job, and the job it closed."""
    assert client.app.state.container.run_wording.run_next() is True
    [job] = [
        j for j in client.get(draft_url(world, "/wording")).json() if j["section_key"] == SECTION
    ]
    return job


def version_of(client, world) -> int:
    """The version of the draft now: the first wording request saved the proposal as version 1."""
    return client.get(draft_url(world)).json()["version"]


def entries(client, world) -> dict:
    section = next(
        s for s in client.get(draft_url(world)).json()["sections"] if s["key"] == SECTION
    )
    return {e["activity_id"]: e for e in section["entries"]}, section


def answers(world):
    def answer(items):
        return {
            by_title(items, "Monografia sobre redes")["id"]: FAITHFUL,
            by_title(items, "Monografia sobre bancos")["id"]: INVENTED,
        }

    return answer


def test_an_invented_number_becomes_the_template_text_and_the_faithful_one_is_accepted(
    client, world
):
    fake = FakeMariTalk(answers(world))
    connect(client, fake)

    waiting = ask_wording(client, world)
    job = wait_wording(client, world)

    assert waiting["state"] == "GERANDO" and waiting["section_key"] == SECTION
    assert (job["state"], [w["code"] for w in job["warnings"]]) == ("PRONTO", ["REDACAO_REJEITADA"])
    by_activity, section = entries(client, world)
    good, bad = by_activity[world.redes["id"]], by_activity[world.bancos["id"]]
    assert (good["text"], good["source"]) == (FAITHFUL, "IA")
    assert (bad["source"], "Monografia sobre bancos" in bad["text"], "40 horas" in bad["text"]) == (
        "MODELO",
        True,
        False,
    )
    assert [w["code"] for w in section["warnings"]] == ["REDACAO_REJEITADA"]


def test_an_unavailable_provider_closes_the_job_ready_with_the_alert_and_the_template_text(
    client, world
):
    before, _ = entries(client, world)
    connect(client, FakeMariTalk(lambda items: httpx.ConnectError("sem rede")))

    ask_wording(client, world)
    job = wait_wording(client, world)

    assert (job["state"], [w["code"] for w in job["warnings"]]) == (
        "PRONTO",
        ["REDACAO_INDISPONIVEL"],
    )
    after, section = entries(client, world)
    assert after == before  # every entry is still the template text
    assert {e["source"] for e in after.values()} == {"MODELO"}
    assert [w["code"] for w in section["warnings"]] == ["REDACAO_INDISPONIVEL"]
    assert client.get(draft_url(world)).status_code == 200  # the draft stays usable


def test_the_edited_text_stays_after_a_new_wording_and_is_not_sent_to_the_provider(client, world):
    fake = FakeMariTalk(answers(world))
    connect(client, fake)
    ask_wording(client, world)
    wait_wording(client, world)
    edit = client.put(
        draft_url(world, f"/entries/{world.redes['id']}"),
        json={"expected_version": version_of(client, world), "text": EDITED},
        headers=world.headers,
    )
    assert edit.status_code == 200, edit.text

    ask_wording(client, world)
    wait_wording(client, world)

    by_activity, _ = entries(client, world)
    assert (by_activity[world.redes["id"]]["text"], by_activity[world.redes["id"]]["source"]) == (
        EDITED,
        "USUARIO",
    )
    second_call = fake.requests[-1]["itens"]
    assert [i["titulo"] for i in second_call] == ["Monografia sobre bancos"]


def test_a_second_ask_while_the_section_is_waiting_is_409_and_the_other_sections_stay_editable(
    client, world
):
    connect(client, FakeMariTalk(answers(world)))
    ask_wording(client, world)

    second = client.post(draft_url(world, f"/sections/{SECTION}/wording"), headers=world.headers)
    other = client.put(
        draft_url(world, "/sections/6"),
        json={"expected_version": version_of(client, world), "free_text": "Texto livre da seção 6"},
        headers=world.headers,
    )

    assert (second.status_code, second.json()["code"]) == (409, "REDACAO_EM_ANDAMENTO")
    assert other.status_code == 200


def test_the_generated_report_has_the_stored_texts_and_never_the_rejected_one(client, world):
    connect(client, FakeMariTalk(answers(world)))
    ask_wording(client, world)
    wait_wording(client, world)
    client.put(
        draft_url(world, f"/entries/{world.redes['id']}"),
        json={"expected_version": version_of(client, world), "text": EDITED},
        headers=world.headers,
    )
    template_text = " ".join(entries(client, world)[0][world.bancos["id"]]["text"].split())

    row = generate(client, world.headers, world.process, "RELATORIO")

    for extension, read in (("docx", docx_text), ("pdf", pdf_text)):
        text = read(client.get(file_url(row, extension)).content)
        assert EDITED in text, extension
        assert template_text in text, extension
        assert INVENTED not in text and "40 horas" not in text, extension
        assert FAITHFUL not in text, extension  # replaced by the text the user wrote
