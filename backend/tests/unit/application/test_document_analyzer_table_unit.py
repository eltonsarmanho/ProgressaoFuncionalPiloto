"""TER-02: the analyzer decides "por ano" by the unit of the official table of the process.

Every case runs with the real items of the official table (`ufpa.json`) as the process table,
so the path of `table_version` (the unit of the item, not only the taxonomy) is exercised.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.entities.document import DocAlertCode
from app.domain.entities.scoring import (
    ScoringCriterion,
    ScoringGroup,
    ScoringMode,
    ScoringTableVersion,
    TableStatus,
)
from app.domain.rules.interstice import Interstice
from tests.unit.application.analyzer_fakes import (
    PROFESSOR,
    FakeAi,
    FakeTextExtractor,
    activity,
    analyzer,
    payload,
    run,
    text_page,
)

SEED = Path(__file__).resolve().parents[3] / "app/infrastructure/database/seed_data/ufpa.json"
INTERSTICE = Interstice(date(2024, 11, 23), date(2026, 11, 23))


def official_table(unit_overrides: dict[tuple[int, int], str] | None = None) -> ScoringTableVersion:
    """The items of `ufpa.json` with their unit labels; `unit_overrides` swaps a unit."""
    overrides = unit_overrides or {}
    data = json.loads(SEED.read_text(encoding="utf-8"))
    groups = []
    for group in data["groups"]:
        criteria = tuple(
            ScoringCriterion(
                group["number"],
                item["item_number"],
                item["description"],
                overrides.get((group["number"], item["item_number"]), item["unit_label"]),
                ScoringMode.POR_UNIDADE,
                unit_points=item["unit_points"],
            )
            for item in group["criteria"]
        )
        groups.append(ScoringGroup(group["number"], f"Grupo {group['number']}", criteria=criteria))
    return ScoringTableVersion(
        table_id=None,
        name="Tabela oficial",
        valid_from=date(2020, 1, 1),
        valid_to=None,
        norm_reference="norma",
        status=TableStatus.OFICIAL,
        groups=tuple(groups),
    )


def start_only(taxonomy, title, role, verb):
    """A page with a start date and no term, and the AI answer for it."""
    text = (
        f"PORTARIA N. 300/2025\n{verb} {PROFESSOR} para {role} ({title}), "
        "a partir de 09/08/2025."
    )
    item = activity(
        taxonomy=taxonomy,
        title=title,
        role=role,
        event_date=None,
        start_date="2025-08-09",
        evidence_text=f"{verb} {PROFESSOR} para {role}",
    )
    return text, item


def director():
    return start_only(
        "FUNCAO_DIRETOR_FACULDADE",
        "Diretor da Faculdade",
        "exercer a funcao de Diretor",
        "Designar",
    )


def analyze(text, item, table):
    ai = FakeAi(payload(item, document_type="PORTARIA"))
    extractor = FakeTextExtractor(text_page(1, text))
    return run(analyzer(extractor, ai), interstice=INTERSTICE, table_version=table)


def codes(result):
    return [(a.code, a.activity_index) for a in result.alerts]


def test_a_yearly_item_of_the_table_is_open_ended_and_goes_to_review():
    text, item = director()
    result = analyze(text, item, official_table())
    [found] = result.activities
    assert (found.group_number, found.item_number) == (6, 6)
    assert found.needs_review is True
    assert (DocAlertCode.DATA_FIM_AUSENTE, 0) in codes(result)
    assert (DocAlertCode.QUANTIDADE_ESTIMADA, 0) in codes(result)
    assert found.quantity == 1  # 2025-08-09 to 2026-11-23: one complete year


def test_the_unit_of_the_table_decides_not_the_taxonomy():
    # a taxonomy outside the per-year list, placed by the table on an item "por ano"
    text, item = start_only(
        "PARTICIPACAO_EVENTO", "Participacao em comissao", "integrar a comissao", "Designar"
    )
    yearly = official_table({(7, 10): "por ano de exercício"})
    result = analyze(text, item, yearly)
    [found] = result.activities
    assert (found.group_number, found.item_number) == (7, 10)
    assert found.needs_review is True  # the open period is left for the human review


def test_an_item_per_action_keeps_the_single_day_and_is_not_sent_to_review():
    text, item = start_only(
        "PARTICIPACAO_EVENTO", "Participacao em comissao", "integrar a comissao", "Designar"
    )
    result = analyze(text, item, official_table())
    [found] = result.activities
    assert (found.group_number, found.item_number) == (7, 10)
    assert found.needs_review is False
    assert DocAlertCode.DATA_FIM_AUSENTE not in [a.code for a in result.alerts]


def test_a_start_only_function_before_the_interstice_is_partial_not_outside():
    text, item = director()
    text = text.replace("09/08/2025", "09/08/2023")
    item = item | {"start_date": "2023-08-09"}
    result = analyze(text, item, official_table())
    [found] = result.activities
    assert found.reasons == ()  # the open period reaches the interstice: not FORA


def test_a_non_string_term_is_refused_as_an_invalid_answer():
    text, item = director()
    result = analyze(text, item | {"term": 2}, official_table())
    assert result.activities == ()
    assert DocAlertCode.RESPOSTA_INVALIDA in [a.code for a in result.alerts]


@pytest.mark.parametrize("term", [2.5, ["2 anos"], {"anos": 2}, True])
def test_other_non_string_terms_are_refused_too(term):
    text, item = director()
    result = analyze(text, item | {"term": term}, official_table())
    assert result.activities == ()
    assert DocAlertCode.RESPOSTA_INVALIDA in [a.code for a in result.alerts]
