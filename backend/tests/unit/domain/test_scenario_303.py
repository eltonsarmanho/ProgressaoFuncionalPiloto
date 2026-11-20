"""GI-01, GI-02, GI-03: the cenário derivado of 2022-2024 with group I inside the total.

The same activities of `scenario_211` on a synthetic table whose group I counts in the total:
group I scores 24, 24, 24 and 20 (92 points, one per PIT hour) and the total is 211 + 92 = 303.
"""

from decimal import Decimal

from app.domain.rules.scoring_engine import RowStatus
from tests.unit.domain.scenario_211 import scenario_303_result, scenario_result

D = Decimal
PERIODS = {"2023.1": D("24"), "2023.2": D("24"), "2023.3": D("24"), "2023.4": D("20")}


def test_the_total_is_the_211_of_groups_ii_to_viii_plus_the_92_points_of_group_i():
    _, _, previous = scenario_result()
    _, _, result = scenario_303_result()

    assert previous.total == D("211")
    subtotals = result.group_subtotals
    assert subtotals[1] == D("92")
    assert [subtotals[g] for g in range(2, 9)] == [D(x) for x in (52, 7, 62, 0, 30, 4, 56)]
    assert result.total == D("303")
    assert result.total == sum(subtotals.values(), D("0"))


def test_the_hours_per_period_are_24_24_24_and_20_and_equal_the_points_of_group_i():
    _, _, result = scenario_303_result()

    assert result.group1_hours_by_period == PERIODS
    assert result.group1_total_hours == D("92") == result.group_subtotals[1]


def test_every_group_i_row_scores_its_pit_hours_as_points():
    _, _, result = scenario_303_result()
    group_one = [r for r in result.rows if r.group_number == 1]

    assert [r.status for r in group_one] == [RowStatus.PONTUADA] * 12
    assert [r.points for r in group_one] == [r.pit_hours for r in group_one]
    assert sorted(r.points for r in group_one) == [D("4")] + [D("8")] * 11
    assert not any(r.outside_total for r in group_one)
