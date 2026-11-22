"""PORT-01, PORT-02, PAR-12, BNAV-03: GetBoard and DownloadOrdinanceFile."""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.domain.entities.board import (
    BoardOpinion,
    OpinionConclusion,
    ReadingState,
    RequestSettings,
)
from app.domain.errors import Gone, NotFound
from tests.integration.doc_usecases.board_support import (
    MEMBERS,
    add_typed_ordinance,
    download_uc,
    get_board_uc,
    stored_board,
    upload_uc,
)
from tests.integration.doc_usecases.conclusion_support import add_all_ready
from tests.integration.doc_usecases.generation_support import add_activity
from tests.integration.doc_usecases.support import pdf

NOW = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)


def save_opinion(world, **fields) -> BoardOpinion:
    opinion = BoardOpinion(world.process.id, **fields)
    with world.uow_factory() as uow:
        saved = uow.opinions.create(opinion, world.docente.id, 0)
        uow.commit()
    return saved


def save_city(world, city) -> RequestSettings:
    with world.uow_factory() as uow:
        saved = uow.request_settings.create(RequestSettings(world.process.id, city), 0)
        uow.commit()
    return saved


def upload(world, docs, name="portaria.pdf"):
    return upload_uc(world, docs).execute(
        world.docente,
        world.process.id,
        docs.incoming(pdf("leitura"), name, "application/pdf"),
        0,
        False,
    )


# --- GetBoard ---------------------------------------------------------------------------------


def test_a_process_with_nothing_saved_reads_empty_entities_of_version_0(world):
    view = get_board_uc(world).execute(world.docente, world.process.id)

    assert view.ordinance.process_id == world.process.id
    assert view.ordinance.reading_state is ReadingState.SEM_ARQUIVO
    assert (view.ordinance.members, view.ordinance.file, view.ordinance.version) == ((), None, 0)
    assert view.ordinance.number is None and view.ordinance.ordinance_date is None
    assert view.opinion.conclusion is None
    assert (view.opinion.opinion_date, view.opinion.place, view.opinion.notes) == (None, None, None)
    assert view.opinion.version == 0
    assert (view.request_settings.city, view.request_settings.version) == (None, 0)


def test_the_read_never_fills_the_conclusion_even_with_the_table_ready_and_points_above(
    official_chosen,
):
    world = official_chosen
    add_activity(world)
    add_all_ready(world)

    view = get_board_uc(world).execute(world.docente, world.process.id)

    assert view.opinion.conclusion is None
    assert view.opinion.version == 0


def test_after_saving_the_three_the_read_returns_each_with_its_own_version(world):
    add_typed_ordinance(world)
    opinion = save_opinion(
        world,
        conclusion=OpinionConclusion.FAVORAVEL,
        opinion_date=date(2025, 4, 1),
        place="Belém",
        notes="Sem ressalvas.",
    )
    city = save_city(world, "Belém")

    view = get_board_uc(world).execute(world.docente, world.process.id)

    assert view.ordinance == stored_board(world)
    assert view.ordinance.members == MEMBERS and view.ordinance.version == 1
    assert view.opinion == opinion
    assert (view.opinion.conclusion, view.opinion.place, view.opinion.notes) == (
        OpinionConclusion.FAVORAVEL,
        "Belém",
        "Sem ressalvas.",
    )
    assert view.request_settings == city
    assert (view.request_settings.city, view.request_settings.version) == ("Belém", 1)


def test_a_read_writes_nothing(world):
    get_board_uc(world).execute(world.docente, world.process.id)

    assert stored_board(world) is None
    with world.uow_factory() as uow:
        assert uow.opinions.get(world.process.id) is None
        assert uow.request_settings.get(world.process.id) is None


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_a_read_without_access_is_not_found(world, who):
    with pytest.raises(NotFound):
        get_board_uc(world).execute(getattr(world, who), world.process.id)
    with pytest.raises(NotFound):
        get_board_uc(world).execute(world.docente, uuid.uuid4())


def test_the_secretariat_of_the_unit_and_the_admin_can_read(world):
    for actor in (world.secretaria, world.admin):
        assert get_board_uc(world).execute(actor, world.process.id).ordinance.version == 0


# --- DownloadOrdinanceFile --------------------------------------------------------------------


def test_the_file_downloads_with_its_type_and_display_name(docs):
    world = docs.world
    uploaded = upload(world, docs, "portaria-da-banca.pdf")

    download = download_uc(world, docs).execute(world.docente, world.process.id)

    assert download.path == docs.storage.path(world.process.id, uploaded.file.internal_name)
    assert download.path.read_bytes() == pdf("leitura")
    assert download.name == "portaria-da-banca.pdf"
    assert download.mime == "application/pdf"


def test_without_a_file_the_download_is_not_found(docs):
    world = docs.world

    with pytest.raises(NotFound):
        download_uc(world, docs).execute(world.docente, world.process.id)
    add_typed_ordinance(world)
    with pytest.raises(NotFound):
        download_uc(world, docs).execute(world.docente, world.process.id)


def test_a_file_missing_from_the_disk_is_not_found(docs):
    world = docs.world
    uploaded = upload(world, docs)
    docs.storage.delete(world.process.id, uploaded.file.internal_name)

    with pytest.raises(NotFound):
        download_uc(world, docs).execute(world.docente, world.process.id)


def test_the_file_the_conclusion_removed_is_gone_but_the_data_stay_in_the_read(docs):
    world = docs.world
    uploaded = upload(world, docs)
    docs.storage.delete(world.process.id, uploaded.file.internal_name)
    with world.uow_factory() as uow:
        uow.board.mark_file_deleted(world.process.id, NOW)
        uow.commit()

    with pytest.raises(Gone) as raised:
        download_uc(world, docs).execute(world.docente, world.process.id)
    view = get_board_uc(world).execute(world.docente, world.process.id)

    assert raised.value.code == "ARQUIVO_EXCLUIDO"
    assert view.ordinance.file.deleted_at == NOW
    assert view.ordinance.reading_state is ReadingState.PENDENTE


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_the_download_without_access_is_not_found(docs, who):
    world = docs.world
    upload(world, docs)

    with pytest.raises(NotFound):
        download_uc(world, docs).execute(getattr(world, who), world.process.id)
