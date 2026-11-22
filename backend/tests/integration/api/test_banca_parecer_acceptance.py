"""PORT-02, PORT-09, PAR-02, PAR-11, PAR-12, REQ-04, DOS-02, DOS-07, BNAV-02 (T39): the whole
flow of the feature through the API, on a synthetic process with a fake AI: the ordinance, the
Parecer, the Requerimento, the checklist and the conclusion. The success criteria of the spec are
checked here: the Total geral of the Parecer is the one of the Tabela, the conclusion is never
filled without the person, and the AI is not called to generate the two documents."""

import re
from datetime import date

import pytest

from app.domain.entities.generated import DocumentKind
from app.domain.entities.process import ProcessStatus
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from app.infrastructure.ai.maritalk import MariTalkClient
from tests.integration.api.board_support import board_url, set_status, settings_url
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import pdf, stored_files
from tests.integration.api.generated_readers import docx_text, pdf_text, pt
from tests.integration.api.generated_support import (
    add_activity,
    add_ready,
    ask,
    choose_table,
    file_url,
    generate,
    process_url,
)
from tests.integration.doc_usecases.board_support import FakeOrdinanceExtractor
from tests.unit.application.analyzer_fakes import FakeTextExtractor, text_page

PAGE_ONE = (
    "PORTARIA Nº 123/2025 - FASI. Belém, 10 de março de 2025. Designa a banca. "
    "Presidente: Maria Aparecida Souza. Membro: José da Silva."
)
PAGE_TWO = "Suplente: Ana Beatriz Lima. Fim."
ANSWER = OrdinanceAi(
    "123/2025",
    1,
    date(2025, 3, 10),
    1,
    (
        OrdinanceAiMember("Maria Aparecida Souza", "PRESIDENTE", 1),
        OrdinanceAiMember("José da Silva", "MEMBRO", 1),
        OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 2),
    ),
)
CORRECTED = "José da Silva Neto"
OPINION_DATE = "2025-04-01"
SIGNATURE_LINE = "_" * 42


class Flow:
    """The scenario of the acceptance: a client whose AI is the fake, the process with the table
    chosen and one validated activity, and the steps the person takes."""

    def __init__(self, client, headers, process, ai):
        self.client, self.headers, self.process, self.ai = client, headers, process, ai

    def url(self, tail=""):
        return board_url(self.process, tail)

    def board(self) -> dict:
        return self.client.get(self.url()).json()

    def scoring(self) -> dict:
        return self.client.get(process_url(self.process, "scoring")).json()

    def documents(self) -> list:
        return self.client.get(process_url(self.process, "documents")).json()

    def activities(self) -> list:
        return self.client.get(process_url(self.process, "activities")).json()

    def checklist(self) -> dict:
        return {i["key"]: i for i in self.client.get(process_url(self.process, "dossier")).json()}

    def send_ordinance(self):
        return self.client.put(
            self.url("/ordinance/file"),
            data={"expected_version": "0"},
            files=[("file", ("portaria.pdf", pdf("portaria-banca"), "application/pdf"))],
            headers=self.headers,
        )

    def read_ordinance(self) -> bool:
        return self.client.app.state.container.run_ordinance_reading.run_next()

    def correct_a_member(self):
        ordinance = self.board()["ordinance"]
        members = [
            {"name": CORRECTED if m["name"] == "José da Silva" else m["name"], "role": m["role"]}
            for m in ordinance["members"]
        ]
        response = self.client.put(
            self.url("/ordinance"),
            json={
                "number": ordinance["number"],
                "ordinance_date": ordinance["ordinance_date"],
                "members": members,
                "expected_version": ordinance["version"],
            },
            headers=self.headers,
        )
        assert response.status_code == 200, response.text
        return response.json()

    def choose_conclusion(self, conclusion="FAVORAVEL"):
        opinion = self.board()["opinion"]
        response = self.client.put(
            self.url("/opinion"),
            json={
                "conclusion": conclusion,
                "opinion_date": OPINION_DATE,
                "place": "Belém",
                "notes": None,
                "expected_version": opinion["version"],
            },
            headers=self.headers,
        )
        assert response.status_code == 200, response.text

    def save_date_and_place_only(self):
        response = self.client.put(
            self.url("/opinion"),
            json={"opinion_date": OPINION_DATE, "place": "Belém", "expected_version": 0},
            headers=self.headers,
        )
        assert response.status_code == 200, response.text

    def generate(self, kind):
        return generate(self.client, self.headers, self.process, kind)

    def ask(self, kind):
        return ask(self.client, self.headers, self.process, kind)

    def texts(self, row) -> dict[str, str]:
        """The words of the DOCX and of the PDF of a ready version, as a reader sees them."""
        docx = self.client.get(file_url(row, "docx")).content
        pdf_bytes = self.client.get(file_url(row, "pdf")).content
        return {"DOCX": docx_text(docx), "PDF": pdf_text(pdf_bytes)}

    def detail(self, row) -> dict:
        return self.client.get(f"/api/generated-documents/{row['id']}").json()


