"""Arrangement and plan of the Comprovante (ARR-01 to ARR-08, CMP-01 to CMP-13).

Pure functions over activities, links and document metadata: nothing here opens a file. The
arrangement is what the user orders; the plan is the numbered list of pages the PDF will have.
"""

import math
from collections.abc import Sequence
from datetime import date
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
    TocEntry,
    TocLevel,
)
from app.domain.entities.generated import GenerationAlertCode
from app.domain.repositories.ports import ActivityEvidence

NO_VOUCHER_NOTE = "Sem comprovante anexado"


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
    # The hash is set when the limits and the hash are added (T18).
    return ComprovantePlan(tuple(pages), "", tuple(toc), tuple(alerts))
