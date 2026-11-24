"""PORT-01, PORT-02, PORT-07, PORT-08, PORT-10, BNAV-02, BNAV-03: the routes of the file of the
ordinance (send, re-read, view), with a fake AI and synthetic PDFs."""

import uuid
from datetime import UTC, datetime

import pytest

from app.domain.entities.board import OrdinanceReadingCode
from app.domain.entities.process import ProcessStatus
from app.domain.repositories.ports import OrdinanceExtractionError
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from tests.integration.api.board_support import as_user, board_url, set_status
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import pdf, stored_files
from tests.integration.doc_usecases.board_support import FakeOrdinanceExtractor
from tests.unit.application.analyzer_fakes import FakeTextExtractor, text_page

MB = 1024 * 1024
PAGE_ONE = (
    "PORTARIA Nº 123/2025 - FASI. Belém, 10 de março de 2025. Designa a banca. "
    "Presidente: Maria Aparecida Souza. Membro: José da Silva."
)
PAGE_TWO = "Suplente: Ana Beatriz Lima. Fim."
ANSWER = OrdinanceAi(
    "123/2025",
    1,
    datetime(2025, 3, 10, tzinfo=UTC).date(),
    1,
    (
        OrdinanceAiMember("Maria Aparecida Souza", "PRESIDENTE", 1),
        OrdinanceAiMember("José da Silva", "MEMBRO", 1),
        OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 2),
    ),
)


@pytest.fixture
def board(make_client, admin, process):
    """A logged-in admin client whose AI is a fake that answers `ANSWER`: `.client`, `.headers`,
    `.process`, `.ai`, and `.run()` which does what the executor does for a queued reading."""
    ai = FakeOrdinanceExtractor(answer=ANSWER)
    client = make_client(
        text_extractor=FakeTextExtractor(text_page(1, PAGE_ONE), text_page(2, PAGE_TWO)),
        ordinance_extractor=ai,
    )
    headers = {"X-CSRF-Token": login(client, "admin@ufpa.br")}

    class Board:
        def __init__(self):
            self.client, self.headers, self.process, self.ai = client, headers, process, ai

        def run(self) -> bool:
            return client.app.state.container.run_ordinance_reading.run_next()

        def get(self) -> dict:
            return client.get(board_url(process)).json()["ordinance"]

        def send(self, content=None, name="portaria.pdf", version=0, replace=None, headers=None):
            data = {"expected_version": str(version)}
            if replace is not None:
                data["replace"] = str(replace).lower()
            return client.put(
                board_url(process, "/ordinance/file"),
                data=data,
                files=[("file", (name, content or pdf("portaria"), "application/pdf"))],
                headers=headers or self.headers,
            )

        def reread(self, version, headers=None):
            return client.post(
                board_url(process, "/ordinance/reread"),
                json={"expected_version": version},
                headers=headers or self.headers,
            )

    return Board()


# --- PORT-01, PORT-02: send, queue, read ---------------------------------------------------------


def test_the_upload_answers_200_with_the_reading_queued_and_the_file_described(board):
    response = board.send(name="portaria-banca.pdf")

    assert response.status_code == 200
    body = response.json()
    assert (body["reading_state"], body["reading_code"]) == ("PENDENTE", None)
    assert body["file"]["original_name"] == "portaria-banca.pdf"
    assert (body["file"]["mime"], body["file"]["deleted"]) == ("application/pdf", False)
    assert body["version"] == 2
    assert board.ai.received == []  # queued only: the AI runs in the executor


