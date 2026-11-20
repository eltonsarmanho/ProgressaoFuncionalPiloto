"""SEG-01, SEG-02, SEG-03, SEG-05: the Tabela, the Relatório and the Comprovante carry only the
valid activities, and the generation is refused while a valid one has no category.

One process, the official table, synthetic data. The valid activity is the one of the `scenario`
(II.7, 2023-05-10, inside the interstice 2022-11-23 to 2024-11-23). The not valid ones are
inserted straight: outside the interstice, rejected, below the minimum hours and a duplicate.
"""

import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pymupdf
import pytest

from app.domain.entities.activity import Activity, ActivityStatus
from tests.integration.api.generated_readers import docx_text, pdf_text
from tests.integration.api.generated_support import (
    ask,
    file_url,
    generate,
    process_url,
)
from tests.support.pdf_pages import source_pdf

OUTSIDE = "Atividade fora do prazo"
REJECTED = "Atividade rejeitada"
SHORT = "Curso de curta duração"
PAGES = {"valid": 1, "outside": 2, "rejected": 3, "short": 4, "duplicate": 5}


def insert(uow_factory, scenario, **fields) -> Activity:
    fields.setdefault("quantity", Decimal(1))
    fields.setdefault("evidence_note", "Declaração")
    fields.setdefault("event_date", date(2023, 5, 10))
    with uow_factory() as uow:
        activity = Activity(
            id=uuid.uuid4(),
            process_id=uuid.UUID(scenario.process["id"]),
            created_by=scenario.user.id,
            **fields,
        )
        uow.activities.add(activity)
        uow.commit()
    return activity


def link(client, headers, activity_id, document, page):
    response = client.post(
        f"/api/activities/{activity_id}/evidences",
        json={"document_id": document["id"], "page": page},
        headers=headers,
    )
    assert response.status_code == 201, response.text


@pytest.fixture
def world(client, scenario, uow_factory):
    """The valid activity plus one not valid for each reason, each with its own page of Alfa."""
    headers, process = scenario.headers, scenario.process
    valid = scenario.activity
    outside = insert(
        uow_factory, scenario, title=OUTSIDE, group_number=2, item_number=7,
        event_date=date(2020, 1, 1),
    )  # fmt: skip
    rejected = insert(
        uow_factory, scenario, title=REJECTED, group_number=2, item_number=7,
        status=ActivityStatus.REJEITADA,
    )  # fmt: skip
    short = insert(
        uow_factory, scenario, title=SHORT, group_number=4, item_number=3, hours=Decimal(10)
    )  # fmt: skip
    duplicate = insert(
        uow_factory, scenario, title=valid["title"], group_number=2, item_number=7
    )  # fmt: skip
    content = source_pdf(5, label="Alfa ").tobytes()
    response = client.post(
        process_url(process, "documents"),
        files=[("file", ("alfa.pdf", content, "application/pdf"))],
        headers=headers,
    )
    assert response.status_code == 201, response.text
    [uploaded] = response.json()
    alfa = uploaded["document"]
    ids = {
        "valid": valid["id"], "outside": str(outside.id), "rejected": str(rejected.id),
        "short": str(short.id), "duplicate": str(duplicate.id),
    }  # fmt: skip
    for key, activity_id in ids.items():
        link(client, headers, activity_id, alfa, PAGES[key])
    scenario.ids = ids
    scenario.outside = outside
    scenario.duplicate = duplicate
    return scenario


def table_text(client, world, extension="docx") -> str:
    row = generate(client, world.headers, world.process, "TABELA")
    content = client.get(file_url(row, extension)).content
    return (docx_text if extension == "docx" else pdf_text)(content)


# --- Tabela --------------------------------------------------------------------------------


@pytest.mark.parametrize("extension", ["docx", "pdf"])
def test_the_tabela_has_only_the_valid_activity_and_no_not_scored_row(client, world, extension):
    text = table_text(client, world, extension)

    assert world.activity["title"] in text
    for title in (OUTSIDE, REJECTED, SHORT):
        assert title not in text, title
    assert text.count(world.activity["title"]) == 1  # the duplicate is not a second row
    assert not re.search(r"Não pontuada(?!s)", text)  # no row with the status; the counter stays
    assert "Não pontuadas: 0" in text


