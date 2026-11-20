"""VAL-06, SEC-02, SEC-06, SEC-07, SEG-01: `classify_activity` decides valid or not valid."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus, PeriodPrecision
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.activity_validity import InvalidReason, ValidityState, classify_activity
from app.domain.rules.interstice import Interstice

D = Decimal
INTERSTICE = Interstice(date(2024, 1, 1), date(2026, 12, 31))
INSIDE = date(2025, 6, 1)


def criterion(group, item, unit="unidade", mode=ScoringMode.POR_UNIDADE, min_hours=None):
    return ScoringCriterion(
        group, item, f"item {group}.{item}", unit, mode, unit_points=D("5"), min_hours=min_hours
    )


def table(*groups: ScoringGroup) -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=None,
        name="Tabela de teste",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Res. 4.644/2015-CONSEPE, Anexo I",
        status=TableStatus.OFICIAL,
        groups=groups,
    )


TABLE = table(
    ScoringGroup(2, "Grupo 2", True, None, (criterion(2, 7), criterion(2, 8, min_hours=D("20")))),
    ScoringGroup(3, "Grupo 3", True, None, (criterion(3, 1, unit="por ano de função"),)),
    ScoringGroup(5, "Grupo 5", False, None, (criterion(5, 1),)),
    ScoringGroup(
        1, "Grupo 1", False, None,
        (criterion(1, 1, unit="horas semanais", mode=ScoringMode.CARGA_SEMANAL),),
    ),
)  # fmt: skip


def act(group=2, item=7, **kwargs) -> Activity:
    defaults = {
        "title": "Atividade",
        "event_date": INSIDE,
        "created_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=group,
        item_number=item, **defaults,
    )  # fmt: skip


def classify(activity, version=TABLE, duplicates=frozenset()):
    return classify_activity(activity, version, INTERSTICE, set(duplicates))


# --- the valid activity --------------------------------------------------------------------


def test_a_dated_categorized_activity_inside_the_interstice_is_valid():
    result = classify(act())

    assert result.state is ValidityState.VALIDA
    assert result.reason is None
    assert result.needs_category is False


# --- rejected (SEC-06, SEC-07) -------------------------------------------------------------


def test_a_rejected_activity_is_not_valid_with_reason_rejeitada():
    result = classify(act(status=ActivityStatus.REJEITADA))

    assert result.state is ValidityState.NAO_VALIDA
    assert result.reason is InvalidReason.REJEITADA


def test_a_rejected_activity_without_category_is_rejeitada_not_a_category_problem():
    result = classify(act(group=None, item=None, status=ActivityStatus.REJEITADA))

    assert result.reason is InvalidReason.REJEITADA
    assert result.needs_category is False


# --- date against the interstice (SEC-06, SEC-07) ------------------------------------------


def test_a_date_one_day_before_the_interstice_is_not_valid_with_the_date_and_the_range():
    day = date(2023, 12, 31)

    result = classify(act(event_date=day))

    assert result.state is ValidityState.NAO_VALIDA
    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.params["event_date"] == day
    assert result.params["interstice_start"] == date(2024, 1, 1)
    assert result.params["interstice_end"] == date(2026, 12, 31)


def test_a_date_one_day_after_the_interstice_is_not_valid():
    day = date(2027, 1, 1)

    result = classify(act(event_date=day))

    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.params["event_date"] == day


def test_the_first_and_the_last_day_of_the_interstice_are_valid():
    assert classify(act(event_date=date(2024, 1, 1))).state is ValidityState.VALIDA
    assert classify(act(event_date=date(2026, 12, 31))).state is ValidityState.VALIDA


def test_a_period_outside_the_interstice_carries_its_start_and_end():
    result = classify(
        act(event_date=None, period_start=date(2022, 1, 1), period_end=date(2022, 6, 1))
    )

    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.params["period_start"] == date(2022, 1, 1)
    assert result.params["period_end"] == date(2022, 6, 1)
    assert "event_date" not in result.params


def test_a_yearly_category_whose_period_crosses_the_interstice_is_valid():
    yearly = act(
        group=3, item=1, event_date=None,
        period_start=date(2022, 1, 1), period_end=date(2024, 3, 1),
    )  # fmt: skip

    assert classify(yearly).state is ValidityState.VALIDA


def test_a_yearly_category_whose_period_does_not_touch_the_interstice_is_not_valid():
    yearly = act(
        group=3, item=1, event_date=None,
        period_start=date(2020, 1, 1), period_end=date(2022, 3, 1),
    )  # fmt: skip

    result = classify(yearly)

    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.params["period_start"] == date(2020, 1, 1)


def test_a_yearly_category_with_only_a_start_runs_to_the_end_of_the_interstice():
    started_before = date(2022, 1, 1)
    yearly = act(group=3, item=1, event_date=None, period_start=started_before)
    per_unit = act(group=2, item=7, event_date=None, period_start=started_before)

    assert classify(yearly).state is ValidityState.VALIDA
    assert classify(per_unit).reason is InvalidReason.FORA_DO_INTERSTICIO


def test_a_month_precision_period_is_expanded_to_whole_months():
    month = act(
        event_date=None, period_start=date(2023, 12, 15), period_end=date(2024, 1, 10),
        period_precision=PeriodPrecision.MONTH,
    )  # fmt: skip

    assert classify(month).state is ValidityState.VALIDA


def test_an_activity_without_date_is_valid():
    assert classify(act(event_date=None)).state is ValidityState.VALIDA


# --- category (SEC-02) ---------------------------------------------------------------------


def test_an_activity_without_category_is_valid_and_needs_a_category():
    result = classify(act(group=None, item=None))

    assert result.state is ValidityState.VALIDA
    assert result.reason is None
    assert result.needs_category is True


def test_an_activity_whose_item_is_not_in_the_table_is_valid_and_needs_a_category():
    result = classify(act(group=2, item=99))

    assert result.state is ValidityState.VALIDA
    assert result.needs_category is True


def test_an_activity_without_category_and_outside_the_interstice_is_not_valid():
    result = classify(act(group=None, item=None, event_date=date(2020, 1, 1)))

    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.needs_category is False


# --- group that does not count (SEC-06) ----------------------------------------------------


def test_a_group_outside_the_total_that_is_not_pit_is_not_valid():
    result = classify(act(group=5, item=1))

    assert result.state is ValidityState.NAO_VALIDA
    assert result.reason is InvalidReason.GRUPO_NAO_CONTA


def test_a_pit_offer_of_group_one_is_valid_although_the_group_is_outside_the_total():
    pit = act(group=1, item=1)

    assert classify(pit).state is ValidityState.VALIDA


# --- residual duplicate --------------------------------------------------------------------


def test_a_residual_duplicate_is_not_valid_with_reason_duplicidade():
    a = act()

    result = classify(a, duplicates={a.id})

    assert result.state is ValidityState.NAO_VALIDA
    assert result.reason is InvalidReason.DUPLICIDADE


# --- minimum hours (SEC-06, SEC-07) --------------------------------------------------------


def test_hours_equal_to_the_minimum_are_valid():
    assert classify(act(item=8, hours=D("20"))).state is ValidityState.VALIDA


def test_hours_below_the_minimum_are_not_valid_with_the_hours_and_the_minimum():
    result = classify(act(item=8, hours=D("19.5")))

    assert result.state is ValidityState.NAO_VALIDA
    assert result.reason is InvalidReason.CARGA_HORARIA_INSUFICIENTE
    assert result.params["hours"] == D("19.5")
    assert result.params["min_hours"] == D("20")


def test_no_informed_hours_is_valid():
    assert classify(act(item=8, hours=None)).state is ValidityState.VALIDA


# --- no table chosen -----------------------------------------------------------------------


def test_without_a_table_a_rejected_activity_is_not_valid():
    result = classify(act(status=ActivityStatus.REJEITADA), version=None)

    assert result.reason is InvalidReason.REJEITADA


def test_without_a_table_the_date_is_judged_as_a_day():
    result = classify(act(event_date=date(2020, 1, 1)), version=None)

    assert result.reason is InvalidReason.FORA_DO_INTERSTICIO


def test_without_a_table_an_activity_with_no_group_or_item_needs_a_category():
    result = classify(act(group=None, item=None), version=None)

    assert result.state is ValidityState.VALIDA
    assert result.needs_category is True


def test_without_a_table_hours_group_and_duplicates_are_not_judged():
    low_hours = act(item=8, hours=D("1"))
    outside_group = act(group=5, item=1)
    duplicate = act()

    assert classify(low_hours, version=None).state is ValidityState.VALIDA
    assert classify(outside_group, version=None).state is ValidityState.VALIDA
    assert classify(duplicate, version=None, duplicates={duplicate.id}).state is (
        ValidityState.VALIDA
    )


# --- the order of the reasons is the engine's ---------------------------------------------


def test_rejected_comes_before_the_date():
    result = classify(act(status=ActivityStatus.REJEITADA, event_date=date(2020, 1, 1)))

    assert result.reason is InvalidReason.REJEITADA


def test_the_date_comes_before_the_group_the_duplicate_and_the_hours():
    old = date(2020, 1, 1)
    a = act(group=5, item=1, event_date=old)

    assert classify(a, duplicates={a.id}).reason is InvalidReason.FORA_DO_INTERSTICIO


def test_the_group_comes_before_the_duplicate():
    a = act(group=5, item=1)

    assert classify(a, duplicates={a.id}).reason is InvalidReason.GRUPO_NAO_CONTA


def test_the_duplicate_comes_before_the_hours():
    a = act(item=8, hours=D("1"))

    assert classify(a, duplicates={a.id}).reason is InvalidReason.DUPLICIDADE
