"""Schemas of the generated documents (VER-03, VER-09, UIG-01): the generation rows, the report
draft and its wording jobs, the arrangement and plan of the Comprovante, the dossier order and the
conclusion.

Nothing here carries a stored file name, a path or the text of an original document: the file of a
version is reached by its format, and what the screen shows about an activity is its title, its
place in the table and its date. A body that comes in refuses fields it does not know (422).
"""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.use_cases.comprovante_layout import LayoutView
from app.application.use_cases.report_draft import ReportDraftView
from app.domain.entities.activity import Activity
from app.domain.entities.comprovante import (
    ComprovanteLayout,
    ComprovantePlan,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
    PageKind,
    PlanAlert,
    PlanPage,
    Staleness,
    TocEntry,
    TocLevel,
)
from app.domain.entities.conclusion import ConclusionPreview, ConclusionResult
from app.domain.entities.generated import (
    DocumentFormat,
    DocumentKind,
    GeneratedDocument,
    GeneratedFile,
    GenerationAlert,
    GenerationState,
    WordingJob,
)
from app.domain.entities.process import ProcessStatus
from app.domain.entities.report import (
    DossierItem,
    DossierSource,
    DraftEntry,
    DraftSection,
    ReportDraft,
)
from app.domain.rules.dossier_checklist import ChecklistItem, ChecklistState


class _Body(BaseModel):
    """A request body: unknown fields are a 422."""

    model_config = ConfigDict(extra="forbid")


class GenerationRequest(_Body):
    kind: DocumentKind


class AlertOut(BaseModel):
    code: str
    message: str

    @classmethod
    def of(cls, alert: GenerationAlert) -> "AlertOut":
        return cls(code=alert.code.value, message=alert.message)


class GeneratedFileOut(BaseModel):
    """A file of a version: its format, size and SHA-256 (the value of the `ETag`)."""

    format: DocumentFormat
    size_bytes: int
    sha256: str

    @classmethod
    def of(cls, file: GeneratedFile) -> "GeneratedFileOut":
        return cls(format=file.format, size_bytes=file.size_bytes, sha256=file.sha256)


class SnapshotSummaryOut(BaseModel):
    """What the version used, in short: the table, the interstice and the totals it showed."""

    table_name: str | None
    norm_reference: str | None
    interstice_start: date | None
    interstice_end: date | None
    total: str | None
    subtotals: dict[str, str]
    pit_total_hours: str | None
    activity_count: int
    excluded: dict[str, int]

    @classmethod
    def of(cls, snapshot: Mapping[str, Any]) -> "SnapshotSummaryOut":
        table = snapshot.get("table_version") or {}
        interstice = snapshot.get("interstice") or {}
        return cls(
            table_name=table.get("name"),
            norm_reference=table.get("norm_reference"),
            interstice_start=_date(interstice.get("start")),
            interstice_end=_date(interstice.get("end")),
            total=snapshot.get("total"),
            subtotals=dict(snapshot.get("subtotals") or {}),
            pit_total_hours=snapshot.get("pit_total_hours"),
            activity_count=len(snapshot.get("activities") or []),
            excluded=dict(snapshot.get("excluded") or {}),
        )


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _table_version_id(snapshot: Mapping[str, Any] | None) -> UUID | None:
    found = ((snapshot or {}).get("table_version") or {}).get("id")
    return UUID(found) if found else None


class GeneratedDocumentOut(BaseModel):
    """One row: running, ready (with number and files) or failed (with code and message)."""

    id: UUID
    process_id: UUID
    kind: DocumentKind
    state: GenerationState
    version_number: int | None
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    alerts: list[AlertOut]
    files: list[GeneratedFileOut]
    table_version_id: UUID | None  # the version of the scoring table the snapshot used (GI-11)

    @classmethod
    def of(cls, row: GeneratedDocument) -> "GeneratedDocumentOut":
        return cls(
            id=row.id,
            process_id=row.process_id,
            kind=row.kind,
            state=row.state,
            version_number=row.version_number,
            requested_at=row.requested_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            error_code=row.error_code.value if row.error_code else None,
            error_message=row.error_message,
            alerts=[AlertOut.of(a) for a in row.alerts],
            files=[GeneratedFileOut.of(f) for f in row.files],
            table_version_id=_table_version_id(row.snapshot),
        )


