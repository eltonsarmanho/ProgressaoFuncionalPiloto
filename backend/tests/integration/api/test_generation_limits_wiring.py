"""CMP-09, CMP-13 (T119): GENERATION_MAX_PAGES, GENERATION_PNG_MAX_MEGAPIXELS and
GENERATION_MAX_OUTPUT_MB reach the limits of the request and of the assembler through the
container."""

import io
import os
import types
import uuid

from PIL import Image

from app.domain.entities.generated import GenerationCode, GenerationState
from tests.integration.api.conftest import login
from tests.integration.api.documents_support import upload
from tests.integration.api.generated_support import (
    add_document_row,
    ask,
    link_page,
    run_executor,
)


def png_bytes(width: int, height: int, noise: bool = False) -> bytes:
    if noise:
        image = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    else:
        image = Image.new("RGB", (width, height), (240, 240, 240))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def refusal(response) -> tuple[int, str]:
    return response.status_code, response.json()["detail"][0]["code"]


def link_png(uow_factory, client, headers, scenario, content: bytes) -> None:
    """Uploads the PNG to the process and links its page 1 to the activity of the scenario."""
    response = upload(client, headers, scenario.process, ("foto.png", content, "image/png"))
    assert response.status_code == 201, response.text
    [result] = response.json()
    assert result["status_code"] == 201, result
    document = types.SimpleNamespace(id=uuid.UUID(result["document"]["id"]))
    link_page(uow_factory, scenario.user, scenario.activity, document, 1)


def test_generation_max_pages_limits_the_pages_the_request_accepts(
    make_client, scenario, uow_factory
):
    document = add_document_row(uow_factory, scenario.process, scenario.user, pages=3)
    for page in (1, 2, 3):
        link_page(uow_factory, scenario.user, scenario.activity, document, page)
    tight = make_client(generation_max_pages=2)
    default = make_client()
    tight_headers = {"X-CSRF-Token": login(tight, "admin@ufpa.br")}
    default_headers = {"X-CSRF-Token": login(default, "admin@ufpa.br")}

    refused = ask(tight, tight_headers, scenario.process, "COMPROVANTE")
    passed_the_limit = ask(default, default_headers, scenario.process, "COMPROVANTE")

    assert refusal(refused) == (422, "COMPROVANTE_GRANDE_DEMAIS")
    # the same three pages pass the default limit of 400 and stop later, at the missing file
    assert refusal(passed_the_limit) == (422, "ORIGINAL_INDISPONIVEL")


def test_generation_png_max_megapixels_limits_the_png_the_request_accepts(
    make_client, scenario, uow_factory
):
    tight = make_client(generation_png_max_megapixels=1)
    headers = {"X-CSRF-Token": login(tight, "admin@ufpa.br")}
    link_png(uow_factory, tight, headers, scenario, png_bytes(1200, 1000))  # 1.2 megapixels
    default = make_client()
    default_headers = {"X-CSRF-Token": login(default, "admin@ufpa.br")}

    refused = ask(tight, headers, scenario.process, "COMPROVANTE")
    accepted = ask(default, default_headers, scenario.process, "COMPROVANTE")

    assert refusal(refused) == (422, "IMAGEM_GRANDE_DEMAIS")
    assert accepted.status_code == 202


def test_generation_max_output_mb_limits_the_size_of_the_comprovante_the_assembler_writes(
    make_client, scenario, uow_factory
):
    tight = make_client(generation_max_output_mb=1)
    headers = {"X-CSRF-Token": login(tight, "admin@ufpa.br")}
    link_png(uow_factory, tight, headers, scenario, png_bytes(600, 600, noise=True))  # about 1.1 MB
    default = make_client()
    default_headers = {"X-CSRF-Token": login(default, "admin@ufpa.br")}

    refused = ask(tight, headers, scenario.process, "COMPROVANTE")
    assert refused.status_code == 202
    assert run_executor(tight) is True
    closed = tight.get(f"/api/generated-documents/{refused.json()['id']}").json()
    accepted = ask(default, default_headers, scenario.process, "COMPROVANTE")
    assert run_executor(default) is True
    done = default.get(f"/api/generated-documents/{accepted.json()['id']}").json()

    assert (closed["state"], closed["error_code"]) == (
        GenerationState.FALHOU.value,
        GenerationCode.COMPROVANTE_GRANDE_DEMAIS.value,
    )
    assert done["state"] == GenerationState.PRONTO.value
