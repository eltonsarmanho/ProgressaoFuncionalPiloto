"""Synthetic plans and fronts for the tests of the Comprovante pdf (no real document)."""

from uuid import UUID

from app.domain.entities.activity import Activity
from app.domain.entities.comprovante import ComprovantePlan
from app.domain.repositories.ports import ComprovanteFront
from app.domain.rules.comprovante_plan import derive_layout, plan_comprovante
from app.infrastructure.documents.front_matter import TOC_CAPACITY
from tests.unit.domain.comprovante_support import PROCESS_ID, link, make_activity
from tests.unit.domain.test_table_document_totals import HEADER

GROUP_NAMES = {1: "Ensino", 2: "Pesquisa", 3: "Extensão"}
ITEM_NAMES = {(1, 1): "Aula de graduação", (2, 3): "Orientação", (3, 2): "Projeto"}


def front(document_names: dict[UUID, str] | None = None) -> ComprovanteFront:
    return ComprovanteFront(
        header=HEADER,
        table_name="Tabela Sintética 2024",
        group_names=GROUP_NAMES,
        item_names=ITEM_NAMES,
        document_names=document_names or {},
    )


def plan_for(activities: list[Activity], links=(), capacity: int = TOC_CAPACITY) -> ComprovantePlan:
    layout = derive_layout(PROCESS_ID, activities, list(links))
    return plan_comprovante(layout, activities, capacity)


def plan_with_toc_lines(lines: int) -> tuple[ComprovantePlan, list[Activity]]:
    """A plan whose table of contents has exactly `lines` lines (4 or more, and not 5).

    One group with one item takes 2 + 2n lines; with two items, 3 + 2n.
    """
    activities: list[Activity] = []
    if lines % 2 == 0:
        activities = [make_activity(1, 1) for _ in range((lines - 2) // 2)]
    else:
        count = (lines - 3) // 2
        activities = [make_activity(1, 1)] + [make_activity(1, 2) for _ in range(count - 1)]
    return plan_for(activities), activities


def attached_links(activity: Activity, document_id: UUID, pages: list[int]):
    return [link(activity, document_id, page) for page in pages]
