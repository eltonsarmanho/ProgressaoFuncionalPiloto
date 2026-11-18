"""ATV-01..03, ATV-05..07, ATV-11, ATV-12: creating activities of a process."""

from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import (
    ActivitySource,
    ActivityStatus,
    Candidate,
    Level,
    PeriodPrecision,
)
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, ValidationFailed
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import NotScoredReason
from app.domain.rules.scoring_engine import calculate

D = Decimal
INTERSTICE = Interstice(date(2022, 11, 23), date(2024, 11, 23))


def data(**kw) -> ActivityData:
    kw.setdefault("title", "Atividade de teste")
    kw.setdefault("event_date", date(2023, 5, 10))
    return ActivityData(**kw)


def create(world, process=None, actor=None, **kw):
    process = process or world.process
    return world.create.execute(actor or world.admin, process.id, data(**kw))


def field_of_failure(world, **kw) -> str:
    with pytest.raises(ValidationFailed) as error:
        create(world, **kw)
    return error.value.field


def test_manual_activity_is_validated_and_persisted_as_given(official_chosen):
    world = official_chosen

    activity = world.create.execute(
        world.secretaria,
        world.process.id,
        data(
            group_number=2,
            item_number=7,
            quantity=D("4"),
            description="Orientações",
            evidence_note="Declaração 12/2023",
        ),
    )

    assert activity.status is ActivityStatus.VALIDADA
    assert activity.source is ActivitySource.MANUAL
    assert (activity.group_number, activity.item_number, activity.quantity) == (2, 7, D("4"))
    assert activity.title == "Atividade de teste"
    assert activity.evidence_note == "Declaração 12/2023"
    assert activity.created_by == world.secretaria.id
    with world.uow_factory() as uow:
        assert uow.activities.get(activity.id).event_date == date(2023, 5, 10)
        [event] = uow.audit.list_for("activity", str(activity.id))
    assert (event.action, event.user_id) == (AuditAction.CREATE, world.secretaria.id)
    assert event.changes["title"] == {"before": None, "after": "Atividade de teste"}


@pytest.mark.parametrize("source", [ActivitySource.SUGERIDA_IA, ActivitySource.IMPORTADA])
def test_non_manual_origin_waits_for_review(official_chosen, source):
    world = official_chosen

    activity = world.create.execute(
        world.admin, world.process.id, data(group_number=2, item_number=7), source=source
    )

    assert activity.status is ActivityStatus.AGUARDANDO_REVISAO
    assert activity.source is source


@pytest.mark.parametrize(
    ("level", "item"), [(Level.GRADUACAO, 1), (Level.POS_GRADUACAO, 2)]
)
def test_group_one_derives_item_from_level(official_chosen, level, item):
    world = official_chosen

    activity = create(
        world,
        group_number=1,
        item_number=3 - item,  # the other course item: ignored, the item follows the level
        academic_period="2023.1",
        level=level,
        hours=D("68"),
        course_hours=D("68"),
    )

    assert (activity.group_number, activity.item_number) == (1, item)
    assert activity.academic_period == "2023.1"
    assert activity.level is level
    assert (activity.hours, activity.course_hours) == (D("68"), D("68"))


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"academic_period": None}, "academic_period"),
        ({"academic_period": "2023-1"}, "academic_period"),
        ({"level": None}, "level"),
        ({"hours": None}, "horas"),
    ],
)
def test_group_one_requires_period_level_and_hours(official_chosen, changes, field):
    base = {
        "group_number": 1,
        "academic_period": "2023.1",
        "level": Level.GRADUACAO,
        "hours": D("68"),
    }

    assert field_of_failure(official_chosen, **{**base, **changes}) == field


@pytest.mark.parametrize(
    "kw", [{}, {"group_number": 2}, {"item_number": 7}, {"group_number": 2, "item_number": 999}]
)
def test_missing_or_unknown_item_is_saved_as_sem_enquadramento(official_chosen, kw):
    world = official_chosen

    activity = create(world, **kw)

    assert activity.status is ActivityStatus.VALIDADA
    row = calculate(world.official_version, [activity], INTERSTICE).rows[0]
    assert row.reasons == (NotScoredReason.SEM_ENQUADRAMENTO,)
    assert row.points == 0


@pytest.mark.parametrize("quantity", [D("-1"), D("10000.01"), D("1.5")])
def test_invalid_quantity_is_422_on_quantidade(official_chosen, quantity):
    assert (
        field_of_failure(official_chosen, group_number=2, item_number=7, quantity=quantity)
        == "quantidade"
    )


def test_quantity_limits_are_inclusive(official_chosen):
    assert create(official_chosen, group_number=2, item_number=7, quantity=D("0")).quantity == 0
    big = create(official_chosen, group_number=2, item_number=7, quantity=D("10000"))
    assert big.quantity == D("10000")


@pytest.mark.parametrize("hours", [D("-0.5"), D("10001")])
def test_invalid_hours_is_422_on_horas(official_chosen, hours):
    assert field_of_failure(official_chosen, group_number=4, item_number=4, hours=hours) == "horas"


def test_title_and_evidence_note_limits(official_chosen):
    assert len(create(official_chosen, title="t" * 300).title) == 300
    assert len(create(official_chosen, evidence_note="n" * 500).evidence_note) == 500
    assert field_of_failure(official_chosen, title="t" * 301) == "title"
    assert field_of_failure(official_chosen, evidence_note="n" * 501) == "evidence_note"


