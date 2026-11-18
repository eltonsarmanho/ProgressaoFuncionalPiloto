"""Arrangement and plan of the Comprovante (ARR-01 to ARR-08, CMP-01 to CMP-13).

Pure functions over activities, links and document metadata: nothing here opens a file. The
arrangement is what the user orders; the plan is the numbered list of pages the PDF will have.
"""

import json
import math
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from hashlib import sha256
from uuid import UUID

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.comprovante import (
    ActivityPageRef,
    ComprovanteLayout,
    ComprovantePlan,
    EvidenceKey,
    LayoutActivity,
    LayoutPage,
    PageKind,
    PlanAlert,
    PlanPage,
    SourceDocument,
    Staleness,
    TocEntry,
    TocLevel,
)
from app.domain.entities.generated import GenerationAlertCode, GenerationCode
from app.domain.errors import GenerationRefused, NotFound, ValidationFailed
from app.domain.repositories.ports import ActivityEvidence

NO_VOUCHER_NOTE = "Sem comprovante anexado"
MAX_ATTACHED_PAGES = 400
PNG_MAX_MEGAPIXELS = 12
_PIXELS_PER_MEGAPIXEL = 1_000_000


class ComprovanteRefused(GenerationRefused):
    """The Comprovante cannot be built; names the document and page when one is to blame."""

    def __init__(
        self,
        code: GenerationCode,
        message: str,
        document_id: UUID | None = None,
        page: int | None = None,
    ):
        super().__init__(code, message)
        self.document_id = document_id
        self.page = page


def eligible_activities(activities: Sequence[Activity]) -> list[Activity]:
    """The activities that go in the Comprovante: validated, with group and item."""
    return [
        a
        for a in activities
        if a.status is ActivityStatus.VALIDADA
        and a.group_number is not None
        and a.item_number is not None
    ]


def _table_order(activity: Activity):
    """Group, item, then the date of the activity (undated last) and its creation."""
    day = activity.event_date or activity.period_start or activity.period_end
    return (
        activity.group_number,
        activity.item_number,
        day is None,
        day or date.min,
        activity.created_at is None,
        activity.created_at,
    )


def derive_layout(
    process_id: UUID, activities: Sequence[Activity], evidences: Sequence[ActivityEvidence]
) -> ComprovanteLayout:
    """The layout of a process with no saved arrangement (ARR-01, ARR-05).

    Groups and items follow the table; inside an item activities follow their date; the pages
    of an activity follow the order of its links.
    """
    arranged = sorted(eligible_activities(activities), key=_table_order)
    pages: dict[UUID, list[LayoutPage]] = {a.id: [] for a in arranged}
    keys: list[EvidenceKey] = []
    for found in evidences:
        if found.activity_id in pages:
            pages[found.activity_id].append(LayoutPage(found.document_id, found.page_number))
            keys.append(EvidenceKey(found.activity_id, found.document_id, found.page_number))
    return ComprovanteLayout(
        process_id,
        tuple(
            LayoutActivity(a.id, tuple(pages[a.id]), a.group_number, a.item_number)
            for a in arranged
        ),
        base_evidence_keys=tuple(keys),
    )


# A group and an item take one line of the table of contents, an activity two: its title and
# where it comes from.
GROUP_LINES = 1
ITEM_LINES = 1
ACTIVITY_LINES = 2


def _arrange(
    layout: ComprovanteLayout, activities: Sequence[Activity]
) -> dict[int, dict[int, list[tuple[Activity, tuple[LayoutPage, ...]]]]]:
    """Current validated activities by group and item, each with the pages the layout gives it.

    Inside an item the order of the layout comes first; an activity the layout does not know
    follows by its date, with no page. Layout entries of activities that are gone are dropped.
    """
    position = {a.activity_id: index for index, a in enumerate(layout.activities)}
    pages = {a.activity_id: a.pages for a in layout.activities}
    ordered = sorted(
        eligible_activities(activities),
        key=lambda a: (
            a.group_number,
            a.item_number,
            position.get(a.id, len(position)),
            _table_order(a),
        ),
    )
    groups: dict[int, dict[int, list[tuple[Activity, tuple[LayoutPage, ...]]]]] = {}
    for activity in ordered:
        items = groups.setdefault(activity.group_number, {})
        items.setdefault(activity.item_number, []).append((activity, pages.get(activity.id, ())))
    return groups


