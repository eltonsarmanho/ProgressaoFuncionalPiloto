"""The PDF of the Comprovante, built page by page from the plan (CMP-01 to CMP-03, CMP-09 to
CMP-11).

The generated pages (cover, table of contents, separators) come from one reportlab PDF and the
original pages from their files, one source open at a time. The output is saved every
`CHECKPOINT_PAGES` pages and reopened, so the objects already written leave the memory (the
prototype of the design peaked at 74 MB on 411 pages); a last full pass with `garbage=3` and
`deflate=True` writes the final file, which must not pass `max_output_bytes`. Nothing is left
at the target path when the assembly fails.
"""

import os
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

import pymupdf

from app.domain.entities.comprovante import ComprovantePlan, PageKind, PlanAlert
from app.domain.entities.generated import GenerationAlert, GenerationAlertCode, GenerationCode
from app.domain.repositories.ports import AssemblyResult, ComprovanteFront
from app.domain.rules.comprovante_plan import ComprovanteRefused
from app.domain.rules.upload_validation import FileKind, detect_kind
from app.infrastructure.documents.front_matter import write_front_matter
from app.infrastructure.documents.source_pages import attach, attach_image

CHECKPOINT_PAGES = 25
MAX_OUTPUT_BYTES = 60 * 1024 * 1024
_STORE_SHRINK_PERCENT = 100
_SIGNATURE_BYTES = 16
_UNKNOWN_DOCUMENT = "documento"


def _plan_alert(
    alert: PlanAlert, plan: ComprovantePlan, front: ComprovanteFront
) -> GenerationAlert:
    title = next((e.title for e in plan.toc if e.activity_id == alert.activity_id), "")
    if alert.code is GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE:
        return GenerationAlert(alert.code, f'A atividade "{title}" não tem comprovante anexado.')
    name = front.document_names.get(alert.document_id, _UNKNOWN_DOCUMENT)
    return GenerationAlert(
        alert.code,
        f'A página {alert.page} de {name} foi repetida na atividade "{title}": '
        f"{alert.justification}",
    )


class _Sources:
    """The original being read: opened when a page asks for it and kept for the run of pages
    that follow, closed when another document comes (one source open at a time)."""

    def __init__(self, resolver: Callable[[UUID], Path], front: ComprovanteFront) -> None:
        self._resolver = resolver
        self._front = front
        self._current: UUID | None = None
        self._path: Path | None = None
        self._pdf: pymupdf.Document | None = None

    def _unavailable(self, document_id: UUID, page: int) -> ComprovanteRefused:
        return ComprovanteRefused(
            GenerationCode.ORIGINAL_INDISPONIVEL,
            f"O documento {self._front.document_names.get(document_id, document_id)} "
            f"não está disponível (página {page}).",
            document_id,
            page,
        )

    def _open(self, document_id: UUID, page: int) -> None:
        self.close()
        try:
            path = self._resolver(document_id)
            if not path.is_file():
                raise FileNotFoundError(path)
            with path.open("rb") as handle:
                kind = detect_kind(handle.read(_SIGNATURE_BYTES))
            if kind is FileKind.PDF:
                self._pdf = pymupdf.open(path, filetype="pdf")
                if self._pdf.needs_pass:
                    raise ValueError("encrypted")
            elif kind not in (FileKind.JPEG, FileKind.PNG):
                raise ValueError("unknown file")
        except (OSError, KeyError, ValueError, RuntimeError) as error:
            raise self._unavailable(document_id, page) from error
        self._current, self._path = document_id, path

    def attach(self, out: pymupdf.Document, document_id: UUID, page: int, number: int):
        """Appends the page; returns the alert of the page when it raised one."""
        if self._current != document_id:
            self._open(document_id, page)
        name = self._front.document_names.get(document_id, _UNKNOWN_DOCUMENT)
        if self._pdf is None:
            if page != 1:
                raise self._unavailable(document_id, page)
            attach_image(out, self._path, number, document_id=document_id)
            return None
        if not 1 <= page <= len(self._pdf):
            raise self._unavailable(document_id, page)
        return attach(out, self._pdf, page - 1, number, name)

    def close(self) -> None:
        if self._pdf is not None:
            self._pdf.close()
        self._current = self._path = self._pdf = None


class PdfComprovanteAssembler:
    """Implements the `ComprovanteAssembler` port with PyMuPDF and reportlab."""

    def __init__(
        self, max_output_bytes: int = MAX_OUTPUT_BYTES, checkpoint_pages: int = CHECKPOINT_PAGES
    ) -> None:
        self._max_output_bytes = max_output_bytes
        self._checkpoint_pages = checkpoint_pages

    def assemble(
        self,
        plan: ComprovantePlan,
        front: ComprovanteFront,
        resolver: Callable[[UUID], Path],
        target: Path,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> AssemblyResult:
        front_path = target.with_name(target.name + ".front")
        final_path = target.with_name(target.name + ".final")
        sources = _Sources(resolver, front)
        try:
            write_front_matter(plan, front, front_path)
            alerts = self._build(plan, front, sources, front_path, target, final_path, on_progress)
            size = final_path.stat().st_size
            if size > self._max_output_bytes:
                raise ComprovanteRefused(
                    GenerationCode.COMPROVANTE_GRANDE_DEMAIS,
                    f"O Comprovante tem {size // (1024 * 1024)} MB; o limite é "
                    f"{self._max_output_bytes // (1024 * 1024)} MB.",
                )
            os.replace(final_path, target)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        finally:
            sources.close()
            front_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
        plan_alerts = tuple(_plan_alert(alert, plan, front) for alert in plan.alerts)
        return AssemblyResult(len(plan.pages), size, plan_alerts + tuple(alerts))

    def _build(
        self, plan, front, sources, front_path, target, final_path, on_progress
    ) -> list[GenerationAlert]:
        alerts: list[GenerationAlert] = []
        generated = pymupdf.open(front_path)
        out = pymupdf.open()
        saved = False
        try:
            next_generated = 0
            for number, page in enumerate(plan.pages, start=1):
                if page.kind is PageKind.ORIGINAL:
                    found = sources.attach(out, page.document_id, page.source_page, number)
                    if found is not None:
                        alerts.append(found)
                else:
                    out.insert_pdf(generated, from_page=next_generated, to_page=next_generated)
                    next_generated += 1
                pymupdf.TOOLS.store_shrink(_STORE_SHRINK_PERCENT)
                if number % self._checkpoint_pages == 0 and number < len(plan.pages):
                    out = self._checkpoint(out, target, saved)
                    saved = True
                if on_progress is not None:
                    on_progress(number, len(plan.pages))
            out.save(final_path, garbage=3, deflate=True)
        finally:
            out.close()
            generated.close()
        return alerts

    @staticmethod
    def _checkpoint(out: pymupdf.Document, target: Path, saved: bool) -> pymupdf.Document:
        """Writes what was built so far and reopens the file, so the memory of the pages already
        written is released: `save` the first time, `saveIncr` after that."""
        if saved:
            out.saveIncr()
        else:
            out.save(target)
        out.close()
        return pymupdf.open(target)
