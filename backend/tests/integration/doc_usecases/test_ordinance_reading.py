"""PORT-02, PORT-03, PORT-04, PORT-07, restart during the reading: RunOrdinanceReading."""

import json
import logging
import uuid
from datetime import date

import pytest

from app.application.use_cases.board import MemberInput
from app.application.use_cases.ordinance_reading import RunOrdinanceReading
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import (
    BoardRole,
    OrdinanceReadingCode,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ReadingState,
    ValueSource,
)
from app.domain.repositories.ports import OrdinanceExtractionError
from app.domain.rules.ordinance_grounding import OrdinanceAi, OrdinanceAiMember
from tests.integration.doc_usecases.board_support import (
    FakeOrdinanceExtractor,
    board_events,
    save_data_uc,
    set_reading_state,
    stored_board,
    upload_uc,
)
from tests.integration.doc_usecases.support import pdf
from tests.unit.application.analyzer_fakes import FakeTextExtractor, ocr_page, text_page

DAY = date(2025, 3, 10)
PAGE_ONE = (
    "PORTARIA Nº 123/2025 - FASI. Belém, 10 de março de 2025. Designa a banca. "
    "Presidente: Maria Aparecida Souza. Membro: José da Silva. "
    "CPF 123.456.789-09, contato maria@exemplo.test, telefone (91) 98888-7777."
)
PAGE_TWO = "Suplente: Ana Beatriz Lima. Fim."
MEMBERS = (
    OrdinanceAiMember("Maria Aparecida Souza", "PRESIDENTE", 1),
    OrdinanceAiMember("José da Silva", "MEMBRO", 1),
    OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 2),
)
ANSWER = OrdinanceAi("123/2025", 1, DAY, 1, MEMBERS)


def queue(docs, process=None, actor=None):
    """An ordinance file sent through the use case: `PENDENTE`, waiting for the executor."""
    world = docs.world
    process = process or world.process
    incoming = docs.incoming(pdf(uuid.uuid4().hex), "portaria.pdf", "application/pdf")
    return upload_uc(world, docs).execute(actor or world.admin, process.id, incoming, 0, False)


def reader(docs, extractor, pages=None):
    """The executor over a fake text extractor; `pages` None gives the two synthetic pages."""
    world = docs.world
    default = (text_page(1, PAGE_ONE), text_page(2, PAGE_TWO))
    text = FakeTextExtractor(*(default if pages is None else pages))
    return RunOrdinanceReading(
        world.uow_factory, world.audit, docs.clock, docs.storage, text, extractor
    )


def read(docs, extractor, pages=None):
    queue(docs)
    assert reader(docs, extractor, pages).run_next() is True
    return stored_board(docs.world)


# --- PORT-02: the reading fills the data with the page of each value --------------------------


def test_a_three_member_ordinance_becomes_lida_with_number_date_and_members_with_their_pages(
    docs,
):
    ordinance = read(docs, FakeOrdinanceExtractor(ANSWER))

    assert ordinance.reading_state is ReadingState.LIDA
    assert ordinance.reading_code is None
    assert (ordinance.number, ordinance.number_page, ordinance.number_source) == (
        "123/2025",
        1,
        ValueSource.EXTRAIDO,
    )
    assert (ordinance.ordinance_date, ordinance.date_page, ordinance.date_source) == (
        DAY,
        1,
        ValueSource.EXTRAIDO,
    )
    assert [(m.name, m.role, m.page, m.source) for m in ordinance.members] == [
        ("Maria Aparecida Souza", BoardRole.PRESIDENTE, 1, ValueSource.EXTRAIDO),
        ("José da Silva", BoardRole.MEMBRO, 1, ValueSource.EXTRAIDO),
        ("Ana Beatriz Lima", BoardRole.SUPLENTE, 2, ValueSource.EXTRAIDO),
    ]
    assert ordinance.warnings == ()
    assert ordinance.is_registered


def test_the_reading_is_audited_without_user_names_or_text(docs):
    read(docs, FakeOrdinanceExtractor(ANSWER))

    finish = board_events(docs.world)[-1]
    assert finish.action is AuditAction.STATUS
    assert finish.user_id is None
    assert finish.changes["reading_state"] == {"before": "LENDO", "after": "LIDA"}
    assert finish.changes["member_count"]["after"] == 3
    assert "Maria" not in json.dumps(finish.changes)


# --- PORT-04: only masked text goes to the AI -------------------------------------------------


def test_the_extractor_gets_one_masked_text_with_page_marks_and_the_names_kept(docs):
    ai = FakeOrdinanceExtractor(ANSWER)

    read(docs, ai)

    [sent] = ai.received
    assert isinstance(sent, str)
    assert sent.startswith("[PÁGINA 1]\n") and "\n\n[PÁGINA 2]\n" in sent
    assert "[CPF]" in sent and "[EMAIL]" in sent and "[TELEFONE]" in sent
    for secret in ("123.456.789-09", "maria@exemplo.test", "98888-7777"):
        assert secret not in sent
    for name in ("Maria Aparecida Souza", "José da Silva", "Ana Beatriz Lima"):
        assert name in sent


