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
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from app.application.services.access_policy import AccessPolicy
from app.application.services.audit_service import AuditService
from app.application.services.generation_inputs import GenerationInputs, load_generation_inputs
from app.application.use_cases.scoring import ProcessScore, _ScoringUseCase, compute_process_score
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import BoardOpinion, BoardOrdinance
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    PageKind,
    SourceDocument,
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
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.report import ReportDraft
from app.domain.entities.user import User
from app.domain.errors import Conflict, GenerationRefused, NotFound, StaleVersion
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
from app.domain.rules.download_names import download_name
from app.domain.rules.generation_snapshot import build_snapshot
from app.domain.rules.interstice import Interstice
from app.domain.rules.opinion_document import build_opinion
from app.domain.rules.report_document import build_report_document
from app.domain.rules.report_draft import (
    STALE,
    STALE_MESSAGE,
    document_sections,
    propose_draft,
    reconcile_draft,
)
from app.domain.rules.request_document import build_request
from app.domain.rules.scoring_verification import MinimumComparison, MinimumStatus
from app.domain.rules.table_document import build_table_document

logger = logging.getLogger("app.documents.generation")

GENERATED_ENTITY = "generated_document"
MB = 1024 * 1024
_PIXELS_PER_MEGAPIXEL = 1_000_000
_BOARD_KINDS = (DocumentKind.PARECER, DocumentKind.REQUERIMENTO)
# the kinds that read the activities, the score and the table of the process to be built
_INPUT_KINDS = (DocumentKind.TABELA, DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)


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


class _EditUseCase(_ScoringUseCase):
    """The writes of the report draft and of the arrangement of the Comprovante: refused in a
    concluded or archived process, and a stale `expected_version` answers with its own code."""

    def _editable(self, uow: UnitOfWork, actor: User, process_id: UUID) -> FunctionalProcess:
        process = self._readable(uow, actor, process_id)
        if process.status.is_read_only:
            raise Conflict(
                "Processo concluído ou arquivado não pode ser alterado",
                GenerationCode.PROCESSO_SOMENTE_LEITURA.value,
            )
        return process

    @staticmethod
    @contextmanager
    def _versioned() -> Iterator[None]:
        try:
            yield
        except StaleVersion as error:
            raise StaleVersion(str(error), GenerationCode.VERSAO_DESATUALIZADA.value) from None


TABLE_OUTDATED_MESSAGE = "A pontuação mudou depois da última Tabela; gere a Tabela de novo"
CONCLUSION_MISSING_MESSAGE = "Escolha a conclusão do Parecer antes de gerar."
NO_MEMBERS_MESSAGE = "Registre ao menos um membro da banca antes de gerar o Parecer."
NO_TABLE_MESSAGE = "Gere a Tabela de Pontuação antes de gerar o Parecer."
_CENTS = Decimal("0.01")


@dataclass(frozen=True)
class OpinionTable:
    """The last Tabela `PRONTO` of the process and the score of now, found equal (PAR-10)."""

    table: GeneratedDocument
    score: ProcessScore


def check_opinion_table(uow: UnitOfWork, process: FunctionalProcess) -> OpinionTable:
    """The Tabela the Parecer copies from, or the refusal that says why it cannot be used.

    `TABELA_AUSENTE` without a `PRONTO` Tabela; `TABELA_DESATUALIZADA` when the Total geral of the
    score of now differs from the one of its snapshot, or when the table of points chosen now is
    not the one the Tabela was made with (the total can match by chance). The request and the run
    both use it, because the score can change between the two (PAR-10).
    """
    table = uow.generations.latest_ready_by_kind(process.id).get(DocumentKind.TABELA)
    if table is None or table.snapshot is None:
        raise GenerationRefused(GenerationCode.TABELA_AUSENTE, NO_TABLE_MESSAGE)
    score = compute_process_score(uow, process)
    chosen = None if score.chosen is None else str(score.chosen.version.id)
    same_total = Decimal(table.snapshot["total"]) == score.result.total.quantize(_CENTS)
    same_version = table.snapshot["table_version"]["id"] == chosen
    if not (same_total and same_version):
        raise GenerationRefused(GenerationCode.TABELA_DESATUALIZADA, TABLE_OUTDATED_MESSAGE)
    return OpinionTable(table, score)


