"""Test-only variants of the official scoring table, persisted next to it.

The official table is the only seeded table and belongs to both FASI and IFCH, so tests that
need "a table that is not the unit's one" or "a table whose group I counts points" build them
here from the official version. The seeded official version has group I inside the total
(GI-07); `add_legacy_ufpa_version` recreates the version it replaced, with group I outside the
total, for the tests of the previous rules (GI-06).
"""

import uuid
from dataclasses import replace
from decimal import Decimal

from app.domain.entities.scoring import ScoringCriterion, ScoringMode, ScoringTableVersion
from app.domain.repositories.ports import ScoringTableRecord

OTHER_TABLE = "Tabela Sintética Alternativa de Teste"
POINTS_TABLE = "Tabela Sintética com Grupo I em Pontos"
INFORMED_GROUP = 8
INFORMED_ITEM = 38  # the item after the last of group VIII of the official table (37)
LEGACY_UFPA_NAME = "Tabela oficial de pontuação UFPA"
LEGACY_UFPA_REFERENCE = (
    "Tabela oficial de pontuação para progressão docente da UFPA "
    "(planilha fornecida pelo usuário em 2026-11-17)"
)
LEGACY_UFPA_NOTES = (
    "Versão anterior à do Grupo I no total: o Grupo I é medido em horas de PIT por semestre e "
    "não entra no total (a fórmula do TOTAL da planilha soma só os Grupos II a VIII); o item "
    "VI.14 vale 6 pontos por ano (fórmula C*6 da célula)."
)


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

    Group I keeps the two weekly-load criteria. Group VIII gets a synthetic VALOR_INFORMADO item
    limited to 10 points, so the tests of informed points and limits keep a table that accepts
    them. The official table has no such item.
    """
    table = ScoringTableRecord(uuid.uuid4(), POINTS_TABLE, unit_ids=())
    uow.scoring_tables.add_table(table)
    group8 = official.get_group(INFORMED_GROUP).criteria
    assert INFORMED_ITEM == max(c.item_number for c in group8) + 1
    informed = ScoringCriterion(
        INFORMED_GROUP, INFORMED_ITEM, "Item de valor informado (sintético)", "pontos",
        ScoringMode.VALOR_INFORMADO, max_points=Decimal("10"),
    )  # fmt: skip
    with_group1 = _with_criteria(official, 1, official.get_group(1).criteria, counts_in_total=True)
    copy = replace(
        _with_criteria(with_group1, INFORMED_GROUP, (*group8, informed)),
        id=uuid.uuid4(),
        table_id=table.id,
        norm_reference="Tabela de teste",
    )
    uow.scoring_tables.add_version(copy)
    return copy


def add_legacy_ufpa_version(uow, official: ScoringTableVersion) -> ScoringTableVersion:
    """The version the seeded one replaced, in the same table (GI-06).

    Same rules as `official` except the ones GI-07 and GI-12 changed: group I in PIT hours
    outside the total (points 0, hours reported) and VI.14 at 6 points a year. It keeps the
    old name, so it is told apart from the seeded version, and it is not marked as superseded:
    a test that wants the previous rules chooses it by id. `official` may be the seeded version
    or any version of the same table; the copy is persisted next to it.
    """
    group6 = tuple(
        replace(c, unit_points=Decimal("6")) if c.item_number == 14 else c
        for c in official.get_group(6).criteria
    )
    outside = _with_criteria(official, 1, official.get_group(1).criteria, counts_in_total=False)
    legacy = replace(
        _with_criteria(outside, 6, group6),
        id=uuid.uuid4(),
        name=LEGACY_UFPA_NAME,
        norm_reference=LEGACY_UFPA_REFERENCE,
        notes=LEGACY_UFPA_NOTES,
        superseded_by_id=None,
    )
    uow.scoring_tables.add_version(legacy)
    return legacy