class GeneratedDocumentDetailOut(GeneratedDocumentOut):
    """The row with the summary of its snapshot (None while it has none)."""

    summary: SnapshotSummaryOut | None

    @classmethod
    def of(cls, row: GeneratedDocument) -> "GeneratedDocumentDetailOut":
        return cls(
            **GeneratedDocumentOut.of(row).model_dump(),
            summary=SnapshotSummaryOut.of(row.snapshot) if row.snapshot else None,
        )


class ActivityRefOut(BaseModel):
    """An activity as the screens of the report and of the arrangement name it."""

    id: UUID
    title: str
    group_number: int | None
    item_number: int | None
    event_date: date | None
    academic_period: str | None

    @classmethod
    def of(cls, activity: Activity) -> "ActivityRefOut":
        return cls(
            id=activity.id,
            title=activity.title,
            group_number=activity.group_number,
            item_number=activity.item_number,
            event_date=activity.event_date,
            academic_period=activity.academic_period,
        )


class ItemNameOut(BaseModel):
    group_number: int
    item_number: int
    name: str


class DraftEntryOut(BaseModel):
    activity_id: UUID
    text: str
    source: str
    warnings: list[AlertOut]

    @classmethod
    def of(cls, entry: DraftEntry) -> "DraftEntryOut":
        return cls(
            activity_id=entry.activity_id,
            text=entry.text,
            source=entry.source.value,
            warnings=[AlertOut.of(w) for w in entry.warnings],
        )


class DraftSectionOut(BaseModel):
    key: str
    title: str
    free_text: str
    entries: list[DraftEntryOut]
    warnings: list[AlertOut]

    @classmethod
    def of(cls, section: DraftSection) -> "DraftSectionOut":
        return cls(
            key=section.key,
            title=section.title,
            free_text=section.free_text,
            entries=[DraftEntryOut.of(e) for e in section.entries],
            warnings=[AlertOut.of(w) for w in section.warnings],
        )


class ReportDraftOut(BaseModel):
    """The draft the screen edits: `version` 0 and `saved` False for a proposal that was never
    saved."""

    process_id: UUID
    template_id: str
    template_version: int
    version: int
    sections: list[DraftSectionOut]

    @classmethod
    def of(cls, draft: ReportDraft) -> "ReportDraftOut":
        return cls(
            process_id=draft.process_id,
            template_id=draft.template_id,
            template_version=draft.template_version,
            version=draft.version,
            sections=[DraftSectionOut.of(s) for s in draft.sections],
        )


class ReportDraftViewOut(ReportDraftOut):
    saved: bool
    empty_sections: list[str]
    alerts: list[AlertOut]
    activities: list[ActivityRefOut]
    item_names: list[ItemNameOut]

    @classmethod
    def of_view(cls, view: ReportDraftView) -> "ReportDraftViewOut":
        return cls(
            **ReportDraftOut.of(view.draft).model_dump(),
            saved=view.saved,
            empty_sections=list(view.empty_sections),
            alerts=[AlertOut.of(a) for a in view.alerts],
            activities=[ActivityRefOut.of(a) for a in view.activities],
            item_names=[
                ItemNameOut(group_number=group, item_number=item, name=name)
                for (group, item), name in sorted(view.item_names.items())
            ],
        )


class EntryTextIn(_Body):
    expected_version: int
    text: str


class SectionTextIn(_Body):
    expected_version: int
    free_text: str


class MoveEntryIn(_Body):
    expected_version: int
    section_key: str


