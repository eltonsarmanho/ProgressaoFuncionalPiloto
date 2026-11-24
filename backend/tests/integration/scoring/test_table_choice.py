"""SEL-02, SEL-04, SEL-05: suggest and choose the scoring table of a process."""

import uuid
from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.repositories.ports import ScoringTableRecord
from app.domain.rules.process_verification import Severity
from app.domain.rules.scoring_alerts import ScoringAlertCode
from tests.integration.scoring.conftest import make_official_pending
from tests.support.races import Gate, Worker, wait_until_blocked


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


def test_other_unit_table_needs_no_justification_and_still_alerts(world):
    """UIM-18: the justification is optional; the alert and the audit event stay."""
    result = world.choose.execute(world.admin, world.process.id, world.other_version.id, None, "  ")

    assert codes(result) == {ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE: Severity.ALERTA}
    assert stored_version_id(world, world.process) == world.other_version.id
    assert audit_events(world, world.process)[0].justification is None


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


# --- GI-07: a superseded version is never suggested nor accepted -------------------------------


def add_twin_version(world):
    """A second version of the same table with the same start, so only the mark tells them apart."""
    twin = replace(world.official_version, id=uuid.uuid4(), name="Versão sintética gêmea")
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(twin)
        uow.commit()
    return twin


def mark_superseded(world, version, by):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(version.id, by.id)
        uow.commit()


def test_the_suggestion_is_the_version_that_is_not_superseded_even_with_the_same_start(world):
    twin = add_twin_version(world)

    mark_superseded(world, world.official_version, twin)
    suggested = world.suggest.execute(world.admin, world.process.id).suggested

    assert suggested.version.id == twin.id


def test_inverting_the_mark_inverts_the_suggestion(world):
    twin = add_twin_version(world)

    mark_superseded(world, twin, world.official_version)
    suggested = world.suggest.execute(world.admin, world.process.id).suggested

    assert suggested.version.id == world.official_version.id


def test_with_only_superseded_versions_there_is_no_suggestion(world):
    twin = add_twin_version(world)
    mark_superseded(world, world.official_version, twin)
    mark_superseded(world, twin, world.official_version)

    assert world.suggest.execute(world.admin, world.process.id).suggested is None


def test_choosing_a_superseded_version_is_422_with_its_code_and_saves_nothing(world):
    twin = add_twin_version(world)
    world.choose.execute(world.admin, world.process.id, twin.id, None, None)
    mark_superseded(world, world.official_version, twin)
    audited = len(audit_events(world, world.process))

    with pytest.raises(ValidationFailed) as error:
        world.choose.execute(
            world.admin, world.process.id, world.official_version.id, None, "Voltar"
        )

    assert error.value.field == "version_id"
    assert error.value.code == "VERSAO_SUBSTITUIDA"
    assert error.value.message == "Esta versão da tabela foi substituída; use a versão atual"
    assert stored_version_id(world, world.process) == twin.id
    assert len(audit_events(world, world.process)) == audited


# --- GTAB-05..GTAB-08: the version in use of the unit comes before the vigência rule -----------


def mark_in_use(world, unit, version):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_unit_default(unit.id, version.id)
        uow.commit()