def remission_text(ref: ActivityPageRef) -> str:
    """What the table of contents says of a page that is attached for another activity."""
    return f"ver comprovante nº {ref.comprovante_page}, p. {ref.source_page}"


def _range(refs: list[ActivityPageRef]) -> tuple[int | None, int | None]:
    """First and last Comprovante page of an activity: the pages attached for it, or else the
    copies its remissions point to."""
    attached = [r.comprovante_page for r in refs if not r.remission]
    numbers = attached or [r.comprovante_page for r in refs]
    return min(numbers, default=None), max(numbers, default=None)


def plan_comprovante(
    layout: ComprovanteLayout, activities: Sequence[Activity], toc_capacity: int
) -> ComprovantePlan:
    """The numbered pages of the Comprovante and its table of contents (CMP-01 to CMP-07).

    Cover, table of contents (`toc_capacity` lines a page), then one separator per group that
    has an activity followed by the original pages. A page already attached for an earlier
    activity is not attached again: the later activity gets a remission, unless the user
    justified the repeat. An activity with no page is listed with a note and an alert. Only
    metadata is used: the plan exists after the originals are gone, so the Tabela can still
    quote the numbers.
    """
    groups = _arrange(layout, activities)
    lines = sum(
        GROUP_LINES + sum(ITEM_LINES + ACTIVITY_LINES * len(found) for found in items.values())
        for items in groups.values()
    )
    toc_pages = math.ceil(lines / toc_capacity)
    pages = [PlanPage(PageKind.CAPA, 1)]
    pages += [PlanPage(PageKind.SUMARIO, 2 + n) for n in range(toc_pages)]
    toc: list[TocEntry] = []
    alerts: list[PlanAlert] = []
    attached_at: dict[tuple[UUID, int], int] = {}
    for group_number, items in groups.items():
        pages.append(PlanPage(PageKind.SEPARADOR, len(pages) + 1, group_number))
        toc.append(TocEntry(TocLevel.GRUPO, group_number, first_page=len(pages)))
        for item_number, found in items.items():
            item_entry = len(toc)
            toc.append(TocEntry(TocLevel.ITEM, group_number, item_number))
            item_first = None
            for activity, layout_pages in found:
                refs: list[ActivityPageRef] = []
                for layout_page in layout_pages:
                    key = (layout_page.document_id, layout_page.page)
                    justification = layout_page.repeat_justification
                    if key in attached_at and justification is None:
                        refs.append(
                            ActivityPageRef(*key, comprovante_page=attached_at[key], remission=True)
                        )
                        continue
                    number = len(pages) + 1
                    pages.append(PlanPage(PageKind.ORIGINAL, number, group_number, *key))
                    if key in attached_at:
                        alerts.append(
                            PlanAlert(
                                GenerationAlertCode.PAGINA_REPETIDA_JUSTIFICADA,
                                activity.id,
                                *key,
                                justification=justification,
                            )
                        )
                    else:
                        attached_at[key] = number
                        justification = None
                    refs.append(
                        ActivityPageRef(*key, comprovante_page=number, justification=justification)
                    )
                    item_first = item_first or number
                note = None
                if not refs:
                    note = NO_VOUCHER_NOTE
                    alerts.append(
                        PlanAlert(GenerationAlertCode.ATIVIDADE_SEM_COMPROVANTE, activity.id)
                    )
                first, last = _range(refs)
                toc.append(
                    TocEntry(
                        TocLevel.ATIVIDADE,
                        group_number,
                        item_number,
                        activity.id,
                        activity.title,
                        first,
                        last,
                        tuple(refs),
                        note,
                    )
                )
            toc[item_entry] = TocEntry(
                TocLevel.ITEM, group_number, item_number, first_page=item_first
            )
    plan = ComprovantePlan(tuple(pages), "", tuple(toc), tuple(alerts))
    return replace(plan, plan_hash=plan_hash(plan))


