"""GTAB-20, GTAB-25, GTAB-27, GTAB-29, GTAB-42: the pure rules that block archiving, deleting
and editing the criteria of scoring tables. The codes and the texts live only in this module."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest

from app.domain.entities.scoring import ScoringTableVersion, TableStatus
from app.domain.rules.scoring_table_guards import (
    TableFacts,
    VersionFacts,
    criteria_read_only_reason,
    has_later_version,
    table_archive_blockers,
    table_delete_blockers,
    version_delete_blockers,
)


def free_version(**changes) -> VersionFacts:
    """A version of a plain table that nothing blocks (it has a sibling, so it is not alone)."""
    return replace(
        VersionFacts(
            process_count=0,
            default_unit_acronyms=(),
            replaces_other=False,
            is_superseded=False,
            has_later_version=False,
            is_only_version=False,
            table_archived=False,
            is_official=False,
        ),
        **changes,
    )


def free_table(**changes) -> TableFacts:
    return replace(
        TableFacts(
            is_official=False, process_count=0, default_unit_acronyms=(), table_archived=False
        ),
        **changes,
    )


def version_starting(valid_from: date) -> ScoringTableVersion:
    return ScoringTableVersion(
        table_id=None,
        name=f"v {valid_from}",
        valid_from=valid_from,
        valid_to=None,
        norm_reference="Ref",
        status=TableStatus.OFICIAL,
    )


def codes(blockers):
    return [b.code for b in blockers]


# --- version_delete_blockers -------------------------------------------------------------


def test_a_free_version_has_no_delete_blocker():
    assert version_delete_blockers(free_version()) == []


def test_the_official_table_protects_the_versions_that_are_not_superseded():
    blockers = version_delete_blockers(free_version(is_official=True))

    assert codes(blockers) == ["TABELA_OFICIAL_PROTEGIDA"]
    assert blockers[0].message == (
        "A versão atual da tabela oficial da UFPA não pode ser excluída; "
        "só as versões substituídas podem ser excluídas"
    )


def test_a_superseded_version_of_the_official_table_can_be_deleted():
    assert version_delete_blockers(free_version(is_official=True, is_superseded=True)) == []


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"process_count": 1}, "VERSAO_USADA_POR_PROCESSO"),
        ({"default_unit_acronyms": ("FASI",)}, "VERSAO_EM_USO_DE_UNIDADE"),
        ({"replaces_other": True}, "VERSAO_SUBSTITUI_OUTRA"),
    ],
    ids=["used-by-process", "in-use-of-unit", "replaces-other"],
)
def test_a_superseded_official_version_still_has_the_other_blockers(changes, code):
    facts = free_version(is_official=True, is_superseded=True, **changes)

    assert codes(version_delete_blockers(facts)) == [code]


def test_a_version_used_by_processes_says_how_many():
    one = version_delete_blockers(free_version(process_count=1))
    three = version_delete_blockers(free_version(process_count=3))

    assert codes(one) == ["VERSAO_USADA_POR_PROCESSO"]
    assert one[0].message == "A versão é usada por 1 processo e não pode ser excluída"
    assert one[0].count == 1
    assert three[0].message == "A versão é usada por 3 processos e não pode ser excluída"
    assert three[0].count == 3


def test_a_version_in_use_of_units_lists_the_acronyms_sorted():
    blockers = version_delete_blockers(free_version(default_unit_acronyms=("IFCH", "FASI")))

    assert codes(blockers) == ["VERSAO_EM_USO_DE_UNIDADE"]
    assert blockers[0].message == (
        "A versão está em uso das unidades FASI, IFCH; marque outra versão ou desmarque-a "
        "antes de excluir"
    )
    assert blockers[0].acronyms == ("FASI", "IFCH")


def test_a_version_that_replaces_another_is_blocked():
    blockers = version_delete_blockers(free_version(replaces_other=True))

    assert codes(blockers) == ["VERSAO_SUBSTITUI_OUTRA"]
    assert blockers[0].message == (
        "A versão substitui outra versão da tabela e não pode ser excluída"
    )


def test_the_only_version_of_a_table_points_to_deleting_the_table():
    blockers = version_delete_blockers(free_version(is_only_version=True))

    assert codes(blockers) == ["ULTIMA_VERSAO_DA_TABELA"]
    assert blockers[0].message == (
        'É a única versão da tabela; para removê-la use "Excluir tabela"'
    )


def test_all_the_blockers_of_a_version_come_in_the_stated_order():
    facts = free_version(
        is_official=True,
        process_count=2,
        default_unit_acronyms=("FASI",),
        replaces_other=True,
        is_only_version=True,
    )

    assert codes(version_delete_blockers(facts)) == [
        "TABELA_OFICIAL_PROTEGIDA",
        "VERSAO_USADA_POR_PROCESSO",
        "VERSAO_EM_USO_DE_UNIDADE",
        "VERSAO_SUBSTITUI_OUTRA",
        "ULTIMA_VERSAO_DA_TABELA",
    ]


def test_a_superseded_or_archived_or_later_version_is_not_a_delete_blocker_by_itself():
    facts = free_version(is_superseded=True, has_later_version=True, table_archived=True)

    assert version_delete_blockers(facts) == []


# --- table_archive_blockers --------------------------------------------------------------


def test_a_table_with_no_version_in_use_can_be_archived_even_if_official_or_used():
    facts = free_table(is_official=True, process_count=4)

    assert table_archive_blockers(facts) == []


def test_a_table_with_a_version_in_use_cannot_be_archived_and_lists_the_acronyms():
    blockers = table_archive_blockers(free_table(default_unit_acronyms=("IFCH", "FASI")))

    assert codes(blockers) == ["TABELA_COM_VERSAO_EM_USO"]
    assert blockers[0].message == (
        "A tabela tem versão em uso das unidades FASI, IFCH; marque outra tabela ou "
        "desmarque a versão antes de arquivar"
    )
    assert blockers[0].acronyms == ("FASI", "IFCH")


# --- table_delete_blockers ---------------------------------------------------------------


def test_a_free_table_has_no_delete_blocker():
    assert table_delete_blockers(free_table()) == []


def test_each_table_delete_blocker_alone():
    official = table_delete_blockers(free_table(is_official=True))
    used = table_delete_blockers(free_table(process_count=2))
    marked = table_delete_blockers(free_table(default_unit_acronyms=("FASI",)))

    assert codes(official) == ["TABELA_OFICIAL_PROTEGIDA"]
    assert official[0].message == (
        "A tabela oficial da UFPA não pode ser excluída; arquive-a se não for mais usada"
    )
    assert codes(used) == ["VERSAO_USADA_POR_PROCESSO"]
    assert used[0].message == (
        "A tabela tem versões usadas por 2 processos e não pode ser excluída"
    )
    assert used[0].count == 2
    assert codes(marked) == ["VERSAO_EM_USO_DE_UNIDADE"]
    assert marked[0].message == (
        "A tabela tem versão em uso das unidades FASI; marque outra tabela ou desmarque "
        "a versão antes de excluir"
    )


def test_the_table_delete_blockers_come_in_the_stated_order():
    facts = free_table(is_official=True, process_count=1, default_unit_acronyms=("FASI",))

    assert codes(table_delete_blockers(facts)) == [
        "TABELA_OFICIAL_PROTEGIDA",
        "VERSAO_USADA_POR_PROCESSO",
        "VERSAO_EM_USO_DE_UNIDADE",
    ]


def test_an_archived_table_is_not_a_delete_blocker():
    assert table_delete_blockers(free_table(table_archived=True)) == []


# --- criteria_read_only_reason -----------------------------------------------------------


def test_an_editable_version_has_no_read_only_reason():
    assert criteria_read_only_reason(free_version()) is None


def test_a_superseded_version_is_read_only_with_the_text_the_api_already_gives():
    reason = criteria_read_only_reason(free_version(is_superseded=True))

    assert reason.code == "VERSAO_SUBSTITUIDA"
    assert reason.message == "Versão substituída é somente leitura; altere a versão que a substitui"


def test_a_version_that_is_not_the_latest_is_read_only():
    reason = criteria_read_only_reason(free_version(has_later_version=True))

    assert reason.code == "VERSAO_NAO_MAIS_RECENTE"
    assert reason.message == (
        "Versão anterior é somente leitura; altere a versão mais recente ou crie uma nova versão"
    )


def test_a_version_used_by_a_process_is_read_only():
    reason = criteria_read_only_reason(free_version(process_count=1))

    assert reason.code == "VERSAO_USADA_POR_PROCESSO"
    assert reason.message == (
        "Versão já usada por processos não pode ser alterada; "
        "crie uma nova versão para alterar os critérios"
    )


def test_the_read_only_order_is_superseded_then_not_latest_then_used_by_a_process():
    everything = free_version(is_superseded=True, has_later_version=True, process_count=2)
    later_and_used = free_version(has_later_version=True, process_count=2)

    assert criteria_read_only_reason(everything).code == "VERSAO_SUBSTITUIDA"
    assert criteria_read_only_reason(later_and_used).code == "VERSAO_NAO_MAIS_RECENTE"


def test_a_later_version_counts_even_when_it_is_superseded_itself():
    mine = version_starting(date(2024, 1, 1))
    later_superseded = replace(version_starting(date(2025, 1, 1)), superseded_by_id=uuid4())

    assert has_later_version(mine, [mine, later_superseded]) is True


def test_only_a_version_that_starts_after_this_one_is_later():
    mine = version_starting(date(2024, 1, 1))
    earlier = version_starting(date(2023, 1, 1))
    same_day = version_starting(date(2024, 1, 1))

    assert has_later_version(mine, [mine, earlier, same_day]) is False
    assert has_later_version(earlier, [mine, earlier]) is True
