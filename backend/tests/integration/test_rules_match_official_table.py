"""MAP-03: every suggestion rule item (principal and alternative) exists in the official table."""

import pytest

from app.domain.entities.activity import Level
from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules import suggestion_rules
from app.domain.rules.suggestion_rules import Item, suggest_item
from app.infrastructure.database.seed import seed_reference_data, seed_scoring_tables
from tests.integration.test_seed import ADMIN_EMAIL, FakeHasher


@pytest.fixture
def official(uow_factory):
    seed_reference_data(uow_factory(), ADMIN_EMAIL, "first-password", FakeHasher())
    seed_scoring_tables(uow_factory())
    with uow_factory() as uow:
        table = next(
            t for t in uow.scoring_tables.list_tables() if t.name == "Tabela de Pontuação da UFPA"
        )
        return uow.scoring_tables.list_versions(table.id)[0]


def _suggested_items() -> dict[str, set[Item]]:
    """Every item each rule can produce, including the Group I rule for every level."""
    found: dict[str, set[Item]] = {}
    for taxonomy in T:
        for level in (None, Level.GRADUACAO, Level.POS_GRADUACAO):
            suggestion = suggest_item(taxonomy, level)
            items = {suggestion.principal, *suggestion.alternatives} - {None}
            found.setdefault(taxonomy.value, set()).update(items)
    return found


def _missing(version) -> list[tuple[str, Item]]:
    return [
        (taxonomy, item)
        for taxonomy, items in _suggested_items().items()
        for item in sorted(items, key=lambda i: (i.group, i.item))
        if version.get_criterion(item.group, item.item) is None
    ]


def test_every_principal_and_alternative_item_exists_in_the_official_table(official):
    assert _missing(official) == []


def test_every_rule_with_an_item_was_checked(official):
    checked = {taxonomy for taxonomy, items in _suggested_items().items() if items}
    without_item = {T.COORIENTACAO_TCC_GRADUACAO, T.BANCA_PROCESSO_SELETIVO,
                    T.EXTENSAO_EVENTO_MINISTRANTE, T.OUTRA}  # fmt: skip
    assert checked == {t.value for t in T} - {t.value for t in without_item}


def test_a_rule_pointing_to_a_missing_item_fails_the_check(official, monkeypatch):
    fake = suggestion_rules._rule(3, 12)  # III.12 does not exist in the official table
    monkeypatch.setitem(suggestion_rules._RULES, T.BANCA_SELECAO_POS, fake)

    assert _missing(official) == [("BANCA_SELECAO_POS", Item(3, 12))]


def test_an_alternative_pointing_to_a_missing_item_fails_the_check(official, monkeypatch):
    fake = suggestion_rules._rule(8, 11, (8, 63))  # VIII.63 only existed in the old numbering
    monkeypatch.setitem(suggestion_rules._RULES, T.ARTIGO_NAO_INDEXADO, fake)

    assert _missing(official) == [("ARTIGO_NAO_INDEXADO", Item(8, 63))]
