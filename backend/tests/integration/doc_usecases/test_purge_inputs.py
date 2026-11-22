"""DEL-05, DEL-06, DEL-08, DEL-09: PurgeInputDocuments removes the file, the pages and the
excerpts of every input document of a process, one document at a time."""

import dataclasses
import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.purge_inputs import PurgeInputDocuments, PurgeOutcome
from tests.integration.doc_usecases.board_support import MEMBERS, stored_board
from tests.integration.doc_usecases.conclusion_support import (
    add_input_document,
    add_ordinance,
    state_of,
)
from tests.integration.doc_usecases.generation_support import add_document

NOW = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FlakyStorage:
    """The real storage, except that removing the named files raises OSError (or does nothing)."""

    def __init__(self, real, failing=(), silent=()):
        self._real = real
        self.failing = set(failing)
        self.silent = set(silent)
        self.deleted = []

    def delete(self, process_id, internal_name):
        if internal_name in self.failing:
            raise PermissionError("trancado")
        if internal_name not in self.silent:
            self._real.delete(process_id, internal_name)
        self.deleted.append(internal_name)

    def path(self, process_id, internal_name):
        return self._real.path(process_id, internal_name)


def purge(gen, storage=None, uow_factory=None) -> PurgeInputDocuments:
    return PurgeInputDocuments(
        uow_factory or gen.world.uow_factory, storage or gen.originals, FixedClock()
    )


@pytest.fixture
def three(gen):
    return [add_input_document(gen, size=100 * n)[0] for n in (1, 2, 3)]


def test_three_documents_lose_file_pages_and_excerpts_and_keep_the_metadata(gen, three):
    process = gen.world.process

    outcome = purge(gen).execute(process.id)

    assert outcome == PurgeOutcome(removed=3, pending=0, bytes_freed=600)
    for before in three:
        after = state_of(gen, before)
        assert after.file_exists is False  # the file is gone from the storage
        assert after.pages == []  # the extracted text is gone
        assert after.links == [(1, "")]  # the link stays with its number, the excerpt is empty
        assert after.row.file_deleted_at == NOW
        kept = ("original_name", "mime", "size_bytes", "sha256", "page_count", "internal_name")
        assert all(getattr(after.row, f) == getattr(before, f) for f in kept)


def test_a_document_outside_the_interstice_is_purged_like_any_other(gen):
    inside, _ = add_input_document(gen, size=10)
    outside, _ = add_input_document(gen, size=20, outside=True)

    outcome = purge(gen).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=2, pending=0, bytes_freed=30)
    for document in (inside, outside):
        after = state_of(gen, document)
        assert (after.file_exists, after.pages) == (False, [])
        assert after.row.file_deleted_at == NOW


def test_a_removal_that_fails_leaves_that_document_pending_and_the_others_go_on(gen, three):
    stuck = three[1]
    storage = FlakyStorage(gen.originals, failing={stuck.internal_name})

    outcome = purge(gen, storage).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=2, pending=1, bytes_freed=100 + 300)
    after = state_of(gen, stuck)
    assert after.file_exists is True
    assert after.row.file_deleted_at is None
    assert after.pages == [1, 2]
    assert after.links == [(1, "trecho")]
    for done in (three[0], three[2]):
        assert state_of(gen, done).row.file_deleted_at == NOW


def test_repeating_removes_what_is_missing_and_a_third_run_finds_nothing(gen, three):
    stuck = three[1]
    purge(gen, FlakyStorage(gen.originals, failing={stuck.internal_name})).execute(
        gen.world.process.id
    )

    again = purge(gen).execute(gen.world.process.id)
    third = purge(gen).execute(gen.world.process.id)

    assert again == PurgeOutcome(removed=1, pending=0, bytes_freed=200)
    assert state_of(gen, stuck).row.file_deleted_at == NOW
    assert third == PurgeOutcome(removed=0, pending=0, bytes_freed=0)


def test_a_file_that_is_already_absent_counts_as_removed(gen):
    document, _ = add_input_document(gen, size=50)
    gen.originals.delete(document.process_id, document.internal_name)

    outcome = purge(gen).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=1, pending=0, bytes_freed=50)
    after = state_of(gen, document)
    assert (after.row.file_deleted_at, after.pages) == (NOW, [])


def test_a_file_that_is_still_there_after_the_removal_is_pending(gen):
    document, _ = add_input_document(gen, size=50)
    storage = FlakyStorage(gen.originals, silent={document.internal_name})

    outcome = purge(gen, storage).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=0, pending=1, bytes_freed=0)
    assert state_of(gen, document).row.file_deleted_at is None


class CrashOnCommit:
    """A unit of work factory whose commit fails with a RuntimeError, as a crash would."""

    def __init__(self, real):
        self._real = real

    def __call__(self):
        uow = self._real()
        uow.commit = self._crash
        return uow

    @staticmethod
    def _crash():
        raise RuntimeError("queda do servidor")


