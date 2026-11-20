"""REL-03 to REL-07, REL-15: running the wording of a section in the background."""

import logging

from app.domain.entities.audit import AuditAction
from app.domain.entities.generated import GenerationAlertCode, GenerationCode, GenerationState
from app.domain.entities.report import EntrySource
from app.domain.repositories.ports import AiWritingError
from tests.integration.doc_usecases.draft_support import (
    FakeReportWriter,
    request_wording_uc,
    run_wording_uc,
    save_entry_uc,
    stored_draft,
)
from tests.integration.doc_usecases.generation_support import add_activity

FAITHFUL = "Orientação da monografia sobre redes, concluída em 10/05/2023."
INVENTED = "Orientação da monografia sobre bancos com 40 horas, em 10/05/2023."


def two_activities(world):
    """Two orientations of the section 1.3: the first one is answered faithfully by the fake AI,
    the second with an invented number."""
    first = add_activity(world, title="Monografia sobre redes", item_number=7)
    second = add_activity(world, title="Monografia sobre bancos", item_number=8)
    return first, second


def ask(gen, section="1.3"):
    world = gen.world
    return request_wording_uc(world, gen.clock).execute(world.docente, world.process.id, section)


def run(gen, writer):
    return run_wording_uc(gen.world, gen.clock, writer).run_next()


def job_row(world, job):
    with world.uow_factory() as uow:
        return uow.wording_jobs.get(job.id)


def entry_of(draft, activity):
    return next(e for s in draft.sections for e in s.entries if e.activity_id == activity.id)


def section_of(draft, key):
    return next(s for s in draft.sections if s.key == key)


def test_a_faithful_answer_becomes_ia_and_an_invented_number_gives_the_template_text(gen):
    world = gen.world
    first, second = two_activities(world)
    job = ask(gen)
    writer = FakeReportWriter({first.id: FAITHFUL, second.id: INVENTED})

    assert run(gen, writer) is True

    stored = stored_draft(world)
    good, bad = entry_of(stored, first), entry_of(stored, second)
    assert (good.text, good.source) == (FAITHFUL, EntrySource.IA)
    assert bad.source is EntrySource.MODELO
    assert "Monografia sobre bancos" in bad.text and "40 horas" not in bad.text
    warnings = section_of(stored, "1.3").warnings
    assert [(w.code, w.message) for w in warnings] == [
        (GenerationAlertCode.REDACAO_REJEITADA, "NUMERO")
    ]
    done = job_row(world, job)
    assert done.state is GenerationState.PRONTO
    assert [w.code for w in done.warnings] == [GenerationAlertCode.REDACAO_REJEITADA]
    assert done.finished_at == gen.clock.now() and done.error_code is None


def test_an_answer_with_the_name_of_the_unit_passes_and_another_name_does_not(gen):
    world = gen.world
    first, second = two_activities(world)
    ask(gen)
    unit = f"{FAITHFUL[:-1]} na {world.fasi.name}."
    other = f"{FAITHFUL[:-1]} na Universidade de Lisboa."
    writer = FakeReportWriter({first.id: unit, second.id: other.replace("redes", "bancos")})

    run(gen, writer)

    stored = stored_draft(world)
    assert (entry_of(stored, first).text, entry_of(stored, first).source) == (unit, EntrySource.IA)
    assert entry_of(stored, second).source is EntrySource.MODELO
    assert section_of(stored, "1.3").warnings[0].message == "NOME"


def test_when_the_ai_is_unavailable_the_template_text_stays_with_the_alert_and_the_job_is_ready(
    gen,
):
    world = gen.world
    first, _ = two_activities(world)
    job = ask(gen)
    before = stored_draft(world)

    run(gen, FakeReportWriter(error=AiWritingError(GenerationAlertCode.REDACAO_INDISPONIVEL)))

    stored = stored_draft(world)
    assert entry_of(stored, first) == entry_of(before, first)
    assert entry_of(stored, first).source is EntrySource.MODELO
    assert [w.code for w in section_of(stored, "1.3").warnings] == [
        GenerationAlertCode.REDACAO_INDISPONIVEL
    ]
    done = job_row(world, job)
    assert done.state is GenerationState.PRONTO
    assert [w.code for w in done.warnings] == [GenerationAlertCode.REDACAO_INDISPONIVEL]


