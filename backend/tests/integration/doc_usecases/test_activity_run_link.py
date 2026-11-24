"""PIPE-09, CLS-04: an activity keeps its extraction run; AI candidates need no reason."""

from app.application.use_cases.scoring import ActivityData
from app.domain.entities.activity import ActivitySource, ActivityStatus, Candidate
from tests.integration.doc_usecases.support import draft_activity, pdf, seed_run


def test_activity_keeps_the_extraction_run_that_suggested_it(docs):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("run-link"))
    run = seed_run(w, document)

    activity = draft_activity(w, w.process, "Sugerida", run=run)

    with w.uow_factory() as uow:
        loaded = uow.activities.get(activity.id)
        [audit] = uow.audit.list_for("activity", str(activity.id))
    assert loaded.extraction_run_id == run.id
    assert audit.changes["extraction_run_id"]["after"] == str(run.id)


def test_manual_and_run_less_activities_have_no_extraction_run(docs):
    w = docs.world

    manual = w.create.execute(w.admin, w.process.id, ActivityData(title="Manual"))
    suggested = draft_activity(w, w.process, "Sem execucao")

    assert manual.extraction_run_id is None
    assert suggested.extraction_run_id is None


def test_editing_an_activity_keeps_its_extraction_run(docs):
    w = docs.world
    document = docs.upload_one(w.docente, w.process, pdf("run-edit"))
    run = seed_run(w, document)
    activity = draft_activity(w, w.process, "Antes", run=run)

    edited = w.update.execute(
        w.admin,
        activity.id,
        ActivityData(title="Depois", group_number=3, item_number=4),
        activity.version,
        None,
    )

    assert (edited.title, edited.extraction_run_id) == ("Depois", run.id)


def test_suggested_activity_may_carry_candidates_without_a_justification(docs):
    w = docs.world
    data = ActivityData(
        title="Com candidato",
        group_number=3,
        item_number=8,
        candidates=(Candidate(3, 12, ""),),
    )

    activity = w.create.execute(w.admin, w.process.id, data, source=ActivitySource.SUGERIDA_IA)

    assert activity.status is ActivityStatus.AGUARDANDO_REVISAO
    assert activity.candidates == (Candidate(3, 12, ""),)
