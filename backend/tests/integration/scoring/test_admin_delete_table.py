"""GTAB-28, GTAB-29, GTAB-30, GTAB-31, GTAB-32, GTAB-42: delete a table with its versions in one
transaction, with a preview. Tables here are synthetic; the official one is OFFICIAL_TABLE."""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.application.services.audit_service import AuditService
from app.application.use_cases import scoring, scoring_admin
from app.application.use_cases.scoring_admin import (
    DeleteScoringTable,
    PreviewDeleteTable,
    ProtectedCatalog,
)
from app.application.use_cases.scoring_defaults import SetUnitDefaultVersion
from app.domain.entities.audit import AuditAction
from app.domain.errors import Conflict, Forbidden, NotFound
from app.domain.repositories.ports import ScoringTableRecord
from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory
from tests.integration.scoring.conftest import OFFICIAL_TABLE
from tests.support.races import Gate, Worker, hooked_factory, wait_until_blocked

REFERENCE = "Res. 7.000/2026-CONSEPE"


@pytest.fixture
def uc(world):
    catalog = ProtectedCatalog(OFFICIAL_TABLE)
    return SimpleNamespace(
        delete=DeleteScoringTable(world.uow_factory, world.audit, catalog),
        preview=PreviewDeleteTable(world.uow_factory, catalog),
        create_table=scoring_admin.CreateScoringTable(world.uow_factory, world.audit),
        create_version=scoring_admin.CreateVersionFrom(world.uow_factory, world.audit),
        mark=SetUnitDefaultVersion(world.uow_factory, world.audit),
    )


def make_table(world, uc, name="Tabela Sintética A", unit_ids=()):
    return uc.create_table.execute(
        world.admin,
        name,
        list(unit_ids),
        date(2020, 1, 1),
        None,
        REFERENCE,
        base_version_id=world.official_version.id,
    )


def two_versions(world, uc, **kw):
    """A table with two versions linked by `superseded_by_id` (the older one is superseded)."""
    table = make_table(world, uc, **kw)
    first = table.versions[0].version
    second = uc.create_version.execute(
        world.admin, table.table.id, first.id, date(2024, 1, 1), None, REFERENCE
    ).version
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(first.id, second.id)
        uow.commit()
    return table.table, first, second


def table_exists(world, table_id):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_table(table_id) is not None


def version_ids(world, table_id):
    with world.uow_factory() as uow:
        return [v.id for v in uow.scoring_tables.list_versions(table_id)]


def table_events(world, table_id):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("scoring_table", str(table_id)))


def rows_of(engine, table_id, version_ids) -> dict[str, int]:
    """How many rows of the table and of its versions are left, by kind."""
    with engine.connect() as conn:
        one = conn.exec_driver_sql
        return {
            "tables": one(
                "SELECT count(*) FROM scoring_tables WHERE id = %(t)s", {"t": table_id}
            ).scalar_one(),
            "units": one(
                "SELECT count(*) FROM scoring_table_units WHERE table_id = %(t)s", {"t": table_id}
            ).scalar_one(),
            "versions": one(
                "SELECT count(*) FROM scoring_table_versions WHERE table_id = %(t)s",
                {"t": table_id},
            ).scalar_one(),
            "groups": one(
                "SELECT count(*) FROM scoring_groups WHERE version_id = ANY(%(v)s)",
                {"v": list(version_ids)},
            ).scalar_one(),
            "criteria": one(
                "SELECT count(*) FROM scoring_criteria c JOIN scoring_groups g "
                "ON g.id = c.group_id WHERE g.version_id = ANY(%(v)s)",
                {"v": list(version_ids)},
            ).scalar_one(),
        }


def test_deleting_removes_the_table_its_versions_groups_criteria_and_unit_associations(
    world, uc, engine
):
    table, first, second = two_versions(world, uc, unit_ids=[world.fasi.id, world.ifch.id])
    ids = (first.id, second.id)
    assert rows_of(engine, table.id, ids) == {
        "tables": 1,
        "units": 2,
        "versions": 2,
        "groups": 16,
        "criteria": 200,
    }

    uc.delete.execute(world.admin, table.id)

    assert rows_of(engine, table.id, ids) == {
        "tables": 0,
        "units": 0,
        "versions": 0,
        "groups": 0,
        "criteria": 0,
    }