@dataclass(frozen=True)
class OpinionInputs:
    """What the Parecer is made of, all checked: the fields, the board and the Tabela."""

    opinion: BoardOpinion
    ordinance: BoardOrdinance
    table: OpinionTable


def check_opinion_inputs(uow: UnitOfWork, process: FunctionalProcess) -> OpinionInputs:
    """The refusals of the Parecer in the order of the spec (PAR-07 to PAR-10); used by the
    request and again by the run, because the person can change any of them in between."""
    opinion = uow.opinions.get(process.id)
    if opinion is None or opinion.conclusion is None:
        raise GenerationRefused(GenerationCode.CONCLUSAO_AUSENTE, CONCLUSION_MISSING_MESSAGE)
    ordinance = uow.board.get(process.id)
    if ordinance is None or not ordinance.members:
        raise GenerationRefused(GenerationCode.BANCA_SEM_MEMBROS, NO_MEMBERS_MESSAGE)
    return OpinionInputs(opinion, ordinance, check_opinion_table(uow, process))


class RequestGeneration(_EditUseCase):
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
        `GERACAO_EM_ANDAMENTO`, raised by the repository without a race. The Parecer and the
        Requerimento are refused in a concluded or archived process (BNAV-02); the Tabela, the
        Relatório and the Comprovante are still generated there (DEL-13).
        """
        with self._uow_factory() as uow:
            if kind in _BOARD_KINDS:
                process = self._editable(uow, actor, process_id)
                if kind is DocumentKind.PARECER:
                    self._check_opinion(uow, process)
                self._check_space()
            else:
                process = self._readable(uow, actor, process_id)
                self._check_table_kind(uow, process, kind)
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

    def _check_table_kind(self, uow: UnitOfWork, process: FunctionalProcess, kind: DocumentKind):
        """The refusals of the Tabela, the Relatório and the Comprovante, in their order."""
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
        self._check_space()
        if kind is DocumentKind.COMPROVANTE:
            checked_comprovante_plan(
                inputs, self._originals, self._inspector, self._limits, self._toc_capacity
            )

    def _check_space(self) -> None:
        if self._storage.free_bytes() < self._limits.min_free_bytes:
            raise GenerationRefused(
                GenerationCode.ESPACO_INSUFICIENTE,
                "Não há espaço livre suficiente no servidor para gerar o documento.",
            )

    @staticmethod
    def _check_opinion(uow: UnitOfWork, process: FunctionalProcess) -> None:
        check_opinion_inputs(uow, process)


_LEFT_OUT_LABELS = {
    "pendentes": "aguardando revisão",
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
    GenerationCode.ATIVIDADE_SEM_CATEGORIA: (
        "Há atividades sem categoria na Etapa 3. Escolha a categoria de cada uma."
    ),
    GenerationCode.CONCLUSAO_AUSENTE: CONCLUSION_MISSING_MESSAGE,
    GenerationCode.BANCA_SEM_MEMBROS: NO_MEMBERS_MESSAGE,
    GenerationCode.TABELA_AUSENTE: NO_TABLE_MESSAGE,
    GenerationCode.TABELA_DESATUALIZADA: TABLE_OUTDATED_MESSAGE,
    GenerationCode.ERRO_INTERNO: "Erro interno ao gerar o documento. Tente gerar de novo.",
}


def _minimum_snapshot(minimum: MinimumComparison) -> dict[str, Any]:
    value = None if minimum.minimum is None else f"{minimum.minimum.quantize(_CENTS):.2f}"
    return {"status": minimum.status.value, "value": value}


def _opinion_minimum(table_snapshot: Mapping[str, Any], score: ProcessScore) -> MinimumComparison:
    """The minimum the Tabela was made with; a Tabela of before the field has the one of now (the
    total was found equal, so the comparison is the same)."""
    saved = table_snapshot.get("minimum")
    if saved is None:
        return score.minimum
    value = saved["value"]
    return MinimumComparison(
        MinimumStatus(saved["status"]),
        None if value is None else Decimal(value),
        Decimal(table_snapshot["total"]),
    )


def _opinion_date(opinion: GeneratedDocument | None) -> date | None:
    """The date the last Parecer `PRONTO` was made with; none without a Parecer or without a
    date in it (REQ-04)."""
    if opinion is None or opinion.snapshot is None:
        return None
    saved = opinion.snapshot.get("opinion_date")
    return None if saved is None else date.fromisoformat(saved)


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
        inputs = None
        saved_draft = None
        if generation.kind in _INPUT_KINDS:
            with self._uow_factory() as uow:
                process = uow.processes.get(generation.process_id)
                inputs = load_generation_inputs(uow, process)
                if generation.kind is DocumentKind.RELATORIO:
                    saved_draft = uow.report_drafts.get(process.id)
        produced = self._produce(generation, inputs, saved_draft, scratch)
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
        inputs: GenerationInputs | None,
        saved: ReportDraft | None,
        scratch: _Scratch,
    ) -> _Produced:
        """One explicit branch per kind; a kind nobody handles is an error, never a Tabela."""
        kind = generation.kind
        if kind in _INPUT_KINDS:
            if inputs is None:
                raise ValueError("the generation inputs were not loaded")
            if kind is DocumentKind.TABELA:
                return self._table(generation, inputs, scratch)
            if kind is DocumentKind.RELATORIO:
                return self._report(generation, inputs, saved, scratch)
            return self._comprovante(generation, inputs, scratch)
        if kind is DocumentKind.PARECER:
            return self._opinion(generation, scratch)
        if kind is DocumentKind.REQUERIMENTO:
            return self._request(generation, scratch)
        raise ValueError(f"unknown kind of generated document: {kind}")

    def _table(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
        scratch: _Scratch,
    ) -> _Produced:
        version = inputs.version
        if version is None:
            raise GenerationRefused(
                GenerationCode.TABELA_NAO_ESCOLHIDA,
                "Escolha a tabela de pontuação do processo antes de gerar.",
            )
        model = build_table_document(
            inputs.header,
            version,
            inputs.score.result,
            inputs.activities,
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
            minimum=inputs.score.minimum,
        )
        return _Produced(outputs, snapshot, _left_out_alert(inputs))

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

    def _opinion(self, generation: GeneratedDocument, scratch: _Scratch) -> _Produced:
        """The Parecer from the snapshot of the last Tabela, the ordinance and the conclusion the
        person chose; the text is built by rules, never by the AI (PAR-02 to PAR-04, PAR-11)."""
        config = self._report_config.load()
        with self._uow_factory() as uow:
            process = uow.processes.get(generation.process_id)
            professor = uow.professors.get(process.professor_id)
            unit = uow.units.get(process.unit_id)
            if professor is None or unit is None:
                raise NotFound("Docente ou unidade do processo não encontrado")
            checked = check_opinion_inputs(uow, process)
            ready = uow.generations.latest_ready_by_kind(process.id)
        table = checked.table
        snapshot_in = table.table.snapshot
        versions = {
            kind: ready[kind].version_number if kind in ready else None
            for kind in (DocumentKind.TABELA, DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)
        }
        minimum = _opinion_minimum(snapshot_in, table.score)
        chosen = table.score.chosen
        model = build_opinion(
            process,
            professor,
            unit,
            checked.ordinance,
            checked.opinion,
            snapshot_in,
            versions,
            minimum,
            {} if chosen is None else {g.number: g.name for g in chosen.version.groups},
            config.layout.page,
        )
        outputs = []
        for fmt in _FORMATS:
            temp = scratch.new_temp()
            outputs.append((fmt, temp))
            self._writer.write_opinion(model, fmt, temp)
        ordinance, opinion = checked.ordinance, checked.opinion
        snapshot = {
            "table_generation_id": str(table.table.id),
            "table_version": snapshot_in["table_version"],
            "interstice": snapshot_in["interstice"],
            "total": snapshot_in["total"],
            "subtotals": snapshot_in["subtotals"],
            "minimum": _minimum_snapshot(minimum),
            "versions_used": {kind.value: number for kind, number in versions.items()},
            "conclusion": opinion.conclusion.value,
            "opinion_date": (
                None if opinion.opinion_date is None else opinion.opinion_date.isoformat()
            ),
            "place": opinion.place,
            "ordinance_number": ordinance.number,
            "ordinance_date": (
                None if ordinance.ordinance_date is None else ordinance.ordinance_date.isoformat()
            ),
            "members": [{"name": m.name, "role": m.role.value} for m in ordinance.members],
        }
        return _Produced(outputs, snapshot, [])

    def _request(self, generation: GeneratedDocument, scratch: _Scratch) -> _Produced:
        """The Requerimento from the data of Stage 1, the city and the date of the last Parecer
        `PRONTO`; it needs no activity and no Tabela and never calls the AI (REQ-01, REQ-08)."""
        config = self._report_config.load()
        with self._uow_factory() as uow:
            process = uow.processes.get(generation.process_id)
            professor = uow.professors.get(process.professor_id)
            unit = uow.units.get(process.unit_id)
            if professor is None or unit is None:
                raise NotFound("Docente ou unidade do processo não encontrado")
            settings = uow.request_settings.get(process.id)
            career = uow.career_versions.structure_code(professor.career_structure_id) or ""
            last_opinion = uow.generations.latest_ready_by_kind(process.id).get(
                DocumentKind.PARECER
            )
        city = None if settings is None else settings.city
        opinion_date = _opinion_date(last_opinion)
        model = build_request(
            process, professor, unit, career, city, opinion_date, config.layout.page
        )
        outputs = []
        for fmt in _FORMATS:
            temp = scratch.new_temp()
            outputs.append((fmt, temp))
            self._writer.write_request(model, fmt, temp)
        snapshot = {
            "career": career,
            "modality": process.modality.value,
            "interstice": {
                "start": process.start_date.isoformat(),
                "end": process.end_date.isoformat(),
            },
            "current": {
                "class": process.current_class,
                "level": process.current_level,
                "denomination": process.current_denomination,
            },
            "target": {
                "class": process.target_class,
                "level": process.target_level,
                "denomination": process.target_denomination,
            },
            "city": city,
            "opening_date": process.opening_date.isoformat(),
            "opinion_date": None if opinion_date is None else opinion_date.isoformat(),
            "opinion_version": None if last_opinion is None else last_opinion.version_number,
        }
        return _Produced(outputs, snapshot, [])

    def _comprovante(
        self,
        generation: GeneratedDocument,
        inputs: GenerationInputs,
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
        alerts = list(result.alerts) + _left_out_alert(inputs)
        return _Produced([(DocumentFormat.PDF, temp)], snapshot, alerts, plan.plan_hash)


WORDING_ENTITY = "report_wording_job"


class RecoverInterruptedGenerations:
    """Run at startup, before the executor starts (VER-08, REL-14)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        clock: Clock,
        storage: GeneratedFileStorage,
    ) -> None:
        self._uow_factory = uow_factory
        self._audit = audit
        self._clock = clock
        self._storage = storage

    def execute(self) -> int:
        """Closes the generations and the wordings a restart left GERANDO and started as FALHOU
        with `INTERROMPIDA`, audited; a row not started stays in the queue and none is queued
        again. Then removes the temporary files and the stored files no row refers to. Returns
        how many rows were closed."""
        with self._uow_factory() as uow:
            now = self._clock.now()
            generations = uow.generations.recover_interrupted(now)
            jobs = uow.wording_jobs.recover_interrupted(now)
            for entity, rows in ((GENERATED_ENTITY, generations), (WORDING_ENTITY, jobs)):
                for row in rows:
                    self._audit.record(
                        uow,
                        None,
                        entity,
                        row.id,
                        AuditAction.STATUS,
                        {"state": GenerationState.GERANDO},
                        {
                            "state": GenerationState.FALHOU,
                            "error_code": GenerationCode.INTERROMPIDA,
                        },
                    )
            uow.commit()
        with self._uow_factory() as uow:
            referenced = {
                process.id: {
                    f.internal_name
                    for generation in uow.generations.list_for_process(process.id)
                    for f in generation.files
                }
                for process in uow.processes.list()
            }
        removed = self._storage.cleanup(referenced)
        logger.info(
            "recovered_generations=%d recovered_wordings=%d removed_files=%d",
            len(generations),
            len(jobs),
            removed,
        )
        return len(generations) + len(jobs)


