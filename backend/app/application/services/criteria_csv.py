"""Parser of the scoring criteria CSV (ADM-08, ADM-09): pure, stdlib `csv`, all-errors.

Comma separated, UTF-8 with or without BOM, dot as the decimal separator. Header
columns: grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite. The optional column
`min_hours` carries the minimum course load of a criterion; empty or absent means none.
"""

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.domain.entities.scoring import ScoringCriterion, ScoringMode

COLUMNS = (
    "grupo",
    "item",
    "descricao",
    "unidade",
    "modo",
    "pontos",
    "horas_por_bloco",
    "limite",
)
OPTIONAL_COLUMNS = ("min_hours",)


@dataclass(frozen=True)
class CsvError:
    line: int
    field: str
    message: str


@dataclass(frozen=True)
class CsvParseResult:
    criteria: tuple[ScoringCriterion, ...] = ()
    lines: tuple[int, ...] = ()  # source line of each criterion
    errors: tuple[CsvError, ...] = ()


def _decimal(value: str) -> Decimal | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() and number >= 0 else None


def _row_criterion(
    line: int, row: dict[str, str], errors: list[CsvError]
) -> ScoringCriterion | None:
    start = len(errors)

    def fail(field: str, message: str) -> None:
        errors.append(CsvError(line, field, message))

    def integer(field: str, low: int, high: int | None) -> int | None:
        text = row[field]
        if not text.isascii() or not text.isdigit() or int(text) < low:
            fail(field, f"deve ser um inteiro a partir de {low}")
        elif high is not None and int(text) > high:
            fail(field, f"deve estar entre {low} e {high}")
        else:
            return int(text)
        return None

    def optional_decimal(field: str) -> Decimal | None:
        text = row[field]
        if not text:
            return None
        number = _decimal(text)
        if number is None:
            fail(field, "número decimal inválido (use ponto e valor não negativo)")
        return number

    group = integer("grupo", 1, 8)
    item = integer("item", 1, None)
    if not row["descricao"]:
        fail("descricao", "descrição é obrigatória")
    mode = None
    try:
        mode = ScoringMode(row["modo"])
    except ValueError:
        fail("modo", f"modo inválido; use um de: {', '.join(m.value for m in ScoringMode)}")
    points = optional_decimal("pontos")
    hours = optional_decimal("horas_por_bloco")
    limit = optional_decimal("limite")
    min_hours = optional_decimal("min_hours") if "min_hours" in row else None
    if mode is ScoringMode.POR_UNIDADE and not row["pontos"]:
        fail("pontos", "obrigatório no modo POR_UNIDADE")
    if mode is ScoringMode.POR_BLOCO_DE_HORAS:
        if not row["pontos"]:
            fail("pontos", "obrigatório no modo POR_BLOCO_DE_HORAS")
        if hours is None and not row["horas_por_bloco"]:
            fail("horas_por_bloco", "obrigatório no modo POR_BLOCO_DE_HORAS")
        elif hours is not None and hours == 0:
            fail("horas_por_bloco", "deve ser maior que zero")
    if len(errors) > start:
        return None
    return ScoringCriterion(
        group_number=group,
        item_number=item,
        description=row["descricao"],
        unit_label=row["unidade"],
        mode=mode,
        unit_points=points,
        hours_per_block=hours,
        min_hours=min_hours,
        max_points=limit,
    )


def parse_criteria_csv(text: str) -> CsvParseResult:
    reader = csv.reader(io.StringIO(text.removeprefix("﻿")))
    rows = [(reader.line_num, row) for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return CsvParseResult(errors=(CsvError(1, "arquivo", "arquivo vazio"),))
    header_line, raw_header = rows[0]
    header = [name.strip() for name in raw_header]
    errors = [
        CsvError(header_line, name, "coluna obrigatória ausente")
        for name in COLUMNS
        if name not in header
    ] + [
        CsvError(header_line, name, "coluna desconhecida")
        for name in header
        if name not in COLUMNS + OPTIONAL_COLUMNS
    ]
    if errors:
        return CsvParseResult(errors=tuple(errors))
    if len(rows) == 1:
        return CsvParseResult(
            errors=(CsvError(header_line, "arquivo", "nenhum critério no arquivo"),)
        )

    criteria: list[ScoringCriterion] = []
    lines: list[int] = []
    seen: set[tuple[int, int]] = set()
    for line, cells in rows[1:]:
        if len(cells) != len(header):
            errors.append(
                CsvError(
                    line, "linha", f"esperadas {len(header)} colunas, encontradas {len(cells)}"
                )
            )
            continue
        row = {name: cell.strip() for name, cell in zip(header, cells, strict=True)}
        criterion = _row_criterion(line, row, errors)
        if criterion is None:
            continue
        key = (criterion.group_number, criterion.item_number)
        if key in seen:
            errors.append(CsvError(line, "item", f"critério {key[0]}.{key[1]} repetido no arquivo"))
        seen.add(key)
        criteria.append(criterion)
        lines.append(line)
    if errors:
        return CsvParseResult(errors=tuple(errors))
    return CsvParseResult(criteria=tuple(criteria), lines=tuple(lines))
