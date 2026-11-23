"""GTAB-26, GTAB-27, GTAB-30, GTAB-31, GTAB-32, GTAB-42: delete a version of a table, with a
preview. Tables here are synthetic; the official one is the table named OFFICIAL_TABLE."""

import uuid
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.application.services.audit_service import AuditService
from app.application.use_cases import scoring_admin
from app.application.use_cases.scoring_admin import (
    DeleteScoringVersion,
    PreviewDeleteVersion,
    ProtectedCatalog,
)
from app.application.use_cases.scoring_defaults import SetUnitDefaultVersion
from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from tests.integration.documents.generated_support import make_file, make_generation
from tests.integration.scoring.conftest import OFFICIAL_TABLE
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked

REFERENCE = "Res. 7.000/2026-CONSEPE"


@pytest.fixture
def uc(world):
    catalog = ProtectedCatalog(OFFICIAL_TABLE)
    return SimpleNamespace(
        delete=DeleteScoringVersion(world.uow_factory, world.audit, catalog),
        preview=PreviewDeleteVersion(world.uow_factory, catalog),
        create_table=scoring_admin.CreateScoringTable(world.uow_factory, world.audit),
        create_version=scoring_admin.CreateVersionFrom(world.uow_factory, world.audit),
        mark=SetUnitDefaultVersion(world.uow_factory, world.audit),
    )


def make_table(world, uc, name="Tabela Sintética A", unit_ids=()):
    """A synthetic table with the official criteria, through the use cases (so it is audited)."""
    return uc.create_table.execute(
        world.admin,
        name,
        list(unit_ids),
        date(2020, 1, 1),
        None,
        REFERENCE,
        base_version_id=world.official_version.id,
    )


def add_version(world, uc, table, valid_from, valid_to=None):
    source = table.versions[0].version
    return uc.create_version.execute(
        world.admin, table.table.id, source.id, valid_from, valid_to, REFERENCE
    ).version


def stored(world, version_id):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_version(version_id)


def events(world, version):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("scoring_version", str(version.id)))


def groups_and_criteria(engine, version_id) -> tuple[int, int]:
    with engine.connect() as conn:
        groups = conn.exec_driver_sql(
            "SELECT count(*) FROM scoring_groups WHERE version_id = %(v)s", {"v": version_id}
        ).scalar_one()
        criteria = conn.exec_driver_sql(
            "SELECT count(*) FROM scoring_criteria c JOIN scoring_groups g ON g.id = c.group_id "
            "WHERE g.version_id = %(v)s",
            {"v": version_id},
        ).scalar_one()
    return groups, criteria


def two_versions(world, uc, **kw):
    table = make_table(world, uc, **kw)
    first = table.versions[0].version
    second = add_version(world, uc, table, date(2024, 1, 1))
    return table, first, second


def test_deleting_removes_the_version_with_its_groups_and_criteria_and_keeps_the_table(
    world, uc, engine
):
    table, first, second = two_versions(world, uc)
    assert groups_and_criteria(engine, second.id) == (8, 100)

    uc.delete.execute(world.admin, second.id)

    assert stored(world, second.id) is None
    assert stored(world, first.id) is not None
    assert groups_and_criteria(engine, second.id) == (0, 0)
    with world.uow_factory() as uow:
        assert uow.scoring_tables.get_table(table.table.id) is not None


def test_the_delete_event_has_the_user_and_the_data_of_the_version_in_before(world, uc):
    _, first, second = two_versions(world, uc)

    uc.delete.execute(world.admin, second.id)

    deleted = events(world, second)[-1]
    assert deleted.action is AuditAction.DELETE
    assert deleted.user_id == world.admin.id
    assert deleted.entity == "scoring_version"
    assert deleted.entity_id == str(second.id)
    before = {field: change["before"] for field, change in deleted.changes.items()}
    assert before == {
        "name": second.name,
        "table_id": str(second.table_id),
        "valid_from": "2024-01-01",
        "norm_reference": REFERENCE,
        "status": "PENDENTE_VALIDACAO",
        "criteria": 100,
    }
    assert all(change["after"] is None for change in deleted.changes.values())


