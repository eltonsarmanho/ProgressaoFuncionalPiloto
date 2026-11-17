"""SEL-02, SEL-04, SEL-05: suggest and choose the scoring table of a process."""

import uuid
from datetime import date

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from tests.integration.scoring.conftest import make_official_pending


def stored_version_id(world, process):
    with world.uow_factory() as uow:
        return uow.processes.get(process.id).scoring_table_version_id


def audit_events(world, process):
    with world.uow_factory() as uow:
        return uow.audit.list_for("process", str(process.id))


def codes(result):
    return {a.code: a.severity for a in result.alerts}


def test_suggests_unit_table_valid_on_interstice_end_without_saving(world):
    result = world.suggest.execute(world.admin, world.process.id)

    assert result.chosen is None
    assert result.suggested.version.id == world.official_version.id
    assert result.suggested.table_name == "Tabela de Pontuação da UFPA"
    assert result.alerts == []
    assert stored_version_id(world, world.process) is None
    assert audit_events(world, world.process) == []


def test_without_a_version_for_the_unit_on_that_date_asks_for_explicit_choice(world, add_process):
    old = add_process(start_date=date(2010, 1, 1), end_date=date(2012, 1, 1))

    result = world.suggest.execute(world.admin, old.id)

    assert result.suggested is None
    assert codes(result) == {
        ScoringAlertCode.TABELA_NAO_ENCONTRADA: Severity.REQUER_ANALISE_NORMATIVA
    }


def test_choosing_saves_version_and_audits_previous_and_new(world):
    result = world.choose.execute(
        world.secretaria, world.process.id, world.official_version.id, None, "Tabela da unidade"
    )

    assert result.chosen.version.id == world.official_version.id
    assert stored_version_id(world, world.process) == world.official_version.id
    [event] = audit_events(world, world.process)
    assert event.user_id == world.secretaria.id
    assert event.action is AuditAction.UPDATE
    assert event.changes == {
        "scoring_table_version_id": {"before": None, "after": str(world.official_version.id)}
    }
    assert event.justification == "Tabela da unidade"


def test_choosing_pending_table_reports_pending_validation_alert(world):
    make_official_pending(world)

    result = world.choose.execute(
        world.docente, world.process.id, world.official_version.id, None, None
    )

    assert codes(result) == {
        ScoringAlertCode.TABELA_PENDENTE_VALIDACAO: Severity.REQUER_ANALISE_NORMATIVA
    }


def test_changing_table_audits_the_previous_version(world):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    world.choose.execute(world.admin, world.process.id, world.other_version.id, None, "Troca")

    events = audit_events(world, world.process)
    assert events[-1].changes == {
        "scoring_table_version_id": {
            "before": str(world.official_version.id),
            "after": str(world.other_version.id),
        }
    }
    assert stored_version_id(world, world.process) == world.other_version.id


def test_other_unit_table_requires_justification_in_that_field(world):
    with pytest.raises(ValidationFailed) as error:
        world.choose.execute(world.admin, world.process.id, world.other_version.id, None, "  ")

    assert error.value.field == "justificativa"
    assert stored_version_id(world, world.process) is None


def test_other_unit_table_with_justification_alerts(world):
    result = world.choose.execute(
        world.admin, world.process.id, world.other_version.id, None, "Sem tabela própria"
    )

    assert codes(result) == {ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE: Severity.ALERTA}
    assert audit_events(world, world.process)[0].justification == "Sem tabela própria"


def test_unknown_version_is_rejected_on_the_version_field(world):
    with pytest.raises(ValidationFailed) as error:
        world.choose.execute(world.admin, world.process.id, uuid.uuid4(), None, None)

    assert error.value.field == "version_id"


@pytest.mark.parametrize("actor", ["other_docente", "other_secretaria"])
def test_process_outside_access_is_not_found(world, actor):
    user = getattr(world, actor)

    with pytest.raises(NotFound):
        world.suggest.execute(user, world.process.id)
    with pytest.raises(NotFound):
        world.choose.execute(user, world.process.id, world.official_version.id, None, None)
    assert stored_version_id(world, world.process) is None


def test_owner_docente_and_unit_secretaria_may_read_the_suggestion(world):
    for actor in (world.docente, world.secretaria, world.admin):
        assert world.suggest.execute(actor, world.process.id).suggested is not None


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_closed_process_cannot_change_table(world, add_process, status):
    closed = add_process(status=status)

    with pytest.raises(Conflict):
        world.choose.execute(world.admin, closed.id, world.official_version.id, None, None)


def test_stale_process_version_is_a_conflict(world):
    with pytest.raises(StaleVersion):
        world.choose.execute(
            world.admin,
            world.process.id,
            world.official_version.id,
            world.process.version + 1,
            None,
        )


# SEL-02: the suggested version is the one valid on the interstice END date, not on its start
def test_suggestion_uses_the_interstice_end_date_not_the_start(world, admin_uc):
    new = admin_uc.create_version.execute(
        world.admin,
        world.official_version.table_id,
        world.official_version.id,
        date(2023, 6, 1),  # between the process start (2022-11-23) and its end (2024-11-23)
        None,
        "Nova norma da FASI, 2023",
    )

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.suggested.version.id == new.version.id
    assert result.suggested.version.id != world.official_version.id


# SEL-02 + assumption "Desempate da sugestão": the newest start of validity wins
def test_suggestion_picks_the_newest_validity_when_several_tables_fit_the_unit(world, admin_uc):
    newer = admin_uc.create_table.execute(
        world.admin,
        name="Outra tabela da FASI",
        unit_ids=[world.professor.unit_id],
        valid_from=date(2024, 1, 1),
        valid_to=None,
        norm_reference="Norma de teste",
    )

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.suggested.table_name == "Outra tabela da FASI"
    assert result.suggested.version.table_id == newer.table.id