def test_the_summary_counts_only_the_valid_activity(client, world):
    row = generate(client, world.headers, world.process, "TABELA")

    assert row["summary"]["activity_count"] == 1
    assert row["summary"]["excluded"] == {}


def test_not_valid_activities_awaiting_validation_leave_no_trace_in_the_summary(
    client, world, uow_factory
):
    # SEG-01: not valid ones that are still awaiting validation are not "pendentes" either
    insert(
        uow_factory, world, title="Fora do prazo aguardando", group_number=2, item_number=7,
        event_date=date(2020, 1, 1), status=ActivityStatus.AGUARDANDO_REVISAO,
    )  # fmt: skip
    insert(
        uow_factory, world, title="Curta aguardando", group_number=4, item_number=3,
        hours=Decimal(10), status=ActivityStatus.AGUARDANDO_REVISAO,
    )  # fmt: skip

    row = generate(client, world.headers, world.process, "TABELA")

    assert row["summary"]["excluded"] == {}
    assert row["summary"]["activity_count"] == 1
    text = docx_text(client.get(file_url(row, "docx")).content)
    assert "Fora do prazo aguardando" not in text
    assert "Curta aguardando" not in text
    assert "ATIVIDADES_FORA_DO_DOCUMENTO" not in [a["code"] for a in row["alerts"]]


# --- Relatório -----------------------------------------------------------------------------


def test_the_relatorio_has_only_the_valid_activity(client, world):
    row = generate(client, world.headers, world.process, "RELATORIO")

    text = docx_text(client.get(file_url(row, "docx")).content)

    assert world.activity["title"] in text
    for title in (OUTSIDE, REJECTED, SHORT):
        assert title not in text, title
    assert row["summary"]["activity_count"] == 1


# --- Comprovante ---------------------------------------------------------------------------


def test_the_comprovante_has_no_page_whose_only_activity_is_not_valid(client, world):
    row = generate(client, world.headers, world.process, "COMPROVANTE")

    with pymupdf.open("pdf", client.get(file_url(row, "pdf")).content) as pdf:
        pages = [" ".join(page.get_text().split()) for page in pdf]
    originals = [p for p in pages if "Origem Alfa pagina" in p]
    assert len(originals) == 1
    assert "Origem Alfa pagina 1" in originals[0]
    text = " ".join(pages)
    for title in (OUTSIDE, REJECTED, SHORT):
        assert title not in text, title


# --- the merged activity (DUP-03, SEG-02) -------------------------------------------------------

MERGED_SUFFIX = " complementar"
LATER = datetime(2100, 1, 1, tzinfo=UTC)


@pytest.fixture
def merge_world(client, scenario, uow_factory):
    """The valid activity (page 1 of Alfa) and a later one with the same item and a title that
    only adds a word (page 4 of Alfa), still apart."""
    headers, process = scenario.headers, scenario.process
    later = insert(
        uow_factory, scenario, title=scenario.activity["title"] + MERGED_SUFFIX,
        group_number=2, item_number=7, status=ActivityStatus.VALIDADA, created_at=LATER,
    )  # fmt: skip
    content = source_pdf(5, label="Alfa ").tobytes()
    response = client.post(
        process_url(process, "documents"),
        files=[("file", ("alfa.pdf", content, "application/pdf"))],
        headers=headers,
    )
    assert response.status_code == 201, response.text
    [uploaded] = response.json()
    alfa = uploaded["document"]
    link(client, headers, scenario.activity["id"], alfa, 1)
    link(client, headers, str(later.id), alfa, 4)
    scenario.merged_title = later.title
    scenario.later = later
    scenario.alfa = alfa
    return scenario


def comprovante_originals(client, world) -> list[str]:
    row = generate(client, world.headers, world.process, "COMPROVANTE")
    with pymupdf.open("pdf", client.get(file_url(row, "pdf")).content) as pdf:
        pages = [" ".join(page.get_text().split()) for page in pdf]
    assert world.merged_title not in " ".join(pages)
    return [p for p in pages if "Origem Alfa pagina" in p]