def test_the_earlier_events_of_the_version_stay_and_the_delete_is_added_to_them(world, uc):
    table, first, second = two_versions(world, uc)
    uc.delete.execute(world.admin, second.id)

    created, deleted = events(world, second)

    assert created.action is AuditAction.CREATE
    assert deleted.action is AuditAction.DELETE
    assert [e.action for e in events(world, first)][0] is AuditAction.CREATE


def test_deleting_the_latest_version_gives_the_previous_one_its_end_of_validity_back(world, uc):
    _, first, second = two_versions(world, uc)
    assert stored(world, first.id).valid_to == date(2023, 12, 31)  # closed by the newer version

    uc.delete.execute(world.admin, second.id)

    assert stored(world, first.id).valid_to is None  # the deleted one was open-ended
    reopened = events(world, first)[-1]
    assert reopened.action is AuditAction.UPDATE
    assert reopened.user_id == world.admin.id
    assert reopened.changes == {"valid_to": {"before": "2023-12-31", "after": None}}


def test_the_previous_version_takes_the_end_of_validity_of_the_deleted_one(world, uc):
    table = make_table(world, uc)
    first = table.versions[0].version
    second = add_version(world, uc, table, date(2024, 1, 1), date(2027, 12, 31))

    uc.delete.execute(world.admin, second.id)

    assert stored(world, first.id).valid_to == date(2027, 12, 31)
    assert events(world, first)[-1].changes == {
        "valid_to": {"before": "2023-12-31", "after": "2027-12-31"}
    }


def test_deleting_a_latest_version_that_did_not_close_the_previous_one_changes_nothing_else(
    world, uc
):
    table = make_table(world, uc)
    first = table.versions[0].version
    with world.uow_factory() as uow:
        uow.scoring_tables.update_version(replace(first, valid_to=date(2021, 12, 31)))
        uow.commit()
    second = add_version(world, uc, table, date(2024, 1, 1))
    with world.uow_factory() as uow:  # the gap between them: the second did not close the first
        assert uow.scoring_tables.get_version(first.id).valid_to == date(2021, 12, 31)
    before = events(world, first)

    uc.delete.execute(world.admin, second.id)

    assert stored(world, first.id).valid_to == date(2021, 12, 31)
    assert events(world, first) == before


def test_deleting_an_older_version_leaves_the_newer_one_as_it_was(world, uc):
    table = make_table(world, uc)
    first = table.versions[0].version
    second = add_version(world, uc, table, date(2024, 1, 1))
    third = add_version(world, uc, table, date(2026, 1, 1))
    newer_before = stored(world, third.id)
    middle_before = stored(world, second.id)
    events_before = events(world, third)

    uc.delete.execute(world.admin, first.id)

    assert stored(world, third.id) == newer_before
    assert stored(world, second.id) == middle_before
    assert events(world, third) == events_before


def test_a_version_used_by_a_process_is_409_with_the_count_and_nothing_is_deleted(world, uc):
    _, first, second = two_versions(world, uc)
    world.choose.execute(world.admin, world.process.id, second.id, None, None)

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, second.id)

    assert refused.value.code == "VERSAO_USADA_POR_PROCESSO"
    assert str(refused.value) == "A versão é usada por 1 processo e não pode ser excluída"
    assert stored(world, second.id) is not None
    assert stored(world, first.id).valid_to == date(2023, 12, 31)
    assert events(world, second)[-1].action is AuditAction.CREATE


def test_a_version_in_use_of_a_unit_is_409_with_the_acronyms(world, uc):
    _, first, second = two_versions(world, uc, unit_ids=[world.fasi.id])
    uc.mark.execute(world.admin, world.fasi.id, second.id)

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, second.id)

    assert refused.value.code == "VERSAO_EM_USO_DE_UNIDADE"
    assert "FASI" in str(refused.value)
    assert stored(world, second.id) is not None


def test_a_version_that_replaces_another_is_409(world, uc):
    _, first, second = two_versions(world, uc)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(first.id, second.id)
        uow.commit()

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, second.id)

    assert refused.value.code == "VERSAO_SUBSTITUI_OUTRA"
    assert stored(world, second.id) is not None
    assert stored(world, first.id).superseded_by_id == second.id