def test_after_the_executor_runs_the_reading_has_number_date_and_three_members_with_pages(board):
    board.send()

    assert board.run() is True

    ordinance = board.get()
    assert ordinance["reading_state"] == "LIDA"
    assert (ordinance["number"], ordinance["number_page"], ordinance["number_source"]) == (
        "123/2025",
        1,
        "EXTRAIDO",
    )
    assert (ordinance["ordinance_date"], ordinance["date_page"], ordinance["date_source"]) == (
        "2025-03-10",
        1,
        "EXTRAIDO",
    )
    assert [(m["name"], m["role"], m["page"], m["source"]) for m in ordinance["members"]] == [
        ("Maria Aparecida Souza", "PRESIDENTE", 1, "EXTRAIDO"),
        ("José da Silva", "MEMBRO", 1, "EXTRAIDO"),
        ("Ana Beatriz Lima", "SUPLENTE", 2, "EXTRAIDO"),
    ]
    assert ordinance["warnings"] == []


# --- PORT-07: a failed reading --------------------------------------------------------------------


def test_a_failing_ai_leaves_the_reading_failed_with_the_reason_and_the_data_editable(board):
    board.ai.error = OrdinanceExtractionError(OrdinanceReadingCode.IA_INDISPONIVEL)
    board.send()

    board.run()

    failed = board.get()
    assert (failed["reading_state"], failed["reading_code"]) == ("FALHOU", "IA_INDISPONIVEL")
    typed = board.client.put(
        board_url(board.process, "/ordinance"),
        json={
            "number": "5/2025",
            "ordinance_date": "2025-03-10",
            "members": [{"name": "Ana Souza", "role": "PRESIDENTE"}],
            "expected_version": failed["version"],
        },
        headers=board.headers,
    )
    assert typed.status_code == 200
    saved = typed.json()
    assert (saved["number"], saved["number_source"]) == ("5/2025", "INFORMADO")
    assert saved["reading_state"] == "FALHOU"  # the failure stays visible beside what was typed


def test_ler_de_novo_queues_the_reading_again_and_a_working_ai_fills_the_data(board):
    board.ai.error = OrdinanceExtractionError(OrdinanceReadingCode.IA_INDISPONIVEL)
    board.send()
    board.run()
    board.ai.error = None

    queued = board.reread(board.get()["version"])

    assert queued.status_code == 200
    assert queued.json()["reading_state"] == "PENDENTE"
    board.run()
    again = board.get()
    assert (again["reading_state"], again["number"], len(again["members"])) == (
        "LIDA",
        "123/2025",
        3,
    )


def test_ler_de_novo_without_a_file_is_a_422_on_arquivo_and_while_queued_a_409(board):
    board.client.put(
        board_url(board.process, "/ordinance"),
        json={"number": "5/2025", "expected_version": 0},
        headers=board.headers,
    )
    without_file = board.reread(1)
    board.send(version=1)
    queued = board.reread(board.get()["version"])

    assert without_file.status_code == 422
    assert without_file.json()["detail"][0]["field"] == "arquivo"
    assert queued.status_code == 409
    assert queued.json()["code"] == "OPERACAO_EM_ANDAMENTO"


# --- PORT-10: limits ------------------------------------------------------------------------------


def test_a_file_of_20_mb_plus_one_byte_is_a_422_on_arquivo_with_the_limit_message(board, tmp_path):
    base = pdf("grande")
    big = base + b"\x00" * (20 * MB + 1 - len(base))

    response = board.send(big)

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert (error["field"], error["code"]) == ("arquivo", "ARQUIVO_GRANDE")
    assert "tamanho máximo" in error["message"]
    assert stored_files(tmp_path) == []
    assert board.get()["version"] == 0


def test_a_file_of_exactly_20_mb_is_accepted(board):
    base = pdf("no-limite")
    exact = base + b"\x00" * (20 * MB - len(base))

    assert board.send(exact).status_code == 200


@pytest.mark.parametrize(
    ("content", "name"),
    [(b"texto qualquer", "portaria.txt"), (b"texto que se passa por pdf", "portaria.pdf")],
)
def test_a_file_that_is_not_pdf_png_or_jpeg_is_a_422_on_arquivo(board, tmp_path, content, name):
    response = board.send(content, name)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "arquivo"
    assert stored_files(tmp_path) == []


