"""VAL-01, SEG-01, SEG-03, SEG-04: the engine scores only the valid activities."""

from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.activity_validity import InvalidReason, ValidityState
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus, calculate

D = Decimal
INTERSTICE = Interstice(date(2024, 1, 1), date(2026, 12, 31))
INSIDE = date(2025, 6, 1)
_seq = count(1)

TABLE = ScoringTableVersion(
    table_id=None,
    name="Tabela de teste",
    valid_from=date(2020, 1, 1),
    valid_to=None,
    norm_reference="Res. 4.644/2015-CONSEPE, Anexo I",
    status=TableStatus.OFICIAL,
    groups=(
        ScoringGroup(
            2, "Grupo 2", True, None,
            (
                ScoringCriterion(2, 7, "item 2.7", "unidade", ScoringMode.POR_UNIDADE,
                                 unit_points=D("8")),
                ScoringCriterion(2, 8, "item 2.8", "unidade", ScoringMode.POR_UNIDADE,
                                 unit_points=D("3"), min_hours=D("20")),
            ),
        ),
    ),
)  # fmt: skip


def act(group=2, item=7, quantity="1", **kwargs) -> Activity:
    n = next(_seq)
    defaults = {
        "title": f"Atividade distinta numero {n} sobre tema {uuid4().hex}",
        "event_date": INSIDE,
        "evidence_note": "Certificado",
        "created_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=group,
        item_number=item, quantity=D(quantity), **defaults,
    )  # fmt: skip


def rows_of(result, *activities):
    ids = {a.id for a in activities}
    return [r for r in result.rows if r.activity_id in ids]


def not_valid_activities() -> dict[str, Activity]:
    first = act(title="Curso de extensão sobre redes", event_date=date(2025, 3, 1))
    duplicate = act(
        title="Curso de extensão sobre redes", event_date=date(2025, 3, 1),
        created_at=datetime(2025, 2, 1, tzinfo=UTC),
    )  # fmt: skip
    return {
        "outside": act(event_date=date(2020, 1, 1)),
        "rejected": act(status=ActivityStatus.REJEITADA),
        "low_hours": act(item=8, hours=D("10")),
        "first": first,
        "duplicate": duplicate,
    }


# --- only the valid activities produce rows and counters (SEG-01, SEG-04) ------------------


def test_not_valid_activities_produce_no_row():
    found = not_valid_activities()

    result = calculate(TABLE, list(found.values()), INTERSTICE)

    for name in ("outside", "rejected", "low_hours", "duplicate"):
        assert rows_of(result, found[name]) == [], name
    assert len(rows_of(result, found["first"])) == 1


def test_not_valid_activities_do_not_count_in_the_counters():
    found = not_valid_activities()
    awaiting = act(status=ActivityStatus.AGUARDANDO_REVISAO)
    everything = [*found.values(), awaiting]

    result = calculate(TABLE, everything, INTERSTICE)

    # valid ones: "first" and "awaiting"
    assert result.counters.activities == 2
    assert result.counters.pending == 1
    assert result.counters.not_scored == 0


def test_the_total_and_the_subtotals_equal_the_ones_of_the_valid_activities_alone():
    found = not_valid_activities()
    valid = [found["first"], act(quantity="3")]

    others = [a for name, a in found.items() if name != "first"]
    with_invalid = calculate(TABLE, [*valid, *others], INTERSTICE)
    alone = calculate(TABLE, valid, INTERSTICE)

    assert with_invalid.total == alone.total == D("32")
    assert with_invalid.group_subtotals == alone.group_subtotals
    assert with_invalid.potential_total == alone.potential_total
    assert len(with_invalid.rows) == len(alone.rows) == 2


# --- the activity without category stays a SEM_ENQUADRAMENTO row (SEC-02) ------------------


def test_an_activity_without_category_keeps_a_row_and_counts_as_valid():
    uncategorized = act(group=None, item=None)

    result = calculate(TABLE, [uncategorized], INTERSTICE)

    [row] = rows_of(result, uncategorized)
    assert row.status is RowStatus.NAO_PONTUADA
    assert row.reasons == (NotScoredReason.SEM_ENQUADRAMENTO,)
    assert result.counters.activities == 1
    assert result.counters.not_scored == 1


# --- validating scores, with no other action (VAL-01) --------------------------------------