def test_the_only_version_of_a_table_is_409_ultima_versao(world, uc):
    table = make_table(world, uc)
    only = table.versions[0].version

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, only.id)

    assert refused.value.code == "ULTIMA_VERSAO_DA_TABELA"
    assert stored(world, only.id) is not None


def test_every_version_of_the_official_table_is_protected_not_only_the_current_one(world, uc):
    newer = replace(
        world.official_version,
        id=uuid.uuid4(),
        name="Versão oficial nova",
        valid_from=date(2030, 1, 1),
        superseded_by_id=None,
    )
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(newer)
        uow.commit()

    for version in (world.official_version, newer):
        with pytest.raises(Conflict) as refused:
            uc.delete.execute(world.admin, version.id)
        assert refused.value.code == "TABELA_OFICIAL_PROTEGIDA"
        assert stored(world, version.id) is not None


def test_the_official_protection_comes_before_the_other_blockers(world, uc):
    world.choose.execute(world.admin, world.process.id, world.official_version.id, None, None)

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, world.official_version.id)

    assert refused.value.code == "TABELA_OFICIAL_PROTEGIDA"


def test_a_non_admin_gets_403_and_an_unknown_version_404(world, uc):
    _, _, second = two_versions(world, uc)
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            uc.delete.execute(actor, second.id)
    with pytest.raises(NotFound):
        uc.delete.execute(world.admin, uuid.uuid4())

    assert stored(world, second.id) is not None


def test_the_preview_gives_the_name_the_criteria_and_no_blocker_for_a_free_version(world, uc):
    _, _, second = two_versions(world, uc)

    preview = uc.preview.execute(second.id)

    assert preview.name == second.name
    assert preview.criteria == 100
    assert preview.blocked == []


def test_the_preview_lists_the_same_blockers_the_deletion_refuses_with(world, uc):
    table, first, second = two_versions(world, uc, unit_ids=[world.fasi.id])
    uc.mark.execute(world.admin, world.fasi.id, second.id)
    world.choose.execute(world.admin, world.process.id, second.id, None, None)

    preview = uc.preview.execute(second.id)

    assert [b.code for b in preview.blocked] == [
        "VERSAO_USADA_POR_PROCESSO",
        "VERSAO_EM_USO_DE_UNIDADE",
    ]
    assert preview.blocked[0].count == 1
    assert preview.blocked[1].acronyms == ("FASI",)
    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, second.id)
    assert refused.value.code == preview.blocked[0].code
    assert str(refused.value) == preview.blocked[0].message


def test_the_preview_of_the_official_table_and_of_the_last_version_name_the_codes(world, uc):
    only = make_table(world, uc).versions[0].version

    assert [b.code for b in uc.preview.execute(world.official_version.id).blocked][0] == (
        "TABELA_OFICIAL_PROTEGIDA"
    )
    assert [b.code for b in uc.preview.execute(only.id).blocked] == ["ULTIMA_VERSAO_DA_TABELA"]


def test_the_preview_of_an_unknown_version_is_404(world, uc):
    with pytest.raises(NotFound):
        uc.preview.execute(uuid.uuid4())


def test_a_process_choosing_the_version_while_the_deletion_waits_for_its_lock_is_refused(
    world, uc, engine
):
    _, _, second = two_versions(world, uc)
    gate = Gate()
    choosing_factory = hooked_factory(engine, ("lock_version",), lambda _name: gate.hold())
    choosing = Worker(lambda: scoring_admin_choose(world, choosing_factory, second.id)).start()
    gate.wait_reached()  # the choice holds the lock of the version, not committed
    deletion = Worker(lambda: uc.delete.execute(world.admin, second.id)).start()
    wait_until_blocked(engine)

    gate.release()
    choosing.join()
    deletion.join()

    assert choosing.error is None
    assert isinstance(deletion.error, Conflict)
    assert deletion.error.code == "VERSAO_USADA_POR_PROCESSO"
    assert stored(world, second.id) is not None


