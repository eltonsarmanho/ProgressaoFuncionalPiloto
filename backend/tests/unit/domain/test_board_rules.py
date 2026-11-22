"""PORT-11, PAR-13, REQ-05 and the MEMBRO_REPETIDO edge case: limits of the board data."""

from app.domain.entities.board import BoardMember, BoardRole, ValueSource
from app.domain.rules.board_rules import (
    BoardFieldError,
    validate_board_data,
    validate_city,
    validate_opinion_fields,
)


def member(name: str, role: BoardRole = BoardRole.MEMBRO) -> BoardMember:
    return BoardMember(name, role, None, ValueSource.INFORMADO)


def members(count: int) -> list[BoardMember]:
    return [member(f"Pessoa Numero{i}") for i in range(count)]


def fields(errors: list[BoardFieldError]) -> list[str]:
    return [e.field for e in errors]


def test_fifteen_members_pass():
    assert validate_board_data("123/2025", members(15)) == []


def test_sixteen_members_are_an_error_on_the_members_field():
    assert fields(validate_board_data("123/2025", members(16))) == ["members"]


def test_an_empty_list_of_members_passes_so_the_person_can_save_without_members():
    assert validate_board_data("123/2025", []) == []


def test_a_member_with_an_empty_name_is_an_error_on_its_own_field():
    listed = [member("Ana Lima"), member("Bia Lima"), member("")]

    assert fields(validate_board_data(None, listed)) == ["members[2].name"]


def test_a_member_with_only_spaces_in_the_name_is_an_error():
    assert fields(validate_board_data(None, [member("   ")])) == ["members[0].name"]


def test_a_name_with_200_characters_passes_and_with_201_is_an_error():
    listed = [member("Ana Lima"), member("Bia Lima"), member("a" * 200)]
    assert validate_board_data(None, listed) == []

    too_long = [member("Ana Lima"), member("Bia Lima"), member("a" * 201)]
    assert fields(validate_board_data(None, too_long)) == ["members[2].name"]


def test_a_number_with_50_characters_passes_and_with_51_is_an_error():
    assert validate_board_data("1" * 50, []) == []
    assert fields(validate_board_data("1" * 51, [])) == ["number"]


def test_the_same_name_without_case_or_accents_is_repeated_at_the_second_index():
    listed = [member("José da Silva"), member("Ana Lima"), member("JOSE DA SILVA")]

    errors = validate_board_data(None, listed)

    assert [(e.field, e.code) for e in errors] == [("members[2].name", "MEMBRO_REPETIDO")]


def test_the_same_name_with_different_roles_is_also_repeated():
    listed = [
        member("José da Silva", BoardRole.PRESIDENTE),
        member("jose da silva", BoardRole.SUPLENTE),
    ]

    errors = validate_board_data(None, listed)

    assert [(e.field, e.code) for e in errors] == [("members[1].name", "MEMBRO_REPETIDO")]


def test_an_error_that_is_not_a_repetition_has_no_code():
    errors = validate_board_data("1" * 51, [])

    assert errors[0].code is None
    assert errors[0].message


def test_notes_with_5000_characters_pass_and_with_5001_are_an_error():
    assert validate_opinion_fields(None, "n" * 5000) == []
    assert fields(validate_opinion_fields(None, "n" * 5001)) == ["notes"]


def test_a_place_with_100_characters_passes_and_with_101_is_an_error():
    assert validate_opinion_fields("p" * 100, None) == []
    assert fields(validate_opinion_fields("p" * 101, None)) == ["place"]


def test_both_opinion_fields_are_checked_together():
    assert fields(validate_opinion_fields("p" * 101, "n" * 5001)) == ["place", "notes"]


def test_a_city_with_100_characters_passes_and_with_101_is_an_error():
    assert validate_city("c" * 100) == []
    assert fields(validate_city("c" * 101)) == ["city"]
