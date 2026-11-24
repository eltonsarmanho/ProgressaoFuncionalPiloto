"""PORT-02, PORT-03, MEMBROS_NAO_ENCONTRADOS: the reading is checked in the cited page."""

from datetime import date
from uuid import uuid4

from app.domain.entities.board import (
    BoardMember,
    BoardOrdinance,
    BoardRole,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ValueSource,
)
from app.domain.rules.ordinance_grounding import (
    GroundedOrdinance,
    OrdinanceAi,
    OrdinanceAiMember,
    ground_ordinance,
    merge_reading,
)

PAGE_ONE = (
    "PORTARIA Nº 123/2025 - FASI. Belém, 10 de março de 2025. "
    "Designa a banca. Presidente: Maria Aparecida SOUZA. Membro: José da Silva. "
    "Suplente: Ana Beatriz Lima."
)
PAGES = {1: PAGE_ONE, 2: "Outra página sem os dados. Portaria 999/2020. Carlos Pereira."}

NO_ORIGIN = OrdinanceWarningCode.VALOR_SEM_ORIGEM


def ai(**changes) -> OrdinanceAi:
    base = {
        "number": "123/2025",
        "number_page": 1,
        "ordinance_date": date(2025, 3, 10),
        "date_page": 1,
        "members": (
            OrdinanceAiMember("Maria Aparecida Souza", "PRESIDENTE", 1),
            OrdinanceAiMember("José da Silva", "MEMBRO", 1),
            OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 1),
        ),
    }
    return OrdinanceAi(**{**base, **changes})


def warnings_of(grounded: GroundedOrdinance) -> list[tuple[OrdinanceWarningCode, str]]:
    return [(w.code, w.field) for w in grounded.warnings]


def test_number_date_and_three_members_found_in_the_cited_page_keep_their_origin():
    grounded = ground_ordinance(ai(), PAGES)

    assert (grounded.number, grounded.number_page) == ("123/2025", 1)
    assert (grounded.ordinance_date, grounded.date_page) == (date(2025, 3, 10), 1)
    assert grounded.members == (
        BoardMember("Maria Aparecida Souza", BoardRole.PRESIDENTE, 1, ValueSource.EXTRAIDO),
        BoardMember("José da Silva", BoardRole.MEMBRO, 1, ValueSource.EXTRAIDO),
        BoardMember("Ana Beatriz Lima", BoardRole.SUPLENTE, 1, ValueSource.EXTRAIDO),
    )
    assert grounded.warnings == ()


def test_a_number_found_only_in_another_page_is_empty_with_a_warning_on_the_field():
    grounded = ground_ordinance(ai(number="999/2020", number_page=1), PAGES)

    assert grounded.number is None
    assert grounded.number_page is None
    assert (NO_ORIGIN, "number") in warnings_of(grounded)


def test_a_date_written_by_extension_or_in_digits_is_found():
    by_digits = {1: "Portaria 123/2025 de 10/03/2025. Presidente: Maria Souza."}

    assert ground_ordinance(ai(), PAGES).ordinance_date == date(2025, 3, 10)
    assert ground_ordinance(ai(), by_digits).ordinance_date == date(2025, 3, 10)


def test_a_date_that_is_not_in_the_cited_page_is_empty_with_a_warning():
    grounded = ground_ordinance(ai(ordinance_date=date(2025, 4, 11)), PAGES)

    assert grounded.ordinance_date is None
    assert grounded.date_page is None
    assert (NO_ORIGIN, "ordinance_date") in warnings_of(grounded)


def test_a_name_with_other_case_and_accents_is_found():
    listed = (OrdinanceAiMember("JOSE DA SILVA", "MEMBRO", 1),)

    grounded = ground_ordinance(ai(members=listed), PAGES)

    assert [m.name for m in grounded.members] == ["JOSE DA SILVA"]
    assert grounded.warnings == ()


def test_a_page_that_does_not_exist_gives_no_origin():
    for missing in (0, 99):
        grounded = ground_ordinance(
            ai(
                number_page=missing,
                date_page=missing,
                members=(OrdinanceAiMember("José da Silva", "MEMBRO", missing),),
            ),
            PAGES,
        )

        assert grounded.number is None
        assert grounded.ordinance_date is None
        assert grounded.members == ()


def test_a_member_whose_name_is_not_in_the_page_is_dropped_and_the_others_stay():
    listed = (
        OrdinanceAiMember("José da Silva", "MEMBRO", 1),
        OrdinanceAiMember("Fulano Inventado", "MEMBRO", 1),
        OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 1),
    )

    grounded = ground_ordinance(ai(members=listed), PAGES)

    assert [m.name for m in grounded.members] == ["José da Silva", "Ana Beatriz Lima"]
    assert warnings_of(grounded) == [(NO_ORIGIN, "members")]