def plan_hash(plan: ComprovantePlan) -> str:
    """SHA-256 of the numbering of the plan as canonical JSON (CMP-04).

    The same pages in the same order give the same hash; a new order, a removed page or a new
    number changes it. Titles and justifications are left out: they never move a number.
    """
    numbering = {
        "pages": [
            [
                page.kind.value,
                page.number,
                page.group_number,
                None if page.document_id is None else str(page.document_id),
                page.source_page,
            ]
            for page in plan.pages
        ],
        "toc": [
            [
                entry.level.value,
                entry.group_number,
                entry.item_number,
                None if entry.activity_id is None else str(entry.activity_id),
                entry.first_page,
                entry.last_page,
                [
                    [str(ref.document_id), ref.source_page, ref.comprovante_page, ref.remission]
                    for ref in entry.sources
                ],
            ]
            for entry in plan.toc
        ],
    }
    text = json.dumps(numbering, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(text.encode("utf-8")).hexdigest()


def check_comprovante(
    plan: ComprovantePlan,
    documents: Sequence[SourceDocument],
    *,
    max_pages: int = MAX_ATTACHED_PAGES,
    png_max_megapixels: int = PNG_MAX_MEGAPIXELS,
) -> None:
    """Refuse a Comprovante that cannot be built (CMP-09, CMP-10, CMP-13, DEL-11).

    `documents` are all the documents of the process. The plan itself is always computable, so
    the Tabela can quote its numbers even when the Comprovante is refused. The first problem
    found is raised, in this order: a deleted original, a source that is not available, a PNG
    that is too large, too many attached pages.
    """
    if any(document.file_deleted for document in documents):
        raise ComprovanteRefused(
            GenerationCode.ORIGINAIS_EXCLUIDOS,
            "Os documentos de entrada deste processo foram excluídos.",
        )
    known = {document.id: document for document in documents}
    attached = [page for page in plan.pages if page.kind is PageKind.ORIGINAL]
    for page in attached:
        document = known.get(page.document_id)
        if document is None or not 1 <= page.source_page <= document.page_count:
            raise ComprovanteRefused(
                GenerationCode.ORIGINAL_INDISPONIVEL,
                f"O documento {page.document_id} não tem a página {page.source_page}.",
                page.document_id,
                page.source_page,
            )
    limit = png_max_megapixels * _PIXELS_PER_MEGAPIXEL
    for page in attached:
        document = known[page.document_id]
        if document.mime == "image/png" and document.pixels is not None and document.pixels > limit:
            raise ComprovanteRefused(
                GenerationCode.IMAGEM_GRANDE_DEMAIS,
                f"A imagem {document.original_name} tem mais de {png_max_megapixels} megapixels.",
                document.id,
            )
    if len(attached) > max_pages:
        raise ComprovanteRefused(
            GenerationCode.COMPROVANTE_GRANDE_DEMAIS,
            f"O Comprovante teria {len(attached)} páginas anexadas; o limite é {max_pages}.",
        )


def layout_staleness(
    layout: ComprovanteLayout,
    activities: Sequence[Activity],
    evidences: Sequence[ActivityEvidence],
) -> Staleness:
    """Whether a saved layout still matches the activities and links (ARR-08).

    An activity of the layout that is no longer validated has left; one the scoring put in
    another item has moved; one with a page link the layout was not built from has a new link;
    a validated activity the layout does not have has joined. Ids follow the layout order
    (table order for the ones that joined).
    """
    current = {a.id: a for a in eligible_activities(activities)}
    arranged = {a.activity_id for a in layout.activities}
    base = set(layout.base_evidence_keys)
    linked = {
        found.activity_id
        for found in evidences
        if EvidenceKey(found.activity_id, found.document_id, found.page_number) not in base
    }
    left, moved, new_link = [], [], []
    for entry in layout.activities:
        now = current.get(entry.activity_id)
        if now is None:
            left.append(entry.activity_id)
        elif entry.group_number is not None and (entry.group_number, entry.item_number) != (
            now.group_number,
            now.item_number,
        ):
            moved.append(entry.activity_id)
        if now is not None and entry.activity_id in linked:
            new_link.append(entry.activity_id)
    joined = [a.id for a in sorted(current.values(), key=_table_order) if a.id not in arranged]
    return Staleness(tuple(left), tuple(moved), tuple(new_link), tuple(joined))


def current_layout(
    layout: ComprovanteLayout,
    activities: Sequence[Activity],
    evidences: Sequence[ActivityEvidence],
) -> ComprovanteLayout:
    """The layout the generation uses: only the current activities (ARR-08).

    Activities that left are dropped, the saved order and pages are kept, the item of each is
    the current one, and the validated activities the layout does not know follow with the
    pages of their links.
    """
    current = {a.id: a for a in eligible_activities(activities)}
    kept = tuple(
        replace(entry, group_number=now.group_number, item_number=now.item_number)
        for entry in layout.activities
        if (now := current.get(entry.activity_id)) is not None
    )
    arranged = {entry.activity_id for entry in layout.activities}
    newcomers = derive_layout(
        layout.process_id, [a for a in current.values() if a.id not in arranged], evidences
    )
    return replace(layout, activities=kept + newcomers.activities)


def invalid_entries(
    layout: ComprovanteLayout, documents: Sequence[SourceDocument]
) -> tuple[EvidenceKey, ...]:
    """The pages of the layout that cannot be attached any more (ARR edge case, CMP-10).

    Their document is no longer in the process, its file was deleted, or the page is past its
    last page. The layout keeps them so the user sees and removes them.
    """
    known = {document.id: document for document in documents}
    invalid = []
    for entry in layout.activities:
        for page in entry.pages:
            document = known.get(page.document_id)
            if document is None or document.file_deleted or page.page > document.page_count:
                invalid.append(EvidenceKey(entry.activity_id, page.document_id, page.page))
    return tuple(invalid)


def layout_page(
    document_id: UUID, page: int, repeat_justification: str | None = None
) -> LayoutPage:
    """A page of the layout; below the first page it is outside the document (ARR-06)."""
    if page < 1:
        raise GenerationRefused(
            GenerationCode.PAGINA_FORA_DO_DOCUMENTO, "A página deve ser a primeira ou uma seguinte."
        )
    return LayoutPage(document_id, page, repeat_justification)


def validate_layout(
    layout: ComprovanteLayout,
    process_documents: Sequence[SourceDocument],
    activities: Sequence[Activity],
) -> ComprovanteLayout:
    """What a layout the user saves may contain (ARR-02 to ARR-06); never writes anything.

    Every activity is a validated one of the process and every page is a page of a document of
    the process. The activities stay in the order of the table's groups and items and none sits
    in an item other than its own: moving one to another item is refused, while reordering
    activities inside an item and pages inside an activity is kept as sent. Removing a page
    leaves the link between the activity and the page alone. Returns the layout with the group
    and item of the scoring on each activity.
    """
    current = {a.id: a for a in eligible_activities(activities)}
    documents = {document.id: document for document in process_documents}
    checked: list[LayoutActivity] = []
    previous = (0, 0)
    for entry in layout.activities:
        now = current.get(entry.activity_id)
        if now is None:
            raise NotFound("Atividade não encontrada")
        where = (now.group_number, now.item_number)
        if entry.group_number is not None and (entry.group_number, entry.item_number) != where:
            raise ValidationFailed("activities", "Uma atividade não muda de item no arranjo.")
        if where < previous:
            raise ValidationFailed(
                "activities", "Os grupos e itens seguem a ordem da tabela de pontuação."
            )
        previous = where
        for page in entry.pages:
            document = documents.get(page.document_id)
            if document is None:
                raise NotFound("Documento não encontrado")
            if not 1 <= page.page <= document.page_count:
                raise GenerationRefused(
                    GenerationCode.PAGINA_FORA_DO_DOCUMENTO,
                    f"O documento tem {document.page_count} páginas; a página {page.page} "
                    "não existe.",
                )
        checked.append(replace(entry, group_number=where[0], item_number=where[1]))
    return replace(layout, activities=tuple(checked))