# --- PORT-03: the check uses the ORIGINAL text of the cited page ------------------------------


def test_a_value_that_only_appears_on_another_page_is_left_empty_with_the_warning(docs):
    elsewhere = OrdinanceAi("123/2025", 2, DAY, 2, MEMBERS)  # both are on page 1 only

    ordinance = read(docs, FakeOrdinanceExtractor(elsewhere))

    assert (ordinance.number, ordinance.number_page, ordinance.number_source) == (None, None, None)
    assert (ordinance.ordinance_date, ordinance.date_source) == (None, None)
    assert OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "number") in ordinance.warnings
    assert (
        OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "ordinance_date")
        in ordinance.warnings
    )
    assert len(ordinance.members) == 3


def test_the_check_runs_on_the_original_page_even_where_the_mask_changed_the_text(docs):
    page = "PORTARIA Nº 12345678901, de 10 de março de 2025. Presidente: Maria Aparecida Souza."
    ai = FakeOrdinanceExtractor(OrdinanceAi("12345678901", 1, DAY, 1, MEMBERS[:1]))

    ordinance = read(docs, ai, (text_page(1, page),))

    assert "[CPF]" in ai.received[0] and "12345678901" not in ai.received[0]
    assert (ordinance.number, ordinance.number_page) == ("12345678901", 1)
    assert all(w.field != "number" for w in ordinance.warnings)


def test_a_member_the_cited_page_does_not_hold_is_dropped_with_the_warning(docs):
    ghost = OrdinanceAiMember("Pessoa Inventada Silva", "MEMBRO", 1)
    invented = OrdinanceAi("123/2025", 1, DAY, 1, (MEMBERS[0], ghost))

    ordinance = read(docs, FakeOrdinanceExtractor(invented))

    assert [m.name for m in ordinance.members] == ["Maria Aparecida Souza"]
    assert OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "members") in ordinance.warnings


def test_an_ordinance_without_members_is_lida_with_the_warning_that_none_were_found(docs):
    ordinance = read(docs, FakeOrdinanceExtractor(OrdinanceAi("123/2025", 1, DAY, 1, ())))

    assert ordinance.reading_state is ReadingState.LIDA
    assert ordinance.members == ()
    assert not ordinance.is_registered
    assert ordinance.warnings == (
        OrdinanceWarning(OrdinanceWarningCode.MEMBROS_NAO_ENCONTRADOS, "members"),
    )


# --- regra 1: what the person typed is never overwritten --------------------------------------


def test_reading_again_keeps_the_typed_number_and_the_member_list_and_fills_the_rest(docs):
    world = docs.world
    queued = queue(docs)
    save_data_uc(world).execute(
        world.docente,
        world.process.id,
        "55/2025",
        None,
        [MemberInput("Digitado Da Silva", BoardRole.PRESIDENTE)],
        queued.version,
    )

    assert reader(docs, FakeOrdinanceExtractor(ANSWER)).run_next() is True

    ordinance = stored_board(world)
    assert ordinance.reading_state is ReadingState.LIDA
    assert (ordinance.number, ordinance.number_source) == ("55/2025", ValueSource.INFORMADO)
    assert [(m.name, m.source) for m in ordinance.members] == [
        ("Digitado Da Silva", ValueSource.INFORMADO)
    ]
    assert (ordinance.ordinance_date, ordinance.date_source) == (DAY, ValueSource.EXTRAIDO)
    assert not any(w.field in ("number", "members") for w in ordinance.warnings)


def test_a_save_made_while_the_reading_runs_is_not_lost_and_the_reading_does_not_fail(docs):
    world = docs.world
    queued = queue(docs)

    def person_saves_the_number():
        save_data_uc(world).execute(
            world.docente, world.process.id, "55/2025", None, [], queued.version
        )

    ai = FakeOrdinanceExtractor(ANSWER, during=person_saves_the_number)

    assert reader(docs, ai).run_next() is True

    ordinance = stored_board(world)
    assert ordinance.reading_state is ReadingState.LIDA
    assert (ordinance.number, ordinance.number_source) == ("55/2025", ValueSource.INFORMADO)
    assert (ordinance.ordinance_date, ordinance.date_source) == (DAY, ValueSource.EXTRAIDO)
    assert len(ordinance.members) == 3
    assert ordinance.version == queued.version + 2  # the save and the end of the reading


