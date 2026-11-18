"""VER-03: MAX_PAGES and MAX_MEGAPIXELS reach the upload limits through the container."""

import uuid

from app.domain.repositories.ports import JobStatus, ProcessingJob
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import seed_document, upload
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


def test_max_job_attempts_setting_reaches_the_recovery_of_stuck_jobs(
    make_client, admin, process, uow_factory, clock
):
    client = make_client(max_job_attempts=1)
    user, _ = admin
    document = seed_document(uow_factory, process, user)
    job = ProcessingJob(
        id=uuid.uuid4(), document_id=document.id, status=JobStatus.PROCESSANDO, attempts=1
    )
    with uow_factory() as uow:
        uow.jobs.add(job)
        uow.commit()

    requeued = client.app.state.container.recover_stuck_jobs.execute()

    assert requeued == 0
    with uow_factory() as uow:
        assert uow.jobs.get(job.id).status is JobStatus.FALHOU
        assert uow.documents.get(document.id).status_code == "TENTATIVAS_ESGOTADAS"
