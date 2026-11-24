"""The text of the Parecer, after the official model (PMOD-01 to PMOD-19).

Pure function of the process, the professor, the unit, the ordinance and the fields the person
filled. The conclusion is the person's choice and its absence stops the document (PMOD-11);
nothing here reads the clock or calls the AI (PMOD-25). The writers (DOCX, PDF) only draw this
model.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.entities.academic_unit import AcademicUnit, UnitKind
from app.domain.entities.board import (
    BoardMember,
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
)
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.report import PageSetup
from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import (
    format_interstice,
    format_long_date,
    format_place_date,
    to_roman,
)
from app.domain.rules.spelled_numbers import spell_number

BLANK_TEXT = "__________"
_BLANK_PARAGRAPH_DATE = "______ dias do mês de ________ de ________"
_BLANK_LINE_DATE = "____ de ________ de ________"
_UNIVERSITY = "Universidade Federal do Pará"
_FIRST_YEAR_IN_WORDS, _LAST_YEAR_IN_WORDS = 1000, 2999


@dataclass(frozen=True)
class TextRun:
    """A stretch of the paragraph with one weight."""

    text: str
    bold: bool = False


@dataclass(frozen=True)
class OpinionDocument:
    page: PageSetup
    header_lines: tuple[str, ...]
    title: str
    place_date_line: str
    paragraph: tuple[TextRun, ...]
    member_lines: tuple[str, ...]


def _header(unit: AcademicUnit, parent_unit: AcademicUnit | None) -> tuple[str, ...]:
    """The campus line only when the parent of the unit is a campus (PMOD-02, PMOD-03)."""
    campus = (parent_unit.name,) if parent_unit and parent_unit.kind is UnitKind.CAMPUS else ()
    return (_UNIVERSITY, *campus, f"{unit.name} – {unit.acronym}")


def _level(number: int) -> str:
    """Roman numeral, or the number as typed when it has none (PMOD-12)."""
    return to_roman(number) if 1 <= number <= 3999 else str(number)


def _year(value: int) -> str:
    in_words = _FIRST_YEAR_IN_WORDS <= value <= _LAST_YEAR_IN_WORDS
    return spell_number(value) if in_words else str(value)


def _paragraph_date(opinion_date: date | None) -> tuple[str, str]:
    """The article before the date and the bold date words (PMOD-07 to PMOD-09, PMOD-16)."""
    if opinion_date is None:
        return "Aos ", _BLANK_PARAGRAPH_DATE
    month = format_long_date(opinion_date).split(" de ")[1]  # lowercase, no locale
    year = _year(opinion_date.year)
    if opinion_date.day == 1:
        return "Ao ", f"primeiro dia do mês de {month} de {year}"
    return "Aos ", f"{spell_number(opinion_date.day)} dias do mês de {month} de {year}"


def _place_date_line(opinion: BoardOpinion) -> str:
    place = (opinion.place or "").strip() or BLANK_TEXT
    when = format_place_date(opinion.opinion_date) if opinion.opinion_date else _BLANK_LINE_DATE
    return f"{place}, {when}."


def _titular_members(ordinance: BoardOrdinance) -> tuple[list[BoardMember], list[BoardMember]]:
    """The presidents and the members, each in the order of the ordinance; alternates are left
    out (PMOD-13)."""
    presidents = [m for m in ordinance.members if m.role is BoardRole.PRESIDENTE]
    members = [m for m in ordinance.members if m.role is BoardRole.MEMBRO]
    return presidents, members


def _member_lines(presidents: list[BoardMember], members: list[BoardMember]) -> tuple[str, ...]:
    return (
        *(f"PRESIDENTE: {m.name}" for m in presidents),
        *(f"MEMBRO {n}: {m.name}" for n, m in enumerate(members, start=1)),
    )


def build_opinion(
    process: FunctionalProcess,
    professor: Professor,
    unit: AcademicUnit,
    parent_unit: AcademicUnit | None,
    ordinance: BoardOrdinance,
    opinion: BoardOpinion,
    page: PageSetup,
) -> OpinionDocument:
    """Without a conclusion there is no Parecer: `ValueError` (PMOD-11). The six fields of the
    process are copied as typed (NMOV-01); only the levels become Roman numerals."""
    if opinion.conclusion is None:
        raise ValueError("the Parecer needs the conclusion chosen by a person")
    decision = "APROVARAM" if opinion.conclusion is OpinionConclusion.FAVORAVEL else "NÃO APROVARAM"
    presidents, members = _titular_members(ordinance)
    names = "".join(f"{m.name} (presidente), " for m in presidents) + "".join(
        f"{m.name}, " for m in members
    )
    number = (ordinance.number or "").strip() or BLANK_TEXT
    opening, date_words = _paragraph_date(opinion.opinion_date)
    interstice = format_interstice(Interstice(process.start_date, process.end_date))
    paragraph = (
        TextRun(opening),
        TextRun(date_words, bold=True),
        TextRun(
            ", reuniram-se os membros da Banca de Análise, nomeados pela Portaria nº "
            f"{number}, {names}responsáveis por analisar o Relatório de Atividades do "
            "Professor "
        ),
        TextRun(
            f"{process.current_denomination} Nível {_level(process.current_level)} "
            f"{professor.full_name}",
            bold=True,
        ),
        TextRun(
            ", para fins de progressão funcional do docente, referente ao interstício de "
            f"{interstice}, para Classe {process.target_class} ({process.target_denomination}) "
            f"Nível {_level(process.target_level)}. Após a análise, os membros {decision} o "
            "referido relatório."
        ),
    )
    return OpinionDocument(
        page=page,
        header_lines=_header(unit, parent_unit),
        title="PARECER",
        place_date_line=_place_date_line(opinion),
        paragraph=paragraph,
        member_lines=_member_lines(presidents, members),
    )
