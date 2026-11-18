"""DOC-01..DOC-04, DOC-07, DOC-12, DOC-14, DOC-15, REV-01 (T36): upload, list and detail routes."""

import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.entities.activity import ActivityStatus
from app.domain.entities.document import DocumentStatus
from app.domain.entities.user import Role
from app.domain.repositories.ports import ActivityEvidence
from tests.integration.api.conftest import PASSWORD, login
from tests.integration.api.documents_support import (
    files_of,
    pdf,
    seed_document,
    seed_run,
    sha256,
    stored_files,
    upload,
    upload_one,
)
from tests.integration.test_scoring_repositories import make_activity
from tests.support import synthetic_docs as synth
from tests.support.process_status import conclude_for_test

DOCUMENT_KEYS = {
    "id", "process_id", "original_name", "mime", "size_bytes", "sha256", "page_count", "status",
    "status_code", "manual_type", "manual_category", "suggested_type", "suggested_category",
    "confidence", "uploaded_by", "uploaded_at", "updated_at", "version",
}  # fmt: skip
LIST_KEYS = DOCUMENT_KEYS | {
    "activity_count", "outside_interstice", "document_date", "document_date_precision",
    "interstice_start", "interstice_end",
}  # fmt: skip
RESULT_KEYS = {
    "original_name", "status_code", "document", "existing_document_id", "field", "code", "message",
}  # fmt: skip


def documents_url(process):
    return f"/api/processes/{process['id']}/documents"


