"""CMP-01 to CMP-03, CMP-09 to CMP-11: the Comprovante pdf assembled from a plan and the
original files, page by page, with incremental saves."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pymupdf
import pytest

from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    LayoutActivity,
    LayoutPage,
    PageKind,
)
from app.domain.entities.generated import GenerationAlertCode, GenerationCode
from app.domain.rules.comprovante_plan import ComprovanteRefused, plan_comprovante
from app.infrastructure.documents import emblem
from app.infrastructure.documents.comprovante_assembler import PdfComprovanteAssembler
from app.infrastructure.documents.emblem import EmblemUnavailable
from app.infrastructure.documents.front_matter import TOC_CAPACITY
from app.infrastructure.documents.source_pages import STRIP_HEIGHT
from tests.support.pdf_pages import render, source_pdf, write_image
from tests.unit.domain.comprovante_support import PROCESS_ID, make_activity
from tests.unit.infrastructure.comprovante_support import front

MB = 1024 * 1024


@dataclass
class Process:
    """A synthetic process: source files on disk, activities and the plan over them."""

    docs: dict[UUID, Path]
    names: dict[UUID, str]
    plan: ComprovantePlan
    activities: list


def build(tmp_path, spec, doc_pages=(6, 4), picture=True) -> Process:
    """`spec` is a list of (group, item, title, [(doc index, page), ...])."""
    docs, names, ids = {}, {}, []
    for index, pages in enumerate(doc_pages):
        document_id = uuid4()
        label = f"{'AB'[index]} "
        path = tmp_path / f"original_{index}.pdf"
        source_pdf(pages=pages, label=label, picture=picture).save(path)
        docs[document_id], names[document_id] = path, f"documento_{'AB'[index]}.pdf"
        ids.append(document_id)
    activities, entries = [], []
    for group, item, title, pages in spec:
        activity = make_activity(group, item, title=title)
        activities.append(activity)
        entries.append(
            LayoutActivity(
                activity.id,
                tuple(LayoutPage(ids[d], p) for d, p in pages),
                group,
                item,
            )
        )
    layout = ComprovanteLayout(PROCESS_ID, tuple(entries))
    plan = plan_comprovante(layout, activities, TOC_CAPACITY)
    return Process(docs, names, plan, activities)


THREE_GROUPS = [
    (1, 1, "Aula de teoria", [(0, 1), (0, 2)]),
    (1, 1, "Aula de prática", [(0, 2)]),  # the same page: a remission
    (2, 3, "Orientação concluída", [(1, 1)]),
    (2, 3, "Orientação sem página", []),
    (3, 2, "Projeto de extensão", [(0, 3), (1, 2)]),
]


def assemble(process: Process, target: Path, assembler=None, on_progress=None, resolver=None):
    assembler = assembler or PdfComprovanteAssembler()
    resolve = resolver or (lambda document_id: process.docs[document_id])
    return assembler.assemble(
        process.plan, front(process.names), resolve, target, on_progress
    )


def foot(page: pymupdf.Page) -> str:
    """The last text of a page: the number at its foot, in the strip or in the generated page."""
    return page.get_text().strip().splitlines()[-1]


def test_a_process_of_three_groups_and_five_activities_is_assembled_as_planned(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    target = tmp_path / "saida.pdf"

    result = assemble(process, target)

    pdf = pymupdf.open(target)
    plan = process.plan
    assert len(pdf) == result.pages == len(plan.pages)
    kinds = [p.kind for p in plan.pages]
    assert kinds[0] is PageKind.CAPA and kinds[1] is PageKind.SUMARIO
    assert kinds.count(PageKind.SEPARADOR) == 3
    assert kinds.count(PageKind.ORIGINAL) == 5  # 6 links, one of them a remission
    # continuous numbering: every page but the cover says its own number at the foot
    assert [foot(page) for page in pdf[1:]] == [
        f"Comprovante p. {n}" for n in range(2, len(plan.pages) + 1)
    ]
    assert "Comprovante p. " not in pdf[0].get_text()
    # the table of contents carries the remission and the activity without a page
    toc = " ".join(" ".join(pdf[1].get_text().split()).split())
    remission = next(e for e in plan.toc if e.title == "Aula de prática")
    assert f"ver comprovante nº {remission.sources[0].comprovante_page}, p. 2" in toc
    assert "Sem comprovante anexado" in toc
    assert [a.code for a in result.alerts] == [GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE]
    assert "Orientação sem página" in result.alerts[0].message


def test_the_attached_pages_are_identical_to_the_originals(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    target = tmp_path / "saida.pdf"
    assemble(process, target)
    pdf = pymupdf.open(target)
    sources = {document_id: pymupdf.open(path) for document_id, path in process.docs.items()}

    originals = [p for p in process.plan.pages if p.kind is PageKind.ORIGINAL]
    assert originals
    for plan_page in originals:
        out_page = pdf[plan_page.number - 1]
        area = pymupdf.Rect(0, 0, out_page.rect.width, out_page.rect.height - STRIP_HEIGHT)
        source = sources[plan_page.document_id][plan_page.source_page - 1]
        assert render(out_page, clip=area) == render(source)
        assert out_page.get_text(clip=area) == source.get_text()
        out_images = [pdf.extract_image(i[0])["image"] for i in out_page.get_images(full=True)]
        src_doc = sources[plan_page.document_id]
        src_images = [src_doc.extract_image(i[0])["image"] for i in source.get_images(full=True)]
        assert out_images == src_images and out_images


def test_the_result_has_the_size_of_the_file_and_no_temporary_file_is_left(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    target = tmp_path / "saida.pdf"

    result = assemble(process, target)

    assert result.size_bytes == target.stat().st_size
    assert sorted(p.name for p in tmp_path.iterdir() if not p.name.startswith("original_")) == [
        "saida.pdf"
    ]


def test_progress_is_reported_page_by_page_up_to_the_total(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    seen = []

    assemble(process, tmp_path / "saida.pdf", on_progress=lambda *args: seen.append(args))

    total = len(process.plan.pages)
    assert seen == [(n, total) for n in range(1, total + 1)]


def test_the_file_is_saved_every_25_pages_while_it_is_built(tmp_path):
    spec = [(1, 1, f"Atividade {n}", [(0, 1 + n)]) for n in range(60)]
    process = build(tmp_path, spec, doc_pages=(60,), picture=False)
    target = tmp_path / "saida.pdf"
    on_disk = {}

    def watch(done, total):
        if done in (24, 25, 26, 51) and target.exists():
            with pymupdf.open(target) as partial:
                on_disk[done] = len(partial)

    assemble(process, target, on_progress=watch)

    assert 24 not in on_disk  # nothing is written before the first 25 pages
    assert on_disk[26] == 25
    assert on_disk[51] == 50
    assert len(pymupdf.open(target)) == len(process.plan.pages)


def test_a_source_is_opened_once_for_each_run_of_its_pages(tmp_path):
    spec = [
        (1, 1, "Um", [(0, 1), (0, 2), (1, 1)]),
        (1, 1, "Dois", [(0, 3)]),
    ]
    process = build(tmp_path, spec)
    asked = []

    def resolve(document_id):
        asked.append(process.names[document_id])
        return process.docs[document_id]

    assemble(process, tmp_path / "saida.pdf", resolver=resolve)

    assert asked == ["documento_A.pdf", "documento_B.pdf", "documento_A.pdf"]


def test_an_output_above_the_limit_fails_and_leaves_no_file(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    probe = assemble(process, tmp_path / "probe.pdf")
    (tmp_path / "probe.pdf").unlink()
    target = tmp_path / "saida.pdf"

    ok = assemble(process, target, PdfComprovanteAssembler(max_output_bytes=probe.size_bytes))
    target.unlink()
    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, target, PdfComprovanteAssembler(max_output_bytes=probe.size_bytes - 1))

    assert ok.size_bytes == probe.size_bytes
    assert refused.value.code is GenerationCode.COMPROVANTE_GRANDE_DEMAIS
    assert [p.name for p in tmp_path.iterdir() if not p.name.startswith("original_")] == []


def test_a_missing_original_fails_naming_the_document_and_the_page_without_a_file(tmp_path):
    process = build(tmp_path, THREE_GROUPS)
    missing = next(p for p in process.plan.pages if p.kind is PageKind.ORIGINAL)
    first_file = process.docs[missing.document_id]
    first_file.unlink()
    target = tmp_path / "saida.pdf"

    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, target)

    assert refused.value.code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert refused.value.document_id == missing.document_id
    assert refused.value.page == missing.source_page
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".pdf")] == [
        p.name for p in process.docs.values() if p.exists()
    ]


def test_a_resolver_that_cannot_find_the_document_is_the_same_failure(tmp_path):
    process = build(tmp_path, THREE_GROUPS)

    def resolve(document_id):
        raise FileNotFoundError(document_id)

    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, tmp_path / "saida.pdf", resolver=resolve)

    assert refused.value.code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert not (tmp_path / "saida.pdf").exists()


def test_a_failure_after_a_saved_checkpoint_leaves_no_target_behind(tmp_path):
    # 60 originals of a 59-page document: the last page fails after two checkpoints were written
    spec = [(1, 1, f"Atividade {n}", [(0, 1 + n)]) for n in range(60)]
    process = build(tmp_path, spec, doc_pages=(59,), picture=False)
    target = tmp_path / "saida.pdf"
    written = []

    def watch(done, total):
        if done == 30 and target.exists():
            written.append(done)  # a partial file was on disk while the pages were built

    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, target, on_progress=watch)

    assert written == [30]
    assert refused.value.code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert not target.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["original_0.pdf"]


def test_an_encrypted_original_is_an_unavailable_original(tmp_path):
    process = build(tmp_path, [(1, 1, "Cifrada", [(0, 1)])], doc_pages=(2,))
    [(document_id, path)] = process.docs.items()
    with pymupdf.open(path) as plain:
        plain.save(
            tmp_path / "cifrado.pdf",
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="segredo",
            owner_pw="dono",
        )
    (tmp_path / "cifrado.pdf").replace(path)

    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, tmp_path / "saida.pdf")

    assert refused.value.code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert refused.value.document_id == document_id
    assert not (tmp_path / "saida.pdf").exists()


def test_a_page_past_the_end_of_the_original_fails_with_the_page(tmp_path):
    process = build(tmp_path, [(1, 1, "Fora", [(1, 9)])])  # document B has 4 pages

    with pytest.raises(ComprovanteRefused) as refused:
        assemble(process, tmp_path / "saida.pdf")

    assert refused.value.code is GenerationCode.ORIGINAL_INDISPONIVEL
    assert refused.value.page == 9


def test_a_justified_repeat_is_attached_again_with_its_alert(tmp_path):
    process = build(
        tmp_path,
        [(1, 1, "Primeira", [(0, 1)]), (1, 1, "Segunda", [(0, 1)])],
    )
    entries = [
        LayoutActivity(a.id, (LayoutPage(next(iter(process.docs)), 1, "Vale para as duas"),), 1, 1)
        for a in process.activities
    ]
    first = ComprovanteLayout(PROCESS_ID, tuple(entries))
    plan = plan_comprovante(first, process.activities, TOC_CAPACITY)
    again = Process(process.docs, process.names, plan, process.activities)

    result = assemble(again, tmp_path / "saida.pdf")

    assert [p.kind for p in plan.pages].count(PageKind.ORIGINAL) == 2
    assert [a.code for a in result.alerts] == [GenerationAlertCode.PAGINA_REPETIDA_JUSTIFICADA]
    assert "Segunda" in result.alerts[0].message


def test_an_image_document_is_assembled_as_a_page_and_a_raster_page_keeps_its_alert(tmp_path):
    photo_id, rotated_id = uuid4(), uuid4()
    photo = tmp_path / "foto.jpg"
    write_image(photo, "JPEG", (600, 800), dpi=150)
    rotated = source_pdf(pages=1, label="C ")
    rotated[0].set_cropbox(pymupdf.Rect(40, 60, 500, 700))
    rotated[0].set_rotation(90)
    rotated_path = tmp_path / "girado.pdf"
    rotated.save(rotated_path)
    activity = make_activity(1, 1, title="Com imagem")
    layout = ComprovanteLayout(
        PROCESS_ID,
        (
            LayoutActivity(
                activity.id, (LayoutPage(photo_id, 1), LayoutPage(rotated_id, 1)), 1, 1
            ),
        ),
    )
    plan = plan_comprovante(layout, [activity], TOC_CAPACITY)
    files = {photo_id: photo, rotated_id: rotated_path}
    names = {photo_id: "foto.jpg", rotated_id: "girado.pdf"}
    target = tmp_path / "saida.pdf"

    result = PdfComprovanteAssembler().assemble(
        plan, front(names), lambda document_id: files[document_id], target
    )

    pdf = pymupdf.open(target)
    assert len(pdf) == len(plan.pages)
    first = plan.toc[-1].sources[0].comprovante_page
    assert (pdf[first - 1].rect.width, pdf[first - 1].rect.height) == (288.0, 384.0 + STRIP_HEIGHT)
    assert [a.code for a in result.alerts] == [GenerationAlertCode.PAGINA_RASTERIZADA]
    assert "girado.pdf" in result.alerts[0].message


def test_without_the_emblem_the_assembly_fails_and_leaves_no_file(monkeypatch, tmp_path):
    # BRAS-10, BRAS-03
    process = build(tmp_path, THREE_GROUPS)
    monkeypatch.setattr(emblem, "EMBLEM_FILE", tmp_path / "ufpa.png")
    target = tmp_path / "saida.pdf"

    with pytest.raises(EmblemUnavailable):
        assemble(process, target)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["original_0.pdf", "original_1.pdf"]


def test_the_assembled_comprovante_has_the_emblem_only_on_its_cover(tmp_path):
    # BRAS-03, BRAS-07
    process = build(tmp_path, THREE_GROUPS)
    target = tmp_path / "saida.pdf"

    result = assemble(process, target)

    pdf = pymupdf.open(target)
    generated_pages = [p.number - 1 for p in process.plan.pages if p.kind is not PageKind.ORIGINAL]
    assert len(pdf) == result.pages == len(process.plan.pages)
    with_emblem = [
        number
        for number in generated_pages
        if any(
            round(rect.width) == 57
            for image in pdf[number].get_images(full=True)
            for rect in pdf[number].get_image_rects(image[0])
        )
    ]
    assert with_emblem == [0]
