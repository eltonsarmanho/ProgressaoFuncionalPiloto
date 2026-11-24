"""ADM-03, ADM-04, SEL-08: criteria edits with the norm reference and the in-use guard."""

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed

REFERENCE = "Res. 5.000/2026, art. 3"


@pytest.fixture
def unused(world, admin_uc):
    """A copy of the official table: its version is used by no process."""
    view = admin_uc.duplicate.execute(world.admin, world.official_version.table_id, "Cópia FASI")
    return view.versions[0].version


def criterion(world, version_id, group, item):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_version(version_id).get_criterion(group, item)


def events(world, version_id):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("scoring_version", str(version_id)))


def test_changes_criterion_of_an_unused_version_and_audits_before_and_after(
    world, admin_uc, unused
):
    before = criterion(world, unused.id, 2, 7)
    assert before.unit_points == Decimal("5")

    admin_uc.update_criteria.execute(
        world.admin, unused.id, 2, 7, {"unit_points": "12.5", "description": "Nova"}, REFERENCE
    )

    after = criterion(world, unused.id, 2, 7)
    assert after.unit_points == Decimal("12.5")
    assert after.description == "Nova"
    [event] = [e for e in events(world, unused.id) if e.action is AuditAction.UPDATE]
    assert event.user_id == world.admin.id
    assert event.justification == REFERENCE
    assert event.changes == {
        "criteria.2.7.unit_points": {"before": "5", "after": "12.5"},
        "criteria.2.7.description": {"before": before.description, "after": "Nova"},
    }


def test_other_criteria_are_untouched(world, admin_uc, unused):
    other = criterion(world, unused.id, 2, 8)

    admin_uc.update_criteria.execute(
        world.admin, unused.id, 2, 7, {"unit_points": "12.5"}, REFERENCE
    )

    assert criterion(world, unused.id, 2, 8) == other


def test_version_chosen_by_a_process_is_409_asking_for_a_new_version(world, admin_uc):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    with pytest.raises(Conflict) as error:
        admin_uc.update_criteria.execute(
            world.admin, world.official_version.id, 2, 7, {"unit_points": "99"}, REFERENCE
        )

    assert "nova versão" in str(error.value)
    assert criterion(world, world.official_version.id, 2, 7).unit_points == Decimal("5")
    history = events(world, world.official_version.id)
    updates = [e for e in history if e.action is AuditAction.UPDATE]
    assert updates == []


@pytest.mark.parametrize("reference", ["", "   "])
def test_missing_change_reference_is_422_on_change_reference(world, admin_uc, unused, reference):
    with pytest.raises(ValidationFailed) as error:
        admin_uc.update_criteria.execute(
            world.admin, unused.id, 2, 7, {"unit_points": "12"}, reference
        )

    assert error.value.field == "change_reference"
    assert criterion(world, unused.id, 2, 7).unit_points == Decimal("5")


@pytest.mark.parametrize("actor", ["docente", "secretaria"])
def test_non_admin_gets_403(world, admin_uc, unused, actor):
    with pytest.raises(Forbidden):
        admin_uc.update_criteria.execute(
            getattr(world, actor), unused.id, 2, 7, {"unit_points": "12"}, REFERENCE
        )

    assert criterion(world, unused.id, 2, 7).unit_points == Decimal("5")


def test_unknown_version_or_criterion_is_404(world, admin_uc, unused):
    with pytest.raises(NotFound):
        admin_uc.update_criteria.execute(
            world.admin, uuid.uuid4(), 2, 7, {"unit_points": "1"}, REFERENCE
        )
    with pytest.raises(NotFound):
        admin_uc.update_criteria.execute(
            world.admin, unused.id, 2, 999, {"unit_points": "1"}, REFERENCE
        )


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"unit_points": "-1"}, "unit_points"),
        ({"unit_points": "abc"}, "unit_points"),
        ({"mode": "OUTRO"}, "mode"),
        ({"description": " "}, "description"),
        ({"group_number": 3}, "changes"),
        ({}, "changes"),
    ],
)
def test_invalid_changes_are_422_on_the_field(world, admin_uc, unused, changes, field):
    with pytest.raises(ValidationFailed) as error:
        admin_uc.update_criteria.execute(world.admin, unused.id, 2, 7, changes, REFERENCE)

    assert error.value.field == field


def test_superseded_version_is_read_only_even_when_no_process_uses_it(world, admin_uc, unused):
    admin_uc.create_version.execute(
        world.admin, unused.table_id, unused.id, date(2027, 1, 1), None, REFERENCE
    )

    with pytest.raises(Conflict) as error:
        admin_uc.update_criteria.execute(
            world.admin, unused.id, 2, 7, {"unit_points": "12"}, REFERENCE
        )

    assert "somente leitura" in str(error.value)
    assert criterion(world, unused.id, 2, 7).unit_points == Decimal("5")