@pytest.fixture
def flow(make_client, admin, process, scoring_tables, monkeypatch, tmp_path):
    """The flow over a client with the fake AI; the MariTalk client is broken, so any call of the
    real AI during the test fails it."""
    calls = []

    def refuse(*args, **kwargs):
        calls.append("MariTalkClient.chat")
        raise AssertionError("the real AI was called")

    monkeypatch.setattr(MariTalkClient, "chat", refuse)
    ai = FakeOrdinanceExtractor(answer=ANSWER)
    client = make_client(
        text_extractor=FakeTextExtractor(text_page(1, PAGE_ONE), text_page(2, PAGE_TWO)),
        ordinance_extractor=ai,
    )
    headers = {"X-CSRF-Token": login(client, "admin@ufpa.br")}
    choose_table(client, headers, process, scoring_tables["OFICIAL"])
    add_activity(client, headers, process)
    scenario = Flow(client, headers, process, ai)
    scenario.real_ai_calls = calls
    scenario.tmp_path = tmp_path
    return scenario


def total_geral(text: str) -> str:
    found = re.search(r"Total geral\s+(\d[\d.]*,\d{2})", text)
    assert found, text[-400:]
    return found.group(1)


# --- PORT-02, PORT-09: the ordinance is read and stays out of the rest ---------------------------


def test_the_ordinance_is_read_corrected_and_never_touches_documents_activities_or_score(flow):
    scoring_before, activities_before = flow.scoring(), flow.activities()
    assert flow.documents() == []

    assert flow.send_ordinance().status_code == 200
    assert flow.read_ordinance() is True

    ordinance = flow.board()["ordinance"]
    assert ordinance["reading_state"] == "LIDA"
    assert [(m["name"], m["page"], m["source"]) for m in ordinance["members"]] == [
        ("Maria Aparecida Souza", 1, "EXTRAIDO"),
        ("José da Silva", 1, "EXTRAIDO"),
        ("Ana Beatriz Lima", 2, "EXTRAIDO"),
    ]
    corrected = flow.correct_a_member()
    assert [(m["name"], m["source"]) for m in corrected["members"]] == [
        ("Maria Aparecida Souza", "EXTRAIDO"),
        (CORRECTED, "INFORMADO"),
        ("Ana Beatriz Lima", "EXTRAIDO"),
    ]
    assert corrected["members"][1]["page"] is None
    assert flow.documents() == []
    assert flow.activities() == activities_before
    assert flow.scoring() == scoring_before
    assert len(flow.ai.received) == 1 and "[PÁGINA 1]" in flow.ai.received[0]


# --- PAR-02, PAR-10, PAR-12: the Parecer ---------------------------------------------------------


