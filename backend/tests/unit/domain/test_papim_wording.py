"""SEG-09: PAPIM and "intervenção metodológica" confirm only the extension coordination item."""

import json
from pathlib import Path

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_extension_project

TABLE = Path(__file__).resolve().parents[3] / "app/infrastructure/database/seed_data/ufpa.json"
GROUP_IV = next(
    group
    for group in json.loads(TABLE.read_text(encoding="utf-8"))["groups"]
    if group["number"] == 4
)
DESCRIPTION = {item["item_number"]: item["description"] for item in GROUP_IV["criteria"]}

PAPIM_TEXTS = [
    "Programa de Apoio a Projetos de Intervenção Metodológica - PAPIM",
    "Projeto PAPIM Dados Abertos",
    "projeto de INTERVENCAO METODOLOGICA em dados",
]


def test_the_official_table_names_papim_only_in_the_coordination_item_iv_1():
    assert "PAPIM" in DESCRIPTION[1] and "Intervenção Metodológica" in DESCRIPTION[1]
    assert "PAPIM" not in DESCRIPTION[2]
    assert "Intervenção Metodológica" not in DESCRIPTION[2]


@pytest.mark.parametrize("text", PAPIM_TEXTS)
def test_papim_wording_confirms_the_coordination_of_an_extension_project(text):
    assert confirm_extension_project(T.EXTENSAO_PROJETO_COORDENACAO, text) is (
        T.EXTENSAO_PROJETO_COORDENACAO
    )


@pytest.mark.parametrize("text", PAPIM_TEXTS)
def test_papim_wording_does_not_confirm_a_participation_in_an_extension_project(text):
    assert confirm_extension_project(T.EXTENSAO_PROJETO_PARTICIPACAO, text) is T.OUTRA


def test_the_word_extension_still_confirms_both_items():
    text = "Projeto de Extensão Dados Abertos"
    assert confirm_extension_project(T.EXTENSAO_PROJETO_COORDENACAO, text) is (
        T.EXTENSAO_PROJETO_COORDENACAO
    )
    assert confirm_extension_project(T.EXTENSAO_PROJETO_PARTICIPACAO, text) is (
        T.EXTENSAO_PROJETO_PARTICIPACAO
    )