def scoring_admin_choose(world, factory, version_id):
    from app.application.use_cases import scoring

    return scoring.ChooseProcessTable(factory, world.audit, world.policy).execute(
        world.admin, world.process.id, version_id, None, None
    )


def test_a_unit_marking_the_version_while_the_deletion_waits_for_its_lock_is_refused(
    world, uc, engine
):
    _, _, second = two_versions(world, uc, unit_ids=[world.fasi.id])
    gate = Gate()
    marking_factory = hooked_factory(engine, ("set_unit_default",), lambda _name: gate.hold())
    marking = Worker(
        lambda: SetUnitDefaultVersion(marking_factory, world.audit).execute(
            world.admin, world.fasi.id, second.id
        )
    ).start()
    gate.wait_reached()  # the mark is written and holds the locks, not committed
    deletion = Worker(lambda: uc.delete.execute(world.admin, second.id)).start()
    wait_until_blocked(engine)

    gate.release()
    marking.join()
    deletion.join()

    assert marking.error is None
    assert isinstance(deletion.error, Conflict)
    assert deletion.error.code == "VERSAO_EM_USO_DE_UNIDADE"
    assert stored(world, second.id) is not None


def test_a_foreign_key_violation_that_escapes_the_facts_is_409_and_nothing_is_deleted(
    world, engine
):
    class BlindUnitOfWork(SqlUnitOfWork):
        """Hides the processes from the facts, so only the foreign key can refuse."""

        def __enter__(self):
            super().__enter__()
            self.scoring_tables.version_process_counts = lambda: {}
            return self

    uc_make = SimpleNamespace(
        create_table=scoring_admin.CreateScoringTable(world.uow_factory, world.audit),
        create_version=scoring_admin.CreateVersionFrom(world.uow_factory, world.audit),
    )
    _, _, second = two_versions(world, uc_make)
    world.choose.execute(world.admin, world.process.id, second.id, None, None)
    factory = make_session_factory(engine)
    blind = DeleteScoringVersion(
        lambda: BlindUnitOfWork(factory), world.audit, ProtectedCatalog(OFFICIAL_TABLE)
    )

    with pytest.raises(Conflict):
        blind.execute(world.admin, second.id)

    assert stored(world, second.id) is not None
    assert events(world, second)[-1].action is AuditAction.CREATE


def test_when_the_delete_event_cannot_be_written_the_version_and_the_reopening_stay(world, uc):
    _, first, second = two_versions(world, uc)

    class FailingAudit(AuditService):
        def record(self, uow, actor_id, entity, entity_id, action, *args, **kwargs):
            if action is AuditAction.DELETE:
                raise RuntimeError("audit down")
            return super().record(uow, actor_id, entity, entity_id, action, *args, **kwargs)

    failing = DeleteScoringVersion(
        world.uow_factory, FailingAudit(world.audit._clock), ProtectedCatalog(OFFICIAL_TABLE)
    )

    with pytest.raises(RuntimeError):
        failing.execute(world.admin, second.id)

    assert stored(world, second.id) is not None
    assert stored(world, first.id).valid_to == date(2023, 12, 31)
    assert events(world, first)[-1].changes == {"valid_to": {"before": None, "after": "2023-12-31"}}


def test_the_generated_documents_of_a_process_do_not_change(world, uc):
    _, _, second = two_versions(world, uc)
    world.choose.execute(world.admin, world.process.id, world.other_version.id, None, None)
    generation = make_generation(world.process, world.admin.id)
    with world.uow_factory() as uow:
        uow.generations.add(generation)
        uow.generations.finish_ready(
            generation.id,
            generation.requested_at + timedelta(minutes=1),
            [make_file()],
            {"scoring_table": world.other_version.name, "total": "20"},
            [],
        )
        uow.commit()
    with world.uow_factory() as uow:
        before = uow.generations.get(generation.id)

    uc.delete.execute(world.admin, second.id)

    with world.uow_factory() as uow:
        assert uow.generations.get(generation.id) == before
        assert uow.processes.get(world.process.id).scoring_table_version_id == (
            world.other_version.id
        )