@pytest.fixture
def superseded_pair(world, unused):
    """GI-07: the unused version superseded by a synthetic twin that starts the same day."""
    twin = replace(unused, id=uuid.uuid4(), name="Versão sintética que a substitui")
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(twin)
        uow.scoring_tables.set_superseded(unused.id, twin.id)
        uow.commit()
    return unused, twin


def test_version_marked_as_superseded_is_read_only_when_no_process_uses_it(
    world, admin_uc, superseded_pair
):
    old, _ = superseded_pair

    with pytest.raises(Conflict) as error:
        admin_uc.update_criteria.execute(
            world.admin, old.id, 2, 7, {"unit_points": "12"}, REFERENCE
        )

    assert "substituída" in str(error.value)
    assert criterion(world, old.id, 2, 7).unit_points == Decimal("5")
    assert [e for e in events(world, old.id) if e.action is AuditAction.UPDATE] == []


def test_the_version_that_supersedes_it_still_accepts_the_criterion_edit(
    world, admin_uc, superseded_pair
):
    _, twin = superseded_pair

    admin_uc.update_criteria.execute(
        world.admin, twin.id, 2, 7, {"unit_points": "12"}, REFERENCE
    )

    assert criterion(world, twin.id, 2, 7).unit_points == Decimal("12")


def _refusal(world, admin_uc, version_id):
    with pytest.raises(Conflict) as error:
        admin_uc.update_criteria.execute(
            world.admin, version_id, 2, 7, {"unit_points": "99"}, REFERENCE
        )
    return error.value


def test_a_version_used_by_a_process_is_refused_with_its_code_and_text(world, admin_uc):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    refusal = _refusal(world, admin_uc, world.official_version.id)

    assert refusal.code == "VERSAO_USADA_POR_PROCESSO"
    assert str(refusal) == (
        "Versão já usada por processos não pode ser alterada; "
        "crie uma nova versão para alterar os critérios"
    )


def test_a_version_that_is_not_the_latest_is_refused_with_its_code_and_text(
    world, admin_uc, unused
):
    admin_uc.create_version.execute(
        world.admin, unused.table_id, unused.id, date(2027, 1, 1), None, REFERENCE
    )
    with world.uow_factory() as uow:
        # Not superseded: the closing by the new version is what makes it a previous one.
        assert uow.scoring_tables.get_version(unused.id).superseded_by_id is None

    refusal = _refusal(world, admin_uc, unused.id)

    assert refusal.code == "VERSAO_NAO_MAIS_RECENTE"
    assert str(refusal) == (
        "Versão anterior é somente leitura; altere a versão mais recente "
        "ou crie uma nova versão"
    )


def test_a_superseded_version_is_refused_with_its_code_and_text(
    world, admin_uc, superseded_pair
):
    old, _ = superseded_pair

    refusal = _refusal(world, admin_uc, old.id)

    assert refusal.code == "VERSAO_SUBSTITUIDA"
    assert str(refusal) == "Versão substituída é somente leitura; altere a versão que a substitui"


def test_the_refusals_come_in_the_order_superseded_then_not_latest_then_used(
    world, admin_uc, superseded_pair
):
    old, twin = superseded_pair
    # Both have a later version now; only the old one is superseded: that rule comes first.
    admin_uc.create_version.execute(
        world.admin, twin.table_id, twin.id, date(2027, 1, 1), None, REFERENCE
    )
    assert _refusal(world, admin_uc, old.id).code == "VERSAO_SUBSTITUIDA"
    assert _refusal(world, admin_uc, twin.id).code == "VERSAO_NAO_MAIS_RECENTE"


def test_a_used_version_that_is_also_not_the_latest_says_not_latest_first(world, admin_uc):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)
    admin_uc.create_version.execute(
        world.admin,
        world.official_version.table_id,
        world.official_version.id,
        date(2099, 1, 1),
        None,
        REFERENCE,
    )
    with world.uow_factory() as uow:
        assert uow.scoring_tables.version_in_use(world.official_version.id) is True

    assert _refusal(world, admin_uc, world.official_version.id).code == "VERSAO_NAO_MAIS_RECENTE"


def test_the_latest_unused_version_keeps_accepting_the_edit_with_the_same_audit_keys(
    world, admin_uc, unused
):
    admin_uc.update_criteria.execute(
        world.admin, unused.id, 2, 7, {"unit_points": "12.5"}, REFERENCE
    )

    [event] = [e for e in events(world, unused.id) if e.action is AuditAction.UPDATE]
    assert list(event.changes) == ["criteria.2.7.unit_points"]