def test_a_validated_activity_with_category_scores_with_the_table_unit_and_the_quantity():
    validated = act(item=7, quantity="1", status=ActivityStatus.VALIDADA)

    result = calculate(TABLE, [validated], INTERSTICE)

    [row] = rows_of(result, validated)
    assert row.status is RowStatus.PONTUADA
    assert row.unit_points == D("8")
    assert row.points == D("8")
    assert result.total == D("8")
    assert result.group_subtotals[2] == D("8")


def test_a_validated_activity_scores_the_informed_quantity_times_the_unit():
    validated = act(item=7, quantity="3")

    result = calculate(TABLE, [validated], INTERSTICE)

    assert result.total == D("24")


# --- the validity map (SEG-03) -------------------------------------------------------------


def test_the_result_carries_the_validity_of_every_activity():
    found = not_valid_activities()
    uncategorized = act(group=None, item=None)
    everything = [*found.values(), uncategorized]

    result = calculate(TABLE, everything, INTERSTICE)

    assert set(result.validity) == {a.id for a in everything}
    assert result.validity[found["outside"].id].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.validity[found["rejected"].id].reason is InvalidReason.REJEITADA
    assert result.validity[found["low_hours"].id].reason is InvalidReason.CARGA_HORARIA_INSUFICIENTE
    assert result.validity[found["duplicate"].id].reason is InvalidReason.DUPLICIDADE
    assert result.validity[found["first"].id].state is ValidityState.VALIDA
    assert result.validity[uncategorized.id].needs_category is True


# --- the quantity assumed to be one (VAL-02) -----------------------------------------------

ASSUMED = ScoringAlertCode.QUANTIDADE_ASSUMIDA

QUANTITY_TABLE = ScoringTableVersion(
    table_id=None,
    name="Tabela de teste",
    valid_from=date(2020, 1, 1),
    valid_to=None,
    norm_reference="Res. 4.644/2015-CONSEPE, Anexo I",
    status=TableStatus.OFICIAL,
    groups=(
        ScoringGroup(
            2, "Grupo 2", True, None,
            (
                ScoringCriterion(2, 7, "por unidade", "por aluno", ScoringMode.POR_UNIDADE,
                                 unit_points=D("8")),
                ScoringCriterion(2, 8, "por bloco", "por bloco", ScoringMode.POR_BLOCO_DE_HORAS,
                                 unit_points=D("2"), hours_per_block=D("10")),
                ScoringCriterion(2, 9, "por ano", "por ano de função", ScoringMode.POR_UNIDADE,
                                 unit_points=D("4")),
                ScoringCriterion(2, 10, "informado", "valor informado", ScoringMode.VALOR_INFORMADO,
                                 max_points=D("30")),
            ),
        ),
    ),
)  # fmt: skip


def alert_codes(result, activity):
    return [a.code for a in row_of(result, activity).alerts]


def row_of(result, activity):
    return next(r for r in result.rows if r.activity_id == activity.id)


def without_quantity(item, **kwargs) -> Activity:
    made = act(item=item, **kwargs)
    made.quantity = None
    return made


def test_a_per_unit_item_without_quantity_scores_one_unit_with_the_alert():
    a = without_quantity(7)

    result = calculate(QUANTITY_TABLE, [a], INTERSTICE)

    assert row_of(result, a).points == D("8")
    assert row_of(result, a).effective_quantity == D("1")
    assert ASSUMED in alert_codes(result, a)


def test_the_alert_is_a_warning_with_a_message_and_the_norm_reference():
    a = without_quantity(7)

    result = calculate(QUANTITY_TABLE, [a], INTERSTICE)

    alert = next(x for x in row_of(result, a).alerts if x.code is ASSUMED)
    assert alert.severity.value == "ALERTA"
    assert alert.message
    assert alert.norm_reference == "Res. 4.644/2015-CONSEPE, Anexo I"


def test_a_per_unit_item_with_the_quantity_informed_has_no_alert():
    a = act(item=7, quantity="3")

    result = calculate(QUANTITY_TABLE, [a], INTERSTICE)

    assert row_of(result, a).points == D("24")
    assert ASSUMED not in alert_codes(result, a)


def test_the_alert_is_only_for_per_unit_items():
    block = without_quantity(8, hours=D("30"))
    yearly = without_quantity(9)
    informed = without_quantity(10, informed_points=D("5"))

    result = calculate(QUANTITY_TABLE, [block, yearly, informed], INTERSTICE)

    for a in (block, yearly, informed):
        assert ASSUMED not in alert_codes(result, a)