def test_the_parecer_has_the_total_of_the_tabela_the_conclusion_and_three_signature_lines(flow):
    flow.send_ordinance()
    flow.read_ordinance()
    flow.correct_a_member()
    flow.save_date_and_place_only()
    assert flow.board()["opinion"]["conclusion"] is None
    table = flow.generate("TABELA")
    assert flow.board()["opinion"]["conclusion"] is None  # nothing filled it in
    refused = flow.ask("PARECER")
    assert refused.status_code == 422
    assert refused.json()["detail"][0]["code"] == "CONCLUSAO_AUSENTE"

    flow.choose_conclusion("FAVORAVEL")
    parecer = flow.generate("PARECER")

    total = flow.scoring()["total"]
    assert (
        flow.detail(parecer)["summary"]["total"] == flow.detail(table)["summary"]["total"] == total
    )
    for fmt, text in flow.texts(parecer).items():
        assert total_geral(text) == pt(total), fmt
        assert "A banca manifesta-se FAVORÁVEL à" in text, fmt
        assert text.count(SIGNATURE_LINE) == 3, fmt
        for name in ("Maria Aparecida Souza", CORRECTED, "Ana Beatriz Lima"):
            assert name in text, (fmt, name)
        assert "123/2025" in text and "10/03/2025" in text, fmt


def test_changing_a_validated_activity_refuses_the_parecer_until_the_tabela_is_made_again(flow):
    flow.send_ordinance()
    flow.read_ordinance()
    flow.generate("TABELA")
    flow.choose_conclusion("DESFAVORAVEL")
    add_activity(flow.client, flow.headers, flow.process, title="Outra orientação")

    stale = flow.ask("PARECER")

    assert stale.status_code == 422
    assert stale.json()["detail"][0]["code"] == "TABELA_DESATUALIZADA"
    table = flow.generate("TABELA")
    parecer = flow.generate("PARECER")
    total = flow.scoring()["total"]
    assert (
        flow.detail(table)["summary"]["total"] == flow.detail(parecer)["summary"]["total"] == total
    )
    for fmt, text in flow.texts(parecer).items():
        assert total_geral(text) == pt(total), fmt
        assert "DESFAVORÁVEL" in text, fmt


# --- REQ-04, PAR-11: the Requerimento and the AI -------------------------------------------------


def test_the_requerimento_has_the_date_of_the_parecer_and_the_ai_is_not_called_to_make_either(flow):
    flow.send_ordinance()
    flow.read_ordinance()
    flow.generate("TABELA")
    flow.choose_conclusion()
    reads_before = len(flow.ai.received)

    before_parecer = flow.generate("REQUERIMENTO")
    parecer = flow.generate("PARECER")
    after_parecer = flow.generate("REQUERIMENTO")

    for fmt, text in flow.texts(before_parecer).items():
        assert "___/___/___" in text, fmt
        assert "realizada na data de 01/04/2025" not in text, fmt
    for fmt, text in flow.texts(after_parecer).items():
        assert "realizada na data de 01/04/2025" in text, fmt
        assert "___/___/___" not in text, fmt
    assert (before_parecer["version_number"], after_parecer["version_number"]) == (1, 2)
    assert parecer["version_number"] == 1
    assert len(flow.ai.received) == reads_before
    assert flow.real_ai_calls == []


# --- DOS-02, DOS-07: the checklist and the conclusion --------------------------------------------


