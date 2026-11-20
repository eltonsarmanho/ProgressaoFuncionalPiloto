"""Synthetic acceptance scenario of the generated documents: 211 points and 92 PIT hours.

Subtotals II to VIII of 52, 7, 62, 0, 30, 4 and 56, group I outside the total with PIT hours
of 24, 24, 24 and 20 per academic period. Made-up names only.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count
from uuid import uuid4

from app.domain.entities.activity import Activity, Level
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_engine import calculate

D = Decimal
INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))
INSIDE = date(2023, 6, 1)
GROUP_NAMES = {
    1: "Docência",
    2: "Orientação",
    3: "Bancas",
    4: "Extensão",
    5: "Pesquisa",
    6: "Administrativas e de Representação",
    7: "Capacitação",
    8: "Produção",
}
_seq = count(1)


def per_unit(group: int, item: int, points: str, **kwargs) -> ScoringCriterion:
    return ScoringCriterion(
        group, item, f"Critério {group}.{item}", "unidade", ScoringMode.POR_UNIDADE,
        unit_points=D(points), **kwargs,
    )  # fmt: skip


def pit_criterion(item: int) -> ScoringCriterion:
    return ScoringCriterion(
        1, item, f"Carga semanal {item}", "horas (PIT)", ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17, prep_ratio=D(item),
    )  # fmt: skip


def group(number: int, *criteria: ScoringCriterion, counts: bool = True) -> ScoringGroup:
    return ScoringGroup(
        number, GROUP_NAMES[number], counts_in_total=counts, criteria=tuple(criteria)
    )


def official_like_table() -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=uuid4(),
        name="Tabela de teste 2022",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Res. de teste, Anexo I",
        status=TableStatus.OFICIAL,
        groups=(
            group(1, pit_criterion(1), pit_criterion(2), counts=False),
            group(2, per_unit(2, 3, "20"), per_unit(2, 7, "16")),
            group(3, per_unit(3, 2, "7")),
            group(4, per_unit(4, 4, "2"), per_unit(4, 5, "60")),
            group(5, per_unit(5, 1, "10")),
            group(6, per_unit(6, 6, "30")),
            group(7, per_unit(7, 1, "4")),
            group(8, per_unit(8, 9, "56")),
        ),
    )


def item_capped_table(max_points: str = "40") -> ScoringTableVersion:
    """The official-like table with item 7 of group II limited to `max_points`: ten orientations
    score 160 in the rows and 40 in the subtotal of the engine."""
    table = official_like_table()
    group_two = table.groups[1]
    capped = replace(group_two.criteria[1], max_points=D(max_points))
    group_two = replace(group_two, criteria=(group_two.criteria[0], capped))
    return replace(table, groups=(table.groups[0], group_two, *table.groups[2:]))


def activity(group_number: int, item: int, quantity: str = "1", **kwargs) -> Activity:
    n = next(_seq)
    defaults = {
        "title": f"Atividade sintética {n}",
        "event_date": INSIDE,
        "evidence_note": "Declaração",
        "created_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=group_number,
        item_number=item, quantity=D(quantity), **defaults,
    )  # fmt: skip


def offer(hours: str, period: str) -> Activity:
    return activity(
        1, 1, hours=D(hours), level=Level.GRADUACAO, academic_period=period, quantity="1"
    )


def scenario_activities() -> list[Activity]:
    pit = [offer("68", p) for p in ("2023.1", "2023.2", "2023.3") for _ in range(3)]
    pit += [offer("68", "2023.4"), offer("68", "2023.4"), offer("34", "2023.4")]
    return pit + [
        activity(2, 3),
        activity(2, 7, "2"),
        activity(3, 2),
        activity(4, 4),
        activity(4, 5),
        activity(6, 6),
        activity(7, 1),
        activity(8, 9),
    ]


def scenario_result(activities=None, version=None):
    version = version or official_like_table()
    activities = scenario_activities() if activities is None else activities
    return version, activities, calculate(version, activities, INTERSTICE)
