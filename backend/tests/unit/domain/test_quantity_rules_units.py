"""VER-12: the quantity of each item follows the unit of the official table (`ufpa.json`).

The unit of every item is read from the table and pinned to the quantity rule of the taxonomy
that suggests that item: "por ação" and the other per-event units count one per activity,
"por ano" counts the complete years inside the interstice, hours units keep the hours.
"""

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.entities.document import DocAlertCode
from app.domain.entities.extraction import ExtractedActivity
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.interstice import Interstice
from app.domain.rules.quantity_rules import derive_quantity
from app.domain.rules.suggestion_rules import suggest_item

TABLE_PATH = (
    Path(__file__).resolve().parents[3] / "app/infrastructure/database/seed_data/ufpa.json"
)
CRITERIA = {
    (group["number"], item["item_number"]): item
    for group in json.loads(TABLE_PATH.read_text(encoding="utf-8"))["groups"]
    for item in group["criteria"]
}

# The table labels VIII.36 "por unidade", but its description says "(ano/revista)": a consultancy
# is counted per year of exercise. Decision to confirm with the user (see the task report).
UNIT_OVERRIDES = {(8, 36): "ANO"}

INTERSTICE = Interstice(date(2023, 1, 1), date(2026, 12, 31))
THREE_YEARS = ExtractedActivity(
    taxonomy=T.OUTRA,
    page=1,
    evidence_text="texto",
    confidence=Decimal("0.9"),
    start_date=date(2023, 1, 1),
    end_date=date(2026, 1, 1),
    hours=Decimal(40),
)


def unit_class(group: int, number: int) -> str:
    """ACAO, ANO, HORAS or UNIDADE (one per activity) for a table item."""
    if (group, number) in UNIT_OVERRIDES:
        return UNIT_OVERRIDES[(group, number)]
    criterion = CRITERIA[(group, number)]
    if criterion["mode"] in ("CARGA_SEMANAL", "POR_BLOCO_DE_HORAS"):
        return "HORAS"
    if criterion["unit_label"].startswith("por ano"):
        return "ANO"
    if criterion["unit_label"] == "por ação":
        return "ACAO"
    return "UNIDADE"


def principal_of(taxonomy: T):
    return suggest_item(taxonomy, None).principal


SUGGESTED = [t for t in T if t is not T.DISCIPLINA_MINISTRADA and principal_of(t) is not None]


def with_taxonomy(taxonomy: T) -> ExtractedActivity:
    return replace(THREE_YEARS, taxonomy=taxonomy)


def unit_of(taxonomy: T) -> str:
    item = principal_of(taxonomy)
    return unit_class(item.group, item.item)


def ids(taxonomy: T) -> str:
    item = principal_of(taxonomy)
    return f"{taxonomy.value}-{item.group}.{item.item}"


@pytest.mark.parametrize("taxonomy", SUGGESTED, ids=ids)
def test_every_suggested_item_has_the_quantity_of_its_table_unit(taxonomy):
    unit = unit_of(taxonomy)

    result = derive_quantity(taxonomy, with_taxonomy(taxonomy), INTERSTICE)

    if unit == "ANO":
        assert result.quantity == Decimal(3)  # complete years inside the interstice
        assert DocAlertCode.QUANTIDADE_ESTIMADA in result.warnings
    elif unit == "HORAS":
        assert result.quantity is None
        assert result.hours == Decimal(40)
    else:  # ACAO: one per action; UNIDADE: one per activity (banca, aluno, unidade, interstício)
        assert result.quantity == Decimal(1)
        assert DocAlertCode.QUANTIDADE_ESTIMADA not in result.warnings


@pytest.mark.parametrize(
    "taxonomy", [T.EXTENSAO_PROJETO_COORDENACAO, T.EXTENSAO_PROJETO_PARTICIPACAO]
)
def test_extension_projects_are_per_action_one_each_whatever_the_period(taxonomy):
    # IV.1 and IV.2 are "por ação" in the official table: a three-year project is one action
    assert unit_of(taxonomy) == "ACAO"
    result = derive_quantity(taxonomy, with_taxonomy(taxonomy), INTERSTICE)
    assert result.quantity == Decimal(1)
    assert result.warnings == ()


@pytest.mark.parametrize(
    "taxonomy",
    [
        T.PESQUISA_PROJETO_COORDENACAO,
        T.COMISSAO_ADMINISTRACAO_SUPERIOR,
        T.COMISSAO_NDE_MEMBRO,
        T.COMISSAO_UNIDADE,
    ],
)
def test_items_per_year_of_exercise_count_complete_years(taxonomy):
    assert unit_of(taxonomy) == "ANO"
    result = derive_quantity(taxonomy, with_taxonomy(taxonomy), INTERSTICE)
    assert result.quantity == Decimal(3)


def test_a_per_year_item_without_a_full_year_is_zero_and_asks_for_the_quantity():
    short = ExtractedActivity(
        taxonomy=T.PESQUISA_GRUPO_MEMBRO,
        page=1,
        evidence_text="texto",
        confidence=Decimal("0.9"),
        start_date=date(2025, 1, 1),
        end_date=date(2025, 8, 1),
    )
    result = derive_quantity(T.PESQUISA_GRUPO_MEMBRO, short, INTERSTICE)
    assert result.quantity == Decimal(0)
    assert result.warnings == (DocAlertCode.QUANTIDADE_ESTIMADA,)


def test_the_table_is_read_with_the_units_the_rules_rely_on():
    assert unit_class(4, 1) == "ACAO" and unit_class(4, 2) == "ACAO"
    assert unit_class(5, 2) == "ANO" and unit_class(6, 13) == "ANO"
    assert unit_class(7, 11) == "HORAS"
    assert unit_class(3, 4) == "UNIDADE"