def test_the_checklist_shows_the_ready_items_and_the_conclusion_keeps_the_data_and_closes(
    flow, uow_factory, process, admin
):
    flow.send_ordinance()
    flow.read_ordinance()
    flow.generate("TABELA")
    flow.choose_conclusion()
    preview_url = process_url(flow.process, "conclusion")
    assert flow.client.get(preview_url).json()["pending_board"] == [
        "REQUERIMENTO",
        "PARECER",
    ]
    flow.generate("REQUERIMENTO")
    flow.generate("PARECER")
    add_ready(uow_factory, process, admin[0], DocumentKind.RELATORIO)
    add_ready(uow_factory, process, admin[0], DocumentKind.COMPROVANTE)
    marked = flow.client.put(
        process_url(flow.process, "dossier/items/CURRICULO_LATTES"),
        json={"entregue": True},
        headers=flow.headers,
    )
    assert marked.status_code == 200

    checklist = flow.checklist()

    assert {k: i["state"] for k, i in checklist.items()} == {
        "REQUERIMENTO": "GERADO",
        "PORTARIA_ULTIMA_PROGRESSAO": "PENDENTE",
        "DECLARACAO_EXERCICIOS_ANTERIORES": "PENDENTE",
        "RELATORIO": "GERADO",
        "TABELA": "GERADO",
        "COMPROVANTE": "GERADO",
        "CURRICULO_LATTES": "ENTREGUE",
        "PORTARIA_BANCA": "REGISTRADA",
        "PARECER": "GERADO",
    }
    assert checklist["PARECER"]["version_number"] == 1
    preview = flow.client.get(preview_url).json()
    assert preview["pending_board"] == []
    assert preview["files"] == 1  # the file of the ordinance counts as an input file
    ordinance_before = flow.board()["ordinance"]
    inputs_before = [p for p in stored_files(flow.tmp_path) if "generated" not in p.parts]
    assert len(inputs_before) == 1

    started = flow.client.post(
        process_url(flow.process, "status"),
        json={
            "status": "EM_ANDAMENTO",
            "expected_version": flow.client.get(f"/api/processes/{flow.process['id']}").json()[
                "version"
            ],
        },
        headers=flow.headers,
    )
    assert started.status_code == 200, started.text
    concluded = flow.client.post(
        preview_url,
        json={
            "expected_version": flow.client.get(f"/api/processes/{flow.process['id']}").json()[
                "version"
            ],
            "confirmar": True,
        },
        headers=flow.headers,
    )

    assert concluded.status_code == 200, concluded.text
    assert concluded.json()["status"] == "CONCLUIDO"
    assert concluded.json()["arquivos_removidos"] == 1
    assert [p for p in stored_files(flow.tmp_path) if "generated" not in p.parts] == []
    after = flow.board()["ordinance"]
    assert (after["number"], after["ordinance_date"], after["members"]) == (
        ordinance_before["number"],
        ordinance_before["ordinance_date"],
        ordinance_before["members"],
    )
    assert after["file"]["deleted"] is True
    gone = flow.client.get(flow.url("/ordinance/file"))
    assert gone.status_code == 410
    assert gone.json()["detail"][0]["code"] == "ARQUIVO_EXCLUIDO"
    refuse_every_write(flow)


# --- BNAV-02: the archived process ---------------------------------------------------------------


def test_an_archived_process_refuses_every_write_of_the_feature_with_409(flow, uow_factory):
    flow.send_ordinance()
    flow.read_ordinance()
    flow.generate("TABELA")
    flow.choose_conclusion()
    set_status(uow_factory, flow.process, ProcessStatus.ARQUIVADO)

    refuse_every_write(flow)

    assert flow.board()["ordinance"]["reading_state"] == "LIDA"  # reading stays possible
    assert flow.client.get(process_url(flow.process, "dossier")).status_code == 200


def refuse_every_write(flow):
    """Every write of the feature is a 409 `PROCESSO_SOMENTE_LEITURA`: the data, the file, the
    new reading, the opinion, the city, the mark and the two documents."""
    board = flow.board()
    version = board["ordinance"]["version"]
    flow_headers = flow.headers
    writes = [
        flow.client.put(
            flow.url("/ordinance"),
            json={"number": "1/2025", "expected_version": version},
            headers=flow_headers,
        ),
        flow.client.put(
            flow.url("/ordinance/file"),
            data={"expected_version": str(version), "replace": "true"},
            files=[("file", ("nova.pdf", pdf("nova"), "application/pdf"))],
            headers=flow_headers,
        ),
        flow.client.post(
            flow.url("/ordinance/reread"), json={"expected_version": version}, headers=flow_headers
        ),
        flow.client.put(
            flow.url("/opinion"),
            json={"conclusion": "FAVORAVEL", "expected_version": board["opinion"]["version"]},
            headers=flow_headers,
        ),
        flow.client.put(
            settings_url(flow.process),
            json={"city": "Belém", "expected_version": board["request_settings"]["version"]},
            headers=flow_headers,
        ),
        flow.client.put(
            process_url(flow.process, "dossier/items/CURRICULO_LATTES"),
            json={"entregue": True},
            headers=flow_headers,
        ),
        flow.ask("PARECER"),
        flow.ask("REQUERIMENTO"),
    ]
    for response in writes:
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "PROCESSO_SOMENTE_LEITURA"