def close_process(client, headers, process, uow_factory, final="CONCLUIDO"):
    if final == "CONCLUIDO":
        steps = ["EM_ANDAMENTO"]
    else:
        steps = ["ARQUIVADO"]
    for status in steps:
        version = client.get(f"/api/processes/{process['id']}").json()["version"]
        response = client.post(
            f"/api/processes/{process['id']}/status",
            json={"status": status, "expected_version": version, "justificativa": "x"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    if final == "CONCLUIDO":
        conclude_for_test(uow_factory, process["id"])


# --- upload: DOC-01 ----------------------------------------------------------------------


def test_one_valid_file_is_201_with_the_stored_document(client, admin, headers, process, tmp_path):
    user, _ = admin
    content = pdf("unico")

    response = upload(client, headers, process, ("declaracao.pdf", content))

    assert response.status_code == 201
    [result] = response.json()
    assert set(result) == RESULT_KEYS
    assert result["original_name"] == "declaracao.pdf"
    assert result["status_code"] == 201
    assert (result["existing_document_id"], result["field"], result["code"]) == (None, None, None)
    assert result["message"] is None
    document = result["document"]
    assert set(document) == DOCUMENT_KEYS
    assert document["process_id"] == process["id"]
    assert document["original_name"] == "declaracao.pdf"
    assert document["mime"] == "application/pdf"
    assert document["size_bytes"] == len(content)
    assert document["sha256"] == sha256(content)
    assert document["page_count"] == 1
    assert document["status"] == "PENDENTE"
    assert document["uploaded_by"] == str(user.id)
    assert document["version"] == 1
    assert document["uploaded_at"] and document["updated_at"]
    for empty in ("status_code", "manual_type", "manual_category", "suggested_type",
                  "suggested_category", "confidence"):  # fmt: skip
        assert document[empty] is None
    assert len(stored_files(tmp_path)) == 1


def test_several_files_all_accepted_are_201_with_one_result_each_in_order(
    client, headers, process
):
    response = upload(
        client,
        headers,
        process,
        ("a.pdf", pdf("a")),
        ("b.png", synth.png_with_text(), "image/png"),
        ("c.jpg", synth.jpg_with_text(), "image/jpeg"),
    )

    assert response.status_code == 201
    results = response.json()
    assert [r["original_name"] for r in results] == ["a.pdf", "b.png", "c.jpg"]
    assert [r["status_code"] for r in results] == [201, 201, 201]
    mimes = [r["document"]["mime"] for r in results]
    assert mimes == ["application/pdf", "image/png", "image/jpeg"]


def test_a_mixed_request_is_207_with_the_outcome_and_reason_of_each_file(client, headers, process):
    first = upload_one(client, headers, process, "primeiro")

    response = upload(
        client,
        headers,
        process,
        ("novo.pdf", pdf("novo")),
        ("repetido.pdf", pdf("primeiro")),
        ("trocado.png", pdf("trocado")),
    )

    assert response.status_code == 207
    novo, repetido, trocado = response.json()
    assert (novo["status_code"], novo["document"]["original_name"]) == (201, "novo.pdf")
    assert repetido["status_code"] == 409
    assert repetido["existing_document_id"] == first["id"]
    assert repetido["document"] is None
    assert trocado["status_code"] == 422
    assert (trocado["field"], trocado["code"]) == ("arquivo", "ASSINATURA_DIVERGENTE")
    assert trocado["document"] is None
    assert trocado["message"]


@pytest.mark.parametrize(
    ("name", "content", "mime", "code"),
    [
        ("planilha.xlsx", b"PK\x03\x04 not a pdf", "application/octet-stream", "EXTENSAO_INVALIDA"),
        ("laudo.pdf", pdf("mime"), "image/png", "MIME_DIVERGENTE"),
        ("script.pdf", synth.pdf_with_javascript(), "application/pdf", "ARQUIVO_INVALIDO"),
        ("fechado.pdf", synth.pdf_encrypted(), "application/pdf", "ARQUIVO_INVALIDO"),
        ("quebrado.pdf", b"%PDF-1.4 truncated", "application/pdf", "ARQUIVO_INVALIDO"),
    ],
)
def test_a_refused_file_shows_field_arquivo_and_the_code_and_is_not_stored(
    client, headers, process, tmp_path, name, content, mime, code
):
    response = upload(client, headers, process, (name, content, mime))

    assert response.status_code == 207
    [result] = response.json()
    assert result["status_code"] == 422
    assert (result["field"], result["code"]) == ("arquivo", code)
    assert result["document"] is None
    assert stored_files(tmp_path) == []
    assert client.get(documents_url(process)).json() == []


def test_a_file_above_the_size_limit_is_refused_and_not_stored(make_client, process, tmp_path):
    small = make_client(max_upload_mb=1)
    csrf = {"X-CSRF-Token": login(small, "admin@ufpa.br")}
    big = b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10)

    response = upload(small, csrf, process, ("grande.pdf", big))

    [result] = response.json()
    assert response.status_code == 207
    assert result["status_code"] == 422
    assert (result["field"], result["code"]) == ("arquivo", "ARQUIVO_GRANDE")
    assert stored_files(tmp_path) == []


def test_a_path_in_the_file_name_is_kept_only_as_display_text(client, headers, process, tmp_path):
    response = upload(client, headers, process, ("../../etc/passwd.pdf", pdf("caminho")))

    [result] = response.json()
    assert result["document"]["original_name"] == "passwd.pdf"
    [stored] = stored_files(tmp_path)
    assert stored.is_relative_to(tmp_path / "storage")
    assert "passwd" not in stored.name


def test_a_request_without_a_file_part_is_422_on_file(client, headers, process):
    response = client.post(documents_url(process), data={"outro": "x"}, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == "file"


@pytest.mark.parametrize("refused", [False, True])
def test_the_temporary_copies_are_always_removed(
    client, headers, process, tmp_path, monkeypatch, refused
):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    content = b"not a pdf" if refused else pdf("temporario")

    response = upload(client, headers, process, ("t.pdf", content))

    assert response.status_code == (207 if refused else 201)
    assert list(scratch.rglob("*")) == []


# --- upload: duplicates and limits (DOC-07, DOC-14) --------------------------------------------


def test_a_duplicate_in_the_same_process_is_409_with_the_existing_id_and_nothing_is_stored(
    client, headers, process, tmp_path
):
    first = upload_one(client, headers, process, "igual")

    response = upload(client, headers, process, ("copia.pdf", pdf("igual")))

    [result] = response.json()
    assert result["status_code"] == 409
    assert result["existing_document_id"] == first["id"]
    assert len(stored_files(tmp_path)) == 1
    assert len(client.get(documents_url(process)).json()) == 1


def test_the_same_file_twice_in_one_request_stores_the_first_and_refuses_the_second(
    client, headers, process
):
    response = upload(client, headers, process, ("a.pdf", pdf("dupla")), ("b.pdf", pdf("dupla")))

    first, second = response.json()
    assert (first["status_code"], second["status_code"]) == (201, 409)
    assert second["existing_document_id"] == first["document"]["id"]


def test_more_than_60_uploads_in_a_minute_is_429_on_the_next_file(
    client, admin, headers, process, uow_factory, clock
):
    user, _ = admin
    for _ in range(60):
        seed_document(uow_factory, process, user, uploaded_at=clock.now() - timedelta(seconds=30))

    response = upload(client, headers, process, ("sessentaum.pdf", pdf("sessentaum")))

    assert response.status_code == 207
    [result] = response.json()
    assert result["status_code"] == 429
    assert result["document"] is None
    assert result["message"]


def test_a_process_with_the_maximum_documents_refuses_with_422_on_limite(
    make_client, admin, process
):
    capped = make_client(max_documents_per_process=1)
    csrf = {"X-CSRF-Token": login(capped, "admin@ufpa.br")}
    upload_one(capped, csrf, process, "cheio")

    response = upload(capped, csrf, process, ("extra.pdf", pdf("extra")))

    [result] = response.json()
    assert result["status_code"] == 422
    assert result["field"] == "limite"


# --- access and CSRF (DOC-12) ----------------------------------------------------------------


def test_unauthenticated_requests_are_401(make_client, process):
    anonymous = make_client()  # a client that never logged in
    document_id = uuid.uuid4()

    assert anonymous.get(documents_url(process)).status_code == 401
    assert anonymous.get(f"/api/documents/{document_id}").status_code == 401
    uploaded = anonymous.post(documents_url(process), files=files_of(("a.pdf", pdf("a"))))
    assert uploaded.status_code == 401


def test_an_upload_without_the_csrf_token_is_403_and_stores_nothing(
    client, headers, process, tmp_path
):
    response = client.post(documents_url(process), files=files_of(("a.pdf", pdf("csrf"))))

    assert response.status_code == 403
    assert stored_files(tmp_path) == []


def test_without_access_to_the_process_everything_is_404(
    client, act_as, headers, process, reference, uow_factory, professor
):
    document = upload_one(client, headers, process, "protegido")
    outsider, outsider_headers = act_as(
        "fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id})
    )

    assert client.get(documents_url(process)).status_code == 404
    assert client.get(f"/api/documents/{document['id']}").status_code == 404
    denied = upload(client, outsider_headers, process, ("x.pdf", pdf("x")))
    assert denied.status_code == 404


@pytest.mark.parametrize("final", ["CONCLUIDO", "ARQUIVADO"])
def test_upload_to_a_closed_process_is_409_and_listing_still_works(
    client, headers, process, tmp_path, uow_factory, final
):
    upload_one(client, headers, process, "antes")
    close_process(client, headers, process, uow_factory, final)

    response = upload(client, headers, process, ("depois.pdf", pdf("depois")))

    assert response.status_code == 409
    assert len(stored_files(tmp_path)) == 1
    assert len(client.get(documents_url(process)).json()) == 1


def test_the_owner_docente_and_the_unit_secretaria_have_access(
    client, act_as, make_user, headers, process, professor, reference
):
    make_user("dono@ufpa.br", role=Role.DOCENTE, professor_id=professor.id)
    document = upload_one(client, headers, process, "compartilhado")
    for email, role, extra in (
        ("dono@ufpa.br", Role.DOCENTE, {}),
        ("sec@ufpa.br", Role.SECRETARIA, {"unit_ids": frozenset({reference["FASI"].id})}),
    ):
        if email == "dono@ufpa.br":
            csrf = {"X-CSRF-Token": login(client, email, PASSWORD)}
        else:
            _, csrf = act_as(email, role, **extra)
        listed = client.get(documents_url(process))
        assert listed.status_code == 200
        assert document["id"] in [d["id"] for d in listed.json()]
        assert upload(client, csrf, process, ("n.pdf", pdf(email))).status_code == 201


# --- list: DOC-15 ----------------------------------------------------------------------------


def test_the_list_is_in_upload_order_with_status_type_category_and_confidence(
    client, admin, process, uow_factory
):
    user, _ = admin
    base = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
    later = seed_document(
        uow_factory, process, user, original_name="segundo.pdf",
        uploaded_at=base + timedelta(hours=1), status=DocumentStatus.PROCESSADO,
        suggested_type="DECLARACAO_BANCA", suggested_category="BANCA_TCC_GRADUACAO",
        confidence=Decimal("0.85"),
    )  # fmt: skip
    earlier = seed_document(
        uow_factory, process, user, original_name="primeiro.pdf", uploaded_at=base,
    )  # fmt: skip
    with uow_factory() as uow:
        activity = make_activity(
            SimpleNamespace(id=uuid.UUID(process["id"])), {"admin": user},
            status=ActivityStatus.AGUARDANDO_REVISAO,
        )  # fmt: skip
        uow.activities.add(activity)
        uow.commit()
        uow.evidences.add(
            ActivityEvidence(uuid.uuid4(), activity.id, later.id, 1, "trecho", user.id)
        )
        uow.commit()

    response = client.get(documents_url(process))

    assert response.status_code == 200
    listed = response.json()
    assert [d["id"] for d in listed] == [str(earlier.id), str(later.id)]
    assert set(listed[0]) == LIST_KEYS
    assert (listed[0]["activity_count"], listed[1]["activity_count"]) == (0, 1)
    assert listed[1]["status"] == "PROCESSADO"
    assert listed[1]["suggested_type"] == "DECLARACAO_BANCA"
    assert listed[1]["suggested_category"] == "BANCA_TCC_GRADUACAO"
    assert listed[1]["confidence"] == "0.85"
    assert listed[0]["confidence"] is None


def test_the_list_filters_by_status_and_by_type(client, admin, process, uow_factory):
    user, _ = admin
    banca = seed_document(
        uow_factory, process, user, status=DocumentStatus.PROCESSADO,
        suggested_type="DECLARACAO_BANCA",
    )  # fmt: skip
    ata = seed_document(
        uow_factory, process, user, status=DocumentStatus.REQUER_REVISAO,
        suggested_type="ATA_DEFESA",
    )  # fmt: skip
    manual = seed_document(
        uow_factory, process, user, status=DocumentStatus.PROCESSADO,
        suggested_type="ATA_DEFESA", manual_type="CERTIFICADO",
    )  # fmt: skip

    def ids(query):
        response = client.get(f"{documents_url(process)}{query}")
        assert response.status_code == 200, response.text
        return {d["id"] for d in response.json()}

    assert ids("?status=PROCESSADO") == {str(banca.id), str(manual.id)}
    assert ids("?status=REQUER_REVISAO") == {str(ata.id)}
    assert ids("?type=DECLARACAO_BANCA") == {str(banca.id)}
    assert ids("?type=CERTIFICADO") == {str(manual.id)}
    assert ids("?status=PROCESSADO&type=ATA_DEFESA") == set()


@pytest.mark.parametrize("query", ["?status=INEXISTENTE", "?type=INEXISTENTE"])
def test_an_unknown_filter_value_is_422_on_that_filter(client, process, headers, query):
    response = client.get(f"{documents_url(process)}{query}")

    assert response.status_code == 422
    assert response.json()["detail"][0]["field"] == query[1:].split("=")[0]


# --- detail: REV-01 --------------------------------------------------------------------------


def test_the_detail_has_pages_extracted_json_alerts_and_linked_activities(
    client, admin, process, uow_factory
):

    user, headers = admin
    document = seed_document(
        uow_factory, process, user, original_name="banca.pdf", status=DocumentStatus.PROCESSADO,
        suggested_type="DECLARACAO_BANCA", confidence=Decimal("0.90"),
    )  # fmt: skip
    warnings = (
        {"code": "TRUNCADO", "field": None, "activity_index": None},
        {"code": "NAO_ENCONTRADO_NO_TEXTO", "field": "event_date", "activity_index": 0},
    )
    run = seed_run(
        uow_factory, document, raw_json={"activities": [{"title": "T"}]}, warnings=warnings,
        model="sabia-4-br-sp",
    )  # fmt: skip
    created = client.post(
        f"/api/processes/{process['id']}/activities",
        json={"title": "Banca de TCC", "group_number": 3, "item_number": 4},
        headers=headers,
    ).json()
    with uow_factory() as uow:
        uow.evidences.add(
            ActivityEvidence(
                uuid.uuid4(), uuid.UUID(created["id"]), document.id, 2, "trecho da pagina", user.id
            )
        )
        uow.commit()

    response = client.get(f"/api/documents/{document.id}")

    assert response.status_code == 200
    body = response.json()
    assert set(DOCUMENT_KEYS) <= set(body)
    assert body["id"] == str(document.id)
    assert body["confidence"] == "0.90"
    assert [(p["page_number"], p["method"], p["ocr_confidence"], p["text"], p["char_count"])
            for p in body["pages"]] == [
        (1, "TEXTO", None, "Primeira pagina", 15),
        (2, "OCR", "88.50", "Segunda pagina", 14),
    ]  # fmt: skip
    assert body["run"]["id"] == str(run.id)
    assert body["run"]["model"] == "sabia-4-br-sp"
    assert body["run"]["duration_ms"] == 1500
    assert body["run"]["raw_json"] == {"activities": [{"title": "T"}]}
    assert body["alerts"] == [{**warning, "detail": None} for warning in warnings]
    [linked] = body["activities"]
    assert linked["id"] == created["id"]
    assert linked["title"] == "Banca de TCC"
    assert (linked["group_number"], linked["item_number"]) == (3, 4)
    assert linked["evidences"] == [
        {
            "id": linked["evidences"][0]["id"],
            "document_id": str(document.id),
            "document_name": "banca.pdf",
            "page": 2,
            "excerpt": "trecho da pagina",
        }
    ]


def test_the_detail_of_an_unread_document_has_no_run_pages_alerts_or_activities(
    client, admin, process, uow_factory
):
    user, _ = admin
    document = seed_document(uow_factory, process, user)

    body = client.get(f"/api/documents/{document.id}").json()

    assert body["run"] is None
    assert (body["pages"], body["alerts"], body["activities"]) == ([], [], [])


def test_the_detail_of_an_unknown_document_is_404(client, admin, headers):
    assert client.get(f"/api/documents/{uuid.uuid4()}").status_code == 404


def test_the_detail_of_a_document_of_a_process_out_of_reach_is_404(
    client, act_as, admin, process, uow_factory, reference
):
    user, _ = admin
    document = seed_document(uow_factory, process, user)
    act_as("fora@ufpa.br", Role.SECRETARIA, unit_ids=frozenset({reference["IFCH"].id}))

    assert client.get(f"/api/documents/{document.id}").status_code == 404
