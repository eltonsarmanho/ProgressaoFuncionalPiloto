"""EXT-06, PIPE-10, CLS-03, VINC-04, REV-03 and the batch edge case (T41): the documents flow.

End to end through the API: real upload, real worker loop, real analyzer with real Tesseract
for the scanned files, and the real MariTalk adapter over a simulated HTTP transport (no network,
no real key). The key is a fake secret that must never leave the backend.
"""

import json
import logging
import uuid
from decimal import Decimal

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.ai.maritalk import MariTalkExtractor
from app.infrastructure.jobs.worker import DocumentWorker
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import files_of
from tests.integration.api.factories import process_payload
from tests.support import synthetic_docs as synth
from tests.unit.application.analyzer_fakes import activity, payload

API_KEY = "mk-fake-secret-for-the-flow-test-0123456789"
BASE = "https://chat.example.test/api"
PROFESSOR = "Maria Docente da Silva"

BANCA = (
    "DECLARACAO DE BANCA EXAMINADORA\n"
    f"Declaramos que {PROFESSOR}, matricula SIAPE 1234567, participou como membro da banca "
    "examinadora do trabalho de conclusao de curso Estudo Ficticio sobre Dados Abertos, "
    "realizada em 12 de marco de 2023, na Faculdade Exemplo de Testes."
)
BANCA_INVENTED_DATE = (
    "DECLARACAO DE BANCA EXAMINADORA\n"
    f"Declaramos que {PROFESSOR}, matricula SIAPE 1234567, participou como membro da banca "
    "examinadora do trabalho de conclusao de curso Modelos Ficticios de Aprendizado, "
    "realizada em 15 de maio de 2023, na Faculdade Exemplo de Testes."
)
VISITA = (
    "ATESTADO DE VISITA TECNICA\n"
    f"Atestamos que {PROFESSOR} acompanhou a visita tecnica ao laboratorio Exemplo em "
    "10 de abril de 2023."
)
COORIENTACAO = (
    "DECLARACAO DE COORIENTACAO\n"
    f"Declaramos que {PROFESSOR} coorientou o trabalho de conclusao de curso de graduacao "
    "Analise Ficticia de Redes, defendido em 20 de junho de 2023."
)
INVENTED = "2019-07-04"


def flat(text: str) -> str:
    """The text on one line: PDF text boxes and OCR break lines where the page does."""
    return " ".join(text.split())


