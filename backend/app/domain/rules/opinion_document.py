"""The text of the Parecer (PAR-03 to PAR-06, PAR-11, PAR-12).

Pure function of the process, the ordinance, the fields the person filled and the snapshot of the
last Tabela. The points are copied from the snapshot, never summed again (PAR-04); the
conclusion is the person's choice and its absence stops the document (PAR-12); nothing here reads
the clock or calls the AI (PAR-11). The writers (DOCX, PDF) only draw this model.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.entities.academic_unit import AcademicUnit
from app.domain.entities.board import (
    BoardOpinion,
    BoardOrdinance,
    BoardRole,
    OpinionConclusion,
)
from app.domain.entities.career import Modality
from app.domain.entities.generated import DocumentKind
from app.domain.entities.process import FunctionalProcess
from app.domain.entities.professor import Professor
from app.domain.entities.report import PageSetup
from app.domain.rules.interstice import Interstice
from app.domain.rules.pt_format import format_date, format_interstice
from app.domain.rules.scoring_verification import MinimumComparison
from app.domain.rules.table_document import roman, two_places

BLANK_TEXT = "__________"
BLANK_DATE = "___/___/___"
NOT_GENERATED = "não gerado"
_HEADER = ("Serviço Público Federal", "Universidade Federal do Pará")
_ROLE_LABELS = {
    BoardRole.PRESIDENTE: "Presidente",
    BoardRole.MEMBRO: "Membro",
    BoardRole.SUPLENTE: "Suplente",
}
_ANALYZED = (
    (DocumentKind.TABELA, "Tabela de Pontuação"),
    (DocumentKind.RELATORIO, "Relatório de Atividades"),
    (DocumentKind.COMPROVANTE, "Comprovante de Documentos"),
)


@dataclass(frozen=True)
class OpinionRow:
    label: str
    value: str


@dataclass(frozen=True)
class OpinionSection:
    """A block of the Parecer: an optional heading, lines of text and table rows; `total` closes
    the table of points."""

    key: str
    heading: str | None
    lines: tuple[str, ...] = ()
    rows: tuple[OpinionRow, ...] = ()
    total: OpinionRow | None = None


@dataclass(frozen=True)
class Signature:
    name: str
    role: str


@dataclass(frozen=True)
class OpinionDocument:
    page: PageSetup
    header_lines: tuple[str, ...]
    title: str
    sections: tuple[OpinionSection, ...]
    signatures: tuple[Signature, ...]


def _modality_noun(process: FunctionalProcess) -> str:
    return "promoção" if process.modality is Modality.PROMOCAO else "progressão"


def _identification(
    process: FunctionalProcess, professor: Professor, unit: AcademicUnit
) -> tuple[str, ...]:
    """The six fields of the process as the person typed them (NMOV-01): nothing is deduced."""
    return (
        f"Docente: {professor.full_name}",
        f"Matrícula SIAPE: {professor.siape}",
        f"Unidade: {unit.name}",
        f"Modalidade: {_modality_noun(process).capitalize()}",
        f"Situação atual: nível {process.current_level} da classe {process.current_class} "
        f"({process.current_denomination})",
        f"Situação pretendida: nível {process.target_level} da classe {process.target_class} "
        f"({process.target_denomination})",
    )


def _ordinance_line(ordinance: BoardOrdinance) -> str:
    number = ordinance.number or BLANK_TEXT
    when = format_date(ordinance.ordinance_date) if ordinance.ordinance_date else BLANK_DATE
    return f"Portaria da banca: nº {number}, de {when}."


def _analyzed(versions_used: Mapping[DocumentKind, int | None]) -> tuple[str, ...]:
    lines = []
    for kind, name in _ANALYZED:
        number = versions_used.get(kind)
        lines.append(f"{name}: {NOT_GENERATED if number is None else f'versão {number}'}")
    return tuple(lines)


def _points(
    snapshot: Mapping[str, Any], group_names: Mapping[int, str]
) -> tuple[tuple[OpinionRow, ...], OpinionRow]:
    """Subtotal of each group and the total, as the snapshot has them; a group without a
    subtotal scored nothing."""
    subtotals = snapshot.get("subtotals", {})
    rows = tuple(
        OpinionRow(
            f"{roman(number)} - {name}",
            two_places(Decimal(subtotals.get(str(number), "0"))),
        )
        for number, name in sorted(group_names.items())
    )
    return rows, OpinionRow("Total geral", two_places(Decimal(snapshot["total"])))


def _minimum_line(minimum: MinimumComparison) -> str:
    if minimum.minimum is None:
        return "Mínimo de referência: não definido pela norma aplicável"
    return f"Mínimo de referência: {two_places(minimum.minimum)} pontos"


def _conclusion_line(
    process: FunctionalProcess,
    professor: Professor,
    conclusion: OpinionConclusion,
    interstice: Interstice,
) -> str:
    stance = "FAVORÁVEL" if conclusion is OpinionConclusion.FAVORAVEL else "DESFAVORÁVEL"
    return (
        f"A banca manifesta-se {stance} à {_modality_noun(process)} de {professor.full_name}, "
        f"do nível {process.current_level} da classe {process.current_class} "
        f"({process.current_denomination}) para o nível {process.target_level} da classe "
        f"{process.target_class} ({process.target_denomination}), referente ao interstício "
        f"de {format_interstice(interstice)}."
    )


def _place_and_date(opinion: BoardOpinion) -> str:
    place = (opinion.place or "").strip() or BLANK_TEXT
    when = format_date(opinion.opinion_date) if opinion.opinion_date else BLANK_DATE
    return f"{place}, {when}"


def build_opinion(
    process: FunctionalProcess,
    professor: Professor,
    unit: AcademicUnit,
    ordinance: BoardOrdinance,
    opinion: BoardOpinion,
    table_snapshot: Mapping[str, Any],
    versions_used: Mapping[DocumentKind, int | None],
    minimum: MinimumComparison,
    group_names: Mapping[int, str],
    page: PageSetup,
) -> OpinionDocument:
    """`versions_used` maps each kind to the number of the version the Parecer analyzed (`None`:
    never generated). Without a conclusion there is no Parecer: `ValueError` (PAR-12)."""
    if opinion.conclusion is None:
        raise ValueError("the Parecer needs the conclusion chosen by a person")
    interstice = Interstice(process.start_date, process.end_date)
    point_rows, total = _points(table_snapshot, group_names)
    sections = [
        OpinionSection("identificacao", "Identificação", _identification(process, professor, unit)),
        OpinionSection("portaria", "Portaria da banca", (_ordinance_line(ordinance),)),
        OpinionSection("intersticio", "Interstício", (format_interstice(interstice),)),
        OpinionSection("documentos", "Documentos analisados", _analyzed(versions_used)),
        OpinionSection("pontos", "Pontuação por grupo", rows=point_rows, total=total),
        OpinionSection("minimo", None, (_minimum_line(minimum),)),
        OpinionSection(
            "conclusao",
            "Conclusão",
            (_conclusion_line(process, professor, opinion.conclusion, interstice),),
        ),
    ]
    notes = (opinion.notes or "").strip()
    if notes:
        sections.append(OpinionSection("observacoes", "Observações", (notes,)))
    sections.append(OpinionSection("local_data", None, (_place_and_date(opinion),)))
    return OpinionDocument(
        page=page,
        header_lines=(*_HEADER, unit.name),
        title="PARECER",
        sections=tuple(sections),
        signatures=tuple(Signature(m.name, _ROLE_LABELS[m.role]) for m in ordinance.members),
    )