def test_the_delete_event_keeps_the_name_the_versions_the_criteria_and_the_units(world, uc):
    table, first, second = two_versions(world, uc, unit_ids=[world.fasi.id])

    uc.delete.execute(world.admin, table.id)

    deleted = table_events(world, table.id)[-1]
    assert deleted.action is AuditAction.DELETE
    assert deleted.user_id == world.admin.id
    assert deleted.entity == "scoring_table"
    assert deleted.entity_id == str(table.id)
    before = {field: change["before"] for field, change in deleted.changes.items()}
    assert before["name"] == "Tabela Sintética A"
    assert before["unit_ids"] == [str(world.fasi.id)]
    assert before["criteria"] == 200
    assert before["versions"] == [
        {
            "id": str(first.id),
            "name": first.name,
            "valid_from": "2020-01-01",
            "valid_to": "2023-12-31",
            "norm_reference": REFERENCE,
            "status": "PENDENTE_VALIDACAO",
        },
        {
            "id": str(second.id),
            "name": second.name,
            "valid_from": "2024-01-01",
            "valid_to": None,
            "norm_reference": REFERENCE,
            "status": "PENDENTE_VALIDACAO",
        },
    ]


def test_the_earlier_events_of_the_table_and_of_its_versions_stay(world, uc):
    table, first, second = two_versions(world, uc)

    uc.delete.execute(world.admin, table.id)

    created, deleted = table_events(world, table.id)
    assert (created.action, deleted.action) == (AuditAction.CREATE, AuditAction.DELETE)
    with world.uow_factory() as uow:
        for version in (first, second):
            actions = [e.action for e in uow.audit.list_for("scoring_version", str(version.id))]
            assert actions[0] is AuditAction.CREATE


def test_a_table_with_no_version_can_be_deleted(world, uc):
    table = ScoringTableRecord(uuid.uuid4(), "Tabela Sintética Vazia", unit_ids=(world.fasi.id,))
    with world.uow_factory() as uow:
        uow.scoring_tables.add_table(table)
        uow.commit()

    uc.delete.execute(world.admin, table.id)

    assert not table_exists(world, table.id)
    assert table_events(world, table.id)[-1].action is AuditAction.DELETE


def test_the_name_of_a_deleted_table_can_be_used_again(world, uc):
    table, _, _ = two_versions(world, uc)
    uc.delete.execute(world.admin, table.id)

    again = make_table(world, uc)

    assert again.table.name == "Tabela Sintética A"
    assert table_exists(world, again.table.id)


def test_the_official_table_is_409_protected_and_nothing_is_deleted(world, uc):
    table_id = world.official_version.table_id

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, table_id)

    assert refused.value.code == "TABELA_OFICIAL_PROTEGIDA"
    assert table_exists(world, table_id)
    assert world.official_version.id in version_ids(world, table_id)


def test_a_version_used_by_a_process_is_409_with_the_count_and_nothing_is_deleted(world, uc):
    table, first, second = two_versions(world, uc)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(first.id, None)  # so it can be chosen
        uow.commit()
    world.choose.execute(world.admin, world.process.id, first.id, None, None)
    world.choose.execute(world.admin, world.ifch_process.id, second.id, None, None)

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, table.id)

    assert refused.value.code == "VERSAO_USADA_POR_PROCESSO"
    assert str(refused.value) == (
        "A tabela tem versões usadas por 2 processos e não pode ser excluída"
    )
    assert version_ids(world, table.id) == [first.id, second.id]


def test_a_version_in_use_of_a_unit_is_409_with_the_acronyms_and_nothing_is_deleted(world, uc):
    table, first, second = two_versions(world, uc, unit_ids=[world.fasi.id, world.ifch.id])
    uc.mark.execute(world.admin, world.ifch.id, second.id)
    uc.mark.execute(world.admin, world.fasi.id, second.id)

    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, table.id)

    assert refused.value.code == "VERSAO_EM_USO_DE_UNIDADE"
    assert "FASI, IFCH" in str(refused.value)
    assert table_exists(world, table.id)
    assert version_ids(world, table.id) == [first.id, second.id]


def test_a_non_admin_gets_403_and_an_unknown_table_404(world, uc):
    table, _, _ = two_versions(world, uc)
    for actor in (world.docente, world.secretaria):
        with pytest.raises(Forbidden):
            uc.delete.execute(actor, table.id)
    with pytest.raises(NotFound):
        uc.delete.execute(world.admin, uuid.uuid4())

    assert table_exists(world, table.id)


def test_the_preview_counts_versions_criteria_and_units_with_no_blocker(world, uc):
    table, _, _ = two_versions(world, uc, unit_ids=[world.fasi.id, world.ifch.id])

    preview = uc.preview.execute(table.id)

    assert preview.name == "Tabela Sintética A"
    assert preview.versions == 2
    assert preview.criteria == 200
    assert sorted((u.id, u.acronym) for u in preview.units) == sorted(
        [(world.fasi.id, "FASI"), (world.ifch.id, "IFCH")]
    )
    assert preview.blocked == []


