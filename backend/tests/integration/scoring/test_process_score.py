"""CALC-01, CALC-08..CALC-13, SEL-09, VERIF-09, VERIF-11, VERIF-12 through the use case."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus, Level
from app.domain.entities.process import ProcessStatus
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.errors import NotFound
from app.domain.repositories.ports import ScoringTableRecord
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import NotScoredReason, ScoringAlertCode
from app.domain.rules.scoring_engine import RowStatus
from app.domain.rules.scoring_verification import MinimumStatus
from tests.integration.scoring.conftest import make_official_pending
from tests.support.scoring_variants import INFORMED_GROUP, INFORMED_ITEM

D = Decimal
INSIDE = date(2023, 5, 10)


def add(world, title, group, item, process=None, source=ActivitySource.MANUAL, **kw):
    kw.setdefault("event_date", INSIDE)
    return world.create.execute(
        world.admin,
        (process or world.process).id,
        ActivityData(title=title, group_number=group, item_number=item, **kw),
        source=source,
    )


def codes(score):
    return {a.code: a.severity for a in score.alerts}


def test_without_a_chosen_table_total_is_zero_with_sem_tabela_and_the_suggestion(world):
    add(world, "Orientação", 2, 7, quantity=D("4"))
    add(world, "Banca", 3, 2)

    score = world.calc.execute(world.admin, world.process.id)

    assert score.chosen is None
    assert score.suggested.version.id == world.official_version.id
    assert score.result.total == 0
    assert all(v == 0 for v in score.result.group_subtotals.values())
    assert [r.reasons for r in score.result.rows] == [(NotScoredReason.SEM_TABELA,)] * 2
    assert {r.status for r in score.result.rows} == {RowStatus.NAO_PONTUADA}
    assert score.result.counters.activities == 2
    assert score.result.counters.not_scored == 2
    assert score.minimum.status is MinimumStatus.NAO_DEFINIDO
    assert score.alerts == []


def test_without_table_and_without_any_candidate_alerts_table_not_found(world, add_process):
    old = add_process(start_date=date(2010, 1, 1), end_date=date(2012, 1, 1))

    score = world.calc.execute(world.admin, old.id)

    assert score.suggested is None
    assert codes(score) == {
        ScoringAlertCode.TABELA_NAO_ENCONTRADA: Severity.REQUER_ANALISE_NORMATIVA
    }


def test_result_has_subtotals_total_potential_rows_and_pending_table_alert(official_chosen):
    world = official_chosen
    make_official_pending(world)
    add(world, "Orientação", 2, 7, quantity=D("4"), evidence_note="Declaração")
    add(world, "Projeto", 4, 1, quantity=D("2"), evidence_note="Ata")
    add(world, "Sugerida", 2, 8, quantity=D("3"), source=ActivitySource.SUGERIDA_IA)

    score = world.calc.execute(world.admin, world.process.id)

    result = score.result
    assert result.group_subtotals[2] == D("20")
    assert result.group_subtotals[4] == D("30")
    assert result.total == D("50")
    assert result.potential_total == D("9")
    assert [(r.group_number, r.item_number, r.points, r.status) for r in result.rows] == [
        (2, 7, D("20"), RowStatus.PONTUADA),
        (2, 8, D("9"), RowStatus.POTENCIAL),
        (4, 1, D("30"), RowStatus.PONTUADA),
    ]
    assert result.rows[0].formula_text == "4 × 5"
    assert result.rows[0].unit_points == D("5")
    assert result.rows[0].effective_quantity == D("4")
    assert result.counters.activities == 3
    assert result.counters.with_evidence == 2
    assert result.counters.pending == 1
    assert score.chosen.table_name == "Tabela de Pontuação da UFPA"
    assert codes(score)[ScoringAlertCode.TABELA_PENDENTE_VALIDACAO] is (
        Severity.REQUER_ANALISE_NORMATIVA
    )
    assert [a.id for a in score.activities] == [r.activity_id for r in result.rows]


def test_counters_count_alerts_and_not_scored(official_chosen):
    world = official_chosen
    add(world, "Com comprovante", 2, 7, evidence_note="ok", quantity=D("1"))
    add(world, "Sem comprovante", 2, 8, quantity=D("1"))
    add(world, "Sem categoria", None, None, evidence_note="ok")
    # SEG-01: an activity outside the interstice is not valid and is not counted
    # EDT-02: a manual activity cannot be dated outside the interstice, so this one is imported
    add(world, "Fora", 2, 9, source=ActivitySource.IMPORTADA, event_date=date(2020, 1, 1),
        evidence_note="ok")  # fmt: skip

    counters = world.calc.execute(world.admin, world.process.id).result.counters

    assert (counters.activities, counters.with_evidence, counters.pending) == (3, 2, 0)
    assert (counters.not_scored, counters.with_alerts) == (1, 1)


def test_group_one_percentage_of_total(points_chosen):
    world = points_chosen
    world.create.execute(
        world.admin,
        world.process.id,
        ActivityData(
            title="Disciplina",
            group_number=1,
            academic_period="2023.1",
            level=Level.GRADUACAO,
            hours=D("170"),  # GI-05: 20 points come from the hours (2 x 170 / 17), not informed
            event_date=INSIDE,
        ),
        "Declaração da unidade",
    )
    add(world, "Orientação", 2, 7, quantity=D("16"))

    result = world.calc.execute(world.admin, world.process.id).result

    assert result.group_subtotals[1] == D("20")
    assert result.total == D("100")
    assert result.group1_percent == D("20.00")
    assert ScoringAlertCode.PONTOS_AJUSTADOS_MANUALMENTE not in [
        a.code for a in result.rows[0].alerts
    ]


@pytest.mark.parametrize(
    ("quantity", "status"),
    [(D("20"), MinimumStatus.ATINGE), (D("19"), MinimumStatus.NAO_ATINGE)],
)
def test_minimum_comparison_for_current_class_c(official_chosen, quantity, status):
    world = official_chosen
    add(world, "Orientação", 2, 7, quantity=quantity)

    score = world.calc.execute(world.admin, world.process.id)

    assert score.minimum.status is status
    assert score.minimum.minimum == D("100")
    assert score.minimum.total == quantity * 5


def test_new_career_structure_leaves_the_minimum_undefined_with_alert(world, add_process):
    process = add_process(start_date=date(2024, 11, 23), end_date=date(2026, 11, 23))
    world.choose.execute(world.admin, process.id, world.official_version.id, None, None)
    add(world, "Orientação", 2, 7, process=process, quantity=D("10"), event_date=date(2025, 5, 1))

    score = world.calc.execute(world.admin, process.id)

    assert score.minimum.status is MinimumStatus.NAO_DEFINIDO
    assert score.minimum.minimum is None
    assert codes(score)[ScoringAlertCode.MINIMO_NAO_DEFINIDO] is Severity.REQUER_ANALISE_NORMATIVA


def test_regime_de_without_extension_or_research_alerts(official_chosen):
    world = official_chosen
    add(world, "Orientação", 2, 7, quantity=D("1"))

    alert = next(
        a
        for a in world.calc.execute(world.admin, world.process.id).alerts
        if a.code is ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA
    )

    assert alert.severity is Severity.ALERTA
    assert "art. 13, II" in alert.norm_reference


def test_extension_points_remove_the_extension_or_research_alert(official_chosen):
    world = official_chosen
    add(world, "Projeto", 4, 1, quantity=D("1"))

    score = world.calc.execute(world.admin, world.process.id)

    assert ScoringAlertCode.SEM_EXTENSAO_OU_PESQUISA not in codes(score)


def test_limit_adjustments_are_reported(points_chosen):
    world = points_chosen
    add(world, "Item de valor informado (sintético)", INFORMED_GROUP, INFORMED_ITEM,
        informed_points=D("15"))  # fmt: skip

    result = world.calc.execute(world.admin, world.process.id).result

    [adjustment] = result.limit_adjustments
    assert (adjustment.scope, adjustment.before, adjustment.after) == (
        "ATIVIDADE",
        D("15"),
        D("10"),
    )
    assert result.group_subtotals[8] == D("10")


def test_switching_table_reevaluates_by_group_and_item(official_chosen):
    world = official_chosen
    add(world, "Comissão", 2, 12, quantity=D("4"))
    add(world, "Banca", 3, 2)
    assert world.calc.execute(world.admin, world.process.id).result.group_subtotals[2] == D("20")

    world.choose.execute(world.admin, world.process.id, world.other_version.id, None, "Troca")

    result = world.calc.execute(world.admin, world.process.id).result
    assert result.group_subtotals[2] == D("40")  # II.12 is worth 10 in the other table
    assert result.rows[0].unit_points == D("10")


def test_switching_to_a_table_without_the_item_marks_sem_enquadramento(official_chosen):
    world = official_chosen
    add(world, "Comissão", 2, 12, quantity=D("4"))
    add(world, "Banca", 3, 2)
    small = ScoringTableVersion(
        table_id=uuid.uuid4(),
        name="v1",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Tabela mínima de teste",
        status=TableStatus.OFICIAL,
        groups=(
            ScoringGroup(
                2,
                "Grupo II",
                criteria=(
                    ScoringCriterion(2, 12, "Item", "unidade", ScoringMode.POR_UNIDADE, D("7")),
                ),
            ),
        ),
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(ScoringTableRecord(small.table_id, "Mínima", False, ()))
        uow.scoring_tables.add_version(small)
        uow.commit()
        small_id = uow.scoring_tables.list_versions(small.table_id)[0].id

    world.choose.execute(world.admin, world.process.id, small_id, None, "Teste")

    rows = world.calc.execute(world.admin, world.process.id).result.rows
    assert [(r.group_number, r.item_number, r.points, r.reasons) for r in rows] == [
        (2, 12, D("28"), ()),
        (3, 2, D("0"), (NotScoredReason.SEM_ENQUADRAMENTO,)),
    ]


def test_same_data_gives_the_same_result(official_chosen):
    world = official_chosen
    add(world, "Orientação", 2, 7, quantity=D("4"))
    add(world, "Sugerida", 2, 8, source=ActivitySource.SUGERIDA_IA)

    first = world.calc.execute(world.admin, world.process.id)
    second = world.calc.execute(world.admin, world.process.id)

    assert first.result == second.result
    assert first.alerts == second.alerts


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_process_outside_access_is_not_found(world, actor):
    with pytest.raises(NotFound):
        world.calc.execute(getattr(world, actor), world.process.id)


def test_owner_docente_and_unit_secretaria_may_calculate_even_when_closed(official_chosen):
    world = official_chosen
    with world.uow_factory() as uow:
        process = uow.processes.get(world.process.id)
        uow.processes.update(replace(process, status=ProcessStatus.ARQUIVADO), process.version)
        uow.commit()

    for actor in (world.docente, world.secretaria):
        assert world.calc.execute(actor, world.process.id).process_id == world.process.id


def test_activity_status_is_visible_through_the_activities(official_chosen):
    world = official_chosen
    add(world, "Sugerida", 2, 8, source=ActivitySource.SUGERIDA_IA)

    score = world.calc.execute(world.admin, world.process.id)

    assert score.activities[0].status is ActivityStatus.AGUARDANDO_REVISAO
