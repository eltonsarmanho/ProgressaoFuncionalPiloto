"""GI-07, GI-10: the new table version supersedes the previous one; editable processes move to
it with one audit event each, the finished ones stay (AD-012)."""

import uuid
from dataclasses import replace

import pytest

from app.application.use_cases.scoring_adoption import AdoptSupersedingVersion
from app.domain.entities.audit import AuditAction
from app.domain.entities.process import ProcessStatus
from tests.integration.documents.generated_support import make_generation
from tests.support.scoring_variants import LEGACY_UFPA_NAME, add_legacy_ufpa_version

JUSTIFICATION = "AD-023: Grupo I no total"


@pytest.fixture
def legacy(world):
    """The previous version in the table of the seeded one; the seeded version is the new one."""
    with world.uow_factory() as uow:
        legacy = add_legacy_ufpa_version(uow, world.official_version)
        uow.commit()
    return legacy


@pytest.fixture
def adopt(world):
    def run(uow=None, name=LEGACY_UFPA_NAME):
        use_case = AdoptSupersedingVersion(world.audit)
        if uow is not None:
            return use_case.execute(uow, world.official_version.table_id, name,
                                    world.official_version.name)  # fmt: skip
        with world.uow_factory() as own:
            moved = use_case.execute(own, world.official_version.table_id, name,
                                     world.official_version.name)  # fmt: skip
            own.commit()
        return moved

    return run


def process_on(world, add_process, version, status=ProcessStatus.RASCUNHO):
    process = add_process(status=status)
    with world.uow_factory() as uow:
        uow.processes.set_scoring_table_version(process.id, version.id)
        uow.commit()
    return process


def chosen_version(world, process):
    with world.uow_factory() as uow:
        return uow.processes.get(process.id).scoring_table_version_id


def audit_of(world, process):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("process", str(process.id)))


def superseded_by(world, version):
    with world.uow_factory() as uow:
        return uow.scoring_tables.get_version(version.id).superseded_by_id


def test_draft_and_in_progress_processes_move_to_the_new_version_with_one_audit_event_each(
    world, add_process, legacy, adopt
):
    draft = process_on(world, add_process, legacy, ProcessStatus.RASCUNHO)
    running = process_on(world, add_process, legacy, ProcessStatus.EM_ANDAMENTO)

    moved = adopt()

    assert moved == 2
    for process in (draft, running):
        assert chosen_version(world, process) == world.official_version.id
        [event] = audit_of(world, process)
        assert event.action is AuditAction.UPDATE
        assert event.user_id is None  # the system, not a user
        assert event.justification == JUSTIFICATION
        assert event.changes == {
            "scoring_table_version_id": {
                "before": str(legacy.id), "after": str(world.official_version.id),
            }
        }  # fmt: skip


def test_the_previous_version_is_marked_as_superseded_by_the_new_one(world, legacy, adopt):
    adopt()

    assert superseded_by(world, legacy) == world.official_version.id
    assert superseded_by(world, world.official_version) is None


def test_concluded_and_archived_processes_keep_the_previous_version_and_get_no_event(
    world, add_process, legacy, adopt
):
    concluded = process_on(world, add_process, legacy, ProcessStatus.CONCLUIDO)
    archived = process_on(world, add_process, legacy, ProcessStatus.ARQUIVADO)

    moved = adopt()

    assert moved == 0
    for process in (concluded, archived):
        assert chosen_version(world, process) == legacy.id
        assert audit_of(world, process) == []


def test_a_process_on_another_table_does_not_change(world, add_process, legacy, adopt):
    other = process_on(world, add_process, world.other_version)

    adopt()

    assert chosen_version(world, other) == world.other_version.id
    assert audit_of(world, other) == []


def test_a_process_without_a_chosen_table_does_not_change(world, add_process, legacy, adopt):
    free = add_process()

    adopt()

    assert chosen_version(world, free) is None
    assert audit_of(world, free) == []


def test_running_it_again_changes_nothing_and_audits_nothing_new(
    world, add_process, legacy, adopt
):
    draft = process_on(world, add_process, legacy)
    adopt()
    after_first = audit_of(world, draft)

    moved = adopt()

    assert moved == 0
    assert chosen_version(world, draft) == world.official_version.id
    assert audit_of(world, draft) == after_first
    assert superseded_by(world, legacy) == world.official_version.id


def test_without_a_previous_version_nothing_happens(world, add_process, adopt):
    draft = process_on(world, add_process, world.official_version)

    assert adopt() == 0
    assert chosen_version(world, draft) == world.official_version.id
    assert audit_of(world, draft) == []


