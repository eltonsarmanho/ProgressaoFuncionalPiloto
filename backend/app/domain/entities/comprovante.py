"""Layout (saved arrangement) and plan (numbered pages) of the Comprovante (ARR-01, CMP-04).

The layout is what the user arranges; the plan is the ordered list of pages the document will
have, computed from the layout and the process metadata only. Both are immutable.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple
from uuid import UUID

from app.domain.entities.generated import GenerationAlertCode


class PageKind(StrEnum):
    CAPA = "CAPA"
    SUMARIO = "SUMARIO"
    SEPARADOR = "SEPARADOR"
    ORIGINAL = "ORIGINAL"


class EvidenceKey(NamedTuple):
    """An activity-page link: the arrangement remembers which ones it was built from."""

    activity_id: UUID
    document_id: UUID
    page: int


@dataclass(frozen=True)
class LayoutPage:
    document_id: UUID
    page: int
    repeat_justification: str | None = None

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be 1 or more")
        if self.repeat_justification is not None and not self.repeat_justification.strip():
            object.__setattr__(self, "repeat_justification", None)


@dataclass(frozen=True)
class LayoutActivity:
    """An activity of the layout with its pages in order.

    `group_number` and `item_number` are where the scoring placed the activity when the layout
    was saved; they let a later change of item be noticed (ARR-05, ARR-08). Unknown when None.
    """

    activity_id: UUID
    pages: tuple[LayoutPage, ...] = ()
    group_number: int | None = None
    item_number: int | None = None


@dataclass(frozen=True)
class ComprovanteLayout:
    """`version` 0 is an arrangement derived from the links and never saved."""

    process_id: UUID
    activities: tuple[LayoutActivity, ...]
    base_evidence_keys: tuple[EvidenceKey, ...] = ()
    version: int = 0


@dataclass(frozen=True)
class PlanPage:
    kind: PageKind
    number: int
    group_number: int | None = None
    document_id: UUID | None = None
    source_page: int | None = None


class TocLevel(StrEnum):
    GRUPO = "GRUPO"
    ITEM = "ITEM"
    ATIVIDADE = "ATIVIDADE"


@dataclass(frozen=True)
class ActivityPageRef:
    """A page of an activity: the source page and the page of the Comprovante it is in.

    A `remission` is a page already attached for another activity: `comprovante_page` is where
    that copy is and nothing new is attached. A repeat the user justified is attached again and
    keeps its `justification`.
    """

    document_id: UUID
    source_page: int
    comprovante_page: int
    remission: bool = False
    justification: str | None = None


@dataclass(frozen=True)
class TocEntry:
    """A line of the table of contents.

    A group or an item has the number of its first page; the table gives it the name. An
    activity has its title, the pages it comes from and the range it takes in the Comprovante.
    """

    level: TocLevel
    group_number: int
    item_number: int | None = None
    activity_id: UUID | None = None
    title: str = ""
    first_page: int | None = None
    last_page: int | None = None
    sources: tuple[ActivityPageRef, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class PlanAlert:
    """Something the plan found that does not stop the generation (CMP-06, CMP-07)."""

    code: GenerationAlertCode
    activity_id: UUID
    document_id: UUID | None = None
    page: int | None = None
    justification: str | None = None


@dataclass(frozen=True)
class ComprovantePlan:
    pages: tuple[PlanPage, ...]
    plan_hash: str
    toc: tuple[TocEntry, ...] = ()
    alerts: tuple[PlanAlert, ...] = ()

    def __post_init__(self) -> None:
        if [p.number for p in self.pages] != list(range(1, len(self.pages) + 1)):
            raise ValueError("page numbers must continue from the cover, starting at 1")


@dataclass(frozen=True)
class Staleness:
    """Why a saved layout no longer matches the current activities (ARR-08)."""

    left_activity_ids: tuple[UUID, ...] = ()
    moved_activity_ids: tuple[UUID, ...] = ()
    new_link_activity_ids: tuple[UUID, ...] = ()

    @property
    def is_stale(self) -> bool:
        return bool(self.left_activity_ids or self.moved_activity_ids or self.new_link_activity_ids)
