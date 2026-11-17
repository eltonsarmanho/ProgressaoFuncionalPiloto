"""PROC-12 (status transitions / read-only), DOC-04 (restricted enums), roles, domain errors."""

import pytest

from app.domain.entities.process import ProcessStatus, can_transition
from app.domain.entities.professor import Titration, WorkRegime
from app.domain.entities.user import Role
from app.domain.errors import ValidationFailed

S = ProcessStatus
ROLES = list(Role)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("is_owner", [True, False])
@pytest.mark.parametrize(
    ("current", "target"),
    [(S.RASCUNHO, S.EM_ANDAMENTO), (S.EM_ANDAMENTO, S.CONCLUIDO)],
)
def test_forward_transitions_allowed(current, target, role, is_owner):
    assert can_transition(current, target, role, is_owner) is True


@pytest.mark.parametrize("current", [S.RASCUNHO, S.EM_ANDAMENTO, S.CONCLUIDO])
def test_archive_allowed_for_admin_or_owner(current):
    assert can_transition(current, S.ARQUIVADO, Role.ADMIN, False) is True
    assert can_transition(current, S.ARQUIVADO, Role.DOCENTE, True) is True
    assert can_transition(current, S.ARQUIVADO, Role.SECRETARIA, True) is True


@pytest.mark.parametrize("current", [S.RASCUNHO, S.EM_ANDAMENTO, S.CONCLUIDO])
@pytest.mark.parametrize("role", [Role.SECRETARIA, Role.DOCENTE])
def test_archive_denied_for_non_admin_non_owner(current, role):
    assert can_transition(current, S.ARQUIVADO, role, False) is False


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.RASCUNHO, S.RASCUNHO),
        (S.RASCUNHO, S.CONCLUIDO),
        (S.EM_ANDAMENTO, S.RASCUNHO),
        (S.EM_ANDAMENTO, S.EM_ANDAMENTO),
        (S.CONCLUIDO, S.RASCUNHO),
        (S.CONCLUIDO, S.EM_ANDAMENTO),
        (S.CONCLUIDO, S.CONCLUIDO),
        (S.ARQUIVADO, S.RASCUNHO),
        (S.ARQUIVADO, S.EM_ANDAMENTO),
        (S.ARQUIVADO, S.CONCLUIDO),
        (S.ARQUIVADO, S.ARQUIVADO),
    ],
)
def test_other_transitions_denied_even_for_admin_owner(current, target):
    assert can_transition(current, target, Role.ADMIN, True) is False


def test_concluded_and_archived_are_read_only():
    assert {s for s in S if s.is_read_only} == {S.CONCLUIDO, S.ARQUIVADO}


def test_status_values():
    assert {s.value for s in S} == {"RASCUNHO", "EM_ANDAMENTO", "CONCLUIDO", "ARQUIVADO"}


def test_titration_values_restricted():
    assert {t.value for t in Titration} == {
        "GRADUACAO",
        "ESPECIALIZACAO",
        "MESTRADO",
        "DOUTORADO",
    }


def test_work_regime_values_restricted():
    assert {w.value for w in WorkRegime} == {"20H", "40H", "DE"}


def test_role_values():
    assert {r.value for r in Role} == {"ADMIN", "SECRETARIA", "DOCENTE"}


def test_validation_failed_names_field():
    error = ValidationFailed("siape", "A matrícula SIAPE deve ter 7 dígitos.")
    assert error.field == "siape"
    assert error.message == "A matrícula SIAPE deve ter 7 dígitos."
