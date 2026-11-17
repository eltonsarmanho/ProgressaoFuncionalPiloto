"""ADM-08, ADM-09: pure parser of the criteria CSV; reports every invalid line and field."""

from decimal import Decimal

import pytest

from app.application.services.criteria_csv import parse_criteria_csv
from app.domain.entities.scoring import ScoringMode

HEADER = "grupo,item,descricao,unidade,modo,pontos,horas_por_bloco,limite"


def csv(*rows: str, header: str = HEADER) -> str:
    return "\n".join([header, *rows]) + "\n"


def errors_of(text: str) -> list[tuple[int, str]]:
    return [(e.line, e.field) for e in parse_criteria_csv(text).errors]


def test_valid_csv_becomes_typed_criteria():
    result = parse_criteria_csv(
        csv(
            "2,7,Orientação de TCC,por aluno,POR_UNIDADE,10.50,,30",
            "4,4,Curso de extensão,a cada 3 horas,POR_BLOCO_DE_HORAS,2,3,",
            "8,66,Outras atividades,ponto,VALOR_INFORMADO,,,5",
            "1,3,Aulas,horas,CARGA_SEMANAL,,,",
        )
    )

    assert result.errors == ()
    a, b, c, d = result.criteria
    assert (a.group_number, a.item_number) == (2, 7)
    assert a.description == "Orientação de TCC"
    assert a.unit_label == "por aluno"
    assert a.mode is ScoringMode.POR_UNIDADE
    assert a.unit_points == Decimal("10.50")
    assert a.hours_per_block is None
    assert a.max_points == Decimal("30")
    assert b.mode is ScoringMode.POR_BLOCO_DE_HORAS
    assert (b.unit_points, b.hours_per_block, b.max_points) == (Decimal("2"), Decimal("3"), None)
    assert c.mode is ScoringMode.VALOR_INFORMADO
    assert (c.unit_points, c.max_points) == (None, Decimal("5"))
    assert d.mode is ScoringMode.CARGA_SEMANAL


def test_utf8_bom_is_accepted():
    result = parse_criteria_csv("﻿" + csv("2,7,Orientação,por aluno,POR_UNIDADE,10,,"))

    assert result.errors == ()
    assert result.criteria[0].description == "Orientação"


def test_quoted_commas_and_blank_lines_are_handled():
    result = parse_criteria_csv(
        csv(
            '2,7,"Orientação, tutoria",por aluno,POR_UNIDADE,10,,',
            "",
            "2,8,Outra,x,POR_UNIDADE,1,,",
        )
    )

    assert result.errors == ()
    assert result.criteria[0].description == "Orientação, tutoria"
    assert len(result.criteria) == 2


def test_reports_every_invalid_line_and_field_without_stopping_at_the_first():
    result = parse_criteria_csv(
        csv(
            "9,7,Ok,x,POR_UNIDADE,10,,",  # line 2: grupo out of range
            "2,0,Ok,x,POR_UNIDADE,10,,",  # line 3: item < 1
            "2,8,Ok,x,INEXISTENTE,10,,",  # line 4: modo
            "2,9,Ok,x,POR_UNIDADE,abc,,",  # line 5: pontos
            "2,10,Ok,x,POR_UNIDADE,10,,-1",  # line 6: limite negative
            "2,11,,x,POR_UNIDADE,10,,",  # line 7: descricao empty
            "x,y,Ok,x,POR_UNIDADE,10,,",  # line 8: grupo and item
        )
    )

    assert result.criteria == ()
    assert [(e.line, e.field) for e in result.errors] == [
        (2, "grupo"),
        (3, "item"),
        (4, "modo"),
        (5, "pontos"),
        (6, "limite"),
        (7, "descricao"),
        (8, "grupo"),
        (8, "item"),
    ]
    assert all(e.message for e in result.errors)


def test_several_errors_in_one_line_are_all_listed():
    assert errors_of(csv("0,0,Ok,x,POR_UNIDADE,10,,")) == [(2, "grupo"), (2, "item")]


def test_decimal_comma_is_rejected_because_the_separator_is_a_dot():
    assert errors_of(csv('2,7,Ok,x,POR_UNIDADE,"1,5",,')) == [(2, "pontos")]


def test_mode_requirements_on_points_and_hours_per_block():
    assert errors_of(
        csv(
            "2,7,Ok,x,POR_UNIDADE,,,",
            "4,4,Ok,x,POR_BLOCO_DE_HORAS,2,,",
            "4,5,Ok,x,POR_BLOCO_DE_HORAS,,3,",
            "4,6,Ok,x,POR_BLOCO_DE_HORAS,2,0,",
        )
    ) == [(2, "pontos"), (3, "horas_por_bloco"), (4, "pontos"), (5, "horas_por_bloco")]


def test_repeated_group_and_item_is_an_error_on_the_second_line():
    assert errors_of(
        csv("2,7,Ok,x,POR_UNIDADE,10,,", "2,7,Outra,x,POR_UNIDADE,5,,")
    ) == [(3, "item")]


def test_missing_column_is_reported_on_the_header_line():
    header = "grupo,item,descricao,unidade,modo,pontos,limite"

    result = parse_criteria_csv(csv("2,7,Ok,x,POR_UNIDADE,10,", header=header))

    assert result.criteria == ()
    assert [(e.line, e.field) for e in result.errors] == [(1, "horas_por_bloco")]


def test_unknown_column_is_reported_on_the_header_line():
    assert errors_of(csv(header=HEADER + ",extra")) == [(1, "extra")]


def test_row_with_a_different_number_of_columns_is_an_error():
    assert errors_of(csv("2,7,Ok,x,POR_UNIDADE")) == [(2, "linha")]


@pytest.mark.parametrize("text", ["", "\n\n"])
def test_empty_file_is_an_error(text):
    result = parse_criteria_csv(text)

    assert result.criteria == ()
    assert [(e.line, e.field) for e in result.errors] == [(1, "arquivo")]


def test_header_only_file_has_no_criteria_and_is_an_error():
    assert errors_of(csv()) == [(1, "arquivo")]