def test_a_crash_between_the_file_removal_and_the_commit_is_closed_by_the_next_attempt(gen):
    document, _ = add_input_document(gen, size=70)
    process_id = gen.world.process.id

    with pytest.raises(RuntimeError):
        purge(gen, uow_factory=CrashOnCommit(gen.world.uow_factory)).execute(process_id)
    crashed = state_of(gen, document)
    assert crashed.file_exists is False  # the file went first
    assert crashed.row.file_deleted_at is None  # but nothing was marked
    assert (crashed.pages, crashed.links) == ([1, 2], [(1, "trecho")])

    outcome = purge(gen).execute(process_id)

    assert outcome == PurgeOutcome(removed=1, pending=0, bytes_freed=70)
    closed = state_of(gen, document)
    assert (closed.row.file_deleted_at, closed.pages, closed.links) == (NOW, [], [(1, "")])


def test_a_document_already_marked_is_skipped_and_other_processes_are_left_alone(gen):
    world = gen.world
    marked, _ = add_input_document(gen, size=40)
    with world.uow_factory() as uow:
        uow.documents.mark_file_deleted(marked.id, datetime(2026, 11, 1, tzinfo=UTC))
        uow.commit()
    other_process = dataclasses.replace(world.process, id=uuid.uuid4())
    with world.uow_factory() as uow:
        uow.processes.add(other_process)
        uow.commit()
    elsewhere, _ = add_input_document(gen, other_process, size=60)
    storage = FlakyStorage(gen.originals)

    outcome = purge(gen, storage).execute(world.process.id)

    assert outcome == PurgeOutcome(removed=0, pending=0, bytes_freed=0)
    assert storage.deleted == []
    assert state_of(gen, marked).row.file_deleted_at == datetime(2026, 11, 1, tzinfo=UTC)
    assert state_of(gen, elsewhere).file_exists is True


def test_a_process_without_documents_purges_nothing(gen):
    assert purge(gen).execute(gen.world.process.id) == PurgeOutcome(0, 0, 0)


def test_documents_added_by_row_only_have_their_rows_closed(gen):
    row_only = add_document(gen.world, size_bytes=33)

    outcome = purge(gen).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=1, pending=0, bytes_freed=33)
    assert state_of(gen, row_only).row.file_deleted_at == NOW


# --- the ordinance file (DOS-07, PORT-09) -------------------------------------------------


def test_the_ordinance_file_goes_with_the_documents_and_the_data_stay(gen, three):
    file, before = add_ordinance(gen, size=40, members=MEMBERS)
    process_id = gen.world.process.id

    outcome = purge(gen).execute(process_id)

    assert outcome == PurgeOutcome(removed=4, pending=0, bytes_freed=600 + 40)
    assert not gen.originals.path(process_id, file.internal_name).exists()
    after = stored_board(gen.world)
    assert after.file.deleted_at == NOW
    assert (after.file.internal_name, after.file.original_name) == (
        file.internal_name,
        file.original_name,
    )
    assert (after.number, after.ordinance_date, after.members) == (
        before.number,
        before.ordinance_date,
        before.members,
    )


def test_without_an_ordinance_the_numbers_are_the_same_as_before(gen, three):
    assert purge(gen).execute(gen.world.process.id) == PurgeOutcome(3, 0, 600)

    typed_only = gen.world.process
    add_ordinance(gen, stored=False)  # typed data and no file: nothing to remove
    assert purge(gen).execute(typed_only.id) == PurgeOutcome(0, 0, 0)
    assert stored_board(gen.world).file is None


def test_an_ordinance_file_that_cannot_be_removed_stays_pending_and_is_not_marked(gen, three):
    file, _ = add_ordinance(gen, size=40)
    storage = FlakyStorage(gen.originals, failing={file.internal_name})

    outcome = purge(gen, storage).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=3, pending=1, bytes_freed=600)
    assert gen.originals.path(gen.world.process.id, file.internal_name).exists()
    assert stored_board(gen.world).file.deleted_at is None


def test_repeating_removes_the_ordinance_file_that_was_left_and_a_third_run_finds_nothing(gen):
    file, _ = add_ordinance(gen, size=40)
    purge(gen, FlakyStorage(gen.originals, failing={file.internal_name})).execute(
        gen.world.process.id
    )

    again = purge(gen).execute(gen.world.process.id)
    third = purge(gen).execute(gen.world.process.id)

    assert again == PurgeOutcome(removed=1, pending=0, bytes_freed=40)
    assert stored_board(gen.world).file.deleted_at == NOW
    assert third == PurgeOutcome(0, 0, 0)


def test_an_ordinance_file_that_is_already_absent_counts_as_removed(gen):
    file, _ = add_ordinance(gen, size=40)
    gen.originals.delete(gen.world.process.id, file.internal_name)

    outcome = purge(gen).execute(gen.world.process.id)

    assert outcome == PurgeOutcome(removed=1, pending=0, bytes_freed=40)
    assert stored_board(gen.world).file.deleted_at == NOW


def test_the_ordinance_of_another_process_is_left_alone(gen):
    world = gen.world
    file, _ = add_ordinance(gen, process=world.ifch_process, size=40)

    outcome = purge(gen).execute(world.process.id)

    assert outcome == PurgeOutcome(0, 0, 0)
    assert gen.originals.path(world.ifch_process.id, file.internal_name).exists()
    assert stored_board(world, world.ifch_process).file.deleted_at is None
