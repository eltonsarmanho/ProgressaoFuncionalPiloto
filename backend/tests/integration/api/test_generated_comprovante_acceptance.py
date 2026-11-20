"""CMP-01, CMP-03, CMP-04, CMP-05, CMP-07, ARR-03, ARR-04 (T90): a synthetic Comprovante asked
through the API, with its arrangement changed, downloaded and read back.

Three groups and five activities: II.7 has A1 (pages 1 and 2 of Alfa) and A2 (page 1 of Alfa
again and page 1 of Beta), IV.4 has A3 (pages 2 and 3 of Beta), VI.6 has A4 (page 4 of Alfa) and
A5 (no page). The user turns the pages of A1 around and takes page 3 of Beta out of A3.
"""

import re

import pymupdf
import pytest

from tests.integration.api.generated_readers import pdf_text
from tests.integration.api.generated_support import (
    add_activity,
    file_url,
    generate,
    process_url,
)
from tests.support.pdf_pages import max_difference, render, source_pdf

FOOTER_HEIGHT = 24  # the strip added under every original page
PAGE_COUNT = {"Alfa": 4, "Beta": 3}


def upload_source(client, headers, process, name):
    """Uploads a synthetic PDF with a text and a picture on each page; returns the document and
    the bytes."""
    content = source_pdf(PAGE_COUNT[name], label=f"{name} ").tobytes()
    response = client.post(
        process_url(process, "documents"),
        files=[("file", (f"{name.lower()}.pdf", content, "application/pdf"))],
        headers=headers,
    )
    assert response.status_code == 201, response.text
    [result] = response.json()
    return result["document"], content


def link(client, headers, activity, document, page):
    response = client.post(
        f"/api/activities/{activity['id']}/evidences",
        json={"document_id": document["id"], "page": page},
        headers=headers,
    )
    assert response.status_code == 201, response.text


@pytest.fixture
def world(client, scenario):
    """The processed arrangement: activities, documents, links and the original bytes."""
    headers, process = scenario.headers, scenario.process
    a1 = scenario.activity
    a1_title = a1["title"]
    a2 = add_activity(client, headers, process, title="Atividade A2", event_date="2023-06-10")
    a3 = add_activity(client, headers, process, title="Atividade A3", group_number=4, item_number=4)
    a4 = add_activity(client, headers, process, title="Atividade A4", group_number=6, item_number=6)
    a5 = add_activity(
        client, headers, process, title="Atividade A5", group_number=6, item_number=6,
        event_date="2023-09-10",
    )  # fmt: skip
    alfa, alfa_bytes = upload_source(client, headers, process, "Alfa")
    beta, beta_bytes = upload_source(client, headers, process, "Beta")
    for activity, document, page in [
        (a1, alfa, 1), (a1, alfa, 2), (a2, alfa, 1), (a2, beta, 1),
        (a3, beta, 2), (a3, beta, 3), (a4, alfa, 4),
    ]:  # fmt: skip
        link(client, headers, activity, document, page)
    scenario.activities = {"A1": a1, "A2": a2, "A3": a3, "A4": a4, "A5": a5}
    scenario.titles = {"A1": a1_title}
    scenario.docs = {"Alfa": alfa, "Beta": beta}
    scenario.sources = {"Alfa": alfa_bytes, "Beta": beta_bytes}
    return scenario


def layout_url(world):
    return process_url(world.process, "comprovante-layout")


def page_ref(world, name, page):
    return {"document_id": world.docs[name]["id"], "page": page}