def add_fasi_table(world, name, valid_from, valid_to=None, unit_ids=None):
    """A synthetic table with a version copied from the official one (its own table)."""
    table = ScoringTableRecord(
        uuid.uuid4(), name, unit_ids=tuple(unit_ids if unit_ids is not None else [world.fasi.id])
    )
    version = replace(
        world.official_version,
        id=uuid.uuid4(),
        table_id=table.id,
        name=f"{name} v1",
        valid_from=valid_from,
        valid_to=valid_to,
        superseded_by_id=None,
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.scoring_tables.add_version(version)
        uow.commit()
    return table, version


def test_the_version_in_use_is_suggested_even_when_a_newer_valid_version_exists(world):
    _, newer = add_fasi_table(world, "Tabela Sintética Mais Nova", date(2024, 1, 1))
    mark_in_use(world, world.fasi, world.official_version)

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.suggested.version.id == world.official_version.id
    assert result.suggested.version.id != newer.id
    assert result.suggested.table_name == "Tabela de Pontuação da UFPA"
    assert result.alerts == []


def test_the_suggestion_is_not_applied_and_writes_no_audit_event(world):
    mark_in_use(world, world.fasi, world.official_version)

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.chosen is None
    assert stored_version_id(world, world.process) is None
    assert audit_events(world, world.process) == []


def test_a_version_in_use_outside_its_validity_is_suggested_and_alerts_when_confirmed(world):
    _, expired = add_fasi_table(
        world, "Tabela Sintética Encerrada", date(2015, 1, 1), date(2020, 12, 31)
    )
    mark_in_use(world, world.fasi, expired)  # the interstice ends on 2024-11-23

    suggested = world.suggest.execute(world.admin, world.process.id)
    confirmed = world.choose.execute(world.admin, world.process.id, expired.id, None, None)

    assert suggested.suggested.version.id == expired.id
    assert suggested.alerts == []
    assert ScoringAlertCode.TABELA_FORA_DE_VIGENCIA in codes(confirmed)


def test_a_unit_without_a_mark_keeps_the_vigencia_suggestion_when_another_unit_has_one(world):
    mark_in_use(world, world.ifch, world.other_version)

    result = world.suggest.execute(world.admin, world.process.id)  # the FASI professor

    assert result.suggested.version.id == world.official_version.id


@pytest.mark.parametrize("case", ["superseded", "archived", "unit_removed"])
def test_a_mark_that_fails_a_guard_falls_back_to_the_vigencia_suggestion(world, case):
    table, marked = add_fasi_table(world, "Tabela Sintética Marcada", date(2015, 1, 1))
    mark_in_use(world, world.fasi, marked)
    with world.uow_factory() as uow:
        if case == "superseded":
            uow.scoring_tables.set_superseded(marked.id, world.official_version.id)
        elif case == "archived":
            uow.scoring_tables.set_table_archived(table.id, True)
        else:
            uow.scoring_tables.set_table_units(table.id, [world.ifch.id])
        uow.commit()
    # the marked table is the newest by vigência; without the guard it would win either way
    with world.uow_factory() as uow:
        uow.scoring_tables.update_version(
            replace(uow.scoring_tables.get_version(marked.id), valid_from=date(2024, 6, 1))
        )
        uow.commit()

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.suggested.version.id == world.official_version.id


def test_a_mark_that_fails_a_guard_with_no_valid_version_keeps_tabela_nao_encontrada(
    world, add_process
):
    old = add_process(start_date=date(2010, 1, 1), end_date=date(2012, 1, 1))
    table, marked = add_fasi_table(world, "Tabela Sintética Arquivada", date(2005, 1, 1))
    mark_in_use(world, world.fasi, marked)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_archived(table.id, True)
        uow.commit()

    result = world.suggest.execute(world.admin, old.id)

    assert result.suggested is None
    assert codes(result) == {
        ScoringAlertCode.TABELA_NAO_ENCONTRADA: Severity.REQUER_ANALISE_NORMATIVA
    }


def test_the_vigencia_suggestion_ignores_an_archived_table(world):
    table, newer = add_fasi_table(world, "Tabela Sintética Arquivada", date(2024, 1, 1))
    assert (
        world.suggest.execute(world.admin, world.process.id).suggested.version.id == newer.id
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_archived(table.id, True)
        uow.commit()

    result = world.suggest.execute(world.admin, world.process.id)

    assert result.suggested.version.id == world.official_version.id


def test_a_process_with_a_chosen_table_keeps_it_when_the_mark_changes(world):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    events = len(audit_events(world, world.process))
    _, other = add_fasi_table(world, "Tabela Sintética Nova Marca", date(2024, 1, 1))

    mark_in_use(world, world.fasi, other)
    result = world.suggest.execute(world.admin, world.process.id)

    assert result.chosen.version.id == world.official_version.id
    assert result.suggested.version.id == other.id
    assert stored_version_id(world, world.process) == world.official_version.id
    assert len(audit_events(world, world.process)) == events


def test_a_new_version_over_the_marked_one_keeps_the_mark_and_the_closed_version_is_suggested(
    world, admin_uc
):
    mark_in_use(world, world.fasi, world.official_version)
    new = admin_uc.create_version.execute(
        world.admin,
        world.official_version.table_id,
        world.official_version.id,
        date(2023, 6, 1),
        None,
        "Nova norma da FASI, 2023",
    )

    suggested = world.suggest.execute(world.admin, world.process.id).suggested
    confirmed = world.choose.execute(
        world.admin, world.process.id, world.official_version.id, None, None
    )

    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_unit_default(world.fasi.id).version_id == (
            world.official_version.id
        )
    assert suggested.version.id == world.official_version.id
    assert suggested.version.id != new.version.id
    assert ScoringAlertCode.TABELA_FORA_DE_VIGENCIA in codes(confirmed)


# --- GTAB-24, GTAB-44: an archived table is not chosen again; a vanished version is a 404 ------


def archive_table(world, version):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_table_archived(version.table_id, True)
        uow.commit()


def test_choosing_a_version_of_an_archived_table_is_409_and_saves_nothing(world):
    archive_table(world, world.official_version)
    audited = len(audit_events(world, world.process))

    with pytest.raises(Conflict) as refused:
        world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    assert refused.value.code == "TABELA_ARQUIVADA"
    assert stored_version_id(world, world.process) is None
    assert len(audit_events(world, world.process)) == audited


def test_resending_the_version_the_process_already_has_is_accepted_even_if_archived(world):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    archive_table(world, world.official_version)

    result = world.choose.execute(
        world.admin, world.process.id, world.official_version.id, None, None
    )

    assert result.chosen.version.id == world.official_version.id
    assert stored_version_id(world, world.process) == world.official_version.id


def test_a_process_with_another_version_cannot_switch_to_an_archived_table(world):
    world.choose.execute(world.admin, world.process.id, world.other_version.id, None, None)
    archive_table(world, world.official_version)

    with pytest.raises(Conflict) as refused:
        world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    assert refused.value.code == "TABELA_ARQUIVADA"
    assert stored_version_id(world, world.process) == world.other_version.id


def test_the_score_of_a_process_that_uses_an_archived_table_still_calculates(world):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    archive_table(world, world.official_version)

    score = world.calc.execute(world.admin, world.process.id)

    assert score.chosen.version.id == world.official_version.id
    assert score.result.total == 0  # no activity yet: the calculation ran without an error


def test_choosing_a_version_deleted_while_the_choice_waits_for_its_lock_is_404(world, engine):
    _, doomed = add_fasi_table(world, "Tabela Sintética Excluída", date(2024, 1, 1))
    gate = Gate()

    def deleting():
        with world.uow_factory() as uow:
            uow.scoring_tables.lock_version(doomed.id)
            uow.scoring_tables.delete_version(doomed.id)
            gate.hold()
            uow.commit()

    deletion = Worker(deleting).start()
    gate.wait_reached()  # the version is deleted and locked, not committed
    choice = Worker(
        lambda: world.choose.execute(world.admin, world.process.id, doomed.id, None, None)
    ).start()
    wait_until_blocked(engine)

    gate.release()
    deletion.join()
    choice.join()

    assert deletion.error is None
    assert isinstance(choice.error, NotFound)
    assert stored_version_id(world, world.process) is None
