"""TAB-07, DEL-12: errors of generation refusals and of deleted files carry code and message."""

import pytest

from app.domain.errors import (
    Conflict,
    DomainError,
    GenerationRefused,
    Gone,
    NotFound,
    StaleVersion,
    ValidationFailed,
)


@pytest.mark.parametrize("error_type", [GenerationRefused, Gone])
def test_the_new_errors_carry_code_and_message_and_are_domain_errors(error_type):
    error = error_type("SEM_ATIVIDADES_VALIDADAS", "Nenhuma atividade validada")

    assert error.code == "SEM_ATIVIDADES_VALIDADAS"
    assert error.message == "Nenhuma atividade validada"
    assert isinstance(error, DomainError)


@pytest.mark.parametrize("error_type", [GenerationRefused, Gone])
def test_the_new_errors_are_raised_and_caught_as_domain_errors(error_type):
    with pytest.raises(DomainError) as caught:
        raise error_type("ARQUIVO_EXCLUIDO", "O arquivo foi excluído")

    assert caught.value.code == "ARQUIVO_EXCLUIDO"
    assert "O arquivo foi excluído" in str(caught.value)


@pytest.mark.parametrize("error_type", [GenerationRefused, Gone])
def test_the_new_errors_do_not_inherit_a_status_already_mapped(error_type):
    # A subclass of NotFound, Conflict or ValidationFailed would be mapped to 404, 409 or 422
    # by the existing handlers instead of 422 and 410.
    assert not issubclass(error_type, (NotFound, Conflict, ValidationFailed))


def test_a_conflict_may_carry_a_code_and_keeps_its_message():
    error = Conflict("Segundo pedido igual", code="GERACAO_EM_ANDAMENTO")

    assert error.code == "GERACAO_EM_ANDAMENTO"
    assert str(error) == "Segundo pedido igual"


def test_a_conflict_without_code_has_none_and_stale_version_stays_a_conflict():
    assert Conflict("Documento já cadastrado").code is None
    assert StaleVersion("recarregue").code is None
    assert issubclass(StaleVersion, Conflict)
