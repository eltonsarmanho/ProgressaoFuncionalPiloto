"""Builders for the Parecer and Requerimento generation tests: the fields of the board saved
straight in the database, a Tabela made ready by the run or crafted by hand. Synthetic data only."""

import uuid
from datetime import date

import httpx
import pytest

from app.domain.entities.board import BoardOpinion, OpinionConclusion, RequestSettings
from app.domain.entities.generated import (
    DocumentKind,
    GeneratedDocument,
    GenerationState,
)
from app.infrastructure.ai.maritalk import MariTalkClient
from tests.integration.doc_usecases.generation_support import add_activity


def add_opinion(
    world,
    conclusion=OpinionConclusion.FAVORAVEL,
    when=date(2025, 4, 2),
    place="Belém",
    notes="Sem observações adicionais.",
) -> BoardOpinion:
    with world.uow_factory() as uow:
        saved = uow.opinions.create(
            BoardOpinion(world.process.id, conclusion, when, place, notes), world.admin.id, 0
        )
        uow.commit()
    return saved


def add_city(world, city="Belém") -> RequestSettings:
    with world.uow_factory() as uow:
        saved = uow.request_settings.create(RequestSettings(world.process.id, city), 0)
        uow.commit()
    return saved


def ask(gen, kind, actor=None, process=None):
    world = gen.world
    return gen.request().execute(actor or world.admin, (process or world.process).id, kind)


def run_one(gen, **overrides):
    assert gen.run(**overrides).run_next() is True


def ready(gen, kind):
    """Asks for a version of `kind`, runs it and returns the stored row."""
    requested = ask(gen, kind)
    run_one(gen)
    with gen.world.uow_factory() as uow:
        return uow.generations.get(requested.id)


def ready_table(gen):
    """A validated activity and a real Tabela `PRONTO` made from it by the run."""
    add_activity(gen.world)
    return ready(gen, DocumentKind.TABELA)


def craft_ready_table(world, clock, snapshot) -> GeneratedDocument:
    """A Tabela `PRONTO` with the given snapshot and no file, for the cases a real run cannot
    produce (a total of zero with no activity, a table version that is not the chosen one)."""
    row = GeneratedDocument(
        id=uuid.uuid4(),
        process_id=world.process.id,
        kind=DocumentKind.TABELA,
        state=GenerationState.GERANDO,
        version_number=None,
        requested_by=world.admin.id,
        requested_at=clock.now(),
    )
    with world.uow_factory() as uow:
        uow.generations.add(row)
        claimed = uow.generations.claim_next(clock.now())
        assert claimed.id == row.id
        done = uow.generations.finish_ready(row.id, clock.now(), [], snapshot, [])
        uow.commit()
    assert done.state is GenerationState.PRONTO
    return done


@pytest.fixture
def no_ai(monkeypatch):
    """Breaks every way out to the AI during a test and records the attempts: the MariTalk client
    and the HTTP client under it. The Parecer and the Requerimento must leave `calls` empty."""
    calls: list[str] = []

    def refuse(name):
        def guard(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"the AI was called: {name}")

        return guard

    monkeypatch.setattr(MariTalkClient, "chat", refuse("MariTalkClient.chat"))
    monkeypatch.setattr(httpx.Client, "send", refuse("httpx.Client.send"))
    monkeypatch.setattr(httpx.AsyncClient, "send", refuse("httpx.AsyncClient.send"))
    return calls