def test_a_failure_in_the_middle_changes_no_process_and_does_not_mark_the_version(
    world, add_process, legacy, adopt
):
    first = process_on(world, add_process, legacy)
    second = process_on(world, add_process, legacy)

    class FlakyProcesses:
        """Delegates to the real repository and raises on the second change."""

        def __init__(self, inner):
            self._inner, self.changes = inner, 0

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def set_scoring_table_version(self, process_id, version_id):
            self.changes += 1
            if self.changes == 2:
                raise RuntimeError("falha simulada")
            self._inner.set_scoring_table_version(process_id, version_id)

    with world.uow_factory() as uow:
        uow.processes = FlakyProcesses(uow.processes)
        with pytest.raises(RuntimeError, match="falha simulada"):
            adopt(uow)  # nothing is committed: leaving the unit of work rolls it back

    for process in (first, second):
        assert chosen_version(world, process) == legacy.id
        assert audit_of(world, process) == []
    assert superseded_by(world, legacy) is None


def test_the_documents_already_generated_keep_the_version_they_were_made_with(
    world, add_process, legacy, adopt
):
    draft = process_on(world, add_process, legacy)
    with world.uow_factory() as uow:
        uow.generations.add(make_generation(draft, world.admin.id))
        uow.commit()
    with world.uow_factory() as uow:
        before = list(uow.generations.list_for_process(draft.id))
    assert len(before) == 1

    adopt()

    with world.uow_factory() as uow:
        assert list(uow.generations.list_for_process(draft.id)) == before


def test_a_version_already_superseded_by_another_one_is_left_alone(
    world, add_process, legacy, adopt
):
    newer = replace(world.official_version, id=uuid.uuid4(), name="Outra versão sintética")
    with world.uow_factory() as uow:
        uow.scoring_tables.add_version(newer)
        uow.scoring_tables.set_superseded(legacy.id, newer.id)
        uow.commit()
    draft = process_on(world, add_process, legacy)

    assert adopt() == 0
    assert chosen_version(world, draft) == legacy.id
    assert superseded_by(world, legacy) == newer.id


# --- GTAB-09: the mark of a unit on a superseded version is cleared ------------------------------


def mark_in_use(world, unit, version):
    with world.uow_factory() as uow:
        uow.scoring_tables.set_unit_default(unit.id, version.id)
        uow.commit()


def mark_of(world, unit):
    with world.uow_factory() as uow:
        found = uow.scoring_tables.get_unit_default(unit.id)
    return found.version_id if found else None


def mark_events(world, unit):
    with world.uow_factory() as uow:
        return list(uow.audit.list_for("unit_scoring_default", str(unit.id)))


def test_the_unit_whose_version_in_use_is_superseded_loses_the_mark_with_a_system_delete_event(
    world, legacy, adopt
):
    mark_in_use(world, world.fasi, legacy)

    adopt()

    assert mark_of(world, world.fasi) is None
    [event] = mark_events(world, world.fasi)
    assert event.action is AuditAction.DELETE
    assert event.user_id is None
    assert event.entity == "unit_scoring_default"
    assert event.entity_id == str(world.fasi.id)
    assert event.changes == {"version_id": {"before": str(legacy.id), "after": None}}


def test_a_unit_with_another_version_in_use_keeps_it_and_gets_no_event(world, legacy, adopt):
    mark_in_use(world, world.fasi, legacy)
    mark_in_use(world, world.ifch, world.official_version)

    adopt()

    assert mark_of(world, world.ifch) == world.official_version.id
    assert mark_events(world, world.ifch) == []


def test_running_it_again_writes_no_new_mark_event(world, legacy, adopt):
    mark_in_use(world, world.fasi, legacy)
    adopt()
    after_first = mark_events(world, world.fasi)

    adopt()

    assert mark_events(world, world.fasi) == after_first
    assert len(after_first) == 1


def test_without_a_mark_on_the_superseded_version_no_mark_event_is_written(world, legacy, adopt):
    adopt()

    assert mark_events(world, world.fasi) == []
    assert mark_events(world, world.ifch) == []


def test_the_mark_is_cleared_in_the_same_transaction_as_the_supersession(world, legacy, adopt):
    mark_in_use(world, world.fasi, legacy)

    with world.uow_factory() as uow:
        adopt(uow)  # nothing is committed: the unit of work rolls it back

    assert mark_of(world, world.fasi) == legacy.id
    assert superseded_by(world, legacy) is None
    assert mark_events(world, world.fasi) == []