GENERATED_NOT_FOUND = "Documento gerado não encontrado"
CONTENT_TYPES = {
    DocumentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    DocumentFormat.PDF: "application/pdf",
}


@dataclass(frozen=True)
class DownloadedGeneratedFile:
    """The stored file of a version; `sha256` is the value of the `ETag` (VER-03)."""

    path: Path
    filename: str
    content_type: str
    sha256: str
    size_bytes: int


class _VersionUseCase(_ScoringUseCase):
    def _generation(
        self, uow: UnitOfWork, actor: User, generation_id: UUID
    ) -> GeneratedDocument:
        """The version, or NotFound when it does not exist or its process is out of reach."""
        generation = uow.generations.get(generation_id)
        if generation is None:
            raise NotFound(GENERATED_NOT_FOUND)
        self._readable(uow, actor, generation.process_id)
        return generation


class ListGeneratedDocuments(_VersionUseCase):
    def execute(
        self, actor: User, process_id: UUID, kind: DocumentKind | None = None
    ) -> Sequence[GeneratedDocument]:
        """The running ones first, then the others from the newest to the oldest (VER-09)."""
        with self._uow_factory() as uow:
            self._readable(uow, actor, process_id)
            return uow.generations.list_for_process(process_id, kind)


class GetGeneratedDocument(_VersionUseCase):
    def execute(self, actor: User, generation_id: UUID) -> GeneratedDocument:
        with self._uow_factory() as uow:
            return self._generation(uow, actor, generation_id)


