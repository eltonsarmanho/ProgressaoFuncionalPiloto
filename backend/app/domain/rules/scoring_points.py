"""Points of one activity under one criterion, by scoring mode (CALC-02..CALC-06).

Decimal arithmetic only. Rounding (half up, 2 places) happens only in CARGA_SEMANAL.
"""

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import ScoringCriterion, ScoringMode

ZERO = Decimal(0)
CENTS = Decimal("0.01")


@dataclass(frozen=True)
class ActivityPoints:
    points: Decimal
    effective_quantity: Decimal
    formula_text: str
    overridden: bool = False  # points_override replaced the calculation
    limited_from: Decimal | None = None  # points before the criterion cap (VALOR_INFORMADO)
    unit_points: Decimal | None = None  # the unit value used (the table's or the typed one)
    unit_overridden: bool = False  # unit_points_override replaced the table's unit value


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _unit_value(criterion: ScoringCriterion, activity: Activity) -> tuple[Decimal, bool]:
    """The unit value of a per-unit or per-block criterion: the typed one wins (UIM-21)."""
    if activity.unit_points_override is not None:
        return activity.unit_points_override, True
    return criterion.unit_points or ZERO, False


def _per_unit(criterion: ScoringCriterion, activity: Activity) -> ActivityPoints:
    quantity = Decimal(1) if activity.quantity is None else activity.quantity
    unit, typed = _unit_value(criterion, activity)
    return ActivityPoints(
        quantity * unit,
        quantity,
        f"{_fmt(quantity)} × {_fmt(unit)}",
        unit_points=unit,
        unit_overridden=typed,
    )


def _per_block(criterion: ScoringCriterion, activity: Activity) -> ActivityPoints:
    hours = activity.hours or ZERO
    unit, typed = _unit_value(criterion, activity)
    size = criterion.hours_per_block
    if not size:
        return ActivityPoints(ZERO, ZERO, "bloco de horas não definido")
    blocks = (hours / size).to_integral_value(rounding=ROUND_FLOOR)
    text = f"{_fmt(hours)} h ÷ {_fmt(size)} h = {_fmt(blocks)} blocos × {_fmt(unit)}"
    return ActivityPoints(blocks * unit, blocks, text, unit_points=unit, unit_overridden=typed)


def _weekly_load(criterion: ScoringCriterion, activity: Activity) -> ActivityPoints:
    hours = activity.hours or ZERO
    weeks = criterion.weeks_per_semester
    prep = criterion.prep_ratio or ZERO
    if activity.points_override is not None:
        text = f"pontos informados {_fmt(activity.points_override)} (substituem o cálculo)"
        return ActivityPoints(activity.points_override, hours, text, overridden=True)
    if not weeks:
        return ActivityPoints(ZERO, hours, "semanas por semestre não definidas")
    points = (hours * (1 + prep) / Decimal(weeks)).quantize(CENTS, rounding=ROUND_HALF_UP)
    text = f"{_fmt(hours)} h ÷ {weeks} semanas × (1 + {_fmt(prep)}) = {points}"
    return ActivityPoints(points, hours, text)


def _informed(criterion: ScoringCriterion, activity: Activity) -> ActivityPoints:
    informed = activity.informed_points or ZERO
    cap = criterion.max_points
    if cap is not None and informed > cap:
        text = f"pontos informados {_fmt(informed)}, limitados a {_fmt(cap)}"
        return ActivityPoints(cap, Decimal(1), text, limited_from=informed)
    return ActivityPoints(informed, Decimal(1), f"pontos informados {_fmt(informed)}")


_BY_MODE = {
    ScoringMode.POR_UNIDADE: _per_unit,
    ScoringMode.POR_BLOCO_DE_HORAS: _per_block,
    ScoringMode.CARGA_SEMANAL: _weekly_load,
    ScoringMode.VALOR_INFORMADO: _informed,
}


def criterion_points(criterion: ScoringCriterion, activity: Activity) -> ActivityPoints:
    return _BY_MODE[criterion.mode](criterion, activity)
