"""Limits of the board data, of the opinion fields and of the city (PORT-11, PMOD-29, REQ-05).

Pure: empty values are valid here, because the person may save before filling everything.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.entities.board import BoardMember
from app.domain.rules.norm_rules import FieldError
from app.domain.rules.scoring_periods import normalize_title

MAX_MEMBERS = 15
MAX_MEMBER_NAME = 200
MAX_NUMBER = 50
MAX_PLACE = 100
MAX_CITY = 100

REPEATED_MEMBER = "MEMBRO_REPETIDO"


@dataclass(frozen=True)
class BoardFieldError(FieldError):
    code: str | None = None


def validate_board_data(
    number: str | None, members: Sequence[BoardMember]
) -> list[BoardFieldError]:
    errors: list[BoardFieldError] = []
    if number is not None and len(number.strip()) > MAX_NUMBER:
        errors.append(BoardFieldError("number", f"Número deve ter até {MAX_NUMBER} caracteres"))
    if len(members) > MAX_MEMBERS:
        errors.append(BoardFieldError("members", f"A banca deve ter até {MAX_MEMBERS} membros"))
    seen: set[str] = set()
    for index, member in enumerate(members):
        field = f"members[{index}].name"
        name = member.name.strip()
        if not name:
            errors.append(BoardFieldError(field, "Nome do membro é obrigatório"))
        elif len(name) > MAX_MEMBER_NAME:
            errors.append(BoardFieldError(field, f"Nome deve ter até {MAX_MEMBER_NAME} caracteres"))
        elif (key := normalize_title(name)) in seen:
            errors.append(BoardFieldError(field, "Membro repetido na lista", code=REPEATED_MEMBER))
        else:
            seen.add(key)
    return errors


def validate_opinion_fields(place: str | None) -> list[BoardFieldError]:
    if place is not None and len(place.strip()) > MAX_PLACE:
        return [BoardFieldError("place", f"Local deve ter até {MAX_PLACE} caracteres")]
    return []


def validate_city(city: str | None) -> list[BoardFieldError]:
    if city is not None and len(city.strip()) > MAX_CITY:
        return [BoardFieldError("city", f"Cidade deve ter até {MAX_CITY} caracteres")]
    return []
