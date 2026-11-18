"""Snapshot saved with every generated version: what was used to build the document (VER-02).

The scoring result is never stored (AD-006), so the snapshot is the record of the totals the
document showed. Plain JSON types only; the same input gives the same output.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from app.domain.entities.activity import Activity
from app.domain.entities.generated import DocumentKind
from app.domain.entities.scoring import ScoringTableVersion
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_engine import ScoringResult

_CENTS = Decimal("0.01")
_WITH_LAYOUT = (DocumentKind.TABELA, DocumentKind.COMPROVANTE)


def _money(value: Decimal) -> str:
    """Two-place text, like the scoring API: `211.00`."""
    return f"{value.quantize(_CENTS):.2f}"


def build_snapshot(
    kind: DocumentKind,
    version: ScoringTableVersion,
    interstice: Interstice,
    result: ScoringResult,
    activities: Sequence[Activity],
    *,
    excluded: Mapping[str, int],
    alerts: Sequence[str],
    template: Mapping[str, Any] | None = None,
    layout: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """`activities` are the ones in the document; `excluded` counts the rest by reason.

    `layout` goes into the Tabela and the Comprovante snapshots, `report` and `template` into
    the Relatório one; the others are ignored.
    """
    listed = {a.id for a in activities}
    snapshot: dict[str, Any] = {
        "table_version": {
            "id": None if version.id is None else str(version.id),
            "name": version.name,
            "norm_reference": version.norm_reference,
        },
        "interstice": {"start": interstice.start.isoformat(), "end": interstice.end.isoformat()},
        "total": _money(result.total),
        "subtotals": {str(n): _money(v) for n, v in sorted(result.group_subtotals.items())},
        "pit_hours": {p: _money(h) for p, h in result.group1_hours_by_period.items()},
        "pit_total_hours": _money(result.group1_total_hours),
        "activities": [
            {
                "id": str(row.activity_id),
                "group": row.group_number,
                "item": row.item_number,
                "quantity": None
                if row.effective_quantity is None
                else _money(row.effective_quantity),
                "points": _money(row.points),
                "status": row.status.value,
            }
            for row in result.rows
            if row.activity_id in listed
        ],
        "excluded": dict(sorted(excluded.items())),
        "alerts": list(alerts),
    }
    if kind in _WITH_LAYOUT and layout is not None:
        snapshot["layout"] = dict(layout)
    if kind is DocumentKind.RELATORIO:
        if template is not None:
            snapshot["template"] = dict(template)
        if report is not None:
            snapshot["report"] = dict(report)
    return snapshot