# --- PORT-08: replacement -------------------------------------------------------------------------


def test_a_second_file_without_replace_is_a_409_and_with_replace_it_takes_the_place(
    board, tmp_path
):
    board.send(pdf("primeira"), "primeira.pdf")
    [first_file] = stored_files(tmp_path)
    version = board.get()["version"]

    refused = board.send(pdf("segunda"), "segunda.pdf", version=version)
    replaced = board.send(pdf("segunda"), "segunda.pdf", version=version, replace=True)

    assert refused.status_code == 409
    assert refused.json()["code"] == "PORTARIA_EXISTENTE"
    assert replaced.status_code == 200
    assert replaced.json()["file"]["original_name"] == "segunda.pdf"
    assert replaced.json()["reading_state"] == "PENDENTE"
    [second_file] = stored_files(tmp_path)
    assert second_file != first_file and not first_file.exists()


# --- GET /board/ordinance/file --------------------------------------------------------------------


def test_the_file_is_served_inline_in_a_sandbox_and_never_sniffed(board):
    content = pdf("para-ver")
    board.send(content, "portaria.pdf")

    response = board.client.get(board_url(board.process, "/ordinance/file"))

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["content-disposition"].startswith("inline")


def test_without_a_file_the_download_is_404(board):
    assert board.client.get(board_url(board.process, "/ordinance/file")).status_code == 404


def test_a_file_the_conclusion_deleted_is_410_with_its_code(board, uow_factory, tmp_path):
    board.send()
    pid = uuid.UUID(board.process["id"])
    [stored] = stored_files(tmp_path)
    stored.unlink()
    with uow_factory() as uow:
        uow.board.mark_file_deleted(pid, datetime(2026, 11, 22, tzinfo=UTC))
        uow.commit()

    response = board.client.get(board_url(board.process, "/ordinance/file"))

    assert response.status_code == 410
    assert response.json()["detail"][0]["code"] == "ARQUIVO_EXCLUIDO"


# --- BNAV-02 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_upload_and_the_new_reading_with_409(
    board, uow_factory, tmp_path, status
):
    board.send()
    board.run()
    version = board.get()["version"]
    set_status(uow_factory, board.process, status)
    before = stored_files(tmp_path)

    upload = board.send(pdf("nova"), version=version, replace=True)
    reread = board.reread(version)

    for response in (upload, reread):
        assert response.status_code == 409
        assert response.json()["code"] == "PROCESSO_SOMENTE_LEITURA"
    assert stored_files(tmp_path) == before
    assert board.get()["reading_state"] == "LIDA"
    assert board.client.get(board_url(board.process, "/ordinance/file")).status_code == 200


# --- BNAV-03 --------------------------------------------------------------------------------------


def test_without_access_to_the_process_the_three_routes_are_404(board, actors, tmp_path):
    board.send()
    before = stored_files(tmp_path)
    version = board.get()["version"]

    for outsider in (actors.other_docente, actors.other_secretaria):
        outsider_headers = as_user(board.client, outsider)

        assert board.send(pdf("fora"), version=version, headers=outsider_headers).status_code == 404
        assert board.reread(version, headers=outsider_headers).status_code == 404
        assert board.client.get(board_url(board.process, "/ordinance/file")).status_code == 404
    assert stored_files(tmp_path) == before


def test_without_a_session_the_three_routes_are_401(board, make_client):
    anonymous = make_client()

    send = anonymous.put(
        board_url(board.process, "/ordinance/file"),
        data={"expected_version": "0"},
        files=[("file", ("portaria.pdf", pdf("anonima"), "application/pdf"))],
    )
    reread = anonymous.post(
        board_url(board.process, "/ordinance/reread"), json={"expected_version": 0}
    )
    download = anonymous.get(board_url(board.process, "/ordinance/file"))

    assert [r.status_code for r in (send, reread, download)] == [401, 401, 401]
