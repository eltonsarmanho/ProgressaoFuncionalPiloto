"""PORT-03, PORT-05, PORT-06, PORT-11, PORT-12, BNAV-02, BNAV-03: SaveOrdinanceData."""

import json
from datetime import date

import pytest

from app.application.use_cases.board import MemberInput
from app.domain.entities.audit import AuditAction
from app.domain.entities.board import (
    BoardRole,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ReadingState,
    ValueSource,
)
from app.domain.entities.process import ProcessStatus
from app.domain.errors import Conflict, NotFound, StaleVersion, ValidationFailed
from app.domain.rules.ordinance_grounding import GroundedOrdinance, merge_reading
from tests.integration.doc_usecases.board_support import (
    MEMBERS,
    add_typed_ordinance,
    board_events,
    save_data_uc,
    stored_board,
    upload_uc,
)
from tests.integration.doc_usecases.draft_support import set_status
from tests.integration.doc_usecases.support import pdf

DATE = date(2025, 3, 10)


def inputs(members=MEMBERS):
    return [MemberInput(m.name, m.role) for m in members]


def save(world, number="77/2025", when=DATE, members=None, version=1, actor=None):
    return save_data_uc(world).execute(
        actor or world.docente,
        world.process.id,
        number,
        when,
        inputs() if members is None else members,
        version,
    )


def read_ordinance(world):
    """An ordinance as a finished reading leaves it: everything extracted, with its pages."""
    return add_typed_ordinance(
        world,
        number_source=ValueSource.EXTRAIDO,
        number_page=1,
        date_source=ValueSource.EXTRAIDO,
        date_page=1,
    )


# --- what the person changed is INFORMADO, the rest keeps origin and page --------------------


def test_correcting_one_name_marks_only_that_member_as_typed_and_keeps_the_others(world):
    stored = read_ordinance(world)
    corrected = inputs()
    corrected[1] = MemberInput("Bruno Membro Lima Filho", BoardRole.MEMBRO)

    saved = save(world, members=corrected, version=stored.version)

    assert saved == stored_board(world)
    first, second, third = saved.members
    assert (first.name, first.page, first.source) == (
        "Ana Presidente Souza",
        1,
        ValueSource.EXTRAIDO,
    )
    assert (second.name, second.role, second.page, second.source) == (
        "Bruno Membro Lima Filho",
        BoardRole.MEMBRO,
        None,
        ValueSource.INFORMADO,
    )
    assert (third.name, third.page, third.source) == (
        "Carla Suplente Reis",
        2,
        ValueSource.EXTRAIDO,
    )
    assert (saved.number_source, saved.number_page) == (ValueSource.EXTRAIDO, 1)
    assert (saved.date_source, saved.date_page) == (ValueSource.EXTRAIDO, 1)
    assert saved.version == stored.version + 1


def test_a_member_moved_in_the_list_keeps_its_page_and_origin_and_a_new_one_is_typed(world):
    stored = read_ordinance(world)
    reordered = [*reversed(inputs()), MemberInput("Daniel Novo Alves", BoardRole.SUPLENTE)]

    saved = save(world, members=reordered, version=stored.version)

    assert [(m.name, m.page, m.source) for m in saved.members] == [
        ("Carla Suplente Reis", 2, ValueSource.EXTRAIDO),
        ("Bruno Membro Lima", 1, ValueSource.EXTRAIDO),
        ("Ana Presidente Souza", 1, ValueSource.EXTRAIDO),
        ("Daniel Novo Alves", None, ValueSource.INFORMADO),
    ]


def test_editing_the_number_marks_only_the_number_as_typed(world):
    stored = read_ordinance(world)

    saved = save(world, number="78/2025", version=stored.version)

    assert (saved.number, saved.number_source, saved.number_page) == (
        "78/2025",
        ValueSource.INFORMADO,
        None,
    )
    assert (saved.ordinance_date, saved.date_source, saved.date_page) == (
        DATE,
        ValueSource.EXTRAIDO,
        1,
    )
    assert saved.members == stored.members


def test_clearing_the_date_leaves_it_empty_and_typed_and_a_new_reading_does_not_revive_it(world):
    stored = read_ordinance(world)

    saved = save(world, when=None, version=stored.version)

    assert (saved.ordinance_date, saved.date_source, saved.date_page) == (
        None,
        ValueSource.INFORMADO,
        None,
    )
    reread = merge_reading(saved, GroundedOrdinance(ordinance_date=DATE, date_page=1))
    assert reread.ordinance_date is None and reread.date_source is ValueSource.INFORMADO


def test_a_save_keeps_the_file_and_the_state_of_the_reading(docs):
    world = docs.world
    file = docs.incoming(pdf("com-arquivo"), "p.pdf", "application/pdf")
    uploaded = upload_uc(world, docs).execute(world.docente, world.process.id, file, 0, False)

    saved = save(world, version=uploaded.version)

    assert saved.file == uploaded.file
    assert saved.reading_state is ReadingState.PENDENTE


def test_editing_a_field_drops_the_warning_about_its_missing_origin(world):
    warned = add_typed_ordinance(
        world,
        number=None,
        number_source=None,
        warnings=(
            OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "number"),
            OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "ordinance_date"),
        ),
    )

    saved = save(world, number="79/2025", when=DATE, version=warned.version)

    assert saved.warnings == (
        OrdinanceWarning(OrdinanceWarningCode.VALOR_SEM_ORIGEM, "ordinance_date"),
    )


# --- PORT-06: typed data without a file -------------------------------------------------------


