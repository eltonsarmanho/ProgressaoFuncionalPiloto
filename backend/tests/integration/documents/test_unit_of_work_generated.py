"""VER-01: the unit of work exposes the generated-document repositories in one transaction."""

import pytest

from app.domain.entities.generated import DocumentKind
from app.infrastructure.database.repositories import (
    SqlGenerationRepository,
    SqlLayoutRepository,
    SqlReportDraftRepository,
    SqlWordingJobRepository,
)
from tests.integration.documents.generated_support import (
    make_draft,
    make_generation,
    make_layout,
    make_wording_job,
)


def write_everything(uow, process, user_id):
    generation = make_generation(process, user_id, DocumentKind.COMPROVANTE)
    job = make_wording_job(process, user_id, "1.2")
    uow.generations.add(generation)
    uow.wording_jobs.add(job)
    uow.report_drafts.create(make_draft(process), user_id, 0)
    uow.comprovante_layouts.create(make_layout(process), user_id, 0)
    return generation, job


def read_everything(uow_factory, process, generation, job):
    with uow_factory() as uow:
        return (
            uow.generations.get(generation.id),
            uow.wording_jobs.get(job.id),
            uow.report_drafts.get(process.id),
            uow.comprovante_layouts.get(process.id),
        )


def test_each_repository_is_reachable_by_its_name_on_the_unit_of_work(uow_factory):
    with uow_factory() as uow:
        assert isinstance(uow.generations, SqlGenerationRepository)
        assert isinstance(uow.wording_jobs, SqlWordingJobRepository)
        assert isinstance(uow.report_drafts, SqlReportDraftRepository)
        assert isinstance(uow.comprovante_layouts, SqlLayoutRepository)


def test_the_four_repositories_commit_together(uow_factory, process, base):
    with uow_factory() as uow:
        generation, job = write_everything(uow, process, base["admin"].id)
        uow.commit()

    stored_generation, stored_job, draft, layout = read_everything(
        uow_factory, process, generation, job
    )
    assert stored_generation == generation
    assert stored_job == job
    assert draft.version == 1
    assert layout.version == 1


def test_leaving_the_unit_of_work_without_commit_rolls_all_four_back(uow_factory, process, base):
    with uow_factory() as uow:
        generation, job = write_everything(uow, process, base["admin"].id)

    assert read_everything(uow_factory, process, generation, job) == (None, None, None, None)


def test_an_explicit_rollback_drops_what_the_four_repositories_wrote(uow_factory, process, base):
    with uow_factory() as uow:
        generation, job = write_everything(uow, process, base["admin"].id)
        uow.rollback()
        assert uow.generations.get(generation.id) is None

    assert read_everything(uow_factory, process, generation, job) == (None, None, None, None)


def test_a_failure_after_the_writes_leaves_nothing_behind(uow_factory, process, base):
    with pytest.raises(RuntimeError), uow_factory() as uow:
        generation, job = write_everything(uow, process, base["admin"].id)
        raise RuntimeError("falha antes do commit")

    assert read_everything(uow_factory, process, generation, job) == (None, None, None, None)
