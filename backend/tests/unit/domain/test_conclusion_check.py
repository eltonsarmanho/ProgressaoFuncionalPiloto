"""DEL-01, DEL-02: a process may be concluded only with the three kinds PRONTO and no operation
running."""

import pytest

from app.domain.entities.conclusion import ConclusionCheck
from app.domain.entities.generated import DocumentKind, GenerationCode
from app.domain.rules.conclusion_rules import check_conclusion

ALL_KINDS = (DocumentKind.TABELA, DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)


def test_all_three_kinds_ready_and_nothing_running_allows_the_conclusion():
    check = check_conclusion(ALL_KINDS, 0)

    assert check == ConclusionCheck()
    assert check.allowed is True


def test_without_a_ready_comprovante_it_refuses_listing_only_the_comprovante():
    check = check_conclusion({DocumentKind.TABELA, DocumentKind.RELATORIO}, 0)

    assert check.allowed is False
    assert check.code is GenerationCode.ARTEFATOS_PENDENTES
    assert check.missing_kinds == (DocumentKind.COMPROVANTE,)


def test_without_any_ready_kind_it_lists_the_three_in_table_report_comprovante_order():
    check = check_conclusion((), 0)

    assert check.code is GenerationCode.ARTEFATOS_PENDENTES
    assert check.missing_kinds == (
        DocumentKind.TABELA,
        DocumentKind.RELATORIO,
        DocumentKind.COMPROVANTE,
    )


def test_the_missing_kinds_follow_the_fixed_order_whatever_the_input_order():
    check = check_conclusion([DocumentKind.RELATORIO], 0)

    assert check.missing_kinds == (DocumentKind.TABELA, DocumentKind.COMPROVANTE)


@pytest.mark.parametrize("missing", ALL_KINDS)
def test_each_single_missing_kind_is_the_only_one_listed(missing):
    ready = [kind for kind in ALL_KINDS if kind is not missing]

    check = check_conclusion(ready, 0)

    assert check.code is GenerationCode.ARTEFATOS_PENDENTES
    assert check.missing_kinds == (missing,)


@pytest.mark.parametrize("running", [1, 2, 7])
def test_an_operation_in_progress_refuses_with_operacao_em_andamento(running):
    check = check_conclusion(ALL_KINDS, running)

    assert check.allowed is False
    assert check.code is GenerationCode.OPERACAO_EM_ANDAMENTO
    assert check.missing_kinds == ()


def test_the_pending_artifacts_are_reported_before_an_operation_in_progress():
    # The design lists ARTEFATOS_PENDENTES first (DEL-01 before DEL-02).
    check = check_conclusion([DocumentKind.TABELA], 1)

    assert check.code is GenerationCode.ARTEFATOS_PENDENTES
    assert check.missing_kinds == (DocumentKind.RELATORIO, DocumentKind.COMPROVANTE)


def test_a_repeated_kind_in_the_ready_set_changes_nothing():
    check = check_conclusion([*ALL_KINDS, DocumentKind.TABELA], 0)

    assert check.allowed is True
