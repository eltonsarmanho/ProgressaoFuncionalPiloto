"""ADM-01, ADM-02, ADM-11: create and duplicate scoring tables."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.entities.scoring import TableStatus
from app.domain.errors import Forbidden, NotFound, ValidationFailed

REFERENCE = "Res. 9.999/2026-CONSEPE"


def create(world, admin_uc, actor=None, **kw):
    args = {
        "name": "Tabela Nova",
        "unit_ids": [world.ifch.id],
        "valid_from": date(2026, 1, 1),
        "valid_to": None,
        "norm_reference": REFERENCE,
    }
    args.update(kw)
    return admin_uc.create_table.execute(actor or world.admin, **args)


def stored(world, table_id):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_table(table_id), list(
            uow.scoring_tables.list_versions(table_id)
        )


def events(world, entity, entity_id):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for(entity, str(entity_id)))


def test_creates_table_with_unique_name_units_and_first_version(world, admin_uc):
    view = create(world, admin_uc, version_name="Versão 2026")

    table, versions = stored(world, view.table.id)
    assert table.name == "Tabela Nova"
    assert table.unit_ids == (world.ifch.id,)
    [version] = versions
    assert version.name == "Versão 2026"
    assert version.valid_from == date(2026, 1, 1)
    assert version.valid_to is None
    assert version.norm_reference == REFERENCE
    assert version.status is TableStatus.PENDENTE_VALIDACAO
    assert [g.number for g in version.groups] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(g.criteria == () for g in version.groups)


def test_first_version_can_copy_groups_and_criteria_from_a_base_version(world, admin_uc):
    view = create(world, admin_uc, base_version_id=world.official_version.id)

    [version] = stored(world, view.table.id)[1]
    assert [len(g.criteria) for g in version.groups] == [2, 16, 9, 6, 5, 14, 11, 37]
    assert version.get_criterion(2, 7) == world.official_version.get_criterion(2, 7)
    assert version.minimums == world.official_version.minimums


def test_creation_is_audited_for_table_and_version_with_the_norm_reference(world, admin_uc):
    view = create(world, admin_uc)

    [table_event] = events(world, "scoring_table", view.table.id)
    assert table_event.action is AuditAction.CREATE
    assert table_event.user_id == world.admin.id
    assert table_event.changes["name"] == {"before": None, "after": "Tabela Nova"}
    assert table_event.changes["unit_ids"]["after"] == [str(world.ifch.id)]
    [version_event] = events(world, "scoring_version", view.versions[0].version.id)
    assert version_event.action is AuditAction.CREATE
    assert version_event.justification == REFERENCE
    assert version_event.changes["valid_from"] == {"before": None, "after": "2026-01-01"}
    assert version_event.changes["status"]["after"] == "PENDENTE_VALIDACAO"


@pytest.mark.parametrize("name", ["Tabela de Pontuação da UFPA", "  tabela de pontuação da ufpa "])
def test_repeated_name_is_422_on_name_and_nothing_is_created(world, admin_uc, name):
    with pytest.raises(ValidationFailed) as error:
        create(world, admin_uc, name=name)

    assert error.value.field == "name"
    with world.uow_factory() as uow:
        assert len(uow.scoring_tables.list_tables()) == 2


def test_empty_name_is_422_on_name(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        create(world, admin_uc, name="   ")

    assert error.value.field == "name"


def test_missing_norm_reference_is_422_on_norm_reference(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        create(world, admin_uc, norm_reference=" ")

    assert error.value.field == "norm_reference"


def test_end_before_start_is_422_on_valid_to(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        create(world, admin_uc, valid_to=date(2025, 12, 31))

    assert error.value.field == "valid_to"


def test_unknown_unit_is_422_on_unit_ids(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        create(world, admin_uc, unit_ids=[uuid.uuid4()])

    assert error.value.field == "unit_ids"


@pytest.mark.parametrize("actor", ["docente", "secretaria"])
def test_non_admin_gets_403_on_create_and_duplicate(world, admin_uc, actor):
    user = getattr(world, actor)

    with pytest.raises(Forbidden):
        create(world, admin_uc, actor=user)
    with pytest.raises(Forbidden):
        admin_uc.duplicate.execute(user, world.official_version.table_id, "Cópia")
    with world.uow_factory() as uow:
        assert len(uow.scoring_tables.list_tables()) == 2


def test_duplicate_copies_latest_version_into_an_independent_table(world, admin_uc):
    view = admin_uc.duplicate.execute(world.admin, world.official_version.table_id, "Cópia da FASI")

    table, versions = stored(world, view.table.id)
    assert table.name == "Cópia da FASI"
    [copy_version] = versions
    assert copy_version.id != world.official_version.id
    assert copy_version.table_id == table.id
    assert copy_version.valid_from == world.official_version.valid_from
    assert copy_version.norm_reference == world.official_version.norm_reference
    assert copy_version.status is TableStatus.OFICIAL
    assert copy_version.minimums == world.official_version.minimums
    assert [len(g.criteria) for g in copy_version.groups] == [2, 16, 9, 6, 5, 14, 11, 37]
    assert copy_version.groups == world.official_version.groups  # same content, new rows


def test_duplicate_does_not_copy_unit_association_unless_given(world, admin_uc):
    view = admin_uc.duplicate.execute(world.admin, world.official_version.table_id, "Sem unidade")
    other = admin_uc.duplicate.execute(
        world.admin, world.official_version.table_id, "Com unidade", unit_ids=[world.ifch.id]
    )

    assert stored(world, view.table.id)[0].unit_ids == ()
    assert stored(world, other.table.id)[0].unit_ids == (world.ifch.id,)


def test_source_and_duplicate_stay_independent(world, admin_uc):
    view = admin_uc.duplicate.execute(world.admin, world.official_version.table_id, "Cópia da FASI")
    copy_version = view.versions[0].version

    with world.uow_factory() as uow:
        criterion = copy_version.get_criterion(2, 7)
        uow.scoring_tables.update_criterion(
            copy_version.id, replace(criterion, unit_points=Decimal("99"))
        )
        uow.commit()

    original = stored(world, world.official_version.table_id)[1][0]
    expected = world.official_version.get_criterion(2, 7).unit_points
    assert original.get_criterion(2, 7).unit_points == expected
    assert expected != Decimal("99")


def test_duplicate_is_audited_with_source_reference(world, admin_uc):
    view = admin_uc.duplicate.execute(world.admin, world.official_version.table_id, "Cópia da FASI")

    [event] = events(world, "scoring_table", view.table.id)
    assert event.action is AuditAction.CREATE
    assert event.changes["name"]["after"] == "Cópia da FASI"
    assert event.changes["duplicated_from"]["after"] == str(world.official_version.table_id)
    [version_event] = events(world, "scoring_version", view.versions[0].version.id)
    copied = version_event.changes["copied_from_version_id"]["after"]
    assert copied == str(world.official_version.id)


def test_duplicate_name_clash_is_422_and_unknown_source_is_404(world, admin_uc):
    with pytest.raises(ValidationFailed) as error:
        admin_uc.duplicate.execute(
            world.admin, world.official_version.table_id, "Tabela de Pontuação da UFPA"
        )
    assert error.value.field == "name"
    with pytest.raises(NotFound):
        admin_uc.duplicate.execute(world.admin, uuid.uuid4(), "Qualquer")


# ADM-02: with several versions, the copy takes the LATEST one (by start of validity)
def test_duplicate_of_a_table_with_two_versions_copies_the_latest(world, admin_uc):
    newer = admin_uc.create_version.execute(
        world.admin,
        world.official_version.table_id,
        world.official_version.id,
        date(2023, 6, 1),
        None,
        "Nova norma da FASI, 2023",
    )

    view = admin_uc.duplicate.execute(
        world.admin, world.official_version.table_id, "Cópia da última"
    )

    _, versions = stored(world, view.table.id)
    [copy_version] = versions
    assert copy_version.valid_from == date(2023, 6, 1)
    assert copy_version.norm_reference == "Nova norma da FASI, 2023"
    assert copy_version.id != newer.version.id