def arrange(client, world):
    """Reorders the two pages of A1 and takes page 3 of Beta out of A3; every other activity
    stays as derived."""
    derived = client.get(layout_url(world)).json()
    assert derived["saved"] is False
    by_activity = {a["activity_id"]: a["pages"] for a in derived["layout"]["activities"]}
    pages = {key: [dict(p) for p in by_activity[a["id"]]]
             for key, a in world.activities.items()}  # fmt: skip
    pages["A1"] = [page_ref(world, "Alfa", 2), page_ref(world, "Alfa", 1)]
    pages["A3"] = [page_ref(world, "Beta", 2)]
    body = {
        "expected_version": 0,
        "activities": [
            {"activity_id": world.activities[key]["id"], "pages": value}
            for key, value in pages.items()
        ],
    }
    response = client.put(layout_url(world), json=body, headers=world.headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def comprovante(client, world):
    saved = arrange(client, world)
    row = generate(client, world.headers, world.process, "COMPROVANTE")
    download = client.get(file_url(row, "pdf"))
    assert download.status_code == 200
    return world, saved, row, download.content


def originals_of(pdf: pymupdf.Document) -> list[str]:
    """The `Origem <label>pagina N` text of every page that carries one, in order."""
    found = []
    for page in pdf:
        match = re.search(r"Origem (\w+) pagina (\d)", " ".join(page.get_text().split()))
        if match:
            found.append(f"{match.group(1)} {match.group(2)}")
    return found


def test_the_pdf_has_the_order_the_continuous_numbers_the_toc_the_remission_and_the_alert(
    comprovante,
):
    world, saved, row, content = comprovante

    with pymupdf.open("pdf", content) as pdf:
        pages = [" ".join(page.get_text().split()) for page in pdf]
        order = originals_of(pdf)
    # group II (A1 turned around, A2 with Beta 1 and a remission to Alfa 1), IV, VI
    assert order == ["Alfa 2", "Alfa 1", "Beta 1", "Beta 2", "Alfa 4"]
    assert "COMPROVANTE DE DOCUMENTOS" in pages[0]
    assert "SUMÁRIO" in pages[1]
    for number, text in enumerate(pages[1:], start=2):
        assert f"Comprovante p. {number}" in text, number  # continuous, from the cover
    numbers = {p["number"]: p for p in saved["plan"]["pages"]}
    assert len(pages) == len(numbers)
    originals = [numbers[n] for n in sorted(numbers) if numbers[n]["kind"] == "ORIGINAL"]
    assert [
        (o["document_id"], o["source_page"], o["number"]) for o in originals
    ] == [
        (world.docs["Alfa"]["id"], 2, 4), (world.docs["Alfa"]["id"], 1, 5),
        (world.docs["Beta"]["id"], 1, 6), (world.docs["Beta"]["id"], 2, 8),
        (world.docs["Alfa"]["id"], 4, 10),
    ]  # fmt: skip
    toc = pages[1]
    for title, first in [("Atividade A2", 6), ("Atividade A3", 8), ("Atividade A4", 10)]:
        assert re.search(rf"{title} {first}\b", toc), title
    assert re.search(rf"{world.titles['A1']} 4\b", toc)
    assert "ver comprovante nº 5, p. 1" in toc  # A2 points at the copy of Alfa 1 under A1
    assert "Sem comprovante anexado" in toc  # A5
    [alert] = [a for a in row["alerts"] if a["code"] == "ATIVIDADE_SEM_COMPROVANTE"]
    assert alert["message"]
    assert [a["code"] for a in saved["alerts"]] == []


def test_every_attached_page_is_the_original_with_a_strip_under_it(comprovante):
    world, saved, _, content = comprovante
    sources = {
        world.docs[name]["id"]: pymupdf.open("pdf", data) for name, data in world.sources.items()
    }
    originals = [p for p in saved["plan"]["pages"] if p["kind"] == "ORIGINAL"]

    with pymupdf.open("pdf", content) as pdf:
        for entry in originals:
            source = sources[entry["document_id"]][entry["source_page"] - 1]
            out = pdf[entry["number"] - 1]
            area = pymupdf.Rect(0, 0, source.rect.width, source.rect.height)
            assert out.rect.height == pytest.approx(source.rect.height + FOOTER_HEIGHT)
            assert max_difference(render(out, clip=area), render(source)) == 0, entry
            assert source.get_text().split() == out.get_textbox(area).split()
            assert f"Comprovante p. {entry['number']}" in out.get_text()


def test_the_page_taken_out_of_the_arrangement_is_missing_but_still_linked(client, comprovante):
    world, saved, _, content = comprovante

    assert "Beta pagina 3" not in pdf_text(content)
    [entry] = [
        a for a in saved["layout"]["activities"] if a["activity_id"] == world.activities["A3"]["id"]
    ]
    assert [p["page"] for p in entry["pages"]] == [2]
    activity = client.get(f"/api/activities/{world.activities['A3']['id']}").json()
    assert sorted(e["page"] for e in activity["evidences"]) == [2, 3]  # the link stays (Etapa 3)


def test_the_new_order_of_the_arrangement_is_the_one_of_the_pdf(comprovante):
    world, saved, _, content = comprovante

    [entry] = [
        a for a in saved["layout"]["activities"] if a["activity_id"] == world.activities["A1"]["id"]
    ]
    saved_order = [p["page"] for p in entry["pages"]]
    with pymupdf.open("pdf", content) as pdf:
        in_pdf = [m for m in originals_of(pdf) if m.startswith("Alfa")][:2]
    assert saved_order == [2, 1]
    assert in_pdf == ["Alfa 2", "Alfa 1"]
