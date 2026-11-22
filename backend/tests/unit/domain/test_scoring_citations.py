"""NLINK-01, NLINK-03: scoring alerts cite the norm code of the table version.

The table versions here are synthetic (one group, one item), not the official table.
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.entities.activity import Activity
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from app.domain.rules.scoring_alerts import ScoringAlertCode
from app.domain.rules.scoring_engine import calculate
from app.domain.rules.scoring_table_choice import verify_table_choice

SYNTHETIC_CODE = "TABELA-SINTETICA"
UNIT = uuid4()
OTHER_UNIT = uuid4()
END = date(2024, 11, 23)
INTERSTICE = Interstice(date(2022, 11, 23), END)


def synthetic_version(norm_code=SYNTHETIC_CODE) -> ScoringTableVersion:
    criterion = ScoringCriterion(
        2, 7, "item sintético 2.7", "unidade", ScoringMode.POR_UNIDADE, unit_points=Decimal(10)
    )
    return ScoringTableVersion(
        table_id=None,
        name="Tabela sintética",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="Norma sintética, Anexo I",
        status=TableStatus.OFICIAL,
        groups=(ScoringGroup(2, "Grupo 2", counts_in_total=True, criteria=(criterion,)),),
        norm_code=norm_code,
    )


def activity_without_evidence() -> Activity:
    return Activity(
        id=uuid4(),
        process_id=uuid4(),
        created_by=uuid4(),
        group_number=2,
        item_number=7,
        quantity=Decimal(1),
        title="Atividade sintética",
        event_date=date(2023, 6, 1),
        evidence_note=None,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize("norm_code", [SYNTHETIC_CODE, None], ids=["linked", "unlinked"])
def test_table_choice_alert_cites_the_synthetic_version_code(norm_code):
    [alert] = verify_table_choice(synthetic_version(norm_code), (OTHER_UNIT,), UNIT, END)
    assert alert.code is ScoringAlertCode.TABELA_DE_OUTRA_UNIDADE
    assert alert.norm_code == norm_code


@pytest.mark.parametrize("norm_code", [SYNTHETIC_CODE, None], ids=["linked", "unlinked"])
def test_engine_row_alert_cites_the_synthetic_version_code(norm_code):
    activity = activity_without_evidence()
    result = calculate(synthetic_version(norm_code), [activity], INTERSTICE)
    [row] = [r for r in result.rows if r.activity_id == activity.id]
    [alert] = [a for a in row.alerts if a.code is ScoringAlertCode.SEM_COMPROVANTE]
    assert alert.norm_code == norm_code


def test_table_not_found_cites_the_official_table():
    [alert] = verify_table_choice(None, (), UNIT, END)
    assert alert.code is ScoringAlertCode.TABELA_NAO_ENCONTRADA
    assert alert.norm_code == "TABELA-OFICIAL-UFPA"


def test_synthetic_versions_differing_only_in_norm_code_are_equal():
    assert synthetic_version("TABELA-SINTETICA") == replace(
        synthetic_version(), norm_code="OUTRA-TABELA-SINTETICA"
    )
    assert synthetic_version(None) == synthetic_version()