class WordingJobOut(BaseModel):
    id: UUID
    section_key: str
    state: GenerationState
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    warnings: list[AlertOut]

    @classmethod
    def of(cls, job: WordingJob) -> "WordingJobOut":
        return cls(
            id=job.id,
            section_key=job.section_key,
            state=job.state,
            requested_at=job.requested_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_code=job.error_code.value if job.error_code else None,
            warnings=[AlertOut.of(w) for w in job.warnings],
        )


class LayoutPageIn(_Body):
    document_id: UUID
    page: int = Field(ge=1)
    repeat_justification: str | None = None


class LayoutActivityIn(_Body):
    activity_id: UUID
    pages: list[LayoutPageIn] = []
    group_number: int | None = None
    item_number: int | None = None

    def to_domain(self) -> LayoutActivity:
        return LayoutActivity(
            activity_id=self.activity_id,
            pages=tuple(
                LayoutPage(p.document_id, p.page, p.repeat_justification) for p in self.pages
            ),
            group_number=self.group_number,
            item_number=self.item_number,
        )


class LayoutSaveIn(_Body):
    expected_version: int
    activities: list[LayoutActivityIn]


class LayoutPageOut(BaseModel):
    document_id: UUID
    page: int
    repeat_justification: str | None


class LayoutActivityOut(BaseModel):
    activity_id: UUID
    group_number: int | None
    item_number: int | None
    pages: list[LayoutPageOut]


class LayoutOut(BaseModel):
    version: int
    activities: list[LayoutActivityOut]

    @classmethod
    def of(cls, layout: ComprovanteLayout) -> "LayoutOut":
        return cls(
            version=layout.version,
            activities=[
                LayoutActivityOut(
                    activity_id=a.activity_id,
                    group_number=a.group_number,
                    item_number=a.item_number,
                    pages=[
                        LayoutPageOut(
                            document_id=p.document_id,
                            page=p.page,
                            repeat_justification=p.repeat_justification,
                        )
                        for p in a.pages
                    ],
                )
                for a in layout.activities
            ],
        )


class StalenessOut(BaseModel):
    left_activity_ids: list[UUID]
    moved_activity_ids: list[UUID]
    new_link_activity_ids: list[UUID]
    joined_activity_ids: list[UUID]

    @classmethod
    def of(cls, staleness: Staleness) -> "StalenessOut":
        return cls(
            left_activity_ids=list(staleness.left_activity_ids),
            moved_activity_ids=list(staleness.moved_activity_ids),
            new_link_activity_ids=list(staleness.new_link_activity_ids),
            joined_activity_ids=list(staleness.joined_activity_ids),
        )


class EvidenceKeyOut(BaseModel):
    activity_id: UUID
    document_id: UUID
    page: int

    @classmethod
    def of(cls, key: EvidenceKey) -> "EvidenceKeyOut":
        return cls(activity_id=key.activity_id, document_id=key.document_id, page=key.page)


class PlanPageOut(BaseModel):
    kind: PageKind
    number: int
    group_number: int | None
    document_id: UUID | None
    source_page: int | None

    @classmethod
    def of(cls, page: PlanPage) -> "PlanPageOut":
        return cls(
            kind=page.kind,
            number=page.number,
            group_number=page.group_number,
            document_id=page.document_id,
            source_page=page.source_page,
        )


class PageRefOut(BaseModel):
    document_id: UUID
    source_page: int
    comprovante_page: int
    remission: bool
    justification: str | None


class TocEntryOut(BaseModel):
    level: TocLevel
    group_number: int
    item_number: int | None
    activity_id: UUID | None
    title: str
    first_page: int | None
    last_page: int | None
    sources: list[PageRefOut]
    note: str | None

    @classmethod
    def of(cls, entry: TocEntry) -> "TocEntryOut":
        return cls(
            level=entry.level,
            group_number=entry.group_number,
            item_number=entry.item_number,
            activity_id=entry.activity_id,
            title=entry.title,
            first_page=entry.first_page,
            last_page=entry.last_page,
            sources=[
                PageRefOut(
                    document_id=s.document_id,
                    source_page=s.source_page,
                    comprovante_page=s.comprovante_page,
                    remission=s.remission,
                    justification=s.justification,
                )
                for s in entry.sources
            ],
            note=entry.note,
        )