def test_month_precision_is_kept(official_chosen):
    activity = create(
        official_chosen,
        event_date=None,
        period_start=date(2022, 12, 1),
        period_end=date(2022, 12, 1),
        period_precision=PeriodPrecision.MONTH,
    )

    assert activity.period_precision is PeriodPrecision.MONTH
    assert (activity.period_start, activity.period_end) == (date(2022, 12, 1), date(2022, 12, 1))


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_closed_process_rejects_creation(world, add_process, status):
    closed = add_process(status=status)

    with pytest.raises(Conflict):
        create(world, process=closed)
    with world.uow_factory() as uow:
        assert uow.activities.list_for_process(closed.id) == []


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_process_outside_access_is_not_found(world, actor):
    with pytest.raises(NotFound):
        create(world, actor=getattr(world, actor))
    with world.uow_factory() as uow:
        assert uow.activities.list_for_process(world.process.id) == []


def test_owner_docente_and_unit_secretaria_may_create(world):
    for actor in (world.docente, world.secretaria, world.admin):
        assert create(world, actor=actor).process_id == world.process.id


def test_points_override_only_for_weekly_load_criteria_and_without_needing_a_justification(
    points_chosen,
):
    world = points_chosen
    weekly = {
        "group_number": 1,
        "academic_period": "2023.1",
        "level": Level.GRADUACAO,
        "hours": D("68"),
        "points_override": D("24"),
    }

    activity = world.create.execute(world.admin, world.process.id, data(**weekly), "Declaração")
    assert activity.points_override == D("24")
    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("activity", str(activity.id))
    assert event.justification == "Declaração"
    assert event.changes["points_override"] == {"before": None, "after": "24"}

    # UIM-16: no justification needed; the audit event simply has none
    without = world.create.execute(world.admin, world.process.id, data(**weekly))
    assert without.points_override == D("24")
    with world.uow_factory() as uow:
        [event_without] = uow.audit.list_for("activity", str(without.id))
    assert event_without.justification is None
    assert event_without.changes["points_override"] == {"before": None, "after": "24"}
    with pytest.raises(ValidationFailed) as per_unit:
        world.create.execute(
            world.admin,
            world.process.id,
            data(group_number=2, item_number=7, points_override=D("5")),
            "x",
        )
    assert per_unit.value.field == "points_override"


def test_unit_points_override_is_saved_audited_and_scored_by_the_engine(official_chosen):
    """UIM-21: the typed unit value feeds the deterministic engine; no justification."""
    world = official_chosen

    activity = create(
        world, group_number=2, item_number=7, quantity=D("3"), unit_points_override=D("2.5")
    )

    assert activity.unit_points_override == D("2.5")
    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("activity", str(activity.id))
        stored = uow.activities.get(activity.id)
    assert event.justification is None
    assert event.changes["unit_points_override"] == {"before": None, "after": "2.5"}
    version = world.official_version
    assert calculate(version, [stored], INTERSTICE).rows[0].points == D("7.5")


@pytest.mark.parametrize(
    "kw",
    [
        {"group_number": 2, "item_number": 7, "unit_points_override": D("-1")},
        {"group_number": 2, "item_number": 7, "unit_points_override": D("10001")},
        {"unit_points_override": D("2")},  # no item chosen
        {"group_number": 2, "item_number": 99, "unit_points_override": D("2")},  # not in the table
    ],
)
def test_unit_points_override_out_of_range_or_without_a_per_unit_item_is_422(official_chosen, kw):
    assert field_of_failure(official_chosen, **kw) == "unit_points_override"


@pytest.mark.parametrize("value", [D("0"), D("10000")])
def test_unit_points_override_accepts_the_range_limits(official_chosen, value):
    activity = create(
        official_chosen, group_number=2, item_number=7, quantity=D("1"), unit_points_override=value
    )

    assert activity.unit_points_override == value


def test_unit_points_override_is_refused_for_weekly_load_and_informed_value_items(points_chosen):
    world = points_chosen
    weekly = {
        "group_number": 1,
        "academic_period": "2023.1",
        "level": Level.GRADUACAO,
        "hours": D("68"),
        "unit_points_override": D("2"),
    }
    informed = {
        "group_number": 1,
        "item_number": 3,
        "informed_points": D("8"),
        "unit_points_override": D("2"),
    }

    assert field_of_failure(world, **weekly) == "unit_points_override"
    assert field_of_failure(world, **informed) == "unit_points_override"


def test_points_override_needs_a_chosen_table(world):
    with pytest.raises(ValidationFailed) as error:
        world.create.execute(
            world.admin,
            world.process.id,
            data(group_number=2, item_number=7, points_override=D("5")),
            "x",
        )

    assert error.value.field == "points_override"


def test_candidate_items_are_saved_with_or_without_a_justification(official_chosen):
    """UIM-16: the justification of a candidate item is optional."""
    candidate = Candidate(4, 2, "Também se enquadra em extensão")
    bare = Candidate(5, 1, "")

    activity = create(
        official_chosen, group_number=3, item_number=2, candidates=(candidate, bare)
    )

    assert activity.candidates == (candidate, bare)


def test_group_one_student_evaluation_item_keeps_informed_points(points_chosen):
    activity = create(points_chosen, group_number=1, item_number=3, informed_points=D("8"))

    assert (activity.group_number, activity.item_number) == (1, 3)
    assert activity.informed_points == D("8")
    assert activity.academic_period is None
