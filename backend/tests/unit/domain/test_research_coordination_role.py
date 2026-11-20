"""SEG-07: research coordination needs a coordination role of the professor in the text."""

import pytest

from app.domain.entities.extraction import TaxonomyCode as T
from app.domain.rules.suggestion_rules import confirm_research_coordination, suggest_item

PROFESSOR = "Fulana de Tal Exemplo"
COORDINATION = [T.PESQUISA_PROJETO_COORDENACAO, T.PESQUISA_GRUPO_COORDENACAO]


@pytest.mark.parametrize("taxonomy", COORDINATION)
def test_a_participation_certificate_has_no_coordination_item(taxonomy):
    text = (
        "Certificamos que Fulana de Tal Exemplo participou do desenvolvimento de um policy "
        "brief sobre dados abertos, com carga horária de 18 horas."
    )
    downgraded = confirm_research_coordination(taxonomy, text, PROFESSOR)
    assert downgraded is T.OUTRA
    assert suggest_item(downgraded).principal is None


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        "Declaramos que Fulana de Tal Exemplo é coordenadora do projeto de pesquisa Dados Abertos.",
        "Projeto de pesquisa Dados Abertos. Coordenador: Prof. Fulana de Tal Exemplo.",
        "EXEMPLO, Fulana de Tal, líder do grupo de pesquisa Dados e Sociedade.",
        "A professora Fulana de Tal Exemplo coordena o projeto de pesquisa Dados Abertos.",
    ],
)
def test_a_coordination_role_of_the_professor_keeps_the_item(taxonomy, text):
    assert confirm_research_coordination(taxonomy, text, PROFESSOR) is taxonomy


@pytest.mark.parametrize("taxonomy", COORDINATION)
@pytest.mark.parametrize(
    "text",
    [
        # another person coordinates; the professor is only a member
        "Projeto de pesquisa Dados Abertos. Coordenador: Beltrano Silva.\n"
        "Membros: Fulana de Tal Exemplo.",
        "Fulana de Tal Exemplo participou do projeto de pesquisa Dados Abertos, "
        "coordenado por Beltrano Silva.",
        # the role is stated but the professor is not named
        "Beltrano Silva é coordenador do projeto de pesquisa Dados Abertos.",
        # the professor is named but no coordination is stated
        "Fulana de Tal Exemplo é membro do grupo de pesquisa Dados e Sociedade.",
    ],
)
def test_coordination_of_someone_else_or_no_coordination_has_no_item(taxonomy, text):
    assert confirm_research_coordination(taxonomy, text, PROFESSOR) is T.OUTRA


@pytest.mark.parametrize("taxonomy", [t for t in T if t not in COORDINATION])
def test_every_other_type_passes_through(taxonomy):
    assert confirm_research_coordination(taxonomy, "participou", PROFESSOR) is taxonomy
