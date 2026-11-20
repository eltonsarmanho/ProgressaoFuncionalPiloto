"""CALC-01, CALC-07..CALC-14 and VERIF-08: the deterministic scoring engine."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count
from uuid import uuid4

from app.domain.entities.activity import Activity, ActivityStatus, Level
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.activity_validity import InvalidReason
from app.domain.rules.interstice import Interstice
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus, calculate

D = Decimal
INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))
INSIDE = date(2023, 6, 1)
_seq = count(1)


def per_unit(group, item, points, max_points=None) -> ScoringCriterion:
    return ScoringCriterion(
        group, item, f"item {group}.{item}", "unidade", ScoringMode.POR_UNIDADE,
        unit_points=D(points), max_points=None if max_points is None else D(max_points),
    )  # fmt: skip


def group(number, *criteria, counts=True, max_points=None) -> ScoringGroup:
    return ScoringGroup(
        number, f"Grupo {number}", counts_in_total=counts,
        max_points=None if max_points is None else D(max_points), criteria=tuple(criteria),
    )  # fmt: skip


def table(*groups) -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=None,
        name="Tabela de teste",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Res. 4.644/2015-CONSEPE, Anexo I",
        status=TableStatus.OFICIAL,
        groups=tuple(groups),
    )


def act(g=2, item=7, quantity="1", **kwargs) -> Activity:
    n = next(_seq)
    defaults = {
        "title": f"Atividade {n}",
        "event_date": INSIDE,
        "evidence_note": "Certificado",
        "created_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Activity(
        id=uuid4(), process_id=uuid4(), created_by=uuid4(), group_number=g, item_number=item,
        quantity=D(quantity), **defaults,
    )  # fmt: skip


BASIC = table(group(2, per_unit(2, 7, "10")))


def row_of(result, activity):
    return next(r for r in result.rows if r.activity_id == activity.id)


def has_row(result, activity) -> bool:
    return any(r.activity_id == activity.id for r in result.rows)


# --- inclusion rules (CALC-08, CALC-10, VERIF-08) -------------------------------------------


def test_validated_activity_inside_interstice_counts_in_total():
    a = act(quantity="4")

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert row_of(result, a).points == D("40")
    assert result.group_subtotals[2] == D("40")
    assert result.total == D("40")


def test_awaiting_review_becomes_potential_and_stays_out_of_the_total():
    a = act(quantity="3", status=ActivityStatus.AGUARDANDO_REVISAO)

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.POTENCIAL
    assert row_of(result, a).points == D("30")
    assert result.potential_total == D("30")
    assert result.total == D("0")
    assert result.group_subtotals[2] == D("0")


def test_rejected_activity_is_not_valid_with_reason_rejeitada_and_has_no_row():
    # SEG-01: a rejected activity is not valid, so it no longer shows as a "not scored" row.
    a = act(status=ActivityStatus.REJEITADA)

    result = calculate(BASIC, [a], INTERSTICE)

    assert not has_row(result, a)
    assert result.validity[a.id].reason is InvalidReason.REJEITADA
    assert result.total == D("0")


def test_activity_without_criterion_in_table_is_sem_enquadramento():
    a = act(item=99)

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.NAO_PONTUADA
    assert row_of(result, a).reasons == (NotScoredReason.SEM_ENQUADRAMENTO,)
    assert result.total == D("0")


def test_activity_without_group_and_item_is_sem_enquadramento():
    a = act(g=None, item=None)

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).reasons == (NotScoredReason.SEM_ENQUADRAMENTO,)


def test_activity_outside_interstice_is_not_valid_fora_do_interstício_and_has_no_row():
    # SEG-01: outside the interstice is a validity reason, not a "not scored" row.
    a = act(event_date=date(2022, 11, 22))

    result = calculate(BASIC, [a], INTERSTICE)

    assert not has_row(result, a)
    assert result.validity[a.id].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.total == D("0")


def test_group_that_does_not_count_gives_zero_subtotal_and_reason():
    version = table(group(1, per_unit(1, 1, "10"), counts=False), group(2, per_unit(2, 7, "10")))
    a = act(g=1, item=1, quantity="2")
    b = act(quantity="1")

    result = calculate(version, [a, b], INTERSTICE)

    # SEG-01: a group outside the total is a validity reason; the activity has no row
    assert not has_row(result, a)
    assert result.validity[a.id].reason is InvalidReason.GRUPO_NAO_CONTA
    assert result.group_subtotals[1] == D("0")
    assert result.total == D("10")


def test_newer_duplicate_is_excluded_and_older_counts():
    older = act(title="Comissão X", created_at=datetime(2025, 1, 1, tzinfo=UTC))
    newer = act(title="comissao x", created_at=datetime(2025, 1, 2, tzinfo=UTC))

    result = calculate(BASIC, [newer, older], INTERSTICE)

    assert row_of(result, older).status is RowStatus.PONTUADA
    # SEG-01: the residual duplicate is not valid; it has no row
    assert not has_row(result, newer)
    assert result.validity[newer.id].reason is InvalidReason.DUPLICIDADE
    assert result.total == D("10")


def test_distinct_justification_makes_both_count():
    older = act(title="Comissão X", created_at=datetime(2025, 1, 1, tzinfo=UTC))
    newer = act(
        title="Comissão X",
        created_at=datetime(2025, 1, 2, tzinfo=UTC),
        distinct_justification="Outra comissão",
    )

    result = calculate(BASIC, [older, newer], INTERSTICE)

    assert result.total == D("20")


def test_precedence_rejected_over_missing_criterion_and_over_period():
    # SEG-01: the rule changed; rejected now comes first, before the missing criterion
    rejected_missing = act(item=99, status=ActivityStatus.REJEITADA)
    rejected_outside = act(status=ActivityStatus.REJEITADA, event_date=date(2020, 1, 1))

    result = calculate(BASIC, [rejected_missing, rejected_outside], INTERSTICE)

    assert result.validity[rejected_missing.id].reason is InvalidReason.REJEITADA
    assert result.validity[rejected_outside.id].reason is InvalidReason.REJEITADA
    assert result.rows == ()


def test_precedence_period_over_group_that_does_not_count():
    version = table(group(1, per_unit(1, 1, "10"), counts=False))
    a = act(g=1, item=1, event_date=date(2020, 1, 1))

    result = calculate(version, [a], INTERSTICE)

    assert result.validity[a.id].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert not has_row(result, a)


def test_awaiting_review_outside_interstice_is_not_potential():
    a = act(status=ActivityStatus.AGUARDANDO_REVISAO, event_date=date(2020, 1, 1))

    result = calculate(BASIC, [a], INTERSTICE)

    assert not has_row(result, a)  # SEG-01
    assert result.potential_total == D("0")


# --- limits (CALC-07) -----------------------------------------------------------------------


def test_criterion_cap_cuts_the_sum_and_reports_before_and_after():
    version = table(group(3, per_unit(3, 1, "6", max_points="10")))
    a, b = act(g=3, item=1), act(g=3, item=1)

    result = calculate(version, [a, b], INTERSTICE)

    assert result.group_subtotals[3] == D("10")
    assert result.total == D("10")
    assert len(result.limit_adjustments) == 1
    adjustment = result.limit_adjustments[0]
    assert (adjustment.scope, adjustment.group_number, adjustment.item_number) == ("CRITERIO", 3, 1)
    assert (adjustment.before, adjustment.after) == (D("12"), D("10"))
    assert adjustment.alert.code is ScoringAlertCode.LIMITE_APLICADO
    assert adjustment.alert.severity is Severity.ALERTA


def test_per_activity_points_stay_uncapped_when_the_criterion_cap_applies():
    version = table(group(3, per_unit(3, 1, "6", max_points="10")))
    a, b = act(g=3, item=1), act(g=3, item=1)

    result = calculate(version, [a, b], INTERSTICE)

    assert row_of(result, a).points == D("6")
    assert row_of(result, b).points == D("6")


def test_group_cap_cuts_the_group_subtotal():
    version = table(group(4, per_unit(4, 1, "30"), per_unit(4, 2, "30"), max_points="50"))

    result = calculate(version, [act(g=4, item=1), act(g=4, item=2)], INTERSTICE)

    assert result.group_subtotals[4] == D("50")
    adjustment = result.limit_adjustments[0]
    assert (adjustment.scope, adjustment.group_number, adjustment.item_number) == ("GRUPO", 4, None)
    assert (adjustment.before, adjustment.after) == (D("60"), D("50"))
    assert adjustment.alert.code is ScoringAlertCode.LIMITE_APLICADO


def test_criterion_cap_is_applied_before_the_group_cap():
    version = table(
        group(4, per_unit(4, 1, "30", max_points="20"), per_unit(4, 2, "30"), max_points="45")
    )

    result = calculate(version, [act(g=4, item=1), act(g=4, item=2)], INTERSTICE)

    assert result.group_subtotals[4] == D("45")
    assert [(a.scope, a.before, a.after) for a in result.limit_adjustments] == [
        ("CRITERIO", D("30"), D("20")),
        ("GRUPO", D("50"), D("45")),
    ]


def test_sum_at_or_below_the_limit_reports_no_adjustment():
    version = table(group(3, per_unit(3, 1, "5", max_points="10")))

    result = calculate(version, [act(g=3, item=1), act(g=3, item=1)], INTERSTICE)

    assert result.group_subtotals[3] == D("10")
    assert result.limit_adjustments == ()


def test_cap_ignores_activities_that_do_not_count():
    version = table(group(3, per_unit(3, 1, "8", max_points="10")))
    counted = act(g=3, item=1)
    pending = act(g=3, item=1, status=ActivityStatus.AGUARDANDO_REVISAO)
    rejected = act(g=3, item=1, status=ActivityStatus.REJEITADA)

    result = calculate(version, [counted, pending, rejected], INTERSTICE)

    assert result.total == D("8")
    assert result.limit_adjustments == ()


def test_informed_value_above_the_criterion_cap_is_reported_per_activity():
    criterion = ScoringCriterion(
        1, 3, "Avaliação discente", "nota", ScoringMode.VALOR_INFORMADO, max_points=D("10")
    )
    a = act(g=1, item=3, informed_points=D("14"))

    result = calculate(table(group(1, criterion)), [a], INTERSTICE)

    assert row_of(result, a).points == D("10")
    assert result.group_subtotals[1] == D("10")
    adjustment = result.limit_adjustments[0]
    assert (adjustment.scope, adjustment.activity_id) == ("ATIVIDADE", a.id)
    assert (adjustment.before, adjustment.after) == (D("14"), D("10"))
    assert ScoringAlertCode.LIMITE_APLICADO in {x.code for x in row_of(result, a).alerts}


# --- row alerts (VERIF-03, VERIF-04, VERIF-08, CALC-06) ---------------------------------------


def codes(result, activity):
    return {alert.code for alert in row_of(result, activity).alerts}


def test_partial_period_is_scored_with_intersticio_parcial_alert():
    a = act(
        quantity="2",
        event_date=None,
        period_start=date(2022, 10, 1),
        period_end=date(2023, 1, 1),
    )

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert row_of(result, a).points == D("20")
    assert ScoringAlertCode.INTERSTICIO_PARCIAL in codes(result, a)


def test_activity_without_date_is_scored_with_data_ausente_alert():
    a = act(event_date=None)

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert ScoringAlertCode.DATA_AUSENTE in codes(result, a)


def test_activity_without_evidence_note_keeps_points_and_gets_sem_comprovante():
    a = act(evidence_note=None)
    b = act(evidence_note="  ")
    c = act()

    result = calculate(BASIC, [a, b, c], INTERSTICE)

    assert ScoringAlertCode.SEM_COMPROVANTE in codes(result, a)
    assert ScoringAlertCode.SEM_COMPROVANTE in codes(result, b)
    assert ScoringAlertCode.SEM_COMPROVANTE not in codes(result, c)
    assert result.total == D("30")


def test_manual_points_on_weekly_load_raise_pontos_ajustados_manualmente():
    criterion = ScoringCriterion(
        1, 1, "Aulas", "h", ScoringMode.CARGA_SEMANAL, weeks_per_semester=17, prep_ratio=D("1")
    )
    a = act(g=1, item=1, hours=D("68"), points_override=D("24"), level=Level.GRADUACAO)

    result = calculate(table(group(1, criterion)), [a], INTERSTICE)

    assert row_of(result, a).points == D("24")
    assert ScoringAlertCode.PONTOS_AJUSTADOS_MANUALMENTE in codes(result, a)


# --- unit value typed by hand (UIM-21) ----------------------------------------------------


def test_unit_points_override_replaces_the_table_value_per_unit():
    a = act(quantity="3", unit_points_override=D("2.5"))

    result = calculate(BASIC, [a], INTERSTICE)

    row = row_of(result, a)
    assert row.points == D("7.5")
    assert row.unit_points == D("2.5")
    assert row.effective_quantity == D("3")
    assert ScoringAlertCode.VALOR_UNITARIO_MANUAL in codes(result, a)
    assert result.total == D("7.5")


def test_unit_points_override_survives_a_quantity_change():
    three = act(quantity="3", unit_points_override=D("2.5"))
    four = replace(three, quantity=D("4"))

    assert row_of(calculate(BASIC, [four], INTERSTICE), four).points == D("10")


def test_unit_points_override_still_meets_the_criterion_cap():
    version = table(group(3, per_unit(3, 1, "6", max_points="10")))
    a = act(g=3, item=1, unit_points_override=D("8"))
    b = act(g=3, item=1, unit_points_override=D("8"))

    result = calculate(version, [a, b], INTERSTICE)

    assert result.group_subtotals[3] == D("10")
    assert (result.limit_adjustments[0].before, result.limit_adjustments[0].after) == (
        D("16"),
        D("10"),
    )


def test_unit_points_override_per_block_multiplies_the_blocks():
    version = _fasi_miniature()
    a = act(g=4, item=4, hours=D("10"), unit_points_override=D("2"))

    row = row_of(calculate(version, [a], INTERSTICE), a)

    assert row.points == D("6")  # floor(10 / 3) = 3 blocks x 2
    assert row.unit_points == D("2")


def test_without_the_override_the_table_value_and_no_manual_alert():
    a = act(quantity="3")

    result = calculate(BASIC, [a], INTERSTICE)

    assert row_of(result, a).points == D("30")
    assert row_of(result, a).unit_points == D("10")
    assert ScoringAlertCode.VALOR_UNITARIO_MANUAL not in codes(result, a)


def test_unit_points_override_is_ignored_where_there_is_no_unit_value():
    weekly = ScoringCriterion(
        1, 1, "Aulas", "h", ScoringMode.CARGA_SEMANAL, weeks_per_semester=17, prep_ratio=D("1")
    )
    informed = ScoringCriterion(1, 3, "Avaliação", "pt", ScoringMode.VALOR_INFORMADO)
    version = table(group(1, weekly, informed))
    a = act(g=1, item=1, hours=D("68"), level=Level.GRADUACAO, unit_points_override=D("99"))
    b = act(g=1, item=3, informed_points=D("8"), unit_points_override=D("99"))

    result = calculate(version, [a, b], INTERSTICE)

    assert row_of(result, a).points == D("8")  # 68 x 2 / 17
    assert row_of(result, b).points == D("8")
    assert ScoringAlertCode.VALOR_UNITARIO_MANUAL not in codes(result, a)
    assert ScoringAlertCode.VALOR_UNITARIO_MANUAL not in codes(result, b)


def test_row_alerts_carry_severity_message_and_norm_reference():
    a = act(event_date=None, evidence_note=None)

    alerts = row_of(calculate(BASIC, [a], INTERSTICE), a).alerts

    assert len(alerts) == 2
    for alert in alerts:
        assert alert.severity is Severity.ALERTA
        assert alert.message
        assert alert.norm_reference == "Res. 4.644/2015-CONSEPE, Anexo I"


def test_invalid_interstice_does_not_exclude_nor_alert_on_dates():
    a = act(event_date=date(2020, 1, 1))
    bad = Interstice(date(2024, 11, 23), date(2022, 11, 23))

    result = calculate(BASIC, [a], bad)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert result.validity[a.id].is_valid
    assert ScoringAlertCode.INTERSTICIO_PARCIAL not in codes(result, a)


def test_non_scored_row_has_no_alerts():
    # SEG-01: the not scored row left is the one without category (outside the interstice has
    # no row any more)
    a = act(g=None, item=None, evidence_note=None)

    assert row_of(calculate(BASIC, [a], INTERSTICE), a).alerts == ()


# --- row detail, percent, counters, determinism (CALC-01, CALC-11..CALC-13) -------------------


def test_row_reports_criterion_unit_points_effective_quantity_and_formula():
    a = act(quantity="4")

    row = row_of(calculate(BASIC, [a], INTERSTICE), a)

    assert (row.group_number, row.item_number) == (2, 7)
    assert row.unit_points == D("10")
    assert row.effective_quantity == D("4")
    assert row.formula_text == "4 × 10"


def test_subtotals_cover_groups_one_to_eight_with_zero_for_empty_groups():
    result = calculate(BASIC, [act()], INTERSTICE)

    assert sorted(result.group_subtotals) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert result.group_subtotals[2] == D("10")
    assert all(v == D("0") for k, v in result.group_subtotals.items() if k != 2)


def test_group1_percent_is_none_when_total_is_zero():
    assert calculate(BASIC, [], INTERSTICE).group1_percent is None


def test_counters():
    version = table(group(2, per_unit(2, 7, "10")))
    ok = act()
    no_evidence = act(evidence_note=None)
    pending = act(status=ActivityStatus.AGUARDANDO_REVISAO)
    rejected = act(status=ActivityStatus.REJEITADA)
    outside = act(event_date=date(2020, 1, 1))

    everything = [ok, no_evidence, pending, rejected, outside]
    counters = calculate(version, everything, INTERSTICE).counters

    # SEG-01: rejected and outside the interstice are not valid and are not counted
    assert counters.activities == 3
    assert counters.with_evidence == 2  # ok and pending, not no_evidence
    assert counters.pending == 1
    assert counters.not_scored == 0
    assert counters.with_alerts == 1  # no_evidence


def test_same_input_gives_the_same_result():
    activities = [act(quantity="2"), act(g=2, item=99), act(event_date=None)]

    assert calculate(BASIC, activities, INTERSTICE) == calculate(BASIC, activities, INTERSTICE)


# --- real case in miniature (CALC-14) ---------------------------------------------------------


def _fasi_miniature() -> ScoringTableVersion:
    weekly = lambda item, prep: ScoringCriterion(  # noqa: E731
        1, item, f"I.{item}", "h", ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17, prep_ratio=D(prep),
    )  # fmt: skip
    iv4 = ScoringCriterion(
        4, 4, "IV.4", "h", ScoringMode.POR_BLOCO_DE_HORAS,
        unit_points=D("5"), hours_per_block=D("3"),
    )  # fmt: skip
    return table(
        group(1, weekly(1, "1"), weekly(2, "2"), counts=True),
        group(2, per_unit(2, 7, "10"), per_unit(2, 8, "10"), per_unit(2, 12, "10")),
        group(3, per_unit(3, 2, "10"), per_unit(3, 3, "5")),
        group(4, per_unit(4, 1, "15"), iv4),
        group(5),
        group(6, per_unit(6, 6, "30")),
        group(7, per_unit(7, 10, "3")),
        group(
            8, per_unit(8, 11, "25"), per_unit(8, 12, "20"), per_unit(8, 13, "6"),
            per_unit(8, 66, "5"),
        ),
    )  # fmt: skip


def test_real_case_fasi_2022_2024_in_miniature():
    activities = [
        act(g=1, item=1, hours=D("68"), points_override=D("24"), level=Level.GRADUACAO),
        act(g=1, item=1, hours=D("68"), points_override=D("24"), level=Level.GRADUACAO),
        act(g=1, item=2, hours=D("68"), points_override=D("24"), level=Level.POS_GRADUACAO),
        act(g=1, item=1, hours=D("20"), points_override=D("20"), level=Level.GRADUACAO),
    ]
    activities += [act(g=2, item=7) for _ in range(4)]
    activities += [act(g=2, item=8) for _ in range(4)]
    activities += [act(g=2, item=12) for _ in range(4)]
    activities += [act(g=3, item=2), act(g=3, item=3)]
    activities += [act(g=4, item=1) for _ in range(4)]
    activities += [act(g=4, item=4, hours=D("21"))]
    activities += [act(g=6, item=6)]
    activities += [act(g=7, item=10) for _ in range(2)]
    activities += [act(g=8, item=n) for n in (11, 12, 13, 66)]

    result = calculate(_fasi_miniature(), activities, INTERSTICE)

    assert [result.group_subtotals[n] for n in range(1, 9)] == [
        D("92"), D("120"), D("15"), D("95"), D("0"), D("30"), D("6"), D("56"),
    ]  # fmt: skip
    assert result.total == D("414")
    assert result.group1_percent == D("22.22")
    assert result.potential_total == D("0")
    assert result.counters.not_scored == 0


# --- minimum course hours (OFI-06, OFI-07) ------------------------------------------------------


def with_minimum(group_number=4, item=4, points="5", min_hours="20") -> ScoringCriterion:
    return ScoringCriterion(
        group_number, item, f"item {group_number}.{item}", "curso", ScoringMode.POR_UNIDADE,
        unit_points=D(points), min_hours=None if min_hours is None else D(min_hours),
    )  # fmt: skip


COURSES = table(group(4, with_minimum(), with_minimum(item=1, min_hours=None)))


def test_activity_with_19_99_hours_is_not_scored_for_insufficient_load():
    a = act(g=4, item=4, hours=D("19.99"))

    result = calculate(COURSES, [a], INTERSTICE)

    # SEG-01: insufficient load is a validity reason; the activity has no row
    assert not has_row(result, a)
    assert result.validity[a.id].reason is InvalidReason.CARGA_HORARIA_INSUFICIENTE
    assert result.total == D("0")


def test_activity_with_exactly_20_hours_is_scored():
    a = act(g=4, item=4, hours=D("20"))

    result = calculate(COURSES, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert row_of(result, a).points == D("5")
    assert row_of(result, a).reasons == ()
    assert result.total == D("5")


def test_activity_above_the_minimum_is_scored_without_a_load_alert():
    a = act(g=4, item=4, hours=D("21"))

    result = calculate(COURSES, [a], INTERSTICE)

    assert row_of(result, a).points == D("5")
    assert ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA not in codes(result, a)


def test_activity_without_hours_is_scored_with_the_missing_hours_alert():
    a = act(g=4, item=4, hours=None)

    result = calculate(COURSES, [a], INTERSTICE)

    assert row_of(result, a).status is RowStatus.PONTUADA
    assert row_of(result, a).points == D("5")
    assert ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA in codes(result, a)
    missing = ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA
    alert = next(x for x in row_of(result, a).alerts if x.code is missing)
    assert alert.severity is Severity.ALERTA
    assert alert.norm_reference == "Res. 4.644/2015-CONSEPE, Anexo I"
    assert result.total == D("5")


def test_zero_hours_is_below_the_minimum_not_missing():
    a = act(g=4, item=4, hours=D("0"))

    result = calculate(COURSES, [a], INTERSTICE)

    # SEG-01
    assert not has_row(result, a)
    assert result.validity[a.id].reason is InvalidReason.CARGA_HORARIA_INSUFICIENTE


def test_criterion_without_minimum_ignores_hours_and_never_alerts_on_them():
    short = act(g=4, item=1, hours=D("1"))
    none = act(g=4, item=1, hours=None)

    result = calculate(COURSES, [short, none], INTERSTICE)

    assert row_of(result, short).points == D("5")
    assert row_of(result, none).points == D("5")
    assert ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA not in codes(result, none)
    assert result.total == D("10")


def test_insufficient_activity_has_no_row_and_is_not_counted():
    # SEG-01: it was a "not scored" row with no alerts; now it is not valid and not counted
    low = act(g=4, item=4, hours=D("10"), evidence_note=None)
    ok = act(g=4, item=4, hours=D("30"))

    result = calculate(COURSES, [low, ok], INTERSTICE)

    assert not has_row(result, low)
    assert result.counters.not_scored == 0
    assert result.counters.activities == 1
    assert result.total == D("5")


def test_awaiting_review_with_insufficient_hours_is_not_potential():
    a = act(g=4, item=4, hours=D("10"), status=ActivityStatus.AGUARDANDO_REVISAO)

    result = calculate(COURSES, [a], INTERSTICE)

    assert not has_row(result, a)  # SEG-01
    assert result.potential_total == D("0")


def test_outside_interstice_takes_precedence_over_insufficient_hours():
    a = act(g=4, item=4, hours=D("10"), event_date=date(2020, 1, 1))

    result = calculate(COURSES, [a], INTERSTICE)

    assert result.validity[a.id].reason is InvalidReason.FORA_DO_INTERSTICIO  # SEG-01


def test_missing_hours_alert_is_added_to_the_other_row_alerts():
    a = act(g=4, item=4, hours=None, evidence_note=None)

    result = calculate(COURSES, [a], INTERSTICE)

    assert {
        ScoringAlertCode.CARGA_HORARIA_NAO_INFORMADA,
        ScoringAlertCode.SEM_COMPROVANTE,
    } == set(codes(result, a))


# --- group I as PIT hours outside the total (PIT-01, PIT-02) --------------------------------------


def pit_criterion(item, prep) -> ScoringCriterion:
    return ScoringCriterion(
        1, item, f"I.{item}", "horas (PIT)", ScoringMode.CARGA_SEMANAL,
        weeks_per_semester=17, prep_ratio=D(prep),
    )  # fmt: skip


def pit_table() -> ScoringTableVersion:
    return table(
        group(1, pit_criterion(1, "1"), pit_criterion(2, "2"), counts=False),
        group(2, per_unit(2, 7, "10")),
    )


def offer(hours, level=Level.GRADUACAO, period="2023.1", **kwargs):
    item = 1 if level is Level.GRADUACAO else 2
    return act(
        g=1, item=item, hours=D(hours), level=level, academic_period=period, **kwargs
    )


def test_68_hours_in_graduation_give_8_pit_hours_and_no_points():
    a = offer("68")

    result = calculate(pit_table(), [a], INTERSTICE)

    assert row_of(result, a).pit_hours == D("8.00")
    assert row_of(result, a).points == D("0")
    assert row_of(result, a).status is RowStatus.PONTUADA
    assert row_of(result, a).reasons == ()


def test_34_hours_in_graduation_give_4_pit_hours():
    a = offer("34")

    assert row_of(calculate(pit_table(), [a], INTERSTICE), a).pit_hours == D("4.00")


def test_68_hours_in_postgraduation_give_12_pit_hours():
    a = offer("68", level=Level.POS_GRADUACAO)

    assert row_of(calculate(pit_table(), [a], INTERSTICE), a).pit_hours == D("12.00")


def test_pit_hours_are_rounded_half_up_to_two_places():
    a = offer("10")  # 10 / 17 * 2 = 1.1764... -> 1.18

    assert row_of(calculate(pit_table(), [a], INTERSTICE), a).pit_hours == D("1.18")


def test_pit_hours_are_summed_per_academic_period():
    offers = [
        offer("68", period="2023.1"),
        offer("68", period="2023.1"),
        offer("68", level=Level.POS_GRADUACAO, period="2023.1"),
        offer("68", period="2023.2"),
        offer("34", period="2023.2"),
    ]

    result = calculate(pit_table(), offers, INTERSTICE)

    assert result.group1_hours_by_period == {"2023.1": D("28.00"), "2023.2": D("12.00")}
    assert list(result.group1_hours_by_period) == ["2023.1", "2023.2"]


def test_three_offers_of_68_hours_in_one_period_give_24_hours():
    offers = [offer("68", period="2022.2") for _ in range(3)]

    result = calculate(pit_table(), offers, INTERSTICE)

    assert result.group1_hours_by_period == {"2022.2": D("24.00")}
    assert result.group1_total_hours == D("24.00")


def test_group1_total_hours_sums_all_periods():
    offers = [
        offer("68", period="2022.2"),
        offer("68", period="2023.1"),
        offer("34", period="2023.1"),
    ]

    assert calculate(pit_table(), offers, INTERSTICE).group1_total_hours == D("20.00")


def test_group1_contributes_nothing_to_subtotal_total_or_potential():
    scored = offer("68")
    pending = offer("68", status=ActivityStatus.AGUARDANDO_REVISAO)
    other = act(g=2, item=7, quantity="2")

    result = calculate(pit_table(), [scored, pending, other], INTERSTICE)

    assert result.group_subtotals[1] == D("0")
    assert result.total == D("20")
    assert result.potential_total == D("0")
    assert result.group1_percent == D("0.00")


def test_group1_only_process_has_zero_total_and_hours_reported():
    result = calculate(pit_table(), [offer("68")], INTERSTICE)

    assert result.total == D("0")
    assert result.group1_total_hours == D("8.00")
    assert result.group1_percent is None


def test_informed_points_do_not_replace_the_pit_hours_calculation():
    a = offer("68", points_override=D("99"))

    row = row_of(calculate(pit_table(), [a], INTERSTICE), a)

    assert row.pit_hours == D("8.00")
    assert row.points == D("0")
    assert ScoringAlertCode.PONTOS_AJUSTADOS_MANUALMENTE not in {x.code for x in row.alerts}


def test_pit_row_reports_the_hours_formula():
    a = offer("68")

    row = row_of(calculate(pit_table(), [a], INTERSTICE), a)

    assert row.formula_text == "68 h ÷ 17 semanas × (1 + 1) = 8.00"


def test_pit_hours_of_awaiting_review_and_rejected_offers_stay_out_of_the_summary():
    pending = offer("68", status=ActivityStatus.AGUARDANDO_REVISAO)
    rejected = offer("68", status=ActivityStatus.REJEITADA)
    valid = offer("34")

    result = calculate(pit_table(), [pending, rejected, valid], INTERSTICE)

    assert row_of(result, pending).pit_hours == D("8.00")
    assert row_of(result, pending).status is RowStatus.POTENCIAL
    assert not has_row(result, rejected)  # SEG-01: a rejected offer has no row
    assert result.group1_total_hours == D("4.00")


def test_offer_outside_the_interstice_has_no_pit_hours():
    a = offer("68", event_date=date(2020, 1, 1))

    result = calculate(pit_table(), [a], INTERSTICE)

    assert not has_row(result, a)  # SEG-01
    assert result.validity[a.id].reason is InvalidReason.FORA_DO_INTERSTICIO
    assert result.group1_total_hours == D("0")


def test_rows_of_other_groups_have_no_pit_hours_and_result_without_group1_is_empty():
    a = act(g=2, item=7)

    result = calculate(pit_table(), [a], INTERSTICE)

    assert row_of(result, a).pit_hours is None
    assert result.group1_hours_by_period == {}
    assert result.group1_total_hours == D("0")


def test_group1_that_counts_in_total_keeps_the_legacy_points_calculation():
    legacy = table(group(1, pit_criterion(1, "1"), counts=True))
    a = offer("68")

    result = calculate(legacy, [a], INTERSTICE)

    assert row_of(result, a).points == D("8.00")
    assert row_of(result, a).pit_hours is None
    assert result.group_subtotals[1] == D("8.00")
    assert result.group1_total_hours == D("0")


# --- potential split by date (REAL-08) ------------------------------------------------------


def pending(**kwargs):
    return act(status=ActivityStatus.AGUARDANDO_REVISAO, **kwargs)


def test_potential_is_split_into_dated_and_undated_and_the_parts_sum_to_the_total():
    dated = pending(quantity="3")
    undated = pending(quantity="2", event_date=None)

    result = calculate(BASIC, [dated, undated], INTERSTICE)

    assert result.potential_total == D("50")
    assert result.potential_dated == D("30")
    assert result.potential_undated == D("20")
    assert result.potential_dated + result.potential_undated == result.potential_total


def test_undated_activity_keeps_the_rule_of_counting_with_the_missing_date_alert():
    a = act(quantity="2", event_date=None)  # validated

    result = calculate(BASIC, [a], INTERSTICE)

    assert result.total == D("20")
    assert ScoringAlertCode.DATA_AUSENTE in [x.code for x in row_of(result, a).alerts]
    assert (result.potential_dated, result.potential_undated) == (D("0"), D("0"))


def test_partially_overlapping_period_counts_as_dated_potential():
    a = pending(quantity="1", event_date=None,
                period_start=date(2022, 1, 1), period_end=date(2023, 1, 1))  # fmt: skip

    result = calculate(BASIC, [a], INTERSTICE)

    assert (result.potential_dated, result.potential_undated) == (D("10"), D("0"))


def test_dated_outside_the_interstice_is_in_neither_part():
    a = pending(quantity="1", event_date=date(2020, 1, 1))

    result = calculate(BASIC, [a], INTERSTICE)

    assert (result.potential_total, result.potential_dated, result.potential_undated) == (
        D("0"), D("0"), D("0"),
    )  # fmt: skip
