"""ADM-05, ADM-06, ADM-07: new versions copy a source, close the open one, reject overlaps."""

import uuid
from dataclasses import replace
from datetime import date

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.scoring import TableStatus
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed

REFERENCE = "Res. 5.000/2026"
NEW_START = date(2026, 3, 1)


def versions(world, table_id):
    with world.uow_factory() as uow:
        return list(uow.scoring_tables.list_versions(table_id))


def new_version(world, admin_uc, valid_from=NEW_START, valid_to=None, **kw):
    return admin_uc.create_version.execute(
        kw.pop("actor", world.admin),
        world.official_version.table_id,
        kw.pop("source_id", world.official_version.id),
        valid_from,
        valid_to,
        kw.pop("norm_reference", REFERENCE),
        **kw,
    )


def test_copies_groups_criteria_and_minimums_from_the_source(world, admin_uc):
    view = new_version(world, admin_uc, version_name="2026")

    created = next(v for v in versions(world, world.official_version.table_id) if v.name == "2026")
    assert created.id == view.version.id
    assert created.valid_from == NEW_START
    assert created.valid_to is None
    assert created.norm_reference == REFERENCE
    assert created.status is TableStatus.PENDENTE_VALIDACAO
    assert [len(g.criteria) for g in created.groups] == [2, 16, 9, 6, 5, 14, 11, 37]
    assert created.groups == world.official_version.groups
    assert created.minimums == world.official_version.minimums


def test_open_version_ends_the_day_before_the_new_start_and_is_audited(world, admin_uc):
    new_version(world, admin_uc)

    old, _ = versions(world, world.official_version.table_id)
    assert old.id == world.official_version.id
    assert old.valid_to == date(2026, 2, 28)
    with world.uow_factory() as uow:
        [event] = [
            e
            for e in uow.audit.list_for("scoring_version", str(old.id))
            if e.action is AuditAction.UPDATE
        ]
    assert event.changes == {"valid_to": {"before": None, "after": "2026-02-28"}}
    assert event.user_id == world.admin.id


def test_creation_audit_has_norm_reference_and_source(world, admin_uc):
    view = new_version(world, admin_uc)

    with world.uow_factory() as uow:
        [event] = uow.audit.list_for("scoring_version", str(view.version.id))
    assert event.action is AuditAction.CREATE
    assert event.justification == REFERENCE
    assert event.changes["valid_from"] == {"before": None, "after": "2026-03-01"}
    assert event.changes["copied_from_version_id"]["after"] == str(world.official_version.id)


def test_process_of_the_open_version_ending_after_new_start_is_409_and_nothing_changes(
    world, admin_uc
):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    with pytest.raises(Conflict):
        new_version(world, admin_uc, valid_from=date(2024, 11, 23))  # process ends 2024-11-23

    [only] = versions(world, world.official_version.table_id)
    assert only.valid_to is None
    with world.uow_factory() as uow:
        events = uow.audit.list_for("scoring_version", str(world.official_version.id))
    assert [e.action for e in events] == []


def test_process_of_the_open_version_ending_before_new_start_does_not_block(world, admin_uc):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    new_version(world, admin_uc, valid_from=date(2024, 11, 24))

    old, new = versions(world, world.official_version.table_id)
    assert old.valid_to == date(2024, 11, 23)
    assert new.valid_from == date(2024, 11, 24)


def test_overlap_with_a_closed_version_is_409(world, admin_uc):
    new_version(world, admin_uc)  # closes the original at 2026-02-28, new one open from 2026-03

    with pytest.raises(Conflict) as error:
        new_version(world, admin_uc, valid_from=date(2024, 1, 1), valid_to=date(2024, 12, 31))

    assert "sobrepõe" in str(error.value)
    assert len(versions(world, world.official_version.table_id)) == 2


def test_new_start_before_the_open_versions_start_is_409_overlap(world, admin_uc):
    with pytest.raises(Conflict):
        new_version(world, admin_uc, valid_from=date(2010, 1, 1))

    [only] = versions(world, world.official_version.table_id)
    assert only.valid_to is None