def test_a_merged_activity_is_in_none_of_the_three_documents_and_the_kept_one_has_both_proofs(
    client, merge_world
):
    world = merge_world
    merged = client.post(
        f"/api/processes/{world.process['id']}/activities/merge-duplicates", headers=world.headers
    )
    assert merged.json() == {"merged": 1}, merged.text

    for kind in ("TABELA", "RELATORIO"):
        row = generate(client, world.headers, world.process, kind)
        text = docx_text(client.get(file_url(row, "docx")).content)
        assert world.merged_title not in text, kind
        assert world.activity["title"] in text, kind
        assert row["summary"]["activity_count"] == 1, kind
        if kind == "TABELA":
            assert text.count(world.activity["title"]) == 1
    originals = comprovante_originals(client, world)
    assert len(originals) == 2  # the proof of the merged one went to the kept one (DUP-01)
    assert "Origem Alfa pagina 1" in originals[0]
    assert "Origem Alfa pagina 4" in originals[1]


def test_a_page_whose_only_activity_is_merged_is_not_in_the_comprovante(
    client, merge_world, uow_factory
):
    # the merged activity keeps its page here (it was not moved) and is no duplicate by title,
    # so only the mark "merged" keeps it out
    world = merge_world
    world.merged_title = "Coordenação de projeto de extensão"
    with uow_factory() as uow:
        stored = uow.activities.get(world.later.id)
        stored.title = world.merged_title
        uow.activities.update(stored, stored.version)
        uow.activities.set_merged_into(stored, uuid.UUID(world.activity["id"]), stored.version)
        uow.commit()

    row = generate(client, world.headers, world.process, "TABELA")
    originals = comprovante_originals(client, world)

    assert world.merged_title not in docx_text(client.get(file_url(row, "docx")).content)
    assert row["summary"]["activity_count"] == 1
    assert len(originals) == 1
    assert "Origem Alfa pagina 1" in originals[0]


# --- correcting an activity brings it in on the next generation (SEG-01) ---------------------


def test_correcting_the_date_of_a_not_valid_activity_includes_it_in_the_next_generation(
    client, world, uow_factory
):
    first = generate(client, world.headers, world.process, "TABELA")
    assert OUTSIDE not in docx_text(client.get(file_url(first, "docx")).content)

    with uow_factory() as uow:
        stored = uow.activities.get(world.outside.id)
        stored.event_date = date(2023, 6, 1)
        uow.activities.update(stored, stored.version)
        uow.commit()

    second = generate(client, world.headers, world.process, "TABELA")

    assert OUTSIDE in docx_text(client.get(file_url(second, "docx")).content)
    assert second["summary"]["activity_count"] == 2


def test_a_version_generated_before_keeps_its_content(client, world, uow_factory):
    first = generate(client, world.headers, world.process, "TABELA")
    before = client.get(file_url(first, "docx")).content

    with uow_factory() as uow:
        stored = uow.activities.get(world.outside.id)
        stored.event_date = date(2023, 6, 1)
        uow.activities.update(stored, stored.version)
        uow.commit()
    generate(client, world.headers, world.process, "TABELA")

    assert client.get(file_url(first, "docx")).content == before
    assert client.get(f"/api/generated-documents/{first['id']}").json()["summary"][
        "activity_count"
    ] == 1


# --- the activity without category refuses the generation (SEG-05) -------------------------


@pytest.mark.parametrize("status", [ActivityStatus.VALIDADA, ActivityStatus.AGUARDANDO_REVISAO])
@pytest.mark.parametrize("kind", ["TABELA", "RELATORIO", "COMPROVANTE"])
def test_a_valid_activity_without_category_refuses_the_three_documents(
    client, scenario, uow_factory, kind, status
):
    insert(uow_factory, scenario, title="Sem categoria", status=status)

    response = ask(client, scenario.headers, scenario.process, kind)

    assert response.status_code == 422
    [detail] = response.json()["detail"]
    assert (detail["field"], detail["code"]) == ("geracao", "ATIVIDADE_SEM_CATEGORIA")


def test_a_not_valid_activity_without_category_does_not_refuse(client, scenario, uow_factory):
    insert(
        uow_factory, scenario, title="Rejeitada sem categoria", status=ActivityStatus.REJEITADA
    )

    assert ask(client, scenario.headers, scenario.process, "TABELA").status_code == 202