class MariTalkServer:
    """Plays the AI by the text it receives; records every request."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        text = flat(json.loads(request.content)["messages"][-1]["content"]).lower()
        if "atestamos" in text:
            answer = payload(
                activity(taxonomy="OUTRA", title="Visita tecnica ao laboratorio Exemplo",
                         role=None, event_date="2023-04-10",
                         evidence_text="acompanhou a visita tecnica"),
                name=None, document_type="OUTRO",
            )  # fmt: skip
        elif "coorientou" in text:
            answer = payload(
                activity(taxonomy="COORIENTACAO_TCC_GRADUACAO", title="Analise Ficticia de Redes",
                         role="coorientador", event_date="2023-06-20",
                         evidence_text="coorientou o trabalho de conclusao"),
                name=None, document_type="DECLARACAO_ORIENTACAO",
            )  # fmt: skip
        elif "modelos ficticios" in text:  # the AI invents a date that is not in the document
            answer = payload(
                activity(title="Modelos Ficticios de Aprendizado", event_date=INVENTED),
                name=PROFESSOR,
            )
        else:
            answer = payload(activity(event_date="2023-03-12"), name=PROFESSOR)
        choice = {"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}
        return httpx.Response(200, json={"choices": [choice]})


@pytest.fixture
def ai():
    return MariTalkServer()


@pytest.fixture
def case(make_client, migrated_url, ai, admin, professor, scoring_tables):
    """(client, CSRF headers, process): an app whose AI is the simulated MariTalk server.

    The process has the FASI table chosen, so the suggested item exists in it.
    """
    settings = Settings(
        _env_file=None,
        database_url=migrated_url,
        admin_email="admin@ufpa.br",
        admin_password="admin-password-1",
        maritalk_api_key=API_KEY,
        maritalk_api_base=BASE,
        maritalk_model="sabiazinho-4",
    )
    extractor = MariTalkExtractor(settings, transport=httpx.MockTransport(ai))
    client = make_client(ai_extractor=extractor, maritalk_api_key=API_KEY, maritalk_api_base=BASE)
    headers = {"X-CSRF-Token": login(client, "admin@ufpa.br")}
    created = client.post("/api/processes", json=process_payload(professor), headers=headers)
    assert created.status_code == 201, created.text
    process = created.json()
    chosen = client.put(
        f"/api/processes/{process['id']}/scoring/table",
        json={"version_id": str(scoring_tables["OFICIAL"].id)},
        headers=headers,
    )
    assert chosen.status_code == 200, chosen.text
    return client, headers, process


def drain(client) -> int:
    """What the background worker does: process jobs until the queue is idle."""
    c = client.app.state.container
    worker = DocumentWorker(c.uow_factory, c.process_document, c.recover_stuck_jobs, c.clock)
    ran = 0
    while worker.run_once():
        ran += 1
    return ran


def upload(client, headers, process, *files):
    response = client.post(
        f"/api/processes/{process['id']}/documents", files=files_of(*files), headers=headers
    )
    assert response.status_code == 201, response.text
    return [r["document"] for r in response.json()]


def detail(client, document):
    response = client.get(f"/api/documents/{document['id']}")
    assert response.status_code == 200, response.text
    return response.json()


def activities(client, process):
    return client.get(f"/api/processes/{process['id']}/activities").json()


def score(client, process):
    return client.get(f"/api/processes/{process['id']}/scoring").json()


def alert_codes(document_detail):
    return [a["code"] for a in document_detail["alerts"]]


def text_pdf(text):
    return synth.pdf_with_text([text])


# --- the three kinds of file, read page by page ----------------------------------------------


def test_a_text_pdf_a_scanned_pdf_and_a_png_are_read_with_the_right_method_per_page(case):
    client, headers, process = case

    text, scanned, image = upload(
        client,
        headers,
        process,
        ("texto.pdf", text_pdf(BANCA)),
        ("digitalizado.pdf", synth.pdf_scanned([VISITA]), "application/pdf"),
        ("imagem.png", synth.png_with_text(COORIENTACAO), "image/png"),
    )
    assert drain(client) == 3

    [text_page] = detail(client, text)["pages"]
    assert text_page["method"] == "TEXTO"
    assert text_page["ocr_confidence"] is None
    assert "participou como membro da banca examinadora" in flat(text_page["text"])
    for document, words in ((scanned, ("atestado", "visita", "tecnica")),
                            (image, ("declaracao", "coorientacao", "graduacao"))):  # fmt: skip
        [page] = detail(client, document)["pages"]
        assert page["page_number"] == 1
        assert page["method"] == "OCR"
        assert Decimal(page["ocr_confidence"]) > 60
        assert all(word in flat(page["text"]).lower() for word in words)
    assert {detail(client, d)["status"] for d in (text, scanned, image)} == {"PROCESSADO"}


# --- the draft activity ------------------------------------------------------------------------


def test_a_banca_declaration_becomes_a_draft_linked_to_document_page_and_excerpt(case):
    client, headers, process = case
    [document] = upload(client, headers, process, ("banca.pdf", text_pdf(BANCA)))

    drain(client)

    body = detail(client, document)
    assert body["status"] == "PROCESSADO"
    assert body["suggested_type"] == "DECLARACAO_BANCA"
    assert body["suggested_category"] == "BANCA_TCC_GRADUACAO"
    [draft] = activities(client, process)
    assert draft["source"] == "SUGERIDA_IA"
    assert draft["status"] == "AGUARDANDO_REVISAO"
    assert (draft["group_number"], draft["item_number"]) == (3, 4)
    assert draft["title"] == "Estudo Ficticio sobre Dados Abertos"
    assert draft["event_date"] == "2023-03-12"
    [evidence] = draft["evidences"]
    assert evidence["document_id"] == document["id"]
    assert evidence["document_name"] == "banca.pdf"
    assert evidence["page"] == 1
    assert "participou como membro da banca examinadora" in flat(evidence["excerpt"])
    assert [a["id"] for a in body["activities"]] == [draft["id"]]
    row = next(r for r in score(client, process)["rows"] if r["title"] == draft["title"])
    assert row["evidence_count"] == 1
    assert "SEM_COMPROVANTE" not in [a["code"] for a in row["alerts"]]


def test_the_ai_that_invents_a_date_is_caught_and_the_date_never_reaches_the_activity(case):
    client, headers, process = case
    [document] = upload(client, headers, process, ("inventada.pdf", text_pdf(BANCA_INVENTED_DATE)))

    drain(client)

    body = detail(client, document)
    assert body["run"]["raw_json"]["activities"][0]["event_date"] == INVENTED  # raw, read only
    [warning] = [a for a in body["alerts"] if a["code"] == "NAO_ENCONTRADO_NO_TEXTO"]
    assert warning["field"] == "event_date"
    [draft] = activities(client, process)
    assert draft["event_date"] is None
    assert INVENTED not in json.dumps(draft)


# --- documents without an item and the TCC co-advising -------------------------------------------


def test_documents_without_an_item_and_the_tcc_coadvising_create_no_activity(case):
    client, headers, process = case
    banca, visita, coorientacao = upload(
        client,
        headers,
        process,
        ("banca.pdf", text_pdf(BANCA)),
        ("visita.pdf", text_pdf(VISITA)),
        ("coorientacao.pdf", text_pdf(COORIENTACAO)),
    )

    assert drain(client) == 3

    [only] = activities(client, process)
    assert only["title"] == "Estudo Ficticio sobre Dados Abertos"
    assert detail(client, banca)["alerts"] == []
    for document in (visita, coorientacao):
        body = detail(client, document)
        assert body["status"] == "PROCESSADO"
        assert body["suggested_category"] == "SEM_ITEM_DE_PONTUACAO"
        assert "SEM_ITEM_DE_PONTUACAO" in alert_codes(body)
        assert body["activities"] == []
        assert body["pages"][0]["text"]  # the text and the extracted data stay available
        assert body["run"]["raw_json"]["activities"]


# --- review and score ----------------------------------------------------------------------------


def test_nothing_is_validated_by_the_processing_and_validating_in_batch_changes_the_total(case):
    client, headers, process = case
    upload(
        client,
        headers,
        process,
        ("banca.pdf", text_pdf(BANCA)),
        ("outra.pdf", text_pdf(BANCA_INVENTED_DATE)),
    )
    drain(client)
    drafts = activities(client, process)
    before = score(client, process)

    assert [d["status"] for d in drafts] == ["AGUARDANDO_REVISAO"] * 2
    assert before["total"] == "0.00"
    assert Decimal(before["potential_total"]) > 0

    response = client.post(
        f"/api/processes/{process['id']}/activities/validate-batch",
        json={"activity_ids": [d["id"] for d in drafts], "justificativa": "Conferi os documentos"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert [a["status"] for a in response.json()] == ["VALIDADA", "VALIDADA"]
    assert all(len(a["evidences"]) == 1 for a in response.json())
    after = score(client, process)
    assert after["total"] != before["total"]
    assert after["total"] == before["potential_total"]
    assert after["counters"]["with_evidence"] == 2


# --- the secret and the logs ----------------------------------------------------------------------


def test_the_api_key_never_appears_in_a_response_or_in_the_logs_and_no_document_text_is_logged(
    case, ai, caplog
):
    client, headers, process = case
    caplog.set_level(logging.DEBUG)
    seen: list[str] = []

    def keep(response):
        seen.append(response.text + str(dict(response.headers)))
        return response

    sent = client.post(
        f"/api/processes/{process['id']}/documents",
        files=files_of(
            ("texto.pdf", text_pdf(BANCA)),
            ("digitalizado.pdf", synth.pdf_scanned([VISITA]), "application/pdf"),
            ("imagem.png", synth.png_with_text(COORIENTACAO), "image/png"),
        ),
        headers=headers,
    )
    documents = [r["document"] for r in keep(sent).json()]
    drain(client)
    for document in documents:
        keep(client.get(f"/api/documents/{document['id']}"))
    keep(client.get(f"/api/processes/{process['id']}/documents"))
    keep(client.get(f"/api/processes/{process['id']}/activities"))
    keep(client.get(f"/api/processes/{process['id']}/scoring"))
    keep(client.get(f"/api/documents/{uuid.uuid4()}"))  # an error body too

    assert len(ai.requests) == 3  # the key was really used for the three documents
    assert all(r.headers["authorization"] == f"Bearer {API_KEY}" for r in ai.requests)
    assert len(seen) == 3 + 1 + 1 + 1 + 1 + 1
    assert not any(API_KEY in body for body in seen)
    assert API_KEY not in caplog.text
    for secret_text in (PROFESSOR, "Estudo Ficticio", "participou como membro", "Analise Ficticia"):
        assert secret_text not in caplog.text
