"""NTIT-01, NTIT-03: the order of the titrations."""

import pytest

from app.domain.entities.professor import TITRATION_ORDER, Titration, titration_at_least


def test_order_is_graduacao_especializacao_mestrado_doutorado():
    assert TITRATION_ORDER == (
        Titration.GRADUACAO,
        Titration.ESPECIALIZACAO,
        Titration.MESTRADO,
        Titration.DOUTORADO,
    )


def test_every_titration_has_a_place_in_the_order():
    assert set(TITRATION_ORDER) == set(Titration)
    assert len(TITRATION_ORDER) == len(Titration)


@pytest.mark.parametrize(
    ("actual", "required", "expected"),
    [
        (Titration.MESTRADO, Titration.DOUTORADO, False),
        (Titration.DOUTORADO, Titration.DOUTORADO, True),
        (Titration.DOUTORADO, Titration.MESTRADO, True),
        (Titration.GRADUACAO, Titration.ESPECIALIZACAO, False),
        (Titration.ESPECIALIZACAO, Titration.GRADUACAO, True),
    ],
)
def test_titration_at_least(actual, required, expected):
    assert titration_at_least(actual, required) is expected