class PlanAlertOut(BaseModel):
    code: str
    activity_id: UUID
    document_id: UUID | None
    page: int | None
    justification: str | None

    @classmethod
    def of(cls, alert: PlanAlert) -> "PlanAlertOut":
        return cls(
            code=alert.code.value,
            activity_id=alert.activity_id,
            document_id=alert.document_id,
            page=alert.page,
            justification=alert.justification,
        )


class PlanOut(BaseModel):
    """The numbering the Comprovante will have (page 1 is the cover)."""

    plan_hash: str
    pages: list[PlanPageOut]
    toc: list[TocEntryOut]
    alerts: list[PlanAlertOut]

    @classmethod
    def of(cls, plan: ComprovantePlan) -> "PlanOut":
        return cls(
            plan_hash=plan.plan_hash,
            pages=[PlanPageOut.of(p) for p in plan.pages],
            toc=[TocEntryOut.of(e) for e in plan.toc],
            alerts=[PlanAlertOut.of(a) for a in plan.alerts],
        )


class LayoutViewOut(BaseModel):
    layout: LayoutOut
    saved: bool
    staleness: StalenessOut
    stale: bool
    invalid: list[EvidenceKeyOut]
    plan: PlanOut
    alerts: list[AlertOut]

    @classmethod
    def of(cls, view: LayoutView) -> "LayoutViewOut":
        return cls(
            layout=LayoutOut.of(view.layout),
            saved=view.saved,
            staleness=StalenessOut.of(view.staleness),
            stale=view.stale,
            invalid=[EvidenceKeyOut.of(k) for k in view.invalid],
            plan=PlanOut.of(view.plan),
            alerts=[AlertOut.of(a) for a in view.alerts],
        )


class DossierItemOut(BaseModel):
    order: int
    title: str
    generated_by: DocumentKind | None

    @classmethod
    def of(cls, item: DossierItem) -> "DossierItemOut":
        return cls(order=item.order, title=item.title, generated_by=item.generated_by)


class ChecklistItemOut(BaseModel):
    """One document of the dossier of a process and where it stands (DOS-01 to DOS-06)."""

    key: str
    order: int
    title: str
    source: DossierSource
    state: ChecklistState
    version_number: int | None
    generation_id: UUID | None
    outdated_table: bool

    @classmethod
    def of(cls, item: ChecklistItem) -> "ChecklistItemOut":
        return cls(
            key=item.key,
            order=item.order,
            title=item.title,
            source=item.source,
            state=item.state,
            version_number=item.version_number,
            generation_id=item.generation_id,
            outdated_table=item.outdated_table,
        )


class DeliveryIn(_Body):
    entregue: bool


class ConclusionPreviewOut(BaseModel):
    """What concluding frees, which required kind already has a ready version and which board
    documents are still missing (a warning, never a block: DOS-07)."""

    files: int
    bytes: int
    artifacts: dict[DocumentKind, bool]
    pending_board: list[str]

    @classmethod
    def of(cls, preview: ConclusionPreview) -> "ConclusionPreviewOut":
        return cls(
            files=preview.files,
            bytes=preview.bytes,
            artifacts=dict(preview.artifacts),
            pending_board=list(preview.pending_board),
        )


class ConclusionIn(_Body):
    expected_version: int
    confirmar: bool = False
    justificativa: str | None = None


class ConclusionOut(BaseModel):
    status: ProcessStatus
    arquivos_removidos: int
    arquivos_pendentes: int
    bytes_liberados: int
    alertas: list[AlertOut]

    @classmethod
    def of(cls, result: ConclusionResult) -> "ConclusionOut":
        return cls(
            status=result.status,
            arquivos_removidos=result.files_removed,
            arquivos_pendentes=result.files_pending,
            bytes_liberados=result.bytes_freed,
            alertas=[AlertOut.of(a) for a in result.alerts],
        )