def test_an_edit_made_while_the_job_runs_stays_and_the_version_does_not_move(gen):
    world = gen.world
    first, second = two_activities(world)
    ask(gen)

    def user_edits():
        save_entry_uc(world).execute(
            world.docente, world.process.id, first.id, "Texto do docente", 1
        )

    writer = FakeReportWriter(
        {first.id: FAITHFUL, second.id: FAITHFUL.replace("redes", "bancos")}, during=user_edits
    )

    run(gen, writer)

    stored = stored_draft(world)
    assert stored.version == 2  # the edit moved it once; the wording did not
    assert (entry_of(stored, first).text, entry_of(stored, first).source) == (
        "Texto do docente",
        EntrySource.USUARIO,
    )
    assert entry_of(stored, second).source is EntrySource.IA


def test_an_unexpected_error_fails_the_job_and_leaves_the_draft_and_the_logs_without_text(
    gen, caplog
):
    world = gen.world
    two_activities(world)
    job = ask(gen)
    before = stored_draft(world)

    with caplog.at_level(logging.INFO, logger="app.documents.wording"):
        run(gen, FakeReportWriter(error=RuntimeError("texto sigiloso do documento")))

    done = job_row(world, job)
    assert (done.state, done.error_code) == (GenerationState.FALHOU, GenerationCode.ERRO_INTERNO)
    assert stored_draft(world) == before
    with world.uow_factory() as uow:
        events = uow.audit.list_for("report_wording_job", str(job.id))
    [status] = [e for e in events if e.action is AuditAction.STATUS]
    assert status.changes["state"] == {"before": "GERANDO", "after": "FALHOU"}
    assert status.changes["error_code"]["after"] == "ERRO_INTERNO"
    assert "sigiloso" not in str(events)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "RuntimeError" in messages and "sigiloso" not in messages
    assert all(r.exc_info is None for r in caplog.records)


def test_the_audit_of_a_finished_job_has_the_state_and_the_warning_codes_but_no_text(gen):
    world = gen.world
    first, second = two_activities(world)
    job = ask(gen)

    run(gen, FakeReportWriter({first.id: FAITHFUL, second.id: INVENTED}))

    with world.uow_factory() as uow:
        events = uow.audit.list_for("report_wording_job", str(job.id))
    [status] = [e for e in events if e.action is AuditAction.STATUS]
    assert status.changes["state"] == {"before": "GERANDO", "after": "PRONTO"}
    assert status.changes["warnings"]["after"] == ["REDACAO_REJEITADA"]
    assert FAITHFUL not in str(events) and "bancos" not in str(events)


def test_only_the_fields_of_the_activities_without_text_of_the_user_are_sent(gen):
    world = gen.world
    typed = add_activity(world, title="Monografia escrita pelo docente", item_number=7)
    sent = add_activity(
        world,
        title="Monografia sobre redes",
        item_number=8,
        description="Contato 123.456.789-09",
        evidence_note="Anotação interna que não vai",
    )
    save_entry_uc(world).execute(world.docente, world.process.id, typed.id, "Texto do docente", 0)
    ask(gen)
    writer = FakeReportWriter()

    run(gen, writer)

    [(title, items)] = writer.calls
    assert title == "Atividades didáticas: orientações"
    assert [i.activity_id for i in items] == [sent.id]
    payload = items[0].payload()
    assert set(payload) <= {
        "id",
        "tipo",
        "titulo",
        "datas",
        "carga_horaria",
        "carga_horaria_curso",
        "periodo_letivo",
        "quantidade",
        "descricao",
    }
    text = str(payload)
    assert "123.456.789-09" not in text
    assert "Anotação interna" not in text
    assert world.professor.full_name not in text and world.professor.siape not in text


def test_a_section_with_only_texts_of_the_user_does_not_call_the_ai_and_the_job_is_ready(gen):
    world = gen.world
    typed = add_activity(world, title="Monografia escrita pelo docente")
    save_entry_uc(world).execute(world.docente, world.process.id, typed.id, "Texto do docente", 0)
    job = ask(gen)
    writer = FakeReportWriter()

    run(gen, writer)

    assert writer.calls == []
    assert job_row(world, job).state is GenerationState.PRONTO
    assert entry_of(stored_draft(world), typed).text == "Texto do docente"


def test_the_runner_takes_the_oldest_waiting_job_and_is_false_when_there_is_none(gen):
    world = gen.world
    add_activity(world)
    first = ask(gen, "1.3")
    gen.clock.advance(seconds=5)
    second = ask(gen, "2")
    writer = FakeReportWriter()

    assert run(gen, writer) is True
    assert job_row(world, first).state is GenerationState.PRONTO
    assert job_row(world, second).state is GenerationState.GERANDO
    assert run(gen, writer) is True
    assert job_row(world, second).state is GenerationState.PRONTO
    assert run(gen, writer) is False
