"""VER-03: MAX_PAGES and MAX_MEGAPIXELS reach the upload limits through the container."""

from tests.integration.api.conftest import login
from tests.integration.api.documents_support import upload
from tests.support import synthetic_docs as synth


def results_of(response):
    return [(r["status_code"], r["code"]) for r in response.json()]


def test_max_pages_setting_limits_the_pdf_pages(make_client, admin, process):
    client = make_client(max_pages=2)
    csrf = {"X-CSRF-Token": login(client, "admin@ufpa.br")}
    three = synth.pdf_with_text(["um", "dois", "tres"])
    two = synth.pdf_with_text(["quatro", "cinco"])

    refused = upload(client, csrf, process, ("tres.pdf", three))
    accepted = upload(client, csrf, process, ("duas.pdf", two))

    assert results_of(refused) == [(422, "PAGINAS_EXCEDIDAS")]
    assert results_of(accepted) == [(201, None)]


def test_max_megapixels_setting_limits_the_pdf_page_size(make_client, admin, process):
    client = make_client(max_megapixels=5)
    csrf = {"X-CSRF-Token": login(client, "admin@ufpa.br")}

    refused = upload(client, csrf, process, ("a4.pdf", synth.pdf_with_text()))

    assert results_of(refused) == [(422, "PAGINA_GRANDE")]


def test_default_limits_accept_an_a4_page(make_client, admin, process):
    client = make_client()
    csrf = {"X-CSRF-Token": login(client, "admin@ufpa.br")}

    accepted = upload(client, csrf, process, ("a4.pdf", synth.pdf_with_text()))

    assert results_of(accepted) == [(201, None)]