def test_start_and_norm_reference_are_required_422(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        new_version(world, admin_uc, norm_reference="  ")
    assert error.value.field == "norm_reference"
    with pytest.raises(ValidationFailed) as error:
        new_version(world, admin_uc, valid_to=date(2026, 2, 1))
    assert error.value.field == "valid_to"


def test_unknown_table_or_source_is_404(world, admin_uc):
    with pytest.raises(NotFound):
        new_version(world, admin_uc, source_id=uuid.uuid4())
    with pytest.raises(NotFound):
        admin_uc.create_version.execute(
            world.admin, uuid.uuid4(), world.official_version.id, NEW_START, None, REFERENCE
        )


@pytest.mark.parametrize("actor", ["docente", "secretaria"])
def test_non_admin_gets_403(world, admin_uc, actor):
    with pytest.raises(Forbidden):
        new_version(world, admin_uc, actor=getattr(world, actor))

    assert len(versions(world, world.official_version.table_id)) == 1


# --- GI-07: a superseded version leaves the open-version, overlap and base rules ---------------


def add_superseded_twin(world):
    """The official version marked as superseded by a twin that starts the same day, open too."""
    twin = replace(world.official_version, id=uuid.uuid4(), name="Versão sintética que a substitui")
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(twin)
        uow.scoring_tables.set_superseded(world.official_version.id, twin.id)
        uow.commit()
    return twin


def test_a_new_version_closes_the_superseding_one_and_neither_conflicts_nor_touches_the_old(
    world, admin_uc
):
    twin = add_superseded_twin(world)

    created = new_version(world, admin_uc)

    by_id = {v.id: v for v in versions(world, world.official_version.table_id)}
    assert created.version.id in by_id
    assert by_id[twin.id].valid_to == date(2026, 2, 28)
    assert by_id[world.official_version.id].valid_to is None  # the superseded one is left alone
    assert by_id[world.official_version.id].superseded_by_id == twin.id
    with world.uow_factory() as uow:
        assert [
            e.action for e in uow.audit.list_for("scoring_version", str(world.official_version.id))
        ] == []


def test_without_the_mark_two_open_versions_still_conflict(world, admin_uc):
    twin = replace(world.official_version, id=uuid.uuid4(), name="Gêmea sem marca")
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(twin)
        uow.commit()

    with pytest.raises(Conflict):
        new_version(world, admin_uc)


def test_latest_version_skips_the_superseded_one_with_the_same_start(world):
    from app.application.use_cases.scoring_admin import latest_version

    twin = add_superseded_twin(world)

    both = versions(world, world.official_version.table_id)
    assert latest_version(both).id == twin.id
    assert latest_version(list(reversed(both))).id == twin.id


def test_the_csv_import_takes_its_base_from_the_version_that_is_not_superseded(world, admin_uc):
    twin = add_superseded_twin(world)
    note = "Nota sintética da versão que substitui"
    with world.uow_factory() as uow:
        uow.scoring_tables.update_version(replace(twin, notes=note))
        uow.commit()
    assert world.official_version.notes != note
    csv = "\n".join(
        [
            "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite",
            "1,1,Aulas,horas,CARGA_SEMANAL,,,",
            "2,7,Orientação,por aluno,POR_UNIDADE,5,,",
        ]
    )

    view = admin_uc.import_csv.execute(
        world.admin, world.official_version.table_id, NEW_START, None, REFERENCE, csv
    )

    assert view.version.notes == note


# --- GTAB-45: the norm code stays in the same table and does not travel to another one ----------


def test_a_new_version_in_the_same_table_keeps_the_norm_code(world, admin_uc):
    view = new_version(world, admin_uc)

    assert world.official_version.norm_code == "TABELA-OFICIAL-UFPA"
    assert stored_version(world, view.version.id).norm_code == "TABELA-OFICIAL-UFPA"


def test_a_new_version_in_another_table_from_an_official_version_has_no_norm_code(
    world, admin_uc
):
    table = admin_uc.create_table.execute(
        world.admin, "Tabela Sintética Destino", [], date(2026, 1, 1), None, REFERENCE
    )

    view = admin_uc.create_version.execute(
        world.admin,
        table.table.id,
        world.official_version.id,
        date(2027, 1, 1),
        None,
        REFERENCE,
    )

    assert stored_version(world, view.version.id).norm_code is None
    assert stored_version(world, view.version.id).table_id == table.table.id
    assert stored_version(world, world.official_version.id).norm_code == "TABELA-OFICIAL-UFPA"


def stored_version(world, version_id):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_version(version_id)