class DownloadGeneratedFile(_VersionUseCase):
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        audit: AuditService,
        policy: AccessPolicy,
        storage: GeneratedFileStorage,
    ) -> None:
        super().__init__(uow_factory, audit, policy)
        self._storage = storage

    def execute(
        self, actor: User, generation_id: UUID, fmt: DocumentFormat
    ) -> DownloadedGeneratedFile:
        """The file as it was stored, never generated again; audited (VER-03).

        A row that is not PRONTO, a format it does not have and a file gone from the volume are
        all NotFound."""
        with self._uow_factory() as uow:
            generation = self._generation(uow, actor, generation_id)
            stored = next((f for f in generation.files if f.format is fmt), None)
            if generation.state is not GenerationState.PRONTO or stored is None:
                raise NotFound(GENERATED_NOT_FOUND)
            path = self._storage.path(generation.process_id, stored.internal_name)
            if not path.is_file():
                logger.error("generation_id=%s file missing from the storage", generation.id)
                raise NotFound(GENERATED_NOT_FOUND)
            process = uow.processes.get(generation.process_id)
            self._audit.record(
                uow,
                actor.id,
                GENERATED_ENTITY,
                generation.id,
                AuditAction.UPDATE,
                {},
                {"operation": "DOWNLOAD", "format": fmt},
            )
            uow.commit()
            return DownloadedGeneratedFile(
                path,
                download_name(
                    generation.kind,
                    fmt,
                    Interstice(process.start_date, process.end_date),
                    generation.version_number,
                ),
                CONTENT_TYPES[fmt],
                stored.sha256,
                stored.size_bytes,
            )
