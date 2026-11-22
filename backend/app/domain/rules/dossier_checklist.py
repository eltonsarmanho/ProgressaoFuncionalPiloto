"""State of each item of the dossier checklist (DOS-01 to DOS-06).

Pure. The order comes from the versioned file; each item is derived from what the process has:
the last ready version of a generated document, the board ordinance with at least one member, or
the mark "Entregue" the person gave to an item the system does not produce.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.entities.board import BoardOrdinance
from app.domain.entities.generated import DocumentKind, GeneratedDocument, GenerationState
from app.domain.entities.report import DossierItem, DossierSource


class ChecklistState(StrEnum):
    GERADO = "GERADO"
    REGISTRADA = "REGISTRADA"
    ENTREGUE = "ENTREGUE"
    PENDENTE = "PENDENTE"


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    order: int
    title: str
    source: DossierSource
    state: ChecklistState
    version_number: int | None = None
    generation_id: UUID | None = None
    outdated_table: bool = False


def latest_ready(documents: Iterable[GeneratedDocument]) -> dict[DocumentKind, GeneratedDocument]:
    """The `PRONTO` version with the highest number of each kind: a newer failure or a run in
    progress does not hide it."""
    found: dict[DocumentKind, GeneratedDocument] = {}
    for row in documents:
        if row.state is not GenerationState.PRONTO or row.version_number is None:
            continue
        current = found.get(row.kind)
        if current is None or (current.version_number or 0) < row.version_number:
            found[row.kind] = row
    return found


def _table_version_id(row: GeneratedDocument) -> str | None:
    return ((row.snapshot or {}).get("table_version") or {}).get("id")


def _is_outdated(row: GeneratedDocument, current_table_version_id: UUID | None) -> bool:
    """True only when the Tabela and the process both name a version and they differ."""
    used = _table_version_id(row)
    if used is None or current_table_version_id is None:
        return False
    return used != str(current_table_version_id)


def _generated(
    item: DossierItem, row: GeneratedDocument | None, current: UUID | None
) -> ChecklistItem:
    if row is None:
        return ChecklistItem(item.key, item.order, item.title, item.source, ChecklistState.PENDENTE)
    return ChecklistItem(
        item.key,
        item.order,
        item.title,
        item.source,
        ChecklistState.GERADO,
        row.version_number,
        row.id,
        outdated_table=row.kind is DocumentKind.TABELA and _is_outdated(row, current),
    )


def _state(item: DossierItem, registered: bool, delivered: Collection[str]) -> ChecklistState:
    if item.source is DossierSource.PORTARIA_BANCA and registered:
        return ChecklistState.REGISTRADA
    if item.source is DossierSource.MANUAL and item.key in delivered:
        return ChecklistState.ENTREGUE
    return ChecklistState.PENDENTE


def dossier_checklist(
    order: Iterable[DossierItem],
    ready_by_kind: Mapping[DocumentKind, GeneratedDocument],
    ordinance: BoardOrdinance | None,
    delivered_keys: Collection[str],
    current_table_version_id: UUID | None,
) -> list[ChecklistItem]:
    """`ready_by_kind` holds the last ready version of each kind (see `latest_ready`);
    `current_table_version_id` is the scoring table version chosen for the process."""
    registered = ordinance is not None and ordinance.is_registered
    items = []
    for item in order:
        if item.source is DossierSource.GERADO and item.generated_by is not None:
            items.append(
                _generated(item, ready_by_kind.get(item.generated_by), current_table_version_id)
            )
        else:
            state = _state(item, registered, delivered_keys)
            items.append(ChecklistItem(item.key, item.order, item.title, item.source, state))
    return items
