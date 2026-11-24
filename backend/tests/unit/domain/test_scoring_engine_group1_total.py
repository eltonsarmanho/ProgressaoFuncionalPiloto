"""GI-01..GI-06, GI-08, GI-09: group I counts in the total at 1 point per PIT hour.

Every version here is a synthetic table (not the official one); the version with the group inside
the total stands for the new official version, the one with the group outside for the old one.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.domain.entities.activity import ActivityStatus, Level
from app.domain.rules.activity_validity import InvalidReason
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus, calculate
from tests.unit.domain.scenario_211 import INTERSTICE, activity
from tests.unit.domain.scenario_211 import official_like_table as _outside_version

D = Decimal


def synthetic_group_inside_version():
    """Synthetic table whose group I counts in the total (stands for the new version)."""
    version = _outside_version()
    inside = replace(version.groups[0], counts_in_total=True)
    return replace(
        version, name="Tabela sintética, Grupo I no total", groups=(inside, *version.groups[1:])
    )


def synthetic_group_outside_version():
    """Synthetic table whose group I is outside the total (stands for the old version)."""
    return replace(_outside_version(), name="Tabela sintética, Grupo I fora do total")


BOTH = (synthetic_group_inside_version, synthetic_group_outside_version)


def offer(hours, level=Level.GRADUACAO, period="2023.1", **kwargs):
    item = 1 if level is Level.GRADUACAO else 2
    return activity(1, item, hours=D(hours), level=level, academic_period=period, **kwargs)


def row_of(result, act):
    return next(r for r in result.rows if r.activity_id == act.id)


def has_row(result, act) -> bool:
    return any(r.activity_id == act.id for r in result.rows)


# --- GI-01: points are the PIT hours -----------------------------------------------------------


def test_68_hours_in_graduation_give_8_points():
    a = offer("68")

    row = row_of(calculate(synthetic_group_inside_version(), [a], INTERSTICE), a)

    assert row.points == D("8.00")


def test_34_hours_in_graduation_give_4_points():
    a = offer("34")

    row = row_of(calculate(synthetic_group_inside_version(), [a], INTERSTICE), a)

    assert row.points == D("4.00")


def test_68_hours_in_postgraduation_give_12_points():
    a = offer("68", level=Level.POS_GRADUACAO)

    row = row_of(calculate(synthetic_group_inside_version(), [a], INTERSTICE), a)

    assert row.points == D("12.00")


def test_a_hundredth_is_rounded_half_up_not_half_even_nor_down():
    # 0,0425 h x 2 / 17 = 0,005 exactly: half up gives 0,01, half even and down give 0,00
    a = offer("0.0425")

    row = row_of(calculate(synthetic_group_inside_version(), [a], INTERSTICE), a)

    assert row.points == D("0.01")


def test_points_equal_the_pit_hours_and_the_row_is_inside_the_total_in_every_weekly_load_row():
    offers = [offer("68"), offer("34"), offer("68", level=Level.POS_GRADUACAO), offer("0.0425")]

    result = calculate(synthetic_group_inside_version(), offers, INTERSTICE)

    assert len(result.rows) == 4
    for row in result.rows:
        assert row.points == row.pit_hours
        assert row.outside_total is False


# --- GI-02: subtotal and total -----------------------------------------------------------------


def test_group1_subtotal_is_the_sum_of_the_scored_offers_and_the_total_sums_groups_i_to_viii():
    offers = [offer("68"), offer("34"), offer("68", level=Level.POS_GRADUACAO)]
    others = [activity(2, 3), activity(3, 2)]  # 20 and 7 points

    result = calculate(synthetic_group_inside_version(), offers + others, INTERSTICE)

    assert result.group_subtotals[1] == D("24.00")
    assert result.total == D("51.00")
    assert result.total == sum(result.group_subtotals[n] for n in range(1, 9))


def test_a_potential_offer_stays_out_of_the_subtotal_and_the_total():
    scored = offer("68")
    waiting = offer("34", status=ActivityStatus.AGUARDANDO_REVISAO)

    result = calculate(synthetic_group_inside_version(), [scored, waiting], INTERSTICE)

    assert row_of(result, waiting).status is RowStatus.POTENCIAL
    assert result.group_subtotals[1] == D("8.00")
    assert result.total == D("8.00")


def test_the_subtotal_is_the_sum_of_the_rounded_rows():
    # three offers of 0,0425 h: each row is 0,01 (half up), the subtotal is 0,03 and not 0,02
    offers = [offer("0.0425"), offer("0.0425"), offer("0.0425")]

    result = calculate(synthetic_group_inside_version(), offers, INTERSTICE)

    assert result.group_subtotals[1] == D("0.03")
    assert result.group_subtotals[1] == sum(r.points for r in result.rows)


# --- GI-03: hours by period and in total -------------------------------------------------------


def test_hours_by_period_and_in_total_equal_the_group1_subtotal_without_a_cap():
    offers = [
        offer("68", period="2023.1"),
        offer("34", period="2023.1"),
        offer("68", period="2023.2"),
    ]

    result = calculate(synthetic_group_inside_version(), offers, INTERSTICE)

    assert result.group1_hours_by_period == {"2023.1": D("12.00"), "2023.2": D("8.00")}
    assert result.group1_total_hours == D("20.00")
    assert result.group1_total_hours == result.group_subtotals[1]


def test_a_cap_on_group_one_makes_the_hours_larger_than_the_subtotal_s4():
    base = synthetic_group_inside_version()
    capped = replace(base.groups[0], max_points=D("5"))
    version = replace(base, groups=(capped, *base.groups[1:]))

    result = calculate(version, [offer("68")], INTERSTICE)

    assert result.group_subtotals[1] == D("5")
    assert result.group1_total_hours == D("8.00")


# --- GI-04: offer outside the interstice -------------------------------------------------------


def test_an_offer_dated_outside_the_interstice_is_not_a_row_and_adds_nothing():
    for make in BOTH:
        out = offer("68", event_date=date(2020, 3, 1))

        result = calculate(make(), [out], INTERSTICE)

        assert not has_row(result, out)
        assert result.validity[out.id].reason is InvalidReason.FORA_DO_INTERSTICIO
        assert result.group_subtotals[1] == D("0")
        assert result.total == D("0")
        assert result.group1_total_hours == D("0")
        assert result.group1_hours_by_period == {}


def test_an_offer_dated_outside_does_not_change_the_hours_of_the_one_inside():
    for make in BOTH:
        out = offer("68", event_date=date(2020, 3, 1))
        inside = offer("34")

        result = calculate(make(), [out, inside], INTERSTICE)

        assert result.group1_total_hours == D("4.00")


# --- GI-05: informed points never replace the calculation --------------------------------------


def test_stored_informed_points_are_ignored_in_both_versions():
    for make in BOTH:
        a = offer("68", points_override=D("99"))

        row = row_of(calculate(make(), [a], INTERSTICE), a)

        assert row.pit_hours == D("8.00")
        assert D("99") not in (row.points, row.pit_hours)
        codes = {alert.code for alert in row.alerts}
        assert ScoringAlertCode.PONTOS_AJUSTADOS_MANUALMENTE not in codes


def test_stored_informed_points_do_not_change_the_group1_subtotal_of_the_new_version():
    a = offer("68", points_override=D("99"))

    result = calculate(synthetic_group_inside_version(), [a], INTERSTICE)

    assert result.group_subtotals[1] == D("8.00")


# --- GI-06: the version with the group outside the total is unchanged ---------------------------


def test_group_outside_the_total_keeps_zero_points_hours_and_the_outside_mark():
    a = offer("68")
    other = activity(2, 3)  # 20 points

    result = calculate(synthetic_group_outside_version(), [a, other], INTERSTICE)

    row = row_of(result, a)
    assert row.points == D("0")
    assert row.pit_hours == D("8.00")
    assert row.outside_total is True
    assert result.group_subtotals[1] == D("0")
    assert result.total == D("20")
    assert result.group1_total_hours == D("8.00")


def test_the_same_set_gives_the_total_of_groups_ii_to_viii_in_the_old_version():
    activities = [offer("68"), offer("34"), activity(2, 3), activity(3, 2)]

    old = calculate(synthetic_group_outside_version(), activities, INTERSTICE)
    new = calculate(synthetic_group_inside_version(), activities, INTERSTICE)

    assert old.total == D("27")
    assert new.total == D("39.00")
    assert new.total - old.total == new.group_subtotals[1]


def test_rows_of_other_groups_are_never_marked_outside_the_total():
    a = activity(2, 3)

    for make in BOTH:
        assert row_of(calculate(make(), [a], INTERSTICE), a).outside_total is False


# --- GI-08: percentage of group I over the total, without an alert -----------------------------


def test_group1_percent_is_the_group1_subtotal_over_the_total():
    activities = [offer("68"), activity(2, 3)]  # 8 + 20

    result = calculate(synthetic_group_inside_version(), activities, INTERSTICE)

    assert result.group1_percent == D("28.57")


def test_the_group1_share_raises_no_alert():
    activities = [offer("68"), offer("68"), offer("68"), activity(3, 2)]  # 24 of 31 points

    result = calculate(synthetic_group_inside_version(), activities, INTERSTICE)

    assert result.group1_percent == D("77.42")
    assert result.limit_adjustments == ()
    assert all(row.alerts == () for row in result.rows)


# --- GI-09: offer with only an academic period (engine side) -----------------------------------


def undated_offer(hours, period):
    return offer(hours, period=period, event_date=None)


def test_an_undated_offer_whose_whole_year_is_outside_the_interstice_adds_nothing():
    for make in BOTH:
        old = undated_offer("68", "2019.1")

        result = calculate(make(), [old], INTERSTICE)

        assert not has_row(result, old)
        assert result.validity[old.id].reason is InvalidReason.FORA_DO_INTERSTICIO
        assert result.group_subtotals[1] == D("0")
        assert result.total == D("0")
        assert result.group1_total_hours == D("0")
        assert result.group1_hours_by_period == {}


def test_an_undated_offer_of_a_year_that_crosses_the_interstice_still_counts():
    crossing = undated_offer("68", "2022.1")  # the interstice starts on 23/11/2022

    result = calculate(synthetic_group_inside_version(), [crossing], INTERSTICE)

    assert has_row(result, crossing)
    assert result.group_subtotals[1] == D("8.00")