# --- PORT-07: failures ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        OrdinanceReadingCode.IA_INDISPONIVEL,
        OrdinanceReadingCode.IA_CREDENCIAL_RECUSADA,
        OrdinanceReadingCode.RESPOSTA_INVALIDA,
    ],
)
def test_an_error_of_the_extractor_is_falhou_with_its_code_and_the_typed_data_stay(docs, code):
    world = docs.world
    queued = queue(docs)
    save_data_uc(world).execute(
        world.docente,
        world.process.id,
        "55/2025",
        DAY,
        [MemberInput("Digitado Da Silva", BoardRole.MEMBRO)],
        queued.version,
    )
    typed = stored_board(world)

    assert reader(docs, FakeOrdinanceExtractor(error=OrdinanceExtractionError(code))).run_next()

    failed = stored_board(world)
    assert failed.reading_state is ReadingState.FALHOU
    assert failed.reading_code is code
    assert (failed.number, failed.ordinance_date, failed.members) == (
        typed.number,
        typed.ordinance_date,
        typed.members,
    )
    assert failed.version == typed.version
    event = board_events(world)[-1]
    assert event.user_id is None
    assert event.changes["reading_state"] == {"before": "LENDO", "after": "FALHOU"}
    assert event.changes["reading_code"]["after"] == code.value


@pytest.mark.parametrize(
    "pages",
    [
        (text_page(1, ""), text_page(2, "   ")),
        (ocr_page(1, "texto ruim de portaria da banca com varias palavras", "40"),),
        (),
    ],
)
def test_empty_or_illegible_text_is_falhou_texto_ilegivel_and_the_ai_is_not_called(docs, pages):
    ai = FakeOrdinanceExtractor(ANSWER)

    ordinance = read(docs, ai, pages)

    assert ordinance.reading_state is ReadingState.FALHOU
    assert ordinance.reading_code is OrdinanceReadingCode.TEXTO_ILEGIVEL
    assert ai.received == []


def test_an_unexpected_exception_is_falhou_erro_interno_and_the_log_has_only_its_type(
    docs, caplog
):
    caplog.set_level(logging.DEBUG)
    ai = FakeOrdinanceExtractor(error=RuntimeError("Maria Aparecida Souza 123.456.789-09"))

    ordinance = read(docs, ai)

    assert ordinance.reading_state is ReadingState.FALHOU
    assert ordinance.reading_code is OrdinanceReadingCode.ERRO_INTERNO
    assert "RuntimeError" in caplog.text
    assert "Maria" not in caplog.text and "123.456" not in caplog.text


# --- the queue --------------------------------------------------------------------------------


def test_run_next_without_a_pending_ordinance_returns_false_and_changes_nothing(docs):
    ai = FakeOrdinanceExtractor(ANSWER)

    assert reader(docs, ai).run_next() is False

    assert ai.received == []
    assert stored_board(docs.world) is None


def test_run_next_takes_the_oldest_pending_ordinance_first(docs):
    world = docs.world
    queue(docs, world.ifch_process)
    docs.clock.advance(minutes=1)
    queue(docs, world.process)
    runner = reader(docs, FakeOrdinanceExtractor(ANSWER))

    assert runner.run_next() is True

    assert stored_board(world, world.ifch_process).reading_state is ReadingState.LIDA
    assert stored_board(world, world.process).reading_state is ReadingState.PENDENTE
    assert runner.run_next() is True
    assert stored_board(world, world.process).reading_state is ReadingState.LIDA
    assert runner.run_next() is False


# --- restart during the reading ---------------------------------------------------------------


def test_recovering_closes_a_lendo_as_interrompida_audits_without_user_and_keeps_the_queue(docs):
    world = docs.world
    queue(docs, world.ifch_process)
    docs.clock.advance(minutes=1)
    queue(docs, world.process)
    with world.uow_factory() as uow:
        assert uow.board.claim_next_pending(docs.clock.now()) is not None  # the ifch one
        uow.commit()
    runner = reader(docs, FakeOrdinanceExtractor(ANSWER))

    assert runner.recover_interrupted() == 1

    interrupted = stored_board(world, world.ifch_process)
    assert interrupted.reading_state is ReadingState.FALHOU
    assert interrupted.reading_code is OrdinanceReadingCode.INTERROMPIDA
    assert stored_board(world, world.process).reading_state is ReadingState.PENDENTE
    [event] = board_events(world, world.ifch_process)[-1:]
    assert event.user_id is None
    assert event.action is AuditAction.STATUS
    assert event.changes["reading_state"] == {"before": "LENDO", "after": "FALHOU"}
    assert event.changes["reading_code"]["after"] == "INTERROMPIDA"


def test_recovering_twice_changes_nothing_the_second_time(docs):
    world = docs.world
    queue(docs)
    set_reading_state(world, ReadingState.LENDO)
    runner = reader(docs, FakeOrdinanceExtractor(ANSWER))
    assert runner.recover_interrupted() == 1
    events_after_first = len(board_events(world))
    state = stored_board(world)

    assert runner.recover_interrupted() == 0

    assert len(board_events(world)) == events_after_first
    assert stored_board(world) == state
