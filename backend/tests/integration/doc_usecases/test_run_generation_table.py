"""TAB-01, VER-01, VER-02, VER-07: running the generation of the scoring table."""

import hashlib
import json
import re
import zipfile

import pymupdf
import pytest

from app.application.services.generation_inputs import load_generation_inputs
from app.domain.entities.activity import ActivityStatus
from app.domain.entities.audit import AuditAction
from app.domain.entities.comprovante import ComprovantePlan
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GenerationAlertCode,
    GenerationState,
)
from app.domain.rules.comprovante_plan import plan_comprovante
from tests.integration.doc_usecases.generation_support import (
    TOC_CAPACITY,
    add_activity,
    add_document,
    add_scenario_211,
    link,
)

SUBTOTALS = ["52,00", "7,00", "62,00", "0,00", "30,00", "4,00", "56,00"]


def generate(gen, kind=DocumentKind.TABELA):
    """Request and run one generation, as the executor would; returns the stored row."""
    world = gen.world
    requested = gen.request().execute(world.admin, world.process.id, kind)
    assert gen.run().run_next() is True
    with world.uow_factory() as uow:
        return uow.generations.get(requested.id)


def file_of(gen, generation, fmt):
    [found] = [f for f in generation.files if f.format is fmt]
    return found, gen.generated.path(generation.process_id, found.internal_name)


def docx_text(path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", " ", xml)


def pdf_text(path) -> str:
    with pymupdf.open(path) as pdf:
        return "\n".join(page.get_text() for page in pdf)


@pytest.fixture
def scenario(gen):
    add_scenario_211(gen.world)
    return gen


def test_the_scenario_ends_ready_as_version_1_with_both_files_and_the_total_211(scenario):
    gen = scenario

    done = generate(gen)

    assert (done.state, done.version_number) == (GenerationState.PRONTO, 1)
    assert sorted(f.format for f in done.files) == [DocumentFormat.DOCX, DocumentFormat.PDF]
    assert done.snapshot["total"] == "211.00"
    assert list(done.snapshot["subtotals"].values()) == [
        "0.00", "52.00", "7.00", "62.00", "0.00", "30.00", "4.00", "56.00",
    ]  # fmt: skip
    assert done.started_at is not None and done.finished_at is not None


def test_each_file_has_the_hash_and_the_size_of_what_is_stored(scenario):
    done = generate(scenario)

    for fmt in DocumentFormat:
        found, path = file_of(scenario, done, fmt)
        content = path.read_bytes()
        assert found.sha256 == hashlib.sha256(content).hexdigest()
        assert found.size_bytes == len(content) > 0
        assert found.internal_name.endswith("." + fmt.value.lower())


def test_the_second_generation_is_version_2(scenario):
    first = generate(scenario)

    second = generate(scenario)

    assert (first.version_number, second.version_number) == (1, 2)


def test_the_docx_and_the_pdf_show_the_same_total_and_subtotals(scenario):
    done = generate(scenario)

    texts = [
        docx_text(file_of(scenario, done, DocumentFormat.DOCX)[1]),
        pdf_text(file_of(scenario, done, DocumentFormat.PDF)[1]),
    ]
    for text in texts:
        assert "211,00" in text
        for subtotal in SUBTOTALS:
            assert subtotal in text


def test_the_status_event_has_hash_and_size_per_format_and_no_text(scenario):
    done = generate(scenario)

    with scenario.world.uow_factory() as uow:
        events = uow.audit.list_for("generated_document", str(done.id))
    status = [e for e in events if e.action is AuditAction.STATUS]
    assert len(status) == 1
    after = status[0].changes["files"]["after"]
    assert sorted(after, key=lambda f: f["format"]) == sorted(
        (
            {"format": f.format.value, "sha256": f.sha256, "size_bytes": f.size_bytes}
            for f in done.files
        ),
        key=lambda f: f["format"],
    )
    assert status[0].changes["state"] == {"before": "GERANDO", "after": "PRONTO"}
    assert status[0].changes["version_number"] == {"before": None, "after": 1}
    assert "Disciplina" not in json.dumps(status[0].changes)


def test_the_executor_takes_the_oldest_waiting_row_and_says_when_there_is_none(gen):
    world = gen.world
    add_activity(world)
    assert gen.run().run_next() is False
    first = gen.request().execute(world.admin, world.process.id, DocumentKind.TABELA)

    assert gen.run().run_next() is True

    with world.uow_factory() as uow:
        assert uow.generations.get(first.id).state is GenerationState.PRONTO
    assert gen.run().run_next() is False


def test_the_table_quotes_the_comprovante_numbers_and_keeps_the_plan_hash(gen):
    world = gen.world
    with_page = add_activity(world, title="Com página", item_number=3)
    add_activity(world, title="Sem página", item_number=7)
    document = add_document(world)
    link(world, with_page, document, 2)

    done = generate(gen)

    with world.uow_factory() as uow:
        inputs = load_generation_inputs(uow, uow.processes.get(world.process.id))
        plan: ComprovantePlan = plan_comprovante(inputs.layout, inputs.activities, TOC_CAPACITY)
    assert done.plan_hash == plan.plan_hash == done.snapshot["layout"]["plan_hash"]
    assert done.snapshot["layout"]["entries"][0]["pages"] == [
        {"document_id": str(document.id), "page": 2}
    ]
    text = pdf_text(file_of(gen, done, DocumentFormat.PDF)[1])
    assert text.count("sem comprovante") == 1


def test_activities_left_out_are_counted_in_the_snapshot_and_alerted(gen):
    world = gen.world
    add_activity(world)
    add_activity(world, status=ActivityStatus.AGUARDANDO_REVISAO)
    add_activity(world, status=ActivityStatus.REJEITADA)

    done = generate(gen)

    assert done.snapshot["excluded"] == {"pendentes": 1, "rejeitadas": 1}
    assert [a.code for a in done.alerts] == [GenerationAlertCode.ATIVIDADES_FORA_DO_DOCUMENTO]
    assert "1 aguardando revisão" in done.alerts[0].message


def test_a_document_outside_the_interstice_is_nowhere_in_the_generated_table(gen):
    world = gen.world
    activity = add_activity(world)
    inside = add_document(world)
    outside = add_document(world, outside=True)
    link(world, activity, inside, 1)
    link(world, activity, outside, 1)

    done = generate(gen)

    assert str(outside.id) not in json.dumps(done.snapshot)
    assert str(inside.id) in json.dumps(done.snapshot)
