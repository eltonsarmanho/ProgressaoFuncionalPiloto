"""Grounding of the ordinance read by the AI: a value stays only if its page proves it (PORT-03).

All checks run against the ORIGINAL page text (AD-009). A value without origin becomes empty with
a VALOR_SEM_ORIGEM warning on its field; a list without members gets MEMBROS_NAO_ENCONTRADOS.
What the person typed (`INFORMADO`) is never overwritten by a reading (regra 1).
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date

from app.domain.entities.board import (
    BoardMember,
    BoardOrdinance,
    BoardRole,
    OrdinanceWarning,
    OrdinanceWarningCode,
    ValueSource,
)
from app.domain.rules.grounding import date_in_text, identifier_in_text, name_in_text

NUMBER, DATE, MEMBERS = "number", "ordinance_date", "members"


@dataclass(frozen=True)
class OrdinanceAiMember:
    name: str
    role: str
    page: int


@dataclass(frozen=True)
class OrdinanceAi:
    """What the AI returned: untrusted until `ground_ordinance` checks it."""

    number: str | None = None
    number_page: int | None = None
    ordinance_date: date | None = None
    date_page: int | None = None
    members: tuple[OrdinanceAiMember, ...] = ()


@dataclass(frozen=True)
class GroundedOrdinance:
    """The values that passed the check; every one of them is `EXTRAIDO`."""

    number: str | None = None
    number_page: int | None = None
    ordinance_date: date | None = None
    date_page: int | None = None
    members: tuple[BoardMember, ...] = ()
    warnings: tuple[OrdinanceWarning, ...] = ()


def _role(text: str) -> BoardRole | None:
    try:
        return BoardRole(text.strip().upper())
    except ValueError:
        return None


def ground_ordinance(ai: OrdinanceAi, pages: Mapping[int, str]) -> GroundedOrdinance:
    warnings: list[OrdinanceWarning] = []
    no_origin = OrdinanceWarningCode.VALOR_SEM_ORIGEM

    number = page = None
    if ai.number is not None:
        if ai.number_page is not None and identifier_in_text(
            ai.number, pages.get(ai.number_page, "")
        ):
            number, page = ai.number, ai.number_page
        else:
            warnings.append(OrdinanceWarning(no_origin, NUMBER))

    found_date = date_page = None
    if ai.ordinance_date is not None:
        if ai.date_page is not None and date_in_text(
            ai.ordinance_date, pages.get(ai.date_page, "")
        ):
            found_date, date_page = ai.ordinance_date, ai.date_page
        else:
            warnings.append(OrdinanceWarning(no_origin, DATE))

    members: list[BoardMember] = []
    for listed in ai.members:
        role = _role(listed.role)
        if role is None or not name_in_text(listed.name, pages.get(listed.page, "")):
            warnings.append(OrdinanceWarning(no_origin, MEMBERS))
            continue
        members.append(BoardMember(listed.name.strip(), role, listed.page, ValueSource.EXTRAIDO))
    if not members:
        warnings.append(OrdinanceWarning(OrdinanceWarningCode.MEMBROS_NAO_ENCONTRADOS, MEMBERS))

    return GroundedOrdinance(
        number=number,
        number_page=page,
        ordinance_date=found_date,
        date_page=date_page,
        members=tuple(members),
        warnings=tuple(warnings),
    )


def merge_reading(current: BoardOrdinance, grounded: GroundedOrdinance) -> BoardOrdinance:
    """The reading fills what is empty or was extracted; what the person typed stays.

    The member list is one field: a single typed member keeps the whole saved list. The warnings
    of a field that was kept are dropped, since they describe a value that is not there.
    """
    kept: set[str] = set()
    merged = replace(current)

    if current.number_source is ValueSource.INFORMADO:
        kept.add(NUMBER)
    else:
        merged.number, merged.number_page = grounded.number, grounded.number_page
        merged.number_source = ValueSource.EXTRAIDO if grounded.number is not None else None

    if current.date_source is ValueSource.INFORMADO:
        kept.add(DATE)
    else:
        merged.ordinance_date, merged.date_page = grounded.ordinance_date, grounded.date_page
        merged.date_source = ValueSource.EXTRAIDO if grounded.ordinance_date is not None else None

    if any(m.source is ValueSource.INFORMADO for m in current.members):
        kept.add(MEMBERS)
    else:
        merged.members = grounded.members

    merged.warnings = tuple(w for w in grounded.warnings if w.field not in kept)
    return merged