def test_saving_without_a_file_creates_the_ordinance_with_everything_typed(world):
    saved = save(world, version=0)

    assert saved.version == 1
    assert saved.reading_state is ReadingState.SEM_ARQUIVO
    assert saved.file is None
    assert (saved.number, saved.number_source, saved.number_page) == (
        "77/2025",
        ValueSource.INFORMADO,
        None,
    )
    assert (saved.ordinance_date, saved.date_source, saved.date_page) == (
        DATE,
        ValueSource.INFORMADO,
        None,
    )
    assert [(m.name, m.role, m.page, m.source) for m in saved.members] == [
        (m.name, m.role, None, ValueSource.INFORMADO) for m in MEMBERS
    ]
    assert saved.is_registered
    assert stored_board(world) == saved


def test_a_first_save_with_an_empty_number_and_date_leaves_them_open_for_a_later_reading(world):
    saved = save(world, number=None, when=None, version=0)

    assert (saved.number, saved.number_source) == (None, None)
    assert (saved.ordinance_date, saved.date_source) == (None, None)


# --- PORT-05: the audit -----------------------------------------------------------------------


def test_the_audit_has_the_number_the_date_the_counts_and_the_fields_but_no_name_or_justification(
    world,
):
    stored = read_ordinance(world)

    save(world, number="78/2025", version=stored.version)

    event = board_events(world)[-1]
    assert event.action is AuditAction.UPDATE
    assert event.user_id == world.docente.id
    assert event.justification is None
    assert event.changes["number"] == {"before": "77/2025", "after": "78/2025"}
    assert event.changes["operation"]["after"] == "SAVE"
    assert event.changes["fields_changed"]["after"] == ["number"]
    assert "ordinance_date" not in event.changes  # untouched
    everything = json.dumps(event.changes, ensure_ascii=False)
    assert not any(member.name in everything for member in MEMBERS)


def test_changing_the_members_is_audited_with_the_counts_only(world):
    stored = read_ordinance(world)

    save(world, members=inputs()[:2], version=stored.version)

    event = board_events(world)[-1]
    assert event.changes["member_count"] == {"before": 3, "after": 2}
    assert event.changes["fields_changed"]["after"] == ["members"]
    assert not any(member.name in json.dumps(event.changes) for member in MEMBERS)


# --- PORT-11: limits --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "members", "field"),
    [
        (None, [MemberInput(f"Membro Numero {i}", BoardRole.MEMBRO) for i in range(16)], "members"),
        (None, [MemberInput("", BoardRole.MEMBRO)], "members[0].name"),
        (
            None,
            [MemberInput("Ana Souza", BoardRole.MEMBRO), MemberInput("N" * 201, BoardRole.MEMBRO)],
            "members[1].name",
        ),
        ("1" * 51, [], "number"),
    ],
)
def test_the_limits_of_the_data_are_a_422_on_the_field_and_nothing_is_stored(
    world, number, members, field
):
    with pytest.raises(ValidationFailed) as raised:
        save(world, number=number, members=members, version=0)

    assert raised.value.field == field
    assert stored_board(world) is None


def test_the_edge_values_are_saved(world):
    members = [MemberInput(f"Membro {i} " + "N" * 190, BoardRole.MEMBRO) for i in range(15)]
    members[0] = MemberInput("N" * 200, BoardRole.PRESIDENTE)

    saved = save(world, number="1" * 50, members=members, version=0)

    assert len(saved.members) == 15
    assert saved.number == "1" * 50


def test_the_same_member_twice_is_a_422_with_membro_repetido(world):
    twice = [
        MemberInput("José da Silva", BoardRole.PRESIDENTE),
        MemberInput("JOSE DA SILVA", BoardRole.SUPLENTE),
    ]

    with pytest.raises(ValidationFailed) as raised:
        save(world, members=twice, version=0)

    assert raised.value.code == "MEMBRO_REPETIDO"
    assert raised.value.field == "members[1].name"
    assert stored_board(world) is None


# --- PORT-12: versions ------------------------------------------------------------------------


def test_two_saves_from_the_same_version_the_first_wins_and_the_second_is_a_409(world):
    stored = read_ordinance(world)
    first = save(world, number="1/2025", version=stored.version)

    with pytest.raises(StaleVersion) as raised:
        save(world, number="2/2025", version=stored.version)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_board(world) == first
    assert first.number == "1/2025"


@pytest.mark.parametrize("sent", [0, 5])
def test_a_save_with_a_version_that_is_not_the_stored_one_is_stale(world, sent):
    stored = add_typed_ordinance(world)

    with pytest.raises(StaleVersion) as raised:
        save(world, number="3/2025", version=sent)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_board(world) == stored


def test_a_first_save_that_expects_a_version_above_zero_is_stale(world):
    with pytest.raises(StaleVersion) as raised:
        save(world, version=1)

    assert raised.value.code == "VERSAO_DESATUALIZADA"
    assert stored_board(world) is None


# --- BNAV-02, BNAV-03 -------------------------------------------------------------------------


@pytest.mark.parametrize("status", [ProcessStatus.CONCLUIDO, ProcessStatus.ARQUIVADO])
def test_a_closed_process_refuses_the_save_with_409(world, status):
    set_status(world, status)

    with pytest.raises(Conflict) as raised:
        save(world, version=0)

    assert raised.value.code == "PROCESSO_SOMENTE_LEITURA"
    assert stored_board(world) is None


@pytest.mark.parametrize("who", ["other_docente", "other_secretaria"])
def test_someone_without_access_gets_not_found(world, who):
    with pytest.raises(NotFound):
        save(world, version=0, actor=getattr(world, who))

    assert stored_board(world) is None
