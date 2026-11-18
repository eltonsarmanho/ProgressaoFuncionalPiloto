"""Generated documents: the request, the run in the background, the recovery and the versions.

Access follows the process (AccessPolicy): anything outside it is NotFound, never Forbidden.
Audit events carry identifiers, kinds, states and codes only, never the text of a document
(VER-07).
"""

import hashlib
import logging
import resource
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.scoring import _ScoringUseCase
from app.domain.entities.audit import AuditAction
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    PageKind,
    SourceDocument,
    TocLevel,
)
from app.domain.entities.document import Document
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationAlert,
    GenerationAlertCode,
    GenerationCode,
    GenerationState,
)
from app.domain.entities.report import ReportDraft
from app.domain.entities.user import User
from app.domain.errors import GenerationRefused, NotFound
from app.domain.repositories.ports import (
    Clock,
    ComprovanteAssembler,
    ComprovanteFront,
    DocumentWriter,
    FileInspector,
    FileStorage,
    GeneratedFileStorage,
    ReportConfigProvider,
    UnitOfWork,
)
from app.domain.rules.comprovante_plan import (
    ComprovanteRefused,
    check_comprovante,
    plan_comprovante,
)
from app.domain.rules.generation_snapshot import build_snapshot
from app.domain.rules.report_document import build_report_document
from app.domain.rules.report_draft import (
    STALE,
    STALE_MESSAGE,
    document_sections,
    propose_draft,
    reconcile_draft,
)
from app.domain.rules.table_document import build_table_document

logger = logging.getLogger("app.documents.generation")

GENERATED_ENTITY = "generated_document"
MB = 1024 * 1024
_PIXELS_PER_MEGAPIXEL = 1_000_000


@dataclass(frozen=True)
class GenerationLimits:
    """What a request may ask for (CMP-09, CMP-13, DEL-11); the defaults are the spec values."""

    max_pages: int = 400
    png_max_megapixels: int = 12
    min_free_bytes: int = 200 * MB


def _png_pixels(
    originals: FileStorage, inspector: FileInspector, document: Document
) -> int | None:
    """Width times height of a PNG original that is still stored; None when it cannot be told."""
    path = originals.path(document.process_id, document.internal_name)
    if not path.is_file():
        return None
    megapixels = inspector.inspect(path).megapixels
    return None if megapixels is None else int(megapixels * _PIXELS_PER_MEGAPIXEL)


def checked_comprovante_plan(
    inputs: GenerationInputs,
    originals: FileStorage,
    inspector: FileInspector,
    limits: GenerationLimits,
    toc_capacity: int,
) -> ComprovantePlan:
    """The plan of the Comprovante, or the refusal that says why it cannot be built (CMP-09,
    CMP-10, CMP-13, DEL-11). Used by the request and again by the run, because an original can
    go away between the two."""
    plan = plan_comprovante(inputs.layout, inputs.activities, toc_capacity)
    attached = [p for p in plan.pages if p.kind is PageKind.ORIGINAL]
    used = {p.document_id for p in attached}
    sources = [
        SourceDocument(
            id=d.id,
            original_name=d.original_name,
            page_count=d.page_count,
            mime=d.mime,
            pixels=(
                _png_pixels(originals, inspector, d)
                if d.mime == "image/png" and d.id in used and d.file_deleted_at is None
                else None
            ),
            file_deleted=d.file_deleted_at is not None,
        )
        for d in inputs.documents
    ]
    check_comprovante(
        plan,
        sources,
        max_pages=limits.max_pages,
        png_max_megapixels=limits.png_max_megapixels,
    )
    known = {d.id: d for d in inputs.documents}
    for page in attached:
        document = known[page.document_id]
        if not originals.path(document.process_id, document.internal_name).is_file():
            raise ComprovanteRefused(
                GenerationCode.ORIGINAL_INDISPONIVEL,
                f"O documento {document.original_name} não está disponível "
                f"(página {page.source_page}).",
                document.id,
                page.source_page,
            )
    return plan


