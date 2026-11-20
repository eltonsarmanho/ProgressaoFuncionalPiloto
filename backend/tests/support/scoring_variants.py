"""Test-only variants of the official scoring table, persisted next to it.

The official table is the only seeded table and belongs to both FASI and IFCH, so tests that
need "a table that is not the unit's one" or "a table whose group I counts points" build them
here from the official version.
"""

import uuid
from dataclasses import replace
from decimal import Decimal

from app.domain.entities.scoring import ScoringCriterion, ScoringMode, ScoringTableVersion
from app.domain.repositories.ports import ScoringTableRecord

OTHER_TABLE = "Tabela Alternativa de Teste"
POINTS_TABLE = "Tabela de Teste com Grupo I em Pontos"


def _with_criteria(version: ScoringTableVersion, group_number, criteria, **group_changes):
    groups = tuple(
        replace(g, criteria=criteria, **group_changes) if g.number == group_number else g
        for g in version.groups
    )
    return replace(version, groups=groups)


def add_other_table(uow, official: ScoringTableVersion) -> ScoringTableVersion:
    """A copy of the official version in a table of no unit, differing only in II.12 (10, not 5).

    The different II.12 lets a test see a table switch.
    """
    table = ScoringTableRecord(uuid.uuid4(), OTHER_TABLE, unit_ids=())
    uow.scoring_tables.add_table(table)
    criteria = tuple(
        replace(c, unit_points=Decimal("10")) if c.item_number == 12 else c
        for c in official.get_group(2).criteria
    )
    copy = replace(
        _with_criteria(official, 2, criteria),
        id=uuid.uuid4(),
        table_id=table.id,
        norm_reference="Tabela de teste, sem norma",
    )
    uow.scoring_tables.add_version(copy)
    return copy


def add_points_table(uow, official: ScoringTableVersion) -> ScoringTableVersion:
    """A copy of the official version whose group I counts in points, as the old FASI table.

    Group I keeps the two weekly-load criteria and gets I.3, a VALOR_INFORMADO item limited to
    10 points, so the tests of informed points and limits keep a table that accepts them.
    """
    table = ScoringTableRecord(uuid.uuid4(), POINTS_TABLE, unit_ids=())
    uow.scoring_tables.add_table(table)
    informed = ScoringCriterion(
        1, 3, "Avaliação discente (item de teste)", "pontos", ScoringMode.VALOR_INFORMADO,
        max_points=Decimal("10"),
    )  # fmt: skip
    copy = replace(
        _with_criteria(official, 1, (*official.get_group(1).criteria, informed),
                       counts_in_total=True),
        id=uuid.uuid4(),
        table_id=table.id,
        norm_reference="Tabela de teste",
    )  # fmt: skip
    uow.scoring_tables.add_version(copy)
    return copy
