"""CARR-02 / CARR-03: seeded Magistério Superior versions (design.md, 'Dados semeados')."""

from datetime import date

import pytest

from app.domain.entities.career import CareerClass, Modality, select_version
from app.domain.rules.career_catalog import (
    LEI_15141_2025,
    MAGISTERIO_SUPERIOR_VERSIONS,
    RES_4644_2015,
)


def test_catalog_has_exactly_the_two_versions():
    assert MAGISTERIO_SUPERIOR_VERSIONS == (RES_4644_2015, LEI_15141_2025)


def test_version_names_match_spec():
    assert RES_4644_2015.name == "Res. 4.644/2015-CONSEPE"
    assert LEI_15141_2025.name == "Lei 12.772/2012 com redação da Lei 15.141/2025"


def test_validity_periods():
    assert RES_4644_2015.valid_to == date(2024, 12, 31)
    assert LEI_15141_2025.valid_from == date(2025, 1, 1)
    assert LEI_15141_2025.valid_to is None
    assert select_version(MAGISTERIO_SUPERIOR_VERSIONS, date(2024, 12, 31)) is RES_4644_2015
    assert select_version(MAGISTERIO_SUPERIOR_VERSIONS, date(2025, 1, 1)) is LEI_15141_2025


def test_res_4644_classes():
    assert RES_4644_2015.classes == (
        CareerClass("A", ("Adjunto A", "Assistente A", "Auxiliar"), (1, 2), None),
        CareerClass("B", ("Assistente",), (1, 2), 24),
        CareerClass("C", ("Adjunto",), (1, 2, 3, 4), 24),
        CareerClass("D", ("Associado",), (1, 2, 3, 4), 24),
        CareerClass("E", ("Titular",), (1,), 24),
    )


def test_lei_15141_classes():
    assert LEI_15141_2025.classes == (
        CareerClass("A", ("Assistente",), (1,), None),
        CareerClass("B", ("Adjunto",), (1, 2, 3, 4), 36),
        CareerClass("C", ("Associado",), (1, 2, 3, 4), 24),
        CareerClass("D", ("Titular",), (1,), 24),
    )


@pytest.mark.parametrize("version", [RES_4644_2015, LEI_15141_2025])
def test_progression_minimum_is_24_months(version):
    assert version.progression_min_months == 24
    assert version.min_months(Modality.PROGRESSAO, "C") == 24


@pytest.mark.parametrize(
    ("version", "fragment"),
    [
        (RES_4644_2015, "Res. 4.644/2015"),
        (LEI_15141_2025, "Lei 15.141/2025"),
    ],
)
def test_every_version_has_norm_reference(version, fragment):
    assert version.norm_reference.strip() != ""
    assert fragment in version.norm_reference