class RequestGeneration(_ScoringUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        clock: Clock,
        storage: GeneratedFileStorage,
        originals: FileStorage,
        inspector: FileInspector,
        limits: GenerationLimits,
        toc_capacity: int,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._clock = clock
        self._storage = storage
        self._originals = originals
        self._inspector = inspector
        self._limits = limits
        self._toc_capacity = toc_capacity

    def execute(self, actor: User, process_id: UUID, kind: DocumentKind) -> GeneratedDocument:
        """Stores a GERANDO row for the executor to pick up (TAB-01, VER-04).

        A second request of the same kind while one is GERANDO is a 409 with the code
        `GERACAO_EM_ANDAMENTO`, raised by the repository without a race.
        """
        with self._uow_factory() as uow:
            process = self._readable(uow, actor, process_id)
            inputs = load_generation_inputs(uow, process)
            if inputs.version is None:
                raise GenerationRefused(
                    GenerationCode.TABELA_NAO_ESCOLHIDA,
                    "Escolha a tabela de pontuação do processo antes de gerar.",
                )
            if not inputs.activities:
                raise GenerationRefused(
                    GenerationCode.SEM_ATIVIDADES_VALIDADAS,
                    "O processo não tem atividade validada.",
                )
            if kind is DocumentKind.RELATORIO:
                for activity in inputs.activities:
                    if not activity.title.strip() and not activity.description.strip():
                        raise GenerationRefused(
                            GenerationCode.ATIVIDADE_SEM_DESCRICAO,
                            f"A atividade {activity.id} não tem título nem descrição.",
                        )
            if self._storage.free_bytes() < self._limits.min_free_bytes:
                raise GenerationRefused(
                    GenerationCode.ESPACO_INSUFICIENTE,
                    "Não há espaço livre suficiente no servidor para gerar o documento.",
                )
            if kind is DocumentKind.COMPROVANTE:
                checked_comprovante_plan(
                    inputs, self._originals, self._inspector, self._limits, self._toc_capacity
                )
            generation = GeneratedDocument(
                id=uuid.uuid4(),
                process_id=process.id,
                kind=kind,
                state=GenerationState.GERANDO,
                version_number=None,
                requested_by=actor.id,
                requested_at=self._clock.now(),
            )
            uow.generations.add(generation)
            self._audit.record(
                uow,
                actor.id,
                GENERATED_ENTITY,
                generation.id,
                AuditAction.CREATE,
                {},
                {"kind": kind, "state": generation.state},
            )
            uow.commit()
            return generation


_LEFT_OUT_LABELS = {
    "pendentes": "aguardando revisão",
    "rejeitadas": "rejeitadas",
    "sem_enquadramento": "sem enquadramento na tabela",
}
_FORMATS = (DocumentFormat.DOCX, DocumentFormat.PDF)
_CHUNK = 1024 * 1024
_PROGRESS_EVERY = 50


@dataclass
class _Produced:
    """What a kind wrote: the temporary files by format, the snapshot and the alerts."""

    outputs: list[tuple[DocumentFormat, Path]]
    snapshot: dict[str, Any]
    alerts: list[GenerationAlert]
    plan_hash: str | None = None


def _digest(path: Path) -> tuple[str, int]:
    """SHA-256 and size of a file, read in chunks (a Comprovante has up to 60 MB)."""
    hasher, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def _left_out_alert(inputs: GenerationInputs) -> list[GenerationAlert]:
    if not inputs.excluded:
        return []
    parts = "; ".join(f"{n} {_LEFT_OUT_LABELS[reason]}" for reason, n in inputs.excluded.items())
    return [
        GenerationAlert(
            GenerationAlertCode.ATIVIDADES_FORA_DO_DOCUMENTO,
            f"Atividades fora do documento: {parts}.",
        )
    ]


def _layout_snapshot(layout: ComprovanteLayout, plan: ComprovantePlan) -> dict[str, Any]:
    """The arrangement the Tabela and the Comprovante were numbered from (VER-02)."""
    entries = []
    for entry in layout.activities:
        pages = []
        for page in entry.pages:
            found: dict[str, Any] = {"document_id": str(page.document_id), "page": page.page}
            if page.repeat_justification:
                found["justification"] = page.repeat_justification
            pages.append(found)
        entries.append({"activity_id": str(entry.activity_id), "pages": pages})
    return {"plan_hash": plan.plan_hash, "entries": entries}


_OTHER_KIND = {
    DocumentKind.TABELA: DocumentKind.COMPROVANTE,
    DocumentKind.COMPROVANTE: DocumentKind.TABELA,
}
_NUMBERING_TEXT = {
    DocumentKind.TABELA: "O Comprovante mais recente foi numerado de outro modo que esta Tabela.",
    DocumentKind.COMPROVANTE: (
        "A Tabela de Pontuação mais recente cita uma numeração diferente deste Comprovante."
    ),
}


def _numbering_alert(
    kind: DocumentKind, plan: ComprovantePlan, latest: Mapping[DocumentKind, GeneratedDocument]
) -> list[GenerationAlert]:
    """The Tabela cites page numbers of the Comprovante: when the latest version of the other
    document was numbered from another plan, the two disagree (NUMERACAO_DIVERGENTE)."""
    other = latest.get(_OTHER_KIND[kind])
    if other is None or other.plan_hash == plan.plan_hash:
        return []
    return [GenerationAlert(GenerationAlertCode.NUMERACAO_DIVERGENTE, _NUMBERING_TEXT[kind])]


_FAILURE_MESSAGES: Mapping[GenerationCode, str] = {
    GenerationCode.ORIGINAL_INDISPONIVEL: (
        "Um documento de origem não está mais disponível no armazenamento."
    ),
    GenerationCode.COMPROVANTE_GRANDE_DEMAIS: (
        "O Comprovante passa do limite de páginas ou de tamanho."
    ),
    GenerationCode.IMAGEM_GRANDE_DEMAIS: "Uma imagem de origem passa do limite de megapixels.",
    GenerationCode.ORIGINAIS_EXCLUIDOS: "Os documentos de entrada deste processo foram excluídos.",
    GenerationCode.TABELA_NAO_ESCOLHIDA: "O processo não tem tabela de pontuação escolhida.",
    GenerationCode.ERRO_INTERNO: "Erro interno ao gerar o documento. Tente gerar de novo.",
}


class _Scratch:
    """The files a run has written so far, to remove them when the run fails (VER-05)."""

    def __init__(self, storage: GeneratedFileStorage, process_id: UUID) -> None:
        self._storage = storage
        self._process_id = process_id
        self._temps: list[Path] = []
        self._names: list[str] = []

    def new_temp(self) -> Path:
        path = self._storage.new_temp_path(self._process_id)
        self._temps.append(path)
        return path

    def commit(self, temp: Path, extension: str) -> str:
        name = self._storage.commit(self._process_id, temp, extension)
        self._names.append(name)
        return name

    def discard(self) -> None:
        """Removes the temporary files and the ones already renamed; never raises."""
        for temp in self._temps:
            temp.unlink(missing_ok=True)
        for name in self._names:
            try:
                self._storage.delete(self._process_id, name)
            except OSError:
                logger.error("cleanup process_id=%s failed", self._process_id)


def _unique(codes: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(codes))


class RunGeneration:
    """The executor side of a generation: builds the document, stores the files and closes the
    row as PRONTO with the next version number (VER-01, VER-02)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        clock: Clock,
        storage: GeneratedFileStorage,
        writer: DocumentWriter,
        assembler: ComprovanteAssembler,
        report_config: ReportConfigProvider,
        originals: FileStorage,
        inspector: FileInspector,
        limits: GenerationLimits,
        toc_capacity: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._audit = audit
        self._clock = clock
        self._storage = storage
        self._writer = writer
        self._assembler = assembler
        self._report_config = report_config
        self._originals = originals
        self._inspector = inspector
        self._limits = limits
        self._toc_capacity = toc_capacity

    def run_next(self) -> bool:
        """The runner of the executor: claims the oldest waiting row and runs it; False when
        there is none."""
        with self._uow_factory() as uow:
            claimed = uow.generations.claim_next(self._clock.now())
            uow.commit()
        if claimed is None:
            return False
        self.execute(claimed.id)
        return True

    def execute(self, generation_id: UUID) -> None:
        """Builds and stores the document of a claimed row. A failure at any point removes what
        was written and closes the row as FALHOU, so the executor never has to (VER-05)."""
        started = time.monotonic()
        with self._uow_factory() as uow:
            generation = uow.generations.get(generation_id)
        if generation is None:
            raise NotFound("Geração não encontrada")
        scratch = _Scratch(self._storage, generation.process_id)
        try:
            files, done = self._build_and_close(generation, scratch)
        except Exception as error:
            scratch.discard()
            code = self._fail(generation, error)
            self._log(generation, GenerationState.FALHOU, started, error_code=code)
            return
        self._log(generation, done.state, started, size=sum(f.size_bytes for f in files))

    def _build_and_close(
        self, generation: GeneratedDocument, scratch: _Scratch
    ) -> tuple[list[GeneratedFile], GeneratedDocument]:
        with self._uow_factory() as uow:
            process = uow.processes.get(generation.process_id)
            inputs = load_generation_inputs(uow, process)
            saved_draft = None
            if generation.kind is DocumentKind.RELATORIO:
                saved_draft = uow.report_drafts.get(process.id)
            latest = uow.generations.latest_ready_by_kind(process.id)
        produced = self._produce(generation, inputs, saved_draft, latest, scratch)
        files = []
        for fmt, temp in produced.outputs:
            sha256, size = _digest(temp)
            name = scratch.commit(temp, fmt.value.lower())
            files.append(GeneratedFile(fmt, name, sha256, size))
        with self._uow_factory() as uow:
            done = uow.generations.finish_ready(
                generation.id,
                self._clock.now(),
                files,
                produced.snapshot,
                produced.alerts,
                produced.plan_hash,
            )
            self._audit.record(
                uow,
                None,
                GENERATED_ENTITY,
                generation.id,
                AuditAction.STATUS,
                {"state": GenerationState.GERANDO},
                {
                    "state": done.state,
                    "version_number": done.version_number,
                    "files": [
                        {"format": f.format, "sha256": f.sha256, "size_bytes": f.size_bytes}
                        for f in files
                    ],
                },
            )
            uow.commit()
        return files, done

    def _fail(self, generation: GeneratedDocument, error: Exception) -> GenerationCode:
        """Closes the row as FALHOU with the code of the error and the fixed message of the code;
        what is not a refusal is ERRO_INTERNO and never leaves its message anywhere."""
        code = GenerationCode.ERRO_INTERNO
        if isinstance(error, GenerationRefused) and error.code in _FAILURE_MESSAGES:
            code = GenerationCode(error.code)
        with self._uow_factory() as uow:
            uow.generations.finish_failed(
                generation.id, self._clock.now(), code, _FAILURE_MESSAGES[code]
            )
            self._audit.record(
                uow,
                None,
                GENERATED_ENTITY,
                generation.id,
                AuditAction.STATUS,
                {"state": GenerationState.GERANDO},
                {"state": GenerationState.FALHOU, "error_code": code},
            )
            uow.commit()
        if code is GenerationCode.ERRO_INTERNO:
            logger.error(
                "generation_id=%s kind=%s error_type=%s",
                generation.id,
                generation.kind.value,
                type(error).__name__,
            )
        return code

    @staticmethod
    def _log(
        generation: GeneratedDocument,
        state: GenerationState,
        started: float,
        size: int = 0,
        error_code: GenerationCode | None = None,
    ) -> None:
        """Identifiers, counts and codes only: nothing the documents say (observability)."""
        logger.info(
            "generation_id=%s kind=%s state=%s duration_ms=%d size_bytes=%d error_code=%s "
            "peak_rss_mb=%d",
            generation.id,
            generation.kind.value,
            state.value,
            (time.monotonic() - started) * 1000,
            size,
            error_code.value if error_code else "-",
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
        )

    def _produce(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
        saved: ReportDraft | None,
        latest: Mapping[DocumentKind, GeneratedDocument],
        scratch: _Scratch,
    ) -> _Produced:
        if generation.kind is DocumentKind.RELATORIO:
            return self._report(generation, inputs, saved, scratch)
        if generation.kind is DocumentKind.COMPROVANTE:
            return self._comprovante(generation, inputs, latest, scratch)
        return self._table(generation, inputs, latest, scratch)

    def _table(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
        latest: Mapping[DocumentKind, GeneratedDocument],
        scratch: _Scratch,
    ) -> _Produced:
        version = inputs.version
        if version is None:
            raise GenerationRefused(
                GenerationCode.TABELA_NAO_ESCOLHIDA,
                "Escolha a tabela de pontuação do processo antes de gerar.",
            )
        plan = plan_comprovante(inputs.layout, inputs.activities, self._toc_capacity)
        numbers = {
            e.activity_id: e.first_page
            for e in plan.toc
            if e.level is TocLevel.ATIVIDADE and e.first_page is not None
        }
        model = build_table_document(
            inputs.header,
            version,
            inputs.score.result,
            inputs.activities,
            numbers,
            inputs.score.alerts,
        )
        outputs = []
        for fmt in _FORMATS:
            temp = scratch.new_temp()
            outputs.append((fmt, temp))
            self._writer.write_table(model, fmt, temp)
        snapshot = build_snapshot(
            generation.kind,
            version,
            inputs.interstice,
            inputs.score.result,
            inputs.activities,
            excluded=inputs.excluded,
            alerts=_unique([a.code for a in model.alerts]),
            layout=_layout_snapshot(inputs.layout, plan),
        )
        alerts = _left_out_alert(inputs) + _numbering_alert(generation.kind, plan, latest)
        return _Produced(outputs, snapshot, alerts, plan.plan_hash)

    def _report(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
        saved: ReportDraft | None,
        scratch: _Scratch,
    ) -> _Produced:
        """The report from the saved draft brought up to date, or from the proposal when nothing
        was saved; the draft itself is never written here (REL-09, REL-07)."""
        version = inputs.version
        if version is None:
            raise GenerationRefused(
                GenerationCode.TABELA_NAO_ESCOLHIDA,
                "Escolha a tabela de pontuação do processo antes de gerar.",
            )
        config = self._report_config.load()
        if saved is None:
            draft = propose_draft(
                config.template,
                inputs.activities,
                config.group_map,
                process_id=generation.process_id,
            )
        else:
            draft = reconcile_draft(saved, inputs.activities, config.template, config.group_map)
        item_names = {
            (c.group_number, c.item_number): c.description
            for group in version.groups
            for c in group.criteria
        }
        model = build_report_document(config, inputs.header, draft, inputs.activities, item_names)
        outputs = []
        for fmt in _FORMATS:
            temp = scratch.new_temp()
            outputs.append((fmt, temp))
            self._writer.write_report(model, fmt, temp)
        report = {
            "sections": [
                {
                    "key": section.key,
                    "free_text": section.free_text,
                    "entries": [
                        {
                            "activity_id": str(e.activity_id),
                            "text": e.text,
                            "source": e.source.value,
                        }
                        for e in section.entries
                    ],
                }
                for section in document_sections(draft)
            ]
        }
        snapshot = build_snapshot(
            generation.kind,
            version,
            inputs.interstice,
            inputs.score.result,
            inputs.activities,
            excluded=inputs.excluded,
            alerts=_unique([a.code for a in inputs.score.alerts]),
            template={"id": config.template.id, "version": config.template.version},
            report=report,
        )
        alerts = _left_out_alert(inputs)
        if any(w.code is STALE for section in draft.sections for w in section.warnings):
            alerts.append(GenerationAlert(STALE, STALE_MESSAGE))
        return _Produced(outputs, snapshot, alerts)

    def _comprovante(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
        latest: Mapping[DocumentKind, GeneratedDocument],
        scratch: _Scratch,
    ) -> _Produced:
        """The PDF assembled from the plan, one original page at a time (CMP-01, CMP-11)."""
        version = inputs.version
        if version is None:
            raise GenerationRefused(
                GenerationCode.TABELA_NAO_ESCOLHIDA,
                "Escolha a tabela de pontuação do processo antes de gerar.",
            )
        plan = checked_comprovante_plan(
            inputs, self._originals, self._inspector, self._limits, self._toc_capacity
        )
        front = ComprovanteFront(
            header=inputs.header,
            table_name=version.name,
            group_names={g.number: g.name for g in version.groups},
            item_names={
                (c.group_number, c.item_number): c.description
                for g in version.groups
                for c in g.criteria
            },
            document_names={d.id: d.original_name for d in inputs.documents},
        )
        names = {d.id: d.internal_name for d in inputs.documents}

        def resolver(document_id: UUID) -> Path:
            return self._originals.path(generation.process_id, names[document_id])

        def on_progress(done: int, total: int) -> None:
            if done % _PROGRESS_EVERY == 0 or done == total:
                logger.debug("generation_id=%s pages=%d/%d", generation.id, done, total)

        temp = scratch.new_temp()
        result = self._assembler.assemble(plan, front, resolver, temp, on_progress)
        snapshot = build_snapshot(
            generation.kind,
            version,
            inputs.interstice,
            inputs.score.result,
            inputs.activities,
            excluded=inputs.excluded,
            alerts=_unique([a.code for a in inputs.score.alerts]),
            layout=_layout_snapshot(inputs.layout, plan),
        )
        alerts = (
            list(result.alerts)
            + _left_out_alert(inputs)
            + _numbering_alert(generation.kind, plan, latest)
        )
        return _Produced([(DocumentFormat.PDF, temp)], snapshot, alerts, plan.plan_hash)