def test_the_preview_lists_the_blockers_the_deletion_refuses_with(world, uc):
    table, _, second = two_versions(world, uc, unit_ids=[world.fasi.id])
    uc.mark.execute(world.admin, world.fasi.id, second.id)

    preview = uc.preview.execute(table.id)

    assert [b.code for b in preview.blocked] == ["VERSAO_EM_USO_DE_UNIDADE"]
    assert preview.blocked[0].acronyms == ("FASI",)
    with pytest.raises(Conflict) as refused:
        uc.delete.execute(world.admin, table.id)
    assert str(refused.value) == preview.blocked[0].message


def test_the_preview_of_the_official_table_names_the_protection_and_an_unknown_table_is_404(
    world, uc
):
    preview = uc.preview.execute(world.official_version.table_id)

    assert [b.code for b in preview.blocked][0] == "TABELA_OFICIAL_PROTEGIDA"
    with pytest.raises(NotFound):
        uc.preview.execute(uuid.uuid4())


def test_when_the_delete_event_cannot_be_written_nothing_is_deleted(world, uc, engine):
    table, first, second = two_versions(world, uc, unit_ids=[world.fasi.id])

    class FailingAudit(AuditService):
        def record(self, uow, actor_id, entity, entity_id, action, *args, **kwargs):
            if action is AuditAction.DELETE:
                raise RuntimeError("audit down")
            return super().record(uow, actor_id, entity, entity_id, action, *args, **kwargs)

    failing = DeleteScoringTable(
        world.uow_factory, FailingAudit(world.audit._clock), ProtectedCatalog(OFFICIAL_TABLE)
    )

    with pytest.raises(RuntimeError):
        failing.execute(world.admin, table.id)

    assert table_exists(world, table.id)
    assert version_ids(world, table.id) == [first.id, second.id]
    assert rows_of(engine, table.id, (first.id, second.id))["units"] == 1


def test_a_process_choosing_a_version_while_the_deletion_waits_for_its_lock_is_refused(
    world, uc, engine
):
    table, _, second = two_versions(world, uc)
    gate = Gate()
    choosing_factory = hooked_factory(engine, ("lock_version",), lambda _name: gate.hold())
    choosing = Worker(
        lambda: scoring.ChooseProcessTable(choosing_factory, world.audit, world.policy).execute(
            world.admin, world.process.id, second.id, None, None
        )
    ).start()
    gate.wait_reached()  # the choice holds the lock of the version, not committed
    deletion = Worker(lambda: uc.delete.execute(world.admin, table.id)).start()
    wait_until_blocked(engine)

    gate.release()
    choosing.join()
    deletion.join()

    assert choosing.error is None
    assert isinstance(deletion.error, Conflict)
    assert deletion.error.code == "VERSAO_USADA_POR_PROCESSO"
    assert table_exists(world, table.id)


def test_a_unit_marking_a_version_while_the_deletion_waits_for_its_lock_is_refused(
    world, uc, engine
):
    table, _, second = two_versions(world, uc, unit_ids=[world.fasi.id])
    gate = Gate()
    marking_factory = hooked_factory(engine, ("set_unit_default",), lambda _name: gate.hold())
    marking = Worker(
        lambda: SetUnitDefaultVersion(marking_factory, world.audit).execute(
            world.admin, world.fasi.id, second.id
        )
    ).start()
    gate.wait_reached()  # the mark is written and holds the locks, not committed
    deletion = Worker(lambda: uc.delete.execute(world.admin, table.id)).start()
    wait_until_blocked(engine)

    gate.release()
    marking.join()
    deletion.join()

    assert marking.error is None
    assert isinstance(deletion.error, Conflict)
    assert deletion.error.code == "VERSAO_EM_USO_DE_UNIDADE"
    assert table_exists(world, table.id)


def test_a_foreign_key_violation_that_escapes_the_facts_is_409_and_nothing_is_deleted(
    world, engine
):
    class BlindUnitOfWork(SqlUnitOfWork):
        """Hides the processes from the facts, so only the foreign key can refuse."""

        def __enter__(self):
            super().__enter__()
            self.scoring_tables.version_process_counts = lambda: {}
            return self

    make = SimpleNamespace(
        create_table=scoring_admin.CreateScoringTable(world.uow_factory, world.audit),
        create_version=scoring_admin.CreateVersionFrom(world.uow_factory, world.audit),
    )
    table, first, second = two_versions(world, make)
    with world.uow_factory() as uow:
        uow.scoring_tables.set_superseded(first.id, None)
        uow.commit()
    world.choose.execute(world.admin, world.process.id, first.id, None, None)
    factory = make_session_factory(engine)
    blind = DeleteScoringTable(
        lambda: BlindUnitOfWork(factory), world.audit, ProtectedCatalog(OFFICIAL_TABLE)
    )

    with pytest.raises(Conflict):
        blind.execute(world.admin, table.id)

    assert table_exists(world, table.id)
    assert version_ids(world, table.id) == [first.id, second.id]
    assert table_events(world, table.id)[-1].action is AuditAction.CREATE