def test_a_member_whose_name_is_only_in_another_page_is_dropped():
    listed = (OrdinanceAiMember("Carlos Pereira", "MEMBRO", 1),)

    grounded = ground_ordinance(ai(members=listed), PAGES)

    assert grounded.members == ()
    assert (NO_ORIGIN, "members") in warnings_of(grounded)


def test_a_role_out_of_the_three_drops_the_member_with_the_warning():
    listed = (
        OrdinanceAiMember("José da Silva", "SECRETARIO", 1),
        OrdinanceAiMember("Ana Beatriz Lima", "SUPLENTE", 1),
    )

    grounded = ground_ordinance(ai(members=listed), PAGES)

    assert [m.name for m in grounded.members] == ["Ana Beatriz Lima"]
    assert warnings_of(grounded) == [(NO_ORIGIN, "members")]


def test_no_member_at_all_leaves_an_empty_list_with_members_not_found():
    grounded = ground_ordinance(ai(members=()), PAGES)

    assert grounded.members == ()
    assert warnings_of(grounded) == [(OrdinanceWarningCode.MEMBROS_NAO_ENCONTRADOS, "members")]


def test_every_member_dropped_also_gives_members_not_found():
    listed = (OrdinanceAiMember("Fulano Inventado", "MEMBRO", 1),)

    grounded = ground_ordinance(ai(members=listed), PAGES)

    assert grounded.members == ()
    assert warnings_of(grounded) == [
        (NO_ORIGIN, "members"),
        (OrdinanceWarningCode.MEMBROS_NAO_ENCONTRADOS, "members"),
    ]


def test_a_value_the_ai_did_not_give_is_empty_without_a_warning():
    grounded = ground_ordinance(ai(number=None, number_page=None), PAGES)

    assert grounded.number is None
    assert grounded.warnings == ()


def current(**changes) -> BoardOrdinance:
    return BoardOrdinance(process_id=uuid4(), **changes)


def read() -> GroundedOrdinance:
    return ground_ordinance(ai(), PAGES)


def test_merge_keeps_the_number_the_person_typed_and_takes_the_rest():
    typed = current(number="777/2024", number_source=ValueSource.INFORMADO)

    merged = merge_reading(typed, read())

    assert (merged.number, merged.number_page, merged.number_source) == (
        "777/2024",
        None,
        ValueSource.INFORMADO,
    )
    assert merged.ordinance_date == date(2025, 3, 10)
    assert merged.date_source is ValueSource.EXTRAIDO
    assert len(merged.members) == 3


def test_merge_keeps_the_date_the_person_typed():
    typed = current(ordinance_date=date(2025, 1, 2), date_source=ValueSource.INFORMADO)

    merged = merge_reading(typed, read())

    assert (merged.ordinance_date, merged.date_source) == (date(2025, 1, 2), ValueSource.INFORMADO)
    assert (merged.number, merged.number_source) == ("123/2025", ValueSource.EXTRAIDO)


def test_merge_replaces_the_values_that_were_extracted_or_empty():
    old = current(
        number="old",
        number_page=3,
        number_source=ValueSource.EXTRAIDO,
        members=(BoardMember("Antigo Nome", BoardRole.MEMBRO, 3, ValueSource.EXTRAIDO),),
    )

    merged = merge_reading(old, read())

    assert (merged.number, merged.number_page) == ("123/2025", 1)
    assert [m.name for m in merged.members] == [
        "Maria Aparecida Souza",
        "José da Silva",
        "Ana Beatriz Lima",
    ]
    assert all(m.source is ValueSource.EXTRAIDO for m in merged.members)


def test_the_member_list_is_one_field_a_single_typed_member_keeps_the_whole_list():
    saved = (
        BoardMember("Pessoa Digitada", BoardRole.PRESIDENTE, None, ValueSource.INFORMADO),
        BoardMember("Pessoa Lida", BoardRole.MEMBRO, 2, ValueSource.EXTRAIDO),
    )

    merged = merge_reading(current(members=saved), read())

    assert merged.members == saved


def test_the_warnings_of_a_field_that_was_kept_are_dropped_and_the_other_warnings_stay():
    typed = current(number="777/2024", number_source=ValueSource.INFORMADO)
    grounded = ground_ordinance(ai(number="999/2020", ordinance_date=date(2025, 4, 11)), PAGES)

    merged = merge_reading(typed, grounded)

    assert merged.warnings == (OrdinanceWarning(NO_ORIGIN, "ordinance_date"),)


def test_merge_does_not_change_the_ordinance_it_received():
    typed = current(number="777/2024", number_source=ValueSource.INFORMADO)

    merge_reading(typed, read())

    assert typed.number == "777/2024"
    assert typed.members == ()
